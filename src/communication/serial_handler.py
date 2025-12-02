import asyncio
import re
import logging
import threading
import time
from typing import Optional, Callable
from datetime import datetime
from glob import glob

import numpy as np
import serial

from interfaces.communication import ISerialReader


BOARDS = [f"UNO{i}_" for i in range(0, 7)]  # UNO0_ ~ UNO6_
HEAD_BOARD = "UNO0_"


class BoardData:
    """단일 보드의 데이터"""

    def __init__(self, board: str, receive_time: datetime, data: dict):
        self.board = board
        self.receive_time = receive_time
        self.data = data


class SerialHandler(ISerialReader):
    """시리얼 통신 구현체 - 멀티포트 지원"""

    def __init__(self, baudrate: int = 115200, timeout: float = 2.0):
        self._baudrate = baudrate
        self._timeout = timeout
        self._logger = logging.getLogger("SerialHandler")

        # 멀티포트 관련
        self._ports: list[str] = []
        self._threads: list[threading.Thread] = []
        self._stop_event = threading.Event()

        # 보드 데이터 (스레드 간 공유)
        self._boards: dict[str, BoardData] = {}
        self._boards_lock = threading.Lock()
        self._update_cv = threading.Condition(self._boards_lock)
        self._revision = 0

    def _find_ports(self) -> list[str]:
        """사용 가능한 시리얼 포트 탐색"""
        ports = sorted(glob("/dev/ttyACM*") + glob("/dev/ttyUSB*"))
        self._logger.info(f"발견된 포트: {ports}")
        return ports

    def connect(self) -> None:
        """시리얼 포트 연결 및 스레드 시작"""
        self._ports = self._find_ports()
        if not self._ports:
            raise ConnectionError("사용 가능한 시리얼 포트가 없습니다")

        self._stop_event.clear()
        self._start_threads()
        self._logger.info(f"{len(self._ports)}개 포트 연결 완료")

    def disconnect(self) -> None:
        """모든 시리얼 연결 해제"""
        self._stop_event.set()
        for thread in self._threads:
            thread.join(timeout=3.0)
        self._threads.clear()
        self._ports.clear()
        self._logger.info("모든 시리얼 스레드 종료")

    def _start_threads(self) -> None:
        """각 포트별 스레드 시작"""
        for port in self._ports:
            thread = threading.Thread(
                target=self._serial_thread,
                args=(port,),
                daemon=True,
                name=f"Serial-{port}"
            )
            self._threads.append(thread)
            thread.start()
            self._logger.info(f"스레드 시작: {port}")

    def _serial_thread(self, port: str) -> None:
        """개별 포트 읽기 스레드"""
        s = None
        try:
            s = serial.Serial(port, self._baudrate, timeout=self._timeout)
            self._logger.info(f"[{port}] 연결 성공")

            # 아두이노 리셋 대기
            time.sleep(2.0)
            s.reset_input_buffer()
            self._logger.info(f"[{port}] 버퍼 초기화 완료")

            while not self._stop_event.is_set():
                line = s.readline()
                if not line:
                    continue

                try:
                    line = line.decode("utf-8").strip()
                except UnicodeDecodeError:
                    self._logger.warning(f"[{port}] Unicode decode error")
                    continue

                data = self._parse(line, port)
                if not data:
                    continue

                with self._update_cv:
                    self._boards[data.board] = data
                    self._revision += 1
                    self._update_cv.notify_all()
                    self._logger.info(f"[{port}] {data.board} 데이터 업데이트: {len(data.data)}개 채널")

        except Exception as e:
            self._logger.error(f"[{port}] 스레드 오류: {e}")
        finally:
            if s is not None:
                try:
                    s.close()
                    self._logger.info(f"[{port}] 연결 해제")
                except Exception:
                    pass

    def _parse(self, line: str, port: str) -> Optional[BoardData]:
        """텍스트 라인 파싱"""
        line = line.strip()
        if not line:
            return None

        # 포맷 1: UNO{n}_Ck:v
        matched = re.search(r"\b(UNO[0-6]_)C\d+\s*[:=]\s*-?\d+\b", line, flags=re.IGNORECASE)
        if matched:
            board = matched.group(1).upper()
            data = {}
            for m in re.finditer(rf"({board}C(\d+))\s*[:=]\s*(-?\d+)", line, flags=re.IGNORECASE):
                ch = int(m.group(2))
                val = int(m.group(3))
                data[f"{board}C{ch}"] = val
            self._logger.debug(f"[{port}] UNO 포맷 파싱: {board} -> {data}")
            return BoardData(board, datetime.now(), data)

        # 포맷 2: [UNO{n}] Ck=v
        matched = re.search(r"\[\s*(UNO[0-6])\s*\]", line, flags=re.IGNORECASE)
        if matched:
            bnorm = matched.group(1).upper()
            board = f"{bnorm}_"
            rest = re.sub(r"^\s*\[\s*" + bnorm + r"\s*\]\s*", "", line, flags=re.IGNORECASE)
            data = {}
            for m in re.finditer(r"\bC\s*(\d+)\s*[:=]\s*(-?\d+)\b", rest):
                ch = int(m.group(1))
                val = int(m.group(2))
                data[f"{board}C{ch}"] = val
            self._logger.debug(f"[{port}] 브래킷 포맷 파싱: {board} -> {data}")
            return BoardData(board, datetime.now(), data)

        self._logger.debug(f"[{port}] 파싱 실패: {line[:50]}")
        return None

    def _convert_to_matrix(self) -> tuple[np.ndarray, np.ndarray]:
        """축적된 보드 데이터를 head (2, 3), body (12, 7) 매트릭스로 변환"""
        head = np.zeros((2, 3), dtype=np.float32)
        body = np.zeros((12, 7), dtype=np.float32)

        for idx, board in enumerate(BOARDS):
            board_data = self._boards.get(board)
            if not board_data:
                continue
            data = board_data.data
            if not data:
                continue

            top = 2 * idx
            bottom = top + 1

            if board == HEAD_BOARD:
                # UNO0: head (2, 3) - C0~C2 → row 0, C3~C5 → row 1
                for c in range(3):
                    val = data.get(f"{board}C{c}")
                    if val is not None:
                        head[0][c] = val
                for c in range(3):
                    val = data.get(f"{board}C{3 + c}")
                    if val is not None:
                        head[1][c] = val
            else:
                # UNO1~UNO6: body (12, 7)
                body_top = top - 2
                body_bottom = bottom - 2
                for c in range(7):
                    val = data.get(f"{board}C{c}")
                    if val is not None:
                        body[body_top][c] = val
                for c in range(7):
                    val = data.get(f"{board}C{7 + c}")
                    if val is not None:
                        body[body_bottom][c] = val

        return head, body

    def read(self, timeout: float = 5.0) -> tuple[np.ndarray, np.ndarray]:
        """현재 수집된 데이터 반환 (동기)

        Args:
            timeout: 최소 1개 보드 데이터 수신 대기 시간

        Returns:
            tuple: (head (2, 3), body (12, 7))
        """
        start_time = time.time()

        # 최소 1개 이상의 보드 데이터가 있을 때까지 대기
        with self._update_cv:
            while not self._boards:
                remaining = timeout - (time.time() - start_time)
                if remaining <= 0:
                    self._logger.warning("데이터 수신 타임아웃")
                    break
                self._update_cv.wait(timeout=remaining)

        with self._boards_lock:
            received_boards = list(self._boards.keys())
            head, body = self._convert_to_matrix()

        self._logger.info(
            f"센서 데이터 반환 - 수신 보드: {received_boards}, "
            f"head: min={head.min():.0f}, max={head.max():.0f}, "
            f"body: min={body.min():.0f}, max={body.max():.0f}"
        )

        return head, body

    async def async_read(self, timeout: float = 5.0) -> tuple[np.ndarray, np.ndarray]:
        """현재 수집된 데이터 반환 (비동기)

        Returns:
            tuple: (head (2, 3), body (12, 7))
        """
        return await asyncio.to_thread(self.read, timeout)
