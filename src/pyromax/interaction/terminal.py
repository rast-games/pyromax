from __future__ import annotations

import asyncio
import getpass
import sys

import qrcode

from ..exceptions import AuthInputRequired
from .auth import AuthCallbacks, AuthInteractor, PasswordRequest


class TerminalAuthInteractor(AuthInteractor):
    """Default auth interaction using callbacks with terminal fallbacks."""

    def __init__(self, callbacks: AuthCallbacks | None = None) -> None:
        self.callbacks = callbacks or AuthCallbacks()

    @property
    def can_prompt(self) -> bool:
        return sys.stdin is not None and sys.stdin.isatty()

    async def show_qr(self, url: str) -> None:
        if self.callbacks.qr_url is not None:
            await self.callbacks.qr_url(url)
            return

        qr = qrcode.QRCode()
        qr.add_data(url)
        qr.make(fit=True)
        qr.print_ascii(invert=True)

    async def request_sms_code(self, phone: str) -> str:
        if self.callbacks.sms_code is not None:
            return str(await self.callbacks.sms_code(phone))
        if not self.can_prompt:
            raise AuthInputRequired(
                "SMS code is required: provide an AuthInteractor or run in a terminal."
            )
        try:
            return await asyncio.to_thread(input, "Write a SMS code: ")
        except EOFError as error:
            raise AuthInputRequired(
                "SMS code is required: provide an AuthInteractor or run in a terminal."
            ) from error

    async def request_password(self, request: PasswordRequest) -> str:
        if self.callbacks.password is not None:
            return await self.callbacks.password(request)
        if not self.can_prompt:
            raise AuthInputRequired(
                "Account has 2FA enabled: pass password=..., provide an "
                "AuthInteractor, or run in a terminal."
            )
        try:
            return await asyncio.to_thread(getpass.getpass, "2FA password: ")
        except EOFError as error:
            raise AuthInputRequired(
                "Account has 2FA enabled: pass password=..., provide an "
                "AuthInteractor, or run in a terminal."
            ) from error
