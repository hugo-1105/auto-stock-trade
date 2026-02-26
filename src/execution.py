from __future__ import annotations

from ib_insync import LimitOrder, MarketOrder, Stock


def build_entry_order(symbol: str, quantity: int, side: str, order_type: str, limit_price: float | None):
    contract = Stock(symbol, "SMART", "USD")
    if order_type == "MKT":
        order = MarketOrder(side, quantity)
    else:
        if limit_price is None:
            raise ValueError("limit_price is required for LMT orders")
        order = LimitOrder(side, quantity, lmtPrice=limit_price)
    return contract, order
