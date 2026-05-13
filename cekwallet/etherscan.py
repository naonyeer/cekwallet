"""Etherscan V2 unified API client.

Etherscan V2 menyatukan 50+ chain di balik 1 endpoint dengan 1 API key.
Dokumentasi: https://docs.etherscan.io/etherscan-v2

Kita pakai modul `account` untuk:
- balance         : native coin balance
- txlist          : daftar tx luar (external)
- txlistinternal  : daftar tx internal
- tokentx         : transfer ERC-20
- tokennfttx      : transfer ERC-721
- token1155tx     : transfer ERC-1155

Free tier: 5 calls/sec, 100k/day. Kita default ke 4.5 rps.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

log = logging.getLogger(__name__)

BASE_URL = "https://api.etherscan.io/v2/api"


class EtherscanError(RuntimeError):
    pass


class EtherscanClient:
    def __init__(
        self,
        api_key: str,
        rate_delay: float = 0.22,
        timeout: float = 30.0,
        session: requests.Session | None = None,
    ):
        if not api_key:
            raise ValueError("ETHERSCAN_API_KEY is required")
        self.api_key = api_key
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

    def _get(self, chain_id: int, params: dict[str, Any]) -> Any:
        """Panggil endpoint Etherscan V2. Retry sederhana untuk rate-limit/5xx."""
        q = {**params, "chainid": chain_id, "apikey": self.api_key}
        last_err: Exception | None = None
        for attempt in range(5):
            self._throttle()
            try:
                r = self.session.get(BASE_URL, params=q, timeout=self.timeout)
            except requests.RequestException as e:
                last_err = e
                time.sleep(min(2**attempt, 10))
                continue
            if r.status_code in (429, 502, 503, 504):
                last_err = EtherscanError(f"HTTP {r.status_code}: {r.text[:200]}")
                time.sleep(min(2**attempt, 10))
                continue
            if r.status_code != 200:
                raise EtherscanError(f"HTTP {r.status_code} for {params}: {r.text[:300]}")
            try:
                data = r.json()
            except ValueError as e:
                raise EtherscanError(f"Invalid JSON from API: {e}") from e
            # API style: { status, message, result }
            status = str(data.get("status", ""))
            message = str(data.get("message", ""))
            result = data.get("result")
            if status == "1":
                return result
            # status=0 with "No transactions found" / "No records found" is benign
            if isinstance(result, list) and result == []:
                return []
            if isinstance(result, str) and (
                "No transactions found" in result
                or "No records found" in result
                or "No token transfers found" in result
            ):
                return []
            # Rate limit hint
            if isinstance(result, str) and "rate limit" in result.lower():
                last_err = EtherscanError(result)
                time.sleep(min(2**attempt, 10))
                continue
            # NOTOK from missing/invalid key is fatal
            if message == "NOTOK" or "Invalid API Key" in str(result):
                raise EtherscanError(f"Etherscan rejected request: {result}")
            # Other status=0: surface as error
            raise EtherscanError(f"API error ({message}) for {params}: {result}")
        raise EtherscanError(f"Exhausted retries; last error: {last_err}")

    # -------- account module --------
    def get_balance_wei(self, chain_id: int, address: str) -> int:
        result = self._get(chain_id, {"module": "account", "action": "balance",
                                       "address": address, "tag": "latest"})
        return int(result)

    def get_balances_wei(self, chain_id: int, addresses: list[str]) -> dict[str, int]:
        """`balancemulti` mendukung sampai 20 address per call."""
        out: dict[str, int] = {}
        for i in range(0, len(addresses), 20):
            chunk = addresses[i : i + 20]
            result = self._get(
                chain_id,
                {"module": "account", "action": "balancemulti",
                 "address": ",".join(chunk), "tag": "latest"},
            )
            for row in result:
                out[row["account"]] = int(row["balance"])
        return out

    def list_txs(self, chain_id: int, address: str, max_pages: int = 10) -> list[dict]:
        return self._paginate(chain_id, address, action="txlist", max_pages=max_pages)

    def list_internal_txs(self, chain_id: int, address: str, max_pages: int = 10) -> list[dict]:
        return self._paginate(chain_id, address, action="txlistinternal", max_pages=max_pages)

    def list_erc20_transfers(self, chain_id: int, address: str, max_pages: int = 20) -> list[dict]:
        return self._paginate(chain_id, address, action="tokentx", max_pages=max_pages)

    def list_erc721_transfers(self, chain_id: int, address: str, max_pages: int = 10) -> list[dict]:
        return self._paginate(chain_id, address, action="tokennfttx", max_pages=max_pages)

    def list_erc1155_transfers(self, chain_id: int, address: str, max_pages: int = 10) -> list[dict]:
        return self._paginate(chain_id, address, action="token1155tx", max_pages=max_pages)

    def _paginate(
        self,
        chain_id: int,
        address: str,
        action: str,
        page_size: int = 10_000,
        max_pages: int = 10,
    ) -> list[dict]:
        all_rows: list[dict] = []
        for page in range(1, max_pages + 1):
            rows = self._get(
                chain_id,
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

    # -------- erc20 current balance via contract module --------
    def get_token_balance(self, chain_id: int, contract: str, address: str) -> int:
        result = self._get(
            chain_id,
            {"module": "account", "action": "tokenbalance",
             "contractaddress": contract, "address": address, "tag": "latest"},
        )
        try:
            return int(result)
        except (TypeError, ValueError):
            return 0
