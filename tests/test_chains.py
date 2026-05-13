from cekwallet.chains import CHAINS, chains_by_ids, get_chain


def test_chains_unique_ids():
    ids = [c.id for c in CHAINS]
    assert len(ids) == len(set(ids)), "duplicate chainid"


def test_get_chain():
    eth = get_chain(1)
    assert eth is not None and eth.symbol == "ETH"
    assert eth.v2_status == "v2_free"
    assert get_chain(999_999_999) is None


def test_chains_by_ids_default_returns_all():
    assert chains_by_ids(None) == list(CHAINS)
    assert chains_by_ids([]) == list(CHAINS)


def test_chains_by_ids_filter():
    out = chains_by_ids([1, 8453, 56])
    assert [c.id for c in out] == [1, 8453, 56]


def test_chains_by_ids_skips_unknown():
    out = chains_by_ids([1, 12345])
    assert [c.id for c in out] == [1]


def test_v2_paid_has_free_fallback_or_rpc():
    """Setiap v2_paid chain wajib punya minimal free_api_base ATAU rpc_url."""
    paid = [c for c in CHAINS if c.v2_status == "v2_paid"]
    assert paid
    for c in paid:
        assert c.free_api_base or c.rpc_url, (
            f"{c.name} tidak punya free_api_base maupun rpc_url"
        )


def test_v1_only_has_free_fallback_or_rpc():
    """Setiap v1_only chain wajib punya minimal free_api_base ATAU rpc_url."""
    v1 = [c for c in CHAINS if c.v2_status == "v1_only"]
    assert v1
    for c in v1:
        assert c.free_api_base or c.rpc_url, (
            f"{c.name} tidak punya free_api_base maupun rpc_url"
        )


def test_bsc_has_rpc_only_fallback():
    """BSC tidak punya free Blockscout, jadi minimal rpc_url."""
    bsc = get_chain(56)
    assert bsc is not None
    assert bsc.v2_status == "v2_paid"
    assert bsc.rpc_url is not None


def test_base_optimism_avalanche_have_free_api():
    """Base/Optimism/Avalanche harus punya free_api_base (Blockscout/Routescan)."""
    for cid in (8453, 10, 43114):
        c = get_chain(cid)
        assert c is not None
        assert c.free_api_base, f"{c.name} missing free_api_base"


def test_fantom_zksync_scroll_have_free_api():
    """Fantom (FtmScout), zkSync (Blockscout), Scroll (Blockscout) harus free."""
    for cid in (250, 324, 534352):
        c = get_chain(cid)
        assert c is not None
        assert c.free_api_base, f"{c.name} missing free_api_base"
