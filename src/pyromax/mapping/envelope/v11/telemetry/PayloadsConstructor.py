from __future__ import annotations

import time
from random import Random
from typing import Any


from ..payloads.models import TelemetryEventMappingModel


class TelemetryPayloadBuilder:
    def __init__(self, rng: Random) -> None:
        self.rng = rng

    def login(self, user_id: int, session_id: int) -> TelemetryEventMappingModel:
        return TelemetryEventMappingModel(
            time=now_ms(),
            user_id=user_id,
            type="PERF",
            event="login",
            params={
                "properties": {
                    "connection_type": 2,
                    "vpn": 0,
                    "class": 2,
                    "background": 1,
                    "warm_start": 1,
                },
                "errorType": 100,
            },
            session_id=session_id,
        )

    def navigation(
        self,
        *,
        user_id: int,
        session_id: int,
        screen_from: int,
        screen_to: int,
        prev_time: int,
        action_id: int,
        extra_params: dict[str, int],
    ) -> TelemetryEventMappingModel:
        params: dict[str, Any] = {
            "prev_time": prev_time,
            "screen_to": screen_to,
            "action_id": action_id,
            "screen_from": screen_from,
        }
        params.update(extra_params)
        return TelemetryEventMappingModel(
            time=now_ms(),
            user_id=user_id,
            type="NAV",
            event="GO",
            params=params,
            session_id=session_id,
        )

    def open_chat(self, user_id: int, session_id: int) -> TelemetryEventMappingModel:
        messages = self.rng.randint(60, 240)
        render = self.rng.randint(50, 260)
        duration = messages + render
        return TelemetryEventMappingModel(
            time=now_ms(),
            user_id=user_id,
            type="PERF",
            event="open_chat_to_render",
            params={
                "spans": [
                    {
                        "duration": duration,
                        "name": "open_chat_to_render",
                    },
                    {
                        "duration": messages,
                        "name": "messages_list_created",
                    },
                    {
                        "duration": render,
                        "name": "messages_render",
                    },
                ],
                "properties": {
                    "class": 2,
                    "warm": 1,
                    "flow": 1,
                },
            },
            session_id=session_id,
        )

    def open_chats(self, user_id: int, session_id: int) -> TelemetryEventMappingModel:
        created = self.rng.randint(50, 230)
        rendered = self.rng.randint(180, 650)
        duration = created + rendered
        return TelemetryEventMappingModel(
            time=now_ms(),
            user_id=user_id,
            type="PERF",
            event="open_chats_to_render",
            params={
                "spans": [
                    {
                        "duration": duration,
                        "name": "open_chats_to_render",
                    },
                    {
                        "duration": created,
                        "name": "chats_tab_created",
                    },
                    {
                        "duration": rendered,
                        "name": "chat_list_render",
                    },
                ],
                "properties": {"class": 2},
            },
            session_id=session_id,
        )

    # def to_payload(self, events: list[TelemetryEventMappingModel]) -> dict:
    #     return TelemetryRequest(events=events).model_dump()


def now_ms() -> int:
    return int(time.time() * 1000)
