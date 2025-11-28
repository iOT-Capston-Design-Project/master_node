from typing import Optional

from interfaces.service import IAlertChecker
from domain.models import Patient, AlertMessage
from domain.enums import BodyPart


class AlertChecker(IAlertChecker):
    """알림 체크 구현체"""

    # 신체 부위 한글명
    BODY_PART_NAMES = {
        BodyPart.OCCIPUT: "후두부",
        BodyPart.SCAPULA: "견갑골",
        BodyPart.RIGHT_ELBOW: "오른쪽 팔꿈치",
        BodyPart.LEFT_ELBOW: "왼쪽 팔꿈치",
        BodyPart.HIP: "엉덩이",
        BodyPart.RIGHT_HEEL: "오른쪽 발뒤꿈치",
        BodyPart.LEFT_HEEL: "왼쪽 발뒤꿈치",
    }

    def check(
        self,
        patient: Patient,
        durations: dict[BodyPart, int],
    ) -> Optional[AlertMessage]:
        """임계값 초과 시 알림 메시지 반환"""
        alert_parts = []

        for body_part, duration_seconds in durations.items():
            # 환자별 임계값 (분 단위) -> 초 단위로 변환
            threshold_seconds = patient.get_threshold(body_part) * 60

            if duration_seconds >= threshold_seconds:
                part_name = self.BODY_PART_NAMES.get(body_part, body_part.value)
                duration_minutes = duration_seconds // 60
                alert_parts.append(f"{part_name} ({duration_minutes}분)")

        if not alert_parts:
            return None

        return AlertMessage(
            device_id=patient.device_id,
            title="욕창 위험 알림",
            body=f"다음 부위에서 압력 임계값 초과: {', '.join(alert_parts)}",
            priority="high",
        )

    def check_posture_change_required(
        self,
        patient: Patient,
        durations: dict[BodyPart, int],
    ) -> bool:
        """자세 변경 필요 여부 확인"""
        for body_part, duration_seconds in durations.items():
            # 환자별 임계값 (분 단위) -> 초 단위로 변환
            threshold_seconds = patient.get_threshold(body_part) * 60

            if duration_seconds >= threshold_seconds:
                return True

        return False
