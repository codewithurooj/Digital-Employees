#!/usr/bin/env python3
"""
Fetch sample emails from Gmail without running the full watcher.

Usage:
    python fetch_sample.py [--query "is:unread"] [--count 5]

Useful for:
- Testing Gmail API connection
- Previewing emails that match a query
- Debugging email parsing
"""

import sys
import json
import base64
from pathlib import Path
from datetime import datetime


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Fetch sample emails from Gmail')
    parser.add_argument('--query', default='is:unread', help='Gmail search query')
    parser.add_argument('--count', type=int, default=5, help='Number of emails to fetch')
    parser.add_argument('--credentials', default='./config/gmail_credentials.json')
    parser.add_argument('--token', default='./config/gmail_token.json')
    parser.add_argument('--json', action='store_true', help='Output as JSON')

    args = parser.parse_args()

    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError:
        print("Error: Gmail API packages not installed")
        print("Run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
        return 1

    # Load credentials
    token_path = Path(args.token)
    if not token_path.exists():
        print(f"Error: Token not found at {args.token}")
        print("Run verify_setup.py first or authenticate via the watcher")
        return 1

    try:
        creds = Credentials.from_authorized_user_file(str(token_path))
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

        service = build('gmail', 'v1', credentials=creds)

        # Fetch messages
        results = service.users().messages().list(
            userId='me',
            q=args.query,
            maxResults=args.count
        ).execute()

        messages = results.get('messages', [])

        if not messages:
            print(f"No emails found matching: {args.query}")
            return 0

        emails = []

        for msg in messages:
            full_msg = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='full'
            ).execute()

            # Extract headers
            headers = {}
            for h in full_msg.get('payload', {}).get('headers', []):
                headers[h['name']] = h['value']

            # Extract snippet
            snippet = full_msg.get('snippet', '')

            email_data = {
                'id': msg['id'],
                'from': headers.get('From', 'Unknown'),
                'to': headers.get('To', ''),
                'subject': headers.get('Subject', 'No Subject'),
                'date': headers.get('Date', ''),
                'snippet': snippet[:200],
                'labels': full_msg.get('labelIds', [])
            }

            emails.append(email_data)

        if args.json:
            print(json.dumps(emails, indent=2))
        else:
            print(f"Found {len(emails)} emails matching: {args.query}\n")
            print("=" * 70)

            for i, email in enumerate(emails, 1):
                print(f"\n[{i}] {email['subject']}")
                print(f"    From: {email['from']}")
                print(f"    Date: {email['date']}")
                print(f"    Labels: {', '.join(email['labels'])}")
                print(f"    Preview: {email['snippet'][:100]}...")
                print("-" * 70)

        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
