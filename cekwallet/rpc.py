"""Minimal JSON-RPC client untuk fallback ke public RPC.

Hanya menyediakan native balance lookup (`eth_getBalance`).
Dipakai sebagai fallback terakhir untuk chain yang tidak punya
Etherscan-compat free API (mis. BSC, Cronos, Arbitrum Nova, Polygon zkEVM).

Tidak butuh API key.
"""

from __future__ import annotations

import logging
import time

import requests

log = logging.getLogger(__name__)


class RpcError(RuntimeError):
    pass


class RpcClient:
    """Klien JSON-RPC minimal (cuma eth_getBalance)."""

    def __init__(
        self,
        url: str,
        rate_delay: float = 0.22,
        timeout: float = 30.0,
        session: requests.Session | None = None,
    ):
        if not url:
            raise ValueError("RPC URL is required")
        self.url = url
        self.rate_delay = max(0.0, float(rate_delay))
        self.timeout = float(timeout)
        self.session = session or requests.Session()
        self._last_call: float = 0.0

    def _throttle(self) -> None:
        if self.rate_delay <= 0:
            return
        elapsed = time.monotonic() - self._last_call
        wait = self.rate_delay - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()

    def _call(self, method: str, params: list) -> str:
        body = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
        last_err: Exception | None = None
        for attempt in range(4):
            self._throttle()
            try:
                r = self.session.post(self.url, json=body, timeout=self.timeout)
            except requests.RequestException as e:
                last_err = e
                time.sleep(min(2**attempt, 10))
                continue
            if r.status_code in (429, 502, 503, 504):
                last_err = RpcError(f"HTTP {r.status_code}")
                time.sleep(min(2**attempt, 10))
                continue
            if r.status_code != 200:
                raise RpcError(f"HTTP {r.status_code}: {r.text[:200]}")
            try:
                data = r.json()
            except ValueError as e:
                raise RpcError(f"Invalid JSON from RPC: {e}") from e
            if "error" in data:
                raise RpcError(f"RPC error: {data['error']}")
            return str(data.get("result", ""))
        raise RpcError(f"Exhausted retries; last error: {last_err}")

    def get_balance_wei(self, address: str) -> int:
        result = self._call("eth_getBalance", [address, "latest"])
        if not result:
            return 0
        try:
            return int(result, 16)
        except ValueError as e:
            raise RpcError(f"Cannot parse balance {result!r}: {e}") from e
