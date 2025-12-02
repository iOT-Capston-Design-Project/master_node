from interfaces.service import IPressureAnalyzer
from domain.enums import PostureType, BodyPart


class PressureAnalyzer(IPressureAnalyzer):
    """압력 분석 구현체 (g) - 자세별 압력 받는 부위 반환"""

    # 자세별로 압력이 예상되는 신체 부위
    POSTURE_BODY_PARTS: dict[PostureType, list[BodyPart]] = {
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
        PostureType.UNKNOWN: [],  # 미확인 시 사용자 없음 - 압력 부위 없음
    }

    def analyze(self, posture: PostureType) -> list[BodyPart]:
        """자세를 기반으로 압력 받는 부위 목록 반환"""
        return self.POSTURE_BODY_PARTS.get(posture, [])
