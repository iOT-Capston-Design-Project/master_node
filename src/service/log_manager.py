from datetime import datetime, date

from interfaces.service import ILogManager
from domain.models import DayLog, PressureLog
from domain.enums import PostureType, BodyPart


class LogManager(ILogManager):
    """로그 관리 구현체 (h)"""

    def __init__(self, device_id: int = 0):
        self._device_id = device_id
        self._durations: dict[BodyPart, int] = {part: 0 for part in BodyPart}
        self._current_daylog: DayLog | None = None
        self._last_posture: PostureType = PostureType.UNKNOWN
        self._cycle_interval_seconds = 1  # 측정 주기

    def set_device_id(self, device_id: int) -> None:
        """디바이스 ID 설정"""
        self._device_id = device_id
        self._current_daylog = DayLog.create_empty(device_id, date.today())

    def record(self, pressures: dict[BodyPart, int], posture: PostureType) -> None:
        """압력 지속 시간 기록"""
        # 자세가 변경되면 지속 시간 초기화
        if self._last_posture != posture:
            self.reset_durations()
            self._last_posture = posture

        # 압력이 있는 부위의 지속 시간 증가
        for body_part, pressure in pressures.items():
            if pressure > 0:
                self._durations[body_part] += self._cycle_interval_seconds
            else:
                self._durations[body_part] = 0

        # DayLog 누적값 업데이트
        self._update_daylog_totals()

    def _update_daylog_totals(self) -> None:
        """DayLog 누적값 업데이트"""
        if self._current_daylog is None:
            self._current_daylog = DayLog.create_empty(self._device_id, date.today())

        # 오늘 날짜가 아니면 새로 생성
        if self._current_daylog.day != date.today():
            self._current_daylog = DayLog.create_empty(self._device_id, date.today())

        # 누적 시간 업데이트
        self._current_daylog.total_occiput = self._durations[BodyPart.OCCIPUT]
        self._current_daylog.total_scapula = self._durations[BodyPart.SCAPULA]
        self._current_daylog.total_right_elbow = self._durations[BodyPart.RIGHT_ELBOW]
        self._current_daylog.total_left_elbow = self._durations[BodyPart.LEFT_ELBOW]
        self._current_daylog.total_hip = self._durations[BodyPart.HIP]
        self._current_daylog.total_right_heel = self._durations[BodyPart.RIGHT_HEEL]
        self._current_daylog.total_left_heel = self._durations[BodyPart.LEFT_HEEL]

    def get_durations(self) -> dict[BodyPart, int]:
        """부위별 압력 지속 시간 반환 (초)"""
        return self._durations.copy()

    def get_current_daylog(self) -> DayLog:
        """현재 DayLog 반환"""
        if self._current_daylog is None:
            self._current_daylog = DayLog.create_empty(self._device_id, date.today())
        return self._current_daylog

    def set_daylog(self, daylog: DayLog) -> None:
        """DayLog 설정 (서버에서 로드한 경우)"""
        self._current_daylog = daylog
        # 누적 시간을 현재 durations로 복원
        self._durations[BodyPart.OCCIPUT] = daylog.total_occiput
        self._durations[BodyPart.SCAPULA] = daylog.total_scapula
        self._durations[BodyPart.RIGHT_ELBOW] = daylog.total_right_elbow
        self._durations[BodyPart.LEFT_ELBOW] = daylog.total_left_elbow
        self._durations[BodyPart.HIP] = daylog.total_hip
        self._durations[BodyPart.RIGHT_HEEL] = daylog.total_right_heel
        self._durations[BodyPart.LEFT_HEEL] = daylog.total_left_heel

    def create_pressure_log(
        self,
        day_id: int,
        pressures: dict[BodyPart, int],
        posture: PostureType,
        posture_change_required: bool,
    ) -> PressureLog:
        """PressureLog 생성"""
        return PressureLog(
            id=0,  # 서버에서 생성
            day_id=day_id,
            created_at=datetime.now(),
            occiput=pressures.get(BodyPart.OCCIPUT, 0),
            scapula=pressures.get(BodyPart.SCAPULA, 0),
            right_elbow=pressures.get(BodyPart.RIGHT_ELBOW, 0),
            left_elbow=pressures.get(BodyPart.LEFT_ELBOW, 0),
            hip=pressures.get(BodyPart.HIP, 0),
            right_heel=pressures.get(BodyPart.RIGHT_HEEL, 0),
            left_heel=pressures.get(BodyPart.LEFT_HEEL, 0),
            posture=posture,
            posture_change_required=posture_change_required,
        )

    def reset_durations(self) -> None:
        """지속 시간 초기화"""
        self._durations = {part: 0 for part in BodyPart}
