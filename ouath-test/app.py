
import httpx
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

import getpass

# --- CONFIGURATION ---
REDIRECT_URI = "http://localhost:8080/callback"
AUTH_URL = "https://github.com/login/oauth/authorize"
TOKEN_URL = "https://github.com/login/oauth/access_token"
SCOPE = "repo,user"

# --- OAuth Handler ---
class OAuthCallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        query_params = parse_qs(parsed_path.query)

        if parsed_path.path == "/callback":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Authentication successful!</h1><p>You can close this window.</p></body></html>")

            code = query_params.get("code", [None])[0]
            if code:
                print(f"Authorization code received: {code}")
                self.server.access_token = self.get_access_token(
                    code, self.server.client_id, self.server.client_secret
                )
            else:
                print("Could not find authorization code in callback.")
            
            # Signal the server to shut down
            self.server.should_shutdown = True
        else:
            self.send_response(404)
            self.end_headers()

    def get_access_token(self, code: str, client_id: str, client_secret: str) -> str | None:
        """Exchanges the authorization code for an access token."""
        headers = {"Accept": "application/json"}
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": REDIRECT_URI,
        }
        try:
            with httpx.Client() as client:
                response = client.post(TOKEN_URL, headers=headers, data=data)
                response.raise_for_status()
                token_data = response.json()
                return token_data.get("access_token")
        except httpx.RequestError as e:
            print(f"Error requesting access token: {e}")
            return None

# --- Main Application Logic ---
def main():
    client_id = input("Enter your GitHub OAuth Client ID: ")
    client_secret = getpass.getpass("Enter your GitHub OAuth Client Secret: ")

    if not client_id or not client_secret:
        print("Client ID and Client Secret are required.")
        return

    # 1. Construct and print the authorization URL
    auth_params = f"client_id={client_id}&redirect_uri={REDIRECT_URI}&scope={SCOPE}"
    authorization_url = f"{AUTH_URL}?{auth_params}"
    
    print("Please open the following URL in your browser to authorize the application:")
    print(authorization_url)
    
    # Optionally, open the URL automatically in the default browser
    # webbrowser.open(authorization_url)

    # 2. Start a local server to listen for the callback
    server_address = ('', 8080)
    httpd = HTTPServer(server_address, OAuthCallbackHandler)
    httpd.client_id = client_id
    httpd.client_secret = client_secret
    httpd.access_token = None
    httpd.should_shutdown = False
    
    print("\nWaiting for authentication callback on port 8080...")

    # 3. Handle requests until the shutdown flag is set
    while not httpd.should_shutdown:
        httpd.handle_request()

    if httpd.access_token:
        print(f"\nGitHub Access Token: {httpd.access_token}")
    else:
        print("\nFailed to retrieve access token.")
        
    print("Application exiting.")

if __name__ == "__main__":
    main()
