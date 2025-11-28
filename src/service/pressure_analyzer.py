import numpy as np

from interfaces.service import IPressureAnalyzer
from domain.enums import PostureType, BodyPart


class PressureAnalyzer(IPressureAnalyzer):
    """압력 분석 구현체 (g)"""

    # 16x16 행렬에서 각 신체 부위의 영역 정의 (row_start, row_end, col_start, col_end)
    BODY_REGIONS = {
        BodyPart.OCCIPUT: (0, 2, 6, 10),           # 후두부
        BodyPart.SCAPULA: (2, 5, 3, 13),           # 견갑골
        BodyPart.RIGHT_ELBOW: (5, 8, 10, 14),      # 오른쪽 팔꿈치
        BodyPart.LEFT_ELBOW: (5, 8, 2, 6),         # 왼쪽 팔꿈치
        BodyPart.HIP: (9, 13, 4, 12),              # 엉덩이
        BodyPart.RIGHT_HEEL: (14, 16, 9, 12),      # 오른쪽 발뒤꿈치
        BodyPart.LEFT_HEEL: (14, 16, 4, 7),        # 왼쪽 발뒤꿈치
    }

    # 자세별로 압력이 예상되는 신체 부위
    POSTURE_BODY_PARTS = {
        PostureType.SUPINE: [
            BodyPart.OCCIPUT,
            BodyPart.SCAPULA,
            BodyPart.HIP,
            BodyPart.RIGHT_HEEL,
            BodyPart.LEFT_HEEL,
        ],
        PostureType.SUPINE_LEFT: [
            BodyPart.OCCIPUT,
            BodyPart.SCAPULA,
            BodyPart.HIP,
            BodyPart.RIGHT_HEEL,
        ],
        PostureType.SUPINE_RIGHT: [
            BodyPart.OCCIPUT,
            BodyPart.SCAPULA,
            BodyPart.HIP,
            BodyPart.LEFT_HEEL,
        ],
        PostureType.PRONE: [
            BodyPart.SCAPULA,
            BodyPart.HIP,
        ],
        PostureType.LEFT_SIDE: [
            BodyPart.SCAPULA,
            BodyPart.LEFT_ELBOW,
            BodyPart.HIP,
            BodyPart.LEFT_HEEL,
        ],
        PostureType.RIGHT_SIDE: [
            BodyPart.SCAPULA,
            BodyPart.RIGHT_ELBOW,
            BodyPart.HIP,
            BodyPart.RIGHT_HEEL,
        ],
        PostureType.SITTING: [
            BodyPart.HIP,
        ],
        PostureType.UNKNOWN: list(BodyPart),
    }

    def analyze(self, posture: PostureType, matrix: np.ndarray) -> dict[BodyPart, int]:
        """자세를 기반으로 압력 부위별 값 분석"""
        relevant_parts = self.POSTURE_BODY_PARTS.get(posture, list(BodyPart))
        pressures: dict[BodyPart, int] = {}

        for body_part in BodyPart:
            region = self.BODY_REGIONS.get(body_part)
            if region is None:
                pressures[body_part] = 0
                continue

            r_start, r_end, c_start, c_end = region
            region_matrix = matrix[r_start:r_end, c_start:c_end]

            # 해당 자세에서 예상되는 부위만 측정
            if body_part in relevant_parts:
                avg_pressure = int(np.mean(region_matrix))
            else:
                avg_pressure = 0

            pressures[body_part] = avg_pressure

        return pressures
