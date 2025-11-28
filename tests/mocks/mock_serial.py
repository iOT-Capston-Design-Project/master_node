import numpy as np

from interfaces.communication import ISerialReader


class MockSerialHandler(ISerialReader):
    """테스트용 Mock 시리얼 핸들러"""

    MATRIX_ROWS = 16
    MATRIX_COLS = 16

    def __init__(self, preset_matrix: np.ndarray | None = None):
        self._preset_matrix = preset_matrix
        self._connected = False

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def read_raw(self) -> bytes:
        """Mock 데이터 반환"""
        if self._preset_matrix is not None:
            return self._preset_matrix.astype(np.uint16).tobytes()

        # 기본: 앙와위 자세 패턴 생성
        matrix = np.zeros((self.MATRIX_ROWS, self.MATRIX_COLS), dtype=np.uint16)

        # 후두부 영역
        matrix[0:2, 6:10] = 400
        # 견갑골 영역
        matrix[2:5, 3:13] = 300
        # 엉덩이 영역
        matrix[9:13, 4:12] = 600
        # 발뒤꿈치 영역
        matrix[14:16, 4:7] = 350
        matrix[14:16, 9:12] = 350

        return matrix.tobytes()

    def to_matrix(self, data: bytes) -> np.ndarray:
        """바이트를 행렬로 변환"""
        values = np.frombuffer(data, dtype=np.uint16)
        matrix = values.reshape((self.MATRIX_ROWS, self.MATRIX_COLS))
        return matrix.astype(np.float32)

    def set_matrix(self, matrix: np.ndarray) -> None:
        """테스트용 행렬 설정"""
        self._preset_matrix = matrix
