import asyncio
import re
import logging
from typing import Optional
from datetime import datetime

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
    """시리얼 통신 구현체 (b) - 텍스트 파싱 방식"""

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 2.0):
        self._port = port
        self._baudrate = baudrate
        self._timeout = timeout
        self._serial: Optional[serial.Serial] = None
        self._boards: dict[str, BoardData] = {}
        self._logger = logging.getLogger("SerialHandler")

    def connect(self) -> None:
        """시리얼 포트 연결"""
        self._serial = serial.Serial(
            port=self._port,
            baudrate=self._baudrate,
            timeout=self._timeout,
        )
        self._logger.info(f"Serial connection established for {self._port}")

    def disconnect(self) -> None:
        """시리얼 포트 연결 해제"""
        if self._serial and self._serial.is_open:
            self._serial.close()
            self._logger.info(f"Serial connection closed for {self._port}")

    def _parse(self, line: str) -> Optional[BoardData]:
        """텍스트 라인을 파싱하여 BoardData 반환

        지원 포맷:
        1) UNO{n}_Ck : v (예: UNO0_C0:123)
        2) [UNO{n}] Ck=v (예: [UNO0] C0=123)
        """
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
            self._logger.debug(f"Parsed UNO format: {board} -> {data}")
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
            self._logger.debug(f"Parsed bracket format: {board} -> {data}")
            return BoardData(board, datetime.now(), data)

        self._logger.warning(f"Failed to parse line: {line}")
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
                # 각 보드당 2행, C0~C6 → 첫 번째 행, C7~C13 → 두 번째 행
                body_top = top - 2  # UNO1부터 body 인덱스 0
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

    def _all_boards_received(self) -> bool:
        """모든 7개 보드 데이터가 수신되었는지 확인"""
        return all(board in self._boards for board in BOARDS)

    def read(self) -> tuple[np.ndarray, np.ndarray]:
        """시리얼에서 데이터 읽기 (동기 블로킹)

        모든 7개 보드(UNO0~UNO6) 데이터가 수신될 때까지 대기 후
        (head, body) 튜플 반환

        Returns:
            tuple: (head (2, 3), body (12, 7))
        """
        if not self._serial or not self._serial.is_open:
            raise ConnectionError("Serial port is not connected")

        # 새 프레임 시작 - 이전 데이터 클리어
        self._boards.clear()

        self._logger.info("시리얼 데이터 수신 대기 중...")
        read_count = 0

        while not self._all_boards_received():
            raw_line = self._serial.readline()
            read_count += 1

            if not raw_line:
                self._logger.info(f"[{read_count}] 타임아웃 - 데이터 없음")
                continue

            try:
                line = raw_line.decode("utf-8").strip()
            except UnicodeDecodeError:
                self._logger.warning(f"[{read_count}] Unicode decode error: {raw_line}")
                continue

            self._logger.info(f"[{read_count}] 수신: {line[:100]}")  # 최대 100자

            board_data = self._parse(line)
            if board_data:
                self._boards[board_data.board] = board_data
                received_boards = list(self._boards.keys())
                self._logger.info(f"[{read_count}] 파싱 성공: {board_data.board}, 수신된 보드: {received_boards}")
            else:
                self._logger.info(f"[{read_count}] 파싱 실패 - 무시됨")

        head, body = self._convert_to_matrix()

        # 수신된 센서 데이터 요약 로그
        self._logger.info(
            f"센서 데이터 수신 완료 - "
            f"head: min={head.min():.0f}, max={head.max():.0f}, "
            f"body: min={body.min():.0f}, max={body.max():.0f}"
        )

        return head, body

    async def async_read(self) -> tuple[np.ndarray, np.ndarray]:
        """시리얼에서 데이터 읽기 (비동기, 별도 스레드에서 실행)

        동기 read()를 별도 스레드에서 실행하여 이벤트 루프를 블로킹하지 않음

        Returns:
            tuple: (head (2, 3), body (12, 7))
        """
        return await asyncio.to_thread(self.read)
