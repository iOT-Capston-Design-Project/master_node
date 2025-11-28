from interfaces.service import IControlGenerator
from domain.models import ControlSignal
from domain.enums import BodyPart


class ControlGenerator(IControlGenerator):
    """제어 신호 생성 구현체 (i)"""

    # 신체 부위별 제어 영역 매핑
    BODY_PART_TO_ZONE: dict[BodyPart, int] = {
        BodyPart.OCCIPUT: 1,
        BodyPart.SCAPULA: 2,
        BodyPart.RIGHT_ELBOW: 3,
        BodyPart.LEFT_ELBOW: 4,
        BodyPart.HIP: 5,
        BodyPart.RIGHT_HEEL: 6,
        BodyPart.LEFT_HEEL: 7,
    }

    # 압력 임계값
    PRESSURE_THRESHOLD = 300
    # 지속 시간 임계값 (초) - 5분
    DURATION_THRESHOLD = 300

    def generate(
        self, pressures: dict[BodyPart, int], durations: dict[BodyPart, int]
    ) -> ControlSignal:
        """압력 및 지속시간으로부터 제어 신호 생성"""
        target_zones = []
        max_pressure = 0

        for body_part in BodyPart:
            pressure = pressures.get(body_part, 0)
            duration = durations.get(body_part, 0)

            # 압력이 임계값을 초과하거나 지속 시간이 임계값을 초과한 경우
            if pressure > self.PRESSURE_THRESHOLD or duration > self.DURATION_THRESHOLD:
                zone = self.BODY_PART_TO_ZONE.get(body_part)
                if zone is not None:
                    target_zones.append(zone)
                    max_pressure = max(max_pressure, pressure)

        if not target_zones:
            return ControlSignal(
                target_zones=[],
                action="none",
                intensity=0,
            )

        # 압력 강도에 따른 제어 강도 계산
        intensity = self._calculate_intensity(max_pressure)

        return ControlSignal(
            target_zones=sorted(set(target_zones)),
            action="inflate",  # 해당 영역 공기 주입으로 압력 분산
            intensity=intensity,
        )

    def _calculate_intensity(self, pressure: int) -> int:
        """압력값에 따른 제어 강도 계산 (0-100)"""
        if pressure <= self.PRESSURE_THRESHOLD:
            return 30  # 최소 강도

        # 선형 매핑: THRESHOLD ~ 1000 -> 30 ~ 100
        normalized = (pressure - self.PRESSURE_THRESHOLD) / (
            1000 - self.PRESSURE_THRESHOLD
        )
        intensity = int(30 + normalized * 70)
        return min(100, max(30, intensity))
