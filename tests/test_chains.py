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


def test_v2_paid_has_legacy_fallback():
    paid = [c for c in CHAINS if c.v2_status == "v2_paid"]
    assert paid
    for c in paid:
        assert c.legacy_api_base, f"{c.name} missing legacy_api_base"
        assert c.legacy_api_key_env, f"{c.name} missing legacy_api_key_env"


def test_v1_only_has_legacy_base():
    v1 = [c for c in CHAINS if c.v2_status == "v1_only"]
    assert v1
    for c in v1:
        assert c.legacy_api_base, f"{c.name} missing legacy_api_base"
