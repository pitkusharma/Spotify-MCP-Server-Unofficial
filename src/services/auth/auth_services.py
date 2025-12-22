import secrets
import time
from typing import Dict, Optional, List
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException
from fastapi.responses import RedirectResponse
from pydantic import HttpUrl

from src.common.exceptions import OAuthException
from src.common.token import JWTService
from src.core.config import settings
from src.common.security import generate_pkce_pair, verify_pkce
from src.models.dto.auth_models import ClientRegistrationRequest

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
        "app": settings.APP_NAMEE,
        "env": settings.ENV,
    }


def protected_resource_metadata():
    return {
        "resource": f'{settings.BASE_URL}/mcp',
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
        "token_endpoint_auth_methods_supported": settings.TOKEN_ENDPOINT_AUTH_METHODS_SUPPORTED,
        "pkce_required": settings.PKCE_REQUIRED,
    }


# ---------------------------------------------------------------------------
# Client registration
# ---------------------------------------------------------------------------

def register_client(payload: ClientRegistrationRequest):
    # redirect_uris required
    if not payload.redirect_uris:
        raise OAuthException(
            error="invalid_client_metadata",
            description="Missing required field: redirect_uris"
        )

    # grant_types: reject if ANY unsupported
    unsupported_grants = set(payload.grant_types) - set(settings.GRANT_TYPES_SUPPORTED)
    if unsupported_grants:
        raise OAuthException(
            error="unsupported_grant_type",
            description=f"Unsupported grant_type(s) requested: {', '.join(unsupported_grants)}"
        )

    # response_types: same rule
    unsupported_responses = set(payload.response_types) - set(settings.RESPONSE_TYPES_SUPPORTED)
    if unsupported_responses:
        raise OAuthException(
            error="unsupported_response_type",
            description=f"Unsupported response_type(s) requested: {', '.join(unsupported_responses)}"
        )

    # token_endpoint_auth_method must be "none"
    if payload.token_endpoint_auth_method != "none":
        raise OAuthException(
            error="invalid_client_metadata",
            description=f"Invalid token_endpoint_auth_method: {payload.token_endpoint_auth_method}"
        )

    # scope validation
    if payload.scope:
        requested = set(payload.scope.split())
        unsupported = requested - set(settings.SUPPORTED_SCOPES)
        if unsupported:
            raise OAuthException(
                error="invalid_scope",
                description=f"Unsupported scope(s) requested: {', '.join(unsupported)}"
            )

    # generate client_id
    client_id = secrets.token_urlsafe(16)

    CLIENTS[client_id] = {
        "client_id": client_id,
        "client_id_issued_at": int(time.time()),
        "client_name": payload.client_name or "",
        "redirect_uris": [str(uri) for uri in payload.redirect_uris],
        "grant_types": payload.grant_types,
        "response_types": payload.response_types,
        "token_endpoint_auth_method": "none",
        "scope": payload.scope,
    }

    return {
        "client_id": client_id,
        "client_id_issued_at": CLIENTS[client_id]["client_id_issued_at"],
        "client_name": CLIENTS[client_id]["client_name"],
        "redirect_uris": CLIENTS[client_id]["redirect_uris"],
        "grant_types": payload.grant_types,
        "response_types": payload.response_types,
        "token_endpoint_auth_method": "none",
        "scope": payload.scope,
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
    # response_type check
    if response_type not in settings.RESPONSE_TYPES_SUPPORTED:
        raise OAuthException(
            error="unsupported_response_type",
            description=f"Unsupported response_type: {response_type}"
        )

    # client_id check
    client = CLIENTS.get(client_id)
    if not client:
        raise OAuthException(
            error="invalid_client",
            description=f"Invalid client_id: {client_id}"
        )

    # redirect_uri check
    if redirect_uri not in client["redirect_uris"]:
        raise OAuthException(
            error="invalid_redirect_uri",
            description=f"redirect_uri not registered: {redirect_uri}"
        )

    # code_challenge check
    if not code_challenge:
        raise OAuthException(
            error="invalid_request",
            description="Missing code_challenge"
        )

    # code_challenge_method check
    if code_challenge_method not in settings.CODE_CHALLENGE_METHODS_SUPPORTED:
        raise OAuthException(
            error="invalid_request",
            description=f"Invalid code_challenge_method: {code_challenge_method}"
        )

    # scope check
    if not scope:
        raise OAuthException(
            error="invalid_scope",
            description="Missing scope in request"
        )

    requested_scopes = set(scope.split())
    unsupported_scopes = requested_scopes - set(settings.SUPPORTED_SCOPES)
    if unsupported_scopes:
        raise OAuthException(
            error="invalid_scope",
            description=f"Unsupported scope(s) requested: {', '.join(unsupported_scopes)}"
        )

    requested_scopes_str = ' '.join(requested_scopes)

    # Create broker-side auth request
    auth_id = secrets.token_urlsafe(32)
    AUTH_REQUESTS[auth_id] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "original_state": state,
        "original_code_challenge": code_challenge,
        "original_scope": requested_scopes_str,
        "expires_at": time.time() + settings.AUTH_REQUEST_TTL,
    }

    code_verifier, code_challenge = generate_pkce_pair()
    AUTH_REQUESTS[auth_id]["code_verifier"] = code_verifier

    spotify_params = {
        "client_id": settings.SPOTIFY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": str(settings.SPOTIFY_REDIRECT_URI),
        "scope": requested_scopes_str,
        "state": auth_id,  # broker state
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
    }

    return RedirectResponse(
        f"{settings.SPOTIFY_AUTH_URL}?{urlencode(spotify_params)}"
    )



