from __future__ import annotations

from typing import Any

import psycopg2.extensions


def get_bench_top_set_e1rm(conn: psycopg2.extensions.connection, session_id: int) -> dict[str, Any] | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT s.session_id, s.phase_id, s.session_date,
                   es.exercise_set_id,
                   es.reps,
                   es.load_kg,
                   ROUND((es.load_kg * (1 + es.reps / 30.0))::numeric, 2) AS top_set_e1rm_kg
            FROM sessions s
            JOIN session_exercises se ON se.session_id = s.session_id
            JOIN exercises e ON e.exercise_id = se.exercise_id
            JOIN exercise_sets es ON es.session_exercise_id = se.session_exercise_id
            WHERE s.session_id = %s
              AND e.is_barbell_bench_press = 1
              AND es.is_top_set = 1
            ORDER BY es.load_kg DESC, es.reps DESC, es.exercise_set_id DESC
            LIMIT 1
            """,
            (session_id,),
        )
        row = cur.fetchone()

    if row is None:
        return None

    return {
        "sessionId": row["session_id"],
        "phaseId": row["phase_id"],
        "sessionDate": row["session_date"],
        "topSetExerciseSetId": row["exercise_set_id"],
        "topSetReps": row["reps"],
        "topSetLoadKg": row["load_kg"],
        "topSetE1rmKg": float(row["top_set_e1rm_kg"]),
        "aggregationVersion": None,
        "source": "live",
    }


def get_bench_volume(conn: psycopg2.extensions.connection, session_id: int) -> dict[str, Any] | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT s.session_id, s.phase_id, s.session_date,
                   ROUND(COALESCE(SUM(es.load_kg * es.reps), 0)::numeric, 2) AS bench_volume_kg_reps
            FROM sessions s
            JOIN session_exercises se ON se.session_id = s.session_id
            JOIN exercises e ON e.exercise_id = se.exercise_id
            JOIN exercise_sets es ON es.session_exercise_id = se.session_exercise_id
            WHERE s.session_id = %s
              AND e.is_barbell_bench_press = 1
              AND es.is_working_set = 1
            GROUP BY s.session_id, s.phase_id, s.session_date
            """,
            (session_id,),
        )
        row = cur.fetchone()

    if row is None:
        return None

    return {
        "sessionId": row["session_id"],
        "phaseId": row["phase_id"],
        "sessionDate": row["session_date"],
        "benchVolumeKgReps": float(row["bench_volume_kg_reps"]),
        "aggregationVersion": None,
        "source": "live",
    }
