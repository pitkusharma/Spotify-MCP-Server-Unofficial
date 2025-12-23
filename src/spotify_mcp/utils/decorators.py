from functools import wraps
from typing import Callable, Any, Dict
import inspect

from mcp.server.auth.middleware.auth_context import get_access_token

from src.common.exceptions import AppException
from src.common.token import JWTService
from src.services.auth.auth_services import SPOTIFY_TOKENS


def with_spotify_token(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Injects Spotify Authorization headers using a verified internal access token.

    Supports both sync and async wrapped functions.
    """

    async def _async_wrapper(*args: Any, **kwargs: Any) -> Any:
        # Step 1: extract internal access token
        token = get_access_token()

        # Step 2: verify internal JWT
        jwt_service = JWTService()
        token_data = jwt_service.verify_access_token(token.token)
        token_id = token_data["token_id"]

        stored_tokens = SPOTIFY_TOKENS.get(token_id)
        if not stored_tokens:
            raise AppException(
                message="Access token expired",
                status_code=401,
                headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
            )

        # Step 3: extract Spotify access token
        access_token = stored_tokens["access_token"]

        headers: Dict[str, str] = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        # Call async function with injected headers
        return await func(headers, *args, **kwargs)

    def _sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        # Step 1: extract internal access token
        token = get_access_token()

        # Step 2: verify internal JWT
        jwt_service = JWTService()
        token_data = jwt_service.verify_access_token(token.token)
        token_id = token_data["token_id"]

        stored_tokens = SPOTIFY_TOKENS.get(token_id)
        if not stored_tokens:
            raise AppException(
                message="Access token expired",
                status_code=401,
                headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
            )

        # Step 3: extract Spotify access token
        access_token = stored_tokens["access_token"]

        headers: Dict[str, str] = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        # Call sync function with injected headers
        return func(headers, *args, **kwargs)

    # Decide which wrapper to return based on function type
    if inspect.iscoroutinefunction(func):
        return wraps(func)(_async_wrapper)
    else:
        return wraps(func)(_sync_wrapper)
