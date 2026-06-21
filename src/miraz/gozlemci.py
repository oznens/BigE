"""Canlı Gözlemci — sürekli tarama + kayıt defteri (terminalMiraz çalışma şekli).

@tradermiraz terminalMiraz'ı sürekli çalıştırıyor: evreni belli aralıklarla
tarıyor, bulduğu her setup'ı bir Learning Journal'a (SQL hafıza) kaydediyor,
yaşam döngüsünü izliyor (Aday → Açık → TP/STOP/Expired) ve canlı P&L tutuyor.

Bu modül aynı döngüyü kurar:
  1. radar_tara ile evreni tarar (long/short/her).
  2. Trade sinyallerini PORTFÖYE (paper-trading) ve DEFTERE (journal) ekler.
  3. Açık/bekleyen pozisyonları taze veriyle günceller (TP/STOP/Expired).
  4. Defter kayıtlarının durumunu portföy sonuçlarından senkronize eder.
  5. terminalMiraz tarzı canlı özet döndürür; her şey diske yazılır.

Tek seferlik (`dongu`) ya da sürekli (CLI `--surekli`) çalıştırılır.

Kullanım:
    from miraz.gozlemci import Gozlemci
    g = Gozlemci(semboller=[...], intervallar=["1h","2h"], taraf="her")
    sonuc = g.dongu()
    print(sonuc.metin)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

from . import veri
from .radar import radar_tara
from .portfoy import Portfoy, radar_sinyallerini_ekle

KOK = Path(__file__).resolve().parents[2]
DEFTER_DOSYA = KOK / "defter.json"
PORTFOY_DOSYA = KOK / "portfoy.json"


def _simdi() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Kayıt Defteri (Learning Journal) — her Trade setup'ı ve yaşam döngüsü
# ---------------------------------------------------------------------------

@dataclass
class Kayit:
    id: int
    acilis_zaman: str
    sembol: str
    interval: str
    taraf: str               # "Long" / "Short"
    kalite: str
    guven: float
    giris: float
    stop: float
    hedef: float
    rr: float
    pattern: str | None = None
    # terminalMiraz lifecycle: Aday → Açık → TP/STOP/Expired/No-Entry/
    # Cancelled/Shelved/Manuel
    durum: str = "Aday"
    kapanis_zaman: str = ""
    r_sonuc: float = 0.0
    # Result Journal motoru: Price Action / Harmonik / Late
    kaynak: str = "Price Action"

    @property
    def aktif(self) -> bool:
        return self.durum in ("Aday", "Açık")


@dataclass
class Defter:
    kayitlar: list = field(default_factory=list)   # list[Kayit]
    id_sayac: int = 0
    tarama_turu: int = 0          # toplam çalıştırılan döngü sayısı
    toplam_tarama: int = 0        # kümülatif tarama adedi (parite×TF×döngü)
    son_dongu: str = ""

    # --- kayıt ekleme / senkronizasyon ---

    def _aktif_kayit(self, sembol, interval, taraf) -> Kayit | None:
        for k in self.kayitlar:
            if (k.sembol == sembol and k.interval == interval
                    and k.taraf == taraf and k.aktif):
                return k
        return None

    def setup_ekle(self, satir) -> Kayit | None:
        """Bir Trade radar satırını deftere işler (zaten aktifse tekrar etmez)."""
        taraf = getattr(satir, "taraf", "Long")
        if self._aktif_kayit(satir.symbol, satir.interval, taraf) is not None:
            return None
        if satir.giris is None or satir.hedef is None or not satir.rr:
            return None
        stop = (satir.stop if getattr(satir, "stop", None) is not None
                else satir.giris - (satir.hedef - satir.giris) / max(satir.rr, 0.1))
        self.id_sayac += 1
        k = Kayit(
            id=self.id_sayac, acilis_zaman=_simdi(), sembol=satir.symbol,
            interval=satir.interval, taraf=taraf, kalite=satir.kalite,
            guven=satir.guven, giris=round(float(satir.giris), 6),
            stop=round(float(stop), 6), hedef=round(float(satir.hedef), 6),
            rr=round(float(satir.rr), 2), pattern=getattr(satir, "pattern", None),
            kaynak=getattr(satir, "kaynak", "Price Action"))
        self.kayitlar.append(k)
        return k

    def senkronize(self, portfoy: Portfoy) -> None:
        """Defter kayıtlarının durumunu portföy pozisyonlarından günceller.

        Portföy durumu (Bekliyor/Açık/TP/STOP/Expired/Manuel) → Kayıt durumu.
        """
        durum_map = {"Bekliyor": "Aday", "Açık": "Açık", "TP": "TP",
                     "STOP": "STOP", "Expired": "Expired", "Manuel": "Manuel"}
        for k in self.kayitlar:
            if not k.aktif:
                continue
            for p in portfoy.pozisyonlar:
                if (p.sembol == k.sembol and p.interval == k.interval
                        and p.yon == k.taraf):
                    k.durum = durum_map.get(p.durum, k.durum)
                    if not k.aktif:
                        k.kapanis_zaman = p.kapanis_zaman or _simdi()
                        k.r_sonuc = p.r_sonuc
                    break

    # --- istatistik ---

    def ozet(self) -> dict:
        # lifecycle sayaçları (terminalMiraz Result Journal alt satırı)
        o = {"toplam": len(self.kayitlar), "aktif": 0, "Aday": 0, "Açık": 0,
             "TP": 0, "STOP": 0, "Expired": 0, "No-Entry": 0, "Cancelled": 0,
             "Shelved": 0, "Filtered": 0, "Manuel": 0}
        # strateji motoru bucket'ları (Result Journal üst satırı)
        buckets: dict[str, dict] = {
            "Price Action": {"tp": 0, "stop": 0, "toplam": 0, "wr": 0.0},
            "Harmonik":     {"tp": 0, "stop": 0, "toplam": 0, "wr": 0.0},
            "Late":         {"tp": 0, "stop": 0, "toplam": 0, "wr": 0.0},
        }
        for k in self.kayitlar:
            o[k.durum] = o.get(k.durum, 0) + 1
            if k.aktif:
                o["aktif"] += 1
            b = getattr(k, "kaynak", "Price Action")
            if b in buckets and k.durum in ("TP", "STOP"):
                buckets[b]["tp" if k.durum == "TP" else "stop"] += 1
        bitti = o["TP"] + o["STOP"]
        o["wr"] = round(100 * o["TP"] / bitti, 1) if bitti else 0.0
        o["toplam_r"] = round(sum(k.r_sonuc for k in self.kayitlar
                                  if not k.aktif), 2)
        for b, bkt in buckets.items():
            done = bkt["tp"] + bkt["stop"]
            bkt["toplam"] = done
            bkt["wr"] = round(100 * bkt["tp"] / done, 1) if done else 0.0
        o["buckets"] = buckets
        return o

    def pnl_analitik(self) -> dict:
        """terminalMiraz PNL ANALYTICS ekranının verisi: profit factor, açık/
        kapalı PNL, en iyi/kötü gün, parite & TF performansı."""
        kapali = [k for k in self.kayitlar if k.durum in ("TP", "STOP")]
        kazanc = sum(k.r_sonuc for k in kapali if k.r_sonuc > 0)
        zarar = -sum(k.r_sonuc for k in kapali if k.r_sonuc < 0)
        kapali_r = round(sum(k.r_sonuc for k in kapali), 2)
        acik = [k for k in self.kayitlar if k.durum == "Açık"]
        tp = sum(1 for k in kapali if k.durum == "TP")
        stop = sum(1 for k in kapali if k.durum == "STOP")

        # günlük PNL → en iyi / en kötü gün
        gunluk: dict[str, float] = {}
        for k in kapali:
            gun = (k.kapanis_zaman or "")[:10] or "?"
            gunluk[gun] = gunluk.get(gun, 0.0) + k.r_sonuc
        en_iyi = max(gunluk.values()) if gunluk else 0.0
        en_kotu = min(gunluk.values()) if gunluk else 0.0
        kazanc_gun = sum(1 for v in gunluk.values() if v > 0)
        zarar_gun = sum(1 for v in gunluk.values() if v < 0)

        # parite & TF kırılımı (WR + toplam R)
        def _kir(anahtar):
            d: dict[str, dict] = {}
            for k in kapali:
                key = getattr(k, anahtar)
                e = d.setdefault(key, {"tp": 0, "stop": 0, "r": 0.0})
                e["tp" if k.durum == "TP" else "stop"] += 1
                e["r"] += k.r_sonuc
            for e in d.values():
                t = e["tp"] + e["stop"]
                e["wr"] = round(100 * e["tp"] / t, 1) if t else 0.0
                e["r"] = round(e["r"], 2)
            return d

        return {
            "net_pnl": kapali_r,
            "acik_pnl": round(sum(k.r_sonuc for k in acik), 2),
            "kapali_pnl": kapali_r,
            "tp": tp, "stop": stop,
            "cancelled": sum(1 for k in self.kayitlar if k.durum == "Cancelled"),
            "wr": round(100 * tp / (tp + stop), 1) if (tp + stop) else 0.0,
            "profit_factor": round(kazanc / zarar, 2) if zarar else (
                kazanc if kazanc else 0.0),
            "en_iyi_gun": round(en_iyi, 1), "en_kotu_gun": round(en_kotu, 1),
            "kazanc_gun": kazanc_gun, "zarar_gun": zarar_gun,
            "parite": _kir("sembol"), "tf": _kir("interval"),
            "konsept": o_buckets if (o_buckets := self.ozet()["buckets"]) else {},
        }

    # --- kalıcılık ---

    def kaydet(self, dosya: str | Path = DEFTER_DOSYA) -> None:
        data = {
            "id_sayac": self.id_sayac, "tarama_turu": self.tarama_turu,
            "toplam_tarama": self.toplam_tarama, "son_dongu": self.son_dongu,
            "kayitlar": [asdict(k) for k in self.kayitlar],
        }
        Path(dosya).write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def yukle(cls, dosya: str | Path = DEFTER_DOSYA) -> "Defter":
        p = Path(dosya)
        if not p.exists():
            return cls()
        d = json.loads(p.read_text(encoding="utf-8"))
        df = cls(id_sayac=d.get("id_sayac", 0),
                 tarama_turu=d.get("tarama_turu", 0),
                 toplam_tarama=d.get("toplam_tarama", 0),
                 son_dongu=d.get("son_dongu", ""))
        df.kayitlar = [Kayit(**k) for k in d.get("kayitlar", [])]
        return df


# ---------------------------------------------------------------------------
# Gözlemci — bir tarama-kayıt-takip döngüsünü yürütür
# ---------------------------------------------------------------------------

@dataclass
class DonguSonuc:
    tarama: int
    radar_ozet: dict
    eklenen: int
    degisenler: list
    defter_ozet: dict
    portfoy_r: float
    portfoy_wr: float
    portfoy_aktif: int
    metin: str = ""
    rapor: object = None   # RadarRapor — CANLI ADAY AKIŞI için


class Gozlemci:
    def __init__(self, semboller, intervallar, taraf="long", rr_hedef=1.0,
                 cluster_hafiza=None, r_dolar=25.0, gun=120, max_bekleme=24,
                 goreceli=False, portfoy=None, defter=None):
        self.semboller = semboller
        self.intervallar = intervallar
        self.taraf = taraf
        self.rr_hedef = rr_hedef
        self.cluster_hafiza = cluster_hafiza
        self.r_dolar = r_dolar
        self.gun = gun
        self.max_bekleme = max_bekleme
        self.goreceli = goreceli
        self.portfoy = portfoy or Portfoy(r_dolar=r_dolar)
        self.defter = defter or Defter()

    def dongu(self) -> DonguSonuc:
        """Tek bir tarama-kayıt-takip turu çalıştırır."""
        # 1. Tara
        rapor = radar_tara(
            self.semboller, self.intervallar, r_dolar=self.r_dolar,
            gun=self.gun, cluster_hafiza=self.cluster_hafiza,
            goreceli=self.goreceli, taraf=self.taraf, rr_hedef=self.rr_hedef)

        # 2. Trade sinyallerini portföye + deftere ekle
        eklenen = radar_sinyallerini_ekle(self.portfoy, rapor)
        for satir in rapor.satirlar:
            if satir.kategori == "Trade":
                self.defter.setup_ekle(satir)

        # 3. Açık/bekleyen pozisyonları taze veriyle güncelle
        aktif_sem = {(p.sembol, p.interval) for p in self.portfoy.aktif}
        df_sozluk = {}
        for (sem, ivl) in aktif_sem:
            try:
                df_sozluk[(sem, ivl)] = veri.indir(sem, ivl, gun=self.gun,
                                                    force=True)
            except Exception:
                continue
        degisenler = self.portfoy.guncelle_hepsi(
            df_sozluk, max_bekleme=self.max_bekleme) if df_sozluk else []

        # 4. Defteri portföyden senkronize et
        self.defter.senkronize(self.portfoy)

        # 5. Sayaçlar + kalıcılık
        self.defter.tarama_turu += 1
        self.defter.toplam_tarama += len(rapor.satirlar)
        self.defter.son_dongu = _simdi()

        d_ozet = self.defter.ozet()
        sonuc = DonguSonuc(
            tarama=len(rapor.satirlar), radar_ozet=rapor.ozet,
            eklenen=eklenen, degisenler=degisenler, defter_ozet=d_ozet,
            portfoy_r=self.portfoy.toplam_r, portfoy_wr=self.portfoy.win_rate,
            portfoy_aktif=len(self.portfoy.aktif), rapor=rapor)
        sonuc.metin = self._metin(sonuc, rapor)
        return sonuc

    def kaydet(self, defter_dosya=DEFTER_DOSYA, portfoy_dosya=PORTFOY_DOSYA):
        self.defter.kaydet(defter_dosya)
        self.portfoy.kaydet(portfoy_dosya)

    def _metin(self, s: DonguSonuc, rapor) -> str:
        ro = s.radar_ozet
        zaman = datetime.now(timezone.utc).strftime("%H:%M:%S")
        sat = [
            f"🔭 TARAMA #{self.defter.tarama_turu} — {zaman} | "
            f"{s.tarama} tarama",
            f"   Aday {ro.get('Trade',0)} · İzle {ro.get('Watch',0)} · "
            f"Atla {ro.get('Skip',0)} · Elenen {ro.get('Elenen',0)}",
        ]
        if s.eklenen:
            sat.append(f"   ➕ {s.eklenen} yeni Trade → portföy + defter")
        for p in s.degisenler:
            ikon = {"TP": "✅", "STOP": "🔴", "Açık": "🟢",
                    "Expired": "⌛"}.get(p.durum, "⬜")
            rtxt = (f" {p.r_sonuc:+.1f}R" if p.durum in ("TP", "STOP") else "")
            sat.append(f"   {ikon} {p.sembol}/{p.interval} {p.durum}{rtxt}")
        d = s.defter_ozet
        sat.append(
            f"   📓 Defter: {d['toplam']} kayıt | {d['aktif']} aktif · "
            f"{d['TP']} TP · {d['STOP']} STOP · {d['Expired']} Expired "
            f"(WR %{d['wr']})")
        sat.append(
            f"   💰 Portföy: {s.portfoy_r:+.1f}R | WR %{s.portfoy_wr} | "
            f"{s.portfoy_aktif} aktif")
        return "\n".join(sat)
