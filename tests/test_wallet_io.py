from pathlib import Path

import pytest

from cekwallet.wallet_io import is_valid_address, load_wallets


def test_is_valid_address():
    assert is_valid_address("0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045")
    assert is_valid_address("0x" + "0" * 40)
    assert not is_valid_address("0x123")
    assert not is_valid_address("d8dA6BF26964aF9D7eEd9e03E53415D37aA96045")
    assert not is_valid_address("")


def test_load_wallets(tmp_path: Path):
    f = tmp_path / "w.txt"
    f.write_text(
        "# comment\n"
        "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045\n"
        "  0xD8DA6BF26964AF9D7EED9E03E53415D37AA96045  # dup\n"
        "\n"
        "0x0000000000000000000000000000000000000001 # second\n",
        encoding="utf-8",
    )
    out = load_wallets(f)
    assert out == [
        "0xd8da6bf26964af9d7eed9e03e53415d37aa96045",
        "0x0000000000000000000000000000000000000001",
    ]


def test_load_wallets_invalid(tmp_path: Path):
    f = tmp_path / "w.txt"
    f.write_text("not-an-address\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_wallets(f)


def test_load_wallets_missing(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_wallets(tmp_path / "nope.txt")
