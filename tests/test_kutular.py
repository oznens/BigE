"""Renkli kutu tespit testleri."""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz.kutular import kutulari_bul, _kumeler, _renk_ata, _guc_puani


def _df(closes: list[float], hacimler: list[float] | None = None) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=len(closes), freq="h", tz="UTC")
    c = np.array(closes, dtype=float)
    v = np.array(hacimler, dtype=float) if hacimler else np.ones(len(closes))
    return pd.DataFrame({
        "open": c, "high": c * 1.002, "low": c * 0.998, "close": c, "volume": v
    }, index=idx)


def test_kumeleme_yakin_fiyatlar_birlesir():
    pivlar = [(0, 100.0, "L"), (5, 100.5, "L"), (10, 150.0, "H"), (15, 149.8, "H")]
    kumeler = _kumeler(pivlar, tolerans=0.02)
    assert len(kumeler) == 2, "Yakın fiyatlar 2 kümeye ayrılmalı"
    boyutlar = sorted(len(k) for k in kumeler)
    assert boyutlar == [2, 2]


def test_kumeleme_uzak_fiyatlar_ayrilir():
    pivlar = [(0, 100.0, "L"), (5, 200.0, "H"), (10, 300.0, "H")]
    kumeler = _kumeler(pivlar, tolerans=0.01)
    assert len(kumeler) == 3, "Uzak fiyatlar ayrı kümelerde olmalı"


def test_guc_puani_araliklarda():
    g = _guc_puani(dokunus=5, son_idx=99, toplam_bar=100, hacim_orani=2.0)
    assert 0 <= g <= 100
    assert g > 90, "Çok dokunuş + taze + yüksek hacim → yüksek puan"
    g2 = _guc_puani(dokunus=2, son_idx=0, toplam_bar=100, hacim_orani=0.5)
    assert g2 < g, "Az dokunuş + eski + düşük hacim → düşük puan"


def test_renk_destek_guclu_mavi():
    assert _renk_ata("Destek", guc=70, mesafe_yuzde=-5) == "Mavi"
    assert _renk_ata("Destek", guc=50, mesafe_yuzde=-5) == "Yeşil"
    assert _renk_ata("Destek", guc=30, mesafe_yuzde=-5) == "Turuncu"


def test_renk_direnc_mor_kirmizi():
    assert _renk_ata("Direnç", guc=60, mesafe_yuzde=5) == "Mor"
    assert _renk_ata("Direnç", guc=85, mesafe_yuzde=5) == "Mor"   # yakın güçlü → Mor
    assert _renk_ata("Direnç", guc=30, mesafe_yuzde=5) == "Turuncu"
    assert _renk_ata("Direnç", guc=60, mesafe_yuzde=30) == "Kırmızı"  # uzak → Kırmızı


def test_destek_direnc_tespiti():
    """Fiyatın altındaki bölge Destek, üstündeki Direnç olmalı."""
    # 100 seviyesinde defalarca dip, 150'de defalarca tepe, son fiyat ~125
    seviyeler = []
    for _ in range(4):
        seviyeler += list(np.linspace(125, 100, 8))   # dip 100
        seviyeler += list(np.linspace(100, 150, 8))    # tepe 150
        seviyeler += list(np.linspace(150, 125, 8))    # 125'e dön
    df = _df(seviyeler)
    kutular = kutulari_bul(df, n=3, tolerans=0.02, min_dokunus=2)
    assert kutular, "En az bir kutu bulunmalı"
    for k in kutular:
        if k.merkez < df["close"].iloc[-1]:
            assert k.tip == "Destek"
        else:
            assert k.tip == "Direnç"


def test_bos_veri():
    df = _df([100, 101, 100])
    assert kutulari_bul(df, n=5) == []
