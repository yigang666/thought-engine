"""Google sign-in for uploading articles.

The session secret is generated and stored under the data directory.
A Google client, when present, is read from that same local config or from
the environment. Neither is written into source.
"""

from __future__ import annotations

import json
import logging
import os
import secrets
import urllib.parse
import urllib.request

from fastapi import Request

from app.storage import data_dir, upsert_user

logger = logging.getLogger("thoughtpage.auth")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"

UNAVAILABLE = "Sign in with Google is not available on this copy yet. You can still read articles."
SIGN_IN_REQUIRED = "Sign in with Google to upload an article."


class AuthError(Exception):
    pass


def google_client() -> tuple[str, str] | None:
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
    if client_id and client_secret:
        return client_id, client_secret
    saved = _local_oauth()
    client_id = str(saved.get("client_id") or "").strip()
    client_secret = str(saved.get("client_secret") or "").strip()
    if client_id and client_secret:
        return client_id, client_secret
    return None


def session_secret() -> str:
    configured = os.environ.get("SESSION_SECRET", "").strip()
    if configured:
        return configured
    path = data_dir() / "session-secret"
    if path.is_file():
        saved = path.read_text(encoding="utf-8").strip()
        if saved:
            return saved
    generated = secrets.token_urlsafe(32)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(generated + "\n", encoding="utf-8")
    path.chmod(0o600)
    return generated


def _local_oauth() -> dict:
    path = data_dir() / "google-oauth.json"
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def current_user(request: Request) -> dict[str, str] | None:
    raw = request.session.get("user")
    if not isinstance(raw, dict):
        return None
    email = str(raw.get("email") or "").strip().lower()
    name = str(raw.get("name") or "").strip() or email
    user_id = str(raw.get("id") or raw.get("sub") or "").strip()
    if "@" not in email or len(email) > 320 or len(name) > 200 or not user_id or len(user_id) > 200:
        return None
    return {"id": user_id[:200], "email": email, "name": name}


def redirect_uri(request: Request) -> str:
    """Return the callback exactly as it is registered for this client.

    The local client file wins. The address in the browser must not replace it,
    or Google rejects the login with redirect_uri_mismatch.
    """
    configured = str(_local_oauth().get("redirect_uri") or "").strip()
    if configured:
        return configured
    explicit = os.environ.get("GOOGLE_REDIRECT_URI", "").strip()
    if explicit:
        return explicit
    return str(request.base_url).rstrip("/") + "/auth/google/callback"


def begin_sign_in(request: Request) -> str:
    client = google_client()
    if client is None:
        raise AuthError(UNAVAILABLE)
    client_id, _secret = client
    state = secrets.token_urlsafe(32)
    callback = redirect_uri(request)
    request.session["oauth_state"] = state
    request.session["oauth_redirect_uri"] = callback
    query = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "redirect_uri": callback,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "prompt": "select_account",
        }
    )
    return f"{GOOGLE_AUTH_URL}?{query}"


def finish_sign_in(request: Request, code: str, state: str) -> dict[str, str]:
    if google_client() is None:
        raise AuthError(UNAVAILABLE)
    expected = str(request.session.get("oauth_state") or "")
    callback = str(request.session.get("oauth_redirect_uri") or "")
    request.session.pop("oauth_state", None)
    request.session.pop("oauth_redirect_uri", None)
    if (
        not expected
        or not callback
        or not state
        or len(state) != len(expected)
        or not secrets.compare_digest(state, expected)
    ):
        raise AuthError("Google sign-in could not be confirmed. Start again from Upload.")
    if not code or len(code) > 2048:
        raise AuthError("Google sign-in did not return a usable code.")
    identity = fetch_google_identity(code, callback)
    saved = upsert_user(user_id=identity["sub"], name=identity["name"], email=identity["email"])
    user = {"id": saved.user_id, "name": saved.name, "email": saved.email}
    request.session["user"] = user
    return user


def fetch_google_identity(code: str, redirect_to: str) -> dict[str, str]:
    client = google_client()
    if client is None:
        raise AuthError(UNAVAILABLE)
    client_id, client_secret = client
    body = urllib.parse.urlencode(
        {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_to,
            "grant_type": "authorization_code",
        }
    ).encode()
    token_request = urllib.request.Request(
        GOOGLE_TOKEN_URL,
        data=body,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    token = _read_json(token_request)
    access_token = token.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise AuthError("Google did not return a sign-in token.")
    info_request = urllib.request.Request(
        GOOGLE_USERINFO_URL,
        headers={"Accept": "application/json", "Authorization": f"Bearer {access_token}"},
    )
    info = _read_json(info_request)
    email = str(info.get("email") or "").strip().lower()
    verified = info.get("email_verified")
    if verified not in {True, "true"} or "@" not in email or len(email) > 320:
        raise AuthError("Google did not provide a verified email address.")
    name = str(info.get("name") or "").strip() or email
    subject = str(info.get("sub") or "").strip()
    if not subject:
        raise AuthError("Google did not provide an account id.")
    return {"email": email, "name": name[:200], "sub": subject[:200]}


def _read_json(request: urllib.request.Request) -> dict:
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        logger.warning("Google sign-in request failed")
        raise AuthError("Google sign-in could not be completed. Try again.") from None
    if not isinstance(payload, dict):
        raise AuthError("Google sign-in could not be completed. Try again.")
    return payload
