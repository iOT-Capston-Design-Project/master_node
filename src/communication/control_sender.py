import asyncio
import json
import logging
from typing import Callable, Awaitable

from interfaces.communication import IControlNodeSender
from domain.models import ControlPacket


class ControlSender(IControlNodeSender):
    """컨트롤 노드 통신 구현체 (c)"""

    def __init__(self, address: str, port: int = 8080):
        self._address = address
        self._port = port
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._sensor_callback: Callable[[dict], Awaitable[None]] | None = None
        self._listening = False
        self._listen_task: asyncio.Task | None = None
        self._logger = logging.getLogger("control_sender")
        self._ack_event: asyncio.Event = asyncio.Event()
        self._ack_received: bool = False

    async def connect(self) -> None:
        """컨트롤 노드 연결"""
        self._reader, self._writer = await asyncio.open_connection(
            self._address, self._port
        )

    async def disconnect(self) -> None:
        """연결 해제"""
        await self.stop_listening()
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()

    async def send_packet(self, packet: ControlPacket) -> bool:
        """통합 패킷 전송 (자세, 압력, 지속시간, controls 포함)"""
        if not self._writer:
            raise ConnectionError("Not connected to control node")

        # ACK 이벤트 초기화
        self._ack_event.clear()
        self._ack_received = False

        message = json.dumps(packet.to_dict()).encode() + b"\n"
        self._writer.write(message)
        await self._writer.drain()

        # _listen_loop에서 ACK를 수신할 때까지 대기
        try:
            await asyncio.wait_for(self._ack_event.wait(), timeout=5.0)
            return self._ack_received
        except asyncio.TimeoutError:
            self._logger.warning("ACK timeout")
            return False

    def set_sensor_callback(self, callback: Callable[[dict], Awaitable[None]]) -> None:
        """센서 데이터 수신 콜백 설정

        Args:
            callback: 센서 데이터(inflated_zones, timestamp) 수신 시 호출될 콜백
        """
        self._sensor_callback = callback

    async def start_listening(self) -> None:
        """컨트롤 노드로부터 센서 데이터 수신 시작"""
        if self._listening:
            return

        self._listening = True
        self._listen_task = asyncio.create_task(self._listen_loop())
        self._logger.info("Started listening for sensor data from control node")

    async def stop_listening(self) -> None:
        """센서 데이터 수신 중지"""
        self._listening = False
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
            self._listen_task = None
        self._logger.info("Stopped listening for sensor data")

    async def _listen_loop(self) -> None:
        """센서 데이터 및 ACK 수신 루프 (단일 reader로 모든 수신 처리)"""
        while self._listening and self._reader:
            try:
                line = await self._reader.readline()
                if not line:
                    self._logger.warning("Connection closed by control node")
                    break

                text = line.decode().strip()

                # ACK 응답 처리
                if text == "ACK":
                    self._ack_received = True
                    self._ack_event.set()
                    self._logger.debug("ACK received from control node")
                    continue

                # JSON 데이터 파싱
                try:
                    data = json.loads(text)

                    # inflated_zones 필드가 있으면 센서 데이터로 처리
                    if "inflated_zones" in data and self._sensor_callback:
                        await self._sensor_callback(data)
                        self._logger.info(f"Received sensor data: {data}")

                except json.JSONDecodeError as e:
                    self._logger.warning(f"Invalid JSON received: {e}, raw: {text}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Error in listen loop: {e}")
                await asyncio.sleep(1)  # 에러 발생 시 잠시 대기
