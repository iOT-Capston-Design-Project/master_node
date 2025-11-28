import numpy as np

from interfaces.service import IPostureDetector
from domain.enums import PostureType


class PostureDetector(IPostureDetector):
    """자세 추론 구현체 (f)"""

    def __init__(self):
        # 각 자세별 압력 분포 패턴 가중치 영역 정의
        # 16x16 행렬 기준
        self._patterns = {
            PostureType.SUPINE: self._create_supine_pattern(),
            PostureType.PRONE: self._create_prone_pattern(),
            PostureType.LEFT_SIDE: self._create_left_side_pattern(),
            PostureType.RIGHT_SIDE: self._create_right_side_pattern(),
            PostureType.SITTING: self._create_sitting_pattern(),
        }

    def _create_supine_pattern(self) -> np.ndarray:
        """앙와위(등) 자세 패턴 - 후두부, 견갑골, 엉덩이, 발뒤꿈치 압력"""
        pattern = np.zeros((16, 16), dtype=np.float32)
        # 후두부 영역 (상단 중앙)
        pattern[0:2, 6:10] = 1.0
        # 견갑골 영역
        pattern[2:5, 3:13] = 0.8
        # 등/허리 영역 (중앙)
        pattern[5:9, 4:12] = 0.4
        # 엉덩이 영역
        pattern[9:13, 4:12] = 1.0
        # 발뒤꿈치 영역
        pattern[14:16, 4:7] = 0.7
        pattern[14:16, 9:12] = 0.7
        return pattern

    def _create_prone_pattern(self) -> np.ndarray:
        """복와위(배) 자세 패턴"""
        pattern = np.zeros((16, 16), dtype=np.float32)
        # 얼굴/가슴 영역
        pattern[0:4, 5:11] = 0.9
        # 배 영역
        pattern[5:10, 4:12] = 1.0
        # 무릎 영역
        pattern[12:14, 4:7] = 0.6
        pattern[12:14, 9:12] = 0.6
        return pattern

    def _create_left_side_pattern(self) -> np.ndarray:
        """좌측위 자세 패턴 - 왼쪽에 압력 집중"""
        pattern = np.zeros((16, 16), dtype=np.float32)
        # 왼쪽 어깨
        pattern[2:5, 2:6] = 1.0
        # 왼쪽 팔꿈치
        pattern[5:7, 1:4] = 0.8
        # 왼쪽 엉덩이
        pattern[9:13, 2:6] = 1.0
        # 왼쪽 무릎/발
        pattern[13:16, 2:5] = 0.7
        return pattern

    def _create_right_side_pattern(self) -> np.ndarray:
        """우측위 자세 패턴 - 오른쪽에 압력 집중"""
        pattern = np.zeros((16, 16), dtype=np.float32)
        # 오른쪽 어깨
        pattern[2:5, 10:14] = 1.0
        # 오른쪽 팔꿈치
        pattern[5:7, 12:15] = 0.8
        # 오른쪽 엉덩이
        pattern[9:13, 10:14] = 1.0
        # 오른쪽 무릎/발
        pattern[13:16, 11:14] = 0.7
        return pattern

    def _create_sitting_pattern(self) -> np.ndarray:
        """앉은 자세 패턴 - 엉덩이에 압력 집중"""
        pattern = np.zeros((16, 16), dtype=np.float32)
        # 엉덩이 영역에 집중
        pattern[8:14, 3:13] = 1.0
        return pattern

    def detect(self, pressure_matrix: np.ndarray) -> PostureType:
        """압력 행렬로부터 자세 추론"""
        if pressure_matrix.shape != (16, 16):
            raise ValueError(f"Expected 16x16 matrix, got {pressure_matrix.shape}")

        # 정규화
        normalized = self._normalize(pressure_matrix)

        # 각 패턴과의 유사도 계산
        scores = {}
        for posture_type, pattern in self._patterns.items():
            score = self._calculate_similarity(normalized, pattern)
            scores[posture_type] = score

        # 최고 점수 자세 선택
        best_posture = max(scores, key=scores.get)
        confidence = scores[best_posture]

        # 신뢰도가 너무 낮으면 UNKNOWN
        if confidence < 0.3:
            return PostureType.UNKNOWN

        return best_posture

    def _normalize(self, matrix: np.ndarray) -> np.ndarray:
        """행렬 정규화 (0~1 범위)"""
        min_val = matrix.min()
        max_val = matrix.max()
        if max_val - min_val == 0:
            return np.zeros_like(matrix)
        return (matrix - min_val) / (max_val - min_val)

    def _calculate_similarity(
        self, matrix: np.ndarray, pattern: np.ndarray
    ) -> float:
        """패턴 유사도 계산 (코사인 유사도)"""
        flat_matrix = matrix.flatten()
        flat_pattern = pattern.flatten()

        dot_product = np.dot(flat_matrix, flat_pattern)
        norm_matrix = np.linalg.norm(flat_matrix)
        norm_pattern = np.linalg.norm(flat_pattern)

        if norm_matrix == 0 or norm_pattern == 0:
            return 0.0

        return float(dot_product / (norm_matrix * norm_pattern))
