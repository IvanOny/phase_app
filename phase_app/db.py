from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "sql" / "schema_sqlite.sql"


def get_connection(db_path: str = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(conn: sqlite3.Connection, *, force: bool = False) -> None:
    has_phases = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='phases'"
    ).fetchone()
    if has_phases and not force:
        return
    if force:
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        for row in tables:
            name = row[0]
            if not name.startswith("sqlite_"):
                conn.execute(f"DROP TABLE IF EXISTS {name}")

    schema = SCHEMA_PATH.read_text()
    conn.executescript(schema)
    conn.commit()


def seed_minimal_bench_data(conn: sqlite3.Connection) -> dict[str, int]:
    phase = conn.execute(
        "SELECT phase_id FROM phases WHERE phase_type='bench' AND start_date='2026-01-01' AND end_date='2026-03-31'"
    ).fetchone()
    if phase is None:
        phase_id = conn.execute(
            """
            INSERT INTO phases (phase_type, start_date, end_date, name)
            VALUES ('bench', '2026-01-01', '2026-03-31', 'Q1 Bench Focus')
            """
        ).lastrowid
    else:
        phase_id = phase["phase_id"]

    exercise = conn.execute(
        "SELECT exercise_id FROM exercises WHERE exercise_name='Barbell Bench Press'"
    ).fetchone()
    if exercise is None:
        exercise_id = conn.execute(
            """
            INSERT INTO exercises (exercise_name, is_barbell_bench_press)
            VALUES ('Barbell Bench Press', 1)
            """
        ).lastrowid
    else:
        exercise_id = exercise["exercise_id"]

    conn.commit()
    return {"phase_id": phase_id, "exercise_id": exercise_id}
