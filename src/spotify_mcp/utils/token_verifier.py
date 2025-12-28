from mcp.server.auth.provider import AccessToken, TokenVerifier
from src.common.token import JWTService
from src.services.auth.auth_services import SPOTIFY_TOKENS

class JWTTokenVerifier(TokenVerifier):
    async def verify_token(self, token: str) -> AccessToken | None:
        jwt_service = JWTService()
        try:
            token_data = jwt_service.verify_access_token(token)
        except Exception as e:
            return None
        spotify_token = SPOTIFY_TOKENS.get(token_data['token_id'])
        if spotify_token:
            return AccessToken(token=token, client_id=spotify_token['client_id'], scopes=spotify_token['scope'].split(), expires_at=token_data['exp'])
        else:
            return None
