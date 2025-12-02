from abc import ABC, abstractmethod
from typing import Optional, Callable, Awaitable
import numpy as np

from domain.models import (
    Patient,
    DeviceData,
    DayLog,
    PressureLog,
    ControlPacket,
    AlertMessage,
)


class ISerialReader(ABC):
    """시리얼 통신 인터페이스 (b)"""

    @abstractmethod
    def connect(self) -> None:
        """시리얼 포트 연결"""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """시리얼 포트 연결 해제"""
        pass

    @abstractmethod
    def read(self) -> tuple[np.ndarray, np.ndarray]:
        """시리얼에서 데이터 읽기 (블로킹)

        Returns:
            tuple: (head (2, 3), body (12, 7))
        """
        pass


class IServerClient(ABC):
    """서버 통신 인터페이스 (Supabase)"""

    # Device 관련
    @abstractmethod
    async def async_fetch_device(self, device_id: int) -> Optional[DeviceData]:
        """디바이스 조회"""
        pass

    @abstractmethod
    async def async_create_device(self, device: DeviceData) -> Optional[DeviceData]:
        """디바이스 등록"""
        pass

    # Patient 관련
    @abstractmethod
    async def async_fetch_patient_with_device(self, device_id: int) -> Optional[Patient]:
        """device_id로 환자 조회 (a)(d)"""
        pass

    # DayLog 관련
    @abstractmethod
    async def async_create_daylog(self, daylog: DayLog) -> DayLog:
        """일별 로그 생성"""
        pass

    @abstractmethod
    async def async_update_daylog(self, daylog: DayLog) -> Optional[DayLog]:
        """일별 로그 업데이트"""
        pass

    @abstractmethod
    async def async_fetch_daylog_by_date(
        self, device_id: int, day: str
    ) -> Optional[DayLog]:
        """특정 날짜의 DayLog 조회"""
        pass

    # PressureLog 관련
    @abstractmethod
    async def async_create_pressurelog(
        self, pressurelog: PressureLog
    ) -> Optional[PressureLog]:
        """압력 로그 생성 (a)"""
        pass

    @abstractmethod
    async def async_update_pressurelog(
        self, pressurelog: PressureLog
    ) -> Optional[PressureLog]:
        """압력 로그 업데이트"""
        pass

    # Heatmap 실시간 업데이트
    @abstractmethod
    async def async_update_heatmap(self, device_id: int, heatmap: np.ndarray) -> bool:
        """히트맵 실시간 업데이트"""
        pass

    # Controls 조회
    @abstractmethod
    async def async_fetch_device_controls(self, device_id: int) -> Optional[dict]:
        """디바이스 controls 컬럼 조회"""
        pass

    # Controls 실시간 브로드캐스팅
    @abstractmethod
    async def async_broadcast_controls(self, device_id: int, controls_data: dict) -> bool:
        """컨트롤 노드로부터 받은 센서 데이터를 실시간 브로드캐스팅"""
        pass


class IControlNodeSender(ABC):
    """컨트롤 노드 통신 인터페이스 (c)"""

    @abstractmethod
    async def connect(self) -> None:
        """컨트롤 노드 연결"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """연결 해제"""
        pass

    @abstractmethod
    async def send_packet(self, packet: ControlPacket) -> bool:
        """통합 패킷 전송 (자세, 압력, 지속시간, controls 포함)"""
        pass

    @abstractmethod
    def set_sensor_callback(self, callback: Callable[[dict], Awaitable[None]]) -> None:
        """센서 데이터 수신 콜백 설정

        Args:
            callback: 센서 데이터(inflated_zones, timestamp) 수신 시 호출될 콜백
        """
        pass

    @abstractmethod
    async def start_listening(self) -> None:
        """컨트롤 노드로부터 센서 데이터 수신 시작"""
        pass

    @abstractmethod
    async def stop_listening(self) -> None:
        """센서 데이터 수신 중지"""
        pass


class INotifier(ABC):
    """알림 전송 인터페이스 (e)"""

    @abstractmethod
    async def send_notification(self, message: AlertMessage) -> bool:
        """푸시 알림 전송"""
        pass
