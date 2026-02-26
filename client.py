"""REST client — sends OHLC bar batches to the QuantWin ingestion endpoint."""

import logging
import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from quantwinmt5feeder.auth import TokenManager
from quantwinmt5feeder.config import (
    BATCH_SIZE,
    INGEST_ENDPOINT,
    INTER_BATCH_DELAY_SECONDS,
)

logger = logging.getLogger(__name__)


def _build_session() -> requests.Session:
    """Build a ``requests.Session`` with automatic retries on transient errors."""
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=1,           # 1s, 2s, 4s, 8s, 16s
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


class QuantWinClient:
    """Sends OHLC bars to ``POST /api/v1/ingest/ohlc``."""

    def __init__(self, token_manager: TokenManager) -> None:
        self._tm = token_manager
        self._session = _build_session()

    # ── single batch ────────────────────────────────────────────────────

    def send_bars(
        self,
        symbol: str,
        timeframe: str,
        source_id: str,
        bars: list[dict[str, Any]],
    ) -> dict:
        """Send a single batch of bars. Returns the JSON response body."""
        token = self._tm.get_token()
        headers = {"Authorization": f"Bearer {token}"}
        params = {
            "symbol": symbol,
            "timeframe": timeframe,
            "source_id": source_id,
        }
        payload = {"bars": bars}

        resp = self._session.post(
            INGEST_ENDPOINT,
            params=params,
            json=payload,
            headers=headers,
            timeout=60,
        )

        # If we get a 401, try one token refresh and retry once.
        if resp.status_code == 401:
            logger.warning("Got 401 — refreshing token and retrying…")
            token = self._tm.force_refresh()
            headers["Authorization"] = f"Bearer {token}"
            resp = self._session.post(
                INGEST_ENDPOINT,
                params=params,
                json=payload,
                headers=headers,
                timeout=60,
            )

        resp.raise_for_status()
        return resp.json()

    # ── chunked batches ─────────────────────────────────────────────────

    def send_bars_batched(
        self,
        symbol: str,
        timeframe: str,
        source_id: str,
        bars: list[dict[str, Any]],
        *,
        batch_size: int = BATCH_SIZE,
        delay: float = INTER_BATCH_DELAY_SECONDS,
        max_retries: int = 3,
    ) -> int:
        """Chunk *bars* into batches and send sequentially.

        Returns the total number of successfully ingested bars.
        """
        total = len(bars)
        if total == 0:
            logger.info("No bars to send.")
            return 0

        chunks = [bars[i : i + batch_size] for i in range(0, total, batch_size)]
        ingested = 0

        for idx, chunk in enumerate(chunks, start=1):
            success = False
            for attempt in range(1, max_retries + 1):
                try:
                    result = self.send_bars(symbol, timeframe, source_id, chunk)
                    count = result.get("ingested", len(chunk))
                    ingested += count
                    logger.info(
                        "Batch %d/%d sent — %d/%d bars ingested.",
                        idx,
                        len(chunks),
                        ingested,
                        total,
                    )
                    success = True
                    break
                except requests.RequestException as exc:
                    logger.error(
                        "Batch %d/%d attempt %d failed: %s",
                        idx,
                        len(chunks),
                        attempt,
                        exc,
                    )
                    if attempt < max_retries:
                        wait = 2 ** attempt
                        logger.info("Retrying in %ds…", wait)
                        time.sleep(wait)

            if not success:
                logger.error(
                    "Batch %d/%d FAILED after %d retries — skipping.",
                    idx,
                    len(chunks),
                    max_retries,
                )

            # inter-batch delay (skip after last batch)
            if idx < len(chunks):
                time.sleep(delay)

        return ingested
