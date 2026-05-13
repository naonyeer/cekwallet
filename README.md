# cekwallet

Bot untuk cek isi wallet EVM lama (dompet jaman dulu) di banyak chain sekaligus:
Ethereum, BSC, Base, Polygon, Arbitrum, Optimism, Avalanche, Fantom, zkSync,
Linea, Scroll, Mantle, Blast, Celo, Moonbeam, Sonic, Berachain, dan lainnya
(36 chain ter-pre-configured).

Pakai **Etherscan V2 unified API** untuk chain yang didukung free tier, dan
**otomatis fallback ke Blockscout / Routescan / public RPC** (semua gratis, tanpa key)
untuk chain yang butuh paid plan di V2 atau belum ada di V2.

Untuk tiap kombinasi `wallet × chain`:

- Saldo native (ETH / BNB / MATIC / dll) + estimasi USD via CoinGecko.
- Total tx (in/out/internal) + tanggal tx pertama & terakhir.
- Token ERC-20 yang pernah lewat — net balance hasil agregasi `tokentx`.
- NFT ERC-721 + ERC-1155 — net count + jumlah transfer.
- **Filter scam otomatis**: token/NFT dengan URL di nama atau keyword
  phishing (claim, redeem, eligible, dll) ditandai `is_scam=True`.
- **Pricing ERC-20** via DexScreener (gratis, tanpa key) untuk token non-scam.
- `total_usd` per chain = native USD + token USD (non-scam).

Output:

- `reports/summary.csv` — 1 baris per `wallet × chain`.
- `reports/tokens.csv` — semua token ERC-20 yang pernah ditemukan (incl `is_scam`, `usd_value`).
- `reports/nfts.csv` — semua koleksi NFT yang pernah ditemukan.
- `reports/wallets/<address>.json` — detail penuh per wallet.

## Keamanan

**Bot ini cuma butuh alamat publik** (`0x…`).
**JANGAN PERNAH** masukkan private key atau seed phrase ke `wallets.txt`,
ke `.env`, atau kemana pun. Semua data di-fetch hanya dari block explorer publik.

⚠️ **Token-token di wallet lama biasanya banyak yang scam phishing airdrop**
(nama token mengandung URL "claim reward" / "swap within 7 days"). Bot ini
otomatis menandai mereka — **JANGAN klik link, JANGAN approve kontrak,
JANGAN swap**. Mereka dibuat untuk mencuri wallet kamu.

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
   untuk semua chain yang ada di tier free V2. Free tier: 5 calls/sec, 100k/hari.
2. (Opsional, jarang perlu) tambah API key per-explorer untuk chain yang
   sekarang butuh paid plan di Etherscan V2. Tidak wajib — bot otomatis
   pakai Blockscout / Routescan / RPC yang gratis. Lihat `.env.example`
   untuk daftar lengkap kalau kamu memang punya akun paid.
3. Salin contoh konfigurasi:

   ```bash
   cp .env.example .env
   cp wallets.example.txt wallets.txt
   ```

4. Edit `.env` → isi `ETHERSCAN_API_KEY` (dan key explorer per-chain kalau mau).
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

# Skip lookup harga ERC-20 (lebih cepat, total_usd = native saja)
cekwallet --no-token-usd

# Tampilkan juga token/NFT yang dianggap scam di tabel ringkasan
cekwallet --show-scam

# Lihat daftar chain + status V2 / legacy key env
cekwallet --list-chains
```

Setelah selesai cek `reports/` — buka `summary.csv` di spreadsheet, atau
`reports/wallets/<address>.json` untuk detail.

## Cara kerja per chain

`cekwallet --list-chains` memunculkan status tiap chain:

- **v2_free** → di-scan via Etherscan V2 dengan `ETHERSCAN_API_KEY`.
  Mayoritas chain (Ethereum, Polygon, Arbitrum One, Linea, Mantle, Blast,
  Celo, Moonbeam, opBNB, Taiko, XDC, dll).
- **v2_paid** (BSC, Base, Optimism, Avalanche) — Etherscan V2 sekarang butuh
  paid plan. Bot otomatis fallback ke alternatif gratis:
  - **Base** → `base.blockscout.com` (Blockscout, full data)
  - **Optimism** → `api.routescan.io/.../10/etherscan` (Routescan, full data)
  - **Avalanche** → `api.routescan.io/.../43114/etherscan` (Routescan, full data)
  - **BSC** → `bsc-dataseed.binance.org` (public RPC, **native balance saja**)
- **v1_only** (belum di V2) — sama, bot otomatis fallback:
  - **Fantom** → `ftmscout.com` (Blockscout, full data)
  - **zkSync Era** → `zksync.blockscout.com` (Blockscout, full data)
  - **Scroll** → `blockscout.scroll.io` (Blockscout, full data)
  - **Soneium** → `soneium.blockscout.com` (Blockscout, full data)
  - **Ink** → `explorer.inkonchain.com` (Blockscout, full data)
  - **Cronos / Arbitrum Nova / Polygon zkEVM** → public RPC (native saja)

Routing priority untuk chain non-`v2_free`:
  1. Legacy key (`BSCSCAN_API_KEY`/dll) kalau di-set di `.env`
  2. Free Etherscan-compat (Blockscout / Routescan) kalau ada
  3. Public RPC (limited: native balance only)
  4. Skipped

Kolom `route` di `summary.csv` memuat path mana yang dipakai
(`v2` / `free:<domain>` / `rpc:<domain>` / `legacy:ENVKEY`).
Chain di mode `rpc:` cuma punya native balance — tx_count, tokens, NFT semuanya 0.

## Pricing

- **Native** (ETH / BNB / MATIC / dll) via [CoinGecko Simple Price API](https://docs.coingecko.com/reference/simple-price). Gratis tanpa key (rate limit 10-30 req/min), opsional `COINGECKO_API_KEY` (Demo) untuk naikkan rate.
- **ERC-20** via [DexScreener `tokens/v1`](https://docs.dexscreener.com/api/reference) — gratis, tanpa key, 300 req/min. Bot pilih pair dengan liquidity USD tertinggi sebagai patokan harga.
- Token yang ditandai scam **tidak** dihitung ke `total_usd` (kecuali pakai `--show-scam`).
- Token tanpa pair DEX (atau belum listing) skip harga; balance tetap tampil.

## Catatan teknis

- Etherscan V2 free tier punya rate limit 5 rps. Default delay 0.22s
  (~4.5 rps); bisa di-tune via `ETHERSCAN_RATE_DELAY` di `.env`.
- Saldo ERC-20 dihitung dari agregasi `tokentx` (in − out). Untuk akurasi
  presisi, kombinasikan dengan `tokenbalance` per kontrak — helper
  `get_token_balance` tersedia di `ScanClient`.
- Heuristik scam tidak sempurna — gunakan `--show-scam` kalau curiga ada
  false-positive. False-positive yang sering kena: token beneran yang
  pakai `$` panjang atau emoji di nama.
- Untuk Blockscout-style explorer (Soneium, Ink), API key tidak wajib.

## Lisensi

MIT.
