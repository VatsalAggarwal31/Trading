# Autonomous Trading Bot — v2

## Setup
```
pip install yfinance pandas numpy tensorflow scikit-learn joblib dhanhq python-dotenv pyotp streamlit plotly
```

## Files
| File | Purpose |
|---|---|
| `auto_trader.py` | Main bot loop — run this first |
| `app.py` | Streamlit dashboard — run in a second terminal |
| `capital_manager.py` | Tracks the growing ₹1000 pool |
| `state_manager.py` | Persists position across restarts |
| `data_engine.py` | Fetches live data + indicators |
| `ai_model.py` | LSTM model training + inference |
| `risk_manager.py` | Position sizing + dynamic stops |
| `broker_api.py` | Dhan API order execution |
| `auth_engine.py` | Dhan token refresh |

## Running
```bash
# Terminal 1 — bot
python auto_trader.py

# Terminal 2 — dashboard
streamlit run app.py
```

## Capital Pool
- Starts at ₹1000
- Every profit is added back; losses are deducted
- Position size scales automatically as capital grows
- Daily loss limit: 10% of current capital → no more trades that day

## Key improvements over v1
- State persisted to `bot_state.json` — survives crashes/restarts
- Stops checked every 60s (not 15min)
- Risk-based position sizing (max 2% capital at risk per trade)
- Daily loss circuit breaker
- No PC shutdown — clean `sys.exit()` only
- Full logging to `bot.log`
- Retries on data fetch failure
- R:R filter — skips trades with R:R < 1.2

## ☁️ 24/7 Google Cloud Platform (GCP) Deployment

The system is configured with production-grade Linux `systemd` daemons and an automated deployment script to run 24/7 on **Google Cloud's Always Free Tier** (`e2-micro` VM running Ubuntu).

### 🚀 Quick Deploy Steps

1. **Create GCP VM Instance**:
   - Create a project on the Google Cloud Console.
   - Navigate to **Compute Engine > VM Instances > Create Instance**.
   - Select `us-central1` (Iowa), `us-east1` (South Carolina), or `us-west1` (Oregon) as region.
   - Select series **E2**, machine type **e2-micro** (2 vCPUs, 1 GB memory).
   - Change boot disk to **Ubuntu 22.04 LTS**, size **30 GB** (Standard persistent disk).
   - Click **Create**.

2. **Open Dashboard Port (8501)**:
   - Navigate to **VPC Network > Firewall**.
   - Create a firewall rule called `allow-streamlit`.
   - Set **Targets** to "All instances in the network" and **Source IPv4 range** to `0.0.0.0/0`.
   - Select **Specified protocols and ports**, check `tcp` and enter `8501`.

3. **Upload Code & Execute Deployment**:
   - Click the **SSH** button next to your VM instance in the GCP console.
   - Drag-and-drop your project files into the terminal window or clone your private git repo.
   - Make the deployment script executable and run it:
     ```bash
     chmod +x setup_gcp.sh
     sudo ./setup_gcp.sh
     ```

4. **Add Broker Credentials**:
   - Edit the newly created `.env` file with your actual Dhan client credentials:
     ```bash
     nano .env
     ```
   - Restart the trading daemon:
     ```bash
     sudo systemctl restart auto_trader
     ```

### 📋 Telemetry & Commands
- **Check Bot Daemon Status**: `sudo systemctl status auto_trader`
- **Stream Real-time Bot Logs**: `sudo journalctl -u auto_trader -f -n 50`
- **Check Dashboard Status**: `sudo systemctl status streamlit_dashboard`

