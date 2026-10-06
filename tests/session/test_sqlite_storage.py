from pathlib import Path

import pytest

from pyromax.models.Session import SessionInfo, SessionKey
from pyromax.models.enum import DeviceType
from pyromax.session.aiosqlite import AioSqLiteSessionStorage


pytestmark = pytest.mark.integration


def session_key(
    *,
    session_id: str = "session-1",
    phone: str | None = "+79990000000",
    token: str | None = "token-1",
) -> SessionKey:
    return SessionKey(
        session_id=session_id,
        session_name="main",
        device_type=DeviceType.Web,
        session_value=None,
        phone=phone,
        device_id="device-1",
        token=token,
    )


def session_info(
    *, session_id: str = "session-1", token: str = "token-1"
) -> SessionInfo:
    return SessionInfo(
        session_id=session_id,
        token=token,
        device_id="device-1",
        phone="+79990000000",
    )


async def test_sqlite_storage_save_load_update_delete(tmp_path: Path) -> None:
    storage = AioSqLiteSessionStorage(str(tmp_path), "sessions.db")
    key = session_key()
    original = session_info()
    try:
        assert await storage.load_session(key) is None

        await storage.save_session(original, key)
        assert await storage.load_session(key) == original

        updated = session_info(token="token-2")
        await storage.update_session(key, updated)
        lookup = session_key(phone=None, token="token-2")
        assert await storage.load_session(lookup) == updated

        await storage.delete_session(lookup)
        assert await storage.load_session(lookup) is None
    finally:
        await storage.close()


async def test_sqlite_storage_renames_session_and_filters_metadata(tmp_path: Path) -> None:
    storage = AioSqLiteSessionStorage(str(tmp_path), "sessions.db")
    old_key = session_key()
    try:
        await storage.save_session(session_info(), old_key)
        renamed = session_info(session_id="session-2")
        await storage.update_session(old_key, renamed)

        assert await storage.load_session(old_key) is None
        new_key = session_key(session_id="session-2")
        assert await storage.load_session(new_key) == renamed

        wrong_phone = session_key(session_id="session-2", phone="+70000000000")
        assert await storage.load_session(wrong_phone) is None
    finally:
        await storage.close()


async def test_sqlite_storage_delete_all_and_reopen(tmp_path: Path) -> None:
    storage = AioSqLiteSessionStorage(str(tmp_path), "sessions.db")
    key = session_key()
    await storage.save_session(session_info(), key)
    await storage.close()

    reopened = AioSqLiteSessionStorage(str(tmp_path), "sessions.db")
    try:
        assert await reopened.load_session(key) == session_info()
        await reopened.delete_all_sessions()
        assert await reopened.load_session(key) is None
    finally:
        await reopened.close()
