"""Every table of the owner's own training data, as plain rows.

For the Data page: see everything that is stored, and copy it straight into a
spreadsheet. Deliberately not a backup format -- it is what a person would want
to read and paste, so values come out as strings already formatted.

What is NOT here, and why: the `move_*` tables hold other people's moves,
names and comments, and `burpee_participants` is other people too. An export
is a copy, and copying someone else's data out of a shared product because it
happens to sit in the same database would be wrong. Only the owner's own
training, health and notebook data is dumped.
"""
from __future__ import annotations

import datetime as _dt
from decimal import Decimal
from typing import Any

# Order matters: this is reading order on the page, not alphabetical. Training
# first, because that is what the app is for; then the body; then the records
# kept by hand; then the daily snacks.
TABLES: tuple[tuple[str, str, str], ...] = (
    ("phases", "Phases", "phase_id"),
    ("sessions", "Sessions", "session_date DESC, session_id DESC"),
    ("session_exercises", "Session exercises", "session_id DESC, exercise_order"),
    ("exercises", "Exercises", "exercise_name"),
    ("exercise_sets", "Sets", "session_exercise_id DESC, set_number"),
    ("bodyweight_log", "Bodyweight", "logged_date DESC"),
    ("confirmed_1rm", "Confirmed 1RM", "1"),
    ("injuries", "Injuries", "1"),
    ("monthly_metrics", "Monthly metrics", "1 DESC"),
    ("monthly_run", "Monthly running", "1 DESC"),
    ("day_notes", "Day notes", "1 DESC"),
    ("notebook_lifts", "Notebook (hand-kept)", "exercise, month"),
    ("pullup_seasons", "Pull-up seasons", "year DESC, season"),
    ("benchmarks", "Benchmarks", "1"),
    ("benchmark_pullup_max_reps", "Benchmark · pull-up max", "1"),
    ("benchmark_run_aerobic_test", "Benchmark · aerobic test", "1"),
    ("exercise_items", "Snacks", "tier, name"),
    ("exercise_history", "Snacks history", "done_at DESC"),
)

# A dump of everything is the one place where a runaway table would matter.
ROW_CAP = 5000


def _cell(v: Any) -> str:
    """One value as the string a person would want pasted into a sheet."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, Decimal):
        # Trailing zeros are noise in a spreadsheet: 74.80 -> 74.8, 5.00 -> 5.
        return format(v.normalize(), "f")
    if isinstance(v, float):
        return repr(round(v, 4)).rstrip("0").rstrip(".") if v % 1 else str(int(v))
    if isinstance(v, (_dt.datetime, _dt.date)):
        return v.isoformat(sep=" ", timespec="seconds") if isinstance(v, _dt.datetime) \
            else v.isoformat()
    s = str(v)
    # Tabs and newlines would break the TSV the page puts on the clipboard.
    return s.replace("\t", " ").replace("\r", " ").replace("\n", " ")


def dump(conn) -> list[dict[str, Any]]:
    """Every table in TABLES that exists, as {name, label, columns, rows}."""
    cur = conn.cursor()
    cur.execute("SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public'")
    present = {r["table_name"] for r in cur.fetchall()}

    out: list[dict[str, Any]] = []
    for name, label, order in TABLES:
        if name not in present:
            continue                       # a table this deployment never created
        cur.execute(f"SELECT * FROM {name} ORDER BY {order} LIMIT {ROW_CAP + 1}")
        rows = cur.fetchall()
        truncated = len(rows) > ROW_CAP
        if truncated:
            rows = rows[:ROW_CAP]
        columns = list(rows[0].keys()) if rows else []
        if not columns:
            # Empty table: still worth showing, so name the columns from the schema.
            cur.execute("SELECT column_name FROM information_schema.columns "
                        "WHERE table_schema = 'public' AND table_name = %s "
                        "ORDER BY ordinal_position", (name,))
            columns = [r["column_name"] for r in cur.fetchall()]
        out.append({
            "name": name,
            "label": label,
            "columns": columns,
            "rows": [[_cell(r[c]) for c in columns] for r in rows],
            "truncated": truncated,
        })
    return out
