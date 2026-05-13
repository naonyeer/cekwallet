"""Tulis laporan: per-wallet JSON, summary CSV, dan ringkasan console."""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable
from pathlib import Path

from .scanner import ChainResult


def write_wallet_json(out_dir: Path, address: str, results: list[ChainResult]) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{address.lower()}.json"
    payload = {
        "address": address,
        "chains": [r.to_dict() for r in results],
    }
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return path


def write_summary_csv(out_dir: Path, rows: Iterable[ChainResult]) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "summary.csv"
    headers = [
        "address",
        "chain_id",
        "chain_name",
        "native_symbol",
        "native",
        "native_usd",
        "tx_count",
        "tx_in",
        "tx_out",
        "internal_tx_count",
        "nonzero_token_count",
        "nft_holdings_count",
        "first_tx_at",
        "last_tx_at",
        "total_usd",
        "error",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for r in rows:
            w.writerow({h: getattr(r, h, "") for h in headers})
    return path


def write_tokens_csv(out_dir: Path, rows: Iterable[ChainResult]) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "tokens.csv"
    headers = [
        "address",
        "chain_id",
        "chain_name",
        "contract",
        "symbol",
        "name",
        "decimals",
        "balance",
        "balance_raw",
        "transfers",
        "first_seen",
        "last_seen",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for r in rows:
            for t in r.tokens:
                w.writerow(
                    {
                        "address": r.address,
                        "chain_id": r.chain_id,
                        "chain_name": r.chain_name,
                        "contract": t.contract,
                        "symbol": t.symbol,
                        "name": t.name,
                        "decimals": t.decimals,
                        "balance": t.balance,
                        "balance_raw": t.balance_raw,
                        "transfers": t.transfers,
                        "first_seen": t.first_seen,
                        "last_seen": t.last_seen,
                    }
                )
    return path


def write_nfts_csv(out_dir: Path, rows: Iterable[ChainResult]) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "nfts.csv"
    headers = [
        "address",
        "chain_id",
        "chain_name",
        "contract",
        "symbol",
        "name",
        "standard",
        "net_count",
        "transfers",
        "first_seen",
        "last_seen",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for r in rows:
            for n in r.nfts:
                w.writerow(
                    {
                        "address": r.address,
                        "chain_id": r.chain_id,
                        "chain_name": r.chain_name,
                        "contract": n.contract,
                        "symbol": n.symbol,
                        "name": n.name,
                        "standard": n.standard,
                        "net_count": n.net_count,
                        "transfers": n.transfers,
                        "first_seen": n.first_seen,
                        "last_seen": n.last_seen,
                    }
                )
    return path
