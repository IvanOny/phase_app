"""REST API for the Exercise Queue web UI (calendar / log / stats).

Token-gated the same way the burpee app is: every request carries ?token=,
resolved against exercise_users.token. Read-only helpers plus the manual
scheduling layer (exercise_schedule) that lets the calendar drag exercises onto
specific days — a manual occurrence overrides the cadence suggestion for that day.

Dispatched from phase_app.api.PhaseApi._handle via a lazy import to avoid a
circular dependency.
"""
from __future__ import annotations

from datetime import date as _date, datetime, timedelta, timezone as _timezone
from typing import Any

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore

from phase_app.api import ApiResponse


class ExerciseQueueApi:
    def __init__(self, conn):
        self.conn = conn

    # ── auth ────────────────────────────────────────────────────────────────
    def _uid(self, qp: dict[str, str]) -> int | None:
        token = (qp or {}).get("token", "")
        if not token:
            return None
        cur = self.conn.cursor()
        cur.execute("SELECT id FROM exercise_users WHERE token = %s", (token,))
        row = cur.fetchone()
        return row["id"] if row else None

    @staticmethod
    def _parse_date(s: str | None) -> _date | None:
        if not s:
            return None
        try:
            return _date.fromisoformat(s[:10])
        except ValueError:
            return None

    # ── exercises ───────────────────────────────────────────────────────────
    def list_exercises(self, qp: dict[str, str]) -> ApiResponse:
        uid = self._uid(qp)
        if uid is None:
            return ApiResponse(401, {"error": "unauthorized"})
        cur = self.conn.cursor()
        cur.execute(
            "SELECT id, name, description, schedule_type, repeat_interval_days, "
            "       acq_interval_days, acq_target_sessions, acq_sessions_done, "
            "       focus_area, location, equipment, load_tag, status, last_done_at "
            "FROM exercise_items WHERE user_id = %s ORDER BY schedule_type, name",
            (uid,),
        )
        return ApiResponse(200, {"items": [self._exercise_row(r) for r in cur.fetchall()]})

    @staticmethod
    def _exercise_row(r) -> dict[str, Any]:
        return {
            "id": r["id"],
            "name": r["name"],
            "description": r["description"],
            "scheduleType": r["schedule_type"],
            "repeatIntervalDays": r["repeat_interval_days"],
            "acqIntervalDays": r["acq_interval_days"],
            "acqTargetSessions": r["acq_target_sessions"],
            "acqSessionsDone": r["acq_sessions_done"],
            "focusArea": r["focus_area"],
            "location": r["location"],
            "equipment": r["equipment"],
            "loadTag": r["load_tag"],
            "status": r["status"],
            "lastDoneAt": r["last_done_at"].isoformat() if r["last_done_at"] else None,
        }

    # ── schedule (occurrences) ──────────────────────────────────────────────
    def get_schedule(self, qp: dict[str, str]) -> ApiResponse:
        """Manual occurrences in [from, to] plus on-the-fly cadence suggestions.
        A manual pin for an exercise on a date suppresses that day's suggestion."""
        uid = self._uid(qp)
        if uid is None:
            return ApiResponse(401, {"error": "unauthorized"})
        start = self._parse_date(qp.get("from"))
        end = self._parse_date(qp.get("to"))
        if not start or not end or end < start:
            return ApiResponse(400, {"error": "validation_error", "detail": "from/to required (YYYY-MM-DD)"})

        cur = self.conn.cursor()
        cur.execute(
            "SELECT s.id, s.exercise_id, s.scheduled_date, s.origin, s.status, e.name "
            "FROM exercise_schedule s JOIN exercise_items e ON e.id = s.exercise_id "
            "WHERE s.user_id = %s AND s.scheduled_date BETWEEN %s AND %s "
            "ORDER BY s.scheduled_date",
            (uid, start, end),
        )
        manual = [self._occurrence_row(r) for r in cur.fetchall()]

        # Dates already covered by a manual pin, per exercise — suggestions skip these.
        pinned = {(o["exerciseId"], o["date"]) for o in manual}
        suggestions = self._project_suggestions(cur, uid, start, end, pinned)

        return ApiResponse(200, {"occurrences": manual, "suggestions": suggestions})

    @staticmethod
    def _occurrence_row(r) -> dict[str, Any]:
        return {
            "id": r["id"],
            "exerciseId": r["exercise_id"],
            "name": r["name"],
            "date": r["scheduled_date"].isoformat(),
            "origin": r["origin"],
            "status": r["status"],
        }

    def _user_today(self, cur, uid) -> _date:
        """Today in the user's timezone — must match the bot's due check."""
        cur.execute("SELECT timezone FROM exercise_users WHERE id = %s", (uid,))
        row = cur.fetchone()
        tzname = (row["timezone"] if row else None) or "Europe/Berlin"
        tz = _timezone.utc
        if ZoneInfo is not None:
            try:
                tz = ZoneInfo(tzname)
            except Exception:
                tz = _timezone.utc
        return datetime.now(tz).date()

    def _project_suggestions(self, cur, uid, start, end, pinned) -> list[dict]:
        """Cadence ghosts for fixed/acquisition items, matching the bot's due model:
        never done => due today; overdue => collapses to today (not a stale past
        date); otherwise last_done + interval. Suggestions are forward-looking only."""
        today = self._user_today(cur, uid)
        cur.execute(
            "SELECT id, name, schedule_type, repeat_interval_days, acq_interval_days, last_done_at "
            "FROM exercise_items "
            "WHERE user_id = %s AND status = 'active' AND schedule_type IN ('fixed', 'acquisition')",
            (uid,),
        )
        out: list[dict] = []
        for e in cur.fetchall():
            interval = e["repeat_interval_days"] if e["schedule_type"] == "fixed" else e["acq_interval_days"]
            if not interval or interval < 1:
                continue
            if e["last_done_at"] is None:
                first = today  # bot: never done is due now
            else:
                last = e["last_done_at"]
                last_date = last.date() if hasattr(last, "date") else last
                nxt = last_date + timedelta(days=interval)
                first = nxt if nxt > today else today  # overdue => do it today
            d = first
            while d < start:
                d += timedelta(days=interval)
            while d <= end:
                if (e["id"], d.isoformat()) not in pinned:
                    out.append({
                        "exerciseId": e["id"],
                        "name": e["name"],
                        "date": d.isoformat(),
                        "origin": "auto",
                        "scheduleType": e["schedule_type"],
                    })
                d += timedelta(days=interval)
        return out

    def create_occurrence(self, body: dict, qp: dict[str, str]) -> ApiResponse:
        uid = self._uid(qp)
        if uid is None:
            return ApiResponse(401, {"error": "unauthorized"})
        ex_id = body.get("exerciseId")
        d = self._parse_date(body.get("date"))
        if not ex_id or not d:
            return ApiResponse(400, {"error": "validation_error", "detail": "exerciseId and date required"})
        cur = self.conn.cursor()
        # Ownership check.
        cur.execute("SELECT name FROM exercise_items WHERE id = %s AND user_id = %s", (ex_id, uid))
        ex = cur.fetchone()
        if not ex:
            return ApiResponse(404, {"error": "not_found"})
        cur.execute(
            "INSERT INTO exercise_schedule (user_id, exercise_id, scheduled_date, origin, status) "
            "VALUES (%s, %s, %s, 'manual', 'planned') "
            "ON CONFLICT (exercise_id, scheduled_date) DO UPDATE SET origin = 'manual' "
            "RETURNING id, exercise_id, scheduled_date, origin, status",
            (uid, ex_id, d),
        )
        row = cur.fetchone()
        row["name"] = ex["name"]
        self.conn.commit()
        return ApiResponse(201, self._occurrence_row(row))

    def move_occurrence(self, occ_id: int, body: dict, qp: dict[str, str]) -> ApiResponse:
        uid = self._uid(qp)
        if uid is None:
            return ApiResponse(401, {"error": "unauthorized"})
        d = self._parse_date(body.get("date"))
        if not d:
            return ApiResponse(400, {"error": "validation_error", "detail": "date required"})
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE exercise_schedule SET scheduled_date = %s "
            "WHERE id = %s AND user_id = %s "
            "RETURNING id, exercise_id, scheduled_date, origin, status",
            (d, occ_id, uid),
        )
        row = cur.fetchone()
        if not row:
            return ApiResponse(404, {"error": "not_found"})
        cur.execute("SELECT name FROM exercise_items WHERE id = %s", (row["exercise_id"],))
        row["name"] = (cur.fetchone() or {}).get("name")
        self.conn.commit()
        return ApiResponse(200, self._occurrence_row(row))

    def delete_occurrence(self, occ_id: int, qp: dict[str, str]) -> ApiResponse:
        uid = self._uid(qp)
        if uid is None:
            return ApiResponse(401, {"error": "unauthorized"})
        cur = self.conn.cursor()
        cur.execute("DELETE FROM exercise_schedule WHERE id = %s AND user_id = %s", (occ_id, uid))
        self.conn.commit()
        return ApiResponse(200, {"deleted": True, "id": occ_id})

    def complete_occurrence(self, occ_id: int, qp: dict[str, str]) -> ApiResponse:
        """Mark an occurrence done, log history, and reset the cadence anchor so the
        rhythm continues from when it was actually done. Advances acquisition."""
        uid = self._uid(qp)
        if uid is None:
            return ApiResponse(401, {"error": "unauthorized"})
        cur = self.conn.cursor()
        cur.execute(
            "SELECT s.exercise_id, s.scheduled_date, e.schedule_type, e.acq_sessions_done, e.acq_target_sessions "
            "FROM exercise_schedule s JOIN exercise_items e ON e.id = s.exercise_id "
            "WHERE s.id = %s AND s.user_id = %s",
            (occ_id, uid),
        )
        occ = cur.fetchone()
        if not occ:
            return ApiResponse(404, {"error": "not_found"})
        # You can't have done something that hasn't happened yet.
        if occ["scheduled_date"] > self._user_today(cur, uid):
            return ApiResponse(400, {"error": "future_occurrence",
                                     "detail": "Can't mark a future day as done."})
        ex_id = occ["exercise_id"]
        cur.execute("UPDATE exercise_schedule SET status = 'done' WHERE id = %s", (occ_id,))
        cur.execute(
            "UPDATE exercise_items SET last_done_at = NOW(), consecutive_skips = 0, skipped_until = NULL "
            "WHERE id = %s",
            (ex_id,),
        )
        cur.execute(
            "INSERT INTO exercise_history (user_id, exercise_id, done_at, source) VALUES (%s, %s, NOW(), 'calendar')",
            (uid, ex_id),
        )
        # Acquisition lifecycle — mirror the bot's auto-demote to queue.
        if occ["schedule_type"] == "acquisition":
            done_n = (occ["acq_sessions_done"] or 0) + 1
            target = occ["acq_target_sessions"] or 0
            if done_n >= target:
                cur.execute(
                    "UPDATE exercise_items SET schedule_type = 'queue', acq_sessions_done = 0, "
                    "acq_target_sessions = NULL, acq_interval_days = NULL WHERE id = %s",
                    (ex_id,),
                )
            else:
                cur.execute("UPDATE exercise_items SET acq_sessions_done = %s WHERE id = %s", (done_n, ex_id))
        self.conn.commit()
        return ApiResponse(200, {"done": True, "id": occ_id})

    # ── history + stats ─────────────────────────────────────────────────────
    def get_history(self, qp: dict[str, str]) -> ApiResponse:
        uid = self._uid(qp)
        if uid is None:
            return ApiResponse(401, {"error": "unauthorized"})
        try:
            limit = min(int(qp.get("limit", "50")), 200)
        except ValueError:
            limit = 50
        cur = self.conn.cursor()
        cur.execute(
            "SELECT h.id, h.done_at, h.dose_actual, h.source, h.exercise_id, e.name "
            "FROM exercise_history h LEFT JOIN exercise_items e ON e.id = h.exercise_id "
            "WHERE h.user_id = %s ORDER BY h.done_at DESC LIMIT %s",
            (uid, limit),
        )
        items = [{
            "id": r["id"],
            "exerciseId": r["exercise_id"],
            "name": r["name"],
            "doneAt": r["done_at"].isoformat() if r["done_at"] else None,
            "doseActual": r["dose_actual"],
            "source": r["source"],
        } for r in cur.fetchall()]
        return ApiResponse(200, {"items": items})

    def get_stats(self, qp: dict[str, str]) -> ApiResponse:
        uid = self._uid(qp)
        if uid is None:
            return ApiResponse(401, {"error": "unauthorized"})
        cur = self.conn.cursor()
        cur.execute(
            "SELECT e.id, e.name, e.schedule_type, e.status, "
            "       COUNT(h.id) AS times_done, MAX(h.done_at) AS last_done "
            "FROM exercise_items e LEFT JOIN exercise_history h ON h.exercise_id = e.id "
            "WHERE e.user_id = %s GROUP BY e.id, e.name, e.schedule_type, e.status "
            "ORDER BY times_done DESC, e.name",
            (uid,),
        )
        per_exercise = [{
            "id": r["id"],
            "name": r["name"],
            "scheduleType": r["schedule_type"],
            "status": r["status"],
            "timesDone": r["times_done"] or 0,
            "lastDone": r["last_done"].isoformat() if r["last_done"] else None,
        } for r in cur.fetchall()]

        cur.execute(
            "SELECT COUNT(*) AS total, COUNT(DISTINCT done_at::date) AS active_days "
            "FROM exercise_history WHERE user_id = %s",
            (uid,),
        )
        totals = cur.fetchone()
        return ApiResponse(200, {
            "perExercise": per_exercise,
            "totalDone": totals["total"] or 0,
            "activeDays": totals["active_days"] or 0,
        })
