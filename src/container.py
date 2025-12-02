from dataclasses import dataclass

from config.settings import Settings

# 인터페이스
from interfaces.communication import (
    ISerialReader,
    IServerClient,
    IControlNodeSender,
    INotifier,
)
from interfaces.service import IServiceFacade
from interfaces.presentation import IDisplay

# 구현체
from communication.serial_handler import SerialHandler
from communication.supabase_client import SupabaseClient
from communication.control_sender import ControlSender
from communication.mock_control_sender import MockControlSender
from communication.fcm_notifier import FCMNotifier

from service.posture_detector import PostureDetector
from service.pressure_analyzer import PressureAnalyzer
from service.log_manager import LogManager
from service.alert_service import AlertChecker
from service.heatmap_converter import HeatmapConverter
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
    """의존성 구성 (test_mode에 따라 Mock 사용)"""

    # 통신 계층 (멀티포트 자동 탐색)
    serial_reader = SerialHandler(settings.baudrate)
    server_client = SupabaseClient(settings.supabase_url, settings.supabase_key)

    # 테스트 모드에서는 MockControlSender 사용
    if settings.test_mode:
        control_sender = MockControlSender()
    else:
        control_sender = ControlSender(
            settings.control_node_address, settings.control_node_port
        )

    notifier = FCMNotifier(settings.fcm_credentials)

    # 서비스 계층
    posture_detector = PostureDetector()
    pressure_analyzer = PressureAnalyzer()
    log_manager = LogManager(settings.device_id)
    alert_checker = AlertChecker()
    heatmap_converter = HeatmapConverter()

    service_facade = ServiceFacade(
        serial_reader=serial_reader,
        server_client=server_client,
        control_sender=control_sender,
        notifier=notifier,
        posture_detector=posture_detector,
        pressure_analyzer=pressure_analyzer,
        log_manager=log_manager,
        alert_checker=alert_checker,
        heatmap_converter=heatmap_converter,
        device_id=settings.device_id,
    )

    # 표현 계층
    display = ConsoleDisplay()

    return Container(
        serial_reader=serial_reader,
        server_client=server_client,
        control_sender=control_sender,
        notifier=notifier,
        service_facade=service_facade,
        display=display,
    )
