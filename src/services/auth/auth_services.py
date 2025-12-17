import datetime
import secrets
import time
from typing import Dict, Optional
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException
from fastapi.responses import RedirectResponse

from src.core.config import settings
from src.common.security import generate_pkce_pair, verify_pkce
from src.models.dto.auth_models import ClientRegistrationRequest


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ACCESS_TOKEN_DEFAULT_TTL = 3600


# ---------------------------------------------------------------------------
# In-memory stores (yes yes, Redis later)
# ---------------------------------------------------------------------------

CLIENTS: Dict[str, dict] = {}
AUTH_REQUESTS: Dict[str, dict] = {}
BROKER_TOKENS: Dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Metadata / utility
# ---------------------------------------------------------------------------

def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "env": settings.ENV,
    }


def protected_resource_metadata():
    return {
        "resource": f"settings.BASE_URL/mcp",
        "authorization_servers": [settings.BASE_URL],
        "scopes_supported": settings.SUPPORTED_SCOPES
    }


def authorization_server_metadata():
    return {
        "issuer": settings.BASE_URL,
        "authorization_endpoint": f"{settings.BASE_URL}/authorize",
        "token_endpoint": f"{settings.BASE_URL}/token",
        "registration_endpoint": f"{settings.BASE_URL}/register",
        "scopes_supported": settings.SUPPORTED_SCOPES,
        "response_types_supported": settings.RESPONSE_TYPES_SUPPORTED,
        "grant_types_supported": settings.GRANT_TYPES_SUPPORTED,
        "code_challenge_methods_supported": settings.CODE_CHALLENGE_METHODS_SUPPORTED,
    }


# ---------------------------------------------------------------------------
# Client registration
# ---------------------------------------------------------------------------

def register_client(payload: ClientRegistrationRequest):
    client_id = secrets.token_urlsafe(16)
    client_secret = secrets.token_urlsafe(32)

    CLIENTS[client_id] = {
        "client_name": payload.client_name,
        "redirect_uris": [str(uri) for uri in payload.redirect_uris],
        "grant_types": payload.grant_types,
        "response_types": payload.response_types,
        "client_secret": client_secret
    }

    return {
        "client_id": client_id,
        "client_secret": client_secret,
    }


# ---------------------------------------------------------------------------
# Authorization endpoint
# ---------------------------------------------------------------------------

def authorize(
    response_type: str,
    client_id: str,
    redirect_uri: str,
    scope: str,
    state: str,
    code_challenge: str,
    code_challenge_method: str,
):
    if response_type not in settings.RESPONSE_TYPES_SUPPORTED:
        raise HTTPException(400, "Unsupported response_type")

    client = CLIENTS.get(client_id)
    if not client:
        raise HTTPException(400, "Invalid client_id")

    if redirect_uri not in client["redirect_uris"]:
        raise HTTPException(400, "Invalid redirect_uri")

    if not code_challenge:
        raise HTTPException(400, "Missing code_challenge")

    if code_challenge_method not in settings.CODE_CHALLENGE_METHODS_SUPPORTED:
        raise HTTPException(400, "Invalid code_challenge_method")

    # Create broker-side auth request
    auth_id = secrets.token_urlsafe(16)
    AUTH_REQUESTS[auth_id] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "original_state": state,
        "original_code_challenge": code_challenge,
        "original_scope": scope,
        "expires_at": datetime.datetime.now() + datetime.timedelta(seconds=settings.AUTH_REQUEST_TTL),
    }
    code_verifier, code_challenge = generate_pkce_pair()
    AUTH_REQUESTS[auth_id]["code_verifier"] = code_verifier

    spotify_params = {
        "client_id": settings.SPOTIFY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": str(settings.SPOTIFY_REDIRECT_URI),
        "scope": settings.SUPPORTED_SCOPES_STR,
        "state": auth_id,  # IMPORTANT
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
    }

    return RedirectResponse(
        f"{settings.SPOTIFY_AUTH_URL}?{urlencode(spotify_params)}"
    )


# ---------------------------------------------------------------------------
# Spotify callback
# ---------------------------------------------------------------------------

async def spotify_callback(code: str, state: Optional[str]):
    auth = AUTH_REQUESTS.get(state, None)
    if not auth:
        raise HTTPException(400, "Invalid or expired state")

    if time.time() > auth["expires_at"]:
        raise HTTPException(400, "Authorization request expired")

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            settings.SPOTIFY_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": str(settings.SPOTIFY_REDIRECT_URI),
                "client_id": settings.SPOTIFY_CLIENT_ID,
                "client_secret": settings.SPOTIFY_CLIENT_SECRET,
                "code_verifier": auth["code_verifier"],
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if resp.status_code != 200:
        raise HTTPException(502, "Spotify token exchange failed")

    tokens = resp.json()

    broker_token = secrets.token_urlsafe(32)
    BROKER_TOKENS[broker_token] = {
        "spotify_access_token": tokens["access_token"],
        "spotify_refresh_token": tokens.get("refresh_token"),
        "expires_at": time.time() + tokens.get("expires_in", ACCESS_TOKEN_DEFAULT_TTL),
        "scope": tokens.get("scope", ""),
        "auth_request_id": state
    }

    redirect_uri = auth["redirect_uri"]
    original_state = auth["original_state"]

    params = {"code": broker_token}
    if original_state:
        params["state"] = original_state

    return RedirectResponse(f"{redirect_uri}?{urlencode(params)}")


# ---------------------------------------------------------------------------
# Token endpoint
# ---------------------------------------------------------------------------

async def issue_token(grant_type: str, code: str, code_verifier: str):
    if grant_type not in settings.GRANT_TYPES_SUPPORTED:
        raise HTTPException(400, "Invalid grant_type")

    token = BROKER_TOKENS.get(code)
    if not token:
        raise HTTPException(400, "Invalid broker token")

    auth_req = AUTH_REQUESTS.pop(token["auth_request_id"], None)
    if not auth_req:
        raise HTTPException(400, "Invalid authorization request")

    verify_pkce(code_verifier, auth_req['original_code_challenge'])

    if time.time() > token["expires_at"]:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                settings.SPOTIFY_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": token["spotify_refresh_token"],
                    "client_id": settings.SPOTIFY_CLIENT_ID,
                    "client_secret": settings.SPOTIFY_CLIENT_SECRET,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        if resp.status_code != 200:
            raise HTTPException(502, "Spotify refresh failed")

        refreshed = resp.json()
        token["spotify_access_token"] = refreshed["access_token"]
        token["expires_at"] = time.time() + refreshed.get(
            "expires_in", ACCESS_TOKEN_DEFAULT_TTL
        )

    return {
        "access_token": token['spotify_access_token'],
        "token_type": "bearer",
        "expires_in": max(0, int(token["expires_at"] - time.time())),
        "scope": token["scope"],
    }
