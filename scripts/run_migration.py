"""Apply one or more SQL migration files to the database in DATABASE_URL.

    python scripts/run_migration.py 042_move_radar_block.sql
    python scripts/run_migration.py migrations/042_move_radar_block.sql
    python scripts/run_migration.py 042 043
    python scripts/run_migration.py --dry-run 042
    python scripts/run_migration.py --status
    python scripts/run_migration.py --pending
    python scripts/run_migration.py --force 042
    python scripts/run_migration.py --baseline

Each file runs in its own transaction, together with the ledger row recording
it, so the two can't drift apart: it either applies whole and is recorded, or
neither happens.

The ledger is the table `schema_migrations` (see migrations/055). A file that
is already recorded is skipped -- pass --force to run it anyway. Migrations are
still written to be re-runnable where they can be, but the ledger is what makes
a one-way migration safe and lets a second machine catch up.

  --status    what has been applied, what hasn't
  --pending   just the names of unapplied files, one per line
  --baseline  record every file as applied WITHOUT running it. For adopting the
              ledger on a database whose schema is already up to date.
  --force     re-apply even if the ledger says it ran
  --dry-run   print the SQL instead of applying it (works with no database)
"""
from __future__ import annotations

import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Migrations carry em dashes in their comments; the Windows console defaults to
# cp1252 and mangles them when --dry-run prints the file.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MIGRATIONS = os.path.join(_ROOT, "migrations")

# The ledger itself has to exist before anything can be recorded, so its own
# migration is applied first and unconditionally whenever the table is missing.
_LEDGER_FILE = "055_schema_migrations.sql"


def _all_migrations() -> list[str]:
    return sorted(f for f in os.listdir(_MIGRATIONS) if f.endswith(".sql"))


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


def _read(path: str) -> tuple[str, str]:
    with open(path, encoding="utf-8") as fh:
        sql = fh.read()
    return sql, hashlib.sha256(sql.encode("utf-8")).hexdigest()


def _connect():
    # Imported here, not at module scope, so --dry-run works on a bare Python
    # with no driver installed.
    try:
        from phase_app.db_pg import get_connection
    except ModuleNotFoundError as exc:
        sys.exit(f"ERROR: {exc.name} is missing.\n"
                 f"  pip install -r requirements.txt")

    if not os.environ.get("DATABASE_URL"):
        sys.exit("ERROR: DATABASE_URL is not set.\n"
                 "  PowerShell:  $env:DATABASE_URL = '<supabase connection string>'")
    try:
        return get_connection()
    except Exception as exc:                             # noqa: BLE001 — connection advice
        hint = ""
        if "could not translate host name" in str(exc) and ".supabase.co" in str(exc):
            # db.<ref>.supabase.co is IPv6-only. Vercel has IPv6 so production is
            # fine; most home networks don't, and the failure surfaces as a DNS
            # error that reads like a typo.
            hint = ("\n  That host is IPv6-only and this network has no IPv6.\n"
                    "  Use the Session pooler string instead (Supabase -> Connect):\n"
                    "    postgresql://postgres.<ref>:<pw>@aws-0-<region>.pooler.supabase.com:5432/postgres")
        sys.exit(f"ERROR: could not connect:\n  {exc}{hint}")


def _ensure_ledger(conn) -> None:
    """Create schema_migrations if it isn't there yet, and record its own file."""
    sql, checksum = _read(os.path.join(_MIGRATIONS, _LEDGER_FILE))
    with conn.cursor() as cur:
        cur.execute(sql)
        cur.execute("INSERT INTO schema_migrations (filename, checksum) VALUES (%s, %s) "
                    "ON CONFLICT (filename) DO NOTHING", (_LEDGER_FILE, checksum))
    conn.commit()


def _applied(conn) -> dict:
    with conn.cursor() as cur:
        cur.execute("SELECT filename, applied_at, checksum FROM schema_migrations")
        rows = cur.fetchall()
    # get_connection hands back dict rows, but don't depend on it here — this
    # script is the thing you reach for when the database is in an odd state.
    out = {}
    for r in rows:
        if isinstance(r, dict):
            out[r["filename"]] = (r["applied_at"], r["checksum"])
        else:
            out[r[0]] = (r[1], r[2])
    return out


