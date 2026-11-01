import asyncio
import logging
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from pyromax.exceptions import MapperApiError, NeedReloginMapperError
from pyromax.mapping.envelope.v11.LifecycleManager import LifecycleManager
from pyromax.mapping.envelope.v11.constants import ErrorCode
from pyromax.mapping.envelope.v11.mixins.auth import AuthMixin
from pyromax.models import SyncOverrides, SyncState


class ReloginTest(unittest.IsolatedAsyncioTestCase):
    async def test_task_group_preserves_need_relogin_error(self) -> None:
        manager = LifecycleManager(SimpleNamespace())  # type: ignore[arg-type]
        error = NeedReloginMapperError("token rejected")

        async def connect() -> None:
            raise error

        with self.assertRaises(NeedReloginMapperError) as raised:
            await manager._observe_task(connect())

        self.assertIs(raised.exception, error)

    async def test_authorize_propagates_need_relogin_error(self) -> None:
        error = NeedReloginMapperError("token rejected")

        class Mapper:
            logged = True

            def __init__(self) -> None:
                self.connect_calls = 0
                self.auth_calls = 0

            async def connect(self) -> None:
                self.connect_calls += 1

            async def close(self, _exception: Exception | None = None) -> None:
                return None

            async def _send_user_agent(self) -> None:
                return None

            async def _send_auth_token(self) -> None:
                self.auth_calls += 1
                raise error

        mapper = Mapper()
        manager = LifecycleManager(mapper)  # type: ignore[arg-type]

        with self.assertRaises(NeedReloginMapperError) as raised:
            await manager._authorize()

        self.assertIs(raised.exception, error)
        self.assertEqual(manager.get_generation(), 1)
        self.assertEqual(mapper.connect_calls, 1)
        self.assertEqual(mapper.auth_calls, 1)

    async def test_disabled_relogin_stops_lifecycle(self) -> None:
        error = NeedReloginMapperError("token rejected")

        mapper = SimpleNamespace(
            extra_config=SimpleNamespace(
                relogin=False,
                reconnect=True,
            ),
        )
        manager = LifecycleManager(mapper)  # type: ignore[arg-type]
        manager._running = True
        manager._authorize = AsyncMock(  # type: ignore[method-assign]
            side_effect=error
        )
        manager._handle_disconnect = AsyncMock()  # type: ignore[method-assign]

        with self.assertRaises(NeedReloginMapperError) as raised:
            await manager._manage_lifecycle()

        self.assertIs(raised.exception, error)
        manager._handle_disconnect.assert_awaited_once_with(error)
        self.assertFalse(manager._running)

    async def test_enabled_relogin_retries_authorization(self) -> None:
        mapper = SimpleNamespace(
            extra_config=SimpleNamespace(relogin=True, reconnect=True),
        )
        manager = LifecycleManager(mapper)  # type: ignore[arg-type]
        error = NeedReloginMapperError("token rejected")
        manager._running = True
        manager._authorize = AsyncMock(  # type: ignore[method-assign]
            side_effect=[error, None]
        )
        manager._handle_disconnect = AsyncMock()  # type: ignore[method-assign]

        task = asyncio.create_task(manager._manage_lifecycle())
        try:
            await asyncio.wait_for(manager._ready.wait(), timeout=1)
        finally:
            manager._running = False
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

        self.assertEqual(manager._authorize.await_count, 2)
        manager._handle_disconnect.assert_awaited_once_with(error)

    async def test_invalid_token_cleanup_respects_relogin_setting(self) -> None:
        for relogin in (False, True):
            with self.subTest(relogin=relogin):
                api_error = MapperApiError("login failed")
                api_error.error = ErrorCode.LOGIN_TOKEN
                api_error.message = "FAIL_LOGIN_TOKEN"

                storage = SimpleNamespace(delete_session=AsyncMock())
                max_api = SimpleNamespace(
                    session=SimpleNamespace(sync=SyncState()),
                    session_storage=storage,
                    session_key="session-key",
                    token="token",
                )

                class AuthTarget:
                    token = "token"
                    logged = True
                    keep_alive_interactive = True
                    extra_config = SimpleNamespace(
                        relogin=relogin,
                        sync=SyncOverrides(),
                    )
                    _logger = logging.getLogger("ReloginTest")

                    def __init__(self) -> None:
                        self.max_api = max_api

                    async def send_raw(self, **kwargs: object) -> None:
                        raise api_error

                target = AuthTarget()

                with self.assertRaisesRegex(
                    NeedReloginMapperError,
                    "MAX rejected the login token.*FAIL_LOGIN_TOKEN",
                ):
                    await AuthMixin._send_auth_token(  # type: ignore[arg-type]
                        target,
                        "token",
                    )

                if relogin:
                    storage.delete_session.assert_awaited_once_with("session-key")
                    self.assertIsNone(target.token)
                    self.assertIsNone(max_api.token)
                else:
                    storage.delete_session.assert_not_awaited()
                    self.assertEqual(target.token, "token")
                    self.assertEqual(max_api.token, "token")
