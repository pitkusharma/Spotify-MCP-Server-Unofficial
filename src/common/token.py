from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

import jwt

from src.common.exceptions import AppException
from src.core.config import settings


class JWTService:
    """
    Secure JWT service for generating and verifying access and refresh tokens.

    Design goals:
    - Accept arbitrary dict payloads
    - Enforce access vs refresh token separation
    - Allow per-call expiry overrides
    - Remain small, auditable, and predictable
    """

    SECRET: str = settings.JWT_SECRET
    ISSUER: str = settings.JWT_ISSUER
    ALGORITHM: str = settings.JWT_ALGORITHM

    DEFAULT_ACCESS_TTL: int = settings.JWT_ACCESS_TTL
    DEFAULT_REFRESH_TTL: int = settings.JWT_REFRESH_TTL

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _utc_now() -> datetime:
        """
        Get the current UTC time.

        Returns:
            A timezone-aware datetime in UTC.
        """
        return datetime.now(timezone.utc)

    @staticmethod
    def _to_timestamp(dt: datetime) -> int:
        """
        Convert a datetime to a UNIX timestamp.

        Args:
            dt: A timezone-aware datetime.

        Returns:
            Integer UNIX timestamp.
        """
        return int(dt.timestamp())

    def _encode_token(
        self,
        payload: Dict[str, Any],
        token_type: str,
        ttl_seconds: int,
    ) -> str:
        """
        Encode and sign a JWT.

        Args:
            payload: Arbitrary claims to embed in the token.
            token_type: Token type identifier ("access" or "refresh").
            ttl_seconds: Token lifetime in seconds.

        Returns:
            A signed JWT string.
        """
        now: datetime = self._utc_now()

        claims: Dict[str, Any] = {
            **payload,
            "iss": self.ISSUER,
            "iat": self._to_timestamp(now),
            "exp": self._to_timestamp(now + timedelta(seconds=ttl_seconds)),
            "typ": token_type,
        }

        return jwt.encode(
            claims,
            self.SECRET,
            algorithm=self.ALGORITHM,
        )

    def _decode_token(
        self,
        token: str,
        expected_type: str,
    ) -> Dict[str, Any]:
        """
        Decode and verify a JWT.

        Args:
            token: The JWT string to verify.
            expected_type: Expected token type ("access" or "refresh").

        Returns:
            The decoded JWT payload.

        Raises:
            jwt.ExpiredSignatureError: If the token has expired.
            jwt.InvalidTokenError: If the token is malformed or invalid.
            ValueError: If the token type does not match the expected type.
        """
        claims: Dict[str, Any] = jwt.decode(
            token,
            self.SECRET,
            algorithms=[self.ALGORITHM],
            issuer=self.ISSUER,
            options={"require": ["exp", "iat", "typ"]},
        )

        if claims.get("typ") != expected_type:
            raise ValueError("Invalid token type")

        return claims

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_access_token(
        self,
        payload: Dict[str, Any],
        expires_in: Optional[int] = None,
    ) -> str:
        """
        Generate a signed JWT access token.

        Args:
            payload: Arbitrary payload to embed in the token.
            expires_in: Optional lifetime override in seconds.

        Returns:
            A signed JWT access token.
        """
        ttl: int = expires_in if expires_in is not None else self.DEFAULT_ACCESS_TTL

        return self._encode_token(
            payload=payload,
            token_type="access",
            ttl_seconds=ttl,
        )

    def generate_refresh_token(
        self,
        payload: Dict[str, Any],
        expires_in: Optional[int] = None,
    ) -> str:
        """
        Generate a signed JWT refresh token.

        Args:
            payload: Arbitrary payload to embed in the token.
            expires_in: Optional lifetime override in seconds.

        Returns:
            A signed JWT refresh token.
        """
        ttl: int = expires_in if expires_in is not None else self.DEFAULT_REFRESH_TTL

        return self._encode_token(
            payload=payload,
            token_type="refresh",
            ttl_seconds=ttl,
        )

    def verify_access_token(self, token: str) -> Dict[str, Any]:
        """
        Verify an access token and return its decoded payload.

        Args:
            token: The JWT access token.

        Returns:
            Decoded JWT payload.
        """
        try:
            return self._decode_token(token, expected_type="access")
        except jwt.ExpiredSignatureError:
            raise AppException(message="Access token expired", status_code=401, headers={
                "WWW-Authenticate": 'Bearer error="invalid_token"'
            })
        except jwt.InvalidTokenError:
            raise AppException(message="Invalid access token", status_code=401, headers={
                "WWW-Authenticate": 'Bearer error="invalid_token"'
            })
        except ValueError as e:
            raise AppException(message=str(e), status_code=401, headers={
                "WWW-Authenticate": 'Bearer error="invalid_token"'
            })

    def verify_refresh_token(self, token: str) -> Dict[str, Any]:
        """
        Verify a refresh token and return its decoded payload.

        Args:
            token: The JWT refresh token.

        Returns:
            Decoded JWT payload.
        """
        try:
            return self._decode_token(token, expected_type="refresh")
        except jwt.ExpiredSignatureError:
            raise AppException(message="Refresh token expired", status_code=401, headers={
                "WWW-Authenticate": 'Bearer error="invalid_token"'
            })
        except jwt.InvalidTokenError:
            raise AppException(message="Invalid refresh token", status_code=401, headers={
                "WWW-Authenticate": 'Bearer error="invalid_token"'
            })
        except ValueError as e:
            raise AppException(message=str(e), status_code=401, headers={
                "WWW-Authenticate": 'Bearer error="invalid_token"'
            })

    def refresh_access_token(
        self,
        refresh_token: str,
        expires_in: Optional[int] = None,
    ) -> str:
        """
        Issue a new access token using a valid refresh token.

        Args:
            refresh_token: A valid JWT refresh token.
            expires_in: Optional lifetime override for the new access token.

        Returns:
            A newly issued JWT access token.
        """
        try:
            claims: Dict[str, Any] = self.verify_refresh_token(refresh_token)
        except AppException as e:
            # propagate refresh token issues
            raise e

        for key in ("exp", "iat", "typ"):
            claims.pop(key, None)

        return self.generate_access_token(payload=claims, expires_in=expires_in)
