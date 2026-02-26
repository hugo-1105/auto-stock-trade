# Practical Setup Guide: Automated US Stock Trading with Interactive Brokers (UK, £1,000, Medium Risk, Python)

> **Audience:** UK-based retail trader building a small but production-oriented automated system.
>
> **Goal:** Preserve capital, keep turnover low, run clean automation, handle UK/US timezones correctly, and size positions realistically with a **£1,000** account.

---

## 1) Core assumptions and constraints

With £1,000, your edge is process quality, not complexity:

- **Capital preservation first:** avoid concentrated bets and hard-fail behavior.
- **Low turnover:** commissions, spread, and slippage can dominate small accounts.
- **US stocks via IBKR from UK:** account base currency can stay GBP, but execution is in USD.
- **Automation should degrade safely:** if market data or broker API fails, do nothing.
- **Medium risk target:** drawdown-aware, diversified, and capped position size.

A practical target at this size is to:

- trade **high-liquidity US ETFs/stocks** only,
- hold for **days to weeks** (not intraday scalping),
- run **1–3 positions max**,
- risk **0.5%–1.0%** of equity per trade.

---

## 2) Recommended architecture (simple, robust)

Use this minimal production layout:

```text
trading-bot/
  config/
    settings.yaml
  data/
    universe.csv
  logs/
  state/
    positions.json
    last_signals.json
  src/
    broker_ibkr.py
    strategy.py
    risk.py
    execution.py
    scheduler.py
    main.py
  requirements.txt
  .env
```

### Responsibilities

- `broker_ibkr.py`: connect/disconnect, account summary, positions, place/cancel orders.
- `strategy.py`: signal generation only (no order placement).
- `risk.py`: position sizing, risk checks, daily loss limits.
- `execution.py`: convert approved signals into broker orders.
- `scheduler.py`: timezone-safe session scheduling.
- `main.py`: orchestrator with structured logging and fail-safe shutdown.

This separation keeps automation clean and easier to debug.

---

## 3) Broker setup (Interactive Brokers)

## 3.1 Account and permissions

1. Open IBKR account (UK individual account).
2. Enable permissions for **US Stocks/ETFs** and live market data (or plan delayed-data workflow).
3. Configure base currency (GBP is fine), and understand FX conversion to USD for purchases.
4. Enable two-factor auth and review API access settings.

## 3.2 TWS or IB Gateway

For headless automation, **IB Gateway** is usually better than TWS.

- Install IB Gateway on your VPS or dedicated machine.
- In API settings, enable socket clients.
- Restrict trusted IPs where possible.
- Disable manual popups that block session startup.

> For small accounts, stability > speed. A single reliable process is better than a distributed microservice setup.

---

## 4) Python stack and environment

Use Python 3.11+ and `ib_insync` (cleaner than raw IB API for most workflows).

### `requirements.txt`

```txt
ib_insync==0.9.86
pandas==2.2.2
numpy==1.26.4
pydantic==2.8.2
python-dotenv==1.0.1
PyYAML==6.0.2
pytz==2024.1
exchange-calendars==4.5.5
structlog==24.2.0
```

### Environment bootstrap

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

Create `.env`:

```env
IB_HOST=127.0.0.1
IB_PORT=7497
IB_CLIENT_ID=10
ACCOUNT_ID=UXXXXXXX
```

Use separate `CLIENT_ID`s for paper and live systems.

---

## 5) Timezone and market-session handling (critical)

You are in UK timezone; market is US timezone. DST changes are not synchronized between UK and US every week of the year.

**Do not hardcode clock times.** Use exchange calendars.

### Safe practice

- Use `America/New_York` for market session logic.
- Use `Europe/London` only for local logs/display.
- Gate trading by `XNYS` open sessions from `exchange-calendars`.
- Submit new entries only in liquid windows (e.g., 10:00–15:30 New York time).

Pseudo-flow:

1. `now_utc = datetime.now(timezone.utc)`
2. Convert to NY timezone.
3. Ask exchange calendar if market is open.
4. If closed: risk checks only, no new orders.
5. If open and in allowed window: evaluate strategy and place orders.

This avoids DST bugs that often break UK-operated US bots.

---

## 6) Universe selection for £1,000 and low turnover

Prefer liquid, lower-spread instruments:

- Core ETFs: `SPY`, `IVV`, `VOO`, `QQQ`, `VTI` (choose 1–2, not all).
- Defensive alternative: `BIL`, `SHV` (parking/cash proxy behavior).
- Optional large-cap stocks only if highly liquid (`AAPL`, `MSFT`, etc.).

Avoid illiquid small caps and frequent rotations.

Keep universe to **5–15 symbols max**.

---

## 7) Strategy style (medium risk, capital preservation)

For this account size, use a **low-turnover trend filter** strategy:

- Daily bars.
- Entry: price above 100/200-day moving average and positive medium-term momentum.
- Exit: close below trend filter or volatility stop breach.
- Rebalance at most **weekly**.

Why this works at £1k:

- Fewer trades → lower fee drag.
- Captures broad moves, avoids overfitting minute-level noise.
- Easy to monitor and stress-test.

---

## 8) Risk framework and realistic position sizing

## 8.1 Risk limits

Use hard limits in code:

- Max portfolio risk per trade: **0.75% equity** (medium risk baseline).
- Max total at-risk exposure: **2.0% equity**.
- Max open positions: **3**.
- Daily loss stop: **1.5% equity** (if breached, no new entries that day).
- Single-name cap: **35%** of equity.

