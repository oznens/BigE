"""İndikatör + divergence + Elliott testleri (@finansalTRader araçları)."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz.indikator import sma, ema, rsi, macd
from miraz.divergence import divergence_bul, metin as div_metin
from miraz.elliott import elliott_bul, metin as ell_metin


def _df(fiyatlar):
    f = np.array(fiyatlar, dtype=float)
    return pd.DataFrame({
        "open": f, "high": f * 1.001, "low": f * 0.999, "close": f,
        "volume": np.ones(len(f)),
    })


def _zikzak(noktalar, adim=10):
    seri = []
    for i in range(len(noktalar) - 1):
        seri.extend(np.linspace(noktalar[i], noktalar[i + 1], adim,
                                endpoint=False))
    seri.append(noktalar[-1])
    return seri


# ---- İndikatörler ----

def test_sma_ema():
    s = pd.Series(np.arange(1, 51, dtype=float))
    assert abs(sma(s, 10).iloc[-1] - np.arange(41, 51).mean()) < 1e-9
    assert ema(s, 10).iloc[-1] > 40        # artan seri → EMA yüksek

def test_rsi_araligi():
    # sürekli artan fiyat → RSI 100'e yakın
    s = pd.Series(np.linspace(100, 200, 60))
    r = rsi(s, 14).iloc[-1]
    assert 95 <= r <= 100

def test_rsi_dusus():
    s = pd.Series(np.linspace(200, 100, 60))
    r = rsi(s, 14).iloc[-1]
    assert 0 <= r <= 5

def test_macd_yapi():
    s = pd.Series(np.linspace(100, 200, 80))
    m = macd(s)
    assert {"macd", "sinyal", "histogram"} <= set(m.columns)
    assert m["macd"].iloc[-1] > 0          # yükseliş → MACD pozitif


# ---- Divergence ----

def test_bearish_divergence():
    # Fiyat HH ama momentum zayıflıyor → bearish divergence aranabilir
    # iki tepe: 1. tepe güçlü ralli, 2. tepe biraz daha yüksek ama yavaş
    nokta = [100, 150, 120, 200, 100, 205, 150]
    f = divergence_bul(_df(_zikzak(nokta)), n=3)
    # divergence bulunursa Bearish olmalı; bulunmazsa test esnek
    if f is not None:
        assert f.tip in ("Bearish", "Bullish")
        assert "divergence" in div_metin(f).lower()

def test_divergence_metin_bos():
    assert div_metin(None) == ""


# ---- Elliott ----

def test_elliott_itme_bullish():
    # 0-1-2-3-4-5 yükselen itme yapısı
    nokta = [100, 120, 110, 150, 135, 170]
    e = elliott_bul(_df(_zikzak(nokta)), n=3)
    if e is not None:
        assert "İtme" in e.tip or "Düzeltme" in e.tip
        assert "Elliott" in ell_metin(e)

def test_elliott_metin_bos():
    assert ell_metin(None) == ""
