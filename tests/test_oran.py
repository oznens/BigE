"""ALT/BTC göreceli güç testleri."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz.oran import _btc_paritesi, metin, GoreceliGuc


def test_btc_paritesi():
    assert _btc_paritesi("ETHUSDT") == "ETHBTC"
    assert _btc_paritesi("SOLUSDT") == "SOLBTC"
    assert _btc_paritesi("BTCUSDT") is None      # BTC'nin kendisi
    assert _btc_paritesi("ETHBTC") is None        # USDT değil


def test_metin_durumlar():
    g = GoreceliGuc("ETHBTC", 0.027, -8.5, "zayıflıyor")
    s = metin(g)
    assert "ZAYIFLIYOR" in s and "ETHBTC" in s and "-8.5" in s
    assert metin(None) == ""


def test_metin_gucleniyor():
    g = GoreceliGuc("SOLBTC", 0.0011, 12.0, "güçleniyor")
    assert "GÜÇLENIYOR" in metin(g)
