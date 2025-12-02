import logging
import asyncio
from typing import Optional

import numpy as np
from supabase import create_async_client, AsyncClient

from interfaces.communication import IServerClient
from domain.models import Patient, DeviceData, DayLog, PressureLog


class SupabaseClient(IServerClient):
    """Supabase 서버 통신 구현체"""

    def __init__(self, url: str, key: str):
        self._url = url
        self._key = key
        self._client: Optional[AsyncClient] = None
        self._logger = logging.getLogger("supabase_client")
        self._device_channels: dict[int, any] = {}

    async def initialize(self) -> None:
        """비동기 초기화"""
        if not self._url or not self._key:
            self._logger.error("Supabase URL and API key must be configured")
            return

        try:
            self._client = await create_async_client(self._url, self._key)
            self._logger.info("Supabase client initialized successfully")
        except Exception as e:
            self._logger.error(f"Failed to initialize Supabase client: {e}")
            self._client = None

    # Device 관련
    async def async_fetch_device(self, device_id: int) -> Optional[DeviceData]:
        """디바이스 조회"""
        if not self._client:
            self._logger.error("Supabase client is not initialized")
            return None

        try:
            self._logger.info(f"Fetching device with id: {device_id}")
            response = await self._client.table("devices").select("*").eq("id", device_id).execute()
            if response.data:
                self._logger.info(f"Device found: {device_id}")
                return DeviceData.from_dict(response.data[0])
            self._logger.warning(f"Device not found: {device_id}")
            return None
        except Exception as e:
            self._logger.error(f"Error fetching device {device_id}: {e}")
            return None

    async def async_create_device(self, device: DeviceData) -> Optional[DeviceData]:
        """디바이스 등록"""
        if not self._client:
            self._logger.error("Supabase client is not initialized")
            return None

        try:
            self._logger.info(f"Creating device with id: {device.id}")
            response = await self._client.table("devices").insert(device.to_dict()).execute()
            if response.data:
                self._logger.info(f"Device created successfully: {device.id}")
                return DeviceData.from_dict(response.data[0])
            self._logger.warning(f"Device creation returned no data: {device.id}")
            return None
        except Exception as e:
            self._logger.error(f"Error creating device {device.id}: {e}")
            return None

    # Patient 관련
    async def async_fetch_patient_with_device(self, device_id: int) -> Optional[Patient]:
        """device_id로 환자 조회"""
        if not self._client:
            self._logger.error("Supabase client is not initialized")
            return None

        try:
            self._logger.info(f"Fetching patient with device_id: {device_id}")
            response = await self._client.table("patients").select("*").eq("device_id", device_id).execute()
            if response.data:
                self._logger.info(f"Patient found for device: {device_id}")
                return Patient.from_dict(response.data[0])
            self._logger.warning(f"No patient found for device: {device_id}")
            return None
        except Exception as e:
            self._logger.error(f"Error fetching patient with device {device_id}: {e}")
            return None

    # DayLog 관련
    async def async_create_daylog(self, daylog: DayLog) -> DayLog:
        """일별 로그 생성"""
        if not self._client:
            self._logger.error("Supabase client is not initialized")
            return daylog

        try:
            self._logger.info(f"Creating daylog for device: {daylog.device_id}, day: {daylog.day}")
            data = daylog.to_dict()
            del data["id"]  # id는 서버에서 생성
            response = await self._client.table("day_logs").insert(data).execute()
            if response.data:
                self._logger.info(f"Daylog created successfully")
                return DayLog.from_dict(response.data[0])
            self._logger.warning(f"Daylog creation returned no data for device: {daylog.device_id}")
            return daylog
        except Exception as e:
            self._logger.error(f"Error creating daylog for device {daylog.device_id}: {e}")
            return daylog

    async def async_update_daylog(self, daylog: DayLog) -> Optional[DayLog]:
        """일별 로그 업데이트"""
        if not self._client:
            self._logger.error("Supabase client is not initialized")
            return daylog

        try:
            self._logger.info(f"Updating daylog: {daylog.id}")
            response = await self._client.table("day_logs").update(daylog.to_dict()).eq("id", daylog.id).execute()
            if response.data:
                self._logger.info(f"Daylog updated successfully: {daylog.id}")
                return DayLog.from_dict(response.data[0])
            self._logger.warning(f"Daylog update returned no data: {daylog.id}")
            return daylog
        except Exception as e:
            self._logger.error(f"Error updating daylog {daylog.id}: {e}")
            return None

    async def async_fetch_daylog_by_date(self, device_id: int, day: str) -> Optional[DayLog]:
        """특정 날짜의 DayLog 조회"""
        if not self._client:
            self._logger.error("Supabase client is not initialized")
            return None

        try:
            self._logger.info(f"Fetching daylog for device: {device_id}, day: {day}")
            response = (
                await self._client.table("day_logs")
                .select("*")
                .eq("device_id", device_id)
                .eq("day", day)
                .execute()
            )
            if response.data:
                self._logger.info(f"Daylog found for device: {device_id}, day: {day}")
                return DayLog.from_dict(response.data[0])
            self._logger.info(f"No daylog found for device: {device_id}, day: {day}")
            return None
        except Exception as e:
            self._logger.error(f"Error fetching daylog: {e}")
            return None

    # PressureLog 관련
    async def async_create_pressurelog(self, pressurelog: PressureLog) -> Optional[PressureLog]:
        """압력 로그 생성"""
        if not self._client:
            self._logger.error("Supabase client is not initialized")
            return pressurelog

        try:
            self._logger.info(f"Creating pressurelog for day: {pressurelog.day_id}")
            data = pressurelog.to_dict()
            del data["id"]  # id는 서버에서 생성
            self._logger.info(f"Pressurelog data to insert: {data}")
            response = await self._client.table("pressure_logs").insert(data).execute()
            if response.data:
                self._logger.info(f"Pressurelog created successfully")
                return PressureLog.from_dict(response.data[0])
            self._logger.warning(f"Pressurelog creation returned no data")
            return pressurelog
        except Exception as e:
            self._logger.error(f"Error creating pressurelog: {e}")
            return None

    async def async_update_pressurelog(self, pressurelog: PressureLog) -> Optional[PressureLog]:
        """압력 로그 업데이트"""
        if not self._client:
            self._logger.error("Supabase client is not initialized")
            return pressurelog

        try:
            self._logger.info(f"Updating pressurelog: {pressurelog.id}")
            response = (
                await self._client.table("pressure_logs")
                .update(pressurelog.to_dict())
                .eq("id", pressurelog.id)
                .execute()
            )
            if response.data:
                self._logger.info(f"Pressurelog updated successfully: {pressurelog.id}")
                return PressureLog.from_dict(response.data[0])
            self._logger.warning(f"Pressurelog update returned no data: {pressurelog.id}")
            return pressurelog
        except Exception as e:
            self._logger.error(f"Error updating pressurelog {pressurelog.id}: {e}")
            return None

    # Heatmap 실시간 업데이트
    async def async_update_heatmap(self, device_id: int, heatmap: np.ndarray) -> bool:
        """히트맵 실시간 업데이트 (Supabase Realtime)"""
        if not self._client:
            return False

        try:
            if device_id in self._device_channels:
                channel = self._device_channels[device_id]
                await channel.send_broadcast(
                    "heatmap_update",
                    {"values": heatmap.flatten().tolist()},
                )
                return True

            # 새 채널 생성 및 구독
            channel = self._client.channel(f"{device_id}")
            self._device_channels[device_id] = channel

            await channel.subscribe()
            await channel.send_broadcast(
                "heatmap_update",
                {"values": heatmap.flatten().tolist()},
            )
            return True
        except Exception as e:
            self._logger.error(f"Error updating heatmap for device {device_id}: {e}")
            return False

    async def async_fetch_device_controls(self, device_id: int) -> Optional[dict]:
        """디바이스 controls 컬럼 조회"""
        if not self._client:
            self._logger.error("Supabase client is not initialized")
            return None

        try:
            response = (
                await self._client.table("devices")
                .select("controls")
                .eq("id", device_id)
                .execute()
            )
            if response.data:
                return response.data[0].get("controls")
            return None
        except Exception as e:
            self._logger.error(f"Error fetching controls for device {device_id}: {e}")
            return None

    async def async_broadcast_controls(self, device_id: int, controls_data: dict) -> bool:
        """컨트롤 노드로부터 받은 센서 데이터를 실시간 브로드캐스팅

        Args:
            device_id: 디바이스 ID
            controls_data: 컨트롤 노드에서 수신한 센서 데이터
                          예: {"inflated_zones": [1, 3], "timestamp": "2025-11-29T10:30:00.123456"}
        """
        if not self._client:
            self._logger.error("Supabase client is not initialized")
            return False

        try:
            if device_id in self._device_channels:
                channel = self._device_channels[device_id]
                await channel.send_broadcast(
                    "controls",
                    controls_data,
                )
                self._logger.debug(f"Controls broadcasted for device {device_id}: {controls_data}")
                return True

            # 새 채널 생성 및 구독
            channel = self._client.channel(f"{device_id}")
            self._device_channels[device_id] = channel

            await channel.subscribe()
            await channel.send_broadcast(
                "controls",
                controls_data,
            )
            self._logger.info(f"New channel created and controls broadcasted for device {device_id}")
            return True
        except Exception as e:
            self._logger.error(f"Error broadcasting controls for device {device_id}: {e}")
            return False
