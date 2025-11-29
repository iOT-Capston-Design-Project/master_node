import argparse
import asyncio
import signal
import sys
import logging

from config.settings import Settings
from container import create_container


class TUILogHandler(logging.Handler):
    """TUI에 로그를 표시하는 핸들러"""

    def __init__(self, display):
        super().__init__()
        self._display = display

    def emit(self, record):
        try:
            msg = self.format(record)
            style = ""
            if record.levelno >= logging.ERROR:
                style = "red"
            elif record.levelno >= logging.WARNING:
                style = "yellow"
            elif record.levelno >= logging.INFO:
                style = "green"
            self._display.add_log(msg, style)
        except Exception:
            pass


class Application:
    """메인 애플리케이션"""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._container = create_container(settings)
        self._running = False
        self._logger = logging.getLogger("application")
        self._test_mode = settings.test_mode

    def _setup_logging(self) -> None:
        """TUI용 로깅 설정"""
        # 기존 핸들러 제거
        root_logger = logging.getLogger()
        root_logger.handlers.clear()

        # TUI 로그 핸들러 추가
        tui_handler = TUILogHandler(self._container.display)
        tui_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
        )
        root_logger.addHandler(tui_handler)
        root_logger.setLevel(logging.INFO)

    async def _connect_serial_with_retry(self) -> bool:
        """시리얼 포트 연결 시도 (재시도 로직 포함)"""
        try:
            self._container.serial_reader.connect()
            self._serial_connected = True
            self._logger.info("시리얼 포트 연결 성공")
            return True
        except Exception as e:
            self._serial_connected = False
            self._logger.warning(f"시리얼 포트 연결 실패: {e}")
            return False

    async def _connect_control_with_retry(self) -> bool:
        """컨트롤 노드 연결 시도 (재시도 로직 포함)"""
        try:
            await self._container.control_sender.connect()
            self._control_connected = True
            self._logger.info("컨트롤 노드 연결 성공")
            return True
        except Exception as e:
            self._control_connected = False
            self._logger.warning(f"컨트롤 노드 연결 실패: {e}")
            return False

    async def start(self) -> None:
        """애플리케이션 시작"""
        self._running = True
        self._serial_connected = False
        self._control_connected = False

        # TUI 시작
        self._container.display.start_live()

        # 로깅을 TUI로 리다이렉트
        self._setup_logging()

        try:
            # 테스트 모드 표시
            if self._test_mode:
                self._container.display.set_test_mode(True)
                self._logger.warning("========== 테스트 모드로 실행 중 ==========")

            # 센서 데이터 수신 콜백 설정 (TUI에 표시)
            async def on_sensor_data(sensor_data: dict) -> None:
                self._container.display.show_sensor_data(sensor_data)

            self._container.service_facade.set_sensor_data_callback(on_sensor_data)

            # 초기화
            self._logger.info("애플리케이션 초기화 중...")
            await self._container.service_facade.initialize()

            # 환자 정보 표시
            patient = self._container.service_facade.get_patient()
            device_id = self._container.service_facade.get_device_id()
            self._container.display.show_patient_info(patient, device_id)

            if not patient:
                self._logger.warning(f"디바이스 {device_id}에 등록된 환자 없음")

            # 초기 연결 시도
            self._logger.info("시리얼 포트 연결 중...")
            await self._connect_serial_with_retry()

            self._logger.info("컨트롤 노드 연결 중...")
            await self._connect_control_with_retry()

            # 컨트롤 노드 연결 성공 시 센서 데이터 수신 시작
            if self._control_connected:
                await self._container.control_sender.start_listening()
                self._logger.info("센서 데이터 수신 대기 시작")

            self._logger.info("모니터링 시작")

            # 메인 루프
            retry_interval = 5.0  # 재연결 시도 간격 (초)
            last_retry_time = 0.0

            while self._running:
                current_time = asyncio.get_event_loop().time()

                # 연결되지 않은 경우 주기적으로 재연결 시도
                if current_time - last_retry_time >= retry_interval:
                    if not self._serial_connected:
                        self._logger.info("시리얼 포트 재연결 시도 중...")
                        await self._connect_serial_with_retry()

                    if not self._control_connected:
                        self._logger.info("컨트롤 노드 재연결 시도 중...")
                        await self._connect_control_with_retry()
                        # 재연결 성공 시 센서 데이터 수신 시작
                        if self._control_connected:
                            await self._container.control_sender.start_listening()
                            self._logger.info("센서 데이터 수신 대기 시작")

                    last_retry_time = current_time

                # 시리얼이 연결되지 않은 경우 대기
                if not self._serial_connected:
                    self._container.display.show_connection_status(
                        serial_connected=False,
                        control_connected=self._control_connected
                    )
                    await asyncio.sleep(1.0)
                    continue

                try:
                    result = await self._container.service_facade.process_cycle()
                    self._container.display.show_cycle_result(result)
                    await asyncio.sleep(self._settings.cycle_interval)
                except (ConnectionError, OSError) as e:
                    # 연결 관련 오류 발생 시 연결 상태 리셋
                    self._serial_connected = False
                    self._container.display.show_error(e)
                    self._logger.error(f"연결 오류: {e}")
                    await asyncio.sleep(1.0)
                except Exception as e:
                    self._container.display.show_error(e)
                    self._logger.error(f"사이클 오류: {e}")
                    await asyncio.sleep(1.0)

        except Exception as e:
            self._logger.error(f"애플리케이션 오류: {e}")
            self._container.display.show_error(e)
            raise
        finally:
            self._container.display.stop_live()

    async def stop(self) -> None:
        """애플리케이션 종료"""
        self._logger.info("애플리케이션 종료 중...")
        self._running = False

        # 연결 해제
        try:
            self._container.serial_reader.disconnect()
        except Exception as e:
            self._logger.error(f"시리얼 연결 해제 오류: {e}")

        try:
            await self._container.control_sender.disconnect()
        except Exception as e:
            self._logger.error(f"컨트롤 노드 연결 해제 오류: {e}")

        self._logger.info("애플리케이션 종료 완료")


