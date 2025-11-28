import numpy as np

from interfaces.service import IPostureDetector
from domain.models import PostureDetectionResult
from service.detection import PostureDetectionModel


class PostureDetector(IPostureDetector):
    """자세 추론 구현체 (f) - ML 모델 사용"""

    def __init__(self):
        self._model = PostureDetectionModel()

    def detect(self, pressure_matrix: np.ndarray) -> PostureDetectionResult:
        """압력 행렬로부터 자세 추론

        Args:
            pressure_matrix: (16, 7) 형태의 압력 데이터

        Returns:
            PostureDetectionResult: 자세 유형 및 신체 부위별 압력 여부
        """
        return self._model.detect(pressure_matrix)
