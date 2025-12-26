#!/usr/bin/env python3
"""
Tumblr OAuth Credential Helper
Helps you obtain OAuth tokens for the Tumblr API
"""

import sys

try:
    from requests_oauthlib import OAuth1Session
except ImportError:
    print("Error: requests_oauthlib not installed.")
    print("Run: python -m pip install requests-oauthlib")
    sys.exit(1)


def get_oauth_tokens(consumer_key, consumer_secret):
    """
    Walk through OAuth 1.0a flow to get access tokens.

    Args:
        consumer_key: Your app's consumer key
        consumer_secret: Your app's consumer secret

    Returns:
        Tuple of (oauth_token, oauth_token_secret)
    """
    # Tumblr OAuth endpoints
    request_token_url = 'https://www.tumblr.com/oauth/request_token'
    authorize_url = 'https://www.tumblr.com/oauth/authorize'
    access_token_url = 'https://www.tumblr.com/oauth/access_token'

    print("\n" + "="*60)
    print("Tumblr OAuth Authentication")
    print("="*60)

    # Step 1: Get request token
    print("\nStep 1: Obtaining request token...")
    oauth = OAuth1Session(consumer_key, client_secret=consumer_secret)

    try:
        fetch_response = oauth.fetch_request_token(request_token_url)
    except Exception as e:
        print(f"\nError obtaining request token: {e}")
        print("\nPossible issues:")
        print("- Check that your Consumer Key and Secret are correct")
        print("- Make sure you registered the app at https://www.tumblr.com/oauth/apps")
        return None

    resource_owner_key = fetch_response.get('oauth_token')
    resource_owner_secret = fetch_response.get('oauth_token_secret')

    print("✓ Request token obtained")

    # Step 2: Get authorization from user
    print("\nStep 2: Authorization required")
    authorization_url = oauth.authorization_url(authorize_url)
    print(f"\nPlease visit this URL to authorize the application:\n")
    print(f"  {authorization_url}\n")
    print("After authorizing, you'll be redirected to a URL.")
    print("Copy the ENTIRE redirect URL and paste it here.")

    redirect_response = input("\nPaste the full redirect URL here: ").strip()

    if not redirect_response:
        print("\nError: No URL provided")
        return None

    # Step 3: Get access token
    print("\nStep 3: Obtaining access token...")
    oauth = OAuth1Session(
        consumer_key,
        client_secret=consumer_secret,
        resource_owner_key=resource_owner_key,
        resource_owner_secret=resource_owner_secret,
        verifier=redirect_response
    )

    try:
        oauth_tokens = oauth.fetch_access_token(access_token_url)
    except Exception as e:
        print(f"\nError obtaining access token: {e}")
        return None

    oauth_token = oauth_tokens.get('oauth_token')
    oauth_token_secret = oauth_tokens.get('oauth_token_secret')

    print("✓ Access token obtained successfully!")

    return (oauth_token, oauth_token_secret)


def save_credentials_to_file(consumer_key, consumer_secret, oauth_token, oauth_token_secret):
    """Save credentials to a .env file"""
    try:
        with open('.env', 'w') as f:
            f.write(f'TUMBLR_CONSUMER_KEY={consumer_key}\n')
            f.write(f'TUMBLR_CONSUMER_SECRET={consumer_secret}\n')
            f.write(f'TUMBLR_OAUTH_TOKEN={oauth_token}\n')
            f.write(f'TUMBLR_OAUTH_SECRET={oauth_token_secret}\n')
        return True
    except Exception as e:
        print(f"\nWarning: Could not save to .env file: {e}")
        return False


def main():
    """Main entry point"""
    print("\n" + "="*60)
    print("Tumblr API Credential Helper")
    print("="*60)
    print("\nThis script will help you get your OAuth tokens.")
    print("\nFirst, you need to register an app at:")
    print("  https://www.tumblr.com/oauth/apps")
    print("\nYou'll need:")
    print("  - Application Name: (any name, e.g., 'Profile Finder')")
    print("  - Application Website: http://localhost")
    print("  - Default callback URL: http://localhost")
    print("\nAfter registering, you'll receive:")
    print("  - OAuth Consumer Key")
    print("  - OAuth Consumer Secret (click 'Show secret key')")
    print("\n" + "="*60)

    # Get consumer credentials from user
    print("\nEnter your app credentials from Tumblr:\n")
    consumer_key = input("OAuth Consumer Key: ").strip()
    consumer_secret = input("OAuth Consumer Secret: ").strip()

    if not consumer_key or not consumer_secret:
        print("\nError: Both Consumer Key and Consumer Secret are required.")
        return 1

    # Get OAuth tokens
    result = get_oauth_tokens(consumer_key, consumer_secret)

    if not result:
        print("\nFailed to obtain OAuth tokens.")
        return 1

    oauth_token, oauth_token_secret = result

    # Save credentials to .env file
    print("\nSaving credentials to .env file...")
    if save_credentials_to_file(consumer_key, consumer_secret, oauth_token, oauth_token_secret):
        print("✓ Credentials saved to .env file")

    # Display results
    print("\n" + "="*60)
    print("SUCCESS! Here are your credentials:")
    print("="*60)
    print(f"\nOAuth Consumer Key:     {consumer_key}")
    print(f"OAuth Consumer Secret:  {consumer_secret}")
    print(f"OAuth Token:            {oauth_token}")
    print(f"OAuth Token Secret:     {oauth_token_secret}")

    # Provide instructions for setting environment variables
    print("\n" + "="*60)
    print("How to use these credentials:")
    print("="*60)

    print("\nOption 1: Use the .env file (RECOMMENDED)")
    print("  The credentials have been saved to .env file automatically!")
    print("  Just run: python tumblr_profile_finder.py")

    print("\nOption 2: Set environment variables manually (PowerShell):\n")
    print(f'$env:TUMBLR_CONSUMER_KEY="{consumer_key}"')
    print(f'$env:TUMBLR_CONSUMER_SECRET="{consumer_secret}"')
    print(f'$env:TUMBLR_OAUTH_TOKEN="{oauth_token}"')
    print(f'$env:TUMBLR_OAUTH_SECRET="{oauth_token_secret}"')

    print("\n" + "="*60)
    print("You're all set! Run tumblr_profile_finder.py to start searching.")
    print("="*60)

    # Pause before closing
    input("\nPress Enter to close this window...")

    return 0


if __name__ == '__main__':
    try:
        exit(main())
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        exit(1)
