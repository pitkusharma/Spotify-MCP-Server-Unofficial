from fastapi import APIRouter, Form
from typing import Optional, List

from pydantic import HttpUrl

from src.services.auth import auth_services
from src.models.dto.auth_models import (
    HealthResponse,
    ProtectedResourceMetadata,
    AuthorizationServerMetadata,
    ClientRegistrationResponse,
    TokenResponse, RefreshTokenResponse,
)

router = APIRouter()


@router.get("/health", response_model=HealthResponse, include_in_schema=False)
def health():
    return auth_services.health()


@router.get("/.well-known/oauth-protected-resource", response_model=ProtectedResourceMetadata)
def protected_resource_metadata():
    return auth_services.protected_resource_metadata()


@router.get("/.well-known/oauth-authorization-server", response_model=AuthorizationServerMetadata)
def authorization_server_metadata():
    return auth_services.authorization_server_metadata()


@router.post("/register", response_model=ClientRegistrationResponse)
def register_client(
        client_name: str = Form(...),
        redirect_uris: List[HttpUrl] = Form(...),
        grant_types: List[str] = Form(...),
        response_types: List[str] = Form(...),
):
    return auth_services.register_client(client_name, redirect_uris, grant_types, response_types)


@router.get("/authorize")
def authorize(
        response_type: str,
        client_id: str,
        redirect_uri: str,
        code_challenge: str,
        code_challenge_method: str,
        state: str = "",
        scope: str = "",
):
    return auth_services.authorize(
        response_type,
        client_id,
        redirect_uri,
        scope,
        state,
        code_challenge,
        code_challenge_method,
    )


@router.get("/callback/spotify")
def spotify_callback(code: str, state: Optional[str] = None):
    return auth_services.spotify_callback(code, state)


@router.post("/token", response_model=TokenResponse | RefreshTokenResponse)
async def token(
        grant_type: str = Form(...),
        client_id: str = Form(...),
        code: str = Form(None),
        redirect_uri: HttpUrl = Form(None),
        code_verifier: str = Form(None),
        client_secret: Optional[str] = Form(None),
        refresh_token: str = Form(None),


):
    return await auth_services.issue_token(grant_type, client_id, code, redirect_uri, code_verifier, client_secret, refresh_token)


# @router.post("/refresh", response_model=TokenResponse)
# async def refresh_token(refresh_token: str = Form(...)):
#     """
#     Exchange a valid refresh token for a new access token.
#     Optionally issues a new refresh token if broker logic allows.
#     """
#     return await auth_services.refresh_token(refresh_token)
#
#
# @router.post("/introspect")
# async def introspect_token(token: str = Form(...)):
#     """
#     Return token metadata.
#     Should return at least:
#     {
#         "active": bool,
#         "scope": str,
#         "client_id": str,
#         "exp": int,  # Optional
#         "iat": int,  # Optional
#         "sub": str,  # Optional
#     }
#     """
#     return await auth_services.introspect_token(token)
#
#
# @router.post("/revoke")
# async def revoke_token(token: str = Form(...), token_type_hint: Optional[str] = Form(None)):
#     """
#     Revoke an access or refresh token.
#     token_type_hint = 'access_token' | 'refresh_token' (optional)
#     """
#     return await auth_services.revoke_token(token, token_type_hint)
