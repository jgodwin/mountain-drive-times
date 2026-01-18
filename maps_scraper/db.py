import sqlite3
from pathlib import Path
from typing import Iterable


def connect(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS travel_times (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            origin TEXT NOT NULL,
            destination TEXT NOT NULL,
            duration_seconds INTEGER NOT NULL,
            distance_meters INTEGER,
            observed_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_travel_times_lookup
        ON travel_times (destination, observed_at)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_travel_times_origin_dest_time
        ON travel_times (origin, destination, observed_at)
        """
    )
    conn.commit()


def insert_travel_times(
    conn: sqlite3.Connection,
    rows: Iterable[tuple[str, str, int, int | None, str]],
) -> None:
    conn.executemany(
        """
        INSERT INTO travel_times (
            origin, destination, duration_seconds, distance_meters, observed_at
        ) VALUES (?, ?, ?, ?, ?)
        """,
        list(rows),
    )
    conn.commit()
