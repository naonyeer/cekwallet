# cekwallet

Bot untuk cek isi wallet EVM lama (dompet jaman dulu) di banyak chain sekaligus:
Ethereum, BSC, Base, Polygon, Arbitrum, Optimism, Avalanche, Fantom, zkSync, Linea,
Scroll, Mantle, Blast, dan lainnya. Pakai **Etherscan V2 unified API** — cukup 1 API key.

Untuk tiap kombinasi `wallet × chain`, bot ngumpulin:

- Saldo native (ETH / BNB / MATIC / dll) + estimasi USD via CoinGecko.
- Total transaksi (in/out/internal) + tanggal tx pertama & terakhir.
- Token ERC-20 yang pernah lewat — net balance hasil agregasi transfer log.
- NFT ERC-721 + ERC-1155 — net count hasil agregasi transfer log.

Hasil disimpan jadi:

- `reports/summary.csv` — 1 baris per `wallet × chain`.
- `reports/tokens.csv` — semua token ERC-20 yang pernah ditemukan.
- `reports/nfts.csv` — semua koleksi NFT yang pernah ditemukan.
- `reports/wallets/<address>.json` — detail penuh per wallet.

## Keamanan

**Bot ini cuma butuh alamat publik** (`0x…`).
**JANGAN PERNAH** masukkan private key atau seed phrase ke `wallets.txt`,
ke `.env`, atau kemana pun. Semua data di-fetch hanya dari block explorer publik.

## Install

```bash
git clone https://github.com/naonyeer/cekwallet.git
cd cekwallet
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

Butuh Python 3.10+.

## Setup

1. Daftar API key Etherscan di https://etherscan.io/myapikey — 1 key dipakai
   untuk semua chain (Etherscan V2). Free tier: 5 calls/sec, 100k/hari.
2. (Opsional) daftar [CoinGecko Demo](https://www.coingecko.com/en/developers/dashboard)
   buat naikkan rate limit harga.
3. Salin contoh konfigurasi:

   ```bash
   cp .env.example .env
   cp wallets.example.txt wallets.txt
   ```

4. Edit `.env` → isi `ETHERSCAN_API_KEY`.
5. Edit `wallets.txt` → 1 alamat per baris, `#` untuk komentar.

## Pakai

```bash
# Scan semua chain yang didukung
cekwallet

# Hanya chain tertentu (chainid)
cekwallet --chains 1,56,8453,42161

# Skip NFT (lebih cepat kalau wallet padat ERC-721)
cekwallet --no-nft

# Skip enumerasi tx history (hanya saldo + token + NFT)
cekwallet --no-tx-history

# Lihat daftar chain yang didukung
cekwallet --list-chains
```

Setelah selesai cek `reports/` — buka `summary.csv` di spreadsheet, atau
`reports/wallets/<address>.json` untuk detail.

## Daftar chain default

Berikut chain yang di-scan kalau `--chains` tidak diset (semua via Etherscan V2):

| chainid | Chain               | Native |
|--------:|---------------------|:------:|
| 1       | Ethereum            | ETH    |
| 56      | BNB Smart Chain     | BNB    |
| 137     | Polygon PoS         | POL    |
| 43114   | Avalanche C-Chain   | AVAX   |
| 250     | Fantom Opera        | FTM    |
| 25      | Cronos              | CRO    |
| 100     | Gnosis              | xDAI   |
| 10      | Optimism            | ETH    |
| 42161   | Arbitrum One        | ETH    |
| 42170   | Arbitrum Nova       | ETH    |
| 324     | zkSync Era          | ETH    |
| 1101    | Polygon zkEVM       | ETH    |
| 59144   | Linea               | ETH    |
| 8453    | Base                | ETH    |
| 534352  | Scroll              | ETH    |
| 5000    | Mantle              | MNT    |
| 81457   | Blast               | ETH    |
| 252     | Fraxtal             | frxETH |
| 480     | World Chain         | ETH    |
| 146     | Sonic               | S      |
| 2741    | Abstract            | ETH    |
| 1868    | Soneium             | ETH    |
| 57073   | Ink                 | ETH    |
| 80094   | Berachain           | BERA   |
| 33139   | ApeChain            | APE    |
| 130     | Unichain            | ETH    |

Jalankan `cekwallet --list-chains` untuk daftar lengkap dari binary kamu.

## Catatan teknis

- Etherscan V2 punya rate limit 5 rps di free tier. Default delay 0.22s
  (~4.5 rps) — bisa diatur via `ETHERSCAN_RATE_DELAY` di `.env`.
- Saldo ERC-20 dihitung dari agregasi `tokentx` (transfer log: in − out).
  Untuk akurasi 100% kamu bisa kombinasikan dengan `--max-token-pages` lebih
  besar. Untuk wallet dengan ribuan token, pertimbangkan `--no-nft` agar cepat.
- USD value sementara hanya menghitung **native coin**, belum ERC-20.
  Untuk pricing ERC-20 perlu integrasi DEX/aggregator API; bisa ditambahkan
  belakangan.
- Beberapa chain di tabel di atas tidak ada di "2019", tapi disertakan karena
  bisa jadi alamat lama kamu juga muncul di chain baru lewat airdrop/migrasi.

## Lisensi

MIT.
