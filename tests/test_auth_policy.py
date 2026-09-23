"""Who may call what: the policy in phase_app/auth.py, and api/index.py
enforcing it.

The Flask tests only exercise refusals and the login exemption's policy, so
they never reach the database -- a refused request returns before a
connection is opened.
"""
import importlib.util
import os
from pathlib import Path

from phase_app.auth import issue_token, needs_auth, require_auth

SECRET = "test-secret"


def _bearer(secret=SECRET, ttl=0):
    return "Bearer " + issue_token(secret, ttl)


# --------------------------------------------------------------------------- #
# Policy                                                                      #
# --------------------------------------------------------------------------- #

def test_training_reads_stay_public():
    for path in ("/v1/phases", "/v1/sessions", "/v1/exercises",
                 "/v1/metrics/session-pl-metrics", "/v1/metrics/phases/19/classification"):
        assert not needs_auth("GET", path), path


def test_health_reads_need_the_login():
    for path in ("/v1/monthly-metrics", "/v1/monthly-run", "/v1/injuries", "/v1/bodyweight"):
        assert needs_auth("GET", path), path
    # A prefix is a path segment, not a string prefix.
    assert not needs_auth("GET", "/v1/bodyweight-standards")


def test_every_write_needs_the_login():
    for method, path in (("POST", "/v1/sessions"), ("PATCH", "/v1/sessions/5"),
                         ("DELETE", "/v1/sessions/5"), ("POST", "/v1/injuries"),
                         ("PATCH", "/v1/injuries/3"), ("POST", "/v1/monthly-run"),
                         ("DELETE", "/v1/bodyweight/7")):
        assert needs_auth(method, path), (method, path)


def test_exemptions():
    assert not needs_auth("POST", "/v1/auth/login")
    # Burpee and the exercise queue check their own ?token=.
    assert not needs_auth("POST", "/v1/burpee")
    assert not needs_auth("DELETE", "/v1/burpee/12")
    assert not needs_auth("POST", "/v1/exq/chat")
    # Outside /v1/: webhooks and cron guard themselves.
    assert not needs_auth("POST", "/api/move")
    assert not needs_auth("POST", "/api/cron/move")


def test_require_auth_checks_the_token():
    assert require_auth("POST", "/v1/sessions", _bearer(), SECRET)
    assert not require_auth("POST", "/v1/sessions", None, SECRET)
    assert not require_auth("POST", "/v1/sessions", "Bearer nonsense", SECRET)
    assert not require_auth("POST", "/v1/sessions", _bearer("other-secret"), SECRET)
    assert not require_auth("POST", "/v1/sessions", _bearer(ttl=-10), SECRET)   # expired
    # No secret configured means nobody gets in, not everybody.
    assert not require_auth("POST", "/v1/sessions", _bearer(""), "")
    # Public reads need nothing.
    assert require_auth("GET", "/v1/phases", None, SECRET)


# --------------------------------------------------------------------------- #
# api/index.py                                                                #
# --------------------------------------------------------------------------- #

def _app():
    os.environ["TOKEN_SECRET"] = SECRET
    spec = importlib.util.spec_from_file_location(
        "vercel_index", Path(__file__).resolve().parent.parent / "api" / "index.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.app.test_client()


def test_index_refuses_anonymous_writes_and_health_reads():
    client = _app()
    assert client.post("/v1/sessions", json={}).status_code == 401
    assert client.delete("/v1/injuries/1").status_code == 401
    assert client.get("/v1/monthly-metrics").status_code == 401
    assert client.get("/v1/bodyweight?phaseId=19").status_code == 401
    bad = {"Authorization": "Bearer 0.deadbeef"}
    assert client.get("/v1/injuries", headers=bad).status_code == 401


def test_index_preflight_is_not_refused():
    client = _app()
    assert client.open("/v1/injuries", method="OPTIONS").status_code == 204


if __name__ == "__main__":
    # pytest isn't installed on this machine; run the functions directly.
    import sys
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("PASS", name)
            except AssertionError as exc:
                failed += 1
                print("FAIL", name, exc)
    sys.exit(1 if failed else 0)
