from abc import ABC, abstractmethod
from typing import Optional
import numpy as np

from domain.models import (
    Patient,
    DayLog,
    PressureLog,
    AlertMessage,
    CycleResult,
    PostureDetectionResult,
)
from domain.enums import PostureType, BodyPart


class IPostureDetector(ABC):
    """자세 추론 인터페이스 (f)"""

    @abstractmethod
    def detect(self, pressure_matrix: np.ndarray) -> PostureDetectionResult:
        """압력 행렬로부터 자세 추론"""
        pass


class IPressureAnalyzer(ABC):
    """압력 분석 인터페이스 (g)"""

    @abstractmethod
    def analyze(self, posture: PostureType, matrix: np.ndarray) -> dict[BodyPart, int]:
        """자세를 기반으로 압력 부위별 값 분석"""
        pass


class ILogManager(ABC):
    """로그 관리 인터페이스 (h)"""

    @abstractmethod
    def set_device_id(self, device_id: int) -> None:
        """디바이스 ID 설정"""
        pass

    @abstractmethod
    def record(self, pressures: dict[BodyPart, int], posture: PostureType) -> None:
        """압력 지속 시간 기록"""
        pass

    @abstractmethod
    def get_durations(self) -> dict[BodyPart, int]:
        """부위별 압력 지속 시간 반환 (초)"""
        pass

    @abstractmethod
    def get_current_daylog(self) -> DayLog:
        """현재 DayLog 반환"""
        pass

    @abstractmethod
    def create_pressure_log(
        self,
        day_id: int,
        pressures: dict[BodyPart, int],
        posture: PostureType,
        posture_change_required: bool,
    ) -> PressureLog:
        """PressureLog 생성"""
        pass

    @abstractmethod
    def reset_durations(self) -> None:
        """지속 시간 초기화"""
        pass


class IAlertChecker(ABC):
    """알림 체크 인터페이스"""

    @abstractmethod
    def check(
        self,
        patient: Patient,
        durations: dict[BodyPart, int],
    ) -> Optional[AlertMessage]:
        """임계값 초과 시 알림 메시지 반환"""
        pass

    @abstractmethod
    def check_posture_change_required(
        self,
        patient: Patient,
        durations: dict[BodyPart, int],
    ) -> bool:
        """자세 변경 필요 여부 확인"""
        pass


class IServiceFacade(ABC):
    """서비스 계층 통합 인터페이스 - 표현 계층에서 사용"""

    @abstractmethod
    async def initialize(self) -> None:
        """초기화 - 환자 정보 로드"""
        pass

    @abstractmethod
    async def process_cycle(self) -> CycleResult:
        """한 사이클 처리 후 결과 반환"""
        pass

    @abstractmethod
    def get_patient(self) -> Optional[Patient]:
        """환자 정보 조회"""
        pass

    @abstractmethod
    def get_device_id(self) -> int:
        """디바이스 ID 조회"""
        pass
