import sqlite3

import pytest

from phase_app.db import get_connection, init_db, seed_minimal_bench_data


def setup_db():
    conn = get_connection()
    init_db(conn)
    ids = seed_minimal_bench_data(conn)
    return conn, ids


def test_session_date_must_be_within_phase_window():
    conn, ids = setup_db()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO sessions (phase_id, session_date, session_type)
            VALUES (?, '2026-04-10', 'heavy_bench')
            """,
            (ids["phase_id"],),
        )


def test_set_number_unique_per_session_exercise():
    conn, ids = setup_db()
    session_id = conn.execute(
        """
        INSERT INTO sessions (phase_id, session_date, session_type)
        VALUES (?, '2026-02-14', 'heavy_bench')
        """,
        (ids["phase_id"],),
    ).lastrowid
    se_id = conn.execute(
        "INSERT INTO session_exercises (session_id, exercise_id, exercise_order) VALUES (?, ?, 1)",
        (session_id, ids["exercise_id"]),
    ).lastrowid
    conn.execute(
        "INSERT INTO exercise_sets (session_exercise_id, set_number, reps, load_kg) VALUES (?, 1, 5, 100)",
        (se_id,),
    )

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO exercise_sets (session_exercise_id, set_number, reps, load_kg) VALUES (?, 1, 3, 105)",
            (se_id,),
        )


def test_only_one_top_set_allowed_per_session_exercise():
    conn, ids = setup_db()
    session_id = conn.execute(
        "INSERT INTO sessions (phase_id, session_date, session_type) VALUES (?, '2026-02-15', 'heavy_bench')",
        (ids["phase_id"],),
    ).lastrowid
    se_id = conn.execute(
        "INSERT INTO session_exercises (session_id, exercise_id, exercise_order) VALUES (?, ?, 1)",
        (session_id, ids["exercise_id"]),
    ).lastrowid

    conn.execute(
        "INSERT INTO exercise_sets (session_exercise_id, set_number, reps, load_kg, is_top_set) VALUES (?, 1, 5, 100, 1)",
        (se_id,),
    )

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO exercise_sets (session_exercise_id, set_number, reps, load_kg, is_top_set) VALUES (?, 2, 3, 110, 1)",
            (se_id,),
        )
