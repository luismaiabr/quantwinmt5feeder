"""Symbol detection — auto-detect the current active WIN futures contract."""

import logging
import re
from datetime import datetime

import MetaTrader5 as mt5
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

SP_TZ = ZoneInfo("America/Sao_Paulo")

# WIN expiry months: the contract is named WIN + letter + 2-digit year.
# Each contract covers the two months *before* its expiry month.
# Example: WINJ26 (April 2026) is the active contract during Feb–Mar 2026.
_MONTH_LETTERS: list[tuple[int, str]] = [
    (2, "G"),   # February
    (4, "J"),   # April
    (6, "M"),   # June
    (8, "Q"),   # August
    (10, "V"),  # October
    (12, "Z"),  # December
]


def _expected_symbol_for_date(dt: datetime) -> str:
    """Compute the expected WIN symbol for a given date.

    The active contract is the one whose expiry month is the *next*
    bimonthly expiry on or after the current month.
    """
    month = dt.month
    year = dt.year % 100  # 2-digit year

    for expiry_month, letter in _MONTH_LETTERS:
        if month <= expiry_month:
            return f"WIN{letter}{year:02d}"

    # Past December → roll to February of the next year.
    return f"WING{(year + 1) % 100:02d}"


def _enable_symbol(symbol: str) -> bool:
    """Enable a symbol in the Market Watch."""
    return bool(mt5.symbol_select(symbol, True))


def detect_active_win_symbol() -> str | None:
    """Auto-detect the current active WIN symbol from MT5.

    Strategy:
      1. Compute the expected symbol from today's date.
      2. Validate it exists and can be enabled in MT5.
      3. Fallback: scan ``mt5.symbols_get(group="*WIN*")`` for the best match.

    Returns the symbol name or ``None`` if nothing could be found.
    """
    now_sp = datetime.now(tz=SP_TZ)
    expected = _expected_symbol_for_date(now_sp)
    logger.info("Expected WIN symbol for %s: %s", now_sp.strftime("%Y-%m-%d"), expected)

    # ── Try the expected symbol first ──────────────────────────────────
    info = mt5.symbol_info(expected)
    if info is not None:
        if _enable_symbol(expected):
            logger.info("Symbol %s found and enabled.", expected)
            return expected
        else:
            logger.warning("Symbol %s exists but could not be enabled.", expected)

    # ── Fallback: scan all WIN symbols ─────────────────────────────────
    logger.info("Expected symbol %s not available — scanning MT5…", expected)
    all_syms = mt5.symbols_get(group="*WIN*")
    if all_syms is None or len(all_syms) == 0:
        logger.error("No WIN symbols found in MT5 at all.")
        return None

    # Prefer symbols whose name matches the pattern WIN[A-Z]\d{2}
    pattern = re.compile(r"^WIN[A-Z]\d{2}$")
    candidates = [s.name for s in all_syms if pattern.match(s.name)]

    if not candidates:
        # Accept anything with WIN in the name
        candidates = [s.name for s in all_syms]

    logger.info("WIN symbol candidates: %s", candidates)

    for sym in candidates:
        if _enable_symbol(sym):
            logger.info("Fallback symbol %s enabled.", sym)
            return sym

    logger.error("Could not enable any WIN symbol from candidates: %s", candidates)
    return None


def ensure_mt5_initialized() -> None:
    """Initialize the MT5 terminal; raise on failure."""
    if not mt5.initialize():
        error = mt5.last_error()
        raise RuntimeError(f"Failed to initialize MetaTrader5: {error}")
    logger.info("MetaTrader 5 initialized — version %s", mt5.version())
