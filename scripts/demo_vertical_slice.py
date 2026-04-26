from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phase_app.api import PhaseApi
from phase_app.db import get_connection, init_db, seed_minimal_bench_data


def main() -> None:
    conn = get_connection()
    init_db(conn, force=True)
    ids = seed_minimal_bench_data(conn)
    api = PhaseApi(conn)

    session = api.handle(
        "POST",
        "/v1/sessions",
        {
            "phaseId": ids["phase_id"],
            "sessionDate": "2026-02-14",
            "sessionType": "heavy_bench",
            "eliteHrvReadiness": 7.4,
            "garminOvernightHrv": 58.2,
        },
    )
    session_id = session.body["sessionId"]

    session_exercise = api.handle(
        "POST",
        f"/v1/sessions/{session_id}/exercises",
        {"exerciseId": ids["exercise_id"], "exerciseOrder": 1},
    )
    se_id = session_exercise.body["sessionExerciseId"]

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
    volume = api.handle("GET", f"/v1/metrics/sessions/{session_id}/bench-volume")

    print("session:", session.body)
    print("top_set:", top_set.body)
    print("volume:", volume.body)


if __name__ == "__main__":
    main()
