from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone

from dotenv import load_dotenv
from ib_insync import IB, Stock, util


@dataclass
class AccountSnapshot:
    equity: float
    available_funds: float
    currency: str
    timestamp_utc: datetime


class IBKRBroker:
    def __init__(self) -> None:
        load_dotenv()
        self.host = os.getenv("IB_HOST", "127.0.0.1")
        self.port = int(os.getenv("IB_PORT", "7497"))
        self.client_id = int(os.getenv("IB_CLIENT_ID", "10"))
        self.ib = IB()

    def connect(self) -> None:
        self.ib.connect(self.host, self.port, clientId=self.client_id, readonly=False)

    def disconnect(self) -> None:
        if self.ib.isConnected():
            self.ib.disconnect()

    def get_account_snapshot(self, account_id: str, currency: str = "GBP") -> AccountSnapshot:
        summary = self.ib.accountSummary(account=account_id)
        summary_map = {(row.tag, row.currency): row.value for row in summary}
        equity = float(summary_map.get(("NetLiquidation", currency), 0.0))
        available_funds = float(summary_map.get(("AvailableFunds", currency), 0.0))
        return AccountSnapshot(
            equity=equity,
            available_funds=available_funds,
            currency=currency,
            timestamp_utc=datetime.now(timezone.utc),
        )

    def get_daily_closes(self, symbol: str, lookback_days: int):
        contract = Stock(symbol, "SMART", "USD")
        self.ib.qualifyContracts(contract)
        bars = self.ib.reqHistoricalData(
            contract,
            endDateTime="",
            durationStr=f"{lookback_days} D",
            barSizeSetting="1 day",
            whatToShow="TRADES",
            useRTH=True,
            formatDate=1,
        )
        df = util.df(bars)
        if df.empty:
            return df
        return df[["date", "close"]]
