import os
import time

import spotipy
from spotipy.oauth2 import SpotifyOAuth


class SpotifyAuthError(Exception):
    pass


class NothingPlaying(Exception):
    pass


def _require_env():
    missing = [
        name
        for name in ("SPOTIPY_CLIENT_ID", "SPOTIPY_CLIENT_SECRET", "SPOTIPY_REDIRECT_URI")
        if not os.getenv(name)
    ]
    if missing:
        raise SpotifyAuthError(
            "Missing %s in the service environment. "
            "Put them in /etc/systemd/system/spotipi.service.d/spotipi_env.conf"
            % ", ".join(missing)
        )


def _save_cache(auth, token_info, token_path):
    auth.cache_handler.save_token_to_cache(token_info)
    try:
        os.chmod(token_path, 0o644)
    except OSError:
        pass


def getSongInfo(username, token_path):
    _require_env()

    auth = SpotifyOAuth(
        scope="user-read-currently-playing",
        cache_path=token_path,
        open_browser=False,
        requests_timeout=8,
    )

    token_info = auth.cache_handler.get_cached_token()
    if not token_info or not token_info.get("access_token"):
        raise SpotifyAuthError("No Spotify token cache at %s. Run generate-token.sh" % token_path)

    # Refresh a couple of minutes early so overnight runs never use a stale token.
    expires_at = float(token_info.get("expires_at") or 0)
    if expires_at - time.time() < 120 or auth.is_token_expired(token_info):
        refresh = token_info.get("refresh_token")
        if not refresh:
            raise SpotifyAuthError(
                "Spotify token expired and .cache has no refresh_token. Run generate-token.sh"
            )
        try:
            token_info = auth.refresh_access_token(refresh)
        except Exception as e:
            raise SpotifyAuthError("Spotify token refresh failed: %s" % e)
        if not token_info or not token_info.get("access_token"):
            raise SpotifyAuthError("Spotify token refresh returned no access_token")
        _save_cache(auth, token_info, token_path)
        print("spotify token refreshed", flush=True)

    sp = spotipy.Spotify(auth=token_info["access_token"], requests_timeout=8)
    result = sp.current_user_playing_track()

    if result is None or result.get("item") is None:
        raise NothingPlaying("No song playing")

    song = result["item"]["name"]
    images = result["item"]["album"].get("images") or []
    if not images:
        raise NothingPlaying("Song has no album art")
    print(song, flush=True)
    return [song, images[0]["url"]]
