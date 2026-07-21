"""REST API for the Exercise Queue web UI (calendar / log / stats).

Token-gated the same way the burpee app is: every request carries ?token=,
resolved against exercise_users.token. Read-only helpers plus the manual
scheduling layer (exercise_schedule) that lets the calendar drag exercises onto
specific days — a manual occurrence overrides the cadence suggestion for that day.

Dispatched from phase_app.api.PhaseApi._handle via a lazy import to avoid a
circular dependency.
"""
from __future__ import annotations

import json
import os
from datetime import date as _date, datetime, timedelta, timezone as _timezone
from typing import Any

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore

from phase_app.api import ApiResponse
from phase_app.exercise_due import first_due, interval_of


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

    def update_exercise(self, ex_id: int, body: dict, qp: dict[str, str]) -> ApiResponse:
        uid = self._uid(qp)
        if uid is None:
            return ApiResponse(401, {"error": "unauthorized"})
        allowed = {
            "name": "name", "description": "description", "scheduleType": "schedule_type",
            "repeatIntervalDays": "repeat_interval_days", "acqIntervalDays": "acq_interval_days",
            "acqTargetSessions": "acq_target_sessions", "focusArea": "focus_area",
            "location": "location", "equipment": "equipment", "loadTag": "load_tag", "status": "status",
        }
        raw = {col: body[key] for key, col in allowed.items() if key in (body or {})}
        if not raw:
            return ApiResponse(400, {"error": "validation_error", "detail": "no updatable fields"})
        int_cols = {"repeat_interval_days", "acq_interval_days", "acq_target_sessions"}
        enums = {"schedule_type": {"queue", "fixed", "acquisition"},
                 "status": {"active", "paused", "parked"}}
        updates: dict[str, Any] = {}
        for col, val in raw.items():
            if col in int_cols:
                updates[col] = int(val) if val not in (None, "") else None
            elif col in enums:
                if val not in enums[col]:
                    return ApiResponse(400, {"error": "validation_error", "detail": f"bad {col}"})
                updates[col] = val
            else:
                updates[col] = val if val != "" else None
        # Keep cadence columns consistent with the chosen schedule type.
        st = updates.get("schedule_type")
        if st == "queue":
            updates.update(repeat_interval_days=None, acq_interval_days=None, acq_target_sessions=None)
        elif st == "fixed":
            updates.update(acq_interval_days=None, acq_target_sessions=None)
        elif st == "acquisition":
            updates["repeat_interval_days"] = None

        cur = self.conn.cursor()
        if "name" in updates and updates["name"]:
            cur.execute(
                "SELECT 1 FROM exercise_items WHERE user_id = %s AND LOWER(name) = LOWER(%s) AND id != %s",
                (uid, updates["name"], ex_id),
            )
            if cur.fetchone():
                return ApiResponse(409, {"error": "duplicate", "detail": "name already exists"})
        set_clause = ", ".join(f"{c} = %s" for c in updates)
        try:
            cur.execute(
                f"UPDATE exercise_items SET {set_clause} WHERE id = %s AND user_id = %s RETURNING *",
                (*updates.values(), ex_id, uid),
            )
            row = cur.fetchone()
        except Exception as exc:
            self.conn.rollback()
            return ApiResponse(400, {"error": "validation_error", "detail": str(exc)})
        if not row:
            return ApiResponse(404, {"error": "not_found"})
        self.conn.commit()
        return ApiResponse(200, self._exercise_row(row))

    def delete_exercise(self, ex_id: int, qp: dict[str, str]) -> ApiResponse:
        uid = self._uid(qp)
        if uid is None:
            return ApiResponse(401, {"error": "unauthorized"})
        cur = self.conn.cursor()
        cur.execute("DELETE FROM exercise_items WHERE id = %s AND user_id = %s", (ex_id, uid))
        self.conn.commit()
        return ApiResponse(200, {"deleted": True, "id": ex_id})

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
            "SELECT s.id, s.exercise_id, s.scheduled_date, s.origin, s.status, e.name, e.description "
            "FROM exercise_schedule s JOIN exercise_items e ON e.id = s.exercise_id "
            "WHERE s.user_id = %s AND s.scheduled_date BETWEEN %s AND %s "
            "ORDER BY s.scheduled_date",
            (uid, start, end),
        )
        rows = [self._occurrence_row(r) for r in cur.fetchall()]

        # Any row (including a 'skipped' tombstone left behind by a single-instance
        # drag) suppresses the cadence ghost for that exercise on that day.
        pinned = {(o["exerciseId"], o["date"]) for o in rows}
        # Tombstones are suppression-only — they aren't shown on the calendar.
        occurrences = [o for o in rows if o["status"] != "skipped"]
        suggestions = self._project_suggestions(cur, uid, start, end, pinned)

        return ApiResponse(200, {"occurrences": occurrences, "suggestions": suggestions})

    @staticmethod
    def _occurrence_row(r) -> dict[str, Any]:
        return {
            "id": r["id"],
            "exerciseId": r["exercise_id"],
            "name": r["name"],                                       # shown on the chip
            "description": r["description"] if "description" in r else None,  # hover tooltip
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
            "SELECT id, name, description, schedule_type, repeat_interval_days, acq_interval_days, last_done_at, anchor_date "
            "FROM exercise_items "
            "WHERE user_id = %s AND status = 'active' AND schedule_type IN ('fixed', 'acquisition')",
            (uid,),
        )
        out: list[dict] = []
        for e in cur.fetchall():
            interval = interval_of(e)
            if not interval:
                continue
            last = e["last_done_at"]
            last_date = (last.date() if hasattr(last, "date") else last) if last else None
            first = first_due(interval, last_date, e["anchor_date"], today)
            if first is None:
                continue
            d = first
            while d < start:
                d += timedelta(days=interval)
            while d <= end:
                if (e["id"], d.isoformat()) not in pinned:
                    out.append({
                        "exerciseId": e["id"],
                        "name": e["name"],
                        "description": e["description"],
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
        cur.execute("SELECT name, description FROM exercise_items WHERE id = %s AND user_id = %s", (ex_id, uid))
        ex = cur.fetchone()
        if not ex:
            return ApiResponse(404, {"error": "not_found"})
        cur.execute(
            "INSERT INTO exercise_schedule (user_id, exercise_id, scheduled_date, origin, status) "
            "VALUES (%s, %s, %s, 'manual', 'planned') "
            "ON CONFLICT (exercise_id, scheduled_date) DO UPDATE SET origin = 'manual', status = 'planned' "
            "RETURNING id, exercise_id, scheduled_date, origin, status",
            (uid, ex_id, d),
        )
        row = cur.fetchone()
        row["name"] = ex["name"]
        row["description"] = ex["description"]
        self._apply_drag_mode(cur, uid, ex_id, d, body)
        self.conn.commit()
        return ApiResponse(201, self._occurrence_row(row))

    def _apply_drag_mode(self, cur, uid: int, ex_id: int, new_date, body: dict) -> None:
        """'shift'  — re-phase the series so every future occurrence follows.
        'single' — only this instance moves; tombstone the day it came from so the
        original cadence ghost doesn't linger."""
        mode = (body or {}).get("mode", "single")
        if mode == "shift":
            cur.execute("UPDATE exercise_items SET anchor_date = %s WHERE id = %s AND user_id = %s",
                        (new_date, ex_id, uid))
            return
        from_date = self._parse_date((body or {}).get("fromDate"))
        if from_date and from_date != new_date:
            cur.execute(
                "INSERT INTO exercise_schedule (user_id, exercise_id, scheduled_date, origin, status) "
                "VALUES (%s, %s, %s, 'manual', 'skipped') "
                "ON CONFLICT (exercise_id, scheduled_date) DO NOTHING",
                (uid, ex_id, from_date),
            )

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
        # 'shift' re-phases the whole series to land on the dropped day.
        if (body or {}).get("mode") == "shift":
            cur.execute("UPDATE exercise_items SET anchor_date = %s WHERE id = %s AND user_id = %s",
                        (d, row["exercise_id"], uid))
        cur.execute("SELECT name, description FROM exercise_items WHERE id = %s", (row["exercise_id"],))
        ex = cur.fetchone() or {}
        row["name"] = ex.get("name")
        row["description"] = ex.get("description")
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
        self._drop_premature_auto(cur, uid, ex_id)
        self.conn.commit()
        return ApiResponse(200, {"done": True, "id": occ_id})

    def _drop_premature_auto(self, cur, uid: int, ex_id: int) -> None:
        """Mirror of exercise_bot._drop_premature_auto — after a completion, bin
        auto-materialised future rows the new rhythm makes too early. Manual
        placements survive; the user put those there on purpose."""
        cur.execute(
            "SELECT schedule_type, repeat_interval_days, acq_interval_days, last_done_at, anchor_date "
            "FROM exercise_items WHERE id = %s AND user_id = %s",
            (ex_id, uid),
        )
        ex = cur.fetchone()
        if not ex or ex["schedule_type"] not in ("fixed", "acquisition"):
            return
        today = self._user_today(cur, uid)
        last = ex["last_done_at"]
        last_date = (last.date() if hasattr(last, "date") else last) if last else None
        nxt = first_due(interval_of(ex), last_date, ex["anchor_date"], today)
        if nxt is None:
            return
        cur.execute(
            "DELETE FROM exercise_schedule WHERE user_id = %s AND exercise_id = %s "
            "AND origin = 'auto' AND status = 'planned' "
            "AND scheduled_date > %s AND scheduled_date < %s",
            (uid, ex_id, today, nxt),
        )

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

    # ── AI slot suggestion ──────────────────────────────────────────────────
    def suggest_slot(self, body: dict, qp: dict[str, str]) -> ApiResponse:
        """Ask Claude where to place a recurring exercise, reasoning from the
        phase-app main-lift week (Tier 1) and existing Movement Snacks (Tier 2).
        Suggestion only — the caller commits it if they accept."""
        uid = self._uid(qp)
        if uid is None:
            return ApiResponse(401, {"error": "unauthorized"})
        ex_id = (body or {}).get("exerciseId")
        if not ex_id:
            return ApiResponse(400, {"error": "validation_error", "detail": "exerciseId required"})
        cur = self.conn.cursor()
        cur.execute(
            "SELECT id, name, description, focus_area, load_tag, schedule_type, "
            "       repeat_interval_days, acq_interval_days, last_done_at "
            "FROM exercise_items WHERE id = %s AND user_id = %s",
            (ex_id, uid),
        )
        ex = cur.fetchone()
        if not ex:
            return ApiResponse(404, {"error": "not_found"})

        today = self._user_today(cur, uid)
        win_start = today + timedelta(days=1)          # earliest we'd place it
        win_end = today + timedelta(days=10)           # planning horizon
        avoid = set((body or {}).get("avoid") or [])   # dates a re-roll should skip

        # Tier 1 — recent + upcoming main-lift days from the phase app.
        cur.execute(
            "SELECT s.session_date, "
            "       BOOL_OR(e.is_squat = 1) AS squat, "
            "       BOOL_OR(e.is_deadlift = 1) AS deadlift, "
            "       BOOL_OR(e.is_barbell_bench_press = 1) AS bench, "
            "       STRING_AGG(DISTINCT s.session_type, ',') AS types "
            "FROM sessions s "
            "LEFT JOIN session_exercises se ON se.session_id = s.session_id "
            "LEFT JOIN exercises e ON e.exercise_id = se.exercise_id "
            "WHERE s.session_date BETWEEN %s AND %s AND COALESCE(s.is_planned, FALSE) = FALSE "
            "GROUP BY s.session_date ORDER BY s.session_date",
            (today - timedelta(days=14), win_end),
        )
        training = []
        for r in cur.fetchall():
            lifts = [n for n, v in (("squat", r["squat"]), ("bench", r["bench"]), ("deadlift", r["deadlift"])) if v]
            training.append({"date": r["session_date"].isoformat(),
                             "weekday": r["session_date"].strftime("%a"),
                             "types": r["types"], "mainLifts": lifts})

        # Tier 2 — already-committed Movement Snacks in the window.
        cur.execute(
            "SELECT s.scheduled_date, e.name FROM exercise_schedule s "
            "JOIN exercise_items e ON e.id = s.exercise_id "
            "WHERE s.user_id = %s AND s.status = 'planned' AND s.scheduled_date BETWEEN %s AND %s "
            "ORDER BY s.scheduled_date",
            (uid, win_start, win_end),
        )
        placed: dict[str, list[str]] = {}
        for r in cur.fetchall():
            placed.setdefault(r["scheduled_date"].isoformat(), []).append(r["name"])

        candidates = []
        d = win_start
        while d <= win_end:
            iso = d.isoformat()
            candidates.append({"date": iso, "weekday": d.strftime("%A"),
                               "scheduled": placed.get(iso, []), "avoid": iso in avoid})
            d += timedelta(days=1)

        interval = interval_of(ex)
        result = self._ask_claude_for_slot(ex, interval, training, candidates)
        if result is None:
            # Heuristic fallback: first non-avoided day with no main lift and this
            # exercise not already there.
            main_days = {t["date"] for t in training if t["mainLifts"]}
            pick = next((c for c in candidates
                         if not c["avoid"] and c["date"] not in main_days
                         and ex["name"] not in c["scheduled"]), None) or candidates[0]
            result = {"date": pick["date"], "rationale": "Picked an open day (AI unavailable)."}

        wd = _date.fromisoformat(result["date"]).strftime("%A")
        return ApiResponse(200, {"date": result["date"], "weekday": wd,
                                 "rationale": result.get("rationale", ""),
                                 "exerciseId": ex["id"], "name": ex["name"]})

    def _ask_claude_for_slot(self, ex, interval, training, candidates):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return None
        prompt = (
            "You help schedule a recurring accessory/mobility exercise into a training week.\n"
            "Pick the single best day for it and explain why in one short sentence.\n\n"
            "EXERCISE TO PLACE:\n"
            f"- name: {ex['name']}\n"
            f"- description: {ex['description'] or '(none)'}\n"
            f"- focus: {ex['focus_area'] or '(none)'}\n"
            f"- load tag: {ex['load_tag'] or '(none)'}\n"
            f"- cadence: every {interval} days\n\n"
            "MAIN LIFTS (Tier 1) — recent and upcoming barbell sessions:\n"
            f"{json.dumps(training, indent=0)}\n\n"
            "CANDIDATE DAYS (choose exactly one 'date' from this list):\n"
            f"{json.dumps(candidates, indent=0)}\n\n"
            "Reason from the exercise itself: infer which muscles/joints it loads and "
            "space it sensibly against the main lifts (e.g. avoid stacking quad-heavy "
            "accessory work the day of or after a heavy squat). Prefer days with lighter "
            "existing load; never choose a day marked \"avoid\": true.\n"
            "Reply with ONLY compact JSON: {\"date\":\"YYYY-MM-DD\",\"rationale\":\"...\"}"
        )
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            message = client.messages.create(
                model="claude-sonnet-4-6", max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()
            data = json.loads(raw)
            valid = {c["date"] for c in candidates if not c["avoid"]}
            if data.get("date") in valid:
                return {"date": data["date"], "rationale": str(data.get("rationale", ""))[:200]}
        except Exception:
            pass
        return None
