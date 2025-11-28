from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime, date

from .enums import PostureType, BodyPart


@dataclass
class Patient:
    """환자 정보 (서버에서 device_id로 조회)"""
    id: int
    device_id: int
    created_at: datetime
    # 부위별 임계값 (분 단위)
    occiput_threshold: int
    scapula_threshold: int
    right_elbow_threshold: int
    left_elbow_threshold: int
    hip_threshold: int
    right_heel_threshold: int
    left_heel_threshold: int

    @staticmethod
    def from_dict(data: dict) -> "Patient":
        """서버 응답을 Patient 객체로 변환"""
        created_at = datetime.fromisoformat(data["created_at"])
        return Patient(
            id=int(data["id"]),
            device_id=int(data.get("device_id") or 0),
            created_at=created_at,
            occiput_threshold=int(data.get("occiput_threshold") or 120),
            scapula_threshold=int(data.get("scapula_threshold") or 120),
            right_elbow_threshold=int(data.get("relbow_threshold") or 120),
            left_elbow_threshold=int(data.get("lelbow_threshold") or 120),
            hip_threshold=int(data.get("hip_threshold") or 120),
            right_heel_threshold=int(data.get("rheel_threshold") or 120),
            left_heel_threshold=int(data.get("lheel_threshold") or 120),
        )

    def get_threshold(self, body_part: BodyPart) -> int:
        """부위별 임계값 반환 (분 단위)"""
        thresholds = {
            BodyPart.OCCIPUT: self.occiput_threshold,
            BodyPart.SCAPULA: self.scapula_threshold,
            BodyPart.RIGHT_ELBOW: self.right_elbow_threshold,
            BodyPart.LEFT_ELBOW: self.left_elbow_threshold,
            BodyPart.HIP: self.hip_threshold,
            BodyPart.RIGHT_HEEL: self.right_heel_threshold,
            BodyPart.LEFT_HEEL: self.left_heel_threshold,
        }
        return thresholds.get(body_part, 120)


@dataclass
class DeviceData:
    """디바이스 정보"""
    id: int
    created_at: datetime

    @staticmethod
    def from_dict(data: dict) -> "DeviceData":
        created_at = datetime.fromisoformat(data["created_at"])
        return DeviceData(id=int(data["id"]), created_at=created_at)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class DayLog:
    """일별 압력 누적 로그"""
    id: int
    day: date
    device_id: int
    total_occiput: int
    total_scapula: int
    total_right_elbow: int
    total_left_elbow: int
    total_hip: int
    total_right_heel: int
    total_left_heel: int

    @staticmethod
    def from_dict(data: dict) -> "DayLog":
        day = date.fromisoformat(data["day"])
        return DayLog(
            id=int(data["id"]),
            day=day,
            device_id=int(data["device_id"]),
            total_occiput=int(data["total_occiput"]),
            total_scapula=int(data["total_scapula"]),
            total_right_elbow=int(data["total_relbow"]),
            total_left_elbow=int(data["total_lelbow"]),
            total_hip=int(data["total_hip"]),
            total_right_heel=int(data["total_rheel"]),
            total_left_heel=int(data["total_lheel"]),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "day": self.day.isoformat(),
            "device_id": self.device_id,
            "total_occiput": self.total_occiput,
            "total_scapula": self.total_scapula,
            "total_relbow": self.total_right_elbow,
            "total_lelbow": self.total_left_elbow,
            "total_hip": self.total_hip,
            "total_rheel": self.total_right_heel,
            "total_lheel": self.total_left_heel,
        }

    @staticmethod
    def create_empty(device_id: int, day: date) -> "DayLog":
        """빈 DayLog 생성"""
        return DayLog(
            id=0,
            day=day,
            device_id=device_id,
            total_occiput=0,
            total_scapula=0,
            total_right_elbow=0,
            total_left_elbow=0,
            total_hip=0,
            total_right_heel=0,
            total_left_heel=0,
        )


@dataclass
class PressureLog:
    """개별 압력 측정 로그"""
    id: int
    day_id: int
    created_at: datetime
    occiput: int
    scapula: int
    right_elbow: int
    left_elbow: int
    hip: int
    right_heel: int
    left_heel: int
    posture: PostureType = PostureType.UNKNOWN
    posture_change_required: bool = False

    @staticmethod
    def from_dict(data: dict) -> "PressureLog":
        created_at = datetime.fromisoformat(data["created_at"])
        return PressureLog(
            id=int(data["id"]),
            day_id=int(data["day_id"]),
            created_at=created_at,
            occiput=int(data["occiput"]),
            scapula=int(data["scapula"]),
            right_elbow=int(data["relbow"]),
            left_elbow=int(data["lelbow"]),
            hip=int(data["hip"]),
            right_heel=int(data["rheel"]),
            left_heel=int(data["lheel"]),
            posture=PostureType(data["posture_type"]),
            posture_change_required=data["posture_change_required"],
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "day_id": self.day_id,
            "created_at": self.created_at.isoformat(),
            "occiput": self.occiput,
            "scapula": self.scapula,
            "relbow": self.right_elbow,
            "lelbow": self.left_elbow,
            "hip": self.hip,
            "rheel": self.right_heel,
            "lheel": self.left_heel,
            "posture_type": self.posture.value,
            "posture_change_required": self.posture_change_required,
        }

    def get_pressure(self, body_part: BodyPart) -> int:
        """부위별 압력값 반환"""
        pressures = {
            BodyPart.OCCIPUT: self.occiput,
            BodyPart.SCAPULA: self.scapula,
            BodyPart.RIGHT_ELBOW: self.right_elbow,
            BodyPart.LEFT_ELBOW: self.left_elbow,
            BodyPart.HIP: self.hip,
            BodyPart.RIGHT_HEEL: self.right_heel,
            BodyPart.LEFT_HEEL: self.left_heel,
        }
        return pressures.get(body_part, 0)


@dataclass
class ControlSignal:
    """컨트롤 노드 제어 신호"""
    target_zones: List[int]  # 제어할 영역 번호
    action: str              # "inflate" | "deflate" | "none"
    intensity: int           # 0-100


@dataclass
class AlertMessage:
    """푸시 알림 메시지"""
    device_id: int
    title: str
    body: str
    priority: str = "normal"


@dataclass
class CycleResult:
    """한 사이클 처리 결과"""
    posture: PostureType
    pressure_log: PressureLog
    control_signal: ControlSignal
    alert_sent: bool
    posture_change_required: bool
    durations: dict  # 부위별 압력 지속 시간 (초)
    timestamp: datetime = field(default_factory=datetime.now)
