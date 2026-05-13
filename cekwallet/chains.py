"""Daftar EVM chain.

Setiap chain punya `v2_status` yang menentukan rute scan:
- "v2_free"  : didukung Etherscan V2 di tier gratis (1 key, default route).
- "v2_paid"  : ada di V2, tapi butuh paid plan. Pakai legacy explorer API
               (BSCScan / Basescan / dll) dengan API key terpisah.
- "v1_only"  : belum di V2; pakai explorer asli pakai API key sendiri.

`legacy_api_base` + `legacy_api_key_env` dipakai untuk chain v2_paid / v1_only:
- legacy_api_base    : base URL untuk Etherscan-family v1 API (mis. https://api.bscscan.com/api).
                       Sebagian besar block explorer Etherscan-family memakai shape API yang sama.
- legacy_api_key_env : nama env var yang menyimpan API key (mis. BSCSCAN_API_KEY).
                       Kalau env var kosong, chain di-skip dengan reason yang jelas.
- legacy_supports_v2 : kalau True, key Etherscan V2 utama (ETHERSCAN_API_KEY) bisa dipakai
                       untuk chain ini KALAU user upgrade plan. Default False.

`cg` adalah id CoinGecko untuk native USD price; None kalau tidak dipakai.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

V2Status = Literal["v2_free", "v2_paid", "v1_only"]


@dataclass(frozen=True)
class Chain:
    id: int
    name: str
    symbol: str
    decimals: int
    cg: str | None
    explorer: str
    launch_year: int
    v2_status: V2Status
    legacy_api_base: str | None = None
    legacy_api_key_env: str | None = None
    # DexScreener slug untuk pricing ERC-20 (None = tidak didukung DexScreener)
    dex_slug: str | None = None


CHAINS: list[Chain] = [
    # === V2 free tier ===
    Chain(1, "Ethereum", "ETH", 18, "ethereum", "https://etherscan.io",
          2015, "v2_free", dex_slug="ethereum"),
    Chain(137, "Polygon PoS", "POL", 18, "polygon-ecosystem-token",
          "https://polygonscan.com", 2020, "v2_free", dex_slug="polygon"),
    Chain(100, "Gnosis", "xDAI", 18, "xdai", "https://gnosisscan.io",
          2018, "v2_free", dex_slug="gnosischain"),
    Chain(42161, "Arbitrum One", "ETH", 18, "ethereum", "https://arbiscan.io",
          2021, "v2_free", dex_slug="arbitrum"),
    Chain(59144, "Linea", "ETH", 18, "ethereum", "https://lineascan.build",
          2023, "v2_free", dex_slug="linea"),
    Chain(81457, "Blast", "ETH", 18, "ethereum", "https://blastscan.io",
          2024, "v2_free", dex_slug="blast"),
    Chain(5000, "Mantle", "MNT", 18, "mantle", "https://mantlescan.xyz",
          2023, "v2_free", dex_slug="mantle"),
    Chain(252, "Fraxtal", "frxETH", 18, "frax-ether", "https://fraxscan.com",
          2024, "v2_free", dex_slug="fraxtal"),
    Chain(480, "World Chain", "ETH", 18, "ethereum", "https://worldscan.org",
          2024, "v2_free", dex_slug="worldchain"),
    Chain(146, "Sonic", "S", 18, "sonic-3", "https://sonicscan.org",
          2024, "v2_free", dex_slug="sonic"),
    Chain(130, "Unichain", "ETH", 18, "ethereum", "https://uniscan.xyz",
          2025, "v2_free", dex_slug="unichain"),
    Chain(2741, "Abstract", "ETH", 18, "ethereum", "https://abscan.org",
          2025, "v2_free", dex_slug="abstract"),
    Chain(80094, "Berachain", "BERA", 18, "berachain-bera",
          "https://berascan.com", 2025, "v2_free", dex_slug="berachain"),
    Chain(33139, "ApeChain", "APE", 18, "apecoin", "https://apescan.io",
          2024, "v2_free", dex_slug="apechain"),
    Chain(42220, "Celo", "CELO", 18, "celo", "https://celoscan.io",
          2020, "v2_free", dex_slug="celo"),
    Chain(1284, "Moonbeam", "GLMR", 18, "moonbeam",
          "https://moonscan.io", 2022, "v2_free", dex_slug="moonbeam"),
    Chain(1285, "Moonriver", "MOVR", 18, "moonriver",
          "https://moonriver.moonscan.io", 2021, "v2_free", dex_slug="moonriver"),
    Chain(204, "opBNB", "BNB", 18, "binancecoin",
          "https://opbnbscan.com", 2023, "v2_free", dex_slug="opbnb"),
    Chain(167000, "Taiko", "ETH", 18, "ethereum",
          "https://taikoscan.io", 2024, "v2_free", dex_slug="taiko"),
    Chain(50, "XDC", "XDC", 18, "xdce-crowd-sale",
          "https://xdcscan.com", 2019, "v2_free", dex_slug="xdc"),
    Chain(199, "BitTorrent Chain", "BTT", 18, "bittorrent",
          "https://bttcscan.com", 2022, "v2_free", dex_slug="bittorrent"),
    Chain(1329, "Sei (EVM)", "SEI", 18, "sei-network",
          "https://seitrace.com", 2024, "v2_free", dex_slug="seiv2"),
    Chain(999, "HyperEVM", "HYPE", 18, "hyperliquid",
          "https://hyperevmscan.io", 2025, "v2_free", dex_slug="hyperevm"),
    Chain(747474, "Katana", "ETH", 18, "ethereum",
          "https://katanascan.com", 2025, "v2_free", dex_slug="katana"),
    Chain(988, "Stable", "USDT0", 18, "tether",
          "https://stablescan.io", 2025, "v2_free"),
    Chain(9745, "Plasma", "XPL", 18, "plasma",
          "https://plasmascan.to", 2025, "v2_free", dex_slug="plasma"),
    Chain(4352, "Memecore", "M", 18, None,
          "https://memecorescan.io", 2025, "v2_free"),

    # === V2 paid tier (perlu paid plan kalau pakai V2; fallback ke explorer legacy) ===
    Chain(56, "BNB Smart Chain", "BNB", 18, "binancecoin", "https://bscscan.com",
          2020, "v2_paid",
          legacy_api_base="https://api.bscscan.com/api",
          legacy_api_key_env="BSCSCAN_API_KEY",
          dex_slug="bsc"),
    Chain(10, "Optimism", "ETH", 18, "ethereum", "https://optimistic.etherscan.io",
          2021, "v2_paid",
          legacy_api_base="https://api-optimistic.etherscan.io/api",
          legacy_api_key_env="OPTIMISTIC_ETHERSCAN_API_KEY",
          dex_slug="optimism"),
    Chain(8453, "Base", "ETH", 18, "ethereum", "https://basescan.org",
          2023, "v2_paid",
          legacy_api_base="https://api.basescan.org/api",
          legacy_api_key_env="BASESCAN_API_KEY",
          dex_slug="base"),
    Chain(43114, "Avalanche C-Chain", "AVAX", 18, "avalanche-2",
          "https://snowtrace.io", 2020, "v2_paid",
          legacy_api_base="https://api.snowtrace.io/api",
          legacy_api_key_env="SNOWTRACE_API_KEY",
          dex_slug="avalanche"),

    # === Belum/tidak ada di V2 (pakai explorer asli) ===
    Chain(250, "Fantom Opera", "FTM", 18, "fantom", "https://ftmscan.com",
          2019, "v1_only",
          legacy_api_base="https://api.ftmscan.com/api",
          legacy_api_key_env="FTMSCAN_API_KEY",
          dex_slug="fantom"),
    Chain(25, "Cronos", "CRO", 18, "crypto-com-chain", "https://cronoscan.com",
          2021, "v1_only",
          legacy_api_base="https://api.cronoscan.com/api",
          legacy_api_key_env="CRONOSCAN_API_KEY",
          dex_slug="cronos"),
    Chain(42170, "Arbitrum Nova", "ETH", 18, "ethereum",
          "https://nova.arbiscan.io", 2022, "v1_only",
          legacy_api_base="https://api-nova.arbiscan.io/api",
          legacy_api_key_env="NOVA_ARBISCAN_API_KEY",
          dex_slug="arbitrumnova"),
    Chain(324, "zkSync Era", "ETH", 18, "ethereum",
          "https://era.zksync.network", 2023, "v1_only",
          legacy_api_base="https://api-era.zksync.network/api",
          legacy_api_key_env="ZKSYNC_ERA_API_KEY",
          dex_slug="zksync"),
    Chain(1101, "Polygon zkEVM", "ETH", 18, "ethereum",
          "https://zkevm.polygonscan.com", 2023, "v1_only",
          legacy_api_base="https://api-zkevm.polygonscan.com/api",
          legacy_api_key_env="ZKEVM_POLYGONSCAN_API_KEY",
          dex_slug="polygonzkevm"),
    Chain(534352, "Scroll", "ETH", 18, "ethereum", "https://scrollscan.com",
          2023, "v1_only",
          legacy_api_base="https://api.scrollscan.com/api",
          legacy_api_key_env="SCROLLSCAN_API_KEY",
          dex_slug="scroll"),
    Chain(1868, "Soneium", "ETH", 18, "ethereum",
          "https://soneium.blockscout.com", 2025, "v1_only",
          legacy_api_base="https://soneium.blockscout.com/api",
          legacy_api_key_env=None,  # Blockscout: no key required for basic queries
          dex_slug="soneium"),
    Chain(57073, "Ink", "ETH", 18, "ethereum",
          "https://explorer.inkonchain.com", 2024, "v1_only",
          legacy_api_base="https://explorer.inkonchain.com/api",
          legacy_api_key_env=None,
          dex_slug="ink"),
]


def get_chain(chain_id: int) -> Chain | None:
    return next((c for c in CHAINS if c.id == chain_id), None)


def chains_by_ids(ids: list[int] | None) -> list[Chain]:
    if not ids:
        return list(CHAINS)
    out = []
    for cid in ids:
        c = get_chain(cid)
        if c is not None:
            out.append(c)
    return out
