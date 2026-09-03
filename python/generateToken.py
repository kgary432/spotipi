import os
import sys
import warnings
from urllib.parse import parse_qs, urlparse

from spotipy.oauth2 import SpotifyOAuth


def _cache_path():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".cache")


def _extract_code(redirected):
    redirected = redirected.strip().strip("'\"")
    parsed = urlparse(redirected)
    code = parse_qs(parsed.query).get("code", [None])[0]
    if code:
        return code
    if redirected and "://" not in redirected and "accounts.spotify.com" not in redirected:
        return redirected
    return None


def main():
    if len(sys.argv) < 2:
        print("Usage: %s username" % (sys.argv[0],))
        sys.exit(1)

    missing = [
        name
        for name in ("SPOTIPY_CLIENT_ID", "SPOTIPY_CLIENT_SECRET", "SPOTIPY_REDIRECT_URI")
        if not os.getenv(name)
    ]
    if missing:
        print("Missing environment variables: " + ", ".join(missing))
        sys.exit(1)

    cache_path = _cache_path()
    auth = SpotifyOAuth(
        scope="user-read-currently-playing",
        cache_path=cache_path,
        open_browser=False,
        show_dialog=True,
        requests_timeout=8,
    )

    print()
    print("This machine has no usable browser (SSH / headless Pi).")
    print("Copy the URL below and open it on your laptop or phone:")
    print()
    print(auth.get_authorize_url(), flush=True)
    print()
    print("Log in to Spotify. The browser will then go to your redirect URI")
    print("(often http://127.0.0.1:...) which may look like it failed to load.")
    print("That is expected. Copy the FULL address bar URL — it contains ?code=...")
    print("Do not paste the accounts.spotify.com/authorize URL.")
    print()

    try:
        redirected = input("Paste the redirect URL: ")
    except EOFError:
        print("No input received. Re-run from an interactive SSH session.")
        sys.exit(1)

    if "accounts.spotify.com/authorize" in redirected and "code=" not in redirected:
        print("That is the login URL, not the redirect.")
        print("After you authorize, paste the localhost URL from the address bar.")
        sys.exit(1)

    code = _extract_code(redirected)
    if not code:
        print("Could not find ?code= in that URL.")
        sys.exit(1)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        token_info = auth.get_access_token(code=code, as_dict=True, check_cache=False)

    if not token_info or not token_info.get("access_token"):
        print("Failed to create token.")
        sys.exit(1)
    if not token_info.get("refresh_token"):
        print("Token was created but Spotify did not return a refresh_token.")
        print("Re-check the app Redirect URI and run this again.")
        sys.exit(1)

    print()
    print("Token saved to", os.path.abspath(cache_path))
    print("refresh_token present: yes")


if __name__ == "__main__":
    main()
