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

from .chains import CHAINS, Chain, chains_by_ids
from .dex_pricer import fetch_token_usd_prices
from .etherscan import ScanClient, make_legacy_client, make_v2_client
from .prices import fetch_usd_prices
from .reporter import write_nfts_csv, write_summary_csv, write_tokens_csv, write_wallet_json
from .scanner import (
    ChainResult,
    apply_native_usd,
    apply_token_usd,
    scan_wallet_on_chain,
)
from .wallet_io import load_wallets

console = Console()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="cekwallet",
        description=(
            "Cek isi wallet EVM lama (Ethereum, BSC, Base, Polygon, dll) "
            "via Etherscan V2 + explorer per-chain."
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
            "Default: semua chain yang didukung."
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
        help="Skip lookup harga USD native (CoinGecko).",
    )
    p.add_argument(
        "--no-token-usd", action="store_true",
        help="Skip lookup harga ERC-20 (DexScreener).",
    )
    p.add_argument(
        "--show-scam", action="store_true",
        help="Tampilkan juga token/NFT yang dianggap scam di console output.",
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
    table = Table(title="Chain yang dikenali")
    table.add_column("chainid", justify="right")
    table.add_column("Name")
    table.add_column("Symbol")
    table.add_column("Since", justify="right")
    table.add_column("V2 status")
    table.add_column("Legacy API key env")
    for c in CHAINS:
        table.add_row(
            str(c.id), c.name, c.symbol, str(c.launch_year),
            c.v2_status, c.legacy_api_key_env or "—",
        )
    console.print(table)


def _make_client_for_chain(
    chain: Chain,
    v2_key: str,
    rate_delay: float,
    timeout: float,
) -> tuple[ScanClient | None, str, str | None]:
    """Return (client, route, skip_reason).

    Route:
      - "v2"           : pakai V2 unified (free)
      - "legacy:<env>" : pakai explorer asli
      - "skipped"      : tidak ada key/route yang tersedia
    """
    if chain.v2_status == "v2_free":
        return (
            make_v2_client(v2_key, chain.id, rate_delay=rate_delay, timeout=timeout),
            "v2",
            None,
        )

    # v2_paid / v1_only → coba legacy explorer
    if not chain.legacy_api_base:
        return None, "skipped", "Tidak ada API base untuk chain ini"
    key_env = chain.legacy_api_key_env
    key = os.environ.get(key_env, "").strip() if key_env else ""
    if key_env and not key:
        reason = (
            f"Butuh ${key_env} di .env (free tier Etherscan V2 belum support chain ini)"
        )
        if chain.v2_status == "v2_paid":
            reason = (
                f"Butuh paid Etherscan V2 atau ${key_env} di .env"
            )
        return None, "skipped", reason
    client = make_legacy_client(
        api_key=key or "YourApiKeyToken",  # Blockscout explorers accept dummy
        base_url=chain.legacy_api_base,
        rate_delay=rate_delay,
        timeout=timeout,
    )
    route = f"legacy:{key_env or 'nokey'}"
    return client, route, None


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
    v2_key = os.environ.get("ETHERSCAN_API_KEY", "").strip()
    if not v2_key:
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

    # Native USD prices via CoinGecko
    native_prices: dict[str, float] = {}
    if not args.no_usd:
        cg_ids = sorted({c.cg for c in chains if c.cg})
        cg_key = os.environ.get("COINGECKO_API_KEY", "").strip() or None
        try:
            native_prices = fetch_usd_prices(cg_ids, api_key=cg_key, timeout=timeout)
        except Exception as e:  # noqa: BLE001
            logging.warning("Gagal ambil harga native USD: %s", e)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    wallets_dir = out_dir / "wallets"

    all_results: list[ChainResult] = []
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
            wallet_results: list[ChainResult] = []
            for chain in chains:
                progress.update(task, description=f"{addr[:10]}… @ {chain.name}")
                client, route, skip_reason = _make_client_for_chain(
                    chain, v2_key, rate_delay, timeout
                )
                if client is None:
                    r = ChainResult(
                        chain_id=chain.id,
                        chain_name=chain.name,
                        address=addr,
                        native_symbol=chain.symbol,
                        route=route,
                        status="skipped",
                        skip_reason=skip_reason,
                    )
                else:
                    r = scan_wallet_on_chain(
                        client,
                        chain,
                        addr,
                        include_nft=not args.no_nft,
                        include_tx_history=not args.no_tx_history,
                        max_tx_pages=args.max_tx_pages,
                        max_token_pages=args.max_token_pages,
                    )
                    r.route = route

                if chain.cg and chain.cg in native_prices:
                    apply_native_usd(r, native_prices[chain.cg])

                # ERC-20 USD pricing via DexScreener
                if (
                    not args.no_token_usd
                    and r.status == "ok"
                    and chain.dex_slug
                    and r.tokens
                ):
                    contracts = [
                        t.contract for t in r.tokens
                        if t.balance_raw > 0 and (args.show_scam or not t.is_scam)
                    ]
                    if contracts:
                        try:
                            prices = fetch_token_usd_prices(chain.dex_slug, contracts)
                            apply_token_usd(r, prices, include_scam=args.show_scam)
                        except Exception as e:  # noqa: BLE001
                            logging.warning(
                                "DexScreener gagal di %s: %s", chain.name, e
                            )

                # Kalau native_usd ada tapi token_usd belum dihitung, set total_usd = native_usd saja
                if r.total_usd is None and r.native_usd is not None:
                    r.total_usd = r.native_usd

                wallet_results.append(r)
                all_results.append(r)
                progress.advance(task)
            write_wallet_json(wallets_dir, addr, wallet_results)

    summary_csv = write_summary_csv(out_dir, all_results)
    tokens_csv = write_tokens_csv(out_dir, all_results)
    nfts_csv = write_nfts_csv(out_dir, all_results)

    _print_top_table(all_results, show_scam=args.show_scam)
    _print_skipped_table(all_results)
    console.print(
        f"\n[green]Selesai![/green]\n"
        f"  Ringkasan: [cyan]{summary_csv}[/cyan]\n"
        f"  Tokens:    [cyan]{tokens_csv}[/cyan]\n"
        f"  NFT:       [cyan]{nfts_csv}[/cyan]\n"
        f"  Per-wallet JSON: [cyan]{wallets_dir}/[/cyan]"
    )
    return 0


def _print_top_table(results: list[ChainResult], show_scam: bool = False) -> None:
    interesting = [
        r for r in results
        if r.status == "ok"
        and (
            r.native_raw > 0
            or (r.nonzero_real_token_count if not show_scam else r.nonzero_token_count) > 0
            or (r.real_nft_holdings_count if not show_scam else r.nft_holdings_count) > 0
            or r.tx_count > 0
        )
    ]
    if not interesting:
        console.print("\n[yellow]Tidak ada aktivitas/saldo (non-scam) terdeteksi.[/yellow]")
        return
    interesting.sort(
        key=lambda r: (r.total_usd if r.total_usd is not None else 0.0, r.tx_count),
        reverse=True,
    )
    table = Table(title="Hasil chain dgn saldo/aktivitas")
    table.add_column("Wallet")
    table.add_column("Chain")
    table.add_column("Native", justify="right")
    table.add_column("Native USD", justify="right")
    table.add_column("Token USD", justify="right")
    table.add_column("Total USD", justify="right")
    table.add_column("Tx", justify="right")
    table.add_column("Real Tok", justify="right")
    table.add_column("Real NFT", justify="right")
    for r in interesting[:60]:
        native_usd = f"${r.native_usd:,.2f}" if r.native_usd is not None else "—"
        token_usd = f"${r.token_usd:,.2f}" if r.token_usd is not None else "—"
        total_usd = f"${r.total_usd:,.2f}" if r.total_usd is not None else "—"
        native = f"{float(r.native):.6f} {r.native_symbol}" if r.native_raw else "0"
        table.add_row(
            r.address,
            r.chain_name,
            native,
            native_usd,
            token_usd,
            total_usd,
            str(r.tx_count),
            str(r.nonzero_real_token_count),
            str(r.real_nft_holdings_count),
        )
    console.print(table)


def _print_skipped_table(results: list[ChainResult]) -> None:
    skipped = [r for r in results if r.status in ("skipped", "error")]
    if not skipped:
        return
    table = Table(title="Chain di-skip / error")
    table.add_column("Wallet")
    table.add_column("Chain")
    table.add_column("Status")
    table.add_column("Reason")
    for r in skipped:
        reason = r.skip_reason or (r.error or "")
        table.add_row(r.address, r.chain_name, r.status, reason[:80])
    console.print(table)


if __name__ == "__main__":
    sys.exit(main())
