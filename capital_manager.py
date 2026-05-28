import json
import os
from datetime import datetime, timezone, timedelta

def get_ist_now():
    return datetime.now(timezone(timedelta(hours=5, minutes=30)))

POOL_FILE = 'pool.json'
STARTING_CAPITAL = 1000.0


def _load_pool():
    if not os.path.exists(POOL_FILE):
        data = {
            'capital': STARTING_CAPITAL,
            'peak_capital': STARTING_CAPITAL,
            'total_trades': 0,
            'winning_trades': 0,
            'history': []
        }
        _save_pool(data)
        return data
    with open(POOL_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def _save_pool(data):
    with open(POOL_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def get_capital():
    """Returns current tradeable capital from the pool."""
    return _load_pool()['capital']


def record_trade_result(action, price, shares, pnl):
    """
    Updates the capital pool after a completed trade.
    Profits grow the pool; losses shrink it.
    Returns the new capital balance.
    """
    data = _load_pool()
    data['capital'] = round(data['capital'] + pnl, 2)
    data['total_trades'] += 1
    if pnl > 0:
        data['winning_trades'] += 1
    if data['capital'] > data['peak_capital']:
        data['peak_capital'] = data['capital']

    data['history'].append({
        'date': get_ist_now().strftime('%Y-%m-%d %H:%M:%S'),
        'action': action,
        'price': round(price, 2),
        'shares': shares,
        'pnl': round(pnl, 2),
        'capital_after': data['capital']
    })
    _save_pool(data)
    return data['capital']


def get_pool_summary():
    """Returns a dict of key pool statistics for the dashboard."""
    data = _load_pool()
    total_trades = data['total_trades']
    win_rate = (data['winning_trades'] / total_trades * 100) if total_trades > 0 else 0.0
    drawdown = ((data['peak_capital'] - data['capital']) / data['peak_capital'] * 100) if data['peak_capital'] > 0 else 0.0

    return {
        'capital': data['capital'],
        'starting_capital': STARTING_CAPITAL,
        'peak_capital': data['peak_capital'],
        'total_pnl': round(data['capital'] - STARTING_CAPITAL, 2),
        'total_pnl_pct': round((data['capital'] - STARTING_CAPITAL) / STARTING_CAPITAL * 100, 2),
        'total_trades': total_trades,
        'winning_trades': data['winning_trades'],
        'win_rate': round(win_rate, 1),
        'max_drawdown_pct': round(drawdown, 1),
        'history': data['history']
    }
