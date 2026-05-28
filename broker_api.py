import os
from dhanhq import dhanhq
from dotenv import load_dotenv

broker_instance = None


def initialize_broker():
    """Connects to Dhan API using static credentials from .env"""
    global broker_instance
    load_dotenv()

    client_id = os.getenv("DHAN_CLIENT_ID")
    access_token = os.getenv("DHAN_ACCESS_TOKEN")

    if not client_id or not access_token:
        print("System Error: Dhan credentials missing in .env file.")
        return False

    try:
        # Dynamically adapt to different dhanhq library signatures
        import inspect
        sig = inspect.signature(dhanhq.__init__)
        if 'client_id' not in sig.parameters:
            broker_instance = dhanhq(access_token)
        else:
            broker_instance = dhanhq(client_id, access_token)
            
        print("System: Broker Actuator (Dhan) Connected successfully.")
        return True
    except Exception as e:
        print(f"System Error: Broker connection failed. {e}")
        return False


TICKER_MAP = {
    "TATASTEEL.NS": "3496",
    "RELIANCE.NS": "2885",
    "INFY.NS": "1594",
    "ITC.NS": "1660",
    "TCS.NS": "11536"
}


def execute_market_order(ticker, quantity, action):
    """Executes a real intraday market order via Dhan."""
    global broker_instance

    if not broker_instance:
        print("Actuator Error: Broker is not initialized. Cannot place order.")
        return False

    try:
        # Load custom Security ID from env, resolve from map, or fallback to TATASTEEL
        security_id = os.getenv("DHAN_SECURITY_ID")
        if not security_id:
            security_id = TICKER_MAP.get(ticker.upper())
            
        if not security_id:
            print(f"System Warning: Ticker '{ticker}' not found in TICKER_MAP. Defaulting to TATASTEEL (3496).")
            security_id = "3496"

        transaction_type = broker_instance.BUY if action == 'BUY' else broker_instance.SELL

        print(f"--- INITIATING REAL ORDER: {action} {quantity} shares of {ticker} (ID: {security_id}) ---")

        order_response = broker_instance.place_order(
            security_id=security_id,
            exchange_segment=broker_instance.NSE,
            transaction_type=transaction_type,
            quantity=quantity,
            order_type=broker_instance.MARKET,
            product_type=broker_instance.INTRA,  # Intraday (MIS)
            price=0
        )

        if order_response.get('status') == 'success':
            print(f"Order Successful! Details: {order_response}")
            return True
        else:
            print(f"Order Failed: {order_response}")
            return False

    except Exception as e:
        print(f"Actuator Error: {e}")
        return False