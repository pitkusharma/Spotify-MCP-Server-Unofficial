from typing import Dict, Optional
import httpx

from src.common.responses import AppResponse
from src.core.config import settings
from src.spotify_mcp.utils.decorators import with_spotify_token


# Shared helper: one client per request (simple & safe)
def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=10.0)


# -------------------------
# PLAYBACK CONTROLS
# -------------------------

@with_spotify_token
async def play(
    headers: Dict[str, str],
    context_uri: Optional[str] = None,
    uris: Optional[list[str]] = None,
) -> AppResponse:
    """
    Start or resume playback.
    Supports either a context (playlist/album/artist) or explicit track URIs.
    """
    payload = {}

    # Spotify accepts either context_uri OR uris
    if context_uri:
        payload["context_uri"] = context_uri
    if uris:
        payload["uris"] = uris

    async with _client() as client:
        response = await client.put(
            f"{settings.SPOTIFY_BASE_URL}/me/player/play",
            headers=headers,
            json=payload if payload else None,
        )

    if response.status_code not in (200, 204):
        return AppResponse(
            status=False,
            message=f"Play failed: {response.text}",
            data=None,
        )

    return AppResponse(
        status=True,
        message="Playback started",
        data=None,
    )


@with_spotify_token
async def pause(headers: Dict[str, str]) -> AppResponse:
    """Pause current playback."""
    async with _client() as client:
        response = await client.put(
            f"{settings.SPOTIFY_BASE_URL}/me/player/pause",
            headers=headers,
        )

    if response.status_code not in (200, 204):
        return AppResponse(
            status=False,
            message=f"Pause failed: {response.text}",
            data=None,
        )

    return AppResponse(
        status=True,
        message="Playback paused",
        data=None,
    )


@with_spotify_token
async def resume(headers: Dict[str, str]) -> AppResponse:
    """Alias for play() without context."""
    return await play(headers=headers)


@with_spotify_token
async def next_track(headers: Dict[str, str]) -> AppResponse:
    """Skip to next track."""
    async with _client() as client:
        response = await client.post(
            f"{settings.SPOTIFY_BASE_URL}/me/player/next",
            headers=headers,
        )

    if response.status_code not in (200, 204):
        return AppResponse(
            status=False,
            message=f"Next track failed: {response.text}",
            data=None,
        )

    return AppResponse(
        status=True,
        message="Skipped to next track",
        data=None,
    )


@with_spotify_token
async def previous_track(headers: Dict[str, str]) -> AppResponse:
    """Skip to previous track."""
    async with _client() as client:
        response = await client.post(
            f"{settings.SPOTIFY_BASE_URL}/me/player/previous",
            headers=headers,
        )

    if response.status_code not in (200, 204):
        return AppResponse(
            status=False,
            message=f"Previous track failed: {response.text}",
            data=None,
        )

    return AppResponse(
        status=True,
        message="Skipped to previous track",
        data=None,
    )


@with_spotify_token
async def get_current_playback(headers: Dict[str, str]) -> AppResponse:
    """Fetch current playback state."""
    async with _client() as client:
        response = await client.get(
            f"{settings.SPOTIFY_BASE_URL}/me/player",
            headers=headers,
        )

    if response.status_code != 200:
        return AppResponse(
            status=False,
            message=f"Playback fetch failed: {response.text}",
            data=None,
        )

    return AppResponse(
        status=True,
        message="Playback state fetched",
        data=response.json(),
    )


# -------------------------
# VOLUME CONTROL
# -------------------------

@with_spotify_token
async def set_volume(headers: Dict[str, str], volume: int) -> AppResponse:
    """
    Set playback volume.
    Volume is clamped between 0–100 to avoid Spotify API errors.
    """
    volume = max(0, min(volume, 100))

    async with _client() as client:
        response = await client.put(
            f"{settings.SPOTIFY_BASE_URL}/me/player/volume",
            headers=headers,
            params={"volume_percent": volume},
        )

    if response.status_code not in (200, 204):
        return AppResponse(
            status=False,
            message=f"Set volume failed: {response.text}",
            data=None,
        )

    return AppResponse(
        status=True,
        message="Volume updated",
        data={"volume": volume},
    )


