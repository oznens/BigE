"""Terminal Dashboard (rich) testleri — terminalMiraz canlı pano.

Görsel çıktıyı bayt bayt doğrulamak yerine, panonun hatasız üretildiğini ve
beklenen metinleri (sembol, bucket başlığı, durum) içerdiğini kontrol ederiz.
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rich.console import Console

from miraz import dashboard as db
from miraz.gozlemci import Defter, Kayit


@dataclass
class _Satir:
    symbol: str = "BTCUSDT"
    interval: str = "1h"
    fiyat: float = 50000.0
    kategori: str = "Trade"
    kalite: str = "A"
    guven: float = 85.0
    yon: str = "destek bölgesi"
    giris: float = 50200.0
    hedef: float = 52200.0
    rr: float = 1.0
    not_: str = ""
    taraf: str = "Long"
    stop: float = 48200.0
    pattern: str = "Gartley"
    kaynak: str = "Harmonic"

    @property
    def _sira(self):
        return (0 if self.kategori == "Trade" else 1, -self.guven)


@dataclass
class _Rapor:
    satirlar: list = field(default_factory=list)

    @property
    def ozet(self):
        o = {"Trade": 0, "Watch": 0, "Skip": 0, "Elenen": 0}
        for s in self.satirlar:
            o[s.kategori] = o.get(s.kategori, 0) + 1
        o["toplam"] = len(self.satirlar)
        return o


def _render(grup) -> str:
    """Bir rich render edilebilir nesneyi düz metne çevirir."""
    con = Console(width=120, file=None, record=True)
    con.print(grup)
    return con.export_text()


def test_fmt_buyukluk_kademeleri():
    assert db._fmt(None) == "—"
    assert db._fmt(50000) == "50,000.00"
    assert "0.000012" in db._fmt(0.0000123) or db._fmt(0.0000123).startswith("0.0")


def test_pano_olustur_temel_metinler():
    rapor = _Rapor([
        _Satir(symbol="BTCUSDT", kategori="Trade", kaynak="Harmonic"),
        _Satir(symbol="ETHUSDT", kategori="Watch", kaynak="Filtered",
               pattern=None),
    ])
    grup = db.pano_olustur(rapor, bilgi="Tarama #1")
    metin = _render(grup)
    # başlık + bucket başlıkları + semboller görünür
    assert "TerminalMiraz" in metin
    assert "SCANNER RESULT" in metin and "HARMONIK RESULT" in metin
    assert "LATE RESULT" in metin and "FILTERED RESULT" in metin
    assert "BTCUSDT" in metin and "ETHUSDT" in metin
    assert "CANLI ADAY AKIŞI" in metin
    assert "SONUÇ BİLDİRİMLERİ" in metin


def test_pano_bucket_wr_defterden():
    """Defter verilince bucket WR'leri metrik kutularında görünür."""
    rapor = _Rapor([_Satir()])
    d = Defter()
    d.kayitlar = [
        Kayit(1, "", "BTCUSDT", "1h", "Long", "A", 80, 100, 95, 110, 1.0,
              durum="TP", r_sonuc=1.0, kaynak="Harmonic"),
        Kayit(2, "", "ETHUSDT", "1h", "Long", "B", 70, 100, 95, 110, 1.0,
              durum="STOP", r_sonuc=-1.0, kaynak="Harmonic"),
    ]
    metin = _render(db.pano_olustur(rapor, defter=d))
    # Harmonic bucket: 2 kapalı, 1 TP, 1 STOP, %50
    assert "TP 1" in metin and "STOP 1" in metin
    assert "%50" in metin


def test_pano_bildirimler_kapanan_kayit():
    """Kapanan defter kayıtları SONUÇ BİLDİRİMLERİ'nde R sonucuyla görünür."""
    rapor = _Rapor([])
    d = Defter()
    d.kayitlar = [
        Kayit(1, "", "SOLUSDT", "4h", "Short", "A", 80, 150, 160, 140, 1.0,
              durum="TP", r_sonuc=1.0, kaynak="Harmonic", pattern="Gartley",
              kapanis_zaman="2025-06-01T12:00:00+00:00"),
    ]
    metin = _render(db.pano_olustur(rapor, defter=d))
    assert "SOLUSDT" in metin
    assert "+1.0R" in metin


def test_pano_setup_yoksa_bos_kart():
    metin = _render(db.pano_olustur(_Rapor([])))
    assert "setup yok" in metin


def test_pano_yazdir_calisir(capsys):
    """pano_yazdir konsola hatasız yazar."""
    db.pano_yazdir(_Rapor([_Satir()]), bilgi="x")
    out = capsys.readouterr().out
    assert "TerminalMiraz" in out
