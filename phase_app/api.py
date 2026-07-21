from __future__ import annotations

import json
import os
import re
import urllib.request
import urllib.error
from datetime import date as _date, datetime, timezone, timedelta
from dataclasses import dataclass
from typing import Any

_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
_LOG_CHAT_ID = os.environ.get("LOG_CHAT_ID", "")


def _tg_log(text: str) -> None:
    if not _LOG_CHAT_ID or not _BOT_TOKEN:
        return
    ts = datetime.now(timezone(timedelta(hours=2))).strftime("%Y-%m-%d %H:%M")
    payload = json.dumps({"chat_id": int(_LOG_CHAT_ID), "text": f"[{ts}]\n{text}"}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{_BOT_TOKEN}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass

import psycopg2
import psycopg2.extensions
import psycopg2.errors


@dataclass
class ApiResponse:
    status: int
    body: dict[str, Any]


class PhaseApi:
    def __init__(self, conn: psycopg2.extensions.connection):
        self.conn = conn

    def _exec(self, sql: str, params: tuple = ()):
        cur = self.conn.cursor()
        cur.execute(sql, params)
        return cur

    def handle(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        query_params: dict[str, str] | None = None,
    ) -> ApiResponse:
        try:
            return self._handle(method, path, body, query_params)
        except Exception as exc:
            try:
                self.conn.rollback()
            except Exception:
                pass
            return ApiResponse(500, {"error": "server_error", "detail": str(exc)})

    def _handle(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        query_params: dict[str, str] | None = None,
    ) -> ApiResponse:
        body = body or {}
        qp = query_params or {}

        if method == "GET" and path == "/v1/phases":
            return self.list_phases()
        if method == "POST" and path == "/v1/phases":
            return self.create_phase(body)
        if method == "PATCH" and re.fullmatch(r"/v1/phases/\d+", path):
            return self.update_phase(int(path.split("/")[3]), body)
        if method == "DELETE" and re.fullmatch(r"/v1/phases/\d+", path):
            return self.delete_phase(int(path.split("/")[3]))

        if method == "GET" and path == "/v1/sessions":
            return self.list_sessions(qp)
        if method == "POST" and path == "/v1/sessions":
            return self.create_session(body)
        if method == "PATCH" and re.fullmatch(r"/v1/sessions/\d+", path):
            return self.update_session(int(path.split("/")[3]), body)
        if method == "DELETE" and re.fullmatch(r"/v1/sessions/\d+", path):
            return self.delete_session(int(path.split("/")[3]))

        # session exercises — more specific patterns before /v1/sessions/\d+
        if method == "POST" and re.fullmatch(r"/v1/sessions/\d+/exercises", path):
            session_id = int(path.split("/")[3])
            return self.create_session_exercise(session_id, body)
        if method == "PATCH" and re.fullmatch(r"/v1/sessions/\d+/exercises/\d+", path):
            parts = path.split("/")
            return self.update_session_exercise(int(parts[3]), int(parts[5]), body)
        if method == "DELETE" and re.fullmatch(r"/v1/sessions/\d+/exercises/\d+", path):
            parts = path.split("/")
            return self.delete_session_exercise(int(parts[3]), int(parts[5]))

        if method == "POST" and re.fullmatch(r"/v1/session-exercises/\d+/sets", path):
            session_exercise_id = int(path.split("/")[3])
            return self.create_exercise_set(session_exercise_id, body)
        if method == "PATCH" and re.fullmatch(r"/v1/session-exercises/\d+/sets/\d+", path):
            parts = path.split("/")
            return self.update_exercise_set(int(parts[3]), int(parts[5]), body)
        if method == "DELETE" and re.fullmatch(r"/v1/session-exercises/\d+/sets/\d+", path):
            parts = path.split("/")
            return self.delete_exercise_set(int(parts[3]), int(parts[5]))

        if method == "GET" and re.fullmatch(r"/v1/sessions/\d+", path):
            return self.get_session(int(path.split("/")[3]))
        if method == "GET" and re.fullmatch(r"/v1/sessions/\d+/exercises", path):
            return self.get_session_exercises(int(path.split("/")[3]))
        if method == "GET" and re.fullmatch(r"/v1/session-exercises/\d+/sets", path):
            return self.get_exercise_sets(int(path.split("/")[3]))

        if method == "GET" and path == "/v1/exercises":
            return self.list_exercises()
        if method == "POST" and path == "/v1/exercises":
            return self.create_exercise(body)
        if method == "PATCH" and re.fullmatch(r"/v1/exercises/\d+", path):
            return self.update_exercise(int(path.split("/")[3]), body)
        if method == "DELETE" and re.fullmatch(r"/v1/exercises/\d+", path):
            return self.delete_exercise(int(path.split("/")[3]))
        if method == "POST" and path == "/v1/exercises/merge":
            return self.merge_exercises(body)

        if method == "GET" and path == "/v1/benchmarks":
            return self.list_benchmarks(qp)
        if method == "POST" and path == "/v1/benchmarks":
            return self.create_benchmark(body)
        if method == "PATCH" and re.fullmatch(r"/v1/benchmarks/\d+", path):
            return self.update_benchmark(int(path.split("/")[3]), body)
        if method == "DELETE" and re.fullmatch(r"/v1/benchmarks/\d+", path):
            return self.delete_benchmark(int(path.split("/")[3]))

        if method == "GET" and re.fullmatch(r"/v1/metrics/sessions/\d+/bench-top-set-e1rm", path):
            return self.get_metric_top_set(int(path.split("/")[4]))
        if method == "GET" and re.fullmatch(r"/v1/metrics/sessions/\d+/bench-volume", path):
            return self.get_metric_bench_volume(int(path.split("/")[4]))
        if method == "GET" and re.fullmatch(r"/v1/metrics/phases/\d+/summary", path):
            return self.get_phase_summary(int(path.split("/")[4]))
        if method == "GET" and re.fullmatch(r"/v1/metrics/phases/\d+/exercise-volumes", path):
            return self.get_phase_exercise_volumes(int(path.split("/")[4]))
        if method == "GET" and re.fullmatch(r"/v1/metrics/phases/\d+/maintenance", path):
            return self.get_phase_maintenance_metrics(int(path.split("/")[4]))
        if method == "GET" and re.fullmatch(r"/v1/metrics/phases/\d+/session-bench-metrics", path):
            return self.get_session_bench_metrics(int(path.split("/")[4]))
        if method == "GET" and re.fullmatch(r"/v1/metrics/phases/\d+/session-pl-metrics", path):
            return self.get_session_pl_metrics(int(path.split("/")[4]))
        if method == "GET" and re.fullmatch(r"/v1/metrics/phases/\d+/classification", path):
            return self.get_classification(int(path.split("/")[4]), qp)

        # Bodyweight log
        if method == "GET" and path == "/v1/bodyweight":
            return self.list_bodyweight(qp)
        if method == "POST" and path == "/v1/bodyweight":
            return self.create_bodyweight(body)
        if method == "DELETE" and re.fullmatch(r"/v1/bodyweight/\d+", path):
            return self.delete_bodyweight(int(path.split("/")[3]))

        # Confirmed 1RM
        if method == "GET" and path == "/v1/confirmed-1rm":
            return self.list_confirmed_1rm(qp)
        if method == "POST" and path == "/v1/confirmed-1rm":
            return self.create_confirmed_1rm(body)
        if method == "DELETE" and re.fullmatch(r"/v1/confirmed-1rm/\d+", path):
            return self.delete_confirmed_1rm(int(path.split("/")[3]))

        if method == "GET" and re.fullmatch(r"/v1/phases/\d+/progression", path):
            return self.get_phase_progression(int(path.split("/")[3]))

        if method == "POST" and path == "/v1/import/screenshot":
            return self.import_screenshot(body)
        if method == "POST" and path == "/v1/import/screenshots":
            return self.import_screenshots(body)

        if method == "POST" and path == "/v1/auth/login":
            return self.login(body)

        # Exercise Queue web UI (token-gated) — dispatched to a separate module
        if path.startswith("/v1/exq/"):
            from phase_app.exercise_api import ExerciseQueueApi
            exq = ExerciseQueueApi(self.conn)
            if method == "GET" and path == "/v1/exq/exercises":
                return exq.list_exercises(qp)
            if method == "PATCH" and re.fullmatch(r"/v1/exq/exercises/\d+", path):
                return exq.update_exercise(int(path.split("/")[4]), body, qp)
            if method == "DELETE" and re.fullmatch(r"/v1/exq/exercises/\d+", path):
                return exq.delete_exercise(int(path.split("/")[4]), qp)
            if method == "GET" and path == "/v1/exq/schedule":
                return exq.get_schedule(qp)
            if method == "POST" and path == "/v1/exq/schedule":
                return exq.create_occurrence(body, qp)
            if method == "PATCH" and re.fullmatch(r"/v1/exq/schedule/\d+", path):
                return exq.move_occurrence(int(path.split("/")[4]), body, qp)
            if method == "DELETE" and re.fullmatch(r"/v1/exq/schedule/\d+", path):
                return exq.delete_occurrence(int(path.split("/")[4]), qp)
            if method == "POST" and re.fullmatch(r"/v1/exq/schedule/\d+/done", path):
                return exq.complete_occurrence(int(path.split("/")[4]), qp)
            if method == "GET" and path == "/v1/exq/history":
                return exq.get_history(qp)
            if method == "GET" and path == "/v1/exq/stats":
                return exq.get_stats(qp)
            if method == "POST" and path == "/v1/exq/suggest-slot":
                return exq.suggest_slot(body, qp)
            if method == "POST" and path == "/v1/exq/chat":
                return exq.chat(body, qp)
            return ApiResponse(status=404, body={"error": "not_found"})

        # Burpee challenge (token-gated, no user auth required)
        if method == "GET" and path == "/v1/burpee/participants":
            return self.get_burpee_participants(qp)
        if method == "GET" and path == "/v1/burpee":
            return self.get_burpee_entries(qp)
        if method == "POST" and path == "/v1/burpee":
            return self.log_burpee_entry(body, qp)
        if method == "DELETE" and re.fullmatch(r"/v1/burpee/\d+", path):
            return self.delete_burpee_entry(int(path.split("/")[3]), qp)
        if method == "POST" and path == "/v1/burpee/ping":
            return self.ping_burpee(qp)

        return ApiResponse(status=404, body={"error": "not_found"})

    def login(self, payload: dict[str, Any]) -> ApiResponse:
        from phase_app.auth import check_credentials, issue_token
        username = payload.get("username", "")
        password = payload.get("password", "")
        if not check_credentials(username, password):
            return ApiResponse(401, {"error": "invalid_credentials"})
        secret = os.environ.get("TOKEN_SECRET", "")
        if not secret:
            return ApiResponse(500, {"error": "server_misconfigured", "detail": "TOKEN_SECRET not set"})
        ttl = int(os.environ.get("TOKEN_TTL_SECONDS", "0"))
        token = issue_token(secret, ttl)
        return ApiResponse(200, {"token": token})

    def create_phase(self, payload: dict[str, Any]) -> ApiResponse:
        required = ["phaseType", "startDate"]
        missing = [field for field in required if field not in payload]
        if missing:
            return ApiResponse(400, {"error": "validation_error", "missing": missing})
        if payload["phaseType"] != "powerlifting" and not payload.get("endDate"):
            return ApiResponse(400, {"error": "validation_error", "missing": ["endDate"]})
        # Powerlifting phases default to 10 years from start date if no end date given
        end_date = payload.get("endDate")
        if payload["phaseType"] == "powerlifting" and not end_date:
            start = _date.fromisoformat(payload["startDate"])
            end_date = start.replace(year=start.year + 10).isoformat()
        try:
            row = self._exec(
                "INSERT INTO phases (phase_type, start_date, end_date, name, notes) "
                "VALUES (%s, %s, %s, %s, %s) RETURNING phase_id",
                (payload["phaseType"], payload["startDate"], end_date,
                 payload.get("name"), payload.get("notes")),
            ).fetchone()
            self.conn.commit()
        except psycopg2.DatabaseError as exc:
            self.conn.rollback()
            return ApiResponse(400, {"error": "validation_error", "detail": str(exc)})
        return ApiResponse(201, {
            "phaseId": row["phase_id"],
            "phaseType": payload["phaseType"],
            "startDate": payload["startDate"],
            "endDate": end_date,
            "name": payload.get("name"),
            "notes": payload.get("notes"),
        })

    def create_session(self, payload: dict[str, Any]) -> ApiResponse:
        required = ["phaseId", "sessionDate", "sessionType"]
        missing = [field for field in required if field not in payload]
        if missing:
            return ApiResponse(400, {"error": "validation_error", "missing": missing})
        is_planned = bool(payload.get("isPlanned", False))
        is_deload = bool(payload.get("isDeload", False))
        try:
            if not is_planned:
                existing = self._exec(
                    "SELECT session_id FROM sessions WHERE phase_id = %s AND session_date = %s AND session_type = %s AND is_planned = FALSE",
                    (payload["phaseId"], payload["sessionDate"], payload["sessionType"]),
                ).fetchone()
                if existing:
                    return ApiResponse(409, {"error": "duplicate", "sessionId": existing["session_id"]})
            row = self._exec(
                "INSERT INTO sessions "
                "(phase_id, session_date, session_type, elite_hrv_readiness, garmin_overnight_hrv, notes, is_planned, is_deload, "
                "distance_km, duration_seconds, avg_hr, avg_pace_sec_per_km, "
                "run_type, max_hr, avg_cadence, avg_gct_ms, avg_vo_cm, ascent_m, rpe, avg_gap_pace_sec_per_km, "
                "work_duration_seconds, calories) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                "RETURNING *, COALESCE(is_planned, FALSE) AS is_planned, COALESCE(is_deload, FALSE) AS is_deload",
                (payload["phaseId"], payload["sessionDate"], payload["sessionType"],
                 payload.get("eliteHrvReadiness"), payload.get("garminOvernightHrv"), payload.get("notes"), is_planned, is_deload,
                 payload.get("distanceKm"), payload.get("durationSeconds"),
                 payload.get("avgHr"), payload.get("avgPaceSecPerKm"),
                 payload.get("runType"), payload.get("maxHr"),
                 payload.get("avgCadence"), payload.get("avgGctMs"),
                 payload.get("avgVoCm"), payload.get("ascentM"),
                 payload.get("rpe"), payload.get("avgGapPaceSecPerKm"),
                 payload.get("workDurationSeconds"), payload.get("calories")),
            ).fetchone()
            if not is_planned:
                self._exec(
                    "DELETE FROM sessions WHERE phase_id = %s AND session_date = %s "
                    "AND is_planned = TRUE AND session_id != %s",
                    (payload["phaseId"], payload["sessionDate"], row["session_id"]),
                )
            self.conn.commit()
        except psycopg2.DatabaseError as exc:
            self.conn.rollback()
            return ApiResponse(400, {"error": "validation_error", "detail": str(exc)})
        return ApiResponse(201, self._session_row(row))

    def create_session_exercise(self, session_id: int, payload: dict[str, Any]) -> ApiResponse:
        required = ["exerciseId", "exerciseOrder"]
        missing = [field for field in required if field not in payload]
        if missing:
            return ApiResponse(400, {"error": "validation_error", "missing": missing})
        try:
            row = self._exec(
                "INSERT INTO session_exercises (session_id, exercise_id, exercise_order, notes) "
                "VALUES (%s, %s, %s, %s) RETURNING session_exercise_id",
                (session_id, payload["exerciseId"], payload["exerciseOrder"], payload.get("notes")),
            ).fetchone()
            self.conn.commit()
        except psycopg2.DatabaseError as exc:
            self.conn.rollback()
            return ApiResponse(400, {"error": "validation_error", "detail": str(exc)})
        return ApiResponse(201, {
            "sessionExerciseId": row["session_exercise_id"],
            "sessionId": session_id,
            "exerciseId": payload["exerciseId"],
            "exerciseOrder": payload["exerciseOrder"],
            "notes": payload.get("notes"),
        })

    def create_exercise_set(self, session_exercise_id: int, payload: dict[str, Any]) -> ApiResponse:
        is_timed = "timeMinutes" in payload
        if is_timed:
            required = ["setNumber", "timeMinutes"]
        else:
            required = ["setNumber", "reps", "loadKg"]
        missing = [field for field in required if field not in payload]
        if missing:
            return ApiResponse(400, {"error": "validation_error", "missing": missing})
        try:
            if is_timed:
                row = self._exec(
                    "INSERT INTO exercise_sets (session_exercise_id, set_number, time_minutes, is_top_set, is_working_set) "
                    "VALUES (%s, %s, %s, %s, %s) RETURNING exercise_set_id",
                    (session_exercise_id, payload["setNumber"], payload["timeMinutes"],
                     int(payload.get("isTopSet", False)), int(payload.get("isWorkingSet", True))),
                ).fetchone()
            else:
                row = self._exec(
                    "INSERT INTO exercise_sets (session_exercise_id, set_number, reps, load_kg, is_top_set, is_working_set) "
                    "VALUES (%s, %s, %s, %s, %s, %s) RETURNING exercise_set_id",
                    (session_exercise_id, payload["setNumber"], payload["reps"], payload["loadKg"],
                     int(payload.get("isTopSet", False)), int(payload.get("isWorkingSet", True))),
                ).fetchone()
            self.conn.commit()
        except psycopg2.DatabaseError as exc:
            self.conn.rollback()
            return ApiResponse(400, {"error": "validation_error", "detail": str(exc)})
        result = {
            "exerciseSetId": row["exercise_set_id"],
            "sessionExerciseId": session_exercise_id,
            "setNumber": payload["setNumber"],
            "isTopSet": bool(payload.get("isTopSet", False)),
            "isWorkingSet": bool(payload.get("isWorkingSet", True)),
        }
        if is_timed:
            result["timeMinutes"] = payload["timeMinutes"]
        else:
            result["reps"] = payload["reps"]
            result["loadKg"] = payload["loadKg"]
        return ApiResponse(201, result)

    def get_session(self, session_id: int) -> ApiResponse:
        row = self._exec(
            "SELECT session_id, phase_id, session_date, session_type, elite_hrv_readiness, garmin_overnight_hrv, notes, "
            "COALESCE(is_planned, FALSE) AS is_planned, COALESCE(is_deload, FALSE) AS is_deload, "
            "distance_km, duration_seconds, avg_hr, avg_pace_sec_per_km, "
            "run_type, max_hr, avg_cadence, avg_gct_ms, avg_vo_cm, ascent_m, rpe, avg_gap_pace_sec_per_km, "
            "work_duration_seconds, calories "
            "FROM sessions WHERE session_id = %s",
            (session_id,),
        ).fetchone()
        if row is None:
            return ApiResponse(404, {"error": "not_found"})
        return ApiResponse(200, self._session_row(row))

    def get_session_exercises(self, session_id: int) -> ApiResponse:
        rows = self._exec(
            "SELECT session_exercise_id, session_id, exercise_id, exercise_order, notes "
            "FROM session_exercises WHERE session_id = %s ORDER BY exercise_order",
            (session_id,),
        ).fetchall()
        return ApiResponse(200, {"items": [{
            "sessionExerciseId": r["session_exercise_id"],
            "sessionId": r["session_id"],
            "exerciseId": r["exercise_id"],
            "exerciseOrder": r["exercise_order"],
            "notes": r["notes"],
        } for r in rows]})

    def get_exercise_sets(self, session_exercise_id: int) -> ApiResponse:
        rows = self._exec(
            "SELECT exercise_set_id, session_exercise_id, set_number, reps, load_kg, is_top_set, is_working_set, time_minutes "
            "FROM exercise_sets WHERE session_exercise_id = %s ORDER BY set_number",
            (session_exercise_id,),
        ).fetchall()
        return ApiResponse(200, {"items": [{
            "exerciseSetId": r["exercise_set_id"],
            "sessionExerciseId": r["session_exercise_id"],
            "setNumber": r["set_number"],
            "reps": r["reps"],
            "loadKg": r["load_kg"],
            "isTopSet": bool(r["is_top_set"]),
            "isWorkingSet": bool(r["is_working_set"]),
            "timeMinutes": float(r["time_minutes"]) if r["time_minutes"] is not None else None,
        } for r in rows]})

    def list_phases(self) -> ApiResponse:
        rows = self._exec(
            "SELECT phase_id, phase_type, start_date, end_date, name, notes "
            "FROM phases ORDER BY start_date DESC"
        ).fetchall()
        return ApiResponse(200, {"items": [{
            "phaseId": r["phase_id"],
            "phaseType": r["phase_type"],
            "startDate": r["start_date"],
            "endDate": r["end_date"],
            "name": r["name"],
            "notes": r["notes"],
        } for r in rows]})

    def _session_row(self, r: dict) -> dict:
        return {
            "sessionId": r["session_id"],
            "phaseId": r["phase_id"],
            "sessionDate": r["session_date"],
            "sessionType": r["session_type"],
            "eliteHrvReadiness": r["elite_hrv_readiness"],
            "garminOvernightHrv": r["garmin_overnight_hrv"],
            "notes": r["notes"],
            "isPlanned": bool(r.get("is_planned", False)),
            "isDeload": bool(r.get("is_deload", False)),
            "distanceKm": float(r["distance_km"]) if r.get("distance_km") is not None else None,
            "durationSeconds": r.get("duration_seconds"),
            "avgHr": r.get("avg_hr"),
            "avgPaceSecPerKm": r.get("avg_pace_sec_per_km"),
            "runType": r.get("run_type"),
            "maxHr": r.get("max_hr"),
            "avgCadence": r.get("avg_cadence"),
            "avgGctMs": r.get("avg_gct_ms"),
            "avgVoCm": float(r["avg_vo_cm"]) if r.get("avg_vo_cm") is not None else None,
            "ascentM": r.get("ascent_m"),
            "rpe": float(r["rpe"]) if r.get("rpe") is not None else None,
            "avgGapPaceSecPerKm": r.get("avg_gap_pace_sec_per_km"),
            "workDurationSeconds": r.get("work_duration_seconds"),
            "calories": r.get("calories"),
        }

    def list_sessions(self, qp: dict[str, str]) -> ApiResponse:
        if "phaseId" not in qp:
            return ApiResponse(400, {"error": "validation_error", "missing": ["phaseId"]})
        rows = self._exec(
            "SELECT session_id, phase_id, session_date, session_type, "
            "elite_hrv_readiness, garmin_overnight_hrv, notes, "
            "COALESCE(is_planned, FALSE) AS is_planned, COALESCE(is_deload, FALSE) AS is_deload, "
            "distance_km, duration_seconds, avg_hr, avg_pace_sec_per_km, "
            "run_type, max_hr, avg_cadence, avg_gct_ms, avg_vo_cm, ascent_m, rpe, avg_gap_pace_sec_per_km, "
            "work_duration_seconds, calories "
            "FROM sessions WHERE phase_id = %s ORDER BY session_date",
            (int(qp["phaseId"]),),
        ).fetchall()
        return ApiResponse(200, {"items": [self._session_row(r) for r in rows]})

    def list_exercises(self) -> ApiResponse:
        rows = self._exec(
            "SELECT exercise_id, exercise_name, is_barbell_bench_press, is_bodyweight, rep_min, rep_max, "
            "COALESCE(is_squat, 0) AS is_squat, COALESCE(is_deadlift, 0) AS is_deadlift, "
            "COALESCE(is_timed, FALSE) AS is_timed "
            "FROM exercises ORDER BY exercise_name"
        ).fetchall()
        return ApiResponse(200, {"items": [{
            "exerciseId":          r["exercise_id"],
            "exerciseName":        r["exercise_name"],
            "isBarbellBenchPress": bool(r["is_barbell_bench_press"]),
            "isBodyweight":        bool(r["is_bodyweight"]),
            "isSquat":             bool(r["is_squat"]),
            "isDeadlift":          bool(r["is_deadlift"]),
            "repMin":              r["rep_min"],
            "repMax":              r["rep_max"],
            "isTimed":             bool(r["is_timed"]),
        } for r in rows]})

    def list_benchmarks(self, qp: dict[str, str]) -> ApiResponse:
        if "phaseId" not in qp:
            return ApiResponse(400, {"error": "validation_error", "missing": ["phaseId"]})
        phase_id = int(qp["phaseId"])

        pullups = self._exec(
            "SELECT b.benchmark_id, b.phase_id, b.benchmark_date, b.benchmark_type, b.notes, "
            "p.reps, p.form_standard_version "
            "FROM benchmarks b "
            "JOIN benchmark_pullup_max_reps p ON b.benchmark_id = p.benchmark_id "
            "WHERE b.phase_id = %s AND b.benchmark_type = 'max_bodyweight_pullups' "
            "ORDER BY b.benchmark_date",
            (phase_id,),
        ).fetchall()

        runs = self._exec(
            "SELECT b.benchmark_id, b.phase_id, b.benchmark_date, b.benchmark_type, b.notes, "
            "r.avg_hr, r.target_hr, r.duration_min, r.pace_min_per_km, r.protocol_compliant "
            "FROM benchmarks b "
            "JOIN benchmark_run_aerobic_test r ON b.benchmark_id = r.benchmark_id "
            "WHERE b.phase_id = %s AND b.benchmark_type = 'run_aerobic_test' "
            "ORDER BY b.benchmark_date",
            (phase_id,),
        ).fetchall()

        items = [{
            "benchmarkId": r["benchmark_id"],
            "phaseId": r["phase_id"],
            "benchmarkDate": r["benchmark_date"],
            "benchmarkType": r["benchmark_type"],
            "notes": r["notes"],
            "reps": r["reps"],
            "formStandardVersion": r["form_standard_version"],
        } for r in pullups] + [{
            "benchmarkId": r["benchmark_id"],
            "phaseId": r["phase_id"],
            "benchmarkDate": r["benchmark_date"],
            "benchmarkType": r["benchmark_type"],
            "notes": r["notes"],
            "avgHr": r["avg_hr"],
            "targetHr": r["target_hr"],
            "durationMin": r["duration_min"],
            "paceMinPerKm": r["pace_min_per_km"],
            "protocolCompliant": bool(r["protocol_compliant"]),
        } for r in runs]
        items.sort(key=lambda x: x["benchmarkDate"])
        return ApiResponse(200, {"items": items})

    def create_benchmark(self, payload: dict[str, Any]) -> ApiResponse:
        required = ["phaseId", "benchmarkDate", "benchmarkType"]
        missing = [f for f in required if f not in payload]
        if missing:
            return ApiResponse(400, {"error": "validation_error", "missing": missing})
        btype = payload["benchmarkType"]
        if btype == "max_bodyweight_pullups":
            if "reps" not in payload:
                return ApiResponse(400, {"error": "validation_error", "missing": ["reps"]})
            if "formStandardVersion" not in payload:
                return ApiResponse(400, {"error": "validation_error", "missing": ["formStandardVersion"]})
        elif btype == "run_aerobic_test":
            if "avgHr" not in payload:
                return ApiResponse(400, {"error": "validation_error", "missing": ["avgHr"]})
            if "paceMinPerKm" not in payload and not ("distanceKm" in payload and "elapsedSec" in payload):
                return ApiResponse(400, {"error": "validation_error", "missing": ["paceMinPerKm"]})
        else:
            return ApiResponse(400, {"error": "validation_error", "detail": f"unknown benchmarkType: {btype}"})

        try:
            row = self._exec(
                "INSERT INTO benchmarks (phase_id, benchmark_date, benchmark_type, notes) "
                "VALUES (%s, %s, %s, %s) RETURNING benchmark_id",
                (payload["phaseId"], payload["benchmarkDate"], btype, payload.get("notes")),
            ).fetchone()
            bid = row["benchmark_id"]

            if btype == "max_bodyweight_pullups":
                self._exec(
                    "INSERT INTO benchmark_pullup_max_reps (benchmark_id, reps, form_standard_version) "
                    "VALUES (%s, %s, %s)",
                    (bid, payload["reps"], payload["formStandardVersion"]),
                )
            else:
                self._exec(
                    "INSERT INTO benchmark_run_aerobic_test "
                    "(benchmark_id, target_hr, duration_min, avg_hr, pace_min_per_km, distance_km, elapsed_sec, protocol_compliant) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (bid, payload.get("targetHr", 140), payload.get("durationMin", 40),
                     payload["avgHr"], payload.get("paceMinPerKm"), payload.get("distanceKm"),
                     payload.get("elapsedSec"), int(payload.get("protocolCompliant", True))),
                )
            self.conn.commit()
        except psycopg2.DatabaseError as exc:
            self.conn.rollback()
            return ApiResponse(400, {"error": "validation_error", "detail": str(exc)})

        result: dict[str, Any] = {
            "benchmarkId": bid,
            "phaseId": payload["phaseId"],
            "benchmarkDate": payload["benchmarkDate"],
            "benchmarkType": btype,
        }
        if btype == "max_bodyweight_pullups":
            result["reps"] = payload["reps"]
            result["formStandardVersion"] = payload["formStandardVersion"]
        else:
            result["avgHr"] = payload["avgHr"]
            result["targetHr"] = payload.get("targetHr", 140)
            result["durationMin"] = payload.get("durationMin", 40)
            result["paceMinPerKm"] = payload.get("paceMinPerKm")
            result["protocolCompliant"] = bool(payload.get("protocolCompliant", True))
        return ApiResponse(201, result)

    def update_phase(self, phase_id: int, payload: dict[str, Any]) -> ApiResponse:
        allowed = {"phaseType": "phase_type", "startDate": "start_date", "endDate": "end_date",
                   "name": "name", "notes": "notes"}
        updates = {col: payload[key] for key, col in allowed.items() if key in payload}
        if not updates:
            return ApiResponse(400, {"error": "validation_error", "detail": "no updatable fields provided"})
        set_clause = ", ".join(f"{col} = %s" for col in updates)
        try:
            cur = self._exec(
                f"UPDATE phases SET {set_clause} WHERE phase_id = %s RETURNING phase_id, phase_type, start_date, end_date, name, notes",
                (*updates.values(), phase_id),
            )
            row = cur.fetchone()
            if row is None:
                return ApiResponse(404, {"error": "not_found"})
            self.conn.commit()
        except psycopg2.DatabaseError as exc:
            self.conn.rollback()
            return ApiResponse(400, {"error": "validation_error", "detail": str(exc)})
        return ApiResponse(200, {
            "phaseId": row["phase_id"],
            "phaseType": row["phase_type"],
            "startDate": row["start_date"],
            "endDate": row["end_date"],
            "name": row["name"],
            "notes": row["notes"],
        })

    def delete_phase(self, phase_id: int) -> ApiResponse:
        try:
            cur = self._exec("DELETE FROM phases WHERE phase_id = %s RETURNING phase_id", (phase_id,))
            row = cur.fetchone()
            if row is None:
                return ApiResponse(404, {"error": "not_found"})
            self.conn.commit()
        except psycopg2.errors.ForeignKeyViolation:
            self.conn.rollback()
            return ApiResponse(409, {"error": "conflict", "detail": "phase has linked sessions or benchmarks"})
        return ApiResponse(200, {"deleted": True, "phaseId": phase_id})

    def update_session(self, session_id: int, payload: dict[str, Any]) -> ApiResponse:
        allowed = {"sessionDate": "session_date", "sessionType": "session_type",
                   "eliteHrvReadiness": "elite_hrv_readiness", "garminOvernightHrv": "garmin_overnight_hrv",
                   "notes": "notes", "isDeload": "is_deload",
                   "distanceKm": "distance_km", "durationSeconds": "duration_seconds",
                   "avgHr": "avg_hr", "avgPaceSecPerKm": "avg_pace_sec_per_km",
                   "runType": "run_type", "maxHr": "max_hr",
                   "avgCadence": "avg_cadence", "avgGctMs": "avg_gct_ms",
                   "avgVoCm": "avg_vo_cm", "ascentM": "ascent_m",
                   "rpe": "rpe", "avgGapPaceSecPerKm": "avg_gap_pace_sec_per_km"}
        updates = {col: payload[key] for key, col in allowed.items() if key in payload}
        if not updates:
            return ApiResponse(400, {"error": "validation_error", "detail": "no updatable fields provided"})
        set_clause = ", ".join(f"{col} = %s" for col in updates)
        try:
            cur = self._exec(
                f"UPDATE sessions SET {set_clause} WHERE session_id = %s "
                "RETURNING *, COALESCE(is_planned, FALSE) AS is_planned, COALESCE(is_deload, FALSE) AS is_deload",
                (*updates.values(), session_id),
            )
            row = cur.fetchone()
            if row is None:
                return ApiResponse(404, {"error": "not_found"})
            self.conn.commit()
        except psycopg2.DatabaseError as exc:
            self.conn.rollback()
            return ApiResponse(400, {"error": "validation_error", "detail": str(exc)})
        return ApiResponse(200, self._session_row(row))

    def delete_session(self, session_id: int) -> ApiResponse:
        cur = self._exec("DELETE FROM sessions WHERE session_id = %s RETURNING session_id", (session_id,))
        row = cur.fetchone()
        if row is None:
            return ApiResponse(404, {"error": "not_found"})
        self.conn.commit()
        return ApiResponse(200, {"deleted": True, "sessionId": session_id})

    def update_session_exercise(self, session_id: int, session_exercise_id: int, payload: dict[str, Any]) -> ApiResponse:
        allowed = {"exerciseOrder": "exercise_order", "notes": "notes"}
        updates = {col: payload[key] for key, col in allowed.items() if key in payload}
        if not updates:
            return ApiResponse(400, {"error": "validation_error", "detail": "no updatable fields provided"})
        set_clause = ", ".join(f"{col} = %s" for col in updates)
        try:
            cur = self._exec(
                f"UPDATE session_exercises SET {set_clause} "
                "WHERE session_exercise_id = %s AND session_id = %s "
                "RETURNING session_exercise_id, session_id, exercise_id, exercise_order, notes",
                (*updates.values(), session_exercise_id, session_id),
            )
            row = cur.fetchone()
            if row is None:
                return ApiResponse(404, {"error": "not_found"})
            self.conn.commit()
        except psycopg2.DatabaseError as exc:
            self.conn.rollback()
            return ApiResponse(400, {"error": "validation_error", "detail": str(exc)})
        return ApiResponse(200, {
            "sessionExerciseId": row["session_exercise_id"],
            "sessionId": row["session_id"],
            "exerciseId": row["exercise_id"],
            "exerciseOrder": row["exercise_order"],
            "notes": row["notes"],
        })

    def delete_session_exercise(self, session_id: int, session_exercise_id: int) -> ApiResponse:
        cur = self._exec(
            "DELETE FROM session_exercises WHERE session_exercise_id = %s AND session_id = %s RETURNING session_exercise_id",
            (session_exercise_id, session_id),
        )
        row = cur.fetchone()
        if row is None:
            return ApiResponse(404, {"error": "not_found"})
        self.conn.commit()
        return ApiResponse(200, {"deleted": True, "sessionExerciseId": session_exercise_id})

    def update_exercise_set(self, session_exercise_id: int, exercise_set_id: int, payload: dict[str, Any]) -> ApiResponse:
        allowed = {"reps": "reps", "loadKg": "load_kg", "isTopSet": "is_top_set", "isWorkingSet": "is_working_set", "timeMinutes": "time_minutes"}
        raw = {col: payload[key] for key, col in allowed.items() if key in payload}
        if not raw:
            return ApiResponse(400, {"error": "validation_error", "detail": "no updatable fields provided"})
        updates = {}
        for col, val in raw.items():
            updates[col] = int(val) if col in ("is_top_set", "is_working_set") else val
        set_clause = ", ".join(f"{col} = %s" for col in updates)
        try:
            cur = self._exec(
                f"UPDATE exercise_sets SET {set_clause} "
                "WHERE exercise_set_id = %s AND session_exercise_id = %s "
                "RETURNING exercise_set_id, session_exercise_id, set_number, reps, load_kg, is_top_set, is_working_set, time_minutes",
                (*updates.values(), exercise_set_id, session_exercise_id),
            )
            row = cur.fetchone()
            if row is None:
                return ApiResponse(404, {"error": "not_found"})
            self.conn.commit()
        except psycopg2.DatabaseError as exc:
            self.conn.rollback()
            return ApiResponse(400, {"error": "validation_error", "detail": str(exc)})
        return ApiResponse(200, {
            "exerciseSetId": row["exercise_set_id"],
            "sessionExerciseId": row["session_exercise_id"],
            "setNumber": row["set_number"],
            "reps": row["reps"],
            "loadKg": row["load_kg"],
            "isTopSet": bool(row["is_top_set"]),
            "isWorkingSet": bool(row["is_working_set"]),
            "timeMinutes": float(row["time_minutes"]) if row["time_minutes"] is not None else None,
        })

    def delete_exercise_set(self, session_exercise_id: int, exercise_set_id: int) -> ApiResponse:
        cur = self._exec(
            "DELETE FROM exercise_sets WHERE exercise_set_id = %s AND session_exercise_id = %s RETURNING exercise_set_id",
            (exercise_set_id, session_exercise_id),
        )
        row = cur.fetchone()
        if row is None:
            return ApiResponse(404, {"error": "not_found"})
        self.conn.commit()
        return ApiResponse(200, {"deleted": True, "exerciseSetId": exercise_set_id})

    def update_benchmark(self, benchmark_id: int, payload: dict[str, Any]) -> ApiResponse:
        base_allowed = {"benchmarkDate": "benchmark_date", "notes": "notes"}
        base_updates = {col: payload[key] for key, col in base_allowed.items() if key in payload}
        pullup_allowed = {"reps": "reps", "formStandardVersion": "form_standard_version"}
        pullup_updates = {col: payload[key] for key, col in pullup_allowed.items() if key in payload}
        run_allowed = {"avgHr": "avg_hr", "paceMinPerKm": "pace_min_per_km", "protocolCompliant": "protocol_compliant",
                       "targetHr": "target_hr", "durationMin": "duration_min"}
        run_updates = {col: payload[key] for key, col in run_allowed.items() if key in payload}
        if not base_updates and not pullup_updates and not run_updates:
            return ApiResponse(400, {"error": "validation_error", "detail": "no updatable fields provided"})
        try:
            if base_updates:
                set_clause = ", ".join(f"{col} = %s" for col in base_updates)
                cur = self._exec(
                    f"UPDATE benchmarks SET {set_clause} WHERE benchmark_id = %s RETURNING benchmark_id, benchmark_type",
                    (*base_updates.values(), benchmark_id),
                )
                row = cur.fetchone()
            else:
                cur = self._exec(
                    "SELECT benchmark_id, benchmark_type FROM benchmarks WHERE benchmark_id = %s",
                    (benchmark_id,),
                )
                row = cur.fetchone()
            if row is None:
                return ApiResponse(404, {"error": "not_found"})
            btype = row["benchmark_type"]
            if pullup_updates and btype == "max_bodyweight_pullups":
                set_clause = ", ".join(f"{col} = %s" for col in pullup_updates)
                self._exec(
                    f"UPDATE benchmark_pullup_max_reps SET {set_clause} WHERE benchmark_id = %s",
                    (*pullup_updates.values(), benchmark_id),
                )
            if run_updates and btype == "run_aerobic_test":
                if "protocol_compliant" in run_updates:
                    run_updates["protocol_compliant"] = int(run_updates["protocol_compliant"])
                set_clause = ", ".join(f"{col} = %s" for col in run_updates)
                self._exec(
                    f"UPDATE benchmark_run_aerobic_test SET {set_clause} WHERE benchmark_id = %s",
                    (*run_updates.values(), benchmark_id),
                )
            self.conn.commit()
        except psycopg2.DatabaseError as exc:
            self.conn.rollback()
            return ApiResponse(400, {"error": "validation_error", "detail": str(exc)})
        return ApiResponse(200, {"benchmarkId": benchmark_id, "updated": True})

    def delete_benchmark(self, benchmark_id: int) -> ApiResponse:
        cur = self._exec(
            "DELETE FROM benchmarks WHERE benchmark_id = %s RETURNING benchmark_id",
            (benchmark_id,),
        )
        row = cur.fetchone()
        if row is None:
            return ApiResponse(404, {"error": "not_found"})
        self.conn.commit()
        return ApiResponse(200, {"deleted": True, "benchmarkId": benchmark_id})

    def create_exercise(self, payload: dict[str, Any]) -> ApiResponse:
        if "exerciseName" not in payload:
            return ApiResponse(400, {"error": "validation_error", "missing": ["exerciseName"]})
        rep_min = payload.get("repMin")
        rep_max = payload.get("repMax")
        try:
            row = self._exec(
                "INSERT INTO exercises (exercise_name, is_barbell_bench_press, is_bodyweight, is_squat, is_deadlift, rep_min, rep_max, is_timed) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING exercise_id",
                (payload["exerciseName"],
                 int(payload.get("isBarbellBenchPress", False)),
                 int(payload.get("isBodyweight", False)),
                 int(payload.get("isSquat", False)),
                 int(payload.get("isDeadlift", False)),
                 int(rep_min) if rep_min is not None else None,
                 int(rep_max) if rep_max is not None else None,
                 bool(payload.get("isTimed", False))),
            ).fetchone()
            self.conn.commit()
        except psycopg2.DatabaseError as exc:
            self.conn.rollback()
            return ApiResponse(400, {"error": "validation_error", "detail": str(exc)})
        return ApiResponse(201, {
            "exerciseId":          row["exercise_id"],
            "exerciseName":        payload["exerciseName"],
            "isBarbellBenchPress": bool(payload.get("isBarbellBenchPress", False)),
            "isBodyweight":        bool(payload.get("isBodyweight", False)),
            "isSquat":             bool(payload.get("isSquat", False)),
            "isDeadlift":          bool(payload.get("isDeadlift", False)),
            "repMin":              int(rep_min) if rep_min is not None else None,
            "repMax":              int(rep_max) if rep_max is not None else None,
            "isTimed":             bool(payload.get("isTimed", False)),
        })

    def delete_exercise(self, exercise_id: int) -> ApiResponse:
        try:
            cur = self._exec(
                "DELETE FROM exercises WHERE exercise_id = %s RETURNING exercise_id",
                (exercise_id,),
            )
            row = cur.fetchone()
            if row is None:
                return ApiResponse(404, {"error": "not_found"})
            self.conn.commit()
        except psycopg2.DatabaseError as exc:
            self.conn.rollback()
            return ApiResponse(400, {"error": "validation_error", "detail": str(exc)})
        return ApiResponse(200, {"deleted": True, "exerciseId": exercise_id})

    def merge_exercises(self, body: dict) -> ApiResponse:
        source_id = body.get("sourceId")
        target_id = body.get("targetId")
        if not source_id or not target_id or source_id == target_id:
            return ApiResponse(400, {"error": "invalid_request"})
        try:
            # Drop source rows in sessions that already have the target (avoid unique conflict)
            self._exec(
                "DELETE FROM session_exercises WHERE exercise_id = %s"
                " AND session_id IN (SELECT session_id FROM session_exercises WHERE exercise_id = %s)",
                (source_id, target_id),
            )
            self._exec(
                "UPDATE session_exercises SET exercise_id = %s WHERE exercise_id = %s",
                (target_id, source_id),
            )
            cur = self._exec(
                "DELETE FROM exercises WHERE exercise_id = %s RETURNING exercise_id",
                (source_id,),
            )
            if cur.fetchone() is None:
                self.conn.rollback()
                return ApiResponse(404, {"error": "not_found"})
            self.conn.commit()
        except psycopg2.DatabaseError as exc:
            self.conn.rollback()
            return ApiResponse(400, {"error": "validation_error", "detail": str(exc)})
        return ApiResponse(200, {"merged": True, "deletedId": source_id, "targetId": target_id})

    def get_phase_summary(self, phase_id: int) -> ApiResponse:
        from phase_app.metrics import get_phase_summary
        payload = get_phase_summary(self.conn, phase_id)
        if payload is None:
            return ApiResponse(404, {"error": "not_found"})
        return ApiResponse(200, payload)

    def get_metric_top_set(self, session_id: int) -> ApiResponse:
        from phase_app.metrics import get_bench_top_set_e1rm
        payload = get_bench_top_set_e1rm(self.conn, session_id)
        if payload is None:
            return ApiResponse(404, {"error": "not_found"})
        return ApiResponse(200, payload)

    def get_metric_bench_volume(self, session_id: int) -> ApiResponse:
        from phase_app.metrics import get_bench_volume
        payload = get_bench_volume(self.conn, session_id)
        if payload is None:
            return ApiResponse(404, {"error": "not_found"})
        return ApiResponse(200, payload)

    def get_phase_exercise_volumes(self, phase_id: int) -> ApiResponse:
        from phase_app.metrics import get_phase_exercise_volumes
        items = get_phase_exercise_volumes(self.conn, phase_id)
        return ApiResponse(200, {"items": items})

    def get_session_bench_metrics(self, phase_id: int) -> ApiResponse:
        from phase_app.metrics import get_session_bench_metrics
        return ApiResponse(200, get_session_bench_metrics(self.conn, phase_id))

    def get_phase_maintenance_metrics(self, phase_id: int) -> ApiResponse:
        from phase_app.metrics import get_phase_maintenance
        return ApiResponse(200, get_phase_maintenance(self.conn, phase_id))

    def get_phase_progression(self, phase_id: int) -> ApiResponse:
        rows = self._exec(
            """
            WITH last_session AS (
              SELECT DISTINCT ON (e.exercise_id, s.session_type)
                e.exercise_id,
                e.exercise_name,
                e.is_bodyweight,
                e.is_barbell_bench_press,
                e.rep_min,
                e.rep_max,
                s.session_id,
                s.session_date,
                s.session_type
              FROM session_exercises se
              JOIN sessions s ON s.session_id = se.session_id
              JOIN exercises e ON e.exercise_id = se.exercise_id
              WHERE s.phase_id = %s
                AND COALESCE(s.is_planned, FALSE) = FALSE
                AND COALESCE(s.is_deload, FALSE) = FALSE
              ORDER BY e.exercise_id, s.session_type, s.session_date DESC, s.session_id DESC
            )
            SELECT
              ls.exercise_id, ls.exercise_name, ls.is_bodyweight, ls.is_barbell_bench_press,
              ls.rep_min, ls.rep_max,
              ls.session_id  AS last_session_id,
              ls.session_date AS last_session_date,
              ls.session_type AS last_session_type,
              es.reps, es.load_kg, es.set_number,
              se.exercise_order
            FROM last_session ls
            JOIN session_exercises se
              ON se.session_id = ls.session_id AND se.exercise_id = ls.exercise_id
            JOIN exercise_sets es ON es.session_exercise_id = se.session_exercise_id
            WHERE es.is_working_set = 1
            ORDER BY se.exercise_order, es.set_number
            """,
            (phase_id,),
        ).fetchall()

        exercises: dict[tuple, dict] = {}
        for r in rows:
            key = (r["exercise_id"], r["last_session_type"])
            if key not in exercises:
                exercises[key] = {
                    "exerciseId": r["exercise_id"],
                    "exerciseName": r["exercise_name"],
                    "isBodyweight": bool(r["is_bodyweight"]),
                    "isBarbellBenchPress": bool(r["is_barbell_bench_press"]),
                    "repMin": r["rep_min"],
                    "repMax": r["rep_max"],
                    "lastSessionId": r["last_session_id"],
                    "lastSessionDate": str(r["last_session_date"]),
                    "lastSessionType": r["last_session_type"],
                    "workingSets": [],
                }
            exercises[key]["workingSets"].append({
                "reps": r["reps"],
                "loadKg": float(r["load_kg"]) if r["load_kg"] is not None else 0.0,
            })
        return ApiResponse(200, {"items": list(exercises.values())})

    # ------------------------------------------------------------------ #
    # Exercises — update to support is_squat / is_deadlift / rep_min/max #
    # ------------------------------------------------------------------ #

    def update_exercise(self, exercise_id: int, payload: dict[str, Any]) -> ApiResponse:
        allowed = {
            "exerciseName":         "exercise_name",
            "isBarbellBenchPress":  "is_barbell_bench_press",
            "isBodyweight":         "is_bodyweight",
            "isSquat":              "is_squat",
            "isDeadlift":           "is_deadlift",
            "repMin":               "rep_min",
            "repMax":               "rep_max",
            "isTimed":              "is_timed",
        }
        raw = {col: payload[key] for key, col in allowed.items() if key in payload}
        if not raw:
            return ApiResponse(400, {"error": "validation_error", "detail": "no updatable fields provided"})
        bool_cols = {"is_barbell_bench_press", "is_bodyweight", "is_squat", "is_deadlift"}
        native_bool_cols = {"is_timed"}
        int_cols = {"rep_min", "rep_max"}
        updates = {}
        for col, val in raw.items():
            if col in bool_cols:
                updates[col] = int(val)
            elif col in native_bool_cols:
                updates[col] = bool(val)
            elif col in int_cols:
                updates[col] = int(val) if val is not None else None
            else:
                updates[col] = val
        set_clause = ", ".join(f"{col} = %s" for col in updates)
        try:
            cur = self._exec(
                f"UPDATE exercises SET {set_clause} WHERE exercise_id = %s "
                "RETURNING exercise_id, exercise_name, is_barbell_bench_press, is_bodyweight, "
                "COALESCE(is_squat, 0) AS is_squat, COALESCE(is_deadlift, 0) AS is_deadlift, rep_min, rep_max, "
                "COALESCE(is_timed, FALSE) AS is_timed",
                (*updates.values(), exercise_id),
            )
            row = cur.fetchone()
            if row is None:
                return ApiResponse(404, {"error": "not_found"})
            self.conn.commit()
        except psycopg2.DatabaseError as exc:
            self.conn.rollback()
            return ApiResponse(400, {"error": "validation_error", "detail": str(exc)})
        return ApiResponse(200, {
            "exerciseId":           row["exercise_id"],
            "exerciseName":         row["exercise_name"],
            "isBarbellBenchPress":  bool(row["is_barbell_bench_press"]),
            "isBodyweight":         bool(row["is_bodyweight"]),
            "isSquat":              bool(row["is_squat"]),
            "isDeadlift":           bool(row["is_deadlift"]),
            "repMin":               row["rep_min"],
            "repMax":               row["rep_max"],
            "isTimed":              bool(row["is_timed"]),
        })

    # ------------------------------------------------------------------ #
    # Powerlifting metrics                                                 #
    # ------------------------------------------------------------------ #

    def get_session_pl_metrics(self, phase_id: int) -> ApiResponse:
        from phase_app.metrics import get_session_pl_metrics
        return ApiResponse(200, get_session_pl_metrics(self.conn, phase_id))

    def get_classification(self, phase_id: int, qp: dict[str, str]) -> ApiResponse:
        from phase_app.classification import classification_payload
        # Use bodyweight from query param if supplied, else latest log entry for phase
        bw_str = qp.get("bodyweightKg")
        if bw_str:
            try:
                bw = float(bw_str)
            except ValueError:
                return ApiResponse(400, {"error": "validation_error", "detail": "invalid bodyweightKg"})
        else:
            row = self._exec(
                "SELECT weight_kg FROM bodyweight_log WHERE phase_id = %s ORDER BY logged_date DESC LIMIT 1",
                (phase_id,),
            ).fetchone()
            if row is None:
                return ApiResponse(404, {"error": "no_bodyweight", "detail": "No bodyweight logged for this phase"})
            bw = float(row["weight_kg"])

        # Best effective max per lift = MAX(e1RM across sessions, confirmed 1RM)
        totals: dict[str, dict] = {}
        for lift, flag in [("squat", "is_squat"), ("bench", "is_barbell_bench_press"), ("deadlift", "is_deadlift")]:
            e1rm_row = self._exec(
                f"""
                SELECT ROUND((es.load_kg * (1 + es.reps / 30.0))::numeric, 2) AS best_e1rm,
                       es.load_kg, es.reps, s.session_date
                FROM sessions s
                JOIN session_exercises se ON se.session_id = s.session_id
                JOIN exercises e ON e.exercise_id = se.exercise_id
                JOIN exercise_sets es ON es.session_exercise_id = se.session_exercise_id
                WHERE s.phase_id = %s AND e.{flag} = 1 AND es.is_top_set = 1
                ORDER BY best_e1rm DESC
                LIMIT 1
                """,
                (phase_id,),
            ).fetchone()
            confirmed_row = self._exec(
                "SELECT MAX(weight_kg) AS best_confirmed FROM confirmed_1rm "
                "WHERE phase_id = %s AND lift_type = %s",
                (phase_id, lift),
            ).fetchone()
            e1rm_val = float(e1rm_row["best_e1rm"]) if e1rm_row and e1rm_row["best_e1rm"] else 0.0
            conf_val = float(confirmed_row["best_confirmed"]) if confirmed_row and confirmed_row["best_confirmed"] else 0.0
            if e1rm_val >= conf_val and e1rm_row:
                totals[lift] = {
                    "value": e1rm_val,
                    "date": str(e1rm_row["session_date"]),
                    "topSetLoadKg": float(e1rm_row["load_kg"]),
                    "topSetReps": int(e1rm_row["reps"]),
                }
            else:
                totals[lift] = {"value": conf_val, "date": None, "topSetLoadKg": None, "topSetReps": None}

        total_kg = totals["squat"]["value"] + totals["bench"]["value"] + totals["deadlift"]["value"]
        payload = classification_payload(bw, total_kg)
        payload["liftMaxes"] = totals
        return ApiResponse(200, payload)

    # ------------------------------------------------------------------ #
    # Bodyweight log                                                       #
    # ------------------------------------------------------------------ #

    def list_bodyweight(self, qp: dict[str, str]) -> ApiResponse:
        if "phaseId" not in qp:
            return ApiResponse(400, {"error": "validation_error", "missing": ["phaseId"]})
        rows = self._exec(
            "SELECT log_id, phase_id, session_id, logged_date, weight_kg "
            "FROM bodyweight_log WHERE phase_id = %s ORDER BY logged_date DESC",
            (int(qp["phaseId"]),),
        ).fetchall()
        return ApiResponse(200, {"items": [{
            "logId":       r["log_id"],
            "phaseId":     r["phase_id"],
            "sessionId":   r["session_id"],
            "loggedDate":  str(r["logged_date"]),
            "weightKg":    float(r["weight_kg"]),
        } for r in rows]})

    def create_bodyweight(self, payload: dict[str, Any]) -> ApiResponse:
        required = ["phaseId", "loggedDate", "weightKg"]
        missing = [f for f in required if f not in payload]
        if missing:
            return ApiResponse(400, {"error": "validation_error", "missing": missing})
        try:
            row = self._exec(
                "INSERT INTO bodyweight_log (phase_id, session_id, logged_date, weight_kg) "
                "VALUES (%s, %s, %s, %s) RETURNING log_id",
                (payload["phaseId"], payload.get("sessionId"), payload["loggedDate"], payload["weightKg"]),
            ).fetchone()
            self.conn.commit()
        except psycopg2.DatabaseError as exc:
            self.conn.rollback()
            return ApiResponse(400, {"error": "validation_error", "detail": str(exc)})
        return ApiResponse(201, {
            "logId":      row["log_id"],
            "phaseId":    payload["phaseId"],
            "sessionId":  payload.get("sessionId"),
            "loggedDate": payload["loggedDate"],
            "weightKg":   payload["weightKg"],
        })

    def delete_bodyweight(self, log_id: int) -> ApiResponse:
        cur = self._exec("DELETE FROM bodyweight_log WHERE log_id = %s RETURNING log_id", (log_id,))
        if cur.fetchone() is None:
            return ApiResponse(404, {"error": "not_found"})
        self.conn.commit()
        return ApiResponse(200, {"deleted": True, "logId": log_id})

    # ------------------------------------------------------------------ #
    # Confirmed 1RM                                                        #
    # ------------------------------------------------------------------ #

    def list_confirmed_1rm(self, qp: dict[str, str]) -> ApiResponse:
        if "phaseId" not in qp:
            return ApiResponse(400, {"error": "validation_error", "missing": ["phaseId"]})
        rows = self._exec(
            "SELECT rm_id, phase_id, session_id, logged_date, lift_type, weight_kg "
            "FROM confirmed_1rm WHERE phase_id = %s ORDER BY logged_date DESC",
            (int(qp["phaseId"]),),
        ).fetchall()
        return ApiResponse(200, {"items": [{
            "rmId":       r["rm_id"],
            "phaseId":    r["phase_id"],
            "sessionId":  r["session_id"],
            "loggedDate": str(r["logged_date"]),
            "liftType":   r["lift_type"],
            "weightKg":   float(r["weight_kg"]),
        } for r in rows]})

    def create_confirmed_1rm(self, payload: dict[str, Any]) -> ApiResponse:
        required = ["phaseId", "loggedDate", "liftType", "weightKg"]
        missing = [f for f in required if f not in payload]
        if missing:
            return ApiResponse(400, {"error": "validation_error", "missing": missing})
        if payload["liftType"] not in ("bench", "squat", "deadlift"):
            return ApiResponse(400, {"error": "validation_error", "detail": "liftType must be bench, squat, or deadlift"})
        try:
            row = self._exec(
                "INSERT INTO confirmed_1rm (phase_id, session_id, logged_date, lift_type, weight_kg) "
                "VALUES (%s, %s, %s, %s, %s) RETURNING rm_id",
                (payload["phaseId"], payload.get("sessionId"), payload["loggedDate"],
                 payload["liftType"], payload["weightKg"]),
            ).fetchone()
            self.conn.commit()
        except psycopg2.DatabaseError as exc:
            self.conn.rollback()
            return ApiResponse(400, {"error": "validation_error", "detail": str(exc)})
        return ApiResponse(201, {
            "rmId":       row["rm_id"],
            "phaseId":    payload["phaseId"],
            "sessionId":  payload.get("sessionId"),
            "loggedDate": payload["loggedDate"],
            "liftType":   payload["liftType"],
            "weightKg":   payload["weightKg"],
        })

    def delete_confirmed_1rm(self, rm_id: int) -> ApiResponse:
        cur = self._exec("DELETE FROM confirmed_1rm WHERE rm_id = %s RETURNING rm_id", (rm_id,))
        if cur.fetchone() is None:
            return ApiResponse(404, {"error": "not_found"})
        self.conn.commit()
        return ApiResponse(200, {"deleted": True, "rmId": rm_id})

    def import_screenshot(self, payload: dict[str, Any]) -> ApiResponse:
        import base64
        import anthropic

        image_b64 = payload.get("imageBase64")
        media_type = payload.get("mediaType", "image/png")

        if not image_b64:
            return ApiResponse(400, {"error": "validation_error", "missing": ["imageBase64"]})
        try:
            base64.b64decode(image_b64, validate=True)
        except Exception:
            return ApiResponse(400, {"error": "validation_error", "detail": "imageBase64 is not valid base64"})

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return ApiResponse(500, {"error": "server_error", "detail": "ANTHROPIC_API_KEY not configured"})

        client = anthropic.Anthropic(api_key=api_key)
        prompt = (
            "You are parsing a workout screenshot from a fitness app (e.g. Garmin Connect, Strong, Hevy).\n"
            "Extract all exercises and sets. Return ONLY valid JSON — no markdown, no commentary.\n"
            "Schema:\n"
            "{\n"
            '  "sessionDate": "YYYY-MM-DD",\n'
            '  "sessionType": "other",\n'
            '  "notes": null,\n'
            '  "exercises": [\n'
            '    {\n'
            '      "exerciseName": "Bench Press",\n'
            '      "isBarbellBenchPress": false,\n'
            '      "isSquat": false,\n'
            '      "isDeadlift": false,\n'
            '      "isTimed": false,\n'
            '      "sets": [\n'
            '        { "setNumber": 1, "reps": 5, "loadKg": 100.0, "isTopSet": false, "isWorkingSet": true }\n'
            '      ]\n'
            '    }\n'
            '  ]\n'
            "}\n"
            "sessionType must be one of: heavy_bench, volume_bench, speed_bench, squat, deadlift, mix, run, pull, rest, other. Use 'mix' for sessions that combine multiple powerlifting lifts or are labelled 'mixed'.\n"
            "Rules:\n"
            "- Convert lbs to kg (multiply by 0.4536). Use 0 for bodyweight exercises.\n"
            "- Garmin Connect tables have columns: Set, Exercise Name, Time, Rest, Reps, Weight, Volume. "
            "Use the Weight column for loadKg. Do NOT use the Volume column (Weight × Reps) — it is much larger.\n"
            "- Exercise classification flags (set on each exercise object):\n"
            "  isBarbellBenchPress: true for barbell bench press variants (flat, incline, close-grip bench with a barbell).\n"
            "  isSquat: true for barbell squat variants (back squat, front squat, low-bar squat, high-bar squat).\n"
            "  isDeadlift: true for barbell deadlift variants (conventional, sumo, Romanian/RDL, trap-bar deadlift).\n"
            "  All three default to false. Only one flag can be true per exercise.\n"
            "  isTimed: true for exercises measured in time rather than reps (e.g. plank, sled push/pull, farmer carry, L-sit, wall sit, hollow hold). "
            "For timed exercises, each set must use { \"setNumber\": 1, \"timeMinutes\": 1.5, \"isTopSet\": false, \"isWorkingSet\": true } "
            "— omit reps and loadKg entirely. timeMinutes is a decimal number of minutes (e.g. 90 seconds = 1.5).\n"
            "- Run sessions (sessionType = 'run'): set exercises to [] and extract structured run metrics as top-level fields:\n"
            "  'runType': string describing run subtype if visible (e.g. 'easy', 'long run', 'tempo', 'intervals', 'race', 'trail'), else null\n"
            "  'distanceKm': number (e.g. 6.01)\n"
            "  'durationSeconds': integer total seconds (e.g. 1963 for 32:43)\n"
            "  'avgHr': integer bpm (e.g. 152)\n"
            "  'maxHr': integer bpm (e.g. 178)\n"
            "  'avgPaceSecPerKm': integer seconds/km for average pace (e.g. 327 for 5:27/km)\n"
            "  'avgGapPaceSecPerKm': integer seconds/km for Grade Adjusted Pace if shown (e.g. 312 for 5:12/km)\n"
            "  'avgCadence': integer steps per minute (e.g. 170)\n"
            "  'avgGctMs': integer milliseconds for average ground contact time (e.g. 230)\n"
            "  'avgVoCm': number centimetres for average vertical oscillation (e.g. 9.2)\n"
            "  'ascentM': integer metres of total ascent/elevation gain (e.g. 48)\n"
            "  'rpe': number 1–10 for Rate of Perceived Exertion if shown (e.g. 6.5)\n"
            "  Omit any field not visible in the screenshot. Set notes to null.\n"
            "- Non-run cardio/warmup activities inside a strength session have no sets: include them with sets: [].\n"
            "- Warmup detection: for each exercise, sets at the start that are significantly lighter than the "
            "working weight (typically ≤ 60% of the top set weight) should have isWorkingSet: false. "
            "All other sets default to isWorkingSet: true.\n"
            "- Top set: set isTopSet: true for the heaviest working set. In Garmin, bolded or highlighted rows indicate the top set. "
            "For volume_bench sessions, never mark any set as isTopSet: true (volume work has no single top set).\n"
            "- sessionType: derive primarily from the workout title/name shown in the screenshot "
            "(e.g. 'volume bench' → 'volume_bench', 'heavy bench' → 'heavy_bench', 'speed bench' → 'speed_bench'). "
            "If no title, infer from exercises: 'run' for cardio/run, 'pull' for pull-only, "
            "'volume_bench'/'heavy_bench'/'speed_bench' if bench dominant, else 'other'.\n"
            "- Extract the exact session date shown in the screenshot.\n"
            "- Strength/non-run sessions: if the screenshot shows session summary stats (e.g. Garmin header row), "
            "extract these as top-level fields (omit if not visible):\n"
            "  'durationSeconds': integer total seconds for Total Time (e.g. 5830 for 1:37:10)\n"
            "  'workDurationSeconds': integer total seconds for Work Time (e.g. 2731 for 45:31)\n"
            "  'avgHr': integer bpm for Avg HR (e.g. 114)\n"
            "  'calories': integer kcal burned (e.g. 667)\n"
            'If this is not a workout screenshot, return: {"error": "not_a_workout"}'
        )

        try:
            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                messages=[{"role": "user", "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_b64}},
                    {"type": "text", "text": prompt},
                ]}],
            )
        except Exception as exc:
            return ApiResponse(502, {"error": "upstream_error", "detail": str(exc)})

        raw = message.content[0].text.strip()
        print("=== PARSER RAW RESPONSE ===\n", raw, "\n===========================")
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return ApiResponse(422, {"error": "parse_error", "raw": raw})

        if "error" in parsed:
            return ApiResponse(422, {"error": "not_a_workout"})

        if not isinstance(parsed.get("exercises"), list):
            return ApiResponse(422, {"error": "parse_error", "raw": raw})

        return ApiResponse(200, parsed)

    def import_screenshots(self, payload: dict[str, Any]) -> ApiResponse:
        import base64
        import anthropic

        images = payload.get("images", [])
        if not images:
            return ApiResponse(400, {"error": "validation_error", "missing": ["images"]})

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return ApiResponse(500, {"error": "server_error", "detail": "ANTHROPIC_API_KEY not configured"})

        content_blocks: list[dict] = []
        for img in images:
            b64 = img.get("imageBase64")
            media_type = img.get("mediaType", "image/png")
            if not b64:
                return ApiResponse(400, {"error": "validation_error", "detail": "each image must have imageBase64"})
            try:
                base64.b64decode(b64, validate=True)
            except Exception:
                return ApiResponse(400, {"error": "validation_error", "detail": "imageBase64 is not valid base64"})
            content_blocks.append({"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}})

        prompt = (
            f"You are given {len(images)} screenshot(s) from the same workout session in a fitness app "
            "(e.g. Garmin Connect, Strong, Hevy). Combine all screenshots into a single unified session.\n"
            "Extract all exercises and sets across all images. Return ONLY valid JSON — no markdown, no commentary.\n"
            "Schema:\n"
            "{\n"
            '  "sessionDate": "YYYY-MM-DD",\n'
            '  "sessionType": "other",\n'
            '  "notes": null,\n'
            '  "exercises": [\n'
            '    {\n'
            '      "exerciseName": "Bench Press",\n'
            '      "isBarbellBenchPress": false,\n'
            '      "isSquat": false,\n'
            '      "isDeadlift": false,\n'
            '      "isTimed": false,\n'
            '      "sets": [\n'
            '        { "setNumber": 1, "reps": 5, "loadKg": 100.0, "isTopSet": false, "isWorkingSet": true }\n'
            '      ]\n'
            '    }\n'
            '  ]\n'
            "}\n"
            "sessionType must be one of: heavy_bench, volume_bench, speed_bench, squat, deadlift, mix, run, pull, rest, other. Use 'mix' for sessions that combine multiple powerlifting lifts or are labelled 'mixed'.\n"
            "Rules:\n"
            "- Combine exercises from all screenshots into one list. Do not duplicate exercises that appear in multiple screenshots.\n"
            "- Convert lbs to kg (multiply by 0.4536). Use 0 for bodyweight exercises.\n"
            "- Garmin Connect tables have columns: Set, Exercise Name, Time, Rest, Reps, Weight, Volume. "
            "Use the Weight column for loadKg. Do NOT use the Volume column (Weight × Reps) — it is much larger.\n"
            "- Exercise classification flags (set on each exercise object):\n"
            "  isBarbellBenchPress: true for barbell bench press variants (flat, incline, close-grip bench with a barbell).\n"
            "  isSquat: true for barbell squat variants (back squat, front squat, low-bar squat, high-bar squat).\n"
            "  isDeadlift: true for barbell deadlift variants (conventional, sumo, Romanian/RDL, trap-bar deadlift).\n"
            "  All three default to false. Only one flag can be true per exercise.\n"
            "  isTimed: true for exercises measured in time rather than reps (e.g. plank, sled push/pull, farmer carry, L-sit, wall sit, hollow hold). "
            "For timed exercises, each set must use { \"setNumber\": 1, \"timeMinutes\": 1.5, \"isTopSet\": false, \"isWorkingSet\": true } "
            "— omit reps and loadKg entirely. timeMinutes is a decimal number of minutes (e.g. 90 seconds = 1.5).\n"
            "- Run sessions (sessionType = 'run'): set exercises to [] and extract structured run metrics as top-level fields:\n"
            "  'runType': string describing run subtype if visible (e.g. 'easy', 'long run', 'tempo', 'intervals', 'race', 'trail'), else null\n"
            "  'distanceKm': number (e.g. 6.01)\n"
            "  'durationSeconds': integer total seconds (e.g. 1963 for 32:43)\n"
            "  'avgHr': integer bpm (e.g. 152)\n"
            "  'maxHr': integer bpm (e.g. 178)\n"
            "  'avgPaceSecPerKm': integer seconds/km for average pace (e.g. 327 for 5:27/km)\n"
            "  'avgGapPaceSecPerKm': integer seconds/km for Grade Adjusted Pace if shown (e.g. 312 for 5:12/km)\n"
            "  'avgCadence': integer steps per minute (e.g. 170)\n"
            "  'avgGctMs': integer milliseconds for average ground contact time (e.g. 230)\n"
            "  'avgVoCm': number centimetres for average vertical oscillation (e.g. 9.2)\n"
            "  'ascentM': integer metres of total ascent/elevation gain (e.g. 48)\n"
            "  'rpe': number 1–10 for Rate of Perceived Exertion if shown (e.g. 6.5)\n"
            "  Omit any field not visible in the screenshots. Set notes to null.\n"
            "- Non-run cardio/warmup activities inside a strength session have no sets: include them with sets: [].\n"
            "- Warmup detection: for each exercise, sets at the start that are significantly lighter than the "
            "working weight (typically ≤ 60% of the top set weight) should have isWorkingSet: false. "
            "All other sets default to isWorkingSet: true.\n"
            "- Top set: set isTopSet: true for the heaviest working set. In Garmin, bolded or highlighted rows indicate the top set. "
            "For volume_bench sessions, never mark any set as isTopSet: true (volume work has no single top set).\n"
            "- sessionType: derive primarily from the workout title/name shown in the screenshots "
            "(e.g. 'volume bench' → 'volume_bench', 'heavy bench' → 'heavy_bench', 'speed bench' → 'speed_bench'). "
            "If no title, infer from exercises: 'run' for cardio/run, 'pull' for pull-only, "
            "'volume_bench'/'heavy_bench'/'speed_bench' if bench dominant, else 'other'.\n"
            "- Extract the exact session date shown in the screenshots.\n"
            "- Strength/non-run sessions: if any screenshot shows session summary stats (e.g. Garmin header row), "
            "extract these as top-level fields (omit if not visible):\n"
            "  'durationSeconds': integer total seconds for Total Time (e.g. 5830 for 1:37:10)\n"
            "  'workDurationSeconds': integer total seconds for Work Time (e.g. 2731 for 45:31)\n"
            "  'avgHr': integer bpm for Avg HR (e.g. 114)\n"
            "  'calories': integer kcal burned (e.g. 667)\n"
            'If these are not workout screenshots, return: {"error": "not_a_workout"}'
        )
        content_blocks.append({"type": "text", "text": prompt})

        try:
            client = anthropic.Anthropic(api_key=api_key)
            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                messages=[{"role": "user", "content": content_blocks}],
            )
        except Exception as exc:
            return ApiResponse(502, {"error": "upstream_error", "detail": str(exc)})

        raw = message.content[0].text.strip()
        print("=== PARSER RAW RESPONSE (multi) ===\n", raw, "\n====================================")
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return ApiResponse(422, {"error": "parse_error", "raw": raw})

        if "error" in parsed:
            return ApiResponse(422, {"error": "not_a_workout"})

        if not isinstance(parsed.get("exercises"), list):
            return ApiResponse(422, {"error": "parse_error", "raw": raw})

        return ApiResponse(200, parsed)

    # ------------------------------------------------------------------ #
    # Burpee challenge                                                      #
    # ------------------------------------------------------------------ #

    def _resolve_burpee_participant(self, qp: dict) -> "str | None":
        """Map token → participant name. Token is stored in telegram_bot_users."""
        token = qp.get("token", "")
        if not token:
            return None
        row = self._exec(
            "SELECT participant_name FROM telegram_bot_users WHERE token = %s",
            (token,),
        ).fetchone()
        return row["participant_name"] if row else None

    def get_burpee_participants(self, qp: dict) -> ApiResponse:
        me = self._resolve_burpee_participant(qp)
        all_rows = self._exec(
            "SELECT name FROM burpee_participants "
            "UNION "
            "SELECT participant_name AS name FROM telegram_bot_users "
            "UNION "
            "SELECT DISTINCT participant AS name FROM burpee_entries "
            "ORDER BY name"
        ).fetchall()
        all_names = [r["name"] for r in all_rows]

        if me:
            follow_rows = self._exec(
                "SELECT receive_participant FROM telegram_bot_receive r "
                "JOIN telegram_bot_users u ON u.telegram_user_id = r.telegram_user_id "
                "WHERE u.token = %s",
                (qp.get("token", ""),),
            ).fetchall()
            follow_set = {r["receive_participant"] for r in follow_rows}
            # __all__ → return everyone
            if "__all__" in follow_set:
                return ApiResponse(200, {"participants": all_names})
            # specific follow list (or empty) → return only followed + self
            filtered = [n for n in all_names if n == me or n in follow_set]
            return ApiResponse(200, {"participants": filtered})

        return ApiResponse(200, {"participants": all_names})

    def get_burpee_entries(self, qp: dict) -> ApiResponse:
        me = self._resolve_burpee_participant(qp)
        if not me:
            return ApiResponse(401, {"error": "unauthorized"})
        rows = self._exec(
            "SELECT id, participant, entry_date, reps, comment FROM burpee_entries ORDER BY entry_date DESC"
        ).fetchall()
        entries = [
            {"id": r["id"], "participant": r["participant"], "entryDate": str(r["entry_date"]), "reps": r["reps"], "comment": r["comment"]}
            for r in rows
        ]
        return ApiResponse(200, {"entries": entries, "me": me})

    def log_burpee_entry(self, body: dict, qp: dict) -> ApiResponse:
        me = self._resolve_burpee_participant(qp)
        if not me:
            return ApiResponse(401, {"error": "unauthorized"})
        entry_date = body.get("entry_date", "")
        reps       = body.get("reps")
        comment    = body.get("comment") or None
        if not entry_date or not reps:
            return ApiResponse(400, {"error": "invalid_input"})
        r = self._exec(
            """
            INSERT INTO burpee_entries (participant, entry_date, reps, comment)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (participant, entry_date) DO UPDATE SET reps = EXCLUDED.reps, comment = EXCLUDED.comment
            RETURNING id, participant, entry_date, reps, comment
            """,
            (me, entry_date, int(reps), comment),
        ).fetchone()
        self.conn.commit()
        return ApiResponse(200, {"id": r["id"], "participant": r["participant"], "entryDate": str(r["entry_date"]), "reps": r["reps"], "comment": r["comment"]})

    def delete_burpee_entry(self, entry_id: int, qp: dict) -> ApiResponse:
        me = self._resolve_burpee_participant(qp)
        if not me:
            return ApiResponse(401, {"error": "unauthorized"})
        self._exec("DELETE FROM burpee_entries WHERE id = %s AND participant = %s", (entry_id, me))
        self.conn.commit()
        return ApiResponse(200, {"deleted": entry_id})

    def ping_burpee(self, qp: dict) -> ApiResponse:
        me = self._resolve_burpee_participant(qp)
        if me:
            _tg_log(f"👆 App opened\n👤 {me}")
        return ApiResponse(200, {})


def to_http_payload(resp: ApiResponse) -> tuple[int, str]:
    import json
    return resp.status, json.dumps(resp.body)