def parse_args() -> argparse.Namespace:
    """CLI 인자 파싱"""
    parser = argparse.ArgumentParser(
        description="베드솔루션 마스터 노드",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--test", "-t",
        action="store_true",
        help="테스트 모드로 실행 (컨트롤 노드에 Mock 데이터 전송)",
    )
    return parser.parse_args()


def main() -> None:
    """메인 진입점"""
    # CLI 인자 파싱
    args = parse_args()

    # 설정 로드
    settings = Settings.from_env()

    # 테스트 모드 설정
    if args.test:
        settings.test_mode = True

    try:
        settings.validate()
    except ValueError as e:
        print(f"설정 오류: {e}")
        print("\n필수 환경 변수:")
        print("  DEVICE_ID: 디바이스 ID (정수)")
        print("  SUPABASE_URL: Supabase URL")
        print("  SUPABASE_KEY: Supabase API Key")
        sys.exit(1)

    # 테스트 모드 시작 메시지
    if settings.test_mode:
        print("\n" + "=" * 50)
        print("  [TEST MODE] 테스트 모드로 실행합니다")
        print("  컨트롤 노드에 Mock 데이터가 전송됩니다")
        print("=" * 50 + "\n")

    app = Application(settings)

    # 이벤트 루프 설정
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # 시그널 핸들러 설정
    def signal_handler():
        loop.create_task(app.stop())

    try:
        loop.add_signal_handler(signal.SIGINT, signal_handler)
        loop.add_signal_handler(signal.SIGTERM, signal_handler)
    except NotImplementedError:
        # Windows에서는 add_signal_handler가 지원되지 않음
        pass

    try:
        loop.run_until_complete(app.start())
    except KeyboardInterrupt:
        loop.run_until_complete(app.stop())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