@with_spotify_token
async def get_volume(headers: Dict[str, str]) -> AppResponse:
    """Get current device volume."""
    async with _client() as client:
        response = await client.get(
            f"{settings.SPOTIFY_BASE_URL}/me/player",
            headers=headers,
        )

    if response.status_code != 200:
        return AppResponse(
            status=False,
            message=f"Volume fetch failed: {response.text}",
            data=None,
        )

    device = response.json().get("device")

    return AppResponse(
        status=True,
        message="Volume fetched",
        data=device.get("volume_percent") if device else None,
    )


# -------------------------
# SEARCH & PLAY
# -------------------------

@with_spotify_token
async def search(
    headers: Dict[str, str],
    query: str,
    search_type: str = "track",
    limit: int = 10,
) -> AppResponse:
    """Search Spotify for tracks, artists, albums, or playlists."""
    params = {
        "q": query,
        "type": search_type,
        "limit": limit,
    }

    async with _client() as client:
        response = await client.get(
            f"{settings.SPOTIFY_BASE_URL}/search",
            headers=headers,
            params=params,
        )

    if response.status_code != 200:
        return AppResponse(
            status=False,
            message=f"Search failed: {response.text}",
            data=None,
        )

    return AppResponse(
        status=True,
        message="Search results fetched",
        data=response.json(),
    )


@with_spotify_token
async def play_track(headers: Dict[str, str], track_uri: str) -> AppResponse:
    """Play a single track by URI."""
    return await play(headers=headers, uris=[track_uri])


@with_spotify_token
async def play_playlist(headers: Dict[str, str], playlist_uri: str) -> AppResponse:
    """Play a playlist by URI."""
    return await play(headers=headers, context_uri=playlist_uri)


@with_spotify_token
async def play_album(headers: Dict[str, str], album_uri: str) -> AppResponse:
    """Play an album by URI."""
    return await play(headers=headers, context_uri=album_uri)


@with_spotify_token
async def play_artist(headers: Dict[str, str], artist_uri: str) -> AppResponse:
    """Start artist radio via context URI."""
    return await play(headers=headers, context_uri=artist_uri)


# -------------------------
# LIBRARY ACCESS
# -------------------------

@with_spotify_token
async def get_liked_tracks(headers: Dict[str, str], limit: int = 20) -> AppResponse:
    """Fetch user's liked (saved) tracks."""
    async with _client() as client:
        response = await client.get(
            f"{settings.SPOTIFY_BASE_URL}/me/tracks",
            headers=headers,
            params={"limit": limit},
        )

    if response.status_code != 200:
        return AppResponse(
            status=False,
            message=f"Liked tracks fetch failed: {response.text}",
            data=None,
        )

    return AppResponse(
        status=True,
        message="Liked tracks fetched",
        data=response.json().get("items", []),
    )


@with_spotify_token
async def get_user_playlists(headers: Dict[str, str], limit: int = 20) -> AppResponse:
    """Fetch user's playlists."""
    async with _client() as client:
        response = await client.get(
            f"{settings.SPOTIFY_BASE_URL}/me/playlists",
            headers=headers,
            params={"limit": limit},
        )

    if response.status_code != 200:
        return AppResponse(
            status=False,
            message=f"Playlists fetch failed: {response.text}",
            data=None,
        )

    return AppResponse(
        status=True,
        message="Playlists fetched",
        data=response.json().get("items", []),
    )


# -------------------------
# DEVICE CONTROL
# -------------------------

@with_spotify_token
async def get_devices(headers: Dict[str, str]) -> AppResponse:
    """List available Spotify playback devices."""
    async with _client() as client:
        response = await client.get(
            f"{settings.SPOTIFY_BASE_URL}/me/player/devices",
            headers=headers,
        )

    if response.status_code != 200:
        return AppResponse(
            status=False,
            message=f"Devices fetch failed: {response.text}",
            data=None,
        )

    return AppResponse(
        status=True,
        message="Devices fetched",
        data=response.json().get("devices", []),
    )


@with_spotify_token
async def transfer_playback(
    headers: Dict[str, str],
    device_id: str,
    play_immediately: bool = True,
) -> AppResponse:
    """
    Transfer playback to a specific device.
    Optionally resumes playback immediately.
    """
    payload = {
        "device_ids": [device_id],
        "play": play_immediately,
    }

    async with _client() as client:
        response = await client.put(
            f"{settings.SPOTIFY_BASE_URL}/me/player",
            headers=headers,
            json=payload,
        )

    if response.status_code not in (200, 204):
        return AppResponse(
            status=False,
            message=f"Transfer playback failed: {response.text}",
            data=None,
        )

    return AppResponse(
        status=True,
        message="Playback transferred",
        data=None,
    )
