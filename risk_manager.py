import math


# Max percentage of capital to risk per trade (stop-loss distance)
MAX_RISK_PER_TRADE_PCT = 0.02   # Risk at most 2% of capital on any single trade
TRANSACTION_BUFFER_PCT = 0.005  # 0.5% buffer for brokerage, STT, and taxes (optimized for INR intraday)


def calculate_position_size(capital, current_price, stop_loss_price=None):
    """
    Calculates the optimal number of shares to buy.

    If stop_loss_price is provided, sizes the position so that hitting the
    stop-loss costs at most MAX_RISK_PER_TRADE_PCT of capital.

    Otherwise, falls back to buying as many shares as the capital allows
    (minus transaction buffer).

    Returns: (shares, actual_cost)
    """
    usable_capital = capital * (1 - TRANSACTION_BUFFER_PCT)

    if stop_loss_price and stop_loss_price < current_price:
        # Risk-based sizing: risk = (entry - stop) * shares <= max_risk
        max_risk_rupees = capital * MAX_RISK_PER_TRADE_PCT
        risk_per_share = current_price - stop_loss_price
        
        # Zero-division guard
        if risk_per_share <= 0:
            risk_based_shares = math.floor(usable_capital / current_price)
        else:
            risk_based_shares = math.floor(max_risk_rupees / risk_per_share)

        # Also cap by what capital can actually afford
        capital_based_shares = math.floor(usable_capital / current_price)

        shares = min(risk_based_shares, capital_based_shares)
    else:
        shares = math.floor(usable_capital / current_price)

    shares = max(shares, 0)
    actual_cost = shares * current_price
    return shares, round(actual_cost, 2)


def calculate_dynamic_stops(entry_price, current_atr, forecast_price):
    """
    Calculates Stop-Loss and Take-Profit using ATR-based volatility.

    Stop-Loss : 1.5x ATR below entry (gives trade room to breathe)
    Take-Profit: AI forecast price, but at minimum 1x ATR above entry
                 (ensures reward >= risk)
    """
    stop_loss = entry_price - (1.5 * current_atr)
    minimum_target = entry_price + current_atr
    take_profit = max(forecast_price, minimum_target)

    return round(stop_loss, 2), round(take_profit, 2)


def get_risk_reward_ratio(entry, stop_loss, take_profit):
    """Returns the R:R ratio for a planned trade. Aim for >= 1.5."""
    risk = entry - stop_loss
    reward = take_profit - entry
    if risk <= 0:
        return 0
    return round(reward / risk, 2)


if __name__ == "__main__":
    capital = 1000.0
    price = 184.50
    atr = 1.01
    forecast = 186.20

    sl, tp = calculate_dynamic_stops(price, atr, forecast)
    shares, cost = calculate_position_size(capital, price, sl)
    rr = get_risk_reward_ratio(price, sl, tp)

    print(f"Capital      : Rs.{capital}")
    print(f"Current Price: Rs.{price:.2f}")
    print(f"Stop-Loss    : Rs.{sl:.2f}  ({((price-sl)/price*100):.2f}% below entry)")
    print(f"Take-Profit  : Rs.{tp:.2f}  ({((tp-price)/price*100):.2f}% above entry)")
    print(f"Shares       : {shares}  |  Cost: Rs.{cost:.2f}")
    print(f"Max Risk     : Rs.{(price - sl) * shares:.2f}  |  R:R = {rr}")

