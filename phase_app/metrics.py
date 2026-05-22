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
              AND s.session_type = 'heavy_bench'
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
                   es.load_kg, es.reps,
                   s.session_date
            FROM sessions s
            JOIN session_exercises se ON se.session_id = s.session_id
            JOIN exercises e ON e.exercise_id = se.exercise_id
            JOIN exercise_sets es ON es.session_exercise_id = se.session_exercise_id
            WHERE s.phase_id = %s AND s.session_type = 'heavy_bench'
              AND e.is_barbell_bench_press = 1 AND es.is_top_set = 1
            ORDER BY s.session_date
            """,
            (phase_id,),
        )
        e1rm_rows = cur.fetchall()
        peak_e1rm = None
        peak_load_kg = None
        peak_reps = None
        start_e1rm = None
        start_load_kg = None
        start_reps = None
        if e1rm_rows:
            peak_row = max(e1rm_rows, key=lambda r: r["e1rm"])
            peak_e1rm = float(peak_row["e1rm"])
            peak_load_kg = float(peak_row["load_kg"])
            peak_reps = int(peak_row["reps"])
            first_row = e1rm_rows[0]
            start_e1rm = float(first_row["e1rm"])
            start_load_kg = float(first_row["load_kg"])
            start_reps = int(first_row["reps"])
        lowest_e1rm = float(min(r["e1rm"] for r in e1rm_rows)) if e1rm_rows else None
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
        "peakTopSetLoadKg": peak_load_kg,
        "peakTopSetReps": peak_reps,
        "startE1rmKg": start_e1rm,
        "startTopSetLoadKg": start_load_kg,
        "startTopSetReps": start_reps,
        "lowestE1rmKg": lowest_e1rm,
        "latestE1rmKg": latest_e1rm,
        "totalBenchVolumeKgReps": total_volume,
    }


def get_phase_exercise_volumes(conn: psycopg2.extensions.connection, phase_id: int) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT e.exercise_id, e.exercise_name, e.is_bodyweight, e.is_barbell_bench_press,
                   s.session_id, s.session_date,
                   es.set_number, es.load_kg, es.reps,
                   es.is_working_set, es.is_top_set
            FROM sessions s
            JOIN session_exercises se ON se.session_id = s.session_id
            JOIN exercises e ON e.exercise_id = se.exercise_id
            JOIN exercise_sets es ON es.session_exercise_id = se.session_exercise_id
            WHERE s.phase_id = %s
            ORDER BY e.exercise_name, s.session_date, es.set_number
            """,
            (phase_id,),
        )
        rows = cur.fetchall()

    exercises: dict[int, dict[str, Any]] = {}
    for row in rows:
        eid = row["exercise_id"]
        if eid not in exercises:
            exercises[eid] = {
                "exerciseId": eid,
                "exerciseName": row["exercise_name"],
                "isBodyweight": bool(row["is_bodyweight"]),
                "isBarbellBenchPress": bool(row["is_barbell_bench_press"]),
                "sessions": {},
            }
        sid = row["session_id"]
        if sid not in exercises[eid]["sessions"]:
            exercises[eid]["sessions"][sid] = {
                "sessionId": sid,
                "sessionDate": str(row["session_date"]),
                "volumeKgReps": 0.0,
                "topLoadKg": 0.0,
                "sets": [],
            }
        sess = exercises[eid]["sessions"][sid]
        if row["is_working_set"] or row["is_top_set"]:
            load = float(row["load_kg"])
            reps = int(row["reps"])
            sess["volumeKgReps"] = round(sess["volumeKgReps"] + load * reps, 2)
            if load > sess["topLoadKg"]:
                sess["topLoadKg"] = load
            sess["sets"].append({"loadKg": load, "reps": reps})

    return [
        {
            "exerciseId": ex["exerciseId"],
            "exerciseName": ex["exerciseName"],
            "isBodyweight": ex["isBodyweight"],
            "isBarbellBenchPress": ex["isBarbellBenchPress"],
            "sessions": sorted(ex["sessions"].values(), key=lambda s: s["sessionDate"]),
        }
        for ex in exercises.values()
    ]


