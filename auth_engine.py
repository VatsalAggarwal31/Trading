import os
import pyotp
from dotenv import load_dotenv
from growwapi import GrowwAPI


def generate_daily_token():
    """
    Automates the login process using algorithmic TOTP generation via Groww API.
    """
    print("--- Initializing Automated Authentication Sequence ---")

    # Load secure credentials
    load_dotenv()
    api_key = os.getenv("GROWW_TOTP_TOKEN")
    totp_secret = os.getenv("GROWW_TOTP_SECRET")

    if not all([api_key, totp_secret]):
        raise ValueError("Security Error: Missing credentials in .env file.")

    # Generate the live 6-digit 2FA code
    current_totp = pyotp.TOTP(totp_secret).now()
    print(f"System: Generated Live TOTP Code: {current_totp}")

    try:
        # Request access token using the TOTP flow
        access_token = GrowwAPI.get_access_token(api_key=api_key, totp=current_totp)

        if access_token:
            print("--- SUCCESS: Daily Access Token Secured ---")
            return access_token
        else:
            raise Exception("Authentication failed. No token returned.")

    except Exception as e:
        print(f"Authentication Error: {e}")
        return None


if __name__ == "__main__":
    # Test the token generation
    test_token = generate_daily_token()
    if test_token:
        print("Integration Test Passed. System is ready for autonomous execution.")