from pydantic import BaseModel, Field, HttpUrl, field_validator, AnyHttpUrl, ConfigDict
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
    token_endpoint_auth_methods_supported: List[str]
    pkce_required: bool = settings.PKCE_REQUIRED

# ----- Client Registration -----
class ClientRegistrationRequest(BaseModel):
    client_name: Optional[str] = None
    redirect_uris: List[AnyHttpUrl]
    grant_types: List[str]
    response_types: List[str]
    token_endpoint_auth_method: Optional[str] = "none"
    scope: Optional[str] = ''

    model_config = ConfigDict(extra="allow")

class ClientRegistrationResponse(BaseModel):
    client_id: str
    client_id_issued_at: int
    client_name: str
    redirect_uris: List[str]
    grant_types: List[str]
    response_types: List[str]
    token_endpoint_auth_method: str
    scope: Optional[str] = None


# ----- Token -----
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str
    scope: str
