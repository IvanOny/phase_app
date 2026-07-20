"""Single source of truth for Movement Snacks cadence maths.

The Telegram bot, the web calendar, and the lock-in job all have to agree on
when something is due. Keeping the rule in one place stops them drifting apart.
"""
from __future__ import annotations

from datetime import date as _date, timedelta


def interval_of(ex) -> int | None:
    """Days between repeats, or None if the item has no usable cadence."""
    iv = ex["repeat_interval_days"] if ex["schedule_type"] == "fixed" else ex["acq_interval_days"]
    return iv if iv and iv >= 1 else None


def first_due(interval: int | None, last_date: _date | None, anchor: _date | None, ref: _date):
    """First occurrence due on or after `ref`.

    - `anchor` (set by a "shift series" drag) re-phases the series and wins.
    - Never done  => due as of `ref`.
    - Overdue     => collapses onto `ref`, so pending work rolls forward
                     instead of being stranded on a past date.
    """
    if not interval or interval < 1:
        return None
    if anchor:
        first = anchor
        while first < ref:
            first += timedelta(days=interval)
        while last_date and first <= last_date:
            first += timedelta(days=interval)
        return first
    if last_date is None:
        return ref
    nxt = last_date + timedelta(days=interval)
    return nxt if nxt > ref else ref
