import asyncio
import json

from interfaces.communication import IControlNodeSender
from domain.models import ControlPacket


class ControlSender(IControlNodeSender):
    """컨트롤 노드 통신 구현체 (c)"""

    def __init__(self, address: str, port: int = 8080):
        self._address = address
        self._port = port
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

    async def connect(self) -> None:
        """컨트롤 노드 연결"""
        self._reader, self._writer = await asyncio.open_connection(
            self._address, self._port
        )

    async def disconnect(self) -> None:
        """연결 해제"""
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()

    async def send_packet(self, packet: ControlPacket) -> bool:
        """통합 패킷 전송 (자세, 압력, 지속시간, controls 포함)"""
        if not self._writer:
            raise ConnectionError("Not connected to control node")

        message = json.dumps(packet.to_dict()).encode() + b"\n"
        self._writer.write(message)
        await self._writer.drain()

        # ACK 대기
        if self._reader:
            response = await asyncio.wait_for(
                self._reader.readline(),
                timeout=5.0,
            )
            return response.strip() == b"ACK"

        return False
