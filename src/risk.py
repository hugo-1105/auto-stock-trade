from __future__ import annotations

import math


def size_position_shares(
    equity_gbp: float,
    risk_per_trade: float,
    entry_usd: float,
    stop_usd: float,
    fx_gbpusd: float,
    max_single_alloc: float,
) -> int:
    risk_budget_gbp = equity_gbp * risk_per_trade
    risk_per_share_gbp = abs(entry_usd - stop_usd) / fx_gbpusd
    if risk_per_share_gbp <= 0:
        return 0

    risk_shares = math.floor(risk_budget_gbp / risk_per_share_gbp)
    notional_cap = math.floor((equity_gbp * max_single_alloc * fx_gbpusd) / entry_usd)
    return max(0, min(risk_shares, notional_cap))
