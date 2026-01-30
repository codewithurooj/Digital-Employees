#!/usr/bin/env python3
"""
Verify Gmail API setup is complete and working.

Usage:
    python verify_setup.py [--credentials path/to/credentials.json]

Checks:
1. Required packages installed
2. Credentials file exists and valid
3. Token file exists or can authenticate
4. Can connect to Gmail API
5. Can fetch email count
"""

import sys
import json
from pathlib import Path

def check_packages():
    """Check if required packages are installed."""
    print("Checking required packages...")

    packages = {
        'google.oauth2.credentials': 'google-auth',
        'google_auth_oauthlib.flow': 'google-auth-oauthlib',
        'googleapiclient.discovery': 'google-api-python-client'
    }

    missing = []
    for module, package in packages.items():
        try:
            __import__(module)
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package} - NOT INSTALLED")
            missing.append(package)

    if missing:
        print(f"\n❌ Missing packages. Install with:")
        print(f"   pip install {' '.join(missing)}")
        return False

    print("  All packages installed\n")
    return True


def check_credentials(credentials_path):
    """Check if credentials file exists and is valid."""
    print(f"Checking credentials file: {credentials_path}")

    creds_file = Path(credentials_path)
    if not creds_file.exists():
        print(f"  ✗ File not found")
        print(f"\n❌ Download credentials from Google Cloud Console:")
        print(f"   https://console.cloud.google.com/apis/credentials")
        return False

    try:
        with open(creds_file) as f:
            creds = json.load(f)

        if 'installed' not in creds:
            print(f"  ✗ Invalid format - expected 'installed' key")
            print(f"  Make sure you downloaded Desktop app credentials")
            return False

        installed = creds['installed']
        required = ['client_id', 'client_secret', 'auth_uri', 'token_uri']

        for field in required:
            if field not in installed:
                print(f"  ✗ Missing field: {field}")
                return False

        print(f"  ✓ Credentials file valid")
        print(f"    Client ID: {installed['client_id'][:20]}...")
        return True

    except json.JSONDecodeError:
        print(f"  ✗ Invalid JSON format")
        return False


def check_token(token_path):
    """Check if token file exists."""
    print(f"Checking token file: {token_path}")

    token_file = Path(token_path)
    if token_file.exists():
        try:
            with open(token_file) as f:
                token = json.load(f)

            if 'refresh_token' in token:
                print(f"  ✓ Token file exists with refresh token")
                return True
            else:
                print(f"  ⚠ Token exists but no refresh token")
                return True
        except:
            print(f"  ✗ Token file corrupted")
            return False
    else:
        print(f"  ⚠ Token not found - will authenticate on first run")
        return True


def test_connection(credentials_path, token_path):
    """Test actual connection to Gmail API."""
    print("Testing Gmail API connection...")

    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
        creds = None

        token_file = Path(token_path)
        if token_file.exists():
            creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("  Refreshing token...")
                creds.refresh(Request())
            else:
                print("  ⚠ Authentication required")
                print("  Run the Gmail watcher to authenticate:")
                print("  python -m src.watchers.gmail_watcher --vault ./AI_Employee_Vault")
                return False

        # Test API call
        service = build('gmail', 'v1', credentials=creds)
        profile = service.users().getProfile(userId='me').execute()

        email = profile.get('emailAddress', 'Unknown')
        total = profile.get('messagesTotal', 0)

        print(f"  ✓ Connected successfully")
        print(f"    Email: {email}")
        print(f"    Total messages: {total:,}")

        # Test query
        results = service.users().messages().list(
            userId='me',
            q='is:unread',
            maxResults=1
        ).execute()

        unread_estimate = results.get('resultSizeEstimate', 0)
        print(f"    Unread messages: ~{unread_estimate}")

        return True

    except Exception as e:
        print(f"  ✗ Connection failed: {e}")
        return False


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Verify Gmail API setup')
    parser.add_argument(
        '--credentials',
        default='./config/gmail_credentials.json',
        help='Path to credentials file'
    )
    parser.add_argument(
        '--token',
        default='./config/gmail_token.json',
        help='Path to token file'
    )

    args = parser.parse_args()

    print("=" * 50)
    print("Gmail Watcher Setup Verification")
    print("=" * 50)
    print()

    results = []

    # Check packages
    results.append(("Packages", check_packages()))

    # Check credentials
    results.append(("Credentials", check_credentials(args.credentials)))

    # Check token
    results.append(("Token", check_token(args.token)))

    # Test connection (only if packages and credentials OK)
    if results[0][1] and results[1][1]:
        results.append(("Connection", test_connection(args.credentials, args.token)))

    # Summary
    print()
    print("=" * 50)
    print("Summary")
    print("=" * 50)

    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("✅ Gmail Watcher setup is complete!")
        print("   Run: python -m src.watchers.gmail_watcher --vault ./AI_Employee_Vault")
    else:
        print("❌ Setup incomplete. Fix issues above and re-run verification.")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
