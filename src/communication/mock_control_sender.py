import asyncio
import logging
import random
from typing import Callable, Awaitable

from interfaces.communication import IControlNodeSender
from domain.models import ControlPacket


class MockControlSender(IControlNodeSender):
    """테스트용 컨트롤 노드 Mock 구현체

    실제 컨트롤 노드에 연결하지 않고 목업 데이터를 생성합니다.
    """

    def __init__(self):
        self._sensor_callback: Callable[[dict], Awaitable[None]] | None = None
        self._listening = False
        self._listen_task: asyncio.Task | None = None
        self._logger = logging.getLogger("mock_control_sender")
        self._connected = False

    async def connect(self) -> None:
        """Mock 연결 (항상 성공)"""
        self._connected = True
        self._logger.info("[TEST MODE] Mock 컨트롤 노드 연결됨")

    async def disconnect(self) -> None:
        """Mock 연결 해제"""
        await self.stop_listening()
        self._connected = False
        self._logger.info("[TEST MODE] Mock 컨트롤 노드 연결 해제됨")

    async def send_packet(self, packet: ControlPacket) -> bool:
        """패킷 전송 Mock (항상 성공, 로그 출력)"""
        if not self._connected:
            raise ConnectionError("Not connected to mock control node")

        self._logger.info(f"[TEST MODE] 패킷 전송: posture={packet.posture.value}")
        self._logger.debug(f"[TEST MODE] 패킷 상세: {packet.to_dict()}")

        # Mock ACK (항상 성공)
        return True

    def set_sensor_callback(self, callback: Callable[[dict], Awaitable[None]]) -> None:
        """센서 데이터 수신 콜백 설정"""
        self._sensor_callback = callback

    async def start_listening(self) -> None:
        """Mock 센서 데이터 수신 시작 (랜덤 데이터 생성)"""
        if self._listening:
            return

        self._listening = True
        self._listen_task = asyncio.create_task(self._mock_listen_loop())
        self._logger.info("[TEST MODE] Mock 센서 데이터 수신 시작")

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
        self._logger.info("[TEST MODE] Mock 센서 데이터 수신 중지")

    async def _mock_listen_loop(self) -> None:
        """Mock 센서 데이터 생성 루프"""
        while self._listening:
            try:
                # 5초마다 랜덤 센서 데이터 생성
                await asyncio.sleep(5.0)

                if self._sensor_callback:
                    mock_data = self._generate_mock_sensor_data()
                    await self._sensor_callback(mock_data)
                    self._logger.debug(f"[TEST MODE] Mock 센서 데이터 생성: {mock_data}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"[TEST MODE] Mock listen loop 오류: {e}")
                await asyncio.sleep(1)

    def _generate_mock_sensor_data(self) -> dict:
        """Mock 센서 데이터 생성"""
        # 랜덤하게 0~3개의 zone을 활성화
        num_zones = random.randint(0, 3)
        zones = random.sample(range(1, 8), num_zones) if num_zones > 0 else []

        return {
            "inflated_zones": zones,
            "timestamp": asyncio.get_event_loop().time(),
            "mock": True,  # 테스트 데이터 표시
        }