def get_phase_maintenance(conn: psycopg2.extensions.connection, phase_id: int) -> dict[str, Any]:
    with conn.cursor() as cur:
        # Bodyweight top sets per session (pull-ups focus)
        cur.execute(
            """
            SELECT s.session_id, s.session_date, e.exercise_name,
                   MAX(es.reps) AS top_reps
            FROM sessions s
            JOIN session_exercises se ON se.session_id = s.session_id
            JOIN exercises e ON e.exercise_id = se.exercise_id
            JOIN exercise_sets es ON es.session_exercise_id = se.session_exercise_id
            WHERE s.phase_id = %s
              AND e.is_bodyweight = 1
              AND es.is_top_set = 1
            GROUP BY s.session_id, s.session_date, e.exercise_name
            ORDER BY s.session_date
            """,
            (phase_id,),
        )
        bw_rows = cur.fetchall()

        # Run sessions (no exercises needed)
        cur.execute(
            "SELECT session_id, session_date FROM sessions "
            "WHERE phase_id = %s AND session_type = 'run' ORDER BY session_date",
            (phase_id,),
        )
        run_rows = cur.fetchall()

        # Barbell bench press top sets per session
        cur.execute(
            """
            SELECT s.session_id, s.session_date, es.load_kg, es.reps,
                   ROUND((es.load_kg * (1 + es.reps / 30.0))::numeric, 2) AS e1rm_kg
            FROM sessions s
            JOIN session_exercises se ON se.session_id = s.session_id
            JOIN exercises e ON e.exercise_id = se.exercise_id
            JOIN exercise_sets es ON es.session_exercise_id = se.session_exercise_id
            WHERE s.phase_id = %s
              AND s.session_type = 'heavy_bench'
              AND e.is_barbell_bench_press = 1
              AND es.is_top_set = 1
            ORDER BY s.session_date, es.load_kg DESC
            """,
            (phase_id,),
        )
        bench_rows = cur.fetchall()

    # One entry per session, highest e1rm wins
    bench_by_session: dict[int, dict[str, Any]] = {}
    for r in bench_rows:
        sid = r["session_id"]
        e1rm = float(r["e1rm_kg"])
        if sid not in bench_by_session or e1rm > bench_by_session[sid]["e1rmKg"]:
            bench_by_session[sid] = {
                "sessionId": sid,
                "sessionDate": str(r["session_date"]),
                "loadKg": float(r["load_kg"]),
                "reps": int(r["reps"]),
                "e1rmKg": e1rm,
            }

    return {
        "pullups": [
            {
                "sessionId": r["session_id"],
                "sessionDate": str(r["session_date"]),
                "exerciseName": r["exercise_name"],
                "topReps": int(r["top_reps"]),
            }
            for r in bw_rows
        ],
        "run": [
            {"sessionId": r["session_id"], "sessionDate": str(r["session_date"])}
            for r in run_rows
        ],
        "bench": sorted(bench_by_session.values(), key=lambda x: x["sessionDate"]),
    }


def get_session_bench_metrics(conn: psycopg2.extensions.connection, phase_id: int) -> dict[str, Any]:
    """Return bench e1rm and volume for all sessions in a phase — single round-trip."""
    with conn.cursor() as cur:
        # Best top-set e1rm per session (highest load among is_top_set=1 bench sets)
        cur.execute(
            """
            SELECT DISTINCT ON (s.session_id)
                s.session_id,
                es.exercise_set_id,
                es.reps,
                es.load_kg,
                ROUND((es.load_kg * (1 + es.reps / 30.0))::numeric, 2) AS e1rm_kg
            FROM sessions s
            JOIN session_exercises se ON se.session_id = s.session_id
            JOIN exercises e  ON e.exercise_id  = se.exercise_id
            JOIN exercise_sets es ON es.session_exercise_id = se.session_exercise_id
            WHERE s.phase_id = %s
              AND s.session_type = 'heavy_bench'
              AND e.is_barbell_bench_press = 1
              AND es.is_top_set = 1
            ORDER BY s.session_id, es.load_kg DESC, es.reps DESC, es.exercise_set_id DESC
            """,
            (phase_id,),
        )
        e1rm_rows = cur.fetchall()

        # Total working volume per session
        cur.execute(
            """
            SELECT s.session_id,
                   ROUND(COALESCE(SUM(es.load_kg * es.reps), 0)::numeric, 2) AS bench_volume
            FROM sessions s
            JOIN session_exercises se ON se.session_id = s.session_id
            JOIN exercises e  ON e.exercise_id  = se.exercise_id
            JOIN exercise_sets es ON es.session_exercise_id = se.session_exercise_id
            WHERE s.phase_id = %s
              AND e.is_barbell_bench_press = 1
              AND es.is_working_set = 1
            GROUP BY s.session_id
            """,
            (phase_id,),
        )
        vol_rows = cur.fetchall()

    e1rm_map = {}
    for r in e1rm_rows:
        e1rm_map[str(r["session_id"])] = {
            "topSetExerciseSetId": r["exercise_set_id"],
            "topSetReps": int(r["reps"]),
            "topSetLoadKg": float(r["load_kg"]),
            "topSetE1rmKg": float(r["e1rm_kg"]),
        }

    vol_map = {}
    for r in vol_rows:
        vol_map[str(r["session_id"])] = {
            "benchVolumeKgReps": float(r["bench_volume"]),
        }

    return {"e1rm": e1rm_map, "volume": vol_map}


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
