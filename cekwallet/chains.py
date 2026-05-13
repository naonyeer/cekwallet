"""Daftar EVM chain yang didukung Etherscan V2 unified API.

Setiap chain punya:
- id        : chainid (param `chainid` di Etherscan V2)
- name      : nama yang ditampilkan
- symbol    : simbol native coin
- decimals  : decimals native coin (selalu 18 untuk semua EVM yang umum)
- cg        : id CoinGecko (untuk USD price), None kalau tidak dipakai
- explorer  : base URL block explorer (untuk link manusiawi)
- launch_year: tahun chain mulai aktif — sebagai info saja
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Chain:
    id: int
    name: str
    symbol: str
    decimals: int
    cg: str | None
    explorer: str
    launch_year: int


CHAINS: list[Chain] = [
    # 2015
    Chain(1, "Ethereum", "ETH", 18, "ethereum", "https://etherscan.io", 2015),
    # 2020
    Chain(56, "BNB Smart Chain", "BNB", 18, "binancecoin", "https://bscscan.com", 2020),
    Chain(137, "Polygon PoS", "POL", 18, "matic-network", "https://polygonscan.com", 2020),
    Chain(43114, "Avalanche C-Chain", "AVAX", 18, "avalanche-2", "https://snowtrace.io", 2020),
    Chain(250, "Fantom Opera", "FTM", 18, "fantom", "https://ftmscan.com", 2019),
    Chain(25, "Cronos", "CRO", 18, "crypto-com-chain", "https://cronoscan.com", 2021),
    Chain(100, "Gnosis", "xDAI", 18, "xdai", "https://gnosisscan.io", 2018),
    # 2021
    Chain(10, "Optimism", "ETH", 18, "ethereum", "https://optimistic.etherscan.io", 2021),
    Chain(42161, "Arbitrum One", "ETH", 18, "ethereum", "https://arbiscan.io", 2021),
    Chain(42170, "Arbitrum Nova", "ETH", 18, "ethereum", "https://nova.arbiscan.io", 2022),
    # 2022-2023
    Chain(324, "zkSync Era", "ETH", 18, "ethereum", "https://era.zksync.network", 2023),
    Chain(1101, "Polygon zkEVM", "ETH", 18, "ethereum", "https://zkevm.polygonscan.com", 2023),
    Chain(59144, "Linea", "ETH", 18, "ethereum", "https://lineascan.build", 2023),
    Chain(8453, "Base", "ETH", 18, "ethereum", "https://basescan.org", 2023),
    Chain(534352, "Scroll", "ETH", 18, "ethereum", "https://scrollscan.com", 2023),
    Chain(5000, "Mantle", "MNT", 18, "mantle", "https://mantlescan.xyz", 2023),
    # 2024
    Chain(81457, "Blast", "ETH", 18, "ethereum", "https://blastscan.io", 2024),
    Chain(252, "Fraxtal", "frxETH", 18, "frax-ether", "https://fraxscan.com", 2024),
    Chain(480, "World Chain", "ETH", 18, "ethereum", "https://worldscan.org", 2024),
    # 2024-2025
    Chain(146, "Sonic", "S", 18, "sonic-3", "https://sonicscan.org", 2024),
    Chain(2741, "Abstract", "ETH", 18, "ethereum", "https://abscan.org", 2025),
    Chain(1868, "Soneium", "ETH", 18, "ethereum", "https://soneium.blockscout.com", 2025),
    Chain(57073, "Ink", "ETH", 18, "ethereum", "https://explorer.inkonchain.com", 2024),
    Chain(80094, "Berachain", "BERA", 18, "berachain-bera", "https://berascan.com", 2025),
    Chain(33139, "ApeChain", "APE", 18, "apecoin", "https://apescan.io", 2024),
    Chain(130, "Unichain", "ETH", 18, "ethereum", "https://uniscan.xyz", 2025),
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
