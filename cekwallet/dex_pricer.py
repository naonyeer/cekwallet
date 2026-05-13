"""Ambil harga USD ERC-20 lewat DexScreener API (gratis, no key).

Doc: https://docs.dexscreener.com/api/reference

Endpoint utama: `GET /tokens/v1/{chainSlug}/{tokenAddresses}` (max 30 alamat).
Response: array of pair objects; tiap pair punya `priceUsd` dan `liquidity.usd`.
Kita pilih pair dengan liquidity tertinggi sebagai patokan harga.

Rate limit: 300 req/min (per IP). Kita throttle ke ~4 rps.
"""

from __future__ import annotations

import logging
import time

import requests

log = logging.getLogger(__name__)

BASE_URL = "https://api.dexscreener.com"
BATCH = 30
THROTTLE = 0.25  # ~4 rps


def fetch_token_usd_prices(
    dex_slug: str,
    contracts: list[str],
    timeout: float = 30.0,
    session: requests.Session | None = None,
) -> dict[str, float]:
    """Return {contract_lower: usd_price}. Token yang tidak ada pair-nya di-skip."""
    if not dex_slug or not contracts:
        return {}
    sess = session or requests.Session()
    contracts_lower = sorted({c.lower() for c in contracts if c})
    out: dict[str, float] = {}
    last_call = 0.0
    for i in range(0, len(contracts_lower), BATCH):
        chunk = contracts_lower[i : i + BATCH]
        # throttle
        wait = THROTTLE - (time.monotonic() - last_call)
        if wait > 0:
            time.sleep(wait)
        last_call = time.monotonic()
        url = f"{BASE_URL}/tokens/v1/{dex_slug}/{','.join(chunk)}"
        try:
            r = sess.get(url, timeout=timeout)
        except requests.RequestException as e:
            log.warning("DexScreener %s req failed: %s", dex_slug, e)
            continue
        if r.status_code == 429:
            log.warning("DexScreener rate limited; backing off 5s")
            time.sleep(5)
            continue
        if r.status_code != 200:
            log.warning("DexScreener %s HTTP %s: %s",
                        dex_slug, r.status_code, r.text[:120])
            continue
        try:
            pairs = r.json()
        except ValueError:
            continue
        if not isinstance(pairs, list):
            continue
        # Per token, pilih price dari pair dengan liquidity USD tertinggi
        best: dict[str, tuple[float, float]] = {}  # contract -> (liq, price)
        for p in pairs:
            try:
                token_addr = (p.get("baseToken") or {}).get("address", "").lower()
                price = float(p.get("priceUsd") or 0)
                liq = float((p.get("liquidity") or {}).get("usd") or 0)
            except (TypeError, ValueError):
                continue
            if not token_addr or price <= 0:
                continue
            cur = best.get(token_addr)
            if cur is None or liq > cur[0]:
                best[token_addr] = (liq, price)
        for addr, (_, price) in best.items():
            out[addr] = price
    return out
