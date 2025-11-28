import firebase_admin
from firebase_admin import credentials, messaging

from interfaces.communication import INotifier
from domain.models import AlertMessage


class FCMNotifier(INotifier):
    """Firebase Cloud Messaging 알림 구현체 (e)"""

    def __init__(self, credentials_path: str):
        self._credentials_path = credentials_path
        self._initialized = False

    def initialize(self) -> None:
        """Firebase 초기화"""
        if not self._initialized:
            cred = credentials.Certificate(self._credentials_path)
            firebase_admin.initialize_app(cred)
            self._initialized = True

    async def send_notification(self, message: AlertMessage) -> bool:
        """푸시 알림 전송"""
        if not self._initialized:
            self.initialize()

        notification = messaging.Message(
            notification=messaging.Notification(
                title=message.title,
                body=message.body,
            ),
            topic=f"patient_{message.patient_id}",
            android=messaging.AndroidConfig(
                priority="high" if message.priority == "high" else "normal",
            ),
        )

        response = messaging.send(notification)
        return bool(response)
