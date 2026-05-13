from cekwallet.chains import CHAINS, chains_by_ids, get_chain


def test_chains_unique_ids():
    ids = [c.id for c in CHAINS]
    assert len(ids) == len(set(ids)), "duplicate chainid"


def test_get_chain():
    eth = get_chain(1)
    assert eth is not None and eth.symbol == "ETH"
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
