from typing import Optional, List
from datetime import datetime

import numpy as np

from interfaces.communication import IServerClient
from domain.models import Patient, DeviceData, DayLog, PressureLog


class MockSupabaseClient(IServerClient):
    """테스트용 Mock Supabase 클라이언트"""

    def __init__(self):
        self._devices: dict[int, DeviceData] = {}
        self._patients: dict[int, Patient] = {}  # key: device_id
        self._daylogs: List[DayLog] = []
        self._pressurelogs: List[PressureLog] = []

    async def initialize(self) -> None:
        """초기화 (Mock은 아무것도 안함)"""
        pass

    # Device 관련
    async def async_fetch_device(self, device_id: int) -> Optional[DeviceData]:
        return self._devices.get(device_id)

    async def async_create_device(self, device: DeviceData) -> Optional[DeviceData]:
        self._devices[device.id] = device
        return device

    # Patient 관련
    async def async_fetch_patient_with_device(self, device_id: int) -> Optional[Patient]:
        return self._patients.get(device_id)

    def set_patient(self, patient: Patient) -> None:
        """테스트용 환자 설정"""
        self._patients[patient.device_id] = patient

    # DayLog 관련
    async def async_create_daylog(self, daylog: DayLog) -> DayLog:
        daylog_with_id = DayLog(
            id=len(self._daylogs) + 1,
            day=daylog.day,
            device_id=daylog.device_id,
            total_occiput=daylog.total_occiput,
            total_scapula=daylog.total_scapula,
            total_right_elbow=daylog.total_right_elbow,
            total_left_elbow=daylog.total_left_elbow,
            total_hip=daylog.total_hip,
            total_right_heel=daylog.total_right_heel,
            total_left_heel=daylog.total_left_heel,
        )
        self._daylogs.append(daylog_with_id)
        return daylog_with_id

    async def async_update_daylog(self, daylog: DayLog) -> Optional[DayLog]:
        for i, dl in enumerate(self._daylogs):
            if dl.id == daylog.id:
                self._daylogs[i] = daylog
                return daylog
        return None

    async def async_fetch_daylog_by_date(
        self, device_id: int, day: str
    ) -> Optional[DayLog]:
        for dl in self._daylogs:
            if dl.device_id == device_id and dl.day.isoformat() == day:
                return dl
        return None

    # PressureLog 관련
    async def async_create_pressurelog(
        self, pressurelog: PressureLog
    ) -> Optional[PressureLog]:
        log_with_id = PressureLog(
            id=len(self._pressurelogs) + 1,
            day_id=pressurelog.day_id,
            created_at=pressurelog.created_at,
            occiput=pressurelog.occiput,
            scapula=pressurelog.scapula,
            right_elbow=pressurelog.right_elbow,
            left_elbow=pressurelog.left_elbow,
            hip=pressurelog.hip,
            right_heel=pressurelog.right_heel,
            left_heel=pressurelog.left_heel,
            posture=pressurelog.posture,
            posture_change_required=pressurelog.posture_change_required,
        )
        self._pressurelogs.append(log_with_id)
        return log_with_id

    async def async_update_pressurelog(
        self, pressurelog: PressureLog
    ) -> Optional[PressureLog]:
        for i, pl in enumerate(self._pressurelogs):
            if pl.id == pressurelog.id:
                self._pressurelogs[i] = pressurelog
                return pressurelog
        return None

    # Heatmap
    async def async_update_heatmap(self, device_id: int, heatmap: np.ndarray) -> bool:
        return True

    # 테스트 헬퍼 메서드
    def get_pressurelogs(self) -> List[PressureLog]:
        return self._pressurelogs.copy()

    def get_daylogs(self) -> List[DayLog]:
        return self._daylogs.copy()

    def clear(self) -> None:
        self._devices.clear()
        self._patients.clear()
        self._daylogs.clear()
        self._pressurelogs.clear()
