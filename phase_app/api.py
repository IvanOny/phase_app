from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any

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

        if method == "GET" and re.fullmatch(r"/v1/phases/\d+/progression", path):
            return self.get_phase_progression(int(path.split("/")[3]))

        if method == "POST" and path == "/v1/import/screenshot":
            return self.import_screenshot(body)

        if method == "POST" and path == "/v1/auth/login":
            return self.login(body)

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
        required = ["phaseType", "startDate", "endDate"]
        missing = [field for field in required if field not in payload]
        if missing:
            return ApiResponse(400, {"error": "validation_error", "missing": missing})
        try:
            row = self._exec(
                "INSERT INTO phases (phase_type, start_date, end_date, name, notes) "
                "VALUES (%s, %s, %s, %s, %s) RETURNING phase_id",
                (payload["phaseType"], payload["startDate"], payload["endDate"],
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
            "endDate": payload["endDate"],
            "name": payload.get("name"),
            "notes": payload.get("notes"),
        })

    def create_session(self, payload: dict[str, Any]) -> ApiResponse:
        required = ["phaseId", "sessionDate", "sessionType"]
        missing = [field for field in required if field not in payload]
        if missing:
            return ApiResponse(400, {"error": "validation_error", "missing": missing})
        is_planned = bool(payload.get("isPlanned", False))
        try:
            row = self._exec(
                "INSERT INTO sessions "
                "(phase_id, session_date, session_type, elite_hrv_readiness, garmin_overnight_hrv, notes, is_planned, "
                "distance_km, duration_seconds, avg_hr, avg_pace_sec_per_km, "
                "run_type, max_hr, avg_cadence, avg_gct_ms, avg_vo_cm, ascent_m, rpe, avg_gap_pace_sec_per_km) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                "RETURNING *, COALESCE(is_planned, FALSE) AS is_planned",
                (payload["phaseId"], payload["sessionDate"], payload["sessionType"],
                 payload.get("eliteHrvReadiness"), payload.get("garminOvernightHrv"), payload.get("notes"), is_planned,
                 payload.get("distanceKm"), payload.get("durationSeconds"),
                 payload.get("avgHr"), payload.get("avgPaceSecPerKm"),
                 payload.get("runType"), payload.get("maxHr"),
                 payload.get("avgCadence"), payload.get("avgGctMs"),
                 payload.get("avgVoCm"), payload.get("ascentM"),
                 payload.get("rpe"), payload.get("avgGapPaceSecPerKm")),
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
        required = ["setNumber", "reps", "loadKg"]
        missing = [field for field in required if field not in payload]
        if missing:
            return ApiResponse(400, {"error": "validation_error", "missing": missing})
        try:
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
        return ApiResponse(201, {
            "exerciseSetId": row["exercise_set_id"],
            "sessionExerciseId": session_exercise_id,
            "setNumber": payload["setNumber"],
            "reps": payload["reps"],
            "loadKg": payload["loadKg"],
            "isTopSet": bool(payload.get("isTopSet", False)),
            "isWorkingSet": bool(payload.get("isWorkingSet", True)),
        })

    def get_session(self, session_id: int) -> ApiResponse:
        row = self._exec(
            "SELECT session_id, phase_id, session_date, session_type, elite_hrv_readiness, garmin_overnight_hrv, notes, "
            "COALESCE(is_planned, FALSE) AS is_planned, "
            "distance_km, duration_seconds, avg_hr, avg_pace_sec_per_km, "
            "run_type, max_hr, avg_cadence, avg_gct_ms, avg_vo_cm, ascent_m, rpe, avg_gap_pace_sec_per_km "
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
            "SELECT exercise_set_id, session_exercise_id, set_number, reps, load_kg, is_top_set, is_working_set "
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
        }

    def list_sessions(self, qp: dict[str, str]) -> ApiResponse:
        if "phaseId" not in qp:
            return ApiResponse(400, {"error": "validation_error", "missing": ["phaseId"]})
        rows = self._exec(
            "SELECT session_id, phase_id, session_date, session_type, "
            "elite_hrv_readiness, garmin_overnight_hrv, notes, "
            "COALESCE(is_planned, FALSE) AS is_planned, "
            "distance_km, duration_seconds, avg_hr, avg_pace_sec_per_km, "
            "run_type, max_hr, avg_cadence, avg_gct_ms, avg_vo_cm, ascent_m, rpe, avg_gap_pace_sec_per_km "
            "FROM sessions WHERE phase_id = %s ORDER BY session_date",
            (int(qp["phaseId"]),),
        ).fetchall()
        return ApiResponse(200, {"items": [self._session_row(r) for r in rows]})

    def list_exercises(self) -> ApiResponse:
        rows = self._exec(
            "SELECT exercise_id, exercise_name, is_barbell_bench_press, is_bodyweight "
            "FROM exercises ORDER BY exercise_name"
        ).fetchall()
        return ApiResponse(200, {"items": [{
            "exerciseId": r["exercise_id"],
            "exerciseName": r["exercise_name"],
            "isBarbellBenchPress": bool(r["is_barbell_bench_press"]),
            "isBodyweight": bool(r["is_bodyweight"]),
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
                   "notes": "notes",
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
                "RETURNING *, COALESCE(is_planned, FALSE) AS is_planned",
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
        allowed = {"reps": "reps", "loadKg": "load_kg", "isTopSet": "is_top_set", "isWorkingSet": "is_working_set"}
        raw = {col: payload[key] for key, col in allowed.items() if key in payload}
        if not raw:
            return ApiResponse(400, {"error": "validation_error", "detail": "no updatable fields provided"})
        # coerce booleans to int for DB
        updates = {}
        for col, val in raw.items():
            updates[col] = int(val) if col in ("is_top_set", "is_working_set") else val
        set_clause = ", ".join(f"{col} = %s" for col in updates)
        try:
            cur = self._exec(
                f"UPDATE exercise_sets SET {set_clause} "
                "WHERE exercise_set_id = %s AND session_exercise_id = %s "
                "RETURNING exercise_set_id, session_exercise_id, set_number, reps, load_kg, is_top_set, is_working_set",
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
        try:
            row = self._exec(
                "INSERT INTO exercises (exercise_name, is_barbell_bench_press, is_bodyweight) "
                "VALUES (%s, %s, %s) RETURNING exercise_id",
                (payload["exerciseName"],
                 int(payload.get("isBarbellBenchPress", False)),
                 int(payload.get("isBodyweight", False))),
            ).fetchone()
            self.conn.commit()
        except psycopg2.DatabaseError as exc:
            self.conn.rollback()
            return ApiResponse(400, {"error": "validation_error", "detail": str(exc)})
        return ApiResponse(201, {
            "exerciseId": row["exercise_id"],
            "exerciseName": payload["exerciseName"],
            "isBarbellBenchPress": bool(payload.get("isBarbellBenchPress", False)),
            "isBodyweight": bool(payload.get("isBodyweight", False)),
        })

    def update_exercise(self, exercise_id: int, payload: dict[str, Any]) -> ApiResponse:
        allowed = {"exerciseName": "exercise_name", "isBarbellBenchPress": "is_barbell_bench_press",
                   "isBodyweight": "is_bodyweight"}
        raw = {col: payload[key] for key, col in allowed.items() if key in payload}
        if not raw:
            return ApiResponse(400, {"error": "validation_error", "detail": "no updatable fields provided"})
        updates = {}
        for col, val in raw.items():
            updates[col] = int(val) if col in ("is_barbell_bench_press", "is_bodyweight") else val
        set_clause = ", ".join(f"{col} = %s" for col in updates)
        try:
            cur = self._exec(
                f"UPDATE exercises SET {set_clause} WHERE exercise_id = %s "
                "RETURNING exercise_id, exercise_name, is_barbell_bench_press, is_bodyweight",
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
            "exerciseId": row["exercise_id"],
            "exerciseName": row["exercise_name"],
            "isBarbellBenchPress": bool(row["is_barbell_bench_press"]),
            "isBodyweight": bool(row["is_bodyweight"]),
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
                s.session_id,
                s.session_date,
                s.session_type
              FROM session_exercises se
              JOIN sessions s ON s.session_id = se.session_id
              JOIN exercises e ON e.exercise_id = se.exercise_id
              WHERE s.phase_id = %s
                AND COALESCE(s.is_planned, FALSE) = FALSE
              ORDER BY e.exercise_id, s.session_type, s.session_date DESC, s.session_id DESC
            )
            SELECT
              ls.exercise_id, ls.exercise_name, ls.is_bodyweight, ls.is_barbell_bench_press,
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
            '      "sets": [\n'
            '        { "setNumber": 1, "reps": 5, "loadKg": 100.0, "isTopSet": false, "isWorkingSet": true }\n'
            '      ]\n'
            '    }\n'
            '  ]\n'
            "}\n"
            "sessionType must be one of: heavy_bench, volume_bench, speed_bench, run, pull, other.\n"
            "Rules:\n"
            "- Convert lbs to kg (multiply by 0.4536). Use 0 for bodyweight exercises.\n"
            "- Garmin Connect tables have columns: Set, Exercise Name, Time, Rest, Reps, Weight, Volume. "
            "Use the Weight column for loadKg. Do NOT use the Volume column (Weight × Reps) — it is much larger.\n"
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


def to_http_payload(resp: ApiResponse) -> tuple[int, str]:
    import json
    return resp.status, json.dumps(resp.body)
