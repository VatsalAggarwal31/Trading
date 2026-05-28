import time
import yfinance as yf
import pandas as pd
import numpy as np


def fetch_and_prepare_data(ticker="TATASTEEL.NS", retries=3, delay=10):
    """
    Fetches the latest intraday data and calculates technical indicators.
    Retries up to `retries` times on failure (yfinance can be flaky).
    """
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            df = yf.download(ticker, period="5d", interval="1m", progress=False)

            if df.empty:
                raise ValueError(f"Yahoo Finance returned no data for {ticker}.")

            # Flatten MultiIndex columns from newer yfinance versions
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # ── Technical indicators ──────────────────────────────
            df['EMA_20']     = df['Close'].ewm(span=20, adjust=False).mean()
            df['Volume_SMA'] = df['Volume'].rolling(window=20).mean()

            # RSI (14) using true Wilder's smoothing (RMA/MMA)
            delta = df['Close'].diff()
            gain = delta.clip(lower=0)
            loss = -delta.clip(upper=0)
            
            avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
            avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
            
            # Prevent division by zero and handle flat periods
            rs = np.where(avg_loss == 0, 1e10, avg_gain / avg_loss)
            df['RSI'] = 100 - (100 / (1 + rs))
            df.loc[avg_loss == 0, 'RSI'] = 100.0
            df.loc[(avg_gain == 0) & (avg_loss == 0), 'RSI'] = 50.0

            # ATR (14)
            high_low   = df['High'] - df['Low']
            high_close = np.abs(df['High'] - df['Close'].shift())
            low_close  = np.abs(df['Low']  - df['Close'].shift())
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            df['ATR']  = true_range.rolling(14).mean()

            df.dropna(inplace=True)

            if len(df) < 50:
                raise ValueError(f"Not enough data after cleaning ({len(df)} rows). Market may be closed or data incomplete.")

            return df

        except Exception as e:
            last_error = e
            if attempt < retries:
                print(f"[DataEngine] Attempt {attempt} failed: {e}. Retrying in {delay}s...")
                time.sleep(delay)

    raise RuntimeError(f"Data engine failed after {retries} attempts. Last error: {last_error}")


if __name__ == "__main__":
    print("--- Data Engine Test ---")
    try:
        data = fetch_and_prepare_data()
        print(f"Success: {len(data)} data points fetched.")
        print(data[['Close', 'RSI', 'EMA_20', 'ATR']].tail(3))
    except Exception as e:
        print(f"Failure: {e}")
