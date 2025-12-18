import secrets
import time
from typing import Dict, Optional, List
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException
from fastapi.responses import RedirectResponse
from pydantic import HttpUrl

from src.common.token import JWTService
from src.core.config import settings
from src.common.security import generate_pkce_pair, verify_pkce


# ---------------------------------------------------------------------------
# In-memory stores (yes yes, Redis later)
# ---------------------------------------------------------------------------

CLIENTS: Dict[str, dict] = {}
AUTH_REQUESTS: Dict[str, dict] = {}
SPOTIFY_TOKENS: Dict[str, dict] = {}


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

def register_client(client_name: str, redirect_uris: List[HttpUrl], grant_types: List[str], response_types: List[str]):
    if not redirect_uris:
        raise HTTPException(400, "redirect_uris required")

    allowed_grants = list(set(grant_types) & set(settings.GRANT_TYPES_SUPPORTED))
    if not allowed_grants:
        raise HTTPException(400, f"Unsupported grant_type provided. supported grant_types: {settings.GRANT_TYPES_SUPPORTED}")

    allowed_responses = list(set(response_types) & set(settings.RESPONSE_TYPES_SUPPORTED))
    if not allowed_responses:
        raise HTTPException(400, f"Unsupported response_type provided. supported response_type : {settings.RESPONSE_TYPES_SUPPORTED}")

    client_id = secrets.token_urlsafe(16)
    client_secret = None
    if settings.TOKEN_ENDPOINT_AUTH_METHOD != "none":
        client_secret = secrets.token_urlsafe(32)

    CLIENTS[client_id] = {
        "client_id": client_id,
        "client_secret": client_secret,
        "client_id_issued_at": int(time.time()),
        "client_secret_expires_at": 0,
        "client_name": client_name,
        "redirect_uris": [str(uri) for uri in redirect_uris],
        "grant_types": allowed_grants,
        "response_types": allowed_responses,
        "token_endpoint_auth_method": settings.TOKEN_ENDPOINT_AUTH_METHOD,
    }

    return CLIENTS[client_id]


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
    auth_id = secrets.token_urlsafe(32)
    AUTH_REQUESTS[auth_id] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "original_state": state,
        "original_code_challenge": code_challenge,
        "original_scope": scope,
        "expires_at": time.time() + settings.AUTH_REQUEST_TTL,
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

def spotify_callback(code: str, state: Optional[str]):
    auth = AUTH_REQUESTS.get(state, None)
    if not auth:
        raise HTTPException(400, "Invalid or expired authorization request")

    if time.time() > auth["expires_at"]:
        del AUTH_REQUESTS[state]
        raise HTTPException(400, "Authorization request expired")

    auth['code'] = code

    redirect_uri = auth["redirect_uri"]
    original_state = auth["original_state"]

    params = {"code": state}
    if original_state:
        params["state"] = original_state

    return RedirectResponse(f"{redirect_uri}?{urlencode(params)}")


# ---------------------------------------------------------------------------
# Token endpoint
# ---------------------------------------------------------------------------

async def issue_token(
        grant_type: str,
        client_id: str,
        code: Optional[str]=None,
        redirect_uri: Optional[HttpUrl]=None,
        code_verifier: Optional[str]=None,
        client_secret: Optional[str]=None,
        refresh_token: Optional[str]=None,
):
    if grant_type not in settings.GRANT_TYPES_SUPPORTED:
        raise HTTPException(400, "Invalid grant_type")

    client = CLIENTS.get(client_id, None)

    if not client:
        raise HTTPException(400, "Invalid client_id")

    if settings.TOKEN_ENDPOINT_AUTH_METHOD == 'client_secret_post' and (
            not client_secret or client_secret != client['client_secret']):
        raise HTTPException(400, "Invalid client_secret")

    if grant_type == "authorization_code":
        return await _code_grant(client_id, code, redirect_uri, code_verifier)
    elif grant_type == "refresh_token":
        return await _refresh_grant(client_id, refresh_token)
    else:
        raise HTTPException(400, "Invalid grant_type")


async def _code_grant(client_id: str, code: str, redirect_uri: HttpUrl, code_verifier: str):
    auth_req = AUTH_REQUESTS.pop(code, None)
    if not auth_req:
        raise HTTPException(400, "Invalid authorization request")

    if str(redirect_uri) != auth_req["redirect_uri"]:
        raise HTTPException(400, "Invalid redirect_uri")

    verify_pkce(code_verifier, auth_req['original_code_challenge'])

    token_service = JWTService()
    token_id = secrets.token_urlsafe(16)

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            settings.SPOTIFY_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": auth_req['code'],
                "redirect_uri": str(settings.SPOTIFY_REDIRECT_URI),
                "client_id": settings.SPOTIFY_CLIENT_ID,
                "client_secret": settings.SPOTIFY_CLIENT_SECRET,
                "code_verifier": auth_req["code_verifier"],
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if resp.status_code != 200:
        raise HTTPException(502, "Spotify token exchange failed")

    spotify_tokens = resp.json()

    access_token = token_service.generate_access_token({'token_id': token_id},
                                                       expires_in=spotify_tokens.get('expires_in'))
    refresh_token = token_service.generate_refresh_token({'token_id': token_id})

    SPOTIFY_TOKENS[token_id] = {
        "client_id": client_id,
        "access_token": spotify_tokens["access_token"],
        "refresh_token": spotify_tokens["refresh_token"],
    }

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": spotify_tokens.get('expires_in'),
        "scope": settings.SUPPORTED_SCOPES_STR
    }

async def _refresh_grant(client_id: str, refresh_token: str):
    token_service = JWTService()

    token_data = token_service.verify_refresh_token(refresh_token)
    token_id = token_data["token_id"]
    stored_tokens = SPOTIFY_TOKENS.get(token_id, None)
    if not stored_tokens:
        raise HTTPException(400, "Invalid refresh_token")

    if client_id != stored_tokens['client_id']:
        raise HTTPException(400, "Invalid client_id")

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            settings.SPOTIFY_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": stored_tokens['refresh_token'],
                "client_id": settings.SPOTIFY_CLIENT_ID,
                "client_secret": settings.SPOTIFY_CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if resp.status_code != 200:
        raise HTTPException(502, "Spotify token exchange failed")

    new_token = resp.json()

    new_token_id = secrets.token_urlsafe(16)
    access_token = token_service.generate_access_token({'token_id': new_token_id}, expires_in=new_token.get('expires_in'))
    refresh_token = token_service.generate_refresh_token({'token_id': new_token_id})

    del SPOTIFY_TOKENS[token_id]
    SPOTIFY_TOKENS[new_token_id] = {
        "client_id": client_id,
        "access_token": new_token['access_token'],
        "refresh_token": new_token['refresh_token'],
    }

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": new_token.get('expires_in'),
        "refresh_token": refresh_token,
        "scope": settings.SUPPORTED_SCOPES_STR
    }
