"""Unit test client tanpa hit jaringan — pakai mock session."""

from __future__ import annotations

from cekwallet.etherscan import make_legacy_client, make_v2_client


class _Resp:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self):
        return self._payload


class _Session:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, dict(params or {})))
        return self.responses.pop(0)


def test_v2_get_balance_wei():
    sess = _Session([_Resp({"status": "1", "message": "OK", "result": "12345"})])
    c = make_v2_client(api_key="X", chain_id=1, rate_delay=0, session=sess)
    assert c.get_balance_wei("0xabc") == 12345
    assert sess.calls[0][1]["chainid"] == 1
    assert sess.calls[0][1]["apikey"] == "X"
    assert sess.calls[0][1]["action"] == "balance"


def test_legacy_no_chainid_param():
    sess = _Session([_Resp({"status": "1", "message": "OK", "result": "99"})])
    c = make_legacy_client(
        api_key="K", base_url="https://api.bscscan.com/api",
        rate_delay=0, session=sess,
    )
    assert c.get_balance_wei("0xabc") == 99
    url, params = sess.calls[0]
    assert url == "https://api.bscscan.com/api"
    assert "chainid" not in params
    assert params["apikey"] == "K"


def test_paginate_stops_when_short_page():
    rows = [{"hash": str(i)} for i in range(2)]
    sess = _Session([_Resp({"status": "1", "message": "OK", "result": rows})])
    c = make_v2_client(api_key="X", chain_id=1, rate_delay=0, session=sess)
    out = c.list_txs("0xabc", max_pages=3)
    assert len(out) == 2
    assert len(sess.calls) == 1


def test_no_transactions_found_returns_empty():
    sess = _Session(
        [_Resp({"status": "0", "message": "No transactions found", "result": []})]
    )
    c = make_v2_client(api_key="X", chain_id=1, rate_delay=0, session=sess)
    assert c.list_txs("0xabc") == []
