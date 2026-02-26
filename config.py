"""Configuration — loads .env and exposes constants."""

import os
import pathlib
from dotenv import load_dotenv

# ── .env ────────────────────────────────────────────────────────────────────
# The .env file lives at the qDATA root: c:\Documents backup\QUANT\qDATA\.env
_ENV_PATH = pathlib.Path(__file__).resolve().parents[1] / ".env"
load_dotenv(_ENV_PATH)

GET_TOKEN_USERNAME: str = os.environ["GET_TOKEN_USERNAME"]
GET_TOKEN_PASSWORD: str = os.environ["GET_TOKEN_PASSWORD"]

# ── API ─────────────────────────────────────────────────────────────────────
API_BASE_URL: str = "https://uptoken.cloud"
AUTH_ENDPOINT: str = f"{API_BASE_URL}/api/v1/auth/token"
INGEST_ENDPOINT: str = f"{API_BASE_URL}/api/v1/ingest/ohlc"

# ── Batching & timing ──────────────────────────────────────────────────────
BATCH_SIZE: int = 200
POLL_INTERVAL_SECONDS: int = 15
TOKEN_REFRESH_MINUTES: int = 30
BACKFILL_HOURS: int = 6
INTER_BATCH_DELAY_SECONDS: float = 0.1  # delay between batches in manual mode

# ── Market hours (São Paulo) ───────────────────────────────────────────────
MARKET_OPEN_HOUR: int = 9
MARKET_OPEN_MINUTE: int = 0
MARKET_CLOSE_HOUR: int = 18
MARKET_CLOSE_MINUTE: int = 0

# ── Source ──────────────────────────────────────────────────────────────────
SOURCE_ID: str = "mt5"
TIMEFRAME_LABEL: str = "M1"
