from __future__ import annotations

import os

import psycopg2
import psycopg2.extras


def get_connection(database_url: str | None = None) -> psycopg2.extensions.connection:
    url = database_url or os.environ["DATABASE_URL"]
    return psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)


def seed_minimal_bench_data(conn: psycopg2.extensions.connection) -> dict[str, int]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT phase_id FROM phases WHERE phase_type='bench' AND start_date='2026-01-01' AND end_date='2026-03-31'"
        )
        phase = cur.fetchone()
        if phase is None:
            cur.execute(
                "INSERT INTO phases (phase_type, start_date, end_date, name) "
                "VALUES ('bench', '2026-01-01', '2026-03-31', 'Q1 Bench Focus') RETURNING phase_id"
            )
            phase_id = cur.fetchone()["phase_id"]
        else:
            phase_id = phase["phase_id"]

        cur.execute("SELECT exercise_id FROM exercises WHERE exercise_name='Barbell Bench Press'")
        exercise = cur.fetchone()
        if exercise is None:
            cur.execute(
                "INSERT INTO exercises (exercise_name, is_barbell_bench_press) "
                "VALUES ('Barbell Bench Press', 1) RETURNING exercise_id"
            )
            exercise_id = cur.fetchone()["exercise_id"]
        else:
            exercise_id = exercise["exercise_id"]

    conn.commit()
    return {"phase_id": phase_id, "exercise_id": exercise_id}
