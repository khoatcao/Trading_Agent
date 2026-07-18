from config import (
    MAX_LEVERAGE, MARGIN_MODE, RISK_PER_TRADE,
    MAX_EXPOSURE, MIN_LIQ_DISTANCE, MAX_DAILY_DRAWDOWN,
    STOP_LOSS_PCT, TAKE_PROFIT_PCT, MIN_NOTIONAL_USDT
)


MAINTENANCE_MARGIN_RATE = 0.005  # 0.5% for Bybit linear perpetuals


def calculate_liquidation_price(entry: float, leverage: int, direction: str) -> float:
    if direction == "LONG":
        return round(entry * (1 - 1 / leverage + MAINTENANCE_MARGIN_RATE), 4)
    else:
        return round(entry * (1 + 1 / leverage - MAINTENANCE_MARGIN_RATE), 4)


def calculate_position_size(balance: float, entry: float, stop_loss: float, risk_pct: float = RISK_PER_TRADE) -> float:
    risk_amount = balance * risk_pct
    distance = abs(entry - stop_loss)
    if distance == 0:
        return 0.0

    size_by_risk = risk_amount / distance
    exposure_cap = (balance * MAX_EXPOSURE) / entry
    position_size = min(size_by_risk, exposure_cap)

    return round(position_size, 6)


def calculate_stop_loss(entry: float, direction: str, pct: float = STOP_LOSS_PCT) -> float:
    if direction == "LONG":
        return round(entry * (1 - pct), 4)
    else:
        return round(entry * (1 + pct), 4)


def calculate_take_profit(entry: float, direction: str, pct: float = TAKE_PROFIT_PCT) -> float:
    if direction == "LONG":
        return round(entry * (1 + pct), 4)
    else:
        return round(entry * (1 - pct), 4)


def liq_distance_pct(entry: float, liq_price: float) -> float:
    return round(abs(entry - liq_price) / entry, 4)


def check_exposure(position_value: float, balance: float) -> bool:
    return (position_value / balance) <= MAX_EXPOSURE


def check_daily_drawdown(starting_balance: float, current_balance: float) -> bool:
    drawdown = (starting_balance - current_balance) / starting_balance
    return drawdown < MAX_DAILY_DRAWDOWN


def validate_risk(entry: float, leverage: int, direction: str,
                  position_size: float, balance: float,
                  starting_balance: float, current_balance: float) -> dict:
    liq_price = calculate_liquidation_price(entry, leverage, direction)
    liq_dist = liq_distance_pct(entry, liq_price)
    position_value = position_size * entry

    checks = {
        "liq_distance_ok": liq_dist >= MIN_LIQ_DISTANCE,
        "leverage_ok": leverage <= MAX_LEVERAGE,
        "exposure_ok": check_exposure(position_value, balance),
        "drawdown_ok": check_daily_drawdown(starting_balance, current_balance),
        "notional_ok": position_value >= MIN_NOTIONAL_USDT,
    }
    approved = all(checks.values())

    return {
        "approved": approved,
        "checks": checks,
        "liq_price": liq_price,
        "liq_distance_pct": liq_dist,
        "position_value": round(position_value, 4),
    }
