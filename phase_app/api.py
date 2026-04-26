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

    def handle(self, method: str, path: str, body: dict[str, Any] | None = None) -> ApiResponse:
        body = body or {}
        if method == "POST" and path == "/v1/phases":
            return self.create_phase(body)
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
