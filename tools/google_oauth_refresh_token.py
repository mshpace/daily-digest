#!/usr/bin/env python3
"""
One-time helper to generate a Google OAuth refresh token for Gmail + Calendar.

Usage:
  export GOOGLE_CLIENT_ID="xxx"
  export GOOGLE_CLIENT_SECRET="yyy"
  python tools/google_oauth_refresh_token.py

It will:
- Open a browser for Google login
- Ask for read-only Gmail + Calendar permission
- Print a REFRESH TOKEN you copy into GitHub Secrets
"""

from __future__ import annotations

import os
import sys

from google_auth_oauthlib.flow import InstalledAppFlow


SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
]


def main() -> None:
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("ERROR: Missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET in environment.")
        sys.exit(1)

    # OAuth config in the format expected by google-auth-oauthlib
    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    flow = InstalledAppFlow.from_client_config(
        client_config=client_config,
        scopes=SCOPES,
    )

    # Opens browser for user consent
    creds = flow.run_local_server(
        port=0,
        prompt="consent",
        access_type="offline",
    )

    if not creds.refresh_token:
        print("ERROR: No refresh token returned. Try again and ensure consent is granted.")
        sys.exit(1)

    print("\n=== COPY THIS VALUE ===")
    print("GOOGLE_REFRESH_TOKEN:")
    print(creds.refresh_token)
    print("======================\n")


if __name__ == "__main__":
    main()
