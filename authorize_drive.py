"""
ONE-TIME, LOCAL-ONLY setup script. Do not run this in GitHub Actions.

Walks you through Google's OAuth consent flow in your browser and prints a
refresh token to paste into .env / GitHub Actions secrets. Requires the
OAuth Client ID + Secret from a "Desktop app" credential in Google Cloud
Console (see README.md -> "Setting up Google Drive").

Usage:
    pip install google-auth-oauthlib
    python authorize_drive.py
"""
from google_auth_oauthlib.flow import InstalledAppFlow

# drive.file = "only files this app creates/opens" — a non-sensitive scope,
# so it doesn't need Google's manual app-verification review.
SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def main():
    client_id = input("Google OAuth Client ID: ").strip()
    client_secret = input("Google OAuth Client Secret: ").strip()

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    print("\nOpening your browser to sign in and grant Drive access...\n")
    creds = flow.run_local_server(port=0)

    print("\n✅ Success! Add these to your .env (local) and repo secrets (GitHub Actions):\n")
    print(f"GOOGLE_CLIENT_ID={client_id}")
    print(f"GOOGLE_CLIENT_SECRET={client_secret}")
    print(f"GOOGLE_REFRESH_TOKEN={creds.refresh_token}")
    print(
        "\nReminder: in Google Cloud Console -> OAuth consent screen, make sure "
        "publishing status is 'In production' (just a button click for a "
        "non-sensitive scope like drive.file — no review needed). Otherwise "
        "this refresh token expires in 7 days."
    )


if __name__ == "__main__":
    main()
