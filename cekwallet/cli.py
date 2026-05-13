"""CLI: cekwallet --wallets wallets.txt --out reports/"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table

from .chains import CHAINS, chains_by_ids
from .etherscan import EtherscanClient
from .prices import fetch_usd_prices
from .reporter import write_nfts_csv, write_summary_csv, write_tokens_csv, write_wallet_json
from .scanner import apply_usd, scan_wallet_on_chain
from .wallet_io import load_wallets

console = Console()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="cekwallet",
        description=(
            "Cek isi wallet EVM lama (Ethereum, BSC, Base, Polygon, dll) via Etherscan V2."
        ),
    )
    p.add_argument(
        "-w", "--wallets", default="wallets.txt",
        help="Path file daftar alamat (default: wallets.txt).",
    )
    p.add_argument(
        "-o", "--out", default="reports",
        help="Folder output (default: reports/).",
    )
    p.add_argument(
        "-c", "--chains", default="",
        help=(
            "Comma-separated chainid yang mau dicek. "
            "Default: semua chain yang didukung (lihat README)."
        ),
    )
    p.add_argument(
        "--no-nft", action="store_true",
        help="Skip pengecekan NFT (ERC-721 / ERC-1155).",
    )
    p.add_argument(
        "--no-tx-history", action="store_true",
        help="Skip enumerasi tx history (lebih cepat, tapi tx_count = 0).",
    )
    p.add_argument(
        "--no-usd", action="store_true",
        help="Skip lookup harga USD via CoinGecko.",
    )
    p.add_argument(
        "--max-tx-pages", type=int, default=10,
        help="Maks halaman tx (default 10 x 10000 = 100k tx).",
    )
    p.add_argument(
        "--max-token-pages", type=int, default=20,
        help="Maks halaman token transfer (default 20 x 10000).",
    )
    p.add_argument(
        "--list-chains", action="store_true",
        help="Tampilkan daftar chain yang didukung lalu keluar.",
    )
    p.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose logging.",
    )
    return p.parse_args(argv)


def _print_chain_list() -> None:
    table = Table(title="Supported chains (Etherscan V2)")
    table.add_column("chainid", justify="right")
    table.add_column("Name")
    table.add_column("Symbol")
    table.add_column("Since", justify="right")
    table.add_column("Explorer")
    for c in CHAINS:
        table.add_row(str(c.id), c.name, c.symbol, str(c.launch_year), c.explorer)
    console.print(table)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True, show_path=False)],
    )

    if args.list_chains:
        _print_chain_list()
        return 0

    load_dotenv()
    api_key = os.environ.get("ETHERSCAN_API_KEY", "").strip()
    if not api_key:
        console.print(
            "[red]ETHERSCAN_API_KEY tidak ditemukan.[/red] "
            "Salin .env.example ke .env dan isi API key dari https://etherscan.io/myapikey"
        )
        return 2

    try:
        rate_delay = float(os.environ.get("ETHERSCAN_RATE_DELAY", "0.22"))
        timeout = float(os.environ.get("HTTP_TIMEOUT", "30"))
    except ValueError:
        rate_delay, timeout = 0.22, 30.0

    try:
        wallets = load_wallets(args.wallets)
    except FileNotFoundError:
        console.print(
            f"[red]File wallet tidak ada:[/red] {args.wallets}. "
            "Salin wallets.example.txt ke wallets.txt dan isi alamatmu."
        )
        return 2
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        return 2

    if not wallets:
        console.print("[yellow]Tidak ada alamat di file wallet.[/yellow]")
        return 0

    chain_ids = [int(x) for x in args.chains.split(",") if x.strip()] if args.chains else None
    chains = chains_by_ids(chain_ids)
    if not chains:
        console.print("[red]Tidak ada chain valid.[/red]")
        return 2

    console.print(
        f"[bold]Scanning[/bold] {len(wallets)} wallet × {len(chains)} chain "
        f"= {len(wallets) * len(chains)} kombinasi"
    )

    client = EtherscanClient(api_key=api_key, rate_delay=rate_delay, timeout=timeout)

    # Harga USD untuk native coin
    prices: dict[str, float] = {}
    if not args.no_usd:
        cg_ids = sorted({c.cg for c in chains if c.cg})
        cg_key = os.environ.get("COINGECKO_API_KEY", "").strip() or None
        try:
            prices = fetch_usd_prices(cg_ids, api_key=cg_key, timeout=timeout)
        except Exception as e:  # noqa: BLE001
            logging.warning("Gagal ambil harga USD: %s", e)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    wallets_dir = out_dir / "wallets"

    all_results = []
    progress = Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TextColumn("•"),
        TimeElapsedColumn(),
        TextColumn("•"),
        TimeRemainingColumn(),
        console=console,
    )
    with progress:
        total = len(wallets) * len(chains)
        task = progress.add_task("Scanning", total=total)
        for addr in wallets:
            wallet_results = []
            for chain in chains:
                progress.update(task, description=f"{addr[:10]}… @ {chain.name}")
                r = scan_wallet_on_chain(
                    client,
                    chain,
                    addr,
                    include_nft=not args.no_nft,
                    include_tx_history=not args.no_tx_history,
                    max_tx_pages=args.max_tx_pages,
                    max_token_pages=args.max_token_pages,
                )
                if chain.cg and chain.cg in prices:
                    apply_usd(r, prices[chain.cg])
                wallet_results.append(r)
                all_results.append(r)
                progress.advance(task)
            write_wallet_json(wallets_dir, addr, wallet_results)

    summary_csv = write_summary_csv(out_dir, all_results)
    tokens_csv = write_tokens_csv(out_dir, all_results)
    nfts_csv = write_nfts_csv(out_dir, all_results)

    _print_top_table(all_results)
    console.print(
        f"\n[green]Selesai![/green]\n"
        f"  Ringkasan: [cyan]{summary_csv}[/cyan]\n"
        f"  Tokens:    [cyan]{tokens_csv}[/cyan]\n"
        f"  NFT:       [cyan]{nfts_csv}[/cyan]\n"
        f"  Per-wallet JSON: [cyan]{wallets_dir}/[/cyan]"
    )
    return 0


def _print_top_table(results) -> None:
    interesting = [
        r for r in results
        if r.native_raw > 0
        or r.nonzero_token_count > 0
        or r.nft_holdings_count > 0
        or r.tx_count > 0
    ]
    if not interesting:
        console.print("\n[yellow]Tidak ada aktivitas/saldo terdeteksi di semua kombinasi.[/yellow]")
        return
    interesting.sort(
        key=lambda r: (r.total_usd if r.total_usd is not None else 0.0, r.tx_count),
        reverse=True,
    )
    table = Table(title="Hasil (yang ada saldo/aktivitas)")
    table.add_column("Wallet")
    table.add_column("Chain")
    table.add_column("Native", justify="right")
    table.add_column("USD", justify="right")
    table.add_column("Tx", justify="right")
    table.add_column("Tokens≠0", justify="right")
    table.add_column("NFT", justify="right")
    for r in interesting[:50]:
        usd = f"${r.total_usd:,.2f}" if r.total_usd is not None else "—"
        native = f"{float(r.native):.6f} {r.native_symbol}" if r.native_raw else "0"
        table.add_row(
            r.address,
            r.chain_name,
            native,
            usd,
            str(r.tx_count),
            str(r.nonzero_token_count),
            str(r.nft_holdings_count),
        )
    console.print(table)


if __name__ == "__main__":
    sys.exit(main())
