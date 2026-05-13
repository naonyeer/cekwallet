"""Inti logika scan: untuk 1 wallet + 1 chain, kumpulkan ringkasan."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from .chains import Chain
from .etherscan import ScanClient
from .rpc import RpcClient
from .scam_filter import is_scam_token

log = logging.getLogger(__name__)


def _ts_to_iso(ts: str | int | None) -> str | None:
    if ts is None or ts == "":
        return None
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()
    except (TypeError, ValueError):
        return None


def _wei_to_decimal(wei: int, decimals: int) -> Decimal:
    if wei == 0:
        return Decimal(0)
    return Decimal(wei) / (Decimal(10) ** decimals)


@dataclass
class TokenSummary:
    contract: str
    symbol: str
    name: str
    decimals: int
    balance_raw: int = 0
    balance: str = "0"
    first_seen: str | None = None
    last_seen: str | None = None
    transfers: int = 0
    is_scam: bool = False
    usd_price: float | None = None
    usd_value: float | None = None


@dataclass
class NftSummary:
    contract: str
    symbol: str
    name: str
    standard: str  # "ERC-721" | "ERC-1155"
    net_count: int = 0
    transfers: int = 0
    first_seen: str | None = None
    last_seen: str | None = None
    is_scam: bool = False


@dataclass
class ChainResult:
    chain_id: int
    chain_name: str
    address: str
    native_symbol: str
    route: str = ""  # "v2" | "v1:bscscan" | "skipped"
    status: str = "ok"  # ok | error | skipped
    native_raw: int = 0
    native: str = "0"
    native_usd: float | None = None
    tx_count: int = 0
    tx_in: int = 0
    tx_out: int = 0
    internal_tx_count: int = 0
    first_tx_at: str | None = None
    last_tx_at: str | None = None
    tokens: list[TokenSummary] = field(default_factory=list)
    nfts: list[NftSummary] = field(default_factory=list)
    nonzero_token_count: int = 0
    nonzero_real_token_count: int = 0
    nft_holdings_count: int = 0
    real_nft_holdings_count: int = 0
    token_usd: float | None = None
    total_usd: float | None = None
    error: str | None = None
    skip_reason: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _aggregate_token_transfers(
    address: str, transfers: list[dict]
) -> dict[str, TokenSummary]:
    address_lc = address.lower()
    by_contract: dict[str, TokenSummary] = {}
    for tx in transfers:
        contract = tx.get("contractAddress", "").lower()
        if not contract:
            continue
        try:
            decimals = int(tx.get("tokenDecimal") or 18)
        except ValueError:
            decimals = 18
        sym = tx.get("tokenSymbol") or "?"
        name = tx.get("tokenName") or "?"
        ts = _ts_to_iso(tx.get("timeStamp"))
        cur = by_contract.get(contract)
        if cur is None:
            cur = TokenSummary(
                contract=contract,
                symbol=sym,
                name=name,
                decimals=decimals,
                first_seen=ts,
                last_seen=ts,
                is_scam=is_scam_token(sym, name),
            )
            by_contract[contract] = cur
        cur.transfers += 1
        if ts:
            if not cur.first_seen or ts < cur.first_seen:
                cur.first_seen = ts
            if not cur.last_seen or ts > cur.last_seen:
                cur.last_seen = ts
        try:
            value = int(tx.get("value") or 0)
        except ValueError:
            value = 0
        if tx.get("to", "").lower() == address_lc:
            cur.balance_raw += value
        elif tx.get("from", "").lower() == address_lc:
            cur.balance_raw -= value
    return by_contract


def _aggregate_nft_transfers(
    address: str, transfers: list[dict], standard: str
) -> dict[str, NftSummary]:
    address_lc = address.lower()
    by_contract: dict[str, NftSummary] = {}
    for tx in transfers:
        contract = tx.get("contractAddress", "").lower()
        if not contract:
            continue
        sym = tx.get("tokenSymbol") or "?"
        name = tx.get("tokenName") or "?"
        cur = by_contract.get(contract)
        if cur is None:
            cur = NftSummary(
                contract=contract,
                symbol=sym,
                name=name,
                standard=standard,
                is_scam=is_scam_token(sym, name),
            )
            by_contract[contract] = cur
        ts = _ts_to_iso(tx.get("timeStamp"))
        cur.transfers += 1
        if ts:
            if not cur.first_seen or ts < cur.first_seen:
                cur.first_seen = ts
            if not cur.last_seen or ts > cur.last_seen:
                cur.last_seen = ts
        if standard == "ERC-1155":
            try:
                qty = int(tx.get("tokenValue") or tx.get("value") or 1)
            except ValueError:
                qty = 1
        else:
            qty = 1
        if tx.get("to", "").lower() == address_lc:
            cur.net_count += qty
        elif tx.get("from", "").lower() == address_lc:
            cur.net_count -= qty
    return by_contract


def scan_wallet_on_chain(
    client: ScanClient,
    chain: Chain,
    address: str,
    include_nft: bool = True,
    include_tx_history: bool = True,
    max_tx_pages: int = 10,
    max_token_pages: int = 20,
) -> ChainResult:
    res = ChainResult(
        chain_id=chain.id,
        chain_name=chain.name,
        address=address,
        native_symbol=chain.symbol,
    )
    try:
        wei = client.get_balance_wei(address)
        res.native_raw = wei
        res.native = f"{_wei_to_decimal(wei, chain.decimals):f}"

        if include_tx_history:
            txs = client.list_txs(address, max_pages=max_tx_pages)
            res.tx_count = len(txs)
            res.tx_in = sum(1 for t in txs if t.get("to", "").lower() == address.lower())
            res.tx_out = sum(1 for t in txs if t.get("from", "").lower() == address.lower())
            if txs:
                res.first_tx_at = _ts_to_iso(txs[0].get("timeStamp"))
                res.last_tx_at = _ts_to_iso(txs[-1].get("timeStamp"))
            try:
                itx = client.list_internal_txs(address, max_pages=max_tx_pages)
                res.internal_tx_count = len(itx)
            except Exception as e:  # noqa: BLE001
                log.warning("internal tx fetch failed (%s/%s): %s", chain.name, address, e)

        erc20 = client.list_erc20_transfers(address, max_pages=max_token_pages)
        tokens = _aggregate_token_transfers(address, erc20)
        for t in tokens.values():
            t.balance = f"{_wei_to_decimal(max(t.balance_raw, 0), t.decimals):f}"
        res.tokens = sorted(tokens.values(), key=lambda x: x.transfers, reverse=True)
        res.nonzero_token_count = sum(1 for t in res.tokens if t.balance_raw > 0)
        res.nonzero_real_token_count = sum(
            1 for t in res.tokens if t.balance_raw > 0 and not t.is_scam
        )

        if include_nft:
            nfts: dict[str, NftSummary] = {}
            try:
                er721 = client.list_erc721_transfers(address, max_pages=max_token_pages)
                nfts.update(_aggregate_nft_transfers(address, er721, "ERC-721"))
            except Exception as e:  # noqa: BLE001
                log.warning("ERC-721 fetch failed (%s/%s): %s", chain.name, address, e)
            try:
                er1155 = client.list_erc1155_transfers(address, max_pages=max_token_pages)
                for k, v in _aggregate_nft_transfers(address, er1155, "ERC-1155").items():
                    nfts[f"{k}:1155"] = v
            except Exception as e:  # noqa: BLE001
                log.warning("ERC-1155 fetch failed (%s/%s): %s", chain.name, address, e)
            res.nfts = sorted(nfts.values(), key=lambda x: x.transfers, reverse=True)
            res.nft_holdings_count = sum(max(n.net_count, 0) for n in res.nfts)
            res.real_nft_holdings_count = sum(
                max(n.net_count, 0) for n in res.nfts if not n.is_scam
            )

        res.status = "ok"
    except Exception as e:  # noqa: BLE001
        log.exception("scan failed for %s on %s", address, chain.name)
        res.error = f"{type(e).__name__}: {e}"
        res.status = "error"
    return res


def scan_wallet_on_chain_rpc(
    client: RpcClient,
    chain: Chain,
    address: str,
) -> ChainResult:
    """Limited-mode scan: native balance saja via JSON-RPC.

    Dipakai kalau chain tidak punya Etherscan-compat free API.
    Tidak ada tx_count, token, NFT — semua field-nya 0/empty.
    """
    res = ChainResult(
        chain_id=chain.id,
        chain_name=chain.name,
        address=address,
        native_symbol=chain.symbol,
    )
    try:
        wei = client.get_balance_wei(address)
        res.native_raw = wei
        res.native = f"{_wei_to_decimal(wei, chain.decimals):f}"
        res.status = "ok"
    except Exception as e:  # noqa: BLE001
        log.exception("RPC scan failed for %s on %s", address, chain.name)
        res.error = f"{type(e).__name__}: {e}"
        res.status = "error"
    return res


def apply_native_usd(result: ChainResult, native_usd_price: float | None) -> None:
    if native_usd_price is None:
        return
    native_dec = Decimal(result.native or "0")
    result.native_usd = float(native_dec * Decimal(str(native_usd_price)))


def apply_token_usd(
    result: ChainResult,
    prices_by_contract: dict[str, float],
    include_scam: bool = False,
) -> None:
    """Set usd_price + usd_value tiap token, lalu hitung token_usd total dan total_usd."""
    token_total = 0.0
    for t in result.tokens:
        if t.balance_raw <= 0:
            continue
        if t.is_scam and not include_scam:
            continue
        price = prices_by_contract.get(t.contract.lower())
        if price is None or price <= 0:
            continue
        try:
            balance_dec = Decimal(t.balance or "0")
        except Exception:  # noqa: BLE001
            continue
        usd_value = float(balance_dec * Decimal(str(price)))
        t.usd_price = price
        t.usd_value = usd_value
        token_total += usd_value
    result.token_usd = token_total
    nat = result.native_usd or 0.0
    result.total_usd = nat + token_total
