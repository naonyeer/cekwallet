"""Ambil harga USD untuk native coin via CoinGecko (free, optional key)."""

from __future__ import annotations

import logging
import time

import requests

log = logging.getLogger(__name__)

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"


def fetch_usd_prices(
    coingecko_ids: list[str],
    api_key: str | None = None,
    timeout: float = 30.0,
) -> dict[str, float]:
    """Return {coingecko_id: usd_price}. Yang tidak ketemu di-skip."""
    ids = sorted({i for i in coingecko_ids if i})
    if not ids:
        return {}
    headers = {}
    if api_key:
        headers["x-cg-demo-api-key"] = api_key
    out: dict[str, float] = {}
    # Batch by 100 ids per call to be safe
    for i in range(0, len(ids), 100):
        chunk = ids[i : i + 100]
        for attempt in range(4):
            try:
                r = requests.get(
                    COINGECKO_URL,
                    params={"ids": ",".join(chunk), "vs_currencies": "usd"},
                    headers=headers,
                    timeout=timeout,
                )
            except requests.RequestException as e:
                log.warning("CoinGecko request failed: %s", e)
                time.sleep(min(2**attempt, 8))
                continue
            if r.status_code == 429:
                log.warning("CoinGecko rate limited, backing off")
                time.sleep(min(2**attempt, 30))
                continue
            if r.status_code != 200:
                log.warning("CoinGecko HTTP %s: %s", r.status_code, r.text[:200])
                break
            data = r.json()
            for cg_id, row in data.items():
                if isinstance(row, dict) and "usd" in row:
                    out[cg_id] = float(row["usd"])
            break
    return out
