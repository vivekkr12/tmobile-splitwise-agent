#!/usr/bin/env python3
"""
Interactive OAuth 2.0 flow for Splitwise.
Run this script once to get your OAuth2 access token.

Usage:
    python agent/oauth2_flow.py
"""
import os
import sys
from urllib.parse import urlparse, parse_qs
from splitwise import Splitwise

# Try to load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def main():
    """Run interactive OAuth 2.0 flow to get access token."""
    print("=" * 60)
    print("Splitwise OAuth 2.0 Authentication")
    print("=" * 60)
    print()

    # Get consumer key and secret from environment
    consumer_key = os.getenv("SW_CONSUMER_KEY")
    consumer_secret = os.getenv("SW_CONSUMER_SECRET")

    if not consumer_key or not consumer_secret:
        print("ERROR: Missing Splitwise app credentials!")
        print()
        print("Please set the following environment variables:")
        print("  SW_CONSUMER_KEY=<your_consumer_key>")
        print("  SW_CONSUMER_SECRET=<your_consumer_secret>")
        print()
        print("You can add these to your .env file or set them directly.")
        print()
        print("Get your credentials from: https://secure.splitwise.com/apps")
        sys.exit(1)

    print(f"✓ Found consumer key: {consumer_key[:8]}...")
    print(f"✓ Found consumer secret: {consumer_secret[:8]}...")
    print()

    # Create Splitwise client
    s = Splitwise(consumer_key, consumer_secret)

    # Step 1: Get authorization URL
    print("Step 1: Authorization")
    print("-" * 60)

    # You can use any redirect URI, even localhost or a custom scheme
    # For simplicity, we'll use a localhost URL
    redirect_uri = "http://localhost:8000/callback"

    try:
        url, state = s.getOAuth2AuthorizeURL(redirect_uri)
    except Exception as e:
        print(f"ERROR: Failed to get authorization URL: {e}")
        sys.exit(1)

    print()
    print("Please visit this URL to authorize the application:")
    print()
    print(f"  {url}")
    print()
    print("After authorizing, you will be redirected to a URL that looks like:")
    print(f"  {redirect_uri}?code=XXXXXX&state=XXXXXX")
    print()
    print("The page might show an error (that's OK if you're using localhost).")
    print("Just copy the ENTIRE URL from your browser's address bar.")
    print()

    # Step 2: Get the redirect URL from user
    print("Step 2: Get Authorization Code")
    print("-" * 60)
    redirect_url = input("Paste the full redirect URL here: ").strip()
    print()

    # Parse the redirect URL to extract code and state
    try:
        parsed = urlparse(redirect_url)
        params = parse_qs(parsed.query)

        code = params.get('code', [None])[0]
        returned_state = params.get('state', [None])[0]

        if not code:
            print("ERROR: No authorization code found in the URL!")
            print("Make sure you copied the complete URL from the browser.")
            sys.exit(1)

        if returned_state != state:
            print("WARNING: State mismatch! This might be a security issue.")
            print(f"Expected: {state}")
            print(f"Got: {returned_state}")
            proceed = input("Continue anyway? (yes/no): ").strip().lower()
            if proceed != 'yes':
                print("Aborted.")
                sys.exit(1)

        print(f"✓ Found authorization code: {code[:10]}...")
        print()

    except Exception as e:
        print(f"ERROR: Failed to parse redirect URL: {e}")
        sys.exit(1)

    # Step 3: Exchange code for access token
    print("Step 3: Exchange Code for Access Token")
    print("-" * 60)

    try:
        access_token_data = s.getOAuth2AccessToken(code, redirect_uri)

        if not access_token_data or 'access_token' not in access_token_data:
            print("ERROR: Failed to get access token!")
            print(f"Response: {access_token_data}")
            sys.exit(1)

        access_token = access_token_data['access_token']
        token_type = access_token_data.get('token_type', 'Bearer')

        print(f"✓ Successfully obtained access token!")
        print()

    except Exception as e:
        print(f"ERROR: Failed to exchange code for token: {e}")
        sys.exit(1)

    # Step 4: Test the token
    print("Step 4: Testing Access Token")
    print("-" * 60)

    try:
        s.setOAuth2AccessToken(access_token_data)
        user = s.getCurrentUser()

        first_name = user.getFirstName() or ""
        last_name = user.getLastName() or ""
        email = user.getEmail() or ""

        print(f"✓ Authentication successful!")
        print(f"  Name: {first_name} {last_name}")
        print(f"  Email: {email}")
        print()

    except Exception as e:
        print(f"ERROR: Failed to verify token: {e}")
        sys.exit(1)

    # Step 5: Show instructions
    print("=" * 60)
    print("SUCCESS! 🎉")
    print("=" * 60)
    print()
    print("Add this to your .env file:")
    print()
    print(f"SW_OAUTH2_ACCESS_TOKEN={access_token}")
    print()
    print("Or set it as an environment variable:")
    print()
    print(f"export SW_OAUTH2_ACCESS_TOKEN={access_token}")
    print()
    print("Note: This access token does not expire, so you can reuse it.")
    print("Keep it secure and never commit it to version control!")
    print()

    # Optionally append to .env file
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_path):
        append = input("Append to .env file automatically? (yes/no): ").strip().lower()
        if append == 'yes':
            with open(env_path, 'a') as f:
                f.write(f"\n# Splitwise OAuth2 Access Token (generated {os.popen('date').read().strip()})\n")
                f.write(f"SW_OAUTH2_ACCESS_TOKEN={access_token}\n")
            print(f"✓ Appended to {env_path}")
    else:
        print(f"No .env file found at {env_path}")
        print("You can create one and add the token manually.")


if __name__ == "__main__":
    main()
