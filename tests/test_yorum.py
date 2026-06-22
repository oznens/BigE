"""Miraz yorumu üretici testleri — @tradermiraz tarzı plan metni."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz.yorum import miraz_yorum, _fmt, _VADE


def test_short_plan_temel_ogeler():
    y = miraz_yorum("BTCUSDT", "4h", "Short", giris=78000, stop=79500,
                    hedef=74100, rr=2.6, pattern="Bat",
                    konseptler=["Shear", "Root"], kategori="Trade")
    m = y["metin"]
    assert "Bitcoin | 4h — Orta Vade Plan" in y["baslik"]
    assert "aşağı yönlü" in m                     # short bias
    assert "Mor kutu" in m                         # strateji bölgesi dili
    assert "Bat" in m and "PRZ" in m               # harmonik patern
    assert "yeşil daire" in m                      # tetik
    assert "Geçersizlik" in m and "79.500$" in m   # stop seviyesi
    assert "2.6R" in m                             # R/R
    assert "Yatırım tavsiyesi değildir" in m       # uyarı


def test_long_plan_yon_ve_bolge():
    y = miraz_yorum("ETHUSDT", "1h", "Long", giris=1700, stop=1660,
                    hedef=1820, rr=3.0, konseptler=["Root"], kategori="Watch")
    m = y["metin"]
    assert "yukarı yönlü" in m
    assert "Mavi kutu" in m                         # long talep bölgesi
    assert "mavi kutudan alım" in m
    assert "altında hacimli kapanışlar" in m        # long geçersizlik yönü
    assert "İzleme" in y["ozet"]


def test_pattern_yoksa_klasik_yapi():
    y = miraz_yorum("SOLUSDT", "30m", "Short", giris=150, stop=155, hedef=140,
                    rr=2.0, konseptler=[], kategori="Skip")
    m = y["metin"]
    assert "çift tepe" in m.lower()                 # patern yoksa S/R+kırılım
    assert _VADE["30m"] in y["baslik"]


def test_konsept_sozluk_eslemesi():
    y = miraz_yorum("BTCUSDT", "1h", "Short", giris=100, stop=105, hedef=90,
                    konseptler=[{"isim": "Cavity"}, {"isim": "Strike"}],
                    kategori="Trade")
    m = y["metin"]
    assert "dengesizlik (FVG)" in m                 # Cavity
    assert "likidite" in m or "stop-avı" in m        # Strike


def test_fmt_fiyat_bicimleme():
    assert _fmt(78000) == "78.000$"
    assert _fmt(1.2345) == "1.23$"
    assert _fmt(0.00012300) == "0.000123$"
    assert _fmt(None) == "—"


def test_yorum_alanlari_dolu():
    y = miraz_yorum("BTCUSDT", "2h", "Long", giris=60000, stop=58000,
                    hedef=66000, rr=3.0, kategori="Trade")
    assert y["baslik"] and y["ozet"] and y["mantra"]
    assert isinstance(y["govde"], list) and len(y["govde"]) >= 4
    assert "Kısa-Orta Vade" in y["baslik"]
