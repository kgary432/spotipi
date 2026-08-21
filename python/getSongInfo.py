import spotipy
from spotipy.oauth2 import SpotifyOAuth


def getSongInfo(username, token_path):
    scope = 'user-read-currently-playing'

    auth = SpotifyOAuth(
        scope=scope,
        cache_path=token_path,
        open_browser=False,
    )

    # Never prompt interactively (systemd has no TTY / no browser)
    token_info = auth.cache_handler.get_cached_token()
    if not token_info:
        print("No Spotify token cache at", token_path)
        print("Run generate-token.sh first")
        return None

    if auth.is_token_expired(token_info):
        refresh = token_info.get('refresh_token')
        if not refresh:
            print("Spotify token expired and no refresh_token; run generate-token.sh")
            return None
        token_info = auth.refresh_access_token(refresh)

    sp = spotipy.Spotify(auth=token_info['access_token'])
    result = sp.current_user_playing_track()

    if result is None or result.get('item') is None:
        print("No song playing")
        return None

    song = result['item']['name']
    imageURL = result['item']['album']['images'][0]['url']
    print(song)
    return [song, imageURL]
