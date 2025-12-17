from pydantic import BaseModel, Field, HttpUrl, field_validator
from typing import List, Optional

from src.core.config import settings


# ----- Health -----
class HealthResponse(BaseModel):
    status: str
    app: str
    env: str


# ----- Well-known -----
class ProtectedResourceMetadata(BaseModel):
    resource: str
    authorization_servers: List[str]
    scopes_supported: List[str]


class AuthorizationServerMetadata(BaseModel):
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    registration_endpoint: str
    scopes_supported: List[str]
    response_types_supported: List[str]
    grant_types_supported: List[str]
    code_challenge_methods_supported: List[str]


# ----- Client Registration -----

class ClientRegistrationRequest(BaseModel):
    client_name: str
    redirect_uris: List[HttpUrl]
    grant_types: List[str]
    response_types: List[str]

    @field_validator("grant_types")
    @classmethod
    def validate_grant_types(cls, value: List[str]) -> List[str]:
        unsupported = set(value) - set(settings.GRANT_TYPES_SUPPORTED)
        if unsupported:
            raise ValueError(
                f"Unsupported grant_types: {unsupported}. "
                f"Supported: {settings.GRANT_TYPES_SUPPORTED}"
            )
        return value

    @field_validator("response_types")
    @classmethod
    def validate_response_types(cls, value: List[str]) -> List[str]:
        unsupported = set(value) - set(settings.RESPONSE_TYPES_SUPPORTED)
        if unsupported:
            raise ValueError(
                f"Unsupported response_types: {unsupported}. "
                f"Supported: {settings.RESPONSE_TYPES_SUPPORTED}"
            )
        return value


class ClientRegistrationResponse(BaseModel):
    client_id: str
    client_secret: str


# ----- Token -----
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    scope: str
