from functools import wraps
from typing import Callable, Any, Dict
from mcp.server.auth.middleware.auth_context import get_access_token

from src.common.exceptions import AppException
from src.common.token import JWTService
from src.services.auth.auth_services import SPOTIFY_TOKENS


def with_spotify_token(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Injects Authorization headers using verified internal access token.
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Step 1: extract token (same call site)
        token = get_access_token()

        # Step 2: verify internal JWT
        jwt_service = JWTService()
        token_data = jwt_service.verify_access_token(token.token)
        token_id = token_data["token_id"]
        stored_tokens = SPOTIFY_TOKENS.get(token_id)
        if not stored_tokens:
            raise AppException(status_code=401, message="Invalid access token")

        # Step 3: extract spotify access token
        access_token = stored_tokens["access_token"]

        headers: Dict[str, str] = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        # Preserve original calling convention
        return func(headers, *args, **kwargs)

    return wrapper
