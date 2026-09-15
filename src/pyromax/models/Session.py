import json
from dataclasses import dataclass
from typing import Any, Self

from pydantic import Field, model_validator

from .base import BaseMaxObject
from .enum import DeviceType


DEFAULT_CONFIG_HASH = (
    "00000000-0000000000000000-00000000-"
    "0000000000000000-0000000000000000-0-"
    "0000000000000000-00000000"
)

ConfigHash = str | int


class SyncState(BaseMaxObject):
    chats_sync: int = -1
    contacts_sync: int = -1
    drafts_sync: int = -1
    presence_sync: int = -1
    chats_count: int | None = None
    config_hash: ConfigHash = DEFAULT_CONFIG_HASH


class SessionInfo(BaseMaxObject):
    session_id: str | None
    token: str | None
    device_id: str | None
    phone: str | None
    mt_instance_id: str = ""
    sync: SyncState = Field(default_factory=SyncState)

    user_agent_config: str | None = None

    def to_string(self) -> str:
        return self.model_dump_json()


    @classmethod
    def from_string(cls: type[Self], string: str) -> Self:
        return cls.model_validate_json(string)

    @model_validator(mode="before")
    @classmethod
    def validate_sync(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "sync" in data:
                sync = data["sync"]
                if isinstance(sync, str):
                    data["sync"] = json.loads(sync)
        return data

@dataclass(frozen=True)
class SessionKey:
    session_id: str | None
    session_name: str
    device_type: DeviceType
    session_value: str | None
    phone: str | None
    device_id: str | None
    token: str | None

class SyncOverrides(BaseMaxObject):
    chats_sync: int | None = None
    contacts_sync: int | None = None
    drafts_sync: int | None = None
    presence_sync: int | None = None
    config_hash: ConfigHash | None = None

    chats_count: int | None = None


    def resolve(self, saved: SyncState) -> SyncState:
        return SyncState(
            chats_sync=(self.chats_sync if self.chats_sync is not None else saved.chats_sync),
            contacts_sync=(
                self.contacts_sync if self.contacts_sync is not None else saved.contacts_sync
            ),
            drafts_sync=(self.drafts_sync if self.drafts_sync is not None else saved.drafts_sync),
            presence_sync=(
                self.presence_sync if self.presence_sync is not None else saved.presence_sync
            ),
            config_hash=(self.config_hash if self.config_hash is not None else saved.config_hash),
            chats_count=self.chats_count or saved.chats_count,
        )


class Session(BaseMaxObject):
    id: int | str | None = None
    device_id: str | None = None
    current: bool | None = None
    user_agent: str | None = None
    app_version: str | None = None
    device_name: str | None = None
    device_type: str | None = None
    platform: str | None = None
    ip: str | None = None
    location: str | None = None
    created: int | None = None
    updated: int | None = None
    last_activity: int | None = None
    options: dict[str, Any] | list[Any] | None = None
    time: int | None = None
    info: str | None = None
