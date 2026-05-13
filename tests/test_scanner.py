from cekwallet.scanner import (
    ChainResult,
    _aggregate_nft_transfers,
    _aggregate_token_transfers,
    apply_usd,
)

ADDR = "0x1111111111111111111111111111111111111111"
OTHER = "0x2222222222222222222222222222222222222222"
CONTRACT = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"


def _tx(to: str, frm: str, value: int, ts: int = 1_600_000_000, decimals: int = 18, sym="USDC", name="USD Coin"):
    return {
        "to": to,
        "from": frm,
        "value": str(value),
        "timeStamp": str(ts),
        "tokenDecimal": str(decimals),
        "tokenSymbol": sym,
        "tokenName": name,
        "contractAddress": CONTRACT,
    }


def test_aggregate_token_balance_in_minus_out():
    transfers = [
        _tx(ADDR, OTHER, 10**18, ts=1_600_000_000),
        _tx(OTHER, ADDR, 3 * 10**17, ts=1_700_000_000),
    ]
    out = _aggregate_token_transfers(ADDR, transfers)
    assert CONTRACT in out
    t = out[CONTRACT]
    assert t.transfers == 2
    assert t.balance_raw == 10**18 - 3 * 10**17  # 0.7 USDC
    assert t.first_seen and t.last_seen
    assert t.first_seen < t.last_seen


def test_aggregate_nft_erc721_count():
    transfers = [
        _tx(ADDR, OTHER, 1, ts=1_600_000_000, sym="BAYC", name="Bored Ape"),
        _tx(ADDR, OTHER, 1, ts=1_650_000_000, sym="BAYC", name="Bored Ape"),
        _tx(OTHER, ADDR, 1, ts=1_700_000_000, sym="BAYC", name="Bored Ape"),
    ]
    out = _aggregate_nft_transfers(ADDR, transfers, "ERC-721")
    n = next(iter(out.values()))
    assert n.transfers == 3
    assert n.net_count == 1  # 2 in - 1 out


def test_apply_usd():
    r = ChainResult(chain_id=1, chain_name="Ethereum", address=ADDR, native_symbol="ETH")
    r.native_raw = 2 * 10**18
    r.native = "2"
    apply_usd(r, native_usd_price=1500.0)
    assert r.native_usd == 3000.0
    assert r.total_usd == 3000.0


def test_apply_usd_none():
    r = ChainResult(chain_id=1, chain_name="Ethereum", address=ADDR, native_symbol="ETH")
    apply_usd(r, native_usd_price=None)
    assert r.native_usd is None
    assert r.total_usd is None
