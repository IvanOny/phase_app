from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from typing import Any

from phase_app.metrics import get_bench_top_set_e1rm, get_bench_volume


@dataclass
class ApiResponse:
    status: int
    body: dict[str, Any]


class PhaseApi:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def handle(
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

        if method == "GET" and path == "/v1/sessions":
            return self.list_sessions(qp)
        if method == "POST" and path == "/v1/sessions":
            return self.create_session(body)
        if method == "POST" and re.fullmatch(r"/v1/sessions/\d+/exercises", path):
            session_id = int(path.split("/")[3])
            return self.create_session_exercise(session_id, body)
        if method == "POST" and re.fullmatch(r"/v1/session-exercises/\d+/sets", path):
            session_exercise_id = int(path.split("/")[3])
            return self.create_exercise_set(session_exercise_id, body)

        if method == "GET" and re.fullmatch(r"/v1/sessions/\d+", path):
            return self.get_session(int(path.split("/")[3]))
        if method == "GET" and re.fullmatch(r"/v1/sessions/\d+/exercises", path):
            return self.get_session_exercises(int(path.split("/")[3]))
        if method == "GET" and re.fullmatch(r"/v1/session-exercises/\d+/sets", path):
            return self.get_exercise_sets(int(path.split("/")[3]))

        if method == "GET" and path == "/v1/exercises":
            return self.list_exercises()

        if method == "GET" and path == "/v1/benchmarks":
            return self.list_benchmarks(qp)
        if method == "POST" and path == "/v1/benchmarks":
            return self.create_benchmark(body)

        if method == "GET" and re.fullmatch(r"/v1/metrics/sessions/\d+/bench-top-set-e1rm", path):
            return self.get_metric_top_set(int(path.split("/")[4]))
        if method == "GET" and re.fullmatch(r"/v1/metrics/sessions/\d+/bench-volume", path):
            return self.get_metric_bench_volume(int(path.split("/")[4]))

        return ApiResponse(status=404, body={"error": "not_found"})

    def create_phase(self, payload: dict[str, Any]) -> ApiResponse:
        required = ["phaseType", "startDate", "endDate"]
        missing = [field for field in required if field not in payload]
        if missing:
            return ApiResponse(400, {"error": "validation_error", "missing": missing})
        try:
            cursor = self.conn.execute(
                """
                INSERT INTO phases (phase_type, start_date, end_date, name, notes)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    payload["phaseType"],
                    payload["startDate"],
                    payload["endDate"],
                    payload.get("name"),
                    payload.get("notes"),
                ),
            )
            self.conn.commit()
        except sqlite3.IntegrityError as exc:
            return ApiResponse(400, {"error": "validation_error", "detail": str(exc)})
        return ApiResponse(
            201,
            {
                "phaseId": cursor.lastrowid,
                "phaseType": payload["phaseType"],
                "startDate": payload["startDate"],
                "endDate": payload["endDate"],
                "name": payload.get("name"),
                "notes": payload.get("notes"),
            },
        )

    def create_session(self, payload: dict[str, Any]) -> ApiResponse:
        required = ["phaseId", "sessionDate", "sessionType"]
        missing = [field for field in required if field not in payload]
        if missing:
            return ApiResponse(400, {"error": "validation_error", "missing": missing})

        try:
            cursor = self.conn.execute(
                """
                INSERT INTO sessions (phase_id, session_date, session_type, elite_hrv_readiness, garmin_overnight_hrv, notes)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["phaseId"],
                    payload["sessionDate"],
                    payload["sessionType"],
                    payload.get("eliteHrvReadiness"),
                    payload.get("garminOvernightHrv"),
                    payload.get("notes"),
                ),
            )
            self.conn.commit()
        except sqlite3.IntegrityError as exc:
            return ApiResponse(400, {"error": "validation_error", "detail": str(exc)})
        return ApiResponse(
            201,
            {
                "sessionId": cursor.lastrowid,
                "phaseId": payload["phaseId"],
                "sessionDate": payload["sessionDate"],
                "sessionType": payload["sessionType"],
                "eliteHrvReadiness": payload.get("eliteHrvReadiness"),
                "garminOvernightHrv": payload.get("garminOvernightHrv"),
                "notes": payload.get("notes"),
            },
        )

    def create_session_exercise(self, session_id: int, payload: dict[str, Any]) -> ApiResponse:
        required = ["exerciseId", "exerciseOrder"]
        missing = [field for field in required if field not in payload]
        if missing:
            return ApiResponse(400, {"error": "validation_error", "missing": missing})
        try:
            cursor = self.conn.execute(
                """
                INSERT INTO session_exercises (session_id, exercise_id, exercise_order, notes)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, payload["exerciseId"], payload["exerciseOrder"], payload.get("notes")),
            )
            self.conn.commit()
        except sqlite3.IntegrityError as exc:
            return ApiResponse(400, {"error": "validation_error", "detail": str(exc)})
        return ApiResponse(
            201,
            {
                "sessionExerciseId": cursor.lastrowid,
                "sessionId": session_id,
                "exerciseId": payload["exerciseId"],
                "exerciseOrder": payload["exerciseOrder"],
                "notes": payload.get("notes"),
            },
        )

    def create_exercise_set(self, session_exercise_id: int, payload: dict[str, Any]) -> ApiResponse:
        required = ["setNumber", "reps", "loadKg"]
        missing = [field for field in required if field not in payload]
        if missing:
            return ApiResponse(400, {"error": "validation_error", "missing": missing})
        try:
            cursor = self.conn.execute(
                """
                INSERT INTO exercise_sets (session_exercise_id, set_number, reps, load_kg, is_top_set, is_working_set)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session_exercise_id,
                    payload["setNumber"],
                    payload["reps"],
                    payload["loadKg"],
                    int(payload.get("isTopSet", False)),
                    int(payload.get("isWorkingSet", True)),
                ),
            )
            self.conn.commit()
        except sqlite3.IntegrityError as exc:
            return ApiResponse(400, {"error": "validation_error", "detail": str(exc)})
        return ApiResponse(
            201,
            {
                "exerciseSetId": cursor.lastrowid,
                "sessionExerciseId": session_exercise_id,
                "setNumber": payload["setNumber"],
                "reps": payload["reps"],
                "loadKg": payload["loadKg"],
                "isTopSet": bool(payload.get("isTopSet", False)),
                "isWorkingSet": bool(payload.get("isWorkingSet", True)),
            },
        )

    def get_session(self, session_id: int) -> ApiResponse:
        row = self.conn.execute(
            "SELECT session_id, phase_id, session_date, session_type, elite_hrv_readiness, garmin_overnight_hrv, notes FROM sessions WHERE session_id=?",
            (session_id,),
        ).fetchone()
        if row is None:
            return ApiResponse(404, {"error": "not_found"})
        return ApiResponse(
            200,
            {
                "sessionId": row["session_id"],
                "phaseId": row["phase_id"],
                "sessionDate": row["session_date"],
                "sessionType": row["session_type"],
                "eliteHrvReadiness": row["elite_hrv_readiness"],
                "garminOvernightHrv": row["garmin_overnight_hrv"],
                "notes": row["notes"],
            },
        )

    def get_session_exercises(self, session_id: int) -> ApiResponse:
        rows = self.conn.execute(
            "SELECT session_exercise_id, session_id, exercise_id, exercise_order, notes FROM session_exercises WHERE session_id=? ORDER BY exercise_order",
            (session_id,),
        ).fetchall()
        return ApiResponse(
            200,
            {
                "items": [
                    {
                        "sessionExerciseId": row["session_exercise_id"],
                        "sessionId": row["session_id"],
                        "exerciseId": row["exercise_id"],
                        "exerciseOrder": row["exercise_order"],
                        "notes": row["notes"],
                    }
                    for row in rows
                ]
            },
        )

    def get_exercise_sets(self, session_exercise_id: int) -> ApiResponse:
        rows = self.conn.execute(
            "SELECT exercise_set_id, session_exercise_id, set_number, reps, load_kg, is_top_set, is_working_set FROM exercise_sets WHERE session_exercise_id=? ORDER BY set_number",
            (session_exercise_id,),
        ).fetchall()
        return ApiResponse(
            200,
            {
                "items": [
                    {
                        "exerciseSetId": row["exercise_set_id"],
                        "sessionExerciseId": row["session_exercise_id"],
                        "setNumber": row["set_number"],
                        "reps": row["reps"],
                        "loadKg": row["load_kg"],
                        "isTopSet": bool(row["is_top_set"]),
                        "isWorkingSet": bool(row["is_working_set"]),
                    }
                    for row in rows
                ]
            },
        )


    def list_phases(self) -> ApiResponse:
        rows = self.conn.execute(
            "SELECT phase_id, phase_type, start_date, end_date, name, notes FROM phases ORDER BY start_date DESC"
        ).fetchall()
        return ApiResponse(200, {"items": [
            {
                "phaseId": r["phase_id"],
                "phaseType": r["phase_type"],
                "startDate": r["start_date"],
                "endDate": r["end_date"],
                "name": r["name"],
                "notes": r["notes"],
            }
            for r in rows
        ]})

    def list_sessions(self, qp: dict[str, str]) -> ApiResponse:
        if "phaseId" not in qp:
            return ApiResponse(400, {"error": "validation_error", "missing": ["phaseId"]})
        rows = self.conn.execute(
            """
            SELECT session_id, phase_id, session_date, session_type,
                   elite_hrv_readiness, garmin_overnight_hrv, notes
            FROM sessions WHERE phase_id=? ORDER BY session_date
            """,
            (int(qp["phaseId"]),),
        ).fetchall()
        return ApiResponse(200, {"items": [
            {
                "sessionId": r["session_id"],
                "phaseId": r["phase_id"],
                "sessionDate": r["session_date"],
                "sessionType": r["session_type"],
                "eliteHrvReadiness": r["elite_hrv_readiness"],
                "garminOvernightHrv": r["garmin_overnight_hrv"],
                "notes": r["notes"],
            }
            for r in rows
        ]})

    def list_exercises(self) -> ApiResponse:
        rows = self.conn.execute(
            "SELECT exercise_id, exercise_name, is_barbell_bench_press, is_bodyweight FROM exercises ORDER BY exercise_name"
        ).fetchall()
        return ApiResponse(200, {"items": [
            {
                "exerciseId": r["exercise_id"],
                "exerciseName": r["exercise_name"],
                "isBarbellBenchPress": bool(r["is_barbell_bench_press"]),
                "isBodyweight": bool(r["is_bodyweight"]),
            }
            for r in rows
        ]})

    def list_benchmarks(self, qp: dict[str, str]) -> ApiResponse:
        if "phaseId" not in qp:
            return ApiResponse(400, {"error": "validation_error", "missing": ["phaseId"]})
        phase_id = int(qp["phaseId"])

        pullups = self.conn.execute(
            """
            SELECT b.benchmark_id, b.phase_id, b.benchmark_date, b.benchmark_type,
                   p.reps, p.form_standard_version
            FROM benchmarks b
            JOIN benchmark_pullup_max_reps p ON b.benchmark_id = p.benchmark_id
            WHERE b.phase_id=? AND b.benchmark_type='max_bodyweight_pullups'
            ORDER BY b.benchmark_date
            """,
            (phase_id,),
        ).fetchall()

        runs = self.conn.execute(
            """
            SELECT b.benchmark_id, b.phase_id, b.benchmark_date, b.benchmark_type,
                   r.avg_hr, r.target_hr, r.duration_min, r.pace_min_per_km, r.protocol_compliant
            FROM benchmarks b
            JOIN benchmark_run_aerobic_test r ON b.benchmark_id = r.benchmark_id
            WHERE b.phase_id=? AND b.benchmark_type='run_aerobic_test'
            ORDER BY b.benchmark_date
            """,
            (phase_id,),
        ).fetchall()

        items = [
            {
                "benchmarkId": r["benchmark_id"],
                "phaseId": r["phase_id"],
                "benchmarkDate": r["benchmark_date"],
                "benchmarkType": r["benchmark_type"],
                "reps": r["reps"],
                "formStandardVersion": r["form_standard_version"],
            }
            for r in pullups
        ] + [
            {
                "benchmarkId": r["benchmark_id"],
                "phaseId": r["phase_id"],
                "benchmarkDate": r["benchmark_date"],
                "benchmarkType": r["benchmark_type"],
                "avgHr": r["avg_hr"],
                "targetHr": r["target_hr"],
                "durationMin": r["duration_min"],
                "paceMinPerKm": r["pace_min_per_km"],
                "protocolCompliant": bool(r["protocol_compliant"]),
            }
            for r in runs
        ]
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
            has_pace = "paceMinPerKm" in payload
            has_dist = "distanceKm" in payload and "elapsedSec" in payload
            if not has_pace and not has_dist:
                return ApiResponse(400, {"error": "validation_error", "missing": ["paceMinPerKm"]})
        else:
            return ApiResponse(400, {"error": "validation_error", "detail": f"unknown benchmarkType: {btype}"})

        try:
            cursor = self.conn.execute(
                "INSERT INTO benchmarks (phase_id, benchmark_date, benchmark_type, notes) VALUES (?, ?, ?, ?)",
                (payload["phaseId"], payload["benchmarkDate"], btype, payload.get("notes")),
            )
            bid = cursor.lastrowid

            if btype == "max_bodyweight_pullups":
                self.conn.execute(
                    "INSERT INTO benchmark_pullup_max_reps (benchmark_id, reps, form_standard_version) VALUES (?, ?, ?)",
                    (bid, payload["reps"], payload["formStandardVersion"]),
                )
            else:
                self.conn.execute(
                    """
                    INSERT INTO benchmark_run_aerobic_test
                        (benchmark_id, target_hr, duration_min, avg_hr, pace_min_per_km, distance_km, elapsed_sec, protocol_compliant)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        bid,
                        payload.get("targetHr", 140),
                        payload.get("durationMin", 40),
                        payload["avgHr"],
                        payload.get("paceMinPerKm"),
                        payload.get("distanceKm"),
                        payload.get("elapsedSec"),
                        int(payload.get("protocolCompliant", True)),
                    ),
                )
            self.conn.commit()
        except sqlite3.IntegrityError as exc:
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

    def get_metric_top_set(self, session_id: int) -> ApiResponse:
        payload = get_bench_top_set_e1rm(self.conn, session_id)
        if payload is None:
            return ApiResponse(404, {"error": "not_found"})
        return ApiResponse(200, payload)

    def get_metric_bench_volume(self, session_id: int) -> ApiResponse:
        payload = get_bench_volume(self.conn, session_id)
        if payload is None:
            return ApiResponse(404, {"error": "not_found"})
        return ApiResponse(200, payload)

def to_http_payload(resp: ApiResponse) -> tuple[int, str]:
    return resp.status, json.dumps(resp.body)
