from typing import Dict, Any

from src.spotify_mcp.server import mcp as spotify_mcp
from src.spotify_mcp.services.spotify_services import (
    play,
    pause,
    resume,
    next_track,
    previous_track,
    get_current_playback,
    set_volume,
    get_volume,
    search,
    play_track,
    play_playlist,
    play_album,
    play_artist,
    get_liked_tracks,
    get_user_playlists,
    get_devices,
    transfer_playback,
)

# =========================
# PLAYBACK TOOLS
# =========================

@spotify_mcp.tool()
async def play_music() -> Dict[str, Any]:
    """
    Start or resume music playback on the user's active Spotify device.

    Use when:
    - User asks to play music
    - Agent decides to resume playback after a pause

    Returns:
        Dict[str, Any]:
            {
                "status": bool,
                "message": str,
                "data": None
            }
    """
    response = await play()
    return response.model_dump()


@spotify_mcp.tool()
async def pause_music() -> Dict[str, Any]:
    """
    Pause the currently playing track.

    Use when:
    - User explicitly asks to pause
    - Agent wants silence without changing context
    """
    response = await pause()
    return response.model_dump()


@spotify_mcp.tool()
async def resume_music() -> Dict[str, Any]:
    """
    Resume playback without changing the current context.

    Alias for play_music.
    """
    response = await resume()
    return response.model_dump()


@spotify_mcp.tool()
async def next_song() -> Dict[str, Any]:
    """
    Skip to the next track in the queue.

    Use when:
    - User dislikes current song
    - Agent detects repeated skips or frustration
    """
    response = await next_track()
    return response.model_dump()


@spotify_mcp.tool()
async def previous_song() -> Dict[str, Any]:
    """
    Go back to the previous track.
    """
    response = await previous_track()
    return response.model_dump()


@spotify_mcp.tool()
async def current_playback() -> Dict[str, Any]:
    """
    Fetch the current playback state.

    Use when:
    - Agent needs context before acting
    - Verifying what is currently playing
    """
    response = await get_current_playback()
    return response.model_dump()


# =========================
# VOLUME TOOLS
# =========================

@spotify_mcp.tool()
async def set_playback_volume(volume: int) -> Dict[str, Any]:
    """
    Set playback volume (0–100).

    Args:
        volume (int): Desired volume percentage.

    Use when:
    - Agent wants to reduce or increase intensity
    - User explicitly asks to change volume
    """
    response = await set_volume(volume=volume)
    return response.model_dump()


@spotify_mcp.tool()
async def get_playback_volume() -> Dict[str, Any]:
    """
    Get the current playback volume.

    Use when:
    - Agent wants to make relative volume adjustments
    """
    response = await get_volume()
    return response.model_dump()


# =========================
# SEARCH & PLAY TOOLS
# =========================

@spotify_mcp.tool()
async def search_spotify(
    query: str,
    search_type: str = "track",
    limit: int = 10,
) -> Dict[str, Any]:
    """
    Search Spotify for tracks, artists, albums, or playlists.

    Args:
        query (str): Search keywords.
        search_type (str): One of 'track', 'artist', 'album', 'playlist'.
        limit (int): Maximum number of results.

    Use when:
    - User asks to play something by name
    - Agent needs to resolve a Spotify URI
    """
    response = await search(
        query=query,
        search_type=search_type,
        limit=limit,
    )
    return response.model_dump()


@spotify_mcp.tool()
async def play_song(track_uri: str) -> Dict[str, Any]:
    """
    Play a specific track by Spotify URI.

    Args:
        track_uri (str): Spotify track URI.

    Use when:
        Exact track is already known.
    """
    response = await play_track(track_uri=track_uri)
    return response.model_dump()


@spotify_mcp.tool()
async def play_playlist_by_uri(playlist_uri: str) -> Dict[str, Any]:
    """
    Play a playlist by Spotify URI.
    """
    response = await play_playlist(playlist_uri=playlist_uri)
    return response.model_dump()


@spotify_mcp.tool()
async def play_album_by_uri(album_uri: str) -> Dict[str, Any]:
    """
    Play an album by Spotify URI.
    """
    response = await play_album(album_uri=album_uri)
    return response.model_dump()


@spotify_mcp.tool()
async def play_artist_radio(artist_uri: str) -> Dict[str, Any]:
    """
    Start playback using an artist context (radio-style).
    """
    response = await play_artist(artist_uri=artist_uri)
    return response.model_dump()


# =========================
# LIBRARY TOOLS
# =========================

@spotify_mcp.tool()
async def liked_tracks(limit: int = 20) -> Dict[str, Any]:
    """
    Retrieve the user's liked (saved) tracks.

    Args:
        limit (int): Maximum number of tracks.

    Use when:
    - Agent wants to personalize playback
    - User asks for liked songs
    """
    response = await get_liked_tracks(limit=limit)
    return response.model_dump()


@spotify_mcp.tool()
async def user_playlists(limit: int = 20) -> Dict[str, Any]:
    """
    Retrieve the user's playlists.

    Args:
        limit (int): Maximum number of playlists.
    """
    response = await get_user_playlists(limit=limit)
    return response.model_dump()


# =========================
# DEVICE TOOLS
# =========================

@spotify_mcp.tool()
async def available_devices() -> Dict[str, Any]:
    """
    List available Spotify playback devices.

    Use when:
    - Playback fails due to no active device
    - Agent needs to switch devices
    """
    response = await get_devices()
    return response.model_dump()


@spotify_mcp.tool()
async def switch_device(
    device_id: str,
    play_immediately: bool = True,
) -> Dict[str, Any]:
    """
    Transfer playback to a specific device.

    Args:
        device_id (str): Spotify device ID.
        play_immediately (bool): Resume playback immediately after transfer.

    Use when:
    - User selects a different device
    - Agent detects no active playback device
    """
    response = await transfer_playback(
        device_id=device_id,
        play_immediately=play_immediately,
    )
    return response.model_dump()
