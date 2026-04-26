from phase_app.db import get_connection, init_db, seed_minimal_bench_data


def test_init_db_is_idempotent_without_force():
    conn = get_connection()
    init_db(conn)
    seed_minimal_bench_data(conn)

    # should not crash on repeated calls
    init_db(conn)
    ids = seed_minimal_bench_data(conn)

    assert ids["phase_id"] == 1
    assert ids["exercise_id"] == 1
