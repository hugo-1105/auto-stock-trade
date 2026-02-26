from __future__ import annotations

import signal
import sys

from broker_ibkr import IBKRBroker
from config import load_settings
from execution import build_entry_order
from logger import configure_logging, get_logger
from risk import size_position_shares
from scheduler import is_trade_window_open
from strategy import trend_signal


def run_once() -> None:
    configure_logging()
    log = get_logger("trading_bot")
    settings = load_settings()

    broker = IBKRBroker()
    broker.connect()
    try:
        snap = broker.get_account_snapshot(settings.account_id, settings.base_currency)
        log.info("account_snapshot", equity=snap.equity, available=snap.available_funds, ccy=snap.currency)

        open_window = is_trade_window_open(
            settings.session.exchange,
            settings.session.market_timezone,
            settings.session.trade_window_ny.start,
            settings.session.trade_window_ny.end,
        )
        if not open_window:
            log.info("market_closed_or_outside_window")
            return

        for symbol in settings.universe.symbols:
            df = broker.get_daily_closes(symbol, settings.strategy.lookback_days)
            if df.empty:
                log.warning("no_data", symbol=symbol)
                continue
            close_series = df["close"]
            signal_val = trend_signal(close_series, settings.strategy.ma_fast, settings.strategy.ma_slow)
            if signal_val != 1:
                continue

            entry = float(close_series.iloc[-1])
            stop = entry * 0.95
            shares = size_position_shares(
                equity_gbp=snap.equity,
                risk_per_trade=settings.risk.risk_per_trade,
                entry_usd=entry,
                stop_usd=stop,
                fx_gbpusd=1.27,
                max_single_alloc=settings.risk.max_single_alloc,
            )
            if shares <= 0:
                log.info("skip_size_zero", symbol=symbol)
                continue

            contract, order = build_entry_order(
                symbol=symbol,
                quantity=shares,
                side="BUY",
                order_type=settings.execution.order_type_entry,
                limit_price=entry if settings.execution.order_type_entry == "LMT" else None,
            )
            trade = broker.ib.placeOrder(contract, order)
            log.info("order_submitted", symbol=symbol, shares=shares, order_id=trade.order.orderId)
    finally:
        broker.disconnect()


def _handle_shutdown(signum, frame):
    raise SystemExit(f"Received signal {signum}")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, _handle_shutdown)
    signal.signal(signal.SIGTERM, _handle_shutdown)
    try:
        run_once()
    except Exception as exc:
        print(f"fatal_error: {exc}", file=sys.stderr)
        raise
