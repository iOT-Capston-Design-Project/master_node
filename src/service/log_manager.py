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

    def record(self, active_parts: list[BodyPart], posture: PostureType) -> bool:
        """압력 지속 시간 기록

        Returns:
            bool: 자세가 변경되었으면 True
        """
        posture_changed = False

        # 자세가 변경되었는지 확인
        if self._last_posture != posture:
            self._last_posture = posture
            posture_changed = True

        # 압력 받는 부위는 지속 시간 증가, 없는 부위는 초기화
        for body_part in BodyPart:
            if body_part in active_parts:
                self._durations[body_part] += self._cycle_interval_seconds
            else:
                self._durations[body_part] = 0

        # DayLog 누적값 업데이트
        self._update_daylog_totals()

        return posture_changed

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
        posture: PostureType,
        posture_change_required: bool,
    ) -> PressureLog:
        """PressureLog 생성 - 부위별 누적 시간(초) 포함"""
        return PressureLog(
            id=0,  # 서버에서 생성
            day_id=day_id,
            created_at=datetime.now(),
            occiput=self._durations[BodyPart.OCCIPUT],
            scapula=self._durations[BodyPart.SCAPULA],
            right_elbow=self._durations[BodyPart.RIGHT_ELBOW],
            left_elbow=self._durations[BodyPart.LEFT_ELBOW],
            hip=self._durations[BodyPart.HIP],
            right_heel=self._durations[BodyPart.RIGHT_HEEL],
            left_heel=self._durations[BodyPart.LEFT_HEEL],
            posture=posture,
            posture_change_required=posture_change_required,
        )

    def update_pressure_log(
        self,
        pressure_log: PressureLog,
        posture_change_required: bool,
    ) -> PressureLog:
        """기존 PressureLog의 누적 시간 업데이트"""
        pressure_log.occiput = self._durations[BodyPart.OCCIPUT]
        pressure_log.scapula = self._durations[BodyPart.SCAPULA]
        pressure_log.right_elbow = self._durations[BodyPart.RIGHT_ELBOW]
        pressure_log.left_elbow = self._durations[BodyPart.LEFT_ELBOW]
        pressure_log.hip = self._durations[BodyPart.HIP]
        pressure_log.right_heel = self._durations[BodyPart.RIGHT_HEEL]
        pressure_log.left_heel = self._durations[BodyPart.LEFT_HEEL]
        pressure_log.posture_change_required = posture_change_required
        return pressure_log

    def reset_durations(self) -> None:
        """지속 시간 초기화"""
        self._durations = {part: 0 for part in BodyPart}
