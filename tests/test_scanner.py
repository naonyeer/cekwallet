from cekwallet.scanner import (
    ChainResult,
    _aggregate_nft_transfers,
    _aggregate_token_transfers,
    apply_native_usd,
    apply_token_usd,
)

ADDR = "0x1111111111111111111111111111111111111111"
OTHER = "0x2222222222222222222222222222222222222222"
CONTRACT = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"


def _tx(to, frm, value, ts=1_600_000_000, decimals=18, sym="USDC", name="USD Coin"):
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
    t = out[CONTRACT]
    assert t.transfers == 2
    assert t.balance_raw == 10**18 - 3 * 10**17
    assert t.is_scam is False
    assert t.first_seen and t.last_seen
    assert t.first_seen < t.last_seen


def test_aggregate_token_marks_scam_from_name():
    transfers = [
        _tx(ADDR, OTHER, 1, sym="$SHIB", name="Claim at shib-claim.live"),
    ]
    out = _aggregate_token_transfers(ADDR, transfers)
    t = out[CONTRACT]
    assert t.is_scam is True


def test_aggregate_nft_erc721_count():
    transfers = [
        _tx(ADDR, OTHER, 1, ts=1_600_000_000, sym="BAYC", name="Bored Ape"),
        _tx(ADDR, OTHER, 1, ts=1_650_000_000, sym="BAYC", name="Bored Ape"),
        _tx(OTHER, ADDR, 1, ts=1_700_000_000, sym="BAYC", name="Bored Ape"),
    ]
    out = _aggregate_nft_transfers(ADDR, transfers, "ERC-721")
    n = next(iter(out.values()))
    assert n.transfers == 3
    assert n.net_count == 1
    assert n.is_scam is False


def test_apply_native_usd():
    r = ChainResult(chain_id=1, chain_name="Ethereum", address=ADDR, native_symbol="ETH")
    r.native_raw = 2 * 10**18
    r.native = "2"
    apply_native_usd(r, native_usd_price=1500.0)
    assert r.native_usd == 3000.0


def test_apply_token_usd_skips_scam_and_zero():
    from cekwallet.scanner import TokenSummary
    r = ChainResult(chain_id=1, chain_name="Ethereum", address=ADDR, native_symbol="ETH")
    r.native = "1"
    r.native_usd = 2000.0
    real_tok = TokenSummary(
        contract="0xreal",
        symbol="DAI",
        name="Dai Stablecoin",
        decimals=18,
        balance_raw=10**18,
        balance="1",
        is_scam=False,
    )
    scam_tok = TokenSummary(
        contract="0xsca",
        symbol="$X",
        name="Claim at scam.live",
        decimals=18,
        balance_raw=10**18,
        balance="1",
        is_scam=True,
    )
    zero_tok = TokenSummary(
        contract="0xzero",
        symbol="ZRO",
        name="Zero",
        decimals=18,
        balance_raw=0,
        balance="0",
        is_scam=False,
    )
    r.tokens = [real_tok, scam_tok, zero_tok]
    prices = {"0xreal": 1.0, "0xsca": 999.0, "0xzero": 5.0}
    apply_token_usd(r, prices, include_scam=False)
    assert real_tok.usd_value == 1.0
    assert scam_tok.usd_value is None
    assert zero_tok.usd_value is None
    assert r.token_usd == 1.0
    assert r.total_usd == 2001.0


def test_apply_token_usd_include_scam():
    from cekwallet.scanner import TokenSummary
    r = ChainResult(chain_id=1, chain_name="Ethereum", address=ADDR, native_symbol="ETH")
    r.native_usd = 0.0
    scam_tok = TokenSummary(
        contract="0xsca",
        symbol="$X",
        name="Claim at scam.live",
        decimals=18,
        balance_raw=10**18,
        balance="2",
        is_scam=True,
    )
    r.tokens = [scam_tok]
    apply_token_usd(r, {"0xsca": 3.0}, include_scam=True)
    assert scam_tok.usd_value == 6.0
    assert r.token_usd == 6.0
