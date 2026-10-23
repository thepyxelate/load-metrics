#!/usr/bin/env python3
"""payload.py — dinamik load_id bilan JSON yaratib, API'ga yuboradi."""
import json
import sys
import uuid
import requests
from datetime import datetime, timezone

API_URL = "http://127.0.0.1:5000/api/v1/collect"

def build_payload(load_id: str | None = None) -> dict:
    load_id = load_id or str(uuid.uuid4())
    return {
        "data": [
            {
                "load_id": load_id,
                "payout": 1399.42,
                "rate_per_mile": 3.29,
                "total_stops": 4,
                "start_time": "2026-08-25T11:21:00Z",
                "end_time": "2026-08-26T14:46:00Z",
                "trip_duration": "27h 25m",
                "total_distance": 395.275324116096,
                "all_stops": [
                    {"loadingType": "PRELOADED", "location": "CLE2", "stop_number": 1, "time": "2026-08-25T11:21:00Z", "type": "PICKUP", "unloadingType": None},
                    {"loadingType": None, "location": "STAGNESHOSPITAL_BALTIMORE_ALG", "stop_number": 2, "time": "2026-08-25T13:00:00Z", "type": "DROPOFF", "unloadingType": "DROP"},
                    {"loadingType": "LIVE", "location": "STAGNESHOSPITAL_BALTIMORE_ALG", "stop_number": 2, "time": "2026-08-25T13:00:00Z", "type": "PICKUP", "unloadingType": None},
                    {"loadingType": None, "location": "MEDWISH MEDWORKS_CLEVELAND_ALG", "stop_number": 3, "time": "2026-08-26T12:00:00Z", "type": "DROPOFF", "unloadingType": "LIVE"},
                    {"loadingType": "PRELOADED", "location": "MEDWISH MEDWORKS_CLEVELAND_ALG", "stop_number": 3, "time": "2026-08-26T12:00:00Z", "type": "PICKUP", "unloadingType": None},
                    {"loadingType": None, "location": "TEB6", "stop_number": 4, "time": "2026-08-26T14:16:00Z", "type": "DROPOFF", "unloadingType": "DROP"},
                ],
                "extracted_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            }
        ]
    }

def main() -> int:
    # CLI: python payload.py [load_id] [--dry-run]
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry_run = "--dry-run" in sys.argv
    load_id = args[0] if args else None

    payload = build_payload(load_id)

    if dry_run:
        print(json.dumps(payload, indent=2))
        return 0

    print(f"→ POST {API_URL} | load_id={payload['data'][0]['load_id']}")
    r = requests.post(API_URL, json=payload, timeout=30)
    print(f"← {r.status_code} {r.text[:300]}")
    return 0 if r.ok else 1

if __name__ == "__main__":
    sys.exit(main())