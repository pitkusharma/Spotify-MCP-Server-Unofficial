from fastapi import APIRouter, Form, Depends
from pydantic import HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.auth import auth_services
from src.core.db import get_session
from src.models.dto.auth_models import (
    HealthResponse,
    ProtectedResourceMetadata,
    AuthorizationServerMetadata,
    ClientRegistrationResponse,
    TokenResponse,
    ClientRegistrationRequest,
)

router = APIRouter()

# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------

@router.get("/health", response_model=HealthResponse, include_in_schema=False)
def health():
    return auth_services.health()


@router.get(
    "/.well-known/oauth-protected-resource",
    response_model=ProtectedResourceMetadata,
)
def protected_resource_metadata():
    return auth_services.protected_resource_metadata()


@router.get(
    "/.well-known/oauth-authorization-server",
    response_model=AuthorizationServerMetadata,
)
def authorization_server_metadata():
    return auth_services.authorization_server_metadata()

# ---------------------------------------------------------------------------
# Client registration
# ---------------------------------------------------------------------------

@router.post(
    "/register",
    response_model=ClientRegistrationResponse,
    responses={415: {"description": "application/json required"}},
)
async def register_client(
    payload: ClientRegistrationRequest,
    db: AsyncSession = Depends(get_session),
):
    return await auth_services.register_client(payload, db)

# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------

@router.get("/authorize")
async def authorize(
    response_type: str,
    client_id: str,
    redirect_uri: str,
    code_challenge: str,
    code_challenge_method: str,
    state: str = "",
    scope: str = "",
    db: AsyncSession = Depends(get_session),
):
    return await auth_services.authorize(
        db=db,
        response_type=response_type,
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=scope,
        state=state,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
    )

# ---------------------------------------------------------------------------
# Spotify callback
# ---------------------------------------------------------------------------

@router.get("/callback/spotify")
def spotify_callback(code: str, state: str):
    return auth_services.spotify_callback(code, state)

# ---------------------------------------------------------------------------
# Token endpoint
# ---------------------------------------------------------------------------

@router.post("/token", response_model=TokenResponse)
async def token(
    grant_type: str = Form(...),
    client_id: str = Form(...),
    code: str = Form(None),
    redirect_uri: HttpUrl = Form(None),
    code_verifier: str = Form(None),
    refresh_token: str = Form(None),
    db: AsyncSession = Depends(get_session),
):
    return await auth_services.issue_token(
        db=db,
        grant_type=grant_type,
        client_id=client_id,
        code=code,
        redirect_uri=redirect_uri,
        code_verifier=code_verifier,
        refresh_token=refresh_token,
    )
