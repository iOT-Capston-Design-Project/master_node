# 소프트웨어 아키텍처 설계서

## 1. 개요

라즈베리파이 마스터 노드 소프트웨어의 계층형 아키텍처 설계서입니다.
각 계층은 인터페이스를 통해 추상화되어 있어 구현체 변경 시 다른 계층에 영향을 주지 않습니다.

---

## 2. 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────┐
│                    표현 계층 (Layer 3)                    │
│                      Display                             │
└─────────────────────────┬───────────────────────────────┘
                          │ IServiceFacade (인터페이스)
┌─────────────────────────▼───────────────────────────────┐
│                    서비스 계층 (Layer 2)                   │
│   PostureDetector, PressureAnalyzer, ControlService      │
└─────────────────────────┬───────────────────────────────┘
                          │ ICommunication* (인터페이스들)
┌─────────────────────────▼───────────────────────────────┐
│                    통신 계층 (Layer 1)                    │
│   SupabaseClient, SerialHandler, ControlSender, FCM      │
└─────────────────────────────────────────────────────────┘
```

**설계 원칙**: 상위 계층은 하위 계층의 **인터페이스**에만 의존하고, 구현체에는 의존하지 않음

---

## 3. 디렉토리 구조

```
master/
├── src/
│   ├── main.py
│   ├── container.py              # 의존성 주입 컨테이너
│   ├── config/
│   │   └── settings.py
│   │
│   ├── domain/                   # 도메인 모델 (공유)
│   │   ├── __init__.py
│   │   ├── models.py             # Posture, PressurePoint, ControlSignal 등
│   │   └── enums.py              # 상태값, 타입 정의
│   │
│   ├── interfaces/               # 계층 간 인터페이스 정의
│   │   ├── __init__.py
│   │   ├── communication.py      # 통신 계층 인터페이스
│   │   ├── service.py            # 서비스 계층 인터페이스
│   │   └── presentation.py       # 표현 계층 인터페이스
│   │
│   ├── communication/            # 통신 계층 구현
│   │   ├── __init__.py
│   │   ├── supabase_client.py
│   │   ├── serial_handler.py
│   │   ├── control_sender.py
│   │   └── fcm_notifier.py
│   │
│   ├── service/                  # 서비스 계층 구현
│   │   ├── __init__.py
│   │   ├── posture_detector.py
│   │   ├── pressure_analyzer.py
│   │   ├── log_manager.py
│   │   ├── control_service.py
│   │   ├── alert_service.py
│   │   └── service_facade.py     # 서비스 계층 통합 Facade
│   │
│   └── presentation/             # 표현 계층 구현
│       ├── __init__.py
│       └── console_display.py
│
├── tests/
│   ├── mocks/                    # 테스트용 Mock 구현체
│   │   ├── mock_serial.py
│   │   └── mock_supabase.py
│   └── ...
│
├── docs/
│   └── ARCHITECTURE.md
├── requirements.txt
└── README.md
```

---

## 4. 계층별 모듈 매핑

### 4.1 통신 계층 (Layer 1)

| 모듈 | README 기능 | 인터페이스 | 주요 메서드 |
|------|-------------|-----------|-------------|
| `supabase_client.py` | (a) 압력 로그 전송, (d) 환자 설정 조회 | `IServerClient` | `upload_pressure_log()`, `fetch_patient_settings()` |
| `serial_handler.py` | (b) 시리얼 데이터 → 행렬 변환 | `ISerialReader` | `read_raw()`, `to_matrix()` |
| `control_sender.py` | (c) 컨트롤 노드 통신 | `IControlNodeSender` | `send_signal()` |
| `fcm_notifier.py` | (e) 푸시 알림 전송 | `INotifier` | `send_notification()` |

### 4.2 서비스 계층 (Layer 2)

| 모듈 | README 기능 | 인터페이스 | 주요 메서드 |
|------|-------------|-----------|-------------|
| `posture_detector.py` | (f) 자세 추론 | `IPostureDetector` | `detect()` |
| `pressure_analyzer.py` | (g) 압력 부위 판단 | `IPressureAnalyzer` | `analyze()` |
| `log_manager.py` | (h) 로그 관리/캐시 | `ILogManager` | `record()`, `get_current_log()` |
| `control_service.py` | (i) 제어 신호 생성 | `IControlGenerator` | `generate()` |
| `alert_service.py` | 알림 임계값 체크 | `IAlertChecker` | `check()` |
| `service_facade.py` | 서비스 통합 | `IServiceFacade` | `process_cycle()` |

### 4.3 표현 계층 (Layer 3)

| 모듈 | README 기능 | 인터페이스 | 주요 메서드 |
|------|-------------|-----------|-------------|
| `console_display.py` | 표/제어신호/환자정보 출력 | `IDisplay` | `show_cycle_result()`, `show_control_signal()`, `show_patient_info()` |

---

## 5. 인터페이스 정의

### 5.1 통신 계층 인터페이스 (`interfaces/communication.py`)

```python
from abc import ABC, abstractmethod
from typing import List, Optional
import numpy as np

