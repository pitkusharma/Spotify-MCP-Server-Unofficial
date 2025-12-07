from typing import Any, Dict, List, Callable
from functools import wraps

import requests

from app.spotify.auth import get_access_token
from app.common.responses import AppResponse


BASE_URL: str = "https://api.spotify.com/v1"


class SpotifyServiceError(Exception):
    """
    Raised when a Spotify API request fails.
    """
    pass


def with_spotify_token(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator that injects a valid Spotify access token into request headers.
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            token: str = get_access_token()
        except Exception as e:
            return AppResponse(
                status=False,
                message=f"Token error: {str(e)}",
                data=None
            )

        headers: Dict[str, str] = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        return func(headers, *args, **kwargs)
    return wrapper


# =========================
# PLAYER CONTROLS
# =========================

@with_spotify_token
def play(headers: Dict[str, str]) -> AppResponse:
    """Resume/start playback."""
    response = requests.put(f"{BASE_URL}/me/player/play", headers=headers)

    if response.status_code not in (200, 204):
        return AppResponse(status=False, message=f"Play failed: {response.text}", data=None)

    return AppResponse(status=True, message="Playback started", data=None)


@with_spotify_token
def pause(headers: Dict[str, str]) -> AppResponse:
    """Pause playback."""
    response = requests.put(f"{BASE_URL}/me/player/pause", headers=headers)

    if response.status_code not in (200, 204):
        return AppResponse(status=False, message=f"Pause failed: {response.text}", data=None)

    return AppResponse(status=True, message="Playback paused", data=None)


@with_spotify_token
def next_track(headers: Dict[str, str]) -> AppResponse:
    """Skip to next track."""
    response = requests.post(f"{BASE_URL}/me/player/next", headers=headers)

    if response.status_code not in (200, 204):
        return AppResponse(status=False, message=f"Next track failed: {response.text}", data=None)

    return AppResponse(status=True, message="Skipped to next track", data=None)


@with_spotify_token
def previous_track(headers: Dict[str, str]) -> AppResponse:
    """Skip to previous track."""
    response = requests.post(f"{BASE_URL}/me/player/previous", headers=headers)

    if response.status_code not in (200, 204):
        return AppResponse(status=False, message=f"Previous track failed: {response.text}", data=None)

    return AppResponse(status=True, message="Skipped to previous track", data=None)


# =========================
# PROFILE
# =========================

@with_spotify_token
def get_user_profile(headers: Dict[str, str]) -> AppResponse:
    """Fetch current user profile."""
    response = requests.get(f"{BASE_URL}/me", headers=headers)

    if response.status_code != 200:
        return AppResponse(status=False, message=f"Profile failed: {response.text}", data=None)

    return AppResponse(status=True, message="Profile fetched", data=response.json())


# =========================
# PLAYLISTS
# =========================

@with_spotify_token
def get_user_playlists(headers: Dict[str, str], limit: int = 20) -> AppResponse:
    """Retrieve user playlists."""
    response = requests.get(
        f"{BASE_URL}/me/playlists",
        headers=headers,
        params={"limit": limit}
    )

    if response.status_code != 200:
        return AppResponse(status=False, message=f"Playlists failed: {response.text}", data=None)

    return AppResponse(status=True, message="Playlists fetched", data=response.json().get("items", []))


@with_spotify_token
def get_playlist_tracks(headers: Dict[str, str], playlist_id: str, limit: int = 50) -> AppResponse:
    """Fetch tracks from a playlist."""
    response = requests.get(
        f"{BASE_URL}/playlists/{playlist_id}/tracks",
        headers=headers,
        params={"limit": limit}
    )

    if response.status_code != 200:
        return AppResponse(status=False, message=f"Tracks fetch failed: {response.text}", data=None)

    return AppResponse(status=True, message="Playlist tracks fetched", data=response.json().get("items", []))


@with_spotify_token
def create_playlist(
    headers: Dict[str, str],
    user_id: str,
    name: str,
    description: str = "",
    public: bool = False
) -> AppResponse:
    """Create a new playlist."""
    payload = {
        "name": name,
        "description": description,
        "public": public
    }

    response = requests.post(
        f"{BASE_URL}/users/{user_id}/playlists",
        headers=headers,
        json=payload
    )

    if response.status_code not in (200, 201):
        return AppResponse(status=False, message=f"Create playlist failed: {response.text}", data=None)

    return AppResponse(status=True, message="Playlist created", data=response.json())


@with_spotify_token
def add_tracks_to_playlist(headers: Dict[str, str], playlist_id: str, track_uris: List[str]) -> AppResponse:
    """Add tracks to playlist."""
    response = requests.post(
        f"{BASE_URL}/playlists/{playlist_id}/tracks",
        headers=headers,
        json={"uris": track_uris}
    )

    if response.status_code not in (200, 201):
        return AppResponse(status=False, message=f"Add tracks failed: {response.text}", data=None)

    return AppResponse(status=True, message="Tracks added", data=None)


@with_spotify_token
def remove_tracks_from_playlist(headers: Dict[str, str], playlist_id: str, track_uris: List[str]) -> AppResponse:
    """Remove tracks from playlist."""
    payload = {"tracks": [{"uri": uri} for uri in track_uris]}

    response = requests.delete(
        f"{BASE_URL}/playlists/{playlist_id}/tracks",
        headers=headers,
        json=payload
    )

    if response.status_code != 200:
        return AppResponse(status=False, message=f"Remove tracks failed: {response.text}", data=None)

    return AppResponse(status=True, message="Tracks removed", data=None)


# =========================
# SEARCH
# =========================

@with_spotify_token
def search_tracks(headers: Dict[str, str], query: str, limit: int = 10) -> AppResponse:
    """Search tracks."""
    params = {"q": query, "type": "track", "limit": limit}
    response = requests.get(f"{BASE_URL}/search", headers=headers, params=params)

    if response.status_code != 200:
        return AppResponse(status=False, message=f"Search failed: {response.text}", data=None)

    items = response.json().get("tracks", {}).get("items", [])
    return AppResponse(status=True, message="Tracks found", data=items)


# =========================
# LIKED SONGS
# =========================

@with_spotify_token
def get_liked_songs(headers: Dict[str, str], limit: int = 20) -> AppResponse:
    """Get user's liked songs."""
    params = {"limit": limit}
    response = requests.get(f"{BASE_URL}/me/tracks", headers=headers, params=params)

    if response.status_code != 200:
        return AppResponse(status=False, message=f"Liked songs failed: {response.text}", data=None)

    return AppResponse(status=True, message="Liked songs fetched", data=response.json().get("items", []))
