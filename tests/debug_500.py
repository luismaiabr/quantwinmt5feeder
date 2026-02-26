import requests
from quantwinmt5feeder.auth import TokenManager
from quantwinmt5feeder.config import INGEST_ENDPOINT
import json

tm = TokenManager()
token = tm.fetch_token()

payload = {
    "bars": [
        {
            "time": 1765886520,
            "time_utc": "2025-12-16T12:02:00+00:00",
            "time_sp": "2025-12-16T09:02:00-03:00",
            "open": 166675.0,
            "high": 166675.0,
            "low": 166675.0,
            "close": 166675.0,
            "tick_volume": 1,
            "spread": 5,
            "real_volume": 1
        }
    ]
}

url = f"{INGEST_ENDPOINT}?symbol=WINJ26&timeframe=M1&source_id=mt5"
headers = {"Authorization": f"Bearer {token}"}
resp = requests.post(url, json=payload, headers=headers)

print(f"Status Code: {resp.status_code}")
try:
    print(resp.json())
except:
    print(resp.text)
