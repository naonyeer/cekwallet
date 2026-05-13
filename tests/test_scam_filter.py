from cekwallet.scam_filter import is_scam_token


def test_real_tokens_pass():
    assert not is_scam_token("USDC", "USD Coin")
    assert not is_scam_token("DAI", "Dai Stablecoin")
    assert not is_scam_token("WETH", "Wrapped Ether")
    assert not is_scam_token("LINK", "ChainLink Token")
    assert not is_scam_token("ARB", "Arbitrum")
    assert not is_scam_token("USDe", "USDe")


def test_url_in_name_is_scam():
    assert is_scam_token("SHIB", "[ t.ly/uSHIB ] $SHIB REWARD POOL")
    assert is_scam_token("USD0", "WWW.TETHER.WS Visit to claim reward !")
    assert is_scam_token("⭐Airdrop", "⭐Airdrop: solshiba .live")
    assert is_scam_token("DRIFT", "Bridge at https://driftsprotocol.xyz/ $Drift")


def test_claim_keyword_is_scam():
    assert is_scam_token("BLAST", "Code H7P6V on blast-claim.finance to Claim BIast Token")
    assert is_scam_token("X", "Eligible holders verify via http://bad.example")


def test_emoji_is_scam():
    assert is_scam_token("ETH", "✅ Free ETH reward")
    assert is_scam_token("X", "🎁 You won the airdrop")


def test_homograph_is_scam():
    assert is_scam_token("ꓴꓢꓓС", "ꓴꓢꓓС")  # USDC look-alike


def test_symbol_with_space_is_scam():
    assert is_scam_token("5ETH at [web3eth.vip]", "wENA")


def test_dollar_prefix_long_symbol_is_scam():
    assert is_scam_token("$claimstuff", "Cool stuff")


def test_real_dollar_short_symbol_passes():
    # Beberapa token beneran pakai $ tapi pendek; jangan flag
    assert not is_scam_token("$PEPE", "Pepe")
