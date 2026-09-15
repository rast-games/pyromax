from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from ..models import SessionInfo, SessionKey

if TYPE_CHECKING:
    from ..core import MaxApi


class BaseSessionStorage(ABC):
    async def save_session(
        self, session_info: SessionInfo, session_key: SessionKey
    ) -> None: ...
    async def load_session(self, session_key: SessionKey) -> SessionInfo | None: ...
    async def update_session(
        self, session_key: SessionKey, session_info: SessionInfo
    ) -> None: ...
    async def delete_session(self, session_key: SessionKey) -> None: ...
    async def close(self) -> None: ...
