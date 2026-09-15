from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qsl

import aiosqlite as asq

from .base import BaseSessionStorage
from ..models.Session import SessionInfo, DEFAULT_CONFIG_HASH, SessionKey

if TYPE_CHECKING:
    from .. import MaxApi


SESSION_COLUMNS = """
    session_id,
    session_name,
    session_value,
    device_type
"""


class AioSqLiteSessionStorage(BaseSessionStorage):
    def __init__(self, work_dir: str, db_name: str | None = "session.db") -> None:
        if db_name is None:
            db_name = "session.db"
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = str(self.work_dir / db_name)
        self.conn: asq.Connection | None = None
        self._logger = logging.getLogger("AioSlqLiteSessionStorage")
        self._logger.debug("Session storage initialized db=%s", self.db_path)

    async def _get_connection(self) -> asq.Connection:
        if self.conn is None:
            self._logger.debug("opening session database db=%s", self.db_path)
            self.conn = await asq.connect(self.db_path)
            self.conn.row_factory = asq.Row
            await self._initialize_db(self.conn)
        return self.conn

    async def _initialize_db(self, conn: asq.Connection) -> None:
        self._logger.debug("Initializing session database")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id NOT NULL PRIMARY KEY,
                session_name NOT NULL,
                session_value NOT NULL,
                device_type TEXT NOT NULL
            )
            """)
        await self._ensure_column(conn, "session_id", "session_id NOT NULL PRIMARY KEY")
        await self._ensure_column(conn, "session_name", "session_name NOT NULL")
        await self._ensure_column(conn, "session_value", "session_value NOT NULL")
        await self._ensure_column(conn, "device_type", "device_type NOT NULL")

        await conn.commit()

    async def _ensure_column(
        self,
        conn: asq.Connection,
        name: str,
        definition: str,
    ) -> None:
        async with conn.execute("PRAGMA table_info(sessions)") as cursor:
            columns = {row["name"] for row in await cursor.fetchall()}

        if name not in columns:
            await conn.execute(f"ALTER TABLE sessions ADD COLUMN {name} {definition}")

    async def save_session(
        self, session_info: SessionInfo, session_key: SessionKey
    ) -> None:
        session_id = session_key.session_id
        session_name = session_key.session_name
        serialized_session_info = session_info.to_string()
        conn = await self._get_connection()
        self._logger.debug(
            "Saving session device_id=%s phone_set=%s mt_instance_id_set=%s",
            session_info.device_id,
            bool(session_info.phone),
            bool(session_info.mt_instance_id),
        )
        await conn.execute(
            f"""
            INSERT OR REPLACE INTO sessions (
                {SESSION_COLUMNS}
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                session_id,
                session_name,
                serialized_session_info,
                session_key.device_type,
            ),
        )
        await conn.commit()
        self._logger.info("Session saved")

    def _validate_session_info_by_session_key(
        self, session_key: SessionKey, session_infos: list[SessionInfo] | list[asq.Row]
    ) -> list[SessionInfo] | None:

        filters = []

        if session_key.phone:
            filters.append(("phone", session_key.phone))
        if session_key.device_id is not None:
            filters.append(
                (
                    "device_id",
                    session_key.device_id,
                )
            )
        if session_key.token:
            filters.append(("token", session_key.token))

        sessions = []
        for session_info in session_infos:
            if isinstance(session_info, asq.Row):
                sessions.append(
                    self._session_value_to_session(session_info["session_value"])
                )
            else:
                sessions.append(session_info)

        if not filters:
            return sessions

        filtered_sessions = []
        for session_info in sessions:
            if all(getattr(session_info, key, None) == value for key, value in filters):
                filtered_sessions.append(session_info)

        if not filtered_sessions:
            return None

        return filtered_sessions

    def _prepare_session_spicies_by_session_key(
        self,
        session_key: SessionKey,
        sql_req: str = "",
        values: list[Any] | None = None,
        session_info: SessionInfo | None = None,
    ) -> tuple[str, list[Any]]:
        if values is None:
            values = []
        params = []

        if session_key.session_id is not None:
            params.append("session_id")
            values.append(session_key.session_id)
        if session_key.session_name is not None:
            params.append("session_name")
            values.append(session_key.session_name)
        if session_key.device_type is not None:
            params.append("device_type")
            values.append(str(session_key.device_type))
        if session_info is not None:
            params.append("session_value")
            values.append(session_info.to_string())

        if params:
            first_param = params[0]
            params = params[1:]
            sql_req += f"""
            WHERE {first_param}=?
            """
            for param in params:
                sql_req += f"""
                AND {param}=?
                """

            return sql_req, values
        else:
            return sql_req, []

    async def load_session(self, session_key: SessionKey) -> SessionInfo | None:
        conn = await self._get_connection()
        sql_req = f"""
            SELECT {SESSION_COLUMNS}
            FROM sessions
            """

        sql_req, values = self._prepare_session_spicies_by_session_key(
            session_key, sql_req
        )

        self._logger.debug("loading first session")
        async with conn.execute(
            sql_req,
            values,
        ) as cursor:
            rows = await cursor.fetchall()
            filtered_rows = self._validate_session_info_by_session_key(
                session_key, rows
            )

            if filtered_rows:
                session_info = filtered_rows[0]
            else:
                self._logger.debug("Session not found")
                return None

        self._logger.debug(
            "session loaded device_id=%s phone_set=%s",
            session_info.device_id,
            bool(session_info.phone),
        )
        return session_info

    async def update_session(
        self, session_key: SessionKey, session_info: SessionInfo
    ) -> None:
        self._logger.debug("Updating session session_id=%s", session_info.session_id)
        new_session_id = session_info.session_id
        if new_session_id is None:
            self._logger.warning(
                "Trying to update session without session_id, session_info=%s, session_key=%s",
                session_info,
                session_key,
            )
            return

        serialized_session = session_info.to_string()
        conn = await self._get_connection()

        if (
            session_key.session_id is not None
            and session_key.session_id != new_session_id
        ):

            sql_req = """
                UPDATE sessions
                SET session_id=?, session_name=?, session_value=?, device_type=?
                """
            values = [
                new_session_id,
                session_key.session_name,
                serialized_session,
                session_key.device_type,
            ]

            sql_req, values = self._prepare_session_spicies_by_session_key(
                session_key, sql_req, values
            )
            cursor = await conn.execute(sql_req, values)

            if cursor.rowcount == 0:
                self._logger.warning(
                    "Session to rename was not found old_session_id=%s",
                    session_key.session_id,
                )
        else:
            await conn.execute(
                """
                INSERT INTO sessions (
                    session_id, session_name, session_value, device_type
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    session_name=excluded.session_name,
                    session_value=excluded.session_value,
                    device_type=excluded.device_type
                """,
                (
                    new_session_id,
                    session_key.session_name,
                    serialized_session,
                    session_key.device_type,
                ),
            )

        await conn.commit()
        self._logger.debug("Session updated")

    async def delete_session(self, session_key: SessionKey) -> None:
        session_info = await self.load_session(session_key)
        if session_info is None:
            self._logger.warning("Deleting session not found")
            return None

        conn = await self._get_connection()
        sql_req = """
            DELETE FROM sessions
            """

        sql_req, values = self._prepare_session_spicies_by_session_key(
            session_key, sql_req, session_info=session_info
        )

        self._logger.warning("Deleting session token_set=%s", bool(session_info.token))
        await conn.execute(
            sql_req,
            values,
        )
        await conn.commit()
        self._logger.info("Session deleted")

    async def delete_all_sessions(self) -> None:
        conn = await self._get_connection()
        self._logger.warning("Deleting all sessions")
        await conn.execute("""
            DELETE FROM sessions
            """)
        await conn.commit()
        self._logger.info("All sessions deleted")

    async def close(self) -> None:
        if self.conn is not None:
            self._logger.debug("Closing session database")
            await self.conn.close()
            self.conn = None

    def _session_value_to_session(self, session_value: str) -> SessionInfo:
        return SessionInfo.from_string(session_value)