# ---------------------------------------------------------------------------
# Spotify callback
# ---------------------------------------------------------------------------

def spotify_callback(code: str, state: str):
    auth = AUTH_REQUESTS.get(state)
    if not auth:
        raise OAuthException(
            error="invalid_request",
            description="Invalid or expired authorization request"
        )

    if time.time() > auth["expires_at"]:
        del AUTH_REQUESTS[state]
        raise OAuthException(
            error="invalid_request",
            description="Authorization request has expired"
        )

    # Mark code in broker request
    auth["code"] = code

    redirect_uri = auth["redirect_uri"]
    original_state = auth.get("original_state")

    # Return code to client
    params = {"code": state}  # broker auth_id as code
    if original_state:
        params["state"] = original_state

    return RedirectResponse(f"{redirect_uri}?{urlencode(params)}")



# ---------------------------------------------------------------------------
# Token endpoint
# ---------------------------------------------------------------------------

async def issue_token(
        grant_type: str,
        client_id: str,
        code: Optional[str] = None,
        redirect_uri: Optional[HttpUrl] = None,
        code_verifier: Optional[str] = None,
        refresh_token: Optional[str] = None,
):
    # Grant type validation
    if grant_type not in settings.GRANT_TYPES_SUPPORTED:
        raise OAuthException(
            error="unsupported_grant_type",
            description=f"Invalid grant_type: {grant_type}"
        )

    # Client validation
    client = CLIENTS.get(client_id)
    if not client:
        raise OAuthException(
            error="invalid_client",
            description=f"Unknown client_id: {client_id}"
        )

    # Dispatch to proper grant
    if grant_type == "authorization_code":
        return await _code_grant(client_id, code, redirect_uri, code_verifier)
    elif grant_type == "refresh_token":
        return await _refresh_grant(client_id, refresh_token)
    else:
        # This should not occur due to the first check
        raise OAuthException(
            error="unsupported_grant_type",
            description=f"Unsupported grant_type: {grant_type}"
        )


async def _code_grant(client_id: str, code: str, redirect_uri: HttpUrl, code_verifier: str):
    if not code or not redirect_uri or not code_verifier:
        raise OAuthException(
            error="invalid_request",
            description="Missing required fields: code, redirect_uri, or code_verifier"
        )

    auth_req = AUTH_REQUESTS.pop(code, None)
    if not auth_req:
        raise OAuthException(
            error="invalid_grant",
            description="Invalid or expired authorization request"
        )

    if str(redirect_uri) != auth_req["redirect_uri"]:
        raise OAuthException(
            error="invalid_request",
            description=f"redirect_uri mismatch: {redirect_uri}"
        )

    if not verify_pkce(code_verifier, auth_req['original_code_challenge']):
        raise OAuthException(error="pkce_failed", description="code challenge mismatch")

    token_service = JWTService()
    token_id = secrets.token_urlsafe(16)

    try:
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
    except Exception as exc:
        raise OAuthException(error="server_error", description="Spotify token retrival failed")

    if resp.status_code != 200:
        raise OAuthException(
            error="server_error",
            description="Spotify token retrival failed"
        )

    spotify_tokens = resp.json()

    access_token = token_service.generate_access_token({'token_id': token_id},
                                                       expires_in=spotify_tokens.get('expires_in'))
    refresh_token = token_service.generate_refresh_token({'token_id': token_id})

    SPOTIFY_TOKENS[token_id] = {
        "client_id": client_id,
        "access_token": spotify_tokens["access_token"],
        "refresh_token": spotify_tokens["refresh_token"],
        "scope": auth_req["original_scope"]
    }

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": spotify_tokens.get('expires_in'),
        "scope": auth_req["original_scope"]
    }


async def _refresh_grant(client_id: str, refresh_token: str):
    if not refresh_token:
        raise OAuthException(
            error="invalid_request",
            description="Missing refresh_token"
        )

    token_service = JWTService()

    try:
        token_data = token_service.verify_refresh_token(refresh_token)
    except Exception:
        raise OAuthException(
            error="invalid_grant",
            description="Invalid refresh_token format"
        )

    token_id = token_data["token_id"]
    stored_tokens = SPOTIFY_TOKENS.get(token_id)
    if not stored_tokens:
        raise OAuthException(
            error="invalid_grant",
            description="Refresh token not found or expired"
        )

    if client_id != stored_tokens['client_id']:
        raise OAuthException(
            error="invalid_client",
            description="refresh_token does not belong to this client"
        )

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
        raise OAuthException(
            error="server_error",
            description="Spotify refresh token exchange failed"
        )

    new_token = resp.json()
    new_token_id = secrets.token_urlsafe(16)

    access_token = token_service.generate_access_token({'token_id': new_token_id}, expires_in=new_token.get('expires_in'))
    refresh_token = token_service.generate_refresh_token({'token_id': new_token_id})

    # Replace old token
    del SPOTIFY_TOKENS[token_id]
    SPOTIFY_TOKENS[new_token_id] = {
        "client_id": client_id,
        "access_token": new_token['access_token'],
        "refresh_token": new_token['refresh_token'],
        "scope": stored_tokens["scope"]
    }

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": new_token.get('expires_in'),
        "refresh_token": refresh_token,
        "scope": stored_tokens["scope"]
    }

