"""Single-owner login: one password (APP_PASSWORD) exchanged for a signed token.

Tokens are HMAC-signed expiry timestamps, so there's no session table to manage.
Changing SECRET_KEY logs every device out.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import Settings, get_settings

bearer = HTTPBearer(auto_error=False)


def _sign(payload: str, key: str) -> str:
    return hmac.new(key.encode(), payload.encode(), hashlib.sha256).hexdigest()


def issue_token(settings: Settings) -> tuple[str, datetime]:
    exp = int(time.time()) + settings.token_days * 86400
    payload = f"{exp}.{secrets.token_hex(8)}"
    return f"{payload}.{_sign(payload, settings.secret_key)}", datetime.fromtimestamp(exp, timezone.utc)


def verify_token(token: str, settings: Settings) -> bool:
    try:
        exp, nonce, sig = token.split(".")
    except ValueError:
        return False
    if not hmac.compare_digest(sig, _sign(f"{exp}.{nonce}", settings.secret_key)):
        return False
    return exp.isdigit() and int(exp) > time.time()


def check_password(given: str, settings: Settings) -> bool:
    return bool(settings.app_password) and hmac.compare_digest(given.encode(), settings.app_password.encode())


def require_auth(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    settings: Settings = Depends(get_settings),
) -> None:
    if not settings.auth_enabled:
        return
    if creds is None or not verify_token(creds.credentials, settings):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in again.", headers={"WWW-Authenticate": "Bearer"})