With £1,000:

- 0.75% risk per trade ≈ **£7.50**.
- If stop distance is $2/share and GBPUSD≈1.27:
  - risk/share ≈ £1.57,
  - shares ≈ floor(7.50 / 1.57) = 4 shares.

This illustrates why high-priced stocks can force tiny positions and why ETFs/fractionals (if available) help.

## 8.2 Position size formula

```text
risk_budget_gbp = equity_gbp * risk_per_trade
risk_per_share_gbp = abs(entry_usd - stop_usd) / fx_gbpusd
shares = floor(risk_budget_gbp / risk_per_share_gbp)

notional_cap_shares = floor((equity_gbp * max_alloc_pct * fx_gbpusd) / entry_usd)
final_shares = min(shares, notional_cap_shares)
```

Then enforce broker minimums and liquidity filters.

---

## 9) Execution rules to reduce slippage and errors

- Use **limit orders** for entries; avoid market orders in thin names.
- For exits on hard risk events, allow marketable limits.
- Cancel stale orders before new cycle.
- Never submit duplicate orders (idempotency key per symbol/date/signal).
- Add a `kill_switch` flag in config to block all new orders instantly.

Basic safeguards:

- If IB connection drops: flattening policy should be explicit (usually *do not panic-sell*; alert and retry).
- If data missing/outlier: skip symbol.
- If clock/calendar uncertain: skip trading cycle.

---

## 10) Monitoring, logging, and alerting

Minimum production logging per cycle:

- timestamp (UTC + local display)
- market session state
- account equity/cash
- signals generated and filtered reason
- risk checks (pass/fail)
- orders submitted/filled/rejected
- exceptions with stack trace

Send alerts (Telegram/email/Slack) for:

- connection loss,
- order rejection,
- daily loss limit hit,
- strategy process crash/restart.

---

## 11) Backtesting and go-live process

1. **Backtest** on daily data including fees/slippage assumptions.
2. **Paper trade** with IBKR for at least 4–8 weeks.
3. Compare expected vs realized slippage/fill quality.
4. Deploy live with reduced risk (`0.5%` per trade initially).
5. Scale to `0.75%` only after stable operation.

Never promote to live if paper trading has unresolved operational failures.

---

## 12) Deployment pattern (UK-friendly)

Recommended:

- Linux VPS (or always-on mini PC) in stable region.
- Run IB Gateway + bot under `systemd`.
- Auto-restart on crash.
- Daily log rotation.
- NTP time sync mandatory.

Example services:

- `ibgateway.service`
- `trading-bot.service`

Start bot after gateway health check passes.

---

## 13) Example configuration (`config/settings.yaml`)

```yaml
mode: paper  # paper | live
base_currency: GBP
risk:
  risk_per_trade: 0.0075
  max_total_risk: 0.02
  max_positions: 3
  daily_loss_limit: 0.015
  max_single_alloc: 0.35
execution:
  order_type_entry: LMT
  use_fractional_if_supported: true
  cancel_stale_orders_minutes: 30
session:
  exchange: XNYS
  trade_window_ny:
    start: "10:00"
    end: "15:30"
strategy:
  timeframe: 1D
  rebalance: weekly
  ma_fast: 100
  ma_slow: 200
universe:
  symbols: ["SPY", "QQQ", "VTI", "AAPL", "MSFT"]
```

---

## 14) Minimal operational checklist

Daily:

- [ ] IB Gateway connected
- [ ] Strategy process healthy
- [ ] Clock sync OK
- [ ] No API permission errors
- [ ] Risk limits loaded correctly

Weekly:

- [ ] Review fills and slippage
- [ ] Review turnover and fee drag
- [ ] Review max drawdown and exposure
- [ ] Confirm no silent exceptions in logs

Monthly:

- [ ] Revalidate universe liquidity
- [ ] Reconfirm strategy behavior vs backtest expectations
- [ ] Reduce complexity where failures occurred

---

## 15) Common failure modes and prevention

- **DST mismatch (UK vs US):** use exchange calendar, never static schedule.
- **Overtrading a small account:** enforce weekly rebalance and trade cooldown.
- **Ignoring FX effects:** include GBPUSD in sizing and PnL attribution.
- **Single-process fragility:** use supervised services + health checks.
- **Strategy drift:** lock config and version every change.

---

## 16) Final practical defaults for your brief

Given UK location, £1,000 capital, and medium risk:

- Start in **paper mode**, then live with **0.5% risk/trade** for first month.
- Trade **1–2 liquid ETFs** first (e.g., SPY/QQQ) before adding single stocks.
- Rebalance **weekly** only.
- Keep **max 2 live positions initially**.
- Use strict loss limits and skip trading whenever data/time checks fail.

This approach is intentionally conservative and production-oriented: it prioritizes staying in the game and avoiding operational blowups over chasing short-term returns.

---

## 17) Starter implementation included in this repo

This repository now includes a minimal IBKR integration scaffold under `src/`:

- `src/config.py` for typed YAML config loading
- `src/broker_ibkr.py` for IB connection, account snapshot, and historical bars
- `src/strategy.py` for a low-turnover trend signal
- `src/risk.py` for risk-budget-based position sizing
- `src/execution.py` for market/limit order construction
- `src/scheduler.py` for exchange-calendar-aware trade window gating
- `src/main.py` as a single-cycle orchestrator

### Quick start

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python src/main.py
```

> Run in paper mode first and verify IB Gateway/TWS connectivity before any live deployment.
