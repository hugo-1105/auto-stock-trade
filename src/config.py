from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field


class RiskConfig(BaseModel):
    risk_per_trade: float = Field(gt=0, lt=1)
    max_total_risk: float = Field(gt=0, lt=1)
    max_positions: int = Field(ge=1)
    daily_loss_limit: float = Field(gt=0, lt=1)
    max_single_alloc: float = Field(gt=0, lt=1)


class ExecutionConfig(BaseModel):
    order_type_entry: Literal["LMT", "MKT"] = "LMT"
    cancel_stale_orders_minutes: int = 30
    slippage_bps: int = 5


class TradeWindow(BaseModel):
    start: str
    end: str


class SessionConfig(BaseModel):
    exchange: str = "XNYS"
    market_timezone: str = "America/New_York"
    local_timezone: str = "Europe/London"
    trade_window_ny: TradeWindow


class StrategyConfig(BaseModel):
    timeframe: str = "1D"
    rebalance: Literal["daily", "weekly"] = "weekly"
    ma_fast: int = 100
    ma_slow: int = 200
    lookback_days: int = 260


class UniverseConfig(BaseModel):
    symbols: list[str]


class Settings(BaseModel):
    mode: Literal["paper", "live"] = "paper"
    base_currency: str = "GBP"
    account_id: str
    risk: RiskConfig
    execution: ExecutionConfig
    session: SessionConfig
    strategy: StrategyConfig
    universe: UniverseConfig


def load_settings(path: str | Path = "config/settings.yaml") -> Settings:
    with Path(path).open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return Settings.model_validate(raw)
