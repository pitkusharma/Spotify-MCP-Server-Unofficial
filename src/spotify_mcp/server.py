from mcp.server import FastMCP
from mcp.server.auth.settings import AuthSettings
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import AnyHttpUrl

from src.core.config import settings
from src.spotify_mcp.utils.token_verifier import JWTTokenVerifier

mcp = FastMCP(
    name="Spotify MCP Server (Unofficial)",
    json_response=True,
    token_verifier=JWTTokenVerifier(),
    auth=AuthSettings(
        issuer_url=AnyHttpUrl(settings.BASE_URL),
        resource_server_url=AnyHttpUrl(f"{settings.BASE_URL}/mcp"),
        required_scopes=settings.SUPPORTED_SCOPES,
    ),
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[host for host in settings.ALLOWED_HOSTS.split(",") if host],
        allowed_origins=[origin for origin in settings.ALLOWED_ORIGINS.split(",") if origin],
    ),
)
