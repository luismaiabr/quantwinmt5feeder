"""Gap Filler — blindly fetches and pushes all data from START_DATE up to today using REST API Upserts.
This avoids needing direct PostgreSQL connection from the local machine."""

import logging
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import MetaTrader5 as mt5

from quantwinmt5feeder.assistance.ochl import SP_TZ, convert_bar_to_dict
from quantwinmt5feeder.auth import TokenManager
from quantwinmt5feeder.client import QuantWinClient
from quantwinmt5feeder.config import (
    BATCH_SIZE,
    INTER_BATCH_DELAY_SECONDS,
    SOURCE_ID,
    START_DATE_GAP_FILLING,
    TIMEFRAME_LABEL,
)
from quantwinmt5feeder.symbol import detect_active_win_symbol, ensure_mt5_initialized

logger = logging.getLogger(__name__)


def _parse_sp_datetime(s: str) -> datetime:
    """Parse a string like ``2024-01-01 09:00`` as São Paulo time."""
    naive = datetime.strptime(s, "%Y-%m-%d %H:%M")
    return naive.replace(tzinfo=SP_TZ)


def _fill_gap(client: QuantWinClient, symbol: str, start_sp: datetime, end_sp: datetime) -> int:
    """Fetch a gap using MT5 and send to REST API."""
    start_utc = start_sp.astimezone(timezone.utc)
    end_utc = end_sp.astimezone(timezone.utc)
    
    rates = None
    for _ in range(5):
        rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, start_utc, end_utc)
        if rates is not None and len(rates) > 0:
            break
        time.sleep(1)
        
    if rates is None or len(rates) == 0:
        logger.info(f" -> No MT5 history found for {start_sp.strftime('%Y-%m-%d')} (Holiday/Weekend?)")
        return 0
        
    bars = [convert_bar_to_dict(r) for r in rates]
    logger.info(f" -> Grabbed {len(bars)} bars. Uploading to API...")
    
    ingested = client.send_bars_batched(
        symbol,
        TIMEFRAME_LABEL,
        SOURCE_ID,
        bars,
        batch_size=BATCH_SIZE,
        delay=INTER_BATCH_DELAY_SECONDS,
        max_retries=3,
    )
    return ingested


def run_gap_filler() -> None:
    ensure_mt5_initialized()
    symbol = detect_active_win_symbol()
    if symbol is None:
        logger.critical("Could not detect active WIN symbol.")
        sys.exit(1)
        
    logger.info(f"Blind Gap filling for symbol: {symbol} starting from {START_DATE_GAP_FILLING}")
    
    start_sp = _parse_sp_datetime(START_DATE_GAP_FILLING)
    
    # State file to remember all processed dates
    state_file = Path("gap_filler_state.txt")
    processed_dates = set()
    if state_file.exists():
        lines = state_file.read_text(encoding="utf-8").splitlines()
        for line in lines:
            line = line.strip()
            if line:
                processed_dates.add(line)
        logger.info(f"Loaded {len(processed_dates)} already processed dates from state file.")
    
    # Run until exactly today at 00:00 (scheduler handles intra-day)
    end_sp = datetime.now(tz=SP_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    
    if start_sp >= end_sp:
        logger.info("Start date is today or in the future. Nothing to gap fill.")
        return
        
    token_mgr = TokenManager()
    token_mgr.fetch_token()
    client = QuantWinClient(token_mgr)
    
    total_ingested = 0
    current_day = start_sp.replace(hour=0, minute=0)
    
    # Loop day by day
    while current_day < end_sp:
        date_str = current_day.strftime("%Y-%m-%d")
        
        # Only process Mon-Fri (0-4) and days not already processed
        if current_day.weekday() < 5:
            if date_str in processed_dates:
                logger.debug(f"Skipping already processed day: {date_str}")
            else:
                day_start = current_day.replace(hour=9, minute=0)
                day_end = current_day.replace(hour=18, minute=5)
                
                logger.info(f"Processing Day: {date_str}")
                ingested = _fill_gap(client, symbol, day_start, day_end)
                total_ingested += ingested
                
                # Append progress after the day is successfully processed
                with state_file.open("a", encoding="utf-8") as f:
                    f.write(date_str + "\n")
                processed_dates.add(date_str)
            
        current_day += timedelta(days=1)
        
    logger.info(f"Gap filling complete! Total bars pushed (some may be updates): {total_ingested}")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    run_gap_filler()


if __name__ == "__main__":
    main()
