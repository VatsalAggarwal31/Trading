import json
import os
from datetime import datetime, timezone, timedelta

STATE_FILE = 'bot_state.json'


def get_ist_date():
    return datetime.now(timezone(timedelta(hours=5, minutes=30))).date()


def _default_state():
    return {
        'positions': {},  # Mapped ticker -> position details
        'tickers': ["TATASTEEL.NS", "ITC.NS", "WIPRO.NS", "ONGC.NS", "SBIN.NS"],
        'daily_pnl': 0.0,
        'daily_date': str(get_ist_date()),
        'trade_count_today': 0,
        'dry_run': True
    }


def load_state():
    """
    Loads the persisted bot state from disk.
    Automatically resets daily stats if it's a new trading day.
    Performs auto-migration if upgrading from legacy single-stock bot state.
    """
    if not os.path.exists(STATE_FILE):
        state = _default_state()
        save_state(state)
        return state

    with open(STATE_FILE, 'r', encoding='utf-8') as f:
        state = json.load(f)

    # Legacy Auto-Migration: Convert single-position keys to multi-position dictionary
    needs_save = False
    if 'positions' not in state:
        state['positions'] = {}
        if state.get('holding_position', False):
            # Migrate the active TATASTEEL position
            state['positions']["TATASTEEL.NS"] = {
                'holding_position': True,
                'current_shares': state.get('current_shares', 0),
                'entry_price': state.get('entry_price', 0.0),
                'active_stop_loss': state.get('active_stop_loss', 0.0),
                'active_take_profit': state.get('active_take_profit', 0.0)
            }
        # Clean up legacy root-level keys
        for key in ['holding_position', 'current_shares', 'entry_price', 'active_stop_loss', 'active_take_profit']:
            state.pop(key, None)
        needs_save = True

    if 'tickers' not in state:
        state['tickers'] = ["TATASTEEL.NS", "ITC.NS", "WIPRO.NS", "ONGC.NS", "SBIN.NS"]
        needs_save = True
    elif state.get('tickers') == ["TATASTEEL.NS", "RELIANCE.NS", "INFY.NS", "ITC.NS", "TCS.NS"]:
        # Auto-upgrade to under-₹1000 scan pool
        state['tickers'] = ["TATASTEEL.NS", "ITC.NS", "WIPRO.NS", "ONGC.NS", "SBIN.NS"]
        needs_save = True

    # New day — reset daily counters but keep position intact
    current_ist_date = str(get_ist_date())
    if state.get('daily_date') != current_ist_date:
        state['daily_pnl'] = 0.0
        state['daily_date'] = current_ist_date
        state['trade_count_today'] = 0
        needs_save = True

    if needs_save:
        save_state(state)

    return state


def save_state(state):
    """Writes the current state to disk atomically."""
    tmp = STATE_FILE + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, STATE_FILE)


def clear_position(state, ticker):
    """Resets position fields for a specific ticker after a completed trade."""
    if 'positions' in state and ticker in state['positions']:
        state['positions'][ticker] = {
            'holding_position': False,
            'current_shares': 0,
            'entry_price': 0.0,
            'active_stop_loss': 0.0,
            'active_take_profit': 0.0
        }
    return state

