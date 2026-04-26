from phase_app.api import PhaseApi
from phase_app.db import get_connection, init_db, seed_minimal_bench_data


def test_read_back_session_exercises_and_sets():
    conn = get_connection()
    init_db(conn)
    ids = seed_minimal_bench_data(conn)
    api = PhaseApi(conn)

    session = api.handle(
        "POST",
        "/v1/sessions",
        {
            "phaseId": ids["phase_id"],
            "sessionDate": "2026-02-22",
            "sessionType": "heavy_bench",
            "eliteHrvReadiness": 8.1,
            "garminOvernightHrv": 61.2,
        },
    )
    session_id = session.body["sessionId"]

    se = api.handle(
        "POST",
        f"/v1/sessions/{session_id}/exercises",
        {"exerciseId": ids["exercise_id"], "exerciseOrder": 1, "notes": "Comp bench"},
    )
    se_id = se.body["sessionExerciseId"]

    api.handle(
        "POST",
        f"/v1/session-exercises/{se_id}/sets",
        {"setNumber": 1, "reps": 5, "loadKg": 100.0, "isWorkingSet": True},
    )
    api.handle(
        "POST",
        f"/v1/session-exercises/{se_id}/sets",
        {"setNumber": 2, "reps": 3, "loadKg": 110.0, "isTopSet": True, "isWorkingSet": True},
    )

    read_session = api.handle("GET", f"/v1/sessions/{session_id}")
    assert read_session.status == 200
    assert read_session.body["sessionType"] == "heavy_bench"

    read_exercises = api.handle("GET", f"/v1/sessions/{session_id}/exercises")
    assert read_exercises.status == 200
    assert len(read_exercises.body["items"]) == 1

    read_sets = api.handle("GET", f"/v1/session-exercises/{se_id}/sets")
    assert read_sets.status == 200
    assert len(read_sets.body["items"]) == 2
    assert read_sets.body["items"][1]["isTopSet"] is True
