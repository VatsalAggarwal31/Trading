import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout
import joblib
import os

# --- NEW ROBUST PATH ROUTING ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_model_paths(ticker):
    safe_ticker = ticker.lower().replace('.', '_').replace('-', '_')
    model_path = os.path.join(BASE_DIR, f'{safe_ticker}_v3.h5')
    scaler_path = os.path.join(BASE_DIR, f'{safe_ticker}_scaler_v3.gz')
    return model_path, scaler_path

# Define our constants
WINDOW_SIZE = 40
FEATURES = ['Close', 'RSI', 'EMA_20', 'ATR', 'Volume_SMA']

def prepare_sequences(data_array):
    """Chunks data into 40-candle windows for the LSTM."""
    X, y = [], []
    # Predict the price 4 candles (1 hour) into the future
    for i in range(WINDOW_SIZE, len(data_array) - 4):
        X.append(data_array[i - WINDOW_SIZE:i])
        y.append(data_array[i + 4, 0])  # Index 0 is the 'Close' price
    return np.array(X), np.array(y)


_cached_models = {}   # ticker -> model instance
_cached_scalers = {}  # ticker -> scaler instance


def train_new_brain(df, ticker="TATASTEEL.NS"):
    """Trains a new LSTM model from scratch using the latest data for the specific ticker."""
    global _cached_models, _cached_scalers
    print(f"--- AI Factory: Forging the 2026 Brain for {ticker} ---")

    # Clear memory cache for this ticker to force reload on next inference
    _cached_models.pop(ticker, None)
    _cached_scalers.pop(ticker, None)

    # Extract features
    data_values = df[FEATURES].values

    # Scale data
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(data_values)
    
    model_path, scaler_path = get_model_paths(ticker)
    joblib.dump(scaler, scaler_path)
    print(f"System: New Scaler saved to {scaler_path}.")

    X, y = prepare_sequences(scaled_data)

    # Build V2 Architecture
    model = Sequential([
        LSTM(64, return_sequences=True, input_shape=(X.shape[1], X.shape[2])),
        Dropout(0.2),
        LSTM(32, return_sequences=False),
        Dropout(0.2),
        Dense(16, activation='relu'),
        Dense(1)
    ])

    model.compile(optimizer='adam', loss='mean_squared_error')

    print(f"Training on {len(X)} sequences...")
    model.fit(X, y, epochs=15, batch_size=32, validation_split=0.1, verbose=1)

    model.save(model_path)
    print(f"--- SUCCESS: Brain V2 Compiled and Saved to {model_path} ---")


def get_live_prediction(df, ticker="TATASTEEL.NS"):
    """Loads the brain (using RAM caching) and predicts the next move based on the latest 40 candles."""
    global _cached_models, _cached_scalers

    model_path, scaler_path = get_model_paths(ticker)

    # Auto-train if missing
    if not os.path.exists(model_path) or not os.path.exists(scaler_path):
        print(f"Missing Model or Scaler for {ticker}. Auto-training a new brain on the fly...")
        train_new_brain(df, ticker)

    if ticker not in _cached_models or ticker not in _cached_scalers:
        _cached_models[ticker] = load_model(model_path)
        _cached_scalers[ticker] = joblib.load(scaler_path)

    # Get the latest window
    recent_data = df[FEATURES].tail(WINDOW_SIZE).values
    scaled_window = _cached_scalers[ticker].transform(recent_data)
    input_tensor = np.expand_dims(scaled_window, axis=0)

    # Predict
    pred_scaled = _cached_models[ticker].predict(input_tensor, verbose=0)

    # Inverse transform to get Rupee value
    dummy = np.zeros((1, len(FEATURES)))
    dummy[0, 0] = pred_scaled[0, 0]
    forecast_price = _cached_scalers[ticker].inverse_transform(dummy)[0, 0]

    return forecast_price



# Local execution test
if __name__ == "__main__":
    from data_engine import fetch_and_prepare_data

    print("Fetching data to train the new model...")
    live_df = fetch_and_prepare_data()

    # Train the model (Uncomment the line below if you want to test the training process)
    train_new_brain(live_df, "TATASTEEL.NS")