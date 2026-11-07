from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from sqlalchemy import Connection, Engine, create_engine, event


def make_engine(db_path: Path) -> Engine:
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", future=True)

    @event.listens_for(engine, "connect")
    def _on_connect(dbapi_conn: sqlite3.Connection, _record: Any) -> None:
        # Let SQLAlchemy own transactions so DDL (migrations) is transactional too;
        # pysqlite's legacy mode would otherwise auto-commit schema changes.
        dbapi_conn.isolation_level = None
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

    @event.listens_for(engine, "begin")
    def _on_begin(conn: Connection) -> None:
        # IMMEDIATE takes the write lock up front, so concurrent read-then-write
        # transactions queue (busy_timeout) instead of deadlocking with SQLITE_BUSY.
        conn.exec_driver_sql("BEGIN IMMEDIATE")

    return engine
