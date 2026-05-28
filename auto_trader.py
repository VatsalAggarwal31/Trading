import time
import os
import sys
import csv
import logging
from datetime import datetime, timezone, timedelta

def get_ist_now():
    return datetime.now(timezone(timedelta(hours=5, minutes=30)))

from data_engine import fetch_and_prepare_data
from ai_model import get_live_prediction
from risk_manager import calculate_position_size, calculate_dynamic_stops, get_risk_reward_ratio
from broker_api import initialize_broker, execute_market_order
from capital_manager import get_capital, record_trade_result
from state_manager import load_state, save_state, clear_position

# ============================================================
#  SYSTEM CONFIGURATION
# ============================================================
TICKER = "TATASTEEL.NS"
DRY_RUN = True               # Set False only when ready for live orders

# Timing
SIGNAL_INTERVAL_SEC = 900    # Generate new entry signals every 15 min
STOP_CHECK_INTERVAL_SEC = 60 # Check stop-loss / take-profit every 60 sec

# Risk rules
DAILY_LOSS_LIMIT_PCT = 0.10  # Halt trading if down 10% on the day (Rs.100 on Rs.1000)
MIN_PROFIT_MARGIN = 0.005    # AI must forecast >0.5% upside to enter
MIN_RISK_REWARD = 1.2        # Skip trade if R:R ratio is below this

# Market schedule (IST)
MARKET_OPEN   = "09:15"
SQUARE_OFF_AT = "15:15"      # Force-close any open position at this time
MARKET_CLOSE  = "15:30"
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger('AutoTrader')


# ── Helpers ──────────────────────────────────────────────────

def _t(hhmm):
    return datetime.strptime(hhmm, "%H:%M").time()


def is_market_open():
    now = get_ist_now()
    # 0 = Monday, 5 = Saturday, 6 = Sunday in Python's weekday()
    if now.weekday() >= 5:
        return False
    return _t(MARKET_OPEN) <= now.time() <= _t(MARKET_CLOSE)


def is_square_off_time():
    return get_ist_now().time() >= _t(SQUARE_OFF_AT)


def daily_limit_hit(state, capital):
    limit = capital * DAILY_LOSS_LIMIT_PCT
    return state['daily_pnl'] <= -abs(limit)


def calculate_free_cash(state, total_capital):
    invested_value = 0.0
    for ticker, pos in state.get('positions', {}).items():
        if pos.get('holding_position', False):
            invested_value += pos.get('entry_price', 0.0) * pos.get('current_shares', 0)
    return max(0.0, round(total_capital - invested_value, 2))


def log_trade_csv(action, ticker, price, shares, pnl=0.0):
    file_exists = os.path.isfile('trade_history.csv')
    with open('trade_history.csv', 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['Timestamp', 'Action', 'Ticker', 'Price', 'Shares', 'Total_Value', 'PnL'])
        writer.writerow([
            get_ist_now().strftime('%Y-%m-%d %H:%M:%S'),
            action, ticker,
            round(price, 2), shares,
            round(price * shares, 2),
            round(pnl, 2)
        ])


# ── Core sell logic ──────────────────────────────────────────

def execute_sell(state, ticker, current_price, reason="", effective_dry_run=None):
    pos = state.get('positions', {}).get(ticker, {})
    if not pos or not pos.get('holding_position', False):
        return state

    shares = pos['current_shares']
    entry  = pos['entry_price']
    pnl    = round((current_price - entry) * shares, 2)
    sign   = "+" if pnl >= 0 else ""
    
    if effective_dry_run is None:
        dry_run_state = state.get('dry_run', True)
        effective_dry_run = dry_run_state
        if not dry_run_state:
            if not initialize_broker():
                effective_dry_run = True

    success = True
    if not effective_dry_run:
        success = execute_market_order(ticker, shares, "SELL")

    if success:
        new_capital = record_trade_result("SELL", current_price, shares, pnl)
        state = clear_position(state, ticker)
        state['daily_pnl'] = round(state.get('daily_pnl', 0) + pnl, 2)
        state['trade_count_today'] = state.get('trade_count_today', 0) + 1
        save_state(state)
        log_trade_csv("SELL", ticker, current_price, shares, pnl)

        icon = "[WIN]" if pnl >= 0 else "[LOSS]"
        log.info(
            f"{icon} SELL {ticker} [{reason}] | {shares} shares @ Rs.{current_price:.2f} | "
            f"PnL: {sign}Rs.{pnl:.2f} | Pool: Rs.{new_capital:.2f}"
        )
    else:
        log.error(f"SELL order failed for {ticker} - broker rejected. Retrying next cycle.")

    return state


