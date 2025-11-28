import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    """애플리케이션 설정"""

    # 디바이스 ID (서버에서 환자 매칭에 사용)
    device_id: int = field(
        default_factory=lambda: int(os.getenv("DEVICE_ID", "0"))
    )

    # 시리얼 통신 설정
    serial_port: str = field(
        default_factory=lambda: os.getenv("SERIAL_PORT", "/dev/ttyUSB0")
    )
    baudrate: int = field(
        default_factory=lambda: int(os.getenv("SERIAL_BAUDRATE", "115200"))
    )

    # Supabase 설정
    supabase_url: str = field(default_factory=lambda: os.getenv("SUPABASE_URL", ""))
    supabase_key: str = field(default_factory=lambda: os.getenv("SUPABASE_KEY", ""))

    # 컨트롤 노드 설정
    control_node_address: str = field(
        default_factory=lambda: os.getenv("CONTROL_NODE_ADDRESS", "10.0.0.2")
    )
    control_node_port: int = field(
        default_factory=lambda: int(os.getenv("CONTROL_NODE_PORT", "24"))
    )

    # FCM 설정
    fcm_credentials: str = field(
        default_factory=lambda: os.getenv("FCM_CREDENTIALS_PATH", "firebase-credentials.json")
    )

    # 사이클 간격 (초)
    cycle_interval: float = field(
        default_factory=lambda: float(os.getenv("CYCLE_INTERVAL", "1.0"))
    )

    @classmethod
    def from_env(cls) -> "Settings":
        """환경 변수로부터 설정 로드"""
        return cls()

    def validate(self) -> None:
        """설정 유효성 검사"""
        if self.device_id == 0:
            raise ValueError("DEVICE_ID is required")
        if not self.supabase_url:
            raise ValueError("SUPABASE_URL is required")
        if not self.supabase_key:
            raise ValueError("SUPABASE_KEY is required")
