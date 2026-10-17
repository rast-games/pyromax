import asyncio
import logging
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from pyromax.exceptions import MapperApiError, NeedReloginMapperError
from pyromax.mapping.envelope.v11.LifecycleManager import LifecycleManager
from pyromax.mapping.envelope.v11.constants import ErrorCode
from pyromax.mapping.envelope.v11.mixins.auth import AuthMixin
from pyromax.models import SyncOverrides, SyncState


class ReloginTest(unittest.IsolatedAsyncioTestCase):
    async def test_task_group_preserves_need_relogin_error(self) -> None:
        manager = LifecycleManager(SimpleNamespace())  # type: ignore[arg-type]
        error = NeedReloginMapperError("token rejected")

        async def observe() -> None:
            await asyncio.Event().wait()

        async def connect() -> None:
            raise error

        with self.assertRaises(NeedReloginMapperError) as raised:
            await manager._observe_task(observe, connect)

        self.assertIs(raised.exception, error)

    async def test_disabled_relogin_reconnects_without_authorization(self) -> None:
        error = NeedReloginMapperError("token rejected")

        class Mapper:
            logged = True
            token = "token"
            user_agent = object()
            extra_config = SimpleNamespace(relogin=False)
            max_api = SimpleNamespace(shutdown_requested=False)

            def __init__(self) -> None:
                self._authorized = asyncio.Event()
                self._protocol_connected = asyncio.Event()
                self.auth_calls = 0
                self.user_agent_calls = 0

            async def connect(self) -> None:
                return None

            async def _auth(self, **kwargs: object) -> None:
                self.auth_calls += 1
                raise error

            async def _send_only_user_agent(self, **kwargs: object) -> None:
                self.user_agent_calls += 1

            async def close(self, _exception: Exception | None = None) -> None:
                return None

        mapper = Mapper()
        manager = LifecycleManager(mapper)  # type: ignore[arg-type]
        backoff = Mock()

        with self.assertRaises(NeedReloginMapperError) as raised:
            await manager._establish_connection(  # type: ignore[arg-type]
                backoff,
                close_firstly=False,
            )

        self.assertIs(raised.exception, error)
        self.assertFalse(mapper._protocol_connected.is_set())
        self.assertFalse(mapper._authorized.is_set())
        self.assertEqual(mapper.auth_calls, 1)
        self.assertTrue(manager._only_send_user_agent)

        await manager._establish_connection(  # type: ignore[arg-type]
            backoff,
            close_firstly=False,
        )

        self.assertTrue(mapper._protocol_connected.is_set())
        self.assertEqual(mapper.auth_calls, 1)
        self.assertEqual(mapper.user_agent_calls, 1)

    async def test_disabled_relogin_emits_auth_error_before_retry(self) -> None:
        emitted = []
        error = NeedReloginMapperError("token rejected")

        class Api:
            async def _emit_disconnect(self, event: object) -> None:
                emitted.append(event)

        mapper = SimpleNamespace(
            extra_config=SimpleNamespace(
                relogin=False,
                reconnect=True,
                reconnect_delay=1.5,
            ),
            max_api=Api(),
            close=AsyncMock(),
        )
        manager = LifecycleManager(mapper)  # type: ignore[arg-type]
        manager._authorize = AsyncMock(  # type: ignore[method-assign]
            side_effect=[error, None]
        )
        backoff = Mock()

        with unittest.mock.patch(
            "pyromax.mapping.envelope.v11.LifecycleManager.asyncio.sleep",
            new=AsyncMock(),
        ) as sleep:
            await manager._authorize_cycle(None, backoff)

        self.assertEqual(manager._authorize.await_count, 2)
        self.assertEqual(len(emitted), 1)
        self.assertIs(emitted[0].exception, error)
        self.assertTrue(emitted[0].reconnect)
        self.assertEqual(emitted[0].delay, 1.5)
        sleep.assert_awaited_once_with(1.5)

    async def test_enabled_relogin_retries_authorization(self) -> None:
        mapper = SimpleNamespace(extra_config=SimpleNamespace(relogin=True))
        manager = LifecycleManager(mapper)  # type: ignore[arg-type]
        error = NeedReloginMapperError("token rejected")
        manager._authorize = AsyncMock(  # type: ignore[method-assign]
            side_effect=[error, None]
        )
        backoff = Mock()

        await manager._authorize_cycle(None, backoff)

        self.assertEqual(manager._authorize.await_count, 2)
        backoff.reset.assert_called_once_with()

    async def test_enabled_relogin_marks_full_login_and_reraises(self) -> None:
        error = NeedReloginMapperError("token rejected")

        class Mapper:
            logged = True
            token = "token"
            user_agent = object()
            extra_config = SimpleNamespace(relogin=True)
            max_api = SimpleNamespace(shutdown_requested=False)
            _authorized = asyncio.Event()

            async def connect(self) -> None:
                return None

            async def _auth(self, **kwargs: object) -> None:
                raise error

        manager = LifecycleManager(Mapper())  # type: ignore[arg-type]

        with self.assertRaises(NeedReloginMapperError) as raised:
            await manager._connect(Mock())  # type: ignore[arg-type]

        self.assertIs(raised.exception, error)
        self.assertTrue(manager._need_login)

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

                self.assertFalse(target.logged)
                if relogin:
                    storage.delete_session.assert_awaited_once_with("session-key")
                    self.assertIsNone(target.token)
                    self.assertIsNone(max_api.token)
                else:
                    storage.delete_session.assert_not_awaited()
                    self.assertEqual(target.token, "token")
                    self.assertEqual(max_api.token, "token")
