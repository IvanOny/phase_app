"""Apply one or more SQL migration files to the database in DATABASE_URL.

    python scripts/run_migration.py 042_move_radar_block.sql
    python scripts/run_migration.py migrations/042_move_radar_block.sql
    python scripts/run_migration.py 042_move_radar_block.sql 043_something.sql
    python scripts/run_migration.py --dry-run 042_move_radar_block.sql

Each file runs in its own transaction: it either applies whole or not at all.
There is no migration ledger in this repo — the files are written to be
re-runnable (CREATE TABLE IF NOT EXISTS, ADD COLUMN IF NOT EXISTS), so running
one twice is a no-op rather than an error.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Migrations carry em dashes in their comments; the Windows console defaults to
# cp1252 and mangles them when --dry-run prints the file.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_MIGRATIONS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "migrations")


def _resolve(name: str) -> str:
    """Accept a path, a bare filename, a name without .sql, or just its number."""
    for candidate in (name, os.path.join(_MIGRATIONS, name),
                      os.path.join(_MIGRATIONS, name + ".sql")):
        if os.path.isfile(candidate):
            return candidate
    # "042" is how anyone actually refers to a migration, so match on the prefix
    # too — but only when it's unambiguous.
    hits = sorted(f for f in os.listdir(_MIGRATIONS) if f.startswith(name))
    if len(hits) == 1:
        return os.path.join(_MIGRATIONS, hits[0])
    if hits:
        sys.exit(f"ERROR: '{name}' matches more than one migration:\n  "
                 + "\n  ".join(hits))
    sys.exit(f"ERROR: no such migration: {name}\n  looked in {_MIGRATIONS}")


def main(argv: list[str]) -> int:
    dry = "--dry-run" in argv
    names = [a for a in argv if not a.startswith("--")]
    if not names:
        sys.exit(__doc__)
    paths = [_resolve(n) for n in names]

    # Before the connection checks: --dry-run only reads files, so it should work
    # on a bare Python with no driver and no DATABASE_URL.
    if dry:
        for p in paths:
            print(f"--- {os.path.basename(p)} " + "-" * 40)
            with open(p, encoding="utf-8") as fh:
                print(fh.read())
        return 0

    # Imported here, not at module scope, for the same reason.
    try:
        from phase_app.db_pg import get_connection
    except ModuleNotFoundError as exc:
        sys.exit(f"ERROR: {exc.name} is missing.\n"
                 f"  pip install -r requirements.txt")

    if not os.environ.get("DATABASE_URL"):
        sys.exit("ERROR: DATABASE_URL is not set.\n"
                 "  PowerShell:  $env:DATABASE_URL = '<supabase connection string>'")

    conn = get_connection()
    try:
        for p in paths:
            with open(p, encoding="utf-8") as fh:
                sql = fh.read()
            try:
                with conn.cursor() as cur:
                    cur.execute(sql)
                conn.commit()
            except Exception as exc:                     # noqa: BLE001 — report and stop
                conn.rollback()
                print(f"ERROR: {os.path.basename(p)} failed, rolled back:\n  {exc}")
                return 1
            print(f"OK   {os.path.basename(p)}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
