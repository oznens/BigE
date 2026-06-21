"""Temas davranışı istatistiği testleri."""

import sys
from pathlib import Path
from dataclasses import dataclass

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz.temas import (temas_olaylari, temas_analizi, senaryo_temas,
                         TemasSonuc)


def _df(bars):
    """bars: [(low, high, close), ...] → OHLCV df."""
    low = np.array([b[0] for b in bars], dtype=float)
    high = np.array([b[1] for b in bars], dtype=float)
    close = np.array([b[2] for b in bars], dtype=float)
    return pd.DataFrame({"open": close, "high": high, "low": low,
                         "close": close, "volume": np.ones(len(bars))})


# ---------------------------------------------------------------------------
# Olay tespiti
# ---------------------------------------------------------------------------

def test_tek_tepki():
    """Fiyat üstte → bölgeye girer → üstte kapanır = 1 tepki."""
    # bölge [95, 97]; başla 100 üstte, dal 96 (girer), topla 99 (üst kapanış)
    df = _df([(100, 101, 100), (95.5, 98, 96), (98, 100, 99)])
    olaylar = temas_olaylari(df, 95, 97)
    assert len(olaylar) == 1
    assert olaylar[0].tip == "tepki"


def test_tek_kirilma():
    """Fiyat üstte → bölgeye girer → alt sınır altında kapanır = kırılma."""
    df = _df([(100, 101, 100), (95.5, 98, 96), (93, 96, 94)])
    olaylar = temas_olaylari(df, 95, 97)
    assert len(olaylar) == 1
    assert olaylar[0].tip == "kırılma"


def test_icerde_suren():
    """Bölgeye girip içeride kalırsa = içeride (açık olay)."""
    df = _df([(100, 101, 100), (95.5, 98, 96), (95.2, 96.5, 96)])
    olaylar = temas_olaylari(df, 95, 97)
    assert len(olaylar) == 1
    assert olaylar[0].tip == "içeride"


def test_iki_tepki_sonra_kirilma():
    """İki kez tepki verip üçüncüde kırılan bölge."""
    df = _df([
        (100, 101, 100),       # üstte
        (95.5, 98, 96),        # girer
        (98, 100, 99),         # tepki (üst kapanış) → ust
        (96, 99, 97.5),        # tekrar girer (low 96 ≤ 97) ... close 97.5 > ust → tepki
        (96.2, 99, 98),        # üstte (close 98)
        (95.5, 97, 96),        # girer 3. kez
        (92, 95.5, 93),        # kırılma
    ])
    olaylar = temas_olaylari(df, 95, 97)
    tipler = [o.tip for o in olaylar]
    assert tipler.count("tepki") == 2
    assert tipler.count("kırılma") == 1
    assert tipler[-1] == "kırılma"


def test_hic_dokunmamis():
    """Fiyat hep bölgenin üstünde → olay yok."""
    df = _df([(100, 102, 101), (101, 103, 102), (100, 102, 101)])
    olaylar = temas_olaylari(df, 95, 97)
    assert olaylar == []


# ---------------------------------------------------------------------------
# Analiz / istatistik
# ---------------------------------------------------------------------------

def test_analiz_tepki_orani():
    df = _df([
        (100, 101, 100), (95.5, 98, 96), (98, 100, 99),   # tepki
        (96, 99, 98), (95.5, 97, 96), (92, 95.5, 93),     # kırılma
    ])
    t = temas_analizi(df, 95, 97)
    assert t.tepki == 1 and t.kirilma == 1
    assert t.tepki_orani == 0.5
    assert t.son_davranis == "kırılma"


def test_analiz_son_kirilma_negatif_guven():
    """Son davranış kırılma → güçlü negatif güven etkisi."""
    df = _df([(100, 101, 100), (95.5, 98, 96), (92, 95.5, 93)])
    t = temas_analizi(df, 95, 97)
    assert t.son_davranis == "kırılma"
    assert t.guven_etkisi == -12.0


def test_analiz_taze_bolge_pozitif():
    """Hiç test edilmemiş taze bölge → küçük pozitif."""
    df = _df([(100, 102, 101), (101, 103, 102)])
    t = temas_analizi(df, 95, 97)
    assert t.toplam == 0
    assert t.guven_etkisi == 3.0
    assert "taze" in t.metin


def test_analiz_hep_tepki_pozitif():
    """Sürekli tepki veren (kırılmamış) bölge → pozitif güven."""
    df = _df([
        (100, 101, 100), (95.5, 98, 96), (98, 100, 99),   # tepki 1
        (96, 99, 98), (95.5, 97, 96.5), (98, 100, 99),    # tepki 2
    ])
    t = temas_analizi(df, 95, 97)
    assert t.kirilma == 0 and t.tepki == 2
    assert t.tepki_orani == 1.0
    assert t.guven_etkisi > 0


def test_alt_ust_ters_duzeltilir():
    """alt > ust verilirse otomatik düzeltilir."""
    df = _df([(100, 101, 100), (95.5, 98, 96), (98, 100, 99)])
    t1 = temas_analizi(df, 95, 97)
    t2 = temas_analizi(df, 97, 95)      # ters
    assert t1.tepki == t2.tepki
    assert t2.alt == 95 and t2.ust == 97


# ---------------------------------------------------------------------------
# senaryo_temas kısa yolu
# ---------------------------------------------------------------------------

@dataclass
class _Sen:
    bolge_alt: float = None
    bolge_ust: float = None


def test_senaryo_temas():
    df = _df([(100, 101, 100), (95.5, 98, 96), (98, 100, 99)])
    s = _Sen(bolge_alt=95, bolge_ust=97)
    t = senaryo_temas(s, df)
    assert t is not None and t.tepki == 1


def test_senaryo_temas_bolge_yoksa_none():
    df = _df([(100, 101, 100)])
    s = _Sen(bolge_alt=None, bolge_ust=None)
    assert senaryo_temas(s, df) is None
