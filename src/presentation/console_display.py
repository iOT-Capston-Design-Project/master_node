from typing import Optional
from collections import deque

from rich.console import Console, Group
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout
from rich.live import Live

from interfaces.presentation import IDisplay
from domain.models import CycleResult, Patient, ControlPacket
from domain.enums import PostureType, BodyPart


class ConsoleDisplay(IDisplay):
    """TUI 기반 콘솔 출력 구현체 (rich.live 사용)"""

    POSTURE_NAMES = {
        PostureType.UNKNOWN: "미확인",
        PostureType.SITTING: "앉은 자세",
        PostureType.LEFT_SIDE: "좌측위",
        PostureType.RIGHT_SIDE: "우측위",
        PostureType.SUPINE: "앙와위 (등)",
        PostureType.PRONE: "복와위 (배)",
        PostureType.SUPINE_LEFT: "앙와위 + 왼다리",
        PostureType.SUPINE_RIGHT: "앙와위 + 오른다리",
    }

    BODY_PART_NAMES = {
        BodyPart.OCCIPUT: "후두부",
        BodyPart.SCAPULA: "견갑골",
        BodyPart.RIGHT_ELBOW: "오른쪽 팔꿈치",
        BodyPart.LEFT_ELBOW: "왼쪽 팔꿈치",
        BodyPart.HIP: "엉덩이",
        BodyPart.RIGHT_HEEL: "오른쪽 발뒤꿈치",
        BodyPart.LEFT_HEEL: "왼쪽 발뒤꿈치",
    }

    MAX_LOG_LINES = 10

    def __init__(self):
        self._console = Console()
        self._live: Optional[Live] = None
        self._patient: Optional[Patient] = None
        self._device_id: int = 0
        self._last_result: Optional[CycleResult] = None
        self._last_error: Optional[Exception] = None
        self._log_messages: deque = deque(maxlen=self.MAX_LOG_LINES)
        self._serial_connected: bool = False
        self._control_connected: bool = False
        self._test_mode: bool = False

    def start_live(self) -> None:
        """Live 디스플레이 시작"""
        self._live = Live(
            self._build_layout(),
            console=self._console,
            refresh_per_second=4,
            screen=True,
        )
        self._live.start()

    def stop_live(self) -> None:
        """Live 디스플레이 종료"""
        if self._live:
            self._live.stop()
            self._live = None

    def add_log(self, message: str, style: str = "") -> None:
        """로그 메시지 추가"""
        self._log_messages.append((message, style))
        self._refresh()

    def _refresh(self) -> None:
        """화면 갱신"""
        if self._live:
            self._live.update(self._build_layout())

    def _build_layout(self) -> Layout:
        """전체 레이아웃 구성"""
        layout = Layout()

        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=self.MAX_LOG_LINES + 2),
        )

        layout["body"].split_row(
            Layout(name="left"),
            Layout(name="right"),
        )

        # 헤더: 타이틀 (테스트 모드 표시 포함)
        header_text = Text()
        if self._test_mode:
            header_text.append("[TEST MODE] ", style="bold yellow on red")
        header_text.append("베드솔루션 모니터링 시스템", style="bold white")
        if self._test_mode:
            header_text.append(" [TEST MODE]", style="bold yellow on red")

        header_border = "red" if self._test_mode else "blue"
        layout["header"].update(
            Panel(
                header_text,
                border_style=header_border,
                title="[bold yellow]테스트 모드[/bold yellow]" if self._test_mode else None,
            )
        )

        # 왼쪽: 환자 정보 + 현재 상태
        layout["left"].update(self._build_left_panel())

        # 오른쪽: 압력 정보 + 제어 신호
        layout["right"].update(self._build_right_panel())

        # 푸터: 로그
        layout["footer"].update(self._build_log_panel())

        return layout

    def _build_left_panel(self) -> Panel:
        """왼쪽 패널 (환자 정보 + 현재 상태)"""
        elements = []

        # 환자 정보 테이블
        patient_table = Table(title="디바이스/환자 정보", expand=True)
        patient_table.add_column("항목", style="cyan")
        patient_table.add_column("값")

        patient_table.add_row("디바이스 ID", str(self._device_id))

        if self._patient:
            patient_table.add_row("환자 ID", str(self._patient.id))
            patient_table.add_row("후두부", f"{self._patient.occiput_threshold}분")
            patient_table.add_row("견갑골", f"{self._patient.scapula_threshold}분")
            patient_table.add_row("오른팔꿈치", f"{self._patient.right_elbow_threshold}분")
            patient_table.add_row("왼팔꿈치", f"{self._patient.left_elbow_threshold}분")
            patient_table.add_row("엉덩이", f"{self._patient.hip_threshold}분")
            patient_table.add_row("오른발뒤꿈치", f"{self._patient.right_heel_threshold}분")
            patient_table.add_row("왼발뒤꿈치", f"{self._patient.left_heel_threshold}분")
        else:
            patient_table.add_row("환자", "[yellow]미등록[/yellow]")

        elements.append(patient_table)

        # 연결 상태
        conn_text = Text()
        serial_status = "연결됨" if self._serial_connected else "연결 안됨"
        serial_style = "green" if self._serial_connected else "red"
        control_status = "연결됨" if self._control_connected else "연결 안됨"
        control_style = "green" if self._control_connected else "red"

        conn_text.append("시리얼: ", style="cyan")
        conn_text.append(f"{serial_status}\n", style=serial_style)
        conn_text.append("컨트롤: ", style="cyan")
        conn_text.append(control_status, style=control_style)

        elements.append(Panel(conn_text, title="연결 상태", border_style="blue"))

        # 알림 상태
        if self._last_result:
            status_text = Text()
            status_text.append(f"마지막 업데이트: {self._last_result.timestamp.strftime('%H:%M:%S')}\n")

            if self._last_result.alert_sent:
                status_text.append("🔔 알림 전송됨", style="bold yellow")
            else:
                status_text.append("알림 없음", style="dim")

            elements.append(Panel(status_text, title="알림 상태", border_style="green"))

        # 에러 표시
        if self._last_error:
            elements.append(
                Panel(
                    f"[bold red]{type(self._last_error).__name__}[/bold red]\n{self._last_error}",
                    title="오류",
                    border_style="red",
                )
            )

        return Panel(Group(*elements), title="정보", border_style="blue")

    def _format_duration(self, seconds: int) -> str:
        """초를 분:초 형식으로 변환"""
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes:02d}:{secs:02d}"

    def _build_right_panel(self) -> Panel:
        """오른쪽 패널 (현재 자세 + 압력 지속 시간 + 제어 신호)"""
        elements = []

        # 현재 자세 표시
        if self._last_result:
            posture_name = self.POSTURE_NAMES.get(self._last_result.posture, "미확인")
            posture_style = "bold cyan"
            if self._last_result.posture_change_required:
                posture_style = "bold red"
            posture_text = Text()
            posture_text.append(f"{posture_name}", style=posture_style)
            if self._last_result.posture_change_required:
                posture_text.append(" (변경 필요)", style="bold red")
            elements.append(Panel(posture_text, title="현재 자세", border_style="cyan"))
        else:
            elements.append(Panel("[dim]대기 중...[/dim]", title="현재 자세", border_style="dim"))

        # 압력 지속 시간 테이블
        duration_table = Table(title="압력 지속 시간", expand=True)
        duration_table.add_column("부위", style="cyan")
        duration_table.add_column("지속 시간", justify="right")

        if self._last_result and self._last_result.durations:
            for body_part in BodyPart:
                part_name = self.BODY_PART_NAMES.get(body_part, body_part.value)
                duration = self._last_result.durations.get(body_part, 0)
                duration_str = self._format_duration(duration)
                # 2분 이상이면 경고 색상
                style = "bold red" if duration >= 120 else ("yellow" if duration >= 60 else "")
                duration_table.add_row(part_name, duration_str, style=style)
        else:
            for body_part in BodyPart:
                part_name = self.BODY_PART_NAMES.get(body_part, body_part.value)
                duration_table.add_row(part_name, "--:--")

        elements.append(duration_table)

        # 서버 제어 명령 테이블
        control_table = Table(title="서버 제어 명령", expand=True)
        control_table.add_column("항목", style="yellow")
        control_table.add_column("값", justify="right")

        if self._last_result and self._last_result.control_packet.controls:
            controls = self._last_result.control_packet.controls
            for key, value in controls.items():
                control_table.add_row(str(key), str(value))
        else:
            control_table.add_row("-", "[dim]없음[/dim]")

        elements.append(control_table)

        return Panel(Group(*elements), title="모니터링", border_style="blue")

    def _build_log_panel(self) -> Panel:
        """로그 패널"""
        log_text = Text()
        for msg, style in self._log_messages:
            log_text.append(f"{msg}\n", style=style)

        if not self._log_messages:
            log_text.append("[dim]로그가 없습니다[/dim]")

        return Panel(log_text, title="로그", border_style="dim")

    def show_cycle_result(self, result: CycleResult) -> None:
        """사이클 처리 결과 표시"""
        self._last_result = result
        self._last_error = None
        self._serial_connected = True  # 결과가 오면 시리얼은 연결된 상태
        self._refresh()

    def show_control_packet(self, packet: ControlPacket) -> None:
        """제어 패킷 표시 (결과에 포함되어 있어 별도 처리 불필요)"""
        pass

    def show_patient_info(self, patient: Optional[Patient], device_id: int) -> None:
        """환자 정보 저장"""
        self._patient = patient
        self._device_id = device_id
        self._refresh()

    def show_error(self, error: Exception) -> None:
        """에러 표시"""
        self._last_error = error
        self.add_log(f"[오류] {type(error).__name__}: {error}", "red")
        self._refresh()

    def show_connection_status(self, serial_connected: bool, control_connected: bool) -> None:
        """연결 상태 업데이트"""
        self._serial_connected = serial_connected
        self._control_connected = control_connected
        self._refresh()

    def set_test_mode(self, enabled: bool) -> None:
        """테스트 모드 설정"""
        self._test_mode = enabled
        self._refresh()
