"""Heuristik untuk identifikasi scam / phishing dust token.

Wallet lama biasanya kebanjiran "airdrop" yang sebenarnya phishing — token-nya
sengaja dibikin biar muncul di explorer dengan nama berisi URL "claim reward"
supaya korban klik. Bot ini menandai token yang match heuristik tersebut
dengan `is_scam=True`.

Heuristik (jangan ada false-negative parah, false-positive kecil OK):

- Nama atau symbol mengandung URL (`http`, `t.ly`, `www.`, atau TLD umum scam).
- Mengandung emoji whitelist (⭐, ✅, ❗, 🎁, …) — proyek beneran jarang pakai.
- Mengandung kata kunci instruksi (`claim`, `redeem`, `swap within`, `bridge at`,
  `visit`, `verify`, `eligible`, `airdrop:`).
- Symbol mengandung spasi (proyek beneran jarang).
- Symbol/nama mengandung huruf Cyrillic/look-alike (ꓴꓢꓓС) — homograph attack.

Pemakai bisa override via `--show-scam` (CLI) atau set `is_scam=False` manual.
"""

from __future__ import annotations

import re

URL_RE = re.compile(
    r"(?:https?://|www\.|t\.ly|t\.co|bit\.ly|tinyurl|t\.me)|"
    r"\.(?:com|net|org|io|co|xyz|finance|app|live|vip|ws|to|me|info|gg|world)\b",
    re.IGNORECASE,
)

EMOJI_FLAGS = ("⭐", "✅", "❗", "🎁", "🔥", "💎", "🎉", "🚀", "🏆", "🎯", "⚠")

SCAM_KEYWORDS = (
    "claim",
    "redeem",
    "swap within",
    "swap before",
    "bridge at",
    "bridge to",
    "visit",
    "verify",
    "eligible",
    "airdrop:",
    "reward pool",
    "code ",
    "use ",
    "free $",
    "winner",
    "you won",
    "you are",
    "you have",
    "voucher",
    "promo",
    "giveaway",
)

# Karakter look-alike Cyrillic / Latin extended yang sering muncul di scam
LOOKALIKE_CHARS = set("АВЕКМНОРСТХаеорсухꓴꓢꓓСԁ")


def _has_lookalike(s: str) -> bool:
    return any(ch in LOOKALIKE_CHARS for ch in s)


def is_scam_token(symbol: str, name: str) -> bool:
    """Return True kalau token kemungkinan scam/phishing dust."""
    sym = symbol or ""
    nm = name or ""
    blob = f"{sym} {nm}".lower()

    # URL/domain di nama → hampir pasti scam
    if URL_RE.search(blob):
        return True

    # Emoji marker
    if any(e in blob for e in EMOJI_FLAGS):
        return True

    # Keyword instruksi
    if any(kw in blob for kw in SCAM_KEYWORDS):
        return True

    # Symbol panjang dengan spasi (mis. "5ETH at [...]")
    if " " in sym.strip():
        return True

    # Karakter look-alike (homograph attack)
    if _has_lookalike(sym) or _has_lookalike(nm):
        return True

    # "*" atau "$" prefix mencurigakan kalau symbol panjang
    return sym.strip().startswith(("*", "$")) and len(sym) > 5
