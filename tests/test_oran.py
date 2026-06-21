"""ALT/BTC göreceli güç testleri."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz.oran import _btc_paritesi, metin, GoreceliGuc, rasyo


def test_btc_paritesi():
    assert _btc_paritesi("ETHUSDT") == "ETHBTC"
    assert _btc_paritesi("SOLUSDT") == "SOLBTC"
    assert _btc_paritesi("BTCUSDT") is None      # BTC → altın benchmark
    assert _btc_paritesi("ETHBTC") is None        # USDT değil


def test_metin_durumlar():
    g = GoreceliGuc("ETHBTC", "BTC", 0.027, -8.5, "zayıflıyor")
    s = metin(g)
    assert "ZAYIFLIYOR" in s and "ETHBTC" in s and "-8.5" in s
    assert "BTC'ye karşı" in s
    assert metin(None) == ""


def test_metin_btc_altin():
    g = GoreceliGuc("BTC/Altın", "Altın", 15.2, -12.0, "zayıflıyor")
    s = metin(g)
    assert "Altın'a karşı" in s and "ZAYIFLIYOR" in s


def test_rasyo_genel(monkeypatch):
    """rasyo(A, B) genel oranı: A güçlenirse 'güçleniyor'."""
    import pandas as pd
    import numpy as np
    from miraz import oran

    def sahte_indir(sembol, interval, gun):
        idx = pd.date_range("2025-01-01", periods=60, freq="D")
        if sembol == "ETHUSDT":
            kapanis = np.linspace(100, 200, 60)   # A yükseliyor
        else:
            kapanis = np.full(60, 100.0)          # B sabit
        return pd.DataFrame({"close": kapanis}, index=idx)

    monkeypatch.setattr(oran.veri, "indir", sahte_indir)
    g = rasyo("ETHUSDT", "SOLUSDT", n=30)
    assert g is not None
    assert g.durum == "güçleniyor"
    assert g.parite == "ETH/SOL" and g.benchmark == "SOL"
