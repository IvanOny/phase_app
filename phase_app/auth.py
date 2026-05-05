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


def require_auth(method: str, path: str, auth_header: str | None, secret: str) -> bool:
    """Return True if the request is allowed through.

    Rules:
    - All GET requests: always allowed (public read).
    - POST /v1/auth/login: always allowed (the login endpoint itself).
    - Everything else (POST/PATCH/DELETE): requires a valid Bearer token.
    """
    if method == "GET":
        return True
    if method == "POST" and path == "/v1/auth/login":
        return True
    if not auth_header or not auth_header.startswith("Bearer "):
        return False
    token = auth_header[len("Bearer "):]
    return verify_token(token, secret)
