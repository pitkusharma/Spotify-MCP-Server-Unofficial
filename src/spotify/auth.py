import os
import time
import json
import base64
from pathlib import Path
from typing import Dict, Optional, Any
import requests
from dotenv import load_dotenv

# Load .env variables into environment
load_dotenv()

TOKEN_FILE: str = str(
    Path(__file__).resolve().parent.parent / "spotify_token.json"
)
AUTH_URL: str = "https://accounts.spotify.com/authorize"
TOKEN_URL: str = "https://accounts.spotify.com/api/token"

# Required Spotify OAuth Scopes
SCOPES: str = (
    "user-read-playback-state "
    "user-modify-playback-state "
    "playlist-read-private "
    "playlist-read-collaborative "
    "playlist-modify-public "
    "playlist-modify-private "
    "user-library-read "
    "user-library-modify "
    "user-read-currently-playing "
    "user-read-playback-position"
)


class SpotifyAuthError(Exception):
    """Custom exception class for Spotify authentication-related errors."""
    pass


def get_env_variable(name: str) -> str:
    """
    Retrieve a required environment variable.

    Args:
        name (str): Environment variable name.

    Returns:
        str: Value of the environment variable.

    Raises:
        SpotifyAuthError: If variable is missing or empty.
    """
    value = os.getenv(name)
    if not value:
        raise SpotifyAuthError(f"Missing required environment variable: {name}")
    return value


def get_authorization_url() -> str:
    """
    Generate the Spotify user authorization URL.

    This URL must be opened in a browser so the user can grant
    permissions to your application.

    Returns:
        str: Fully constructed OAuth authorization URL.
    """
    client_id: str = get_env_variable("SPOTIFY_CLIENT_ID")
    redirect_uri: str = get_env_variable("SPOTIFY_REDIRECT_URI")

    return (
        f"{AUTH_URL}"
        f"?response_type=code"
        f"&client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&scope={SCOPES}"
    )


def save_token(token_data: Dict[str, Any]) -> None:
    """
    Persist token information to disk and calculate its expiry timestamp.

    Args:
        token_data (Dict[str, Any]): Raw token response from Spotify.

    Returns:
        None
    """
    token_data["expires_at"] = int(time.time()) + int(token_data["expires_in"])

    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=4)


def load_token() -> Optional[Dict[str, Any]]:
    """
    Load token data from disk.

    Returns:
        Optional[Dict[str, Any]]: Token data if file exists, else None.
    """
    if not os.path.exists(TOKEN_FILE):
        return None

    with open(TOKEN_FILE, "r") as f:
        return json.load(f)


def is_token_expired(token: Dict[str, Any], buffer_seconds: int = 300) -> bool:
    """
    Determine whether the access token is expired or about to expire.

    Args:
        token (Dict[str, Any]): Stored token data.
        buffer_seconds (int): Safety buffer in seconds.

    Returns:
        bool: True if token is expired or close to expiring.
    """
    current_time: int = int(time.time())
    return current_time >= int(token["expires_at"]) - buffer_seconds


def exchange_code_for_token(code: str) -> None:
    """
    Exchange an authorization code for access and refresh tokens.

    Args:
        code (str): Authorization code from Spotify redirect.

    Returns:
        None

    Raises:
        SpotifyAuthError: When token exchange fails.
    """
    client_id: str = get_env_variable("SPOTIFY_CLIENT_ID")
    client_secret: str = get_env_variable("SPOTIFY_CLIENT_SECRET")
    redirect_uri: str = get_env_variable("SPOTIFY_REDIRECT_URI")

    auth_b64: str = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    headers: Dict[str, str] = {
        "Authorization": f"Basic {auth_b64}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data: Dict[str, str] = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
    }

    response = requests.post(TOKEN_URL, headers=headers, data=data)
    if response.status_code != 200:
        raise SpotifyAuthError(f"Token exchange failed: {response.text}")

    save_token(response.json())


def refresh_access_token(refresh_token: str) -> None:
    """
    Refresh the access token using a refresh token.

    Args:
        refresh_token (str): Previously issued refresh token.

    Returns:
        None

    Raises:
        SpotifyAuthError: If Spotify rejects the refresh request.
    """
    client_id: str = get_env_variable("SPOTIFY_CLIENT_ID")
    client_secret: str = get_env_variable("SPOTIFY_CLIENT_SECRET")

    auth_b64: str = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    headers: Dict[str, str] = {
        "Authorization": f"Basic {auth_b64}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data: Dict[str, str] = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }

    response = requests.post(TOKEN_URL, headers=headers, data=data)
    if response.status_code != 200:
        raise SpotifyAuthError(f"Token refresh failed: {response.text}")

    new_data = response.json()
    new_data["refresh_token"] = new_data.get("refresh_token", refresh_token)
    save_token(new_data)


def get_access_token() -> str:
    """
    Retrieve a valid Spotify access token.

    Automatically refreshes token if expired.

    Returns:
        str: Valid access token.

    Raises:
        SpotifyAuthError: If tokens are missing or invalid.
    """
    token: Optional[Dict[str, Any]] = load_token()

    if not token:
        raise SpotifyAuthError("No token file found. Run initial authorization.")

    if is_token_expired(token):
        refresh_access_token(token["refresh_token"])
        token = load_token()

    if not token:
        raise SpotifyAuthError("Failed to load token after refresh.")

    return str(token["access_token"])
