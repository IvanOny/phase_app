from phase_app.api import PhaseApi
from phase_app.db import get_connection, init_db, seed_minimal_bench_data


def test_vertical_slice_acceptance_contract():
    conn = get_connection()
    init_db(conn)
    ids = seed_minimal_bench_data(conn)
    api = PhaseApi(conn)

    session = api.handle(
        "POST",
        "/v1/sessions",
        {
            "phaseId": ids["phase_id"],
            "sessionDate": "2026-02-25",
            "sessionType": "heavy_bench",
            "eliteHrvReadiness": 7.6,
            "garminOvernightHrv": 57.4,
        },
    )
    assert session.status == 201
    assert "sleepHours" not in session.body

    se = api.handle(
        "POST",
        f"/v1/sessions/{session.body['sessionId']}/exercises",
        {"exerciseId": ids["exercise_id"], "exerciseOrder": 1},
    )
    assert se.status == 201

    set_resp = api.handle(
        "POST",
        f"/v1/session-exercises/{se.body['sessionExerciseId']}/sets",
        {"setNumber": 1, "reps": 3, "loadKg": 115, "isTopSet": True, "isWorkingSet": True},
    )
    assert set_resp.status == 201
    assert "isTopSet" in set_resp.body

    top = api.handle("GET", f"/v1/metrics/sessions/{session.body['sessionId']}/bench-top-set-e1rm")
    vol = api.handle("GET", f"/v1/metrics/sessions/{session.body['sessionId']}/bench-volume")

    assert top.status == 200
    assert vol.status == 200
    assert top.body["source"] == "live"
    assert vol.body["source"] == "live"
