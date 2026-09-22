"""Parse one row of Garmin's monthly running table, pasted as-is.

The row is what the browser puts on the clipboard when you select a line of
Garmin Connect's report: the month, then twenty-two tab-separated cells with
their units still attached -- `96.12 km`, `9:33:33 h:m:s`, `5:58 /km`,
`6,986`. This turns it into typed numbers, and says exactly which cell it
could not read rather than saving twenty-one of twenty-two.
"""
from __future__ import annotations

import re

MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}

# (key, kind) in Garmin's column order, after the month.
#   num  -> a number, units stripped, thousands separators removed
#   int  -> the same, rounded to an integer
#   hms  -> h:mm:ss or m:ss, to seconds
#   pace -> m:ss (per km), to seconds per km
COLUMNS = [
    ("activities",        "int"),
    ("totalKm",           "num"),
    ("avgKm",             "num"),
    ("maxKm",             "num"),
    ("totalTimeS",        "hms"),
    ("calories",          "int"),
    ("totalAscentM",      "int"),
    ("avgAscentM",        "int"),
    ("maxAscentM",        "int"),
    ("totalDescentM",     "int"),
    ("avgDescentM",       "int"),
    ("maxDescentM",       "int"),
    ("avgPaceS",          "pace"),
    ("gapPaceS",          "pace"),
    ("bestPaceS",         "pace"),
    ("avgHr",             "int"),
    ("maxHr",             "int"),
    ("avgCadenceSpm",     "int"),
    ("maxCadenceSpm",     "int"),
    ("verticalOscCm",     "num"),
    ("groundContactMs",   "int"),
    ("avgStrideM",        "num"),
]

LABELS = {
    "activities": "Activities", "totalKm": "Total distance", "avgKm": "Average distance",
    "maxKm": "Max distance", "totalTimeS": "Total activity time", "calories": "Activity calories",
    "totalAscentM": "Total ascent", "avgAscentM": "Avg ascent", "maxAscentM": "Max ascent",
    "totalDescentM": "Total descent", "avgDescentM": "Avg descent", "maxDescentM": "Max descent",
    "avgPaceS": "Average pace", "gapPaceS": "Grade-adjusted pace", "bestPaceS": "Best pace",
    "avgHr": "Average heart rate", "maxHr": "Max heart rate", "avgCadenceSpm": "Average run cadence",
    "maxCadenceSpm": "Max run cadence", "verticalOscCm": "Vertical oscillation",
    "groundContactMs": "Ground contact time", "avgStrideM": "Average stride length",
}


class ParseError(ValueError):
    pass


def parse_month(cell: str) -> str:
    """'Sep 2026', 'September 2026' or '2026-09' -> '2026-09'."""
    c = cell.strip()
    m = re.fullmatch(r"(\d{4})-(0[1-9]|1[0-2])", c)
    if m:
        return c
    m = re.fullmatch(r"([A-Za-z]+)\.?\s+(\d{4})", c)
    if m and m.group(1)[:3].lower() in MONTHS:
        return f"{m.group(2)}-{MONTHS[m.group(1)[:3].lower()]:02d}"
    raise ParseError(f"month: could not read {cell!r}")


def _number(cell: str, label: str) -> float:
    m = re.match(r"\s*(-?[\d,]*\.?\d+)", cell)
    if not m:
        raise ParseError(f"{label}: could not read {cell!r}")
    return float(m.group(1).replace(",", ""))


def _clock(cell: str, label: str) -> int:
    """'9:33:33 h:m:s' or '5:58 /km' -> seconds. Two or three parts."""
    m = re.match(r"\s*(\d+):(\d{2})(?::(\d{2}))?", cell)
    if not m:
        raise ParseError(f"{label}: could not read {cell!r}")
    a, b, c = m.group(1), m.group(2), m.group(3)
    if c is not None:
        return int(a) * 3600 + int(b) * 60 + int(c)
    return int(a) * 60 + int(b)


def parse_row(raw: str) -> dict:
    """The pasted line -> {'month': 'YYYY-MM', <22 typed fields>, 'raw': line}.

    Tabs are the separator -- that is what a table row puts on the clipboard.
    A line with the wrong number of cells is refused with the count, since a
    missing cell would shift every column after it onto the wrong metric.
    """
    line = raw.strip().replace("\r", "")
    if "\n" in line:
        raise ParseError("one row at a time -- paste a single line")
    cells = line.split("\t")
    if len(cells) != len(COLUMNS) + 1:
        raise ParseError(f"expected {len(COLUMNS) + 1} tab-separated cells, got {len(cells)}")
    out = {"month": parse_month(cells[0]), "raw": line}
    for (key, kind), cell in zip(COLUMNS, cells[1:]):
        label = LABELS[key]
        if kind == "num":
            out[key] = _number(cell, label)
        elif kind == "int":
            out[key] = int(round(_number(cell, label)))
        else:                                  # hms, pace
            out[key] = _clock(cell, label)
    return out


def fmt_clock(seconds: int | None, pace: bool = False) -> str:
    """Back the other way, for display: 34413 -> '9:33:33', 358 -> '5:58'."""
    if seconds is None:
        return ""
    s = int(seconds)
    if pace or s < 3600:
        return f"{s // 60}:{s % 60:02d}"
    return f"{s // 3600}:{(s % 3600) // 60:02d}:{s % 60:02d}"
