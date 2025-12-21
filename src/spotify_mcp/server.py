from mcp.server import FastMCP
from mcp.server.auth.settings import AuthSettings
from pydantic import AnyHttpUrl

from src.core.config import settings
from src.spotify_mcp.utils.token_verifier import JWTTokenVerifier

mcp = FastMCP(
    name="Spotify MCP Server (Unofficial)",
    json_response=True,
    token_verifier=JWTTokenVerifier(),
    auth=AuthSettings(
        issuer_url=AnyHttpUrl(settings.BASE_URL),  # Authorization Server URL
        resource_server_url=AnyHttpUrl(f'{settings.BASE_URL}/mcp'),  # This server's URL
        required_scopes=settings.SUPPORTED_SCOPES)
)
