from datetime import datetime, date
from typing import Optional, Callable, Awaitable

from interfaces.communication import (
    ISerialReader,
    IServerClient,
    IControlNodeSender,
    INotifier,
)
from interfaces.service import (
    IPostureDetector,
    IPressureAnalyzer,
    ILogManager,
    IAlertChecker,
    IServiceFacade,
)
from domain.models import Patient, CycleResult, ControlPacket
from service.heatmap_converter import HeatmapConverter


class ServiceFacade(IServiceFacade):
    """서비스 계층 통합 Facade"""

    def __init__(
        self,
        serial_reader: ISerialReader,
        server_client: IServerClient,
        control_sender: IControlNodeSender,
        notifier: INotifier,
        posture_detector: IPostureDetector,
        pressure_analyzer: IPressureAnalyzer,
        log_manager: ILogManager,
        alert_checker: IAlertChecker,
        heatmap_converter: HeatmapConverter,
        device_id: int,
    ):
        self._serial_reader = serial_reader
        self._server_client = server_client
        self._control_sender = control_sender
        self._notifier = notifier
        self._posture_detector = posture_detector
        self._pressure_analyzer = pressure_analyzer
        self._log_manager = log_manager
        self._alert_checker = alert_checker
        self._heatmap_converter = heatmap_converter
        self._device_id = device_id
        self._patient: Optional[Patient] = None
        self._sensor_data_callback: Optional[Callable[[dict], Awaitable[None]]] = None

    async def initialize(self) -> None:
        """초기화 - 환자 정보 로드"""
        # Supabase 클라이언트 초기화
        await self._server_client.initialize()

        # device_id로 환자 정보 조회
        self._patient = await self._server_client.async_fetch_patient_with_device(
            self._device_id
        )

        # 로그 매니저에 device_id 설정
        self._log_manager.set_device_id(self._device_id)

        # 오늘 날짜의 DayLog 조회 또는 생성
        today = date.today().isoformat()
        daylog = await self._server_client.async_fetch_daylog_by_date(
            self._device_id, today
        )

        if daylog:
            self._log_manager.set_daylog(daylog)
        else:
            # 새 DayLog 생성
            new_daylog = self._log_manager.get_current_daylog()
            created_daylog = await self._server_client.async_create_daylog(new_daylog)
            self._log_manager.set_daylog(created_daylog)

        # 컨트롤 노드로부터 센서 데이터 수신 콜백 설정 (리스닝은 connect 후 main에서 시작)
        self._control_sender.set_sensor_callback(self._on_sensor_data_received)

    async def _on_sensor_data_received(self, sensor_data: dict) -> None:
        """컨트롤 노드로부터 센서 데이터 수신 시 처리

        Args:
            sensor_data: 컨트롤 노드에서 수신한 센서 데이터
                        예: {"inflated_zones": [1, 3], "timestamp": "2025-11-29T10:30:00.123456"}
        """
        # Supabase 채널로 센서 데이터 브로드캐스팅
        await self._server_client.async_broadcast_controls(self._device_id, sensor_data)

        # 외부 콜백 호출 (Display 업데이트 등)
        if self._sensor_data_callback:
            await self._sensor_data_callback(sensor_data)

    def set_sensor_data_callback(self, callback: Callable[[dict], Awaitable[None]]) -> None:
        """센서 데이터 수신 콜백 설정"""
        self._sensor_data_callback = callback

    async def process_cycle(self) -> CycleResult:
        """한 사이클 처리 후 결과 반환"""
        # (b) 시리얼 데이터 읽기 (비동기로 별도 스레드에서 실행)
        head, body = await self._serial_reader.async_read()

        # head (2, 3) + body (12, 7) → heatmap (14, 7)
        heatmap = self._heatmap_converter.convert(head, body)

        # 히트맵 실시간 업데이트
        await self._server_client.async_update_heatmap(self._device_id, heatmap)

        # (f) 자세 추론
        detection_result = self._posture_detector.detect(heatmap)
        posture = detection_result.posture_type

        # (g) 압력 받는 부위 분석
        active_parts = self._pressure_analyzer.analyze(posture)

        # (h) 로그 기록
        self._log_manager.record(active_parts, posture)
        durations = self._log_manager.get_durations()

        # 자세 변경 필요 여부 확인
        posture_change_required = False
        if self._patient:
            posture_change_required = self._alert_checker.check_posture_change_required(
                self._patient, durations
            )

        # PressureLog 생성
        daylog = self._log_manager.get_current_daylog()
        pressure_log = self._log_manager.create_pressure_log(
            day_id=daylog.id,
            posture=posture,
            posture_change_required=posture_change_required,
        )

        # (a) 서버에 로그 업로드
        await self._server_client.async_create_pressurelog(pressure_log)
        await self._server_client.async_update_daylog(daylog)

        # 서버에서 controls 조회
        controls = await self._server_client.async_fetch_device_controls(self._device_id)

        # 통합 패킷 생성
        control_packet = ControlPacket(
            posture=posture,
            active_parts=[bp.value for bp in active_parts],
            durations={bp.value: v for bp, v in durations.items()},
            controls=controls,
        )

        # (c) 컨트롤 노드에 통합 패킷 전송
        await self._control_sender.send_packet(control_packet)

        # 알림 체크 및 전송
        alert_sent = False
        if self._patient and posture_change_required:
            alert_message = self._alert_checker.check(self._patient, durations)
            if alert_message:
                # (e) 푸시 알림 전송
                await self._notifier.send_notification(alert_message)
                alert_sent = True

        return CycleResult(
            posture=posture,
            pressure_log=pressure_log,
            control_packet=control_packet,
            alert_sent=alert_sent,
            posture_change_required=posture_change_required,
            durations=durations,
            timestamp=datetime.now(),
        )

    def get_patient(self) -> Optional[Patient]:
        """환자 정보 조회"""
        return self._patient

    def get_device_id(self) -> int:
        """디바이스 ID 조회"""
        return self._device_id
