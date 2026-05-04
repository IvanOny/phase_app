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


def get_phase_summary(conn: psycopg2.extensions.connection, phase_id: int) -> dict[str, Any] | None:
    with conn.cursor() as cur:
        cur.execute("SELECT phase_id FROM phases WHERE phase_id = %s", (phase_id,))
        if cur.fetchone() is None:
            return None

        cur.execute(
            """
            SELECT COUNT(DISTINCT s.session_id) AS session_count,
                   AVG(s.elite_hrv_readiness) AS avg_hrv
            FROM sessions s
            WHERE s.phase_id = %s
            """,
            (phase_id,),
        )
        row = cur.fetchone()
        session_count = row["session_count"] or 0
        avg_hrv = float(row["avg_hrv"]) if row["avg_hrv"] is not None else None

        cur.execute(
            """
            SELECT ROUND((es.load_kg * (1 + es.reps / 30.0))::numeric, 2) AS e1rm,
                   s.session_date
            FROM sessions s
            JOIN session_exercises se ON se.session_id = s.session_id
            JOIN exercises e ON e.exercise_id = se.exercise_id
            JOIN exercise_sets es ON es.session_exercise_id = se.session_exercise_id
            WHERE s.phase_id = %s AND e.is_barbell_bench_press = 1 AND es.is_top_set = 1
            ORDER BY s.session_date
            """,
            (phase_id,),
        )
        e1rm_rows = cur.fetchall()
        peak_e1rm = float(max(r["e1rm"] for r in e1rm_rows)) if e1rm_rows else None
        latest_e1rm = float(e1rm_rows[-1]["e1rm"]) if e1rm_rows else None

        cur.execute(
            """
            SELECT ROUND(COALESCE(SUM(es.load_kg * es.reps), 0)::numeric, 2) AS total_volume
            FROM sessions s
            JOIN session_exercises se ON se.session_id = s.session_id
            JOIN exercises e ON e.exercise_id = se.exercise_id
            JOIN exercise_sets es ON es.session_exercise_id = se.session_exercise_id
            WHERE s.phase_id = %s AND e.is_barbell_bench_press = 1 AND es.is_working_set = 1
            """,
            (phase_id,),
        )
        vol_row = cur.fetchone()
        total_volume = float(vol_row["total_volume"]) if vol_row else 0.0

    return {
        "phaseId": phase_id,
        "sessionCount": session_count,
        "avgHrv": avg_hrv,
        "peakE1rmKg": peak_e1rm,
        "latestE1rmKg": latest_e1rm,
        "totalBenchVolumeKgReps": total_volume,
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
