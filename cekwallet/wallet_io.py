"""Load + validasi daftar alamat wallet."""

from __future__ import annotations

import re
from pathlib import Path

_HEX_ADDR = re.compile(r"^0x[0-9a-fA-F]{40}$")


def is_valid_address(addr: str) -> bool:
    return bool(_HEX_ADDR.match(addr.strip()))


def load_wallets(path: str | Path) -> list[str]:
    """Baca file alamat (1 per baris, '#' komen). Dedup + lowercase."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Wallets file not found: {p}")
    seen: set[str] = set()
    out: list[str] = []
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # buang inline komen
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        if not is_valid_address(line):
            raise ValueError(f"Invalid address: {line!r} in {p}")
        low = line.lower()
        if low in seen:
            continue
        seen.add(low)
        out.append(low)
    return out
