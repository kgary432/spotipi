import sys
from spotipy.oauth2 import SpotifyOAuth

if len(sys.argv) > 1:
    username = sys.argv[1]
    scope = 'user-read-currently-playing'

    # Print a URL instead of opening a browser (use a normal browser on another device)
    auth = SpotifyOAuth(
        scope=scope,
        cache_path='.cache',
        open_browser=False,
    )
    auth.get_access_token(as_dict=True)
else:
    print("Usage: %s username" % (sys.argv[0],))
    sys.exit(1)
