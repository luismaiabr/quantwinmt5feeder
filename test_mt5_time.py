import MetaTrader5 as mt5
from datetime import datetime, timezone
from quantwinmt5feeder.assistance.ochl import SP_TZ
import logging

logging.basicConfig(level=logging.INFO)

mt5.initialize()
symbol = "WINJ26"

print(f"Current GMT time in MT5: {mt5.symbol_info_tick(symbol).time if mt5.symbol_info_tick(symbol) else 'N/A'}")

# Test 1: SP naive
d1 = datetime(2026, 2, 26, 9, 0, 0)
d2 = datetime(2026, 2, 26, 10, 0, 0)
rates1 = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, d1, d2)
print("Test 1 (SP Naive):", len(rates1) if rates1 is not None else "None")

# Test 2: UTC aware
d1_utc = d1.replace(tzinfo=SP_TZ).astimezone(timezone.utc)
d2_utc = d2.replace(tzinfo=SP_TZ).astimezone(timezone.utc)
rates2 = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, d1_utc, d2_utc)
print("Test 2 (UTC Aware):", len(rates2) if rates2 is not None else "None")

# Test 3: SP aware
d1_aw = d1.replace(tzinfo=SP_TZ)
d2_aw = d2.replace(tzinfo=SP_TZ)
rates3 = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, d1_aw, d2_aw)
print("Test 3 (SP Aware):", len(rates3) if rates3 is not None else "None")

# Test 4: UTC naive
rates4 = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, d1_utc.replace(tzinfo=None), d2_utc.replace(tzinfo=None))
print("Test 4 (UTC Naive):", len(rates4) if rates4 is not None else "None")

mt5.shutdown()
