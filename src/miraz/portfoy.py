"""Portföy yönetimi — paper-trading motoru (terminalMiraz tarzı aktif işlem takibi).

terminalMiraz'da her Trade sinyali sanal portföyde izlenir:
  • Bekliyor — limit emir girildi, fiyat henüz ulaşmadı.
  • Açık     — giriş dolu, TP / STOP bekleniyor.
  • TP / STOP / Manuel — işlem kapandı.

Kullanım:
    from miraz.portfoy import Portfoy
    pf = Portfoy(r_dolar=25.0)
    pf.ekle("BTCUSDT", "4h", giris=95000, stop=93000, hedef=102000,
            rr=3.5, kalite="A", guven=78.0)
    pf.guncelle("BTCUSDT", "4h", df)
    print(pf.tablo())
    pf.kaydet("portfoy.json")
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .bicim import f as _f


# ---------------------------------------------------------------------------
# Veri yapıları
# ---------------------------------------------------------------------------

@dataclass
class Pozisyon:
    id: int
    sembol: str
    interval: str
    yon: str = "Long"
    giris: float = 0.0
    stop: float = 0.0
    hedef: float = 0.0
    rr: float = 0.0
    kalite: str = "C"
    guven: float = 0.0
    durum: str = "Bekliyor"       # Bekliyor / Açık / TP / STOP / Manuel
    acilis_zaman: str = ""        # ISO-8601 UTC
    kapanis_zaman: str = ""
    son_kontrol_zaman: str = ""   # güncelleme sırasında işlenen son barın zamanı
    r_sonuc: float = 0.0          # +rr (TP) / -1.0 (STOP) / 0.0
    son_fiyat: float = 0.0


@dataclass
class Portfoy:
    pozisyonlar: list = field(default_factory=list)   # list[Pozisyon]
    r_dolar: float = 25.0
    id_sayac: int = 0

    # -----------------------------------------------------------------------
    # Pozisyon ekleme
    # -----------------------------------------------------------------------

    def ekle(self, sembol: str, interval: str, giris: float, stop: float,
             hedef: float, rr: float, kalite: str, guven: float,
             yon: str = "Long", zaman: str | None = None) -> Pozisyon | None:
        """Yeni bir pozisyon (Bekliyor) ekler.

        Aynı sembol+interval için zaten Bekliyor veya Açık işlem varsa
        ekleme yapılmaz (None döner).
        """
        for p in self.pozisyonlar:
            if (p.sembol == sembol and p.interval == interval
                    and p.durum in ("Bekliyor", "Açık")):
                return None

        if zaman is None:
            zaman = _simdi()
        poz = Pozisyon(
            id=self.id_sayac,
            sembol=sembol, interval=interval, yon=yon,
            giris=giris, stop=stop, hedef=hedef, rr=rr,
            kalite=kalite, guven=guven,
            durum="Bekliyor", acilis_zaman=zaman, son_kontrol_zaman=zaman,
            son_fiyat=giris,
        )
        self.pozisyonlar.append(poz)
        self.id_sayac += 1
        return poz

    def kapat_manuel(self, pozisyon_id: int) -> bool:
        """Belirtilen pozisyonu manuel olarak kapatır."""
        for p in self.pozisyonlar:
            if p.id == pozisyon_id and p.durum in ("Bekliyor", "Açık"):
                p.durum = "Manuel"
                p.kapanis_zaman = _simdi()
                return True
        return False

    # -----------------------------------------------------------------------
    # Güncelleme — TP / STOP takibi
    # -----------------------------------------------------------------------

    def guncelle(self, sembol: str, interval: str, df: pd.DataFrame) -> list:
        """Bir sembol için açık/bekleyen pozisyonları OHLCV veriyle günceller.

        df: veri.indir()'den gelen UTC DatetimeIndex'li OHLCV DataFrame.
        Döndürür: durum değişen Pozisyon listesi.
        """
        aktif = [p for p in self.pozisyonlar
                 if p.sembol == sembol and p.interval == interval
                 and p.durum in ("Bekliyor", "Açık")]
        if not aktif:
            return []

        degisenler: list[Pozisyon] = []
        son_fiyat = float(df["close"].iloc[-1])

        for poz in aktif:
            poz.son_fiyat = son_fiyat

            # Son kontrol zamanından sonraki barları al
            if poz.son_kontrol_zaman:
                baslangic = pd.Timestamp(poz.son_kontrol_zaman).tz_convert("UTC")
                alt_df = df[df.index > baslangic]
            else:
                alt_df = df

            if alt_df.empty:
                continue

            low = alt_df["low"].to_numpy()
            high = alt_df["high"].to_numpy()
            idx = alt_df.index

            kapanis_oldu = False
            for j in range(len(alt_df)):
                if poz.durum == "Bekliyor":
                    if low[j] <= poz.giris:
                        poz.durum = "Açık"
                        degisenler.append(poz)

                if poz.durum == "Açık":
                    if low[j] <= poz.stop and high[j] >= poz.hedef:
                        # Aynı barda ikisi birden → muhafazakâr STOP
                        poz.durum = "STOP"
                        poz.r_sonuc = -1.0
                        poz.kapanis_zaman = _simdi()
                        degisenler.append(poz)
                        kapanis_oldu = True
                        break
                    if low[j] <= poz.stop:
                        poz.durum = "STOP"
                        poz.r_sonuc = -1.0
                        poz.kapanis_zaman = _simdi()
                        degisenler.append(poz)
                        kapanis_oldu = True
                        break
                    if high[j] >= poz.hedef:
                        poz.durum = "TP"
                        poz.r_sonuc = poz.rr
                        poz.kapanis_zaman = _simdi()
                        degisenler.append(poz)
                        kapanis_oldu = True
                        break

            if not kapanis_oldu:
                # Son incelenen barın zamanını kaydet
                poz.son_kontrol_zaman = idx[-1].isoformat()

        return degisenler

    def guncelle_hepsi(self, df_sozluk: dict) -> list:
        """Tüm sembolleri günceller. df_sozluk: {(sembol, interval): df}"""
        tum: list[Pozisyon] = []
        for (sem, ivl), df in df_sozluk.items():
            tum.extend(self.guncelle(sem, ivl, df))
        return tum

    # -----------------------------------------------------------------------
    # Istatistikler
    # -----------------------------------------------------------------------

    @property
    def aktif(self) -> list:
        return [p for p in self.pozisyonlar if p.durum in ("Bekliyor", "Açık")]

    @property
    def kapali(self) -> list:
        return [p for p in self.pozisyonlar
                if p.durum in ("TP", "STOP", "Manuel")]

    @property
    def toplam_r(self) -> float:
        return round(sum(p.r_sonuc for p in self.kapali), 2)

    @property
    def win_rate(self) -> float:
        bitti = [p for p in self.kapali if p.durum in ("TP", "STOP")]
        if not bitti:
            return 0.0
        tp = sum(1 for p in bitti if p.durum == "TP")
        return round(100 * tp / len(bitti), 1)

    def gunluk_r(self, tarih: str | None = None) -> float:
        """Belirtilen gündeki R kazancı (YYYY-MM-DD). None → bugün."""
        if tarih is None:
            tarih = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return round(sum(p.r_sonuc for p in self.kapali
                         if p.kapanis_zaman.startswith(tarih)), 2)

    def r_gecmisi(self) -> list[dict]:
        """Kapalı işlemleri zaman sırasıyla döndürür."""
        return sorted(
            [{"zaman": p.kapanis_zaman, "sembol": p.sembol, "durum": p.durum,
              "r": p.r_sonuc, "kalite": p.kalite}
             for p in self.kapali if p.kapanis_zaman],
            key=lambda x: x["zaman"])

    # -----------------------------------------------------------------------
    # Tablo / görsel çıktı
    # -----------------------------------------------------------------------

    def tablo(self, sadece_aktif: bool = False) -> str:
        """terminalMiraz tarzı konsol tablosu."""
        sat: list[str] = []
        W = 66

        def cizgi(char="═"):
            return char * W

        aktif = self.aktif
        kapali = self.kapali
        tp_n = sum(1 for p in kapali if p.durum == "TP")
        stop_n = sum(1 for p in kapali if p.durum == "STOP")

        sat.append(cizgi())
        sat.append(f"📊  PORTFÖY — Aktif İşlem Yönetimi  "
                   f"(paper-trading, 1R = {self.r_dolar:.0f}$)")
        sat.append(cizgi())

        # Aktif pozisyonlar
        baslik = (f"{'Sembol':<10} {'TF':<4} {'Durum':<10} "
                  f"{'Giriş':>10} {'Stop':>10} {'Hedef':>10} "
                  f"{'R/R':>4} {'Kal':>3} {'Fiyat':>10}")
        sat.append(baslik)
        sat.append(cizgi("─"))

        if aktif:
            for p in sorted(aktif, key=lambda x: (-x.guven, x.sembol)):
                ikon = "🟢 Açık   " if p.durum == "Açık" else "⏳ Bekliyor"
                # anlık kâr/zarar (açık pozisyonlar için)
                if p.durum == "Açık" and p.son_fiyat and p.giris > 0:
                    fark_r = (p.son_fiyat - p.giris) / (p.giris - p.stop)
                    pnl = f"{fark_r:+.2f}R"
                else:
                    pnl = ""
                sat.append(
                    f"{p.sembol:<10} {p.interval:<4} {ikon:<10} "
                    f"{_f(p.giris):>10} {_f(p.stop):>10} {_f(p.hedef):>10} "
                    f"{p.rr:>4.1f} {p.kalite:>3}  "
                    f"{_f(p.son_fiyat):>9}{f'  {pnl}' if pnl else ''}"
                )
        else:
            sat.append("   (açık/bekleyen işlem yok)")

        if not sadece_aktif:
            sat.append(cizgi("─"))
            sat.append(f"GEÇMİŞ  ({len(kapali)} işlem · son 10):")
            if kapali:
                for p in sorted(kapali,
                                 key=lambda x: x.kapanis_zaman, reverse=True)[:10]:
                    ikon = "✅" if p.durum == "TP" else ("🔴" if p.durum == "STOP"
                                                          else "⬜")
                    tarih = p.kapanis_zaman[:10] if p.kapanis_zaman else "—"
                    sat.append(
                        f"  {ikon} {p.sembol:<10} {p.interval:<4} "
                        f"giriş {_f(p.giris):>10}  {p.durum:5}  "
                        f"{p.r_sonuc:+.1f}R  {tarih}  [{p.kalite}]")
            else:
                sat.append("   (henüz kapanan işlem yok)")

        sat.append(cizgi())
        bugun = self.gunluk_r()
        sat.append(
            f"ÖZET  Açık: {len(aktif)}  |  "
            f"Kapalı: {len(kapali)} (TP {tp_n} · STOP {stop_n})  |  "
            f"WR %{self.win_rate}  |  Toplam {self.toplam_r:+.1f}R")
        sat.append(
            f"      Bugün: {bugun:+.1f}R  |  "
            f"1R = {self.r_dolar:.0f}$  → bugün $ "
            f"{bugun * self.r_dolar:+.1f}")
        sat.append(cizgi())
        return "\n".join(sat)

    def ozet_metin(self) -> str:
        """Kısa özet (tek satır)."""
        bugun = self.gunluk_r()
        return (
            f"Portföy: {len(self.aktif)} açık | "
            f"{len(self.kapali)} kapalı (WR %{self.win_rate}) | "
            f"Toplam {self.toplam_r:+.1f}R | Bugün {bugun:+.1f}R"
        )

    # -----------------------------------------------------------------------
    # Kalıcılık (JSON serialize / deserialize)
    # -----------------------------------------------------------------------

    def kaydet(self, dosya: str | Path = "portfoy.json") -> None:
        data = {
            "r_dolar": self.r_dolar,
            "id_sayac": self.id_sayac,
            "pozisyonlar": [asdict(p) for p in self.pozisyonlar],
        }
        Path(dosya).write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def yukle(cls, dosya: str | Path = "portfoy.json") -> "Portfoy":
        data = json.loads(Path(dosya).read_text(encoding="utf-8"))
        pf = cls(r_dolar=data.get("r_dolar", 25.0),
                 id_sayac=data.get("id_sayac", 0))
        for d in data.get("pozisyonlar", []):
            pf.pozisyonlar.append(Pozisyon(**d))
        return pf


# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------

def _simdi() -> str:
    return datetime.now(timezone.utc).isoformat()


def radar_sinyallerini_ekle(portfoy: Portfoy, radar_raporu,
                             interval: str = "4h") -> int:
    """RadarRapor'daki Trade sinyallerini portföye ekler.

    Döndürür: eklenen yeni pozisyon sayısı.
    """
    eklendi = 0
    for satir in radar_raporu.satirlar:
        if satir.kategori != "Trade":
            continue
        if satir.giris is None or satir.hedef is None:
            continue
        poz = portfoy.ekle(
            sembol=satir.symbol,
            interval=satir.interval or interval,
            giris=satir.giris,
            stop=satir.giris - (satir.hedef - satir.giris) / max(satir.rr, 0.1),
            hedef=satir.hedef,
            rr=satir.rr,
            kalite=satir.kalite,
            guven=satir.guven,
        )
        if poz is not None:
            eklendi += 1
    return eklendi
