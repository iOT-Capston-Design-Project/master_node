import numpy as np
import serial

from interfaces.communication import ISerialReader


class SerialHandler(ISerialReader):
    """시리얼 통신 구현체 (b)"""

    MATRIX_ROWS = 16
    MATRIX_COLS = 16

    def __init__(self, port: str, baudrate: int = 115200):
        self._port = port
        self._baudrate = baudrate
        self._serial: serial.Serial | None = None

    def connect(self) -> None:
        """시리얼 포트 연결"""
        self._serial = serial.Serial(
            port=self._port,
            baudrate=self._baudrate,
            timeout=1.0,
        )

    def disconnect(self) -> None:
        """시리얼 포트 연결 해제"""
        if self._serial and self._serial.is_open:
            self._serial.close()

    def read_raw(self) -> bytes:
        """시리얼에서 원시 데이터 읽기"""
        if not self._serial or not self._serial.is_open:
            raise ConnectionError("Serial port is not connected")

        expected_size = self.MATRIX_ROWS * self.MATRIX_COLS * 2  # 16-bit values
        data = self._serial.read(expected_size)
        return data

    def to_matrix(self, data: bytes) -> np.ndarray:
        """원시 데이터를 압력 행렬로 변환"""
        if len(data) < self.MATRIX_ROWS * self.MATRIX_COLS * 2:
            raise ValueError(f"Insufficient data: expected {self.MATRIX_ROWS * self.MATRIX_COLS * 2} bytes")

        values = np.frombuffer(data, dtype=np.uint16)
        matrix = values.reshape((self.MATRIX_ROWS, self.MATRIX_COLS))
        return matrix.astype(np.float32)
