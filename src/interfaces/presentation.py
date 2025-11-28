from abc import ABC, abstractmethod
from typing import Optional

from domain.models import CycleResult, Patient, ControlSignal


class IDisplay(ABC):
    """화면 출력 인터페이스"""

    @abstractmethod
    def show_cycle_result(self, result: CycleResult) -> None:
        """사이클 처리 결과 표시"""
        pass

    @abstractmethod
    def show_control_signal(self, signal: ControlSignal) -> None:
        """제어 신호 표시"""
        pass

    @abstractmethod
    def show_patient_info(self, patient: Optional[Patient], device_id: int) -> None:
        """환자 정보 표시"""
        pass

    @abstractmethod
    def show_error(self, error: Exception) -> None:
        """에러 표시"""
        pass