# ── Main loop ────────────────────────────────────────────────

def run():
    run.market_was_closed = False
    
    # Pre-load state to fetch tickers
    initial_state = load_state()
    ticker_list = initial_state.get('tickers', ["TATASTEEL.NS", "RELIANCE.NS", "INFY.NS", "ITC.NS", "TCS.NS"])
    
    log.info("=" * 54)
    log.info("  AUTONOMOUS PORTFOLIO TRADING ENGINE  -  ONLINE")
    log.info(f"  TICKERS: {', '.join(ticker_list)}")
    log.info(f"  POOL   : Rs.{get_capital():.2f}")
    log.info("=" * 54)

    last_signal_check = 0   # unix timestamp of last entry-signal attempt

    while True:
        try:
            state   = load_state()
            capital = get_capital()
            dry_run = state.get('dry_run', True)
            tickers = state.get('tickers', ["TATASTEEL.NS", "RELIANCE.NS", "INFY.NS", "ITC.NS", "TCS.NS"])

            # ── 1. Market hours guard ──────────────────────────
            if not is_market_open():
                if not run.market_was_closed:
                    log.info("Market is currently closed - standby mode activated.")
                    run.market_was_closed = True
                time.sleep(60)
                continue
            else:
                if run.market_was_closed:
                    log.info("Market has opened! Initiating scanners and actuators.")
                    run.market_was_closed = False

            # On-the-fly broker connection for dynamic live trading toggles with self-healing auto-recovery
            effective_dry_run = dry_run
            if not dry_run:
                if initialize_broker():
                    log.info("Dhan API credentials validated. LIVE execution active.")
                else:
                    log.warning("Dhan connection failed or token expired. Safely falling back to temporary DEMO mode for this cycle.")
                    effective_dry_run = True

            # ── 2. Daily loss circuit breaker ──────────────────
            if daily_limit_hit(state, capital):
                log.warning(
                    f"Daily loss limit reached (Rs.{state['daily_pnl']:.2f}). "
                    f"No new trades until tomorrow. Liquidating active positions..."
                )
                for ticker, pos in list(state.get('positions', {}).items()):
                    if pos.get('holding_position', False):
                        try:
                            df = fetch_and_prepare_data(ticker=ticker)
                            price = df['Close'].iloc[-1]
                        except Exception:
                            price = pos['entry_price']
                        state = execute_sell(state, ticker, price, reason="DAILY_LIMIT", effective_dry_run=effective_dry_run)
                time.sleep(300)
                continue

            # ── 3. Mandatory square-off at 15:15 ──────────────
            if is_square_off_time():
                has_active = False
                for ticker, pos in list(state.get('positions', {}).items()):
                    if pos.get('holding_position', False):
                        has_active = True
                        log.warning(f"15:15 square-off — closing position for {ticker} before market end.")
                        try:
                            df = fetch_and_prepare_data(ticker=ticker)
                            current_price = df['Close'].iloc[-1]
                        except Exception:
                            current_price = pos['entry_price']
                        state = execute_sell(state, ticker, current_price, reason="SQUARE_OFF", effective_dry_run=effective_dry_run)
                if has_active:
                    time.sleep(60)
                    continue

            # ── 4. Active position management (every 60s) ─────
            # Manage all active positions
            active_tickers = []
            for ticker, pos in list(state.get('positions', {}).items()):
                if pos.get('holding_position', False):
                    active_tickers.append(ticker)
                    
            if active_tickers:
                for ticker in active_tickers:
                    pos = state['positions'][ticker]
                    try:
                        df = fetch_and_prepare_data(ticker=ticker)
                        current_price = df['Close'].iloc[-1]
                    except Exception as e:
                        log.error(f"Failed to fetch data for checking stops on {ticker}: {e}")
                        continue
                        
                    sl = pos['active_stop_loss']
                    tp = pos['active_take_profit']
                    pnl_now = (current_price - pos['entry_price']) * pos['current_shares']
                    log.info(
                        f"HOLDING {ticker} | {pos['current_shares']} shares | "
                        f"Rs.{pos['entry_price']:.2f} -> Rs.{current_price:.2f} | "
                        f"PnL: Rs.{pnl_now:+.2f} | SL Rs.{sl:.2f} | TP Rs.{tp:.2f}"
                    )

                    if current_price <= sl:
                        log.warning(f"STOP-LOSS triggered for {ticker}.")
                        state = execute_sell(state, ticker, current_price, reason="STOP_LOSS", effective_dry_run=effective_dry_run)
                    elif current_price >= tp:
                        log.info(f"TAKE-PROFIT target hit for {ticker}.")
                        state = execute_sell(state, ticker, current_price, reason="TAKE_PROFIT", effective_dry_run=effective_dry_run)

            # ── 5. Entry signal scan (every 15 min) ───────────
            now = time.time()
            if now - last_signal_check >= SIGNAL_INTERVAL_SEC:
                last_signal_check = now
                
                tickers_to_scan = [t for t in tickers if not state.get('positions', {}).get(t, {}).get('holding_position', False)]
                
                if tickers_to_scan:
                    log.info(f"AI entry scan initiated for: {', '.join(tickers_to_scan)}")
                    
                    for ticker in tickers_to_scan:
                        free_cash = calculate_free_cash(state, capital)
                        if free_cash < 10.0: # arbitrary minimum
                            log.warning(f"Available Free Cash (Rs.{free_cash:.2f}) is too low to initiate new trades.")
                            break
                            
                        try:
                            df = fetch_and_prepare_data(ticker=ticker)
                            current_price = df['Close'].iloc[-1]
                            current_atr   = df['ATR'].iloc[-1]
                            
                            forecast      = get_live_prediction(df, ticker)
                            profit_margin = (forecast - current_price) / current_price

                            log.info(
                                f"AI scan for {ticker} | Rs.{current_price:.2f} -> forecast Rs.{forecast:.2f} | "
                                f"edge {profit_margin*100:+.2f}%"
                            )

                            if profit_margin < MIN_PROFIT_MARGIN:
                                log.info(f"No signal for {ticker} — edge insufficient.")
                                continue

                            # Calculate stops first so we can do risk-based sizing
                            sl, tp = calculate_dynamic_stops(current_price, current_atr, forecast)
                            shares, cost = calculate_position_size(free_cash, current_price, sl)
                            rr = get_risk_reward_ratio(current_price, sl, tp)

                            if shares < 1:
                                log.warning(
                                    f"Free cash Rs.{free_cash:.2f} too small to buy 1 share of {ticker} at Rs.{current_price:.2f}."
                                )
                                continue

                            if rr < MIN_RISK_REWARD:
                                log.info(f"No signal for {ticker} — R:R {rr} below minimum {MIN_RISK_REWARD}.")
                                continue

                            log.info(
                                f"BUY signal for {ticker} | {shares} shares @ Rs.{current_price:.2f} | "
                                f"Cost Rs.{cost:.2f} | SL Rs.{sl:.2f} | TP Rs.{tp:.2f} | R:R {rr}"
                            )

                            success = True
                            if not effective_dry_run:
                                success = execute_market_order(ticker, shares, "BUY")
                            else:
                                log.info(f"DEMO MODE - order for {ticker} simulated.")

                            if success:
                                if 'positions' not in state:
                                    state['positions'] = {}
                                state['positions'][ticker] = {
                                    'holding_position': True,
                                    'current_shares': shares,
                                    'entry_price': current_price,
                                    'active_stop_loss': sl,
                                    'active_take_profit': tp
                                }
                                save_state(state)
                                log_trade_csv("BUY", ticker, current_price, shares)
                                log.info(f"BUY recorded for {ticker}. Added to active portfolio.")
                                
                        except Exception as e:
                            log.error(f"AI inference failure for {ticker}: {e}")

            time.sleep(STOP_CHECK_INTERVAL_SEC)

        except KeyboardInterrupt:
            log.info("Manual shutdown. Goodbye.")
            sys.exit(0)
        except Exception as e:
            log.error(f"Unexpected error: {e}. Recovering in 60s.")
            time.sleep(60)


if __name__ == "__main__":
    run()