def _status(conn) -> int:
    applied = _applied(conn)
    files = _all_migrations()
    for f in files:
        if f not in applied:
            print(f"  PENDING  {f}")
            continue
        when, checksum = applied[f]
        _, now = _read(os.path.join(_MIGRATIONS, f))
        changed = "  (file has changed since it ran)" if checksum and checksum != now else ""
        print(f"  applied  {f}  {when:%Y-%m-%d %H:%M}{changed}")
    orphans = sorted(set(applied) - set(files))
    for f in orphans:
        print(f"  ?        {f}  recorded, but no such file in migrations/")
    pending = [f for f in files if f not in applied]
    print(f"\n{len(files) - len(pending)} applied, {len(pending)} pending"
          + (f", {len(orphans)} recorded with no file" if orphans else ""))
    return 0


def _baseline(conn) -> int:
    """Adopt the ledger on a database that is already up to date."""
    files = _all_migrations()
    applied = _applied(conn)
    new = [f for f in files if f not in applied]
    with conn.cursor() as cur:
        for f in new:
            _, checksum = _read(os.path.join(_MIGRATIONS, f))
            cur.execute("INSERT INTO schema_migrations (filename, checksum) VALUES (%s, %s) "
                        "ON CONFLICT (filename) DO NOTHING", (f, checksum))
    conn.commit()
    print(f"recorded {len(new)} migration(s) as applied without running them:")
    for f in new:
        print(f"  {f}")
    if not new:
        print("  (nothing to do — every file was already in the ledger)")
    return 0


def main(argv: list[str]) -> int:
    flags = {a for a in argv if a.startswith("--")}
    unknown = flags - {"--dry-run", "--status", "--pending", "--baseline", "--force"}
    if unknown:
        sys.exit(f"ERROR: unknown option(s): {', '.join(sorted(unknown))}\n\n{__doc__}")
    names = [a for a in argv if not a.startswith("--")]

    # --dry-run only reads files, so it comes before any connection handling.
    if "--dry-run" in flags:
        if not names:
            sys.exit(__doc__)
        for p in (_resolve(n) for n in names):
            print(f"--- {os.path.basename(p)} " + "-" * 40)
            print(_read(p)[0])
        return 0

    if not names and not (flags & {"--status", "--pending", "--baseline"}):
        sys.exit(__doc__)

    conn = _connect()
    try:
        _ensure_ledger(conn)
        if "--status" in flags:
            return _status(conn)
        if "--pending" in flags:
            applied = _applied(conn)
            for f in _all_migrations():
                if f not in applied:
                    print(f)
            return 0
        if "--baseline" in flags:
            return _baseline(conn)

        applied = _applied(conn)
        for path in (_resolve(n) for n in names):
            name = os.path.basename(path)
            sql, checksum = _read(path)
            if name in applied and "--force" not in flags:
                when, _ = applied[name]
                print(f"SKIP {name}  (applied {when:%Y-%m-%d %H:%M} — use --force to re-run)")
                continue
            try:
                # The ledger row goes in the same transaction as the migration:
                # a migration that applied but wasn't recorded would be re-run
                # next time, which is exactly what the ledger exists to prevent.
                with conn.cursor() as cur:
                    cur.execute(sql)
                    cur.execute(
                        "INSERT INTO schema_migrations (filename, checksum) VALUES (%s, %s) "
                        "ON CONFLICT (filename) DO UPDATE SET applied_at = NOW(), "
                        "checksum = EXCLUDED.checksum", (name, checksum))
                conn.commit()
            except Exception as exc:                     # noqa: BLE001 — report and stop
                conn.rollback()
                print(f"ERROR: {name} failed, rolled back (and not recorded):\n  {exc}")
                return 1
            print(f"OK   {name}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