from domain.models import PressureLog, PatientSettings, ControlSignal, AlertMessage


class ISerialReader(ABC):
    """시리얼 통신 인터페이스 (b)"""

    @abstractmethod
    def read_raw(self) -> bytes:
        """시리얼에서 원시 데이터 읽기"""
        pass

    @abstractmethod
    def to_matrix(self, data: bytes) -> np.ndarray:
        """원시 데이터를 행렬로 변환"""
        pass


class IServerClient(ABC):
    """서버 통신 인터페이스 (a)(d)"""

    @abstractmethod
    async def upload_pressure_log(self, log: PressureLog) -> bool:
        """압력 로그 업로드 (a)"""
        pass

    @abstractmethod
    async def fetch_patient_settings(self, patient_id: str) -> PatientSettings:
        """환자 설정 조회 (d)"""
        pass


class IControlNodeSender(ABC):
    """컨트롤 노드 통신 인터페이스 (c)"""

    @abstractmethod
    async def send_signal(self, signal: ControlSignal) -> bool:
        """제어 신호 전송"""
        pass


class INotifier(ABC):
    """알림 전송 인터페이스 (e)"""

    @abstractmethod
    async def send_notification(self, message: AlertMessage) -> bool:
        """푸시 알림 전송"""
        pass
```

### 5.2 서비스 계층 인터페이스 (`interfaces/service.py`)

```python
from abc import ABC, abstractmethod
from typing import List, Optional
import numpy as np

from domain.models import (
    Posture, PressurePoint, ControlSignal,
    PressureLog, PatientSettings, AlertMessage, CycleResult, PatientInfo
)


class IPostureDetector(ABC):
    """자세 추론 인터페이스 (f)"""

    @abstractmethod
    def detect(self, pressure_matrix: np.ndarray) -> Posture:
        """압력 행렬로부터 자세 추론"""
        pass


class IPressureAnalyzer(ABC):
    """압력 분석 인터페이스 (g)"""

    @abstractmethod
    def analyze(self, posture: Posture, matrix: np.ndarray) -> List[PressurePoint]:
        """자세를 기반으로 압력 부위 분석"""
        pass


class ILogManager(ABC):
    """로그 관리 인터페이스 (h)"""

    @abstractmethod
    def record(self, points: List[PressurePoint]) -> None:
        """압력 지속 시간 기록"""
        pass

    @abstractmethod
    def get_current_log(self) -> PressureLog:
        """현재 로그 반환"""
        pass


class IControlGenerator(ABC):
    """제어 신호 생성 인터페이스 (i)"""

    @abstractmethod
    def generate(self, points: List[PressurePoint]) -> ControlSignal:
        """압력 부위로부터 제어 신호 생성"""
        pass


class IAlertChecker(ABC):
    """알림 체크 인터페이스"""

    @abstractmethod
    def check(self, settings: PatientSettings, points: List[PressurePoint]) -> Optional[AlertMessage]:
        """임계값 초과 시 알림 메시지 반환"""
        pass


class IServiceFacade(ABC):
    """서비스 계층 통합 인터페이스 - 표현 계층에서 사용"""

    @abstractmethod
    async def process_cycle(self) -> CycleResult:
        """한 사이클 처리 후 결과 반환"""
        pass

    @abstractmethod
    def get_patient_info(self) -> PatientInfo:
        """환자 정보 조회"""
        pass
```

### 5.3 표현 계층 인터페이스 (`interfaces/presentation.py`)

```python
from abc import ABC, abstractmethod
from domain.models import CycleResult, PatientInfo, ControlSignal


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
    def show_patient_info(self, info: PatientInfo) -> None:
        """환자 정보 표시"""
        pass

    @abstractmethod
    def show_error(self, error: Exception) -> None:
        """에러 표시"""
        pass
```

---

## 6. 도메인 모델 (`domain/models.py`)

```python
from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum


class PostureType(Enum):
    SUPINE = "supine"           # 앙와위 (등)
    PRONE = "prone"             # 복와위 (배)
    LEFT_LATERAL = "left"       # 좌측위
    RIGHT_LATERAL = "right"     # 우측위
    UNKNOWN = "unknown"


class BodyPart(Enum):
    HEAD = "head"
    SHOULDER_LEFT = "shoulder_left"
    SHOULDER_RIGHT = "shoulder_right"
    BACK = "back"
    HIP = "hip"
    HEEL_LEFT = "heel_left"
    HEEL_RIGHT = "heel_right"


@dataclass
class Posture:
    type: PostureType
    confidence: float
    timestamp: datetime


@dataclass
class PressurePoint:
    body_part: BodyPart
    pressure_value: float
    duration_seconds: int       # 압력 유지 시간


@dataclass
class ControlSignal:
    target_zones: List[int]     # 제어할 영역 번호
    action: str                 # "inflate" | "deflate"
    intensity: int              # 0-100


