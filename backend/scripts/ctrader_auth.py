"""
cTrader OAuth 2.0 Authorization Script

Usage: cd backend && python -m scripts.ctrader_auth

This script:
1. Opens the browser for cTrader OAuth authorization
2. Starts a local HTTP server to capture the callback
3. Exchanges the authorization code for access/refresh tokens
4. Saves tokens to config/ctrader_accounts_local.py
"""
import http.server
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import webbrowser

# cTrader OAuth endpoints
AUTH_URL = "https://openapi.ctrader.com/apps/auth"
TOKEN_URL = "https://openapi.ctrader.com/apps/token"
REDIRECT_URI = "http://localhost:5000/callback"
CALLBACK_PORT = 5000

# Load current config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.ctrader_accounts_local import CTRADER_CLIENT_ID, CTRADER_CLIENT_SECRET


class OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    """HTTP handler to capture OAuth callback"""
    auth_code = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "code" in params:
            OAuthCallbackHandler.auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Authorization successful!</h1>"
                           b"<p>You can close this window.</p></body></html>")
        else:
            error = params.get("error", ["unknown"])[0]
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(f"<html><body><h1>Error: {error}</h1></body></html>".encode())

    def log_message(self, format, *args):
        pass  # Suppress default logging


def exchange_code_for_tokens(auth_code: str) -> dict:
    """Exchange authorization code for access and refresh tokens"""
    data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CTRADER_CLIENT_ID,
        "client_secret": CTRADER_CLIENT_SECRET,
    }).encode()

    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())


def refresh_tokens(refresh_token: str) -> dict:
    """Refresh access token using refresh token"""
    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": CTRADER_CLIENT_ID,
        "client_secret": CTRADER_CLIENT_SECRET,
    }).encode()

    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())


def save_tokens(access_token: str, refresh_token: str):
    """Update tokens in ctrader_accounts_local.py"""
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "config", "ctrader_accounts_local.py"
    )

    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Replace access token
    content = re.sub(
        r'CTRADER_ACCESS_TOKEN\s*=\s*"[^"]*"',
        f'CTRADER_ACCESS_TOKEN = "{access_token}"',
        content
    )

    # Replace refresh token
    content = re.sub(
        r'CTRADER_REFRESH_TOKEN\s*=\s*"[^"]*"',
        f'CTRADER_REFRESH_TOKEN = "{refresh_token}"',
        content
    )

    with open(config_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Tokens saved to {config_path}")


def main():
    print("=" * 60)
    print("cTrader OAuth 2.0 Authorization")
    print("=" * 60)

    # Check for refresh mode
    if len(sys.argv) > 1 and sys.argv[1] == "--refresh":
        from config.ctrader_accounts_local import CTRADER_REFRESH_TOKEN
        if not CTRADER_REFRESH_TOKEN:
            print("No refresh token found. Run without --refresh first.")
            sys.exit(1)
        print("Refreshing tokens...")
        tokens = refresh_tokens(CTRADER_REFRESH_TOKEN)
        save_tokens(tokens["access_token"], tokens["refresh_token"])
        print("Tokens refreshed successfully!")
        return

    # Build authorization URL
    auth_params = urllib.parse.urlencode({
        "client_id": CTRADER_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "accounts",
    })
    auth_url = f"{AUTH_URL}?{auth_params}"

    print(f"\nClient ID: {CTRADER_CLIENT_ID[:20]}...")
    print(f"Redirect URI: {REDIRECT_URI}")
    print(f"\nOpening browser for authorization...")
    print(f"If the browser doesn't open, visit:\n{auth_url}\n")

    # Start local HTTP server
    server = http.server.HTTPServer(("localhost", CALLBACK_PORT), OAuthCallbackHandler)
    server.timeout = 120  # 2 minute timeout

    # Open browser
    webbrowser.open(auth_url)

    print(f"Waiting for callback on port {CALLBACK_PORT}...")

    # Wait for callback
    while OAuthCallbackHandler.auth_code is None:
        server.handle_request()

    auth_code = OAuthCallbackHandler.auth_code
    print(f"\nAuthorization code received: {auth_code[:20]}...")

    # Exchange code for tokens
    print("Exchanging code for tokens...")
    tokens = exchange_code_for_tokens(auth_code)

    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    print(f"Access token: {access_token[:20]}...")
    print(f"Refresh token: {refresh_token[:20]}...")

    # Save tokens
    save_tokens(access_token, refresh_token)

    print("\nDone! You can now start the monitor with cTrader support.")
    print("To refresh tokens later: python -m scripts.ctrader_auth --refresh")


if __name__ == "__main__":
    main()
