"""Live/scheduler mode — startup backfill + live polling loop during market hours."""

import logging
import sys
import time
from datetime import datetime, timedelta, timezone

import MetaTrader5 as mt5

# Re-use conversion helpers from the existing assistance module.
from quantwinmt5feeder.assistance.ochl import SP_TZ, convert_bar_to_dict

from quantwinmt5feeder.auth import TokenManager
from quantwinmt5feeder.client import QuantWinClient
from quantwinmt5feeder.config import (
    BACKFILL_HOURS,
    BATCH_SIZE,
    MARKET_CLOSE_HOUR,
    MARKET_CLOSE_MINUTE,
    MARKET_OPEN_HOUR,
    MARKET_OPEN_MINUTE,
    POLL_INTERVAL_SECONDS,
    SOURCE_ID,
    TIMEFRAME_LABEL,
)
from quantwinmt5feeder.symbol import detect_active_win_symbol, ensure_mt5_initialized

logger = logging.getLogger(__name__)

# ─── helpers ────────────────────────────────────────────────────────────────


def _is_market_hours(now_sp: datetime) -> bool:
    """Return True if *now_sp* falls within B3 regular trading hours (Mon–Fri)."""
    if now_sp.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    market_open = now_sp.replace(
        hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MINUTE, second=0, microsecond=0
    )
    market_close = now_sp.replace(
        hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MINUTE, second=0, microsecond=0
    )
    return market_open <= now_sp < market_close


def _seconds_until_market_open(now_sp: datetime) -> float:
    """Seconds until the next market-open moment."""
    today_open = now_sp.replace(
        hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MINUTE, second=0, microsecond=0
    )
    if now_sp < today_open and now_sp.weekday() < 5:
        return (today_open - now_sp).total_seconds()
    # Find the next weekday
    days_ahead = 1
    candidate = now_sp + timedelta(days=days_ahead)
    while candidate.weekday() >= 5:
        days_ahead += 1
        candidate = now_sp + timedelta(days=days_ahead)
    next_open = candidate.replace(
        hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MINUTE, second=0, microsecond=0
    )
    return (next_open - now_sp).total_seconds()


def _format_bar_log(bar_dict: dict) -> str:
    """One-line summary of a bar for logging."""
    t_sp = bar_dict["time_sp"]
    # Extract just HH:MM from the ISO string
    hhmm = t_sp[11:16] if isinstance(t_sp, str) else t_sp.strftime("%H:%M")
    return (
        f"{hhmm} | "
        f"O={bar_dict['open']:.0f} "
        f"H={bar_dict['high']:.0f} "
        f"L={bar_dict['low']:.0f} "
        f"C={bar_dict['close']:.0f}"
    )


# ─── core logic ─────────────────────────────────────────────────────────────


def _startup_backfill(
    symbol: str, client: QuantWinClient
) -> int:
    """Fetch the last BACKFILL_HOURS of M1 bars and send them.

    Returns the unix timestamp of the last ingested bar (or 0).
    """
    now_utc = datetime.now(timezone.utc)
    start_utc = now_utc - timedelta(hours=BACKFILL_HOURS)

    logger.info(
        "Startup backfill: fetching last %d hours of M1 bars for %s …",
        BACKFILL_HOURS,
        symbol,
    )

    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, start_utc, now_utc)

    if rates is None or len(rates) == 0:
        logger.info("No bars returned for backfill window.")
        return 0

    bars = [convert_bar_to_dict(r) for r in rates]
    total = len(bars)
    logger.info("Backfill: %d bars fetched — sending in batches of %d.", total, BATCH_SIZE)

    ingested = client.send_bars_batched(
        symbol, TIMEFRAME_LABEL, SOURCE_ID, bars, batch_size=BATCH_SIZE
    )
    logger.info("Backfill complete: %d/%d bars ingested.", ingested, total)

    # Return the latest bar timestamp
    return int(rates[-1]["time"])


def _poll_once(
    symbol: str,
    client: QuantWinClient,
    last_time: int,
) -> int:
    """Fetch new bars since *last_time* and send them.

    Returns the updated *last_time*.
    """
    from_dt = datetime.fromtimestamp(last_time + 60, tz=timezone.utc)
    rates = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_M1, from_dt, 10)

    if rates is None or len(rates) == 0:
        return last_time

    # Filter out bars we've already sent (in case copy_rates_from includes
    # the boundary bar).
    new_rates = [r for r in rates if int(r["time"]) > last_time]
    if not new_rates:
        return last_time

    bars = [convert_bar_to_dict(r) for r in new_rates]
    client.send_bars(symbol, TIMEFRAME_LABEL, SOURCE_ID, bars)

    for b in bars:
        logger.info("Ingested 1 bar: %s", _format_bar_log(b))

    return int(new_rates[-1]["time"])


# ─── main loop ──────────────────────────────────────────────────────────────


def run() -> None:
    """Entry point for the live scheduler."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 1. Initialize MT5
    ensure_mt5_initialized()

    # 2. Detect symbol
    symbol = detect_active_win_symbol()
    if symbol is None:
        logger.critical("Could not detect active WIN symbol — aborting.")
        mt5.shutdown()
        sys.exit(1)
    logger.info("Active symbol: %s", symbol)

    # 3. Fetch fresh auth token
    token_mgr = TokenManager()
    token_mgr.fetch_token()

    # 4. Build REST client
    client = QuantWinClient(token_mgr)

    # 5. Startup backfill
    last_time = _startup_backfill(symbol, client)

    # 6. Live polling loop
    logger.info("Entering live polling loop (every %ds)…", POLL_INTERVAL_SECONDS)
    backoff = 0  # exponential backoff counter for errors

    try:
        while True:
            now_sp = datetime.now(tz=SP_TZ)

            if not _is_market_hours(now_sp):
                wait = _seconds_until_market_open(now_sp)
                logger.info(
                    "Outside market hours (%s) — sleeping %.0f min until next open.",
                    now_sp.strftime("%H:%M %a"),
                    wait / 60,
                )
                time.sleep(min(wait, 300))  # wake up every 5 min max to re-check
                continue

            try:
                last_time = _poll_once(symbol, client, last_time)
                backoff = 0  # reset backoff on success
            except Exception as exc:
                backoff = min(backoff + 1, 6)
                wait = 2 ** backoff
                logger.error("Poll error: %s — retrying in %ds", exc, wait)
                time.sleep(wait)
                continue

            time.sleep(POLL_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        logger.info("Shutting down (KeyboardInterrupt).")
    finally:
        mt5.shutdown()
        logger.info("MT5 connection closed.")


# ─── allow ``python -m quantwinmt5feeder.scheduler`` ────────────────────────

if __name__ == "__main__":
    run()