@dataclass
class PressureLog:
    patient_id: str
    timestamp: datetime
    posture: Posture
    pressure_points: List[PressurePoint]


@dataclass
class PatientSettings:
    patient_id: str
    alert_threshold_seconds: int
    pressure_threshold: float


@dataclass
class AlertMessage:
    patient_id: str
    title: str
    body: str
    priority: str


@dataclass
class CycleResult:
    posture: Posture
    pressure_points: List[PressurePoint]
    control_signal: ControlSignal
    alert_sent: bool
    timestamp: datetime


@dataclass
class PatientInfo:
    patient_id: str
    name: str
    settings: PatientSettings
```

---

## 7. 데이터 흐름

```
[센서]
   ↓ (b) ISerialReader.read_raw() → to_matrix()
[압력 행렬 데이터]
   ↓ (f) IPostureDetector.detect()
[추론된 자세]
   ↓ (g) IPressureAnalyzer.analyze()
[압력 부위 정보]
   ├─→ (h) ILogManager.record() → (a) IServerClient.upload_pressure_log() → [서버 로그]
   ├─→ (i) IControlGenerator.generate() → (c) IControlNodeSender.send_signal() → [컨트롤 노드]
   └─→ IAlertChecker.check() → (e) INotifier.send_notification() → [푸시 알림]
              ↑
      (d) IServerClient.fetch_patient_settings() [환자 설정]
```

---

## 8. 의존성 주입 (`container.py`)

```python
from dataclasses import dataclass
from config.settings import Settings

# 인터페이스
from interfaces.communication import (
    ISerialReader, IServerClient, IControlNodeSender, INotifier
)
from interfaces.service import IServiceFacade
from interfaces.presentation import IDisplay

# 구현체
from communication.serial_handler import SerialHandler
from communication.supabase_client import SupabaseClient
from communication.control_sender import ControlSender
from communication.fcm_notifier import FCMNotifier

from service.posture_detector import PostureDetector
from service.pressure_analyzer import PressureAnalyzer
from service.log_manager import LogManager
from service.control_service import ControlGenerator
from service.alert_service import AlertChecker
from service.service_facade import ServiceFacade

from presentation.console_display import ConsoleDisplay


@dataclass
class Container:
    """의존성 주입 컨테이너"""
    serial_reader: ISerialReader
    server_client: IServerClient
    control_sender: IControlNodeSender
    notifier: INotifier
    service_facade: IServiceFacade
    display: IDisplay


def create_container(settings: Settings) -> Container:
    """프로덕션 의존성 구성"""

    # 통신 계층
    serial_reader = SerialHandler(settings.serial_port, settings.baudrate)
    server_client = SupabaseClient(settings.supabase_url, settings.supabase_key)
    control_sender = ControlSender(settings.control_node_address)
    notifier = FCMNotifier(settings.fcm_credentials)

    # 서비스 계층
    posture_detector = PostureDetector()
    pressure_analyzer = PressureAnalyzer()
    log_manager = LogManager()
    control_generator = ControlGenerator()
    alert_checker = AlertChecker()

    service_facade = ServiceFacade(
        serial_reader=serial_reader,
        server_client=server_client,
        control_sender=control_sender,
        notifier=notifier,
        posture_detector=posture_detector,
        pressure_analyzer=pressure_analyzer,
        log_manager=log_manager,
        control_generator=control_generator,
        alert_checker=alert_checker,
        patient_id=settings.patient_id
    )

    # 표현 계층
    display = ConsoleDisplay()

    return Container(
        serial_reader=serial_reader,
        server_client=server_client,
        control_sender=control_sender,
        notifier=notifier,
        service_facade=service_facade,
        display=display
    )


def create_test_container(**mocks) -> Container:
    """테스트용 의존성 구성 - Mock 주입 가능"""
    pass
```

---

## 9. 변경 영향 격리

| 변경 사항 | 수정 범위 | 다른 계층 영향 |
|----------|----------|---------------|
| Supabase → Firebase로 교체 | `supabase_client.py` 삭제, `firebase_client.py` 추가, `container.py` 수정 | ❌ 없음 |
| 시리얼 → MQTT로 변경 | `serial_handler.py` → `mqtt_handler.py`, `container.py` 수정 | ❌ 없음 |
| 자세 추론 알고리즘 변경 | `posture_detector.py` 내부만 수정 | ❌ 없음 |
| 콘솔 → GUI로 변경 | `console_display.py` → `gui_display.py`, `container.py` 수정 | ❌ 없음 |

---

## 10. 기술 스택

| 구분 | 기술 |
|------|------|
| 언어 | Python 3.9+ |
| 시리얼 통신 | `pyserial` |
| Supabase | `supabase-py` |
| FCM | `firebase-admin` |
| 행렬 처리 | `numpy` |
| 비동기 처리 | `asyncio` |
| 화면 출력 | `rich` (터미널 테이블) |
