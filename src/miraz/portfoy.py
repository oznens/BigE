"""Portföy yönetimi — paper-trading motoru (terminalMiraz tarzı aktif işlem takibi).

TP/STOP/Expired yaşam döngüsü zamanları, scanner'ın çalıştığı duvar saatinden
ziyade olayı gerçekten oluşturan OHLCV barının zamanıyla kaydedilir. Böylece
günlük P&L, cooldown ve journal zamanları geçmiş veri taramalarında da doğru
zamana bağlanır.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .bicim import f as _f


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
    durum: str = "Bekliyor"
    acilis_zaman: str = ""
    kapanis_zaman: str = ""
    son_kontrol_zaman: str = ""
    r_sonuc: float = 0.0
    son_fiyat: float = 0.0


@dataclass
class Portfoy:
    pozisyonlar: list = field(default_factory=list)
    r_dolar: float = 25.0
    id_sayac: int = 0

    _IV_SN = {"1m": 60, "3m": 180, "5m": 300, "15m": 900, "30m": 1800,
              "1h": 3600, "2h": 7200, "4h": 14400, "6h": 21600,
              "12h": 43200, "1d": 86400}

    def ekle(self, sembol: str, interval: str, giris: float, stop: float,
             hedef: float, rr: float, kalite: str, guven: float,
             yon: str = "Long", zaman: str | None = None,
             cooldown_bar: int = 24) -> Pozisyon | None:
        """Yeni bir bekleyen pozisyon ekler; aktif/çok yeni duplikatı engeller."""
        for p in self.pozisyonlar:
            if (p.sembol == sembol and p.interval == interval
                    and p.durum in ("Bekliyor", "Açık")):
                return None

        zaman = zaman or _simdi()
        sn = self._IV_SN.get(interval, 900)
        cooldown_sn = cooldown_bar * sn
        try:
            simdi_ts = _utc_ts(zaman)
        except Exception:
            simdi_ts = None

        if simdi_ts is not None:
            for p in self.pozisyonlar:
                if (p.sembol == sembol and p.interval == interval
                        and p.yon == yon
                        and p.durum in ("Expired", "STOP", "TP", "Manuel")
                        and giris > 0 and abs(p.giris - giris) <= giris * 0.005):
                    ref = p.kapanis_zaman or p.acilis_zaman
                    if not ref:
                        continue
                    try:
                        gecen = (simdi_ts - _utc_ts(ref)).total_seconds()
                    except Exception:
                        continue
                    if 0 <= gecen < cooldown_sn:
                        return None

        poz = Pozisyon(
            id=self.id_sayac, sembol=sembol, interval=interval, yon=yon,
            giris=giris, stop=stop, hedef=hedef, rr=rr,
            kalite=kalite, guven=guven, durum="Bekliyor",
            acilis_zaman=zaman, son_kontrol_zaman=zaman, son_fiyat=giris,
        )
        self.pozisyonlar.append(poz)
        self.id_sayac += 1
        return poz

    def kapat_manuel(self, pozisyon_id: int) -> bool:
        for p in self.pozisyonlar:
            if p.id == pozisyon_id and p.durum in ("Bekliyor", "Açık"):
                p.durum = "Manuel"
                p.kapanis_zaman = _simdi()
                return True
        return False

    def guncelle(self, sembol: str, interval: str, df: pd.DataFrame,
                 max_bekleme: int = 24) -> list:
        """Pozisyonları bar bar yürütür; TP/STOP/Expired zamanını bar zamanından alır."""
        aktif = [p for p in self.pozisyonlar
                 if p.sembol == sembol and p.interval == interval
                 and p.durum in ("Bekliyor", "Açık")]
        if not aktif or df is None or df.empty:
            return []

        degisenler: list[Pozisyon] = []
        son_fiyat = float(df["close"].iloc[-1])

        for poz in aktif:
            poz.son_fiyat = son_fiyat
            if poz.son_kontrol_zaman:
                baslangic = _utc_ts(poz.son_kontrol_zaman)
                alt_df = df[df.index > baslangic]
            else:
                alt_df = df
            if alt_df.empty:
                continue

            low = alt_df["low"].to_numpy(dtype=float)
            high = alt_df["high"].to_numpy(dtype=float)
            idx = alt_df.index
            short = poz.yon == "Short"
            acilis_ts = _utc_ts(poz.acilis_zaman) if poz.acilis_zaman else None
            kapanis_oldu = False

            for j in range(len(alt_df)):
                bar_zamani = idx[j].isoformat()

                if poz.durum == "Bekliyor":
                    if acilis_ts is not None:
                        gecen_j = int(((df.index > acilis_ts)
                                       & (df.index <= idx[j])).sum())
                        if gecen_j > max_bekleme:
                            poz.durum = "Expired"
                            poz.r_sonuc = 0.0
                            poz.kapanis_zaman = bar_zamani
                            degisenler.append(poz)
                            kapanis_oldu = True
                            break

                    doldu = (high[j] >= poz.giris) if short else (low[j] <= poz.giris)
                    if doldu:
                        poz.durum = "Açık"
                        degisenler.append(poz)

                if poz.durum == "Açık":
                    stop_vurdu = (high[j] >= poz.stop) if short else (low[j] <= poz.stop)
                    tp_vurdu = (low[j] <= poz.hedef) if short else (high[j] >= poz.hedef)
                    # Aynı bar hem TP hem STOP ise muhafazakâr biçimde STOP.
                    if stop_vurdu:
                        poz.durum = "STOP"
                        poz.r_sonuc = -1.0
                        poz.kapanis_zaman = bar_zamani
                        degisenler.append(poz)
                        kapanis_oldu = True
                        break
                    if tp_vurdu:
                        poz.durum = "TP"
                        poz.r_sonuc = poz.rr
                        poz.kapanis_zaman = bar_zamani
                        degisenler.append(poz)
                        kapanis_oldu = True
                        break

            if not kapanis_oldu:
                poz.son_kontrol_zaman = idx[-1].isoformat()
                if poz.durum == "Bekliyor" and poz.acilis_zaman:
                    acilis = _utc_ts(poz.acilis_zaman)
                    gecen = int((df.index > acilis).sum())
                    if gecen >= max_bekleme:
                        poz.durum = "Expired"
                        poz.r_sonuc = 0.0
                        poz.kapanis_zaman = idx[-1].isoformat()
                        degisenler.append(poz)

        return degisenler

    def guncelle_hepsi(self, df_sozluk: dict, max_bekleme: int = 24) -> list:
        tum: list[Pozisyon] = []
        for (sem, ivl), df in df_sozluk.items():
            tum.extend(self.guncelle(sem, ivl, df, max_bekleme=max_bekleme))
        return tum

    @property
    def aktif(self) -> list:
        return [p for p in self.pozisyonlar if p.durum in ("Bekliyor", "Açık")]

    @property
    def kapali(self) -> list:
        return [p for p in self.pozisyonlar
                if p.durum in ("TP", "STOP", "Manuel", "Expired")]

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
        if tarih is None:
            tarih = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return round(sum(p.r_sonuc for p in self.kapali
                         if p.kapanis_zaman.startswith(tarih)), 2)

    def r_gecmisi(self) -> list[dict]:
        return sorted(
            [{"zaman": p.kapanis_zaman, "sembol": p.sembol, "durum": p.durum,
              "r": p.r_sonuc, "kalite": p.kalite}
             for p in self.kapali if p.kapanis_zaman],
            key=lambda x: x["zaman"])

    def tablo(self, sadece_aktif: bool = False) -> str:
        sat: list[str] = []
        W = 66
        cizgi = lambda char="═": char * W
        aktif = self.aktif
        kapali = self.kapali
        tp_n = sum(1 for p in kapali if p.durum == "TP")
        stop_n = sum(1 for p in kapali if p.durum == "STOP")

        sat.append(cizgi())
        sat.append(f"📊  PORTFÖY — Aktif İşlem Yönetimi  (paper-trading, 1R = {self.r_dolar:.0f}$)")
        sat.append(cizgi())
        baslik = (f"{'Sembol':<10} {'TF':<4} {'Yön':<5} {'Durum':<10} "
                  f"{'Giriş':>10} {'Stop':>10} {'Hedef':>10} "
                  f"{'R/R':>4} {'Kal':>3} {'Fiyat':>10}")
        sat.append(baslik)
        sat.append(cizgi("─"))

        if aktif:
            for p in sorted(aktif, key=lambda x: (-x.guven, x.sembol)):
                ikon = "🟢 Açık   " if p.durum == "Açık" else "⏳ Bekliyor"
                yon_e = "🔻S" if p.yon == "Short" else "🔼L"
                pnl = ""
                if (p.durum == "Açık" and p.son_fiyat and p.giris > 0
                        and p.giris != p.stop):
                    if p.yon == "Short":
                        fark_r = (p.giris - p.son_fiyat) / (p.stop - p.giris)
                    else:
                        fark_r = (p.son_fiyat - p.giris) / (p.giris - p.stop)
                    pnl = f"{fark_r:+.2f}R"
                sat.append(
                    f"{p.sembol:<10} {p.interval:<4} {yon_e:<5} {ikon:<10} "
                    f"{_f(p.giris):>10} {_f(p.stop):>10} {_f(p.hedef):>10} "
                    f"{p.rr:>4.1f} {p.kalite:>3}  {_f(p.son_fiyat):>9}"
                    f"{f'  {pnl}' if pnl else ''}")
        else:
            sat.append("   (açık/bekleyen işlem yok)")

        if not sadece_aktif:
            sat.append(cizgi("─"))
            sat.append(f"GEÇMİŞ  ({len(kapali)} işlem · son 10):")
            if kapali:
                for p in sorted(kapali, key=lambda x: x.kapanis_zaman,
                                reverse=True)[:10]:
                    ikon = "✅" if p.durum == "TP" else ("🔴" if p.durum == "STOP" else "⬜")
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
            f"ÖZET  Açık: {len(aktif)}  |  Kapalı: {len(kapali)} "
            f"(TP {tp_n} · STOP {stop_n})  |  WR %{self.win_rate}  |  "
            f"Toplam {self.toplam_r:+.1f}R")
        sat.append(
            f"      Bugün: {bugun:+.1f}R  |  1R = {self.r_dolar:.0f}$  "
            f"→ bugün $ {bugun * self.r_dolar:+.1f}")
        sat.append(cizgi())
        return "\n".join(sat)

    def ozet_metin(self) -> str:
        bugun = self.gunluk_r()
        return (
            f"Portföy: {len(self.aktif)} açık | {len(self.kapali)} kapalı "
            f"(WR %{self.win_rate}) | Toplam {self.toplam_r:+.1f}R | "
            f"Bugün {bugun:+.1f}R")

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


def _utc_ts(zaman: str | pd.Timestamp) -> pd.Timestamp:
    """Naive/aware zamanı güvenli biçimde UTC Timestamp'e çevirir."""
    ts = pd.Timestamp(zaman)
    if ts.tzinfo is None:
        return ts.tz_localize("UTC")
    return ts.tz_convert("UTC")


def _simdi() -> str:
    return datetime.now(timezone.utc).isoformat()


def radar_sinyallerini_ekle(portfoy: Portfoy, radar_raporu,
                             interval: str = "4h") -> int:
    """RadarRapor'daki Trade sinyallerini portföye ekler (long + short)."""
    eklendi = 0
    for satir in radar_raporu.satirlar:
        if satir.kategori != "Trade":
            continue
        if satir.giris is None or satir.hedef is None or not satir.rr:
            continue
        yon = "Short" if getattr(satir, "taraf", "Long") == "Short" else "Long"
        poz = portfoy.ekle(
            sembol=satir.symbol,
            interval=satir.interval or interval,
            giris=satir.giris,
            stop=satir.giris - (satir.hedef - satir.giris) / max(satir.rr, 0.1),
            hedef=satir.hedef,
            rr=satir.rr,
            kalite=satir.kalite,
            guven=satir.guven,
            yon=yon,
        )
        if poz is not None:
            eklendi += 1
    return eklendi
