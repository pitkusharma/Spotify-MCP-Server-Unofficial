from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    APP_NAME: str = "Spotify MCP Server (Unofficial)"
    DEBUG: bool = True
    ENV: str = "development"
    PROTOCOL: str = "http"
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    @property
    def BASE_URL(self) -> str:
        return f"{self.PROTOCOL}://{self.HOST}:{self.PORT}"

    # ------------------------------------------------------------------
    # Spotify OAuth
    # ------------------------------------------------------------------
    SPOTIFY_CLIENT_ID: str
    SPOTIFY_CLIENT_SECRET: str
    SPOTIFY_AUTH_URL: str = "https://accounts.spotify.com/authorize"
    SPOTIFY_TOKEN_URL: str = "https://accounts.spotify.com/api/token"

    @property
    def SPOTIFY_REDIRECT_URI(self) -> str:
        return f"{self.BASE_URL}/callback/spotify"

    # ------------------------------------------------------------------
    # OAuth Broker
    # ------------------------------------------------------------------
    SUPPORTED_SCOPES: List[str] = [
        "user-read-private",
        "user-read-email",
        "user-read-playback-state",
        "user-modify-playback-state",
        "playlist-read-private",
        "playlist-read-collaborative",
        "playlist-modify-public",
        "playlist-modify-private",
        "user-library-read",
        "user-library-modify",
        "user-read-currently-playing",
        "user-read-playback-position"
    ]

    @property
    def SUPPORTED_SCOPES_STR(self) -> str:
        return " ".join(self.SUPPORTED_SCOPES)

    TOKEN_BYTES: int = 32
    STATE_BYTES: int = 16

    RESPONSE_TYPES_SUPPORTED: List[str] = ["code"]
    GRANT_TYPES_SUPPORTED: List[str] = ["authorization_code"]
    CODE_CHALLENGE_METHODS_SUPPORTED: List[str] = ["S256"]

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    CORS_ALLOW_ORIGINS: List[str] = ["*"]
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    # ------------------------------------------------------------------
    # Meta
    # ------------------------------------------------------------------
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Singleton settings object (import this everywhere)
settings = Settings()
