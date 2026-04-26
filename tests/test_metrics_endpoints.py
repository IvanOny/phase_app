from phase_app.api import PhaseApi
from phase_app.db import get_connection, init_db, seed_minimal_bench_data


def test_bench_metric_endpoints_live_values():
    conn = get_connection()
    init_db(conn)
    ids = seed_minimal_bench_data(conn)
    api = PhaseApi(conn)

    session = api.handle(
        "POST",
        "/v1/sessions",
        {"phaseId": ids["phase_id"], "sessionDate": "2026-02-20", "sessionType": "heavy_bench"},
    )
    session_id = session.body["sessionId"]
    se = api.handle(
        "POST",
        f"/v1/sessions/{session_id}/exercises",
        {"exerciseId": ids["exercise_id"], "exerciseOrder": 1},
    )
    se_id = se.body["sessionExerciseId"]

    api.handle(
        "POST",
        f"/v1/session-exercises/{se_id}/sets",
        {"setNumber": 1, "reps": 5, "loadKg": 100, "isWorkingSet": True},
    )
    api.handle(
        "POST",
        f"/v1/session-exercises/{se_id}/sets",
        {"setNumber": 2, "reps": 3, "loadKg": 110, "isTopSet": True, "isWorkingSet": True},
    )

    top_set = api.handle("GET", f"/v1/metrics/sessions/{session_id}/bench-top-set-e1rm")
    assert top_set.status == 200
    assert top_set.body["topSetE1rmKg"] == 121.0
    assert top_set.body["source"] == "live"

    volume = api.handle("GET", f"/v1/metrics/sessions/{session_id}/bench-volume")
    assert volume.status == 200
    assert volume.body["benchVolumeKgReps"] == 830.0
    assert volume.body["source"] == "live"
