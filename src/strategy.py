from __future__ import annotations

import pandas as pd


def trend_signal(closes: pd.Series, ma_fast: int, ma_slow: int) -> int:
    if closes.size < ma_slow:
        return 0
    ma_fast_v = closes.rolling(ma_fast).mean().iloc[-1]
    ma_slow_v = closes.rolling(ma_slow).mean().iloc[-1]
    px = closes.iloc[-1]
    if px > ma_fast_v and px > ma_slow_v:
        return 1
    return 0
