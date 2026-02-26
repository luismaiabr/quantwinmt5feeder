"""Manual/backfill mode — CLI for filling larger historical date ranges."""

import argparse
import logging
import sys
from datetime import datetime, timezone

import MetaTrader5 as mt5

from quantwinmt5feeder.assistance.ochl import SP_TZ, convert_bar_to_dict

from quantwinmt5feeder.auth import TokenManager
from quantwinmt5feeder.client import QuantWinClient
from quantwinmt5feeder.config import (
    BATCH_SIZE,
    INTER_BATCH_DELAY_SECONDS,
    SOURCE_ID,
    TIMEFRAME_LABEL,
)
from quantwinmt5feeder.symbol import detect_active_win_symbol, ensure_mt5_initialized

logger = logging.getLogger(__name__)


def _parse_sp_datetime(s: str) -> datetime:
    """Parse a string like ``2026-02-20 09:00`` as São Paulo time."""
    naive = datetime.strptime(s, "%Y-%m-%d %H:%M")
    return naive.replace(tzinfo=SP_TZ)


def run_backfill(start_sp: datetime, end_sp: datetime) -> None:
    """Fetch bars in [start, end] from MT5 and send to the API."""
    # 1. Initialise MT5
    ensure_mt5_initialized()

    # 2. Detect symbol
    symbol = detect_active_win_symbol()
    if symbol is None:
        logger.critical("Could not detect active WIN symbol — aborting.")
        mt5.shutdown()
        sys.exit(1)
    logger.info("Active symbol: %s", symbol)

    # 3. Fresh auth token
    token_mgr = TokenManager()
    token_mgr.fetch_token()

    # 4. REST client
    client = QuantWinClient(token_mgr)

    # 5. Convert to UTC for MT5 call
    start_utc = start_sp.astimezone(timezone.utc)
    end_utc = end_sp.astimezone(timezone.utc)

    logger.info(
        "Fetching M1 bars: %s → %s (SP) …",
        start_sp.strftime("%Y-%m-%d %H:%M"),
        end_sp.strftime("%Y-%m-%d %H:%M"),
    )

    # Wait for MT5 to download history (asynchronous)
    rates = None
    for _ in range(10):
        rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, start_utc, end_utc)
        if rates is not None and len(rates) > 0:
            break
        time.sleep(1)

    if rates is None or len(rates) == 0:
        logger.info("No bars returned for the requested range (history might be empty).")
        mt5.shutdown()
        return

    bars = [convert_bar_to_dict(r) for r in rates]
    total = len(bars)
    logger.info("%d bars fetched — sending in batches of %d.", total, BATCH_SIZE)

    # 6. Send in batches (with token refresh support for long runs)
    ingested = client.send_bars_batched(
        symbol,
        TIMEFRAME_LABEL,
        SOURCE_ID,
        bars,
        batch_size=BATCH_SIZE,
        delay=INTER_BATCH_DELAY_SECONDS,
        max_retries=3,
    )

    logger.info("Backfill complete: %d/%d bars ingested.", ingested, total)

    # 7. Cleanup
    mt5.shutdown()
    logger.info("MT5 connection closed.")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    parser = argparse.ArgumentParser(
        description="QuantWin MT5 manual backfill — fetch and ingest historical M1 bars."
    )
    parser.add_argument(
        "--start",
        required=True,
        help='Start datetime in São Paulo time, e.g. "2026-02-20 09:00"',
    )
    parser.add_argument(
        "--end",
        required=True,
        help='End datetime in São Paulo time, e.g. "2026-02-20 18:00"',
    )

    args = parser.parse_args()

    start_sp = _parse_sp_datetime(args.start)
    end_sp = _parse_sp_datetime(args.end)

    if end_sp <= start_sp:
        logger.error("--end must be after --start.")
        sys.exit(1)

    run_backfill(start_sp, end_sp)


if __name__ == "__main__":
    main()
