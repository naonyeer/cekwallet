"""Klien Etherscan API.

Mendukung 2 mode:
1. Etherscan V2 unified (default): 1 endpoint + 1 key untuk 50+ chain via `chainid` param.
   Dokumentasi: https://docs.etherscan.io/etherscan-v2
2. Etherscan V1 legacy: 1 endpoint per explorer (BSCScan / FtmScan / Snowtrace / dll),
   API key per explorer. Shape API sama dengan V2 (modul `account`, dll), cuma tidak butuh `chainid`.

`ScanClient` adalah abstraksi tipis di atas keduanya — tetap pakai
modul yang sama (`balance`, `txlist`, `tokentx`, ...).

Free tier:
- V2 (Etherscan): 5 calls/sec, 100k/hari, hanya beberapa chain di tier free
- V1 per-explorer: biasanya 2-5 calls/sec
"""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

log = logging.getLogger(__name__)

V2_BASE_URL = "https://api.etherscan.io/v2/api"


class EtherscanError(RuntimeError):
    pass


class ScanClient:
    """Klien untuk Etherscan-family (V2 unified atau V1 per-explorer)."""

    def __init__(
        self,
        api_key: str,
        base_url: str = V2_BASE_URL,
        chain_id: int | None = None,
        send_chainid: bool = True,
        rate_delay: float = 0.22,
        timeout: float = 30.0,
        session: requests.Session | None = None,
    ):
        if not api_key:
            raise ValueError("API key is required")
        self.api_key = api_key
        self.base_url = base_url
        self.chain_id = chain_id
        self.send_chainid = send_chainid
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

    def _get(self, params: dict[str, Any]) -> Any:
        q: dict[str, Any] = {**params}
        if self.send_chainid and self.chain_id is not None:
            q["chainid"] = self.chain_id
        q["apikey"] = self.api_key
        last_err: Exception | None = None
        for attempt in range(5):
            self._throttle()
            try:
                r = self.session.get(self.base_url, params=q, timeout=self.timeout)
            except requests.RequestException as e:
                last_err = e
                time.sleep(min(2**attempt, 10))
                continue
            if r.status_code in (429, 502, 503, 504):
                last_err = EtherscanError(f"HTTP {r.status_code}: {r.text[:200]}")
                time.sleep(min(2**attempt, 10))
                continue
            if r.status_code != 200:
                raise EtherscanError(
                    f"HTTP {r.status_code} for {params}: {r.text[:300]}"
                )
            try:
                data = r.json()
            except ValueError as e:
                raise EtherscanError(f"Invalid JSON from API: {e}") from e
            status = str(data.get("status", ""))
            message = str(data.get("message", ""))
            result = data.get("result")
            if status == "1":
                return result
            if isinstance(result, list) and result == []:
                return []
            if isinstance(result, str) and (
                "No transactions found" in result
                or "No records found" in result
                or "No token transfers found" in result
            ):
                return []
            if isinstance(result, str) and "rate limit" in result.lower():
                last_err = EtherscanError(result)
                time.sleep(min(2**attempt, 10))
                continue
            if message == "NOTOK" or "Invalid API Key" in str(result):
                raise EtherscanError(f"API rejected request: {result}")
            raise EtherscanError(f"API error ({message}) for {params}: {result}")
        raise EtherscanError(f"Exhausted retries; last error: {last_err}")

    # -------- account module --------
    def get_balance_wei(self, address: str) -> int:
        result = self._get({"module": "account", "action": "balance",
                            "address": address, "tag": "latest"})
        return int(result)

    def list_txs(self, address: str, max_pages: int = 10) -> list[dict]:
        return self._paginate(address, action="txlist", max_pages=max_pages)

    def list_internal_txs(self, address: str, max_pages: int = 10) -> list[dict]:
        return self._paginate(address, action="txlistinternal", max_pages=max_pages)

    def list_erc20_transfers(self, address: str, max_pages: int = 20) -> list[dict]:
        return self._paginate(address, action="tokentx", max_pages=max_pages)

    def list_erc721_transfers(self, address: str, max_pages: int = 10) -> list[dict]:
        return self._paginate(address, action="tokennfttx", max_pages=max_pages)

    def list_erc1155_transfers(self, address: str, max_pages: int = 10) -> list[dict]:
        return self._paginate(address, action="token1155tx", max_pages=max_pages)

    def _paginate(
        self,
        address: str,
        action: str,
        page_size: int = 10_000,
        max_pages: int = 10,
    ) -> list[dict]:
        all_rows: list[dict] = []
        for page in range(1, max_pages + 1):
            rows = self._get(
                {
                    "module": "account",
                    "action": action,
                    "address": address,
                    "startblock": 0,
                    "endblock": 99999999,
                    "page": page,
                    "offset": page_size,
                    "sort": "asc",
                },
            )
            if not isinstance(rows, list) or not rows:
                break
            all_rows.extend(rows)
            if len(rows) < page_size:
                break
        return all_rows

    def get_token_balance(self, contract: str, address: str) -> int:
        result = self._get(
            {"module": "account", "action": "tokenbalance",
             "contractaddress": contract, "address": address, "tag": "latest"},
        )
        try:
            return int(result)
        except (TypeError, ValueError):
            return 0


# --- Factories for clarity ---
def make_v2_client(
    api_key: str,
    chain_id: int,
    rate_delay: float = 0.22,
    timeout: float = 30.0,
    session: requests.Session | None = None,
) -> ScanClient:
    return ScanClient(
        api_key=api_key,
        base_url=V2_BASE_URL,
        chain_id=chain_id,
        send_chainid=True,
        rate_delay=rate_delay,
        timeout=timeout,
        session=session,
    )


def make_legacy_client(
    api_key: str,
    base_url: str,
    rate_delay: float = 0.22,
    timeout: float = 30.0,
    session: requests.Session | None = None,
) -> ScanClient:
    return ScanClient(
        api_key=api_key or "YourApiKeyToken",  # some explorers accept dummy on free
        base_url=base_url,
        chain_id=None,
        send_chainid=False,
        rate_delay=rate_delay,
        timeout=timeout,
        session=session,
    )
