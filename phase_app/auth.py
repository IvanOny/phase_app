from __future__ import annotations

import hashlib
import hmac
import os
import time


def issue_token(secret: str, ttl: int = 0) -> str:
    """Issue an HMAC-SHA256 signed token.

    ttl=0 (default) means the token never expires.
    Otherwise, ttl is the number of seconds until expiry.
    Token format: "{expiry}.{hmac_hex}"
    """
    expiry = 0 if ttl == 0 else int(time.time()) + ttl
    msg = str(expiry).encode()
    sig = hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()
    return f"{expiry}.{sig}"


def verify_token(token: str, secret: str) -> bool:
    """Verify an HMAC-signed token. Returns True if valid (and not expired)."""
    try:
        expiry_str, sig = token.split(".", 1)
        expiry = int(expiry_str)
        # expiry == 0 means non-expiring; otherwise check against current time
        if expiry != 0 and time.time() > expiry:
            return False
        msg = expiry_str.encode()
        expected = hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, sig)
    except Exception:
        return False


def check_credentials(username: str, password: str) -> bool:
    """Check submitted credentials against APP_USERNAME / APP_PASSWORD env vars."""
    expected_user = os.environ.get("APP_USERNAME", "")
    expected_pass = os.environ.get("APP_PASSWORD", "")
    if not expected_user or not expected_pass:
        return False
    # Use compare_digest to avoid timing attacks
    user_ok = hmac.compare_digest(expected_user, username)
    pass_ok = hmac.compare_digest(expected_pass, password)
    return user_ok and pass_ok


# Who may call what.
#
# Training reads stay public: the dashboard is meant to be viewable logged
# out, and a lift history is not a medical record. Reads about the person --
# recovery metrics, running summaries, injuries, the bodyweight log -- need
# the login, as does every write. A few routes carry their own credential in
# the query string and are left to check it themselves.
PRIVATE_READS = (
    "/v1/monthly-metrics",
    "/v1/monthly-run",
    "/v1/injuries",
    "/v1/bodyweight",
)
_SELF_GUARDED = ("/v1/burpee", "/v1/exq")      # ?token= resolved by the handler
_READ_METHODS = ("GET", "HEAD", "OPTIONS")


def _under(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(prefix + "/")


def needs_auth(method: str, path: str) -> bool:
    """True if this request must carry a valid Bearer token.

    Only /v1/ is policed here. The Telegram webhooks and the cron trigger
    live outside it and have guards of their own.
    """
    if not path.startswith("/v1/"):
        return False
    if path == "/v1/auth/login":
        return False
    if any(_under(path, p) for p in _SELF_GUARDED):
        return False
    if method in _READ_METHODS:
        return any(_under(path, p) for p in PRIVATE_READS)
    return True


def is_authenticated(auth_header: str | None, secret: str) -> bool:
    """A valid, unexpired token signed with `secret`. No secret, no one."""
    if not secret or not auth_header or not auth_header.startswith("Bearer "):
        return False
    return verify_token(auth_header[len("Bearer "):], secret)


def require_auth(method: str, path: str, auth_header: str | None, secret: str) -> bool:
    """Return True if the request is allowed through."""
    return not needs_auth(method, path) or is_authenticated(auth_header, secret)
