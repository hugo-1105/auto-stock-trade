from __future__ import annotations

from datetime import datetime, timezone

import exchange_calendars as xcals
import pytz


def is_trade_window_open(exchange: str, market_tz: str, start_hhmm: str, end_hhmm: str) -> bool:
    cal = xcals.get_calendar(exchange)
    now_utc = datetime.now(timezone.utc)
    now_ny = now_utc.astimezone(pytz.timezone(market_tz))

    if not cal.is_session(now_ny.date()):
        return False

    sh, sm = map(int, start_hhmm.split(":"))
    eh, em = map(int, end_hhmm.split(":"))
    now_minutes = now_ny.hour * 60 + now_ny.minute
    start_minutes = sh * 60 + sm
    end_minutes = eh * 60 + em
    return start_minutes <= now_minutes <= end_minutes
