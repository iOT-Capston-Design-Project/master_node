import asyncio
import numpy as np

from interfaces.communication import ISerialReader


class MockSerialHandler(ISerialReader):
    """테스트용 Mock 시리얼 핸들러"""

    def __init__(
        self,
        preset_head: np.ndarray | None = None,
        preset_body: np.ndarray | None = None,
    ):
        self._preset_head = preset_head
        self._preset_body = preset_body
        self._connected = False

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def read(self, timeout: float = 5.0) -> tuple[np.ndarray, np.ndarray]:
        """Mock 데이터 반환 - head (2, 3), body (12, 7)"""
        if self._preset_head is not None and self._preset_body is not None:
            return self._preset_head, self._preset_body

        # 기본: 앙와위 자세 패턴 생성
        head = np.zeros((2, 3), dtype=np.float32)
        body = np.zeros((12, 7), dtype=np.float32)

        # 후두부 영역 (head)
        head[0:2, 0:3] = 400

        # 견갑골 영역 (body 상단)
        body[0:2, 1:6] = 300
        # 엉덩이 영역 (body 중앙)
        body[5:8, 1:6] = 600
        # 발뒤꿈치 영역 (body 하단)
        body[10:12, 1:3] = 350
        body[10:12, 4:6] = 350

        return head, body

    async def async_read(self, timeout: float = 5.0) -> tuple[np.ndarray, np.ndarray]:
        """비동기 Mock 데이터 반환"""
        return await asyncio.to_thread(self.read, timeout)

    def set_data(self, head: np.ndarray, body: np.ndarray) -> None:
        """테스트용 데이터 설정"""
        self._preset_head = head
        self._preset_body = body
