from __future__ import annotations

from abc import abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from .base import BaseInteractor


@dataclass(frozen=True, slots=True)
class PasswordRequest:
    """Context supplied when a two-factor password is requested."""

    track_id: str
    phone: str | None = None


@dataclass(slots=True)
class AuthCallbacks:
    """Optional overrides for the standard authentication interaction."""

    qr_url: Callable[[str], Awaitable[None]] | None = None
    sms_code: Callable[[str], Awaitable[str | int]] | None = None
    password: Callable[[PasswordRequest], Awaitable[str]] | None = None


class AuthInteractor(BaseInteractor):
    """Interaction contract required by the built-in authentication flow."""

    @abstractmethod
    async def show_qr(self, url: str) -> None: ...

    @abstractmethod
    async def request_sms_code(self, phone: str) -> str: ...

    @abstractmethod
    async def request_password(self, request: PasswordRequest) -> str: ...

