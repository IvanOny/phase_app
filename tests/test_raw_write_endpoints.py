from phase_app.api import PhaseApi
from phase_app.db import get_connection, init_db, seed_minimal_bench_data


def build_api():
    conn = get_connection()
    init_db(conn)
    ids = seed_minimal_bench_data(conn)
    return PhaseApi(conn), ids


def test_create_phase():
    api, _ = build_api()
    resp = api.handle(
        "POST",
        "/v1/phases",
        {
            "phaseType": "run",
            "startDate": "2026-04-01",
            "endDate": "2026-05-01",
            "name": "Run block",
        },
    )
    assert resp.status == 201
    assert resp.body["phaseType"] == "run"


def test_create_session_exercise_and_set():
    api, ids = build_api()

    session_resp = api.handle(
        "POST",
        "/v1/sessions",
        {
            "phaseId": ids["phase_id"],
            "sessionDate": "2026-02-14",
            "sessionType": "heavy_bench",
            "eliteHrvReadiness": 7.2,
        },
    )
    assert session_resp.status == 201

    se_resp = api.handle(
        "POST",
        f"/v1/sessions/{session_resp.body['sessionId']}/exercises",
        {"exerciseId": ids["exercise_id"], "exerciseOrder": 1},
    )
    assert se_resp.status == 201

    set_resp = api.handle(
        "POST",
        f"/v1/session-exercises/{se_resp.body['sessionExerciseId']}/sets",
        {
            "setNumber": 1,
            "reps": 4,
            "loadKg": 110,
            "isTopSet": True,
            "isWorkingSet": True,
        },
    )
    assert set_resp.status == 201
    assert set_resp.body["isTopSet"] is True


def test_constraint_error_bubbles_as_validation_error():
    api, ids = build_api()
    resp = api.handle(
        "POST",
        "/v1/sessions",
        {
            "phaseId": ids["phase_id"],
            "sessionDate": "2026-04-14",
            "sessionType": "heavy_bench",
        },
    )
    assert resp.status == 400
    assert resp.body["error"] == "validation_error"
