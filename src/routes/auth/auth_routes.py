from fastapi import APIRouter, Form
from typing import Optional

from src.services.auth import auth_services
from src.models.dto.auth_models import (
    HealthResponse,
    ProtectedResourceMetadata,
    AuthorizationServerMetadata,
    ClientRegistrationRequest,
    ClientRegistrationResponse,
    TokenResponse,
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
def register_client(payload: ClientRegistrationRequest):
    return auth_services.register_client(payload)


@router.get("/authorize")
def authorize(
        response_type: str,
        client_id: str,
        redirect_uri: str,
        code_challenge: str,
        code_challenge_method: str,
        state: str,
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
async def spotify_callback(code: str, state: Optional[str] = None):
    return await auth_services.spotify_callback(code, state)


@router.post("/token", response_model=TokenResponse)
async def token(
        grant_type: str = Form(...),
        code: str = Form(...),
        code_verifier: str = Form(...),
):
    return await auth_services.issue_token(grant_type, code, code_verifier)
