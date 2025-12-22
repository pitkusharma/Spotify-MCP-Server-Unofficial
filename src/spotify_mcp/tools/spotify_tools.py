from typing import Dict, Any, List

from src.spotify_mcp.server import mcp as spotify_mcp
from src.spotify_mcp.services.spotify_services import play, pause, next_track, previous_track, get_user_profile, \
    get_user_playlists, get_playlist_tracks, create_playlist, add_tracks_to_playlist, remove_tracks_from_playlist, \
    search_tracks, get_liked_songs


# =========================
# PLAYER TOOLS
# =========================

@spotify_mcp.tool()
def play_music() -> Dict[str, Any]:
    """
    Start or resume music playback on the user's active Spotify device.

    Returns:
        Dict[str, Any]:
            A JSON-like dictionary containing:
            - "status": bool -> True if request succeeded, False otherwise.
            - "message": str -> Human-readable success or error message.
            - "data": Any -> Additional response data if available, else None.
    """
    return play().model_dump()


@spotify_mcp.tool()
def pause_music() -> Dict[str, Any]:
    """
    Pause the currently playing Spotify track.

    Returns:
        Dict[str, Any]:
            JSON-like dict with status, message, and optional data.
    """
    return pause().model_dump()


@spotify_mcp.tool()
def next_song() -> Dict[str, Any]:
    """
    Skip forward to the next track in the playback queue.

    Returns:
        Dict[str, Any]:
            JSON-like dict with status, message, and optional data.
    """
    return next_track().model_dump()


@spotify_mcp.tool()
def previous_song() -> Dict[str, Any]:
    """
    Skip backward to the previous track in the playback queue.

    Returns:
        Dict[str, Any]:
            JSON-like dict with status, message, and optional data.
    """
    return previous_track().model_dump()


# =========================
# PROFILE TOOLS
# =========================

@spotify_mcp.tool()
def get_profile() -> Dict[str, Any]:
    """
    Retrieve the Spotify profile of the currently authenticated user.

    Returns:
        Dict[str, Any]:
            Dictionary with:
            - "status": bool
            - "message": str
            - "data": dict with user profile details if successful
    """
    return get_user_profile().model_dump()


# =========================
# PLAYLIST TOOLS
# =========================

@spotify_mcp.tool()
def list_playlists(limit: int = 20) -> Dict[str, Any]:
    """
    Fetch the current user's playlists.

    Args:
        limit (int): Maximum number of playlists to return.

    Returns:
        Dict[str, Any]:
            Dictionary containing playlists data if successful.
    """
    return get_user_playlists(limit=limit).model_dump()


@spotify_mcp.tool()
def list_playlist_tracks(playlist_id: str, limit: int = 50) -> Dict[str, Any]:
    """
    Get tracks from a specific Spotify playlist.

    Args:
        playlist_id (str): Spotify ID of the playlist.
        limit (int): Maximum number of tracks to fetch.

    Returns:
        Dict[str, Any]:
            Dictionary containing track list if successful.
    """
    return get_playlist_tracks(playlist_id=playlist_id, limit=limit).model_dump()


@spotify_mcp.tool()
def create_new_playlist(
    user_id: str,
    name: str,
    description: str = "",
    public: bool = False
) -> Dict[str, Any]:
    """
    Create a new playlist for a Spotify user.

    Args:
        user_id (str): Spotify user ID.
        name (str): Name of the new playlist.
        description (str): Optional description for the playlist.
        public (bool): Whether the playlist should be publicly visible.

    Returns:
        Dict[str, Any]:
            Dictionary containing created playlist info if successful.
    """
    return create_playlist(
        user_id=user_id,
        name=name,
        description=description,
        public=public
    ).model_dump()


@spotify_mcp.tool()
def add_tracks(
    playlist_id: str,
    track_uris: List[str]
) -> Dict[str, Any]:
    """
    Add tracks to an existing Spotify playlist.

    Args:
        playlist_id (str): Spotify playlist ID.
        track_uris (List[str]): List of Spotify track URIs.

    Returns:
        Dict[str, Any]:
            Dictionary indicating success or failure.
    """
    return add_tracks_to_playlist(
        playlist_id=playlist_id,
        track_uris=track_uris
    ).model_dump()


@spotify_mcp.tool()
def remove_tracks(
    playlist_id: str,
    track_uris: List[str]
) -> Dict[str, Any]:
    """
    Remove tracks from a Spotify playlist.

    Args:
        playlist_id (str): Spotify playlist ID.
        track_uris (List[str]): List of Spotify track URIs to remove.

    Returns:
        Dict[str, Any]:
            Dictionary indicating success or failure.
    """
    return remove_tracks_from_playlist(
        playlist_id=playlist_id,
        track_uris=track_uris
    ).model_dump()


# =========================
# SEARCH TOOLS
# =========================

@spotify_mcp.tool()
def search_song(query: str, limit: int = 10) -> Dict[str, Any]:
    """
    Search for tracks on Spotify using a text query.

    Args:
        query (str): Search keywords (song name, artist, etc.).
        limit (int): Max results to return.

    Returns:
        Dict[str, Any]:
            Dictionary containing matching tracks.
    """
    return search_tracks(query=query, limit=limit).model_dump()


# =========================
# LIBRARY TOOLS
# =========================

@spotify_mcp.tool()
def liked_songs(limit: int = 20) -> Dict[str, Any]:
    """
    Retrieve the user's liked (saved) songs from Spotify.

    Args:
        limit (int): Maximum number of songs to return.

    Returns:
        Dict[str, Any]:
            Dictionary containing liked tracks.
    """
    return get_liked_songs(limit=limit).model_dump()
