"""Token management — fresh on startup, auto-refresh every 30 min."""

import logging
import time

import requests

from quantwinmt5feeder.config import (
    AUTH_ENDPOINT,
    GET_TOKEN_PASSWORD,
    GET_TOKEN_USERNAME,
    TOKEN_REFRESH_MINUTES,
)

logger = logging.getLogger(__name__)


class TokenManager:
    """Manages the Bearer token lifecycle for the QuantWin REST API.

    * Always fetches a fresh token on startup (never reuses cached tokens).
    * Auto-refreshes every ``TOKEN_REFRESH_MINUTES`` minutes while running.
    """

    def __init__(self) -> None:
        self._token: str | None = None
        self._fetched_at: float = 0.0  # monotonic timestamp

    # ── public ──────────────────────────────────────────────────────────

    def fetch_token(self) -> str:
        """Request a brand-new token from the auth endpoint."""
        payload = {
            "username": GET_TOKEN_USERNAME,
            "password": GET_TOKEN_PASSWORD,
        }
        logger.info("Requesting new auth token from %s …", AUTH_ENDPOINT)

        resp = requests.post(AUTH_ENDPOINT, json=payload, timeout=30)
        resp.raise_for_status()

        data = resp.json()
        self._token = data["access_token"]
        self._fetched_at = time.monotonic()

        logger.info("Auth token obtained successfully.")
        return self._token

    def get_token(self) -> str:
        """Return the current token, refreshing it if it's stale (>30 min)."""
        if self._token is None:
            return self.fetch_token()

        elapsed_minutes = (time.monotonic() - self._fetched_at) / 60.0
        if elapsed_minutes >= TOKEN_REFRESH_MINUTES:
            logger.info(
                "Token age %.1f min ≥ %d min — refreshing.",
                elapsed_minutes,
                TOKEN_REFRESH_MINUTES,
            )
            return self.fetch_token()

        return self._token

    def force_refresh(self) -> str:
        """Force an immediate token refresh (e.g. after a 401)."""
        return self.fetch_token()
