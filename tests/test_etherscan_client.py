"""Unit test client tanpa hit jaringan — pakai requests-style mock session."""

from __future__ import annotations

from cekwallet.etherscan import EtherscanClient


class _Resp:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self):
        return self._payload


class _Session:
    def __init__(self, responses: list[_Resp]):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, dict(params or {})))
        return self.responses.pop(0)


def test_get_balance_wei():
    sess = _Session([_Resp({"status": "1", "message": "OK", "result": "12345"})])
    c = EtherscanClient(api_key="X", rate_delay=0, session=sess)
    assert c.get_balance_wei(1, "0xabc") == 12345
    assert sess.calls[0][1]["chainid"] == 1
    assert sess.calls[0][1]["apikey"] == "X"
    assert sess.calls[0][1]["action"] == "balance"


def test_paginate_stops_when_short_page():
    rows = [{"hash": str(i)} for i in range(2)]
    sess = _Session([_Resp({"status": "1", "message": "OK", "result": rows})])
    c = EtherscanClient(api_key="X", rate_delay=0, session=sess)
    out = c.list_txs(1, "0xabc", max_pages=3)
    assert len(out) == 2
    # Should only have made 1 call (short page exits loop)
    assert len(sess.calls) == 1


def test_no_transactions_found_returns_empty():
    sess = _Session(
        [_Resp({"status": "0", "message": "No transactions found", "result": []})]
    )
    c = EtherscanClient(api_key="X", rate_delay=0, session=sess)
    assert c.list_txs(1, "0xabc") == []


def test_balancemulti_chunked():
    addrs = [f"0x{i:040x}" for i in range(25)]
    sess = _Session(
        [
            _Resp(
                {
                    "status": "1",
                    "message": "OK",
                    "result": [{"account": a, "balance": "1"} for a in addrs[:20]],
                }
            ),
            _Resp(
                {
                    "status": "1",
                    "message": "OK",
                    "result": [{"account": a, "balance": "2"} for a in addrs[20:]],
                }
            ),
        ]
    )
    c = EtherscanClient(api_key="X", rate_delay=0, session=sess)
    out = c.get_balances_wei(1, addrs)
    assert len(out) == 25
    assert out[addrs[0]] == 1
    assert out[addrs[-1]] == 2
