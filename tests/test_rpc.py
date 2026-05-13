"""Unit tests for the minimal JSON-RPC client."""

from __future__ import annotations

import pytest

from cekwallet.rpc import RpcClient, RpcError


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

    def post(self, url, json=None, timeout=None):
        self.calls.append((url, dict(json or {})))
        return self.responses.pop(0)


def test_rpc_get_balance_hex():
    sess = _Session([_Resp({"jsonrpc": "2.0", "id": 1, "result": "0x6d2d58d83d066"})])
    c = RpcClient("https://bsc-dataseed.binance.org/", rate_delay=0, session=sess)
    assert c.get_balance_wei("0xabc") == 0x6D2D58D83D066
    url, body = sess.calls[0]
    assert url == "https://bsc-dataseed.binance.org/"
    assert body["method"] == "eth_getBalance"
    assert body["params"] == ["0xabc", "latest"]


def test_rpc_get_balance_zero():
    sess = _Session([_Resp({"jsonrpc": "2.0", "id": 1, "result": "0x0"})])
    c = RpcClient("https://rpc.example/", rate_delay=0, session=sess)
    assert c.get_balance_wei("0xabc") == 0


def test_rpc_raises_on_error():
    sess = _Session(
        [_Resp({"jsonrpc": "2.0", "id": 1, "error": {"code": -32000, "message": "boom"}})]
    )
    c = RpcClient("https://rpc.example/", rate_delay=0, session=sess)
    with pytest.raises(RpcError):
        c.get_balance_wei("0xabc")


def test_rpc_requires_url():
    with pytest.raises(ValueError):
        RpcClient("")
