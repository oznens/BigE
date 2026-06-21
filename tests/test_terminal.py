"""TerminalMiraz görsel paneli — smoke testleri (PNG üretimi)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz.radar import RadarRapor, RadarSatiri
from miraz.terminal import panel_ciz, _bildirimler, _fmt


def _ornek_rapor():
    return RadarRapor(satirlar=[
        RadarSatiri(symbol="BTCUSDT", interval="4h", fiyat=65000,
                    kategori="Trade", kalite="A", guven=82, yon="Long",
                    giris=64000, hedef=66000, rr=1.0, not_="mavi daire",
                    taraf="Long", stop=63000),
        RadarSatiri(symbol="ETHUSDT", interval="4h", fiyat=3500,
                    kategori="Watch", kalite="B", guven=68, yon="Nötr",
                    giris=3450, hedef=3380, rr=1.0, not_="bearish diverj.",
                    taraf="Short", stop=3520),
        RadarSatiri(symbol="SOLUSDT", interval="4h", fiyat=150,
                    kategori="Elenen", kalite="C", guven=55, yon="Long",
                    giris=None, hedef=None, rr=None,
                    not_="HTF aşağı", taraf="Long", stop=None),
    ])


def test_panel_ciz_dosya_uretir(tmp_path):
    dosya = tmp_path / "terminal.png"
    yol = panel_ciz(_ornek_rapor(), dosya=dosya)
    assert Path(yol).exists()
    assert dosya.stat().st_size > 1000      # gerçek bir PNG


def test_panel_bos_rapor(tmp_path):
    dosya = tmp_path / "bos.png"
    panel_ciz(RadarRapor(), dosya=dosya)
    assert dosya.exists()


def test_bildirimler_radar_fallback():
    # portföy yokken Trade/Watch satırları bildirime düşer
    rapor = _ornek_rapor()
    b = _bildirimler(None, rapor.satirlar)
    semboller = [x[0] for x in b]
    assert "BTCUSDT" in semboller and "ETHUSDT" in semboller
    assert "SOLUSDT" not in semboller       # Elenen bildirime düşmez


def test_fmt_hassasiyet():
    assert _fmt(None) == "—"
    assert _fmt(65000).startswith("65,000")
    assert _fmt(0.00012345).count("0") >= 3   # kuruş-altı hassas
