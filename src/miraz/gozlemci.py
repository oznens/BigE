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

import pandas as pd

from . import veri
from .radar import radar_tara
from .portfoy import Portfoy, radar_sinyallerini_ekle

KOK = Path(__file__).resolve().parents[2]
DEFTER_DOSYA = KOK / "defter.json"
PORTFOY_DOSYA = KOK / "portfoy.json"


def _simdi() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _filtered_nedeni(s, eski_guven: float | None = None) -> str:
    """Radar kanıtından denetim alt nedeni üretir; Miraz'ın özel taksonomisi değil."""
    n = (getattr(s, "not_", "") or "").lower()
    if "htf" in n or "üst zaman" in n:
        return "htf-conflict"
    if "hedef zaten görüldü" in n or "bölge çiğnenmiş" in n:
        return "stale-zone"
    if "stop bölgesi çiğnenmiş" in n:
        return "structural-invalidity"
    if eski_guven is not None and getattr(s, "guven", eski_guven) < eski_guven:
        return "quality-weakened"
    return "filtered-other"


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
    entry_zaman: str = ""
    entry_kalite: str | None = None
    entry_guven: float | None = None
    entry_hacim: float | None = None
    entry_hacim_oran: float | None = None
    entry_hacim_pencere: int | None = None
    entry_kapanis: float | None = None
    entry_bekleme_bar: int | None = None
    entry_bekleme_limiti: int | None = None
    kapanis_zaman: str = ""
    r_sonuc: float = 0.0
    # Result Journal motoru: Price Action / Harmonik / Late
    kaynak: str = "Price Action"
    # Bağlı portföy pozisyonunun id'si — senkronize() bununla eşler.
    # -1 = bağ yok (legacy / pozisyon bulunamadı). Duplikat setuplarda
    # sembol+TF+yön eşlemesi yanlış pozisyonu seçtiği için id şart.
    poz_id: int = -1
    # Entry öncesi Kalite Motoru değişimleri. Yalnız gerçek değişimler saklanır;
    # aynı snapshot tekrar tekrar yazılmaz (tweet 2064005426710986769).
    kalite_gecmisi: list = field(default_factory=list)
    durum_nedeni: str = ""
    # Filtrelenen setup sonradan ayrıca izlenip gerçekten TP/STOP'a ulaştıysa
    # kaydedilir. Boş değer, karşı-olgusal sonucun takip edilmediği anlamına gelir.
    # Bu alan işlem sonucuna ve Result Journal R hesabına dahil değildir.
    karsi_olgusal_sonuc: str = ""
    karsi_olgusal_zaman: str = ""
    karsi_olgusal_durum: str = ""
    karsi_olgusal_entry_zaman: str = ""
    karsi_olgusal_son_mum: str = ""
    ana_tf_yapi: str = ""
    htf_tf: str = ""
    htf_yapi: str = ""
    ltf_tf: str = ""
    ltf_yapi: str = "not-implemented"
    ltf_onay: str = "not-available"
    setup_turleri: list = field(default_factory=list)
    setup_tur_detaylari: dict = field(default_factory=dict)
    harmonik_detay: dict = field(default_factory=dict)
    harmonik_gecmisi: list = field(default_factory=list)
    risk_modu: str = "legacy-unknown"
    risk_rr_hedef: float | None = None
    risk_r_dolar: float | None = None
    temas_detay: dict = field(default_factory=dict)
    konseptler: list = field(default_factory=list)

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

    def setup_ekle(self, satir, portfoy=None) -> Kayit | None:
        """Bir Trade radar satırını deftere işler (zaten aktifse tekrar etmez).

        portfoy verilirse, bu setup'a karşılık gelen AKTİF (Bekliyor/Açık)
        pozisyon bulunup id'si bağlanır; senkronize() sonucu bu id ile alır.
        """
        taraf = getattr(satir, "taraf", "Long")
        if self._aktif_kayit(satir.symbol, satir.interval, taraf) is not None:
            return None
        if satir.giris is None or satir.hedef is None or not satir.rr:
            return None
        stop = (satir.stop if getattr(satir, "stop", None) is not None
                else satir.giris - (satir.hedef - satir.giris) / max(satir.rr, 0.1))
        # Bu setup'ın aktif portföy pozisyonunu bul (duplikatlarda kapanmışları
        # atla — yalnız Bekliyor/Açık olan bu yeni setup'a aittir).
        poz_id = -1
        if portfoy is not None:
            for p in portfoy.pozisyonlar:
                if (p.sembol == satir.symbol and p.interval == satir.interval
                        and p.yon == taraf and p.durum in ("Bekliyor", "Açık")):
                    poz_id = p.id
                    break
            # Portföy aktif pozisyon açmadıysa (dedup/cooldown) → kayıt da açma.
            # Aksi halde poz_id=-1 dangling kayıt birikir (duplikat defter).
            if poz_id < 0:
                return None
        self.id_sayac += 1
        acilis = _simdi()
        k = Kayit(
            id=self.id_sayac, acilis_zaman=acilis, sembol=satir.symbol,
            interval=satir.interval, taraf=taraf, kalite=satir.kalite,
            guven=satir.guven, giris=round(float(satir.giris), 6),
            stop=round(float(stop), 6), hedef=round(float(satir.hedef), 6),
            rr=round(float(satir.rr), 2), pattern=getattr(satir, "pattern", None),
            kaynak=getattr(satir, "kaynak", "Price Action"), poz_id=poz_id,
            ana_tf_yapi=getattr(satir, "ana_tf_yapi", ""),
            htf_tf=getattr(satir, "htf_tf", ""),
            htf_yapi=getattr(satir, "htf_yapi", ""),
            ltf_tf=getattr(satir, "ltf_tf", ""),
            ltf_yapi=getattr(satir, "ltf_yapi", "not-implemented"),
            ltf_onay=getattr(satir, "ltf_onay", "not-available"),
            setup_turleri=list(getattr(satir, "setup_turleri", None) or []),
            setup_tur_detaylari=dict(
                getattr(satir, "setup_tur_detaylari", None) or {}),
            harmonik_detay=dict(getattr(satir, "harmonik_detay", None) or {}),
            harmonik_gecmisi=([{
                "zaman": acilis, "olay": "pattern-detected",
                "pattern": getattr(satir, "pattern", None),
                "prz": dict((getattr(satir, "harmonik_detay", None) or {})
                            .get("prz") or {}),
                "motor_kalite": (getattr(satir, "harmonik_detay", None) or {})
                                .get("motor_kalite"),
            }] if getattr(satir, "pattern", None) else []),
            risk_modu=getattr(satir, "risk_modu", "legacy-unknown"),
            risk_rr_hedef=getattr(satir, "risk_rr_hedef", None),
            risk_r_dolar=getattr(satir, "risk_r_dolar", None),
            temas_detay=dict(getattr(satir, "temas_detay", None) or {}),
            konseptler=list(getattr(satir, "konseptler", None) or []),
            kalite_gecmisi=[{
                "zaman": acilis, "kalite": satir.kalite,
                "guven": satir.guven, "kategori": satir.kategori,
                    "olay": "candidate-quality-snapshot",
                    "lifecycle": getattr(satir, "lifecycle", "Candidate"),
                    "ana_tf_yapi": getattr(satir, "ana_tf_yapi", ""),
                    "htf_tf": getattr(satir, "htf_tf", ""),
                    "htf_yapi": getattr(satir, "htf_yapi", ""),
                    "ltf_tf": getattr(satir, "ltf_tf", ""),
                    "ltf_yapi": getattr(satir, "ltf_yapi", "not-implemented"),
                    "ltf_onay": getattr(satir, "ltf_onay", "not-available"),
                }])
        self.kayitlar.append(k)
        return k

    def senkronize(self, portfoy: Portfoy) -> None:
        """Defter kayıtlarının durumunu portföy pozisyonlarından günceller.

        Portföy durumu (Bekliyor/Açık/TP/STOP/Expired/Manuel) → Kayıt durumu.

        Eşleme poz_id ile yapılır (benzersiz). poz_id yoksa (legacy kayıt) yalnız
        AKTİF pozisyonlara sembol+TF+yön ile düşülür — böylece kapanmış eski bir
        pozisyonun sonucu yanlışlıkla yeni kayda kopyalanmaz (eski bug buydu).
        """
        durum_map = {"Bekliyor": "Aday", "Açık": "Açık", "TP": "TP",
                     "STOP": "STOP", "Expired": "Expired", "Manuel": "Manuel",
                     "Cancelled": "Cancelled", "Filtered": "Filtered",
                     "Late": "Late", "No-Entry": "No-Entry",
                     "Shelved": "Shelved"}
        poz_idx = {p.id: p for p in portfoy.pozisyonlar}
        # poz_id ile bağlı kayıtların sahip olduğu pozisyonlar — legacy eşleme
        # bunları "claimed" sayıp atlar (iki kayıt aynı pozisyonu kapamasın).
        claimed = {k.poz_id for k in self.kayitlar if k.poz_id >= 0}
        for k in self.kayitlar:
            if not k.aktif:
                continue
            p = None
            if k.poz_id >= 0:
                p = poz_idx.get(k.poz_id)
            else:
                # Legacy (poz_id yok): sembol+TF+yön + giriş seviyesi eşle.
                # Başka kaydın sahiplendiği pozisyonu atla; giriş eşleşmesi
                # duplikatları ayırır (eski "ilk eşleşen" bug'ını önler).
                for q in portfoy.pozisyonlar:
                    if (q.sembol == k.sembol and q.interval == k.interval
                            and q.yon == k.taraf and q.id not in claimed
                            and (k.giris <= 0
                                 or abs(q.giris - k.giris) <= k.giris * 0.005)):
                        p = q
                        claimed.add(q.id)
                        break
            if p is None:
                continue
            if getattr(p, "entry_zaman", "") and not k.entry_zaman:
                k.entry_zaman = p.entry_zaman
                k.entry_kalite = k.kalite
                k.entry_guven = k.guven
                k.entry_hacim = getattr(p, "entry_hacim", None)
                k.entry_hacim_oran = getattr(p, "entry_hacim_oran", None)
                k.entry_hacim_pencere = getattr(p, "entry_hacim_pencere", None)
                k.entry_kapanis = getattr(p, "entry_kapanis", None)
                k.entry_bekleme_bar = getattr(p, "entry_bekleme_bar", None)
                k.entry_bekleme_limiti = getattr(
                    p, "entry_bekleme_limiti", None)
                k.kalite_gecmisi.append({
                    "zaman": k.entry_zaman, "kalite": k.kalite,
                    "guven": k.guven, "kategori": "Trade",
                    "lifecycle": "Entry", "olay": "entry-quality-snapshot",
                })
                if k.pattern:
                    k.harmonik_gecmisi.append({
                        "zaman": k.entry_zaman, "olay": "entry-filled",
                        "pattern": k.pattern, "entry": k.giris,
                    })
            k.durum = durum_map.get(p.durum, k.durum)
            if not k.aktif:
                k.kapanis_zaman = p.kapanis_zaman or _simdi()
                k.r_sonuc = p.r_sonuc

    def rafa_kaldir(self, kayit_id: int, portfoy: Portfoy,
                    neden: str = "explicit-shelve") -> Kayit | None:
        """Bekleyen setup'ı açık kararla Shelved yapar; otomatik kriter üretmez.

        Arşiv yalnız Shelved/Rafa Kalktı sonucunun varlığını kanıtlar
        (2065351367544181110), karar koşulunu açıklamaz. Bu nedenle çağrı açık
        olmalı ve neden denetim izi olarak saklanmalıdır.
        """
        k = next((x for x in self.kayitlar if x.id == kayit_id), None)
        if k is None or k.durum != "Aday" or k.poz_id < 0:
            return None
        if not portfoy.bekleyen_iptal(k.poz_id, "Shelved"):
            return None
        p = next((x for x in portfoy.pozisyonlar if x.id == k.poz_id), None)
        k.durum = "Shelved"
        k.kapanis_zaman = p.kapanis_zaman if p else _simdi()
        k.r_sonuc = 0.0
        k.durum_nedeni = neden
        k.kalite_gecmisi.append({
            "zaman": k.kapanis_zaman, "kalite": k.kalite, "guven": k.guven,
            "kategori": "Elenen", "lifecycle": "Shelved", "neden": neden,
        })
        return k

    def entry_olmadi(self, kayit_id: int, portfoy: Portfoy,
                     neden: str = "entry-zone-not-reached") -> Kayit | None:
        """Bekleyen setup'ı açık gözlemle No-Entry kapatır.

        Arşiv entry bölgesine gelmemeyi kanıtlar fakat gözlem ufkunu açıklamaz;
        bu yüzden otomatik süre uydurulmaz ve çağrı açık yapılır.
        """
        k = next((x for x in self.kayitlar if x.id == kayit_id), None)
        if k is None or k.durum != "Aday" or k.poz_id < 0:
            return None
        if not portfoy.bekleyen_iptal(k.poz_id, "No-Entry"):
            return None
        p = next((x for x in portfoy.pozisyonlar if x.id == k.poz_id), None)
        k.durum = "No-Entry"
        k.kapanis_zaman = p.kapanis_zaman if p else _simdi()
        k.r_sonuc = 0.0
        k.durum_nedeni = neden
        k.kalite_gecmisi.append({
            "zaman": k.kapanis_zaman, "kalite": k.kalite, "guven": k.guven,
            "kategori": "Elenen", "lifecycle": "No-Entry", "neden": neden,
        })
        return k

    def adaylari_yeniden_degerlendir(self, rapor, portfoy: Portfoy) -> list[Kayit]:
        """Bekleyen setup'ları yeni radar kalitesiyle güncelle veya filtrele.

        Arşiv kanıtı: tweet 2064005426710986769. Puan entry'ye kadar değişir;
        zayıflayan yapı elenir, güçlenen takip edilir. Açılmış pozisyona dokunulmaz.
        Radar hatası/yokluğu iptal sebebi değildir; yalnız eşleşen satırın yeni
        kararı uygulanır.
        """
        idx = {(s.symbol, s.interval, getattr(s, "taraf", "Long")): s
               for s in rapor.satirlar}
        poz_idx = {p.id: p for p in portfoy.pozisyonlar}
        degisen = []
        izinli = {"Filtered", "Late", "Cancelled", "No-Entry"}
        for k in self.kayitlar:
            if k.durum != "Aday":
                continue
            p = poz_idx.get(k.poz_id)
            if p is None or p.durum != "Bekliyor":
                continue
            s = idx.get((k.sembol, k.interval, k.taraf))
            if s is None:
                continue
            eski = (k.kalite, k.guven)
            k.kalite, k.guven = s.kalite, s.guven
            p.kalite, p.guven = s.kalite, s.guven
            k.ana_tf_yapi = getattr(s, "ana_tf_yapi", k.ana_tf_yapi)
            k.htf_tf = getattr(s, "htf_tf", k.htf_tf)
            k.htf_yapi = getattr(s, "htf_yapi", k.htf_yapi)
            k.ltf_tf = getattr(s, "ltf_tf", k.ltf_tf)
            k.ltf_yapi = getattr(s, "ltf_yapi", k.ltf_yapi)
            k.ltf_onay = getattr(s, "ltf_onay", k.ltf_onay)
            k.setup_turleri = list(
                getattr(s, "setup_turleri", None) or k.setup_turleri)
            k.setup_tur_detaylari = dict(
                getattr(s, "setup_tur_detaylari", None) or k.setup_tur_detaylari)
            if eski != (s.kalite, s.guven):
                k.kalite_gecmisi.append({
                    "zaman": _simdi(), "kalite": s.kalite, "guven": s.guven,
                    "kategori": s.kategori,
                    "lifecycle": getattr(s, "lifecycle", "Candidate"),
                    "ana_tf_yapi": getattr(s, "ana_tf_yapi", ""),
                    "htf_tf": getattr(s, "htf_tf", ""),
                    "htf_yapi": getattr(s, "htf_yapi", ""),
                    "ltf_tf": getattr(s, "ltf_tf", ""),
                    "ltf_yapi": getattr(s, "ltf_yapi", "not-implemented"),
                    "ltf_onay": getattr(s, "ltf_onay", "not-available"),
                })
            # Harmonik setup kimliği C/D yapısına bağlıdır. Sonraki başarılı
            # taramada aynı pattern artık yoksa veya başka pattern'e döndüyse
            # eski PRZ emri taşınamaz (tweet 2062383146415333550).
            yeni_pattern = getattr(s, "pattern", None)
            if k.pattern and yeni_pattern != k.pattern:
                if portfoy.bekleyen_iptal(p.id, "Cancelled"):
                    k.durum = "Cancelled"
                    k.kapanis_zaman = p.kapanis_zaman
                    k.r_sonuc = 0.0
                    k.durum_nedeni = "harmonic-pattern-changed-or-disappeared"
                    k.harmonik_gecmisi.append({
                        "zaman": k.kapanis_zaman,
                        "olay": "pattern-changed-or-disappeared",
                        "onceki_pattern": k.pattern,
                        "yeni_pattern": yeni_pattern,
                    })
                    degisen.append(k)
                continue
            if s.kategori == "Trade":
                continue
            neden = getattr(s, "lifecycle", "Filtered")
            if neden not in izinli:
                neden = "Filtered"
            if portfoy.bekleyen_iptal(p.id, neden):
                k.durum = neden
                k.kapanis_zaman = p.kapanis_zaman
                k.r_sonuc = 0.0
                if neden == "Filtered":
                    k.durum_nedeni = _filtered_nedeni(s, eski_guven=eski[1])
                    k.karsi_olgusal_durum = "Bekliyor"
                degisen.append(k)
        return degisen

    # --- istatistik ---

    def ozet(self) -> dict:
        # lifecycle sayaçları (terminalMiraz Result Journal alt satırı)
        o = {"toplam": len(self.kayitlar), "aktif": 0, "Aday": 0, "Açık": 0,
             "TP": 0, "STOP": 0, "Expired": 0, "No-Entry": 0, "Cancelled": 0,
             "Shelved": 0, "Filtered": 0, "Manuel": 0}
        # strateji motoru bucket'ları (Result Journal üst satırı)
        buckets: dict[str, dict] = {
            "Price Action": {"tp": 0, "stop": 0, "toplam": 0, "wr": 0.0, "r": 0.0},
            "Harmonik":     {"tp": 0, "stop": 0, "toplam": 0, "wr": 0.0, "r": 0.0},
            "Late":         {"tp": 0, "stop": 0, "toplam": 0, "wr": 0.0, "r": 0.0},
        }
        for k in self.kayitlar:
            o[k.durum] = o.get(k.durum, 0) + 1
            if k.aktif:
                o["aktif"] += 1
            b = getattr(k, "kaynak", "Price Action")
            if b in buckets and k.durum in ("TP", "STOP"):
                buckets[b]["tp" if k.durum == "TP" else "stop"] += 1
                buckets[b]["r"] += k.r_sonuc
        bitti = o["TP"] + o["STOP"]
        o["wr"] = round(100 * o["TP"] / bitti, 1) if bitti else 0.0
        o["toplam_r"] = round(sum(k.r_sonuc for k in self.kayitlar
                                  if not k.aktif), 2)
        for b, bkt in buckets.items():
            done = bkt["tp"] + bkt["stop"]
            bkt["toplam"] = done
            bkt["wr"] = round(100 * bkt["tp"] / done, 1) if done else 0.0
            bkt["r"] = round(bkt["r"], 2)
        o["buckets"] = buckets
        # Tweet 2065351363828003079 performansı Late dahil/hariç ayrı kıyaslar.
        o["toplam_r_late_haric"] = round(
            o["toplam_r"] - buckets["Late"]["r"], 2)
        o["late_katki_r"] = buckets["Late"]["r"]
        return o

    def filtered_neden_ozeti(self) -> dict[str, int]:
        """Kalıcı Filtered kayıtlarını denetim alt nedenlerine göre sayar."""
        out: dict[str, int] = {}
        for k in self.kayitlar:
            if k.durum != "Filtered":
                continue
            neden = k.durum_nedeni or "legacy-unknown"
            out[neden] = out.get(neden, 0) + 1
        return out

    def karsi_olgusal_sonuc_kaydet(self, kayit_id: int, sonuc: str) -> bool:
        """Filtered setup için sonradan doğrulanmış TP/STOP sonucunu kaydet."""
        sonuc = (sonuc or "").upper()
        if sonuc not in ("TP", "STOP"):
            return False
        kayit = next((k for k in self.kayitlar if k.id == kayit_id), None)
        if kayit is None or kayit.durum != "Filtered":
            return False
        kayit.karsi_olgusal_sonuc = sonuc
        kayit.karsi_olgusal_durum = sonuc
        kayit.karsi_olgusal_zaman = _simdi()
        return True

    def filtered_karsi_olgusal_guncelle(self, df_sozluk: dict) -> list[Kayit]:
        """Filtered setup'ları yalnız filtre kararından sonraki mumlarla izle.

        İlk görülen son mum başlangıç çizgisidir ve sonuç hesabına katılmaz.
        Entry/TP temasla, STOP invalidasyon ötesi mum kapanışıyla çalışır.
        Arşiv takip penceresini açıklamadığı için burada otomatik expiry yoktur.
        """
        degisen: list[Kayit] = []
        for k in self.kayitlar:
            if k.durum != "Filtered" or k.karsi_olgusal_sonuc:
                continue
            df = df_sozluk.get((k.sembol, k.interval))
            if df is None or df.empty:
                continue
            if not k.karsi_olgusal_durum:
                k.karsi_olgusal_durum = "Bekliyor"
            if not k.karsi_olgusal_son_mum:
                # Aynı taramadaki geçmişi karşı-olgusal başarı/zarar sayma.
                k.karsi_olgusal_son_mum = df.index[-1].isoformat()
                continue
            baslangic = pd.Timestamp(k.karsi_olgusal_son_mum)
            if baslangic.tzinfo is None:
                baslangic = baslangic.tz_localize("UTC")
            else:
                baslangic = baslangic.tz_convert("UTC")
            alt_df = df[df.index > baslangic]
            if alt_df.empty:
                continue
            short = k.taraf == "Short"
            for idx, mum in alt_df.iterrows():
                if k.karsi_olgusal_durum == "Bekliyor":
                    doldu = mum["high"] >= k.giris if short else mum["low"] <= k.giris
                    if not doldu:
                        continue
                    k.karsi_olgusal_durum = "Açık"
                    k.karsi_olgusal_entry_zaman = idx.isoformat()
                    degisen.append(k)
                if k.karsi_olgusal_durum == "Açık":
                    stop = mum["close"] > k.stop if short else mum["close"] < k.stop
                    tp = mum["low"] <= k.hedef if short else mum["high"] >= k.hedef
                    sonuc = "STOP" if stop else "TP" if tp else ""
                    if sonuc:
                        k.karsi_olgusal_durum = sonuc
                        k.karsi_olgusal_sonuc = sonuc
                        k.karsi_olgusal_zaman = idx.isoformat()
                        degisen.append(k)
                        break
            k.karsi_olgusal_son_mum = alt_df.index[-1].isoformat()
        return degisen

    def filtered_etki_ozeti(self) -> dict:
        """Filtre hacmi ile doğrulanmış karşı-olgusal sonucu ayrı raporlar."""
        nedenler = self.filtered_neden_ozeti()
        filtreli = [k for k in self.kayitlar if k.durum == "Filtered"]
        izlenen = [k for k in filtreli if
                   k.karsi_olgusal_sonuc in ("TP", "STOP")]
        bekleyen = sum(k.durum == "Filtered" and
                       k.karsi_olgusal_durum == "Bekliyor" for k in self.kayitlar)
        acik = sum(k.durum == "Filtered" and
                   k.karsi_olgusal_durum == "Açık" for k in self.kayitlar)
        stop = sum(k.karsi_olgusal_sonuc == "STOP" for k in izlenen)
        tp = sum(k.karsi_olgusal_sonuc == "TP" for k in izlenen)
        toplam = sum(nedenler.values())

        def kirilim(alan: str) -> list[dict]:
            gruplar: dict[str, list[Kayit]] = {}
            for kayit in filtreli:
                varsayilan = "legacy-unknown" if alan == "durum_nedeni" else "Bilinmiyor"
                ad = str(getattr(kayit, alan, "") or varsayilan)
                gruplar.setdefault(ad, []).append(kayit)
            out = []
            for ad, kayitlar in gruplar.items():
                dogrulanmis = [k for k in kayitlar if
                               k.karsi_olgusal_sonuc in ("TP", "STOP")]
                n_stop = sum(k.karsi_olgusal_sonuc == "STOP"
                             for k in dogrulanmis)
                n_tp = sum(k.karsi_olgusal_sonuc == "TP"
                           for k in dogrulanmis)
                n = len(dogrulanmis)
                out.append({
                    "ad": ad, "setup_sayisi": len(kayitlar),
                    "dogrulanmis_n": n,
                    "engellenen_stop": n_stop if n else None,
                    "olasi_tp": n_tp if n else None,
                    "stop_payi_yuzde": round(100 * n_stop / n, 1) if n else None,
                    "kapsama_yuzde": round(100 * n / len(kayitlar), 1),
                    "claim_allowed": bool(n),
                })
            return sorted(out, key=lambda x: (-x["setup_sayisi"], x["ad"]))

        return {
            "setup_sayisi": toplam,
            "nedenler": nedenler,
            "dogrulanmis_n": len(izlenen),
            "karsi_olgusal_bekliyor": bekleyen,
            "karsi_olgusal_acik": acik,
            "engellenen_stop": stop if izlenen else None,
            "olasi_tp": tp if izlenen else None,
            "kapsama_yuzde": round(100 * len(izlenen) / toplam, 1) if toplam else 0.0,
            "durum": "verified-counterfactual" if izlenen else "not-tracked",
            "claim_allowed": bool(izlenen),
            "kirilimlar": {
                "motor": kirilim("kaynak"),
                "timeframe": kirilim("interval"),
                "kalite": kirilim("kalite"),
                "neden": kirilim("durum_nedeni"),
            },
        }

    def filtered_kalite_gecis_ozeti(self) -> dict:
        """Filtered setup'lardaki gerçek, ardışık kalite değişimlerini özetle.

        Aynı setup'ta aynı geçiş tekrarlanırsa o geçiş için bir kez sayılır.
        Bir setup farklı geçişlerde ayrı ayrı görünebilir; bu nedensellik iddiası
        değil, kalıcı snapshot geçmişinin betimsel dökümüdür.
        """
        sira = {"A+": 0, "A": 1, "B": 2, "C": 3, "D": 4}
        gruplar: dict[str, list[Kayit]] = {}
        kapsanan: set[int] = set()
        for k in self.kayitlar:
            if k.durum != "Filtered" or len(k.kalite_gecmisi) < 2:
                continue
            kaliteler = [str(x.get("kalite", "") or "")
                         for x in k.kalite_gecmisi]
            gorulen: set[str] = set()
            for onceki, sonraki in zip(kaliteler, kaliteler[1:]):
                if not onceki or not sonraki or onceki == sonraki:
                    continue
                ad = f"{onceki}→{sonraki}"
                if ad in gorulen:
                    continue
                gorulen.add(ad)
                gruplar.setdefault(ad, []).append(k)
                kapsanan.add(k.id)

        satirlar = []
        for ad, kayitlar in gruplar.items():
            onceki, sonraki = ad.split("→", 1)
            dogrulanmis = [k for k in kayitlar if
                           k.karsi_olgusal_sonuc in ("TP", "STOP")]
            stop = sum(k.karsi_olgusal_sonuc == "STOP" for k in dogrulanmis)
            tp = sum(k.karsi_olgusal_sonuc == "TP" for k in dogrulanmis)
            if onceki in sira and sonraki in sira:
                yon = ("zayifladi" if sira[sonraki] > sira[onceki]
                       else "guclendi")
            else:
                yon = "siniflandirilmadi"
            n = len(dogrulanmis)
            satirlar.append({
                "gecis": ad, "yon": yon, "setup_sayisi": len(kayitlar),
                "dogrulanmis_n": n,
                "engellenen_stop": stop if n else None,
                "olasi_tp": tp if n else None,
                "kapsama_yuzde": round(100 * n / len(kayitlar), 1),
                "claim_allowed": bool(n),
            })
        satirlar.sort(key=lambda x: (-x["setup_sayisi"], x["gecis"]))
        filtreli = sum(k.durum == "Filtered" for k in self.kayitlar)
        return {
            "gecisler": satirlar,
            "gecisli_setup_sayisi": len(kapsanan),
            "filtered_setup_sayisi": filtreli,
            "gecmis_kapsama_yuzde": round(100 * len(kapsanan) / filtreli, 1)
            if filtreli else 0.0,
            "tekrar_politikasi": "same-transition-on-same-setup-counted-once",
            "causality_claim": "not-made",
        }

    def htf_denetim_ozeti(self) -> dict:
        """BigE HTF çatışma filtresini snapshot ve sonuçlarla denetlenebilir yap."""
        kayitlar = [k for k in self.kayitlar if k.durum == "Filtered" and
                    k.durum_nedeni == "htf-conflict"]

        def istatistik(secici) -> list[dict]:
            gruplar: dict[str, list[Kayit]] = {}
            for k in kayitlar:
                ad = str(secici(k) or "Bilinmiyor")
                gruplar.setdefault(ad, []).append(k)
            out = []
            for ad, grup in gruplar.items():
                dogrulanmis = [k for k in grup if
                               k.karsi_olgusal_sonuc in ("TP", "STOP")]
                stop = sum(k.karsi_olgusal_sonuc == "STOP" for k in dogrulanmis)
                tp = sum(k.karsi_olgusal_sonuc == "TP" for k in dogrulanmis)
                n = len(dogrulanmis)
                out.append({
                    "ad": ad, "setup_sayisi": len(grup), "dogrulanmis_n": n,
                    "engellenen_stop": stop if n else None,
                    "olasi_tp": tp if n else None,
                    "kapsama_yuzde": round(100 * n / len(grup), 1),
                    "claim_allowed": bool(n),
                })
            return sorted(out, key=lambda x: (-x["setup_sayisi"], x["ad"]))

        def gecisler(k: Kayit) -> list[str]:
            kalite = [str(x.get("kalite", "") or "") for x in k.kalite_gecmisi]
            return list(dict.fromkeys(
                f"{a}→{b}" for a, b in zip(kalite, kalite[1:])
                if a and b and a != b))

        dogrulanmis_n = sum(k.karsi_olgusal_sonuc in ("TP", "STOP")
                            for k in kayitlar)
        return {
            "setup_sayisi": len(kayitlar),
            "dogrulanmis_n": dogrulanmis_n,
            "kapsama_yuzde": round(100 * dogrulanmis_n / len(kayitlar), 1)
            if kayitlar else 0.0,
            "kirilimlar": {
                "tf_esleme": istatistik(
                    lambda k: f"{k.interval}→{k.htf_tf or 'Bilinmiyor'}"),
                "ana_tf_yapi": istatistik(lambda k: k.ana_tf_yapi),
                "htf_yapi": istatistik(lambda k: k.htf_yapi),
                "ltf_yapi": istatistik(lambda k: k.ltf_yapi),
                "ltf_onay": istatistik(lambda k: k.ltf_onay),
                "motor": istatistik(lambda k: k.kaynak),
                "kalite": istatistik(lambda k: k.kalite),
            },
            "kayitlar": [{
                "id": k.id, "sembol": k.sembol, "interval": k.interval,
                "taraf": k.taraf, "motor": k.kaynak, "kalite": k.kalite,
                "ana_tf_yapi": k.ana_tf_yapi or "Bilinmiyor",
                "htf_tf": k.htf_tf or "Bilinmiyor",
                "htf_yapi": k.htf_yapi or "Bilinmiyor",
                "ltf_tf": k.ltf_tf or "Bilinmiyor", "ltf_yapi": k.ltf_yapi,
                "ltf_onay": k.ltf_onay,
                "kalite_gecisleri": gecisler(k),
                "karsi_olgusal_durum": k.karsi_olgusal_durum or "Takip Başlamadı",
                "karsi_olgusal_sonuc": k.karsi_olgusal_sonuc or None,
            } for k in list(reversed(kayitlar))[:30]],
            "mapping_origin": "BigE-interpretation",
            "current_implementation": "upper-veto-plus-lower-observation",
            "ltf_status": "observation-only",
            "miraz_exact_mapping": "undisclosed-by-archive",
            "causality_claim": "not-made",
        }

    def ltf_gozlem_ozeti(self) -> dict:
        """Filtered setuplarda karar-dışı LTF gözlemi ile sonucu eşleştir."""
        filtreli = [k for k in self.kayitlar if k.durum == "Filtered"]
        gecerli_onay = {"trend-devam", "zayiflama", "notr"}
        gozlemli = [k for k in filtreli if k.ltf_onay in gecerli_onay]

        def istatistik(secici, havuz=None) -> list[dict]:
            kayit_havuzu = gozlemli if havuz is None else havuz
            gruplar: dict[str, list[Kayit]] = {}
            for k in kayit_havuzu:
                ad = str(secici(k) or "Bilinmiyor")
                gruplar.setdefault(ad, []).append(k)
            out = []
            for ad, grup in gruplar.items():
                dogrulanmis = [k for k in grup if
                               k.karsi_olgusal_sonuc in ("TP", "STOP")]
                stop = sum(k.karsi_olgusal_sonuc == "STOP" for k in dogrulanmis)
                tp = sum(k.karsi_olgusal_sonuc == "TP" for k in dogrulanmis)
                n = len(dogrulanmis)
                out.append({
                    "ad": ad, "setup_sayisi": len(grup), "dogrulanmis_n": n,
                    "counterfactual_stop": stop if n else None,
                    "counterfactual_tp": tp if n else None,
                    # Bu bir WR değil; yalnız doğrulanmış gözlem dağılımıdır.
                    "tp_payi_yuzde": round(100 * tp / n, 1) if n else None,
                    "sonuc_kapsama_yuzde": round(100 * n / len(grup), 1),
                    "claim_allowed": bool(n),
                })
            return sorted(out, key=lambda x: (-x["setup_sayisi"], x["ad"]))

        dogrulanmis_n = sum(k.karsi_olgusal_sonuc in ("TP", "STOP")
                            for k in gozlemli)
        return {
            "filtered_setup_sayisi": len(filtreli),
            "gozlemli_setup_sayisi": len(gozlemli),
            "gozlem_kapsama_yuzde": round(100 * len(gozlemli) / len(filtreli), 1)
            if filtreli else 0.0,
            "dogrulanmis_n": dogrulanmis_n,
            "sonuc_kapsama_yuzde": round(100 * dogrulanmis_n / len(gozlemli), 1)
            if gozlemli else 0.0,
            "siniflar": istatistik(lambda k: k.ltf_onay),
            "kirilimlar": {
                "tf_esleme": istatistik(
                    lambda k: f"{k.interval}→{k.ltf_tf or 'Bilinmiyor'}"),
                "motor": istatistik(lambda k: k.kaynak),
                "kalite": istatistik(lambda k: k.kalite),
            },
            "karar_etkisi": "none-observation-only",
            "metric_name": "verified-counterfactual-distribution-not-win-rate",
            "mapping_origin": "BigE-adjacent-observed-TF-interpretation",
            "miraz_exact_mapping": "undisclosed-by-archive",
            "causality_claim": "not-made",
        }

    def harmonik_pattern_ozeti(self) -> dict:
        """Harmonik kayıtları desen bazında; gerçek ve karşı-olgusal ayrı denetle."""
        harm = [k for k in self.kayitlar if k.pattern]
        gruplar: dict[str, list[Kayit]] = {}
        for k in harm:
            gruplar.setdefault(k.pattern or "Unknown", []).append(k)
        satirlar = []
        for pattern, kayitlar in gruplar.items():
            journal = [k for k in kayitlar if k.durum in ("TP", "STOP")]
            j_tp = sum(k.durum == "TP" for k in journal)
            j_stop = sum(k.durum == "STOP" for k in journal)
            cf = [k for k in kayitlar
                  if k.karsi_olgusal_sonuc in ("TP", "STOP")]
            cf_tp = sum(k.karsi_olgusal_sonuc == "TP" for k in cf)
            cf_stop = sum(k.karsi_olgusal_sonuc == "STOP" for k in cf)
            detayli = [k for k in kayitlar if k.harmonik_detay]
            kaliteler = [float(k.harmonik_detay.get("motor_kalite"))
                         for k in detayli
                         if k.harmonik_detay.get("motor_kalite") is not None]
            satirlar.append({
                "pattern": pattern, "setup_sayisi": len(kayitlar),
                "journal_n": len(journal), "journal_tp": j_tp,
                "journal_stop": j_stop,
                "journal_wr": round(j_tp / len(journal) * 100, 1) if journal else 0.0,
                "counterfactual_n": len(cf), "counterfactual_tp": cf_tp,
                "counterfactual_stop": cf_stop,
                "detayli_snapshot_n": len(detayli),
                "motor_kalite_ortalama": round(sum(kaliteler) / len(kaliteler), 1)
                if kaliteler else None,
                "cancelled_cd": sum(
                    k.durum == "Cancelled" and
                    k.durum_nedeni == "harmonic-pattern-changed-or-disappeared"
                    for k in kayitlar),
            })
        satirlar.sort(key=lambda x: (-x["setup_sayisi"], x["pattern"]))
        return {
            "patternler": satirlar, "harmonik_setup_sayisi": len(harm),
            "detayli_snapshot_sayisi": sum(bool(k.harmonik_detay) for k in harm),
            "desteklenen_patternler": [
                "Gartley", "Bat", "Butterfly", "Crab", "Deep Crab",
                "AB=CD", "Shark", "Cypher"],
            "snapshot_scope": "new-records-only-no-legacy-backfill",
            "ratio_origin": "BigE-harmonic-engine-not-Miraz-hidden-filters",
            "minimum_sample": None,
            "recommendation_status": "locked-undisclosed-threshold",
            "causality_claim": "not-made",
        }

    def risk_modu_ozeti(self) -> dict:
        """Risk modu snapshot'larını gerçek Journal sonuçlarıyla ayrı göster."""
        gruplar: dict[str, list[Kayit]] = {}
        for k in self.kayitlar:
            gruplar.setdefault(k.risk_modu or "legacy-unknown", []).append(k)
        rows = []
        for mod, kayitlar in gruplar.items():
            journal = [k for k in kayitlar if k.durum in ("TP", "STOP")]
            tp = sum(k.durum == "TP" for k in journal)
            stop = sum(k.durum == "STOP" for k in journal)
            rrler = sorted({k.risk_rr_hedef for k in kayitlar
                            if k.risk_rr_hedef is not None})
            rows.append({
                "risk_modu": mod, "setup_sayisi": len(kayitlar),
                "journal_n": len(journal), "tp": tp, "stop": stop,
                "wr": round(100 * tp / len(journal), 1) if journal else None,
                "toplam_r": round(sum(k.r_sonuc for k in journal), 2),
                "rr_hedefleri": rrler,
                "r_dolar_snapshot_n": sum(k.risk_r_dolar is not None
                                             for k in kayitlar),
            })
        rows.sort(key=lambda x: (-x["setup_sayisi"], x["risk_modu"]))
        return {
            "modlar": rows,
            "kanitli_modlar": {"guvenli": 1.0, "dengeli": 2.0,
                                "riskli": 3.5},
            "kanit_tweet_id": "2062336764656677002",
            "legacy_backfill": False,
            "custom_mode_origin": "BigE-not-terminalMiraz",
        }

    def temas_davranisi_ozeti(self) -> dict:
        """PA temas snapshot'larını Journal sonuçlarıyla dokunuş kovalarında göster."""
        kovalar = {"0": [], "1": [], "2": [], "3+": []}
        kapsam = 0
        for k in self.kayitlar:
            if k.kaynak not in ("Price Action", "Scanner"):
                continue
            detay = k.temas_detay or {}
            if not detay:
                continue
            kapsam += 1
            toplam = int(detay.get("toplam", 0) or 0)
            kovalar[str(toplam) if toplam < 3 else "3+"].append(k)
        rows = []
        for ad, kayitlar in kovalar.items():
            journal = [k for k in kayitlar if k.durum in ("TP", "STOP")]
            tp = sum(k.durum == "TP" for k in journal)
            stop = sum(k.durum == "STOP" for k in journal)
            rows.append({
                "dokunus": ad, "setup_sayisi": len(kayitlar),
                "journal_n": len(journal), "tp": tp, "stop": stop,
                "wr": round(100 * tp / len(journal), 1) if journal else None,
                "toplam_r": round(sum(k.r_sonuc for k in journal), 2),
            })
        return {
            "kovalar": rows, "snapshot_kapsami": kapsam,
            "kanit_tweet_id": "2063838608230883776",
            "kanit_gorseller": ["HKQ4_NFWgAEVWK2.png", "HKQ5As9XkAAP1e0.png"],
            "legacy_backfill": False,
            "sayim_modeli": "BigE-heuristic-not-disclosed-by-archive",
            "guven_puani_miraz_kurali": False,
        }

    def pa_alt_tur_ozeti(self) -> dict:
        """Price Action kayıtlarını çok-etiketli setup türlerine göre denetle."""
        pa = [k for k in self.kayitlar if k.kaynak == "Price Action"]
        gruplar: dict[str, list[Kayit]] = {}
        for k in pa:
            turler = list(dict.fromkeys(k.setup_turleri or ["Unclassified"]))
            for tur in turler:
                gruplar.setdefault(tur, []).append(k)
        satirlar = []
        for tur, kayitlar in gruplar.items():
            journal = [k for k in kayitlar if k.durum in ("TP", "STOP")]
            j_tp = sum(k.durum == "TP" for k in journal)
            j_stop = sum(k.durum == "STOP" for k in journal)
            filtreli = [k for k in kayitlar if k.durum == "Filtered"]
            cf = [k for k in filtreli if k.karsi_olgusal_sonuc in ("TP", "STOP")]
            cf_tp = sum(k.karsi_olgusal_sonuc == "TP" for k in cf)
            cf_stop = sum(k.karsi_olgusal_sonuc == "STOP" for k in cf)
            satirlar.append({
                "tur": tur, "setup_sayisi": len(kayitlar),
                "journal_n": len(journal), "journal_tp": j_tp,
                "journal_stop": j_stop,
                "journal_wr": round(100 * j_tp / len(journal), 1)
                if journal else None,
                "filtered_n": len(filtreli), "counterfactual_n": len(cf),
                "counterfactual_tp": cf_tp if cf else None,
                "counterfactual_stop": cf_stop if cf else None,
                "counterfactual_kapsama_yuzde": round(
                    100 * len(cf) / len(filtreli), 1) if filtreli else 0.0,
            })
        satirlar.sort(key=lambda x: (-x["setup_sayisi"], x["tur"]))
        etiketli = sum(bool(k.setup_turleri) for k in pa)
        return {
            "pa_setup_sayisi": len(pa), "etiketli_setup_sayisi": etiketli,
            "etiket_kapsama_yuzde": round(100 * etiketli / len(pa), 1)
            if pa else 0.0,
            "turler": satirlar,
            "multi_label": True,
            "rows_are_not_additive": True,
            "ob_label": "OB Proxy",
            "ob_origin": "BigE-zone-heuristic-not-exact-order-block",
            "classification_origin": "BigE-detectors-mapped-to-archive-concepts",
            "miraz_exact_subtype_classifier": "undisclosed-by-archive",
            "causality_claim": "not-made",
        }

    def harmonik_capraz_ozeti(self) -> dict:
        """Pattern × TF/yön/kalite/PRZ/C→D hücrelerini açıklayıcı denetle."""
        harm = [k for k in self.kayitlar if k.pattern]
        hucreler: dict[tuple[str, str, str], list[Kayit]] = {}

        def motor_kalite(k: Kayit) -> str:
            q = k.harmonik_detay.get("motor_kalite") if k.harmonik_detay else None
            return "legacy-unknown" if q is None else f"{round(float(q), 1)}"

        for k in harm:
            cd = ("cancelled-pattern-changed-or-disappeared"
                  if k.durum == "Cancelled" and
                  k.durum_nedeni == "harmonic-pattern-changed-or-disappeared"
                  else "no-recorded-cd-cancellation")
            prz = ((k.harmonik_detay.get("prz") or {}).get("kaynak")
                   if k.harmonik_detay else None) or "legacy-unknown"
            boyutlar = {
                "timeframe": k.interval or "Unknown",
                "side": k.taraf or "Unknown",
                "journal-quality": k.kalite or "Unknown",
                "motor-quality-exact": motor_kalite(k),
                "prz-snapshot": prz,
                "cd-status": cd,
            }
            for boyut, deger in boyutlar.items():
                hucreler.setdefault((k.pattern, boyut, deger), []).append(k)

        rows = []
        for (pattern, boyut, deger), kayitlar in hucreler.items():
            journal = [k for k in kayitlar if k.durum in ("TP", "STOP")]
            j_tp = sum(k.durum == "TP" for k in journal)
            j_stop = sum(k.durum == "STOP" for k in journal)
            filtreli = [k for k in kayitlar if k.durum == "Filtered"]
            cf = [k for k in filtreli
                  if k.karsi_olgusal_sonuc in ("TP", "STOP")]
            cf_tp = sum(k.karsi_olgusal_sonuc == "TP" for k in cf)
            cf_stop = sum(k.karsi_olgusal_sonuc == "STOP" for k in cf)
            kapsam = round(100 * len(cf) / len(filtreli), 1) if filtreli else 0.0
            if filtreli and len(cf) < len(filtreli):
                kilit = "locked-incomplete-counterfactual-coverage"
            elif not journal and not cf:
                kilit = "locked-no-verified-outcomes"
            else:
                kilit = "locked-minimum-threshold-undisclosed"
            rows.append({
                "pattern": pattern, "boyut": boyut, "deger": deger,
                "setup_sayisi": len(kayitlar), "journal_n": len(journal),
                "journal_tp": j_tp, "journal_stop": j_stop,
                "journal_wr": round(100 * j_tp / len(journal), 1)
                if journal else None,
                "filtered_n": len(filtreli), "counterfactual_n": len(cf),
                "counterfactual_tp": cf_tp if cf else None,
                "counterfactual_stop": cf_stop if cf else None,
                "counterfactual_kapsama_yuzde": kapsam,
                "claim_state": kilit, "recommendation_allowed": False,
            })
        rows.sort(key=lambda x: (-x["setup_sayisi"], x["pattern"],
                                 x["boyut"], x["deger"]))
        return {
            "hucreler": rows, "hucre_sayisi": len(rows),
            "dimensions": ["timeframe", "side", "journal-quality",
                           "motor-quality-exact", "prz-snapshot", "cd-status"],
            "minimum_sample": None,
            "minimum_sample_origin": "undisclosed-by-archive",
            "motor_quality_origin": "BigE-engine-exact-value-no-bucketing",
            "legacy_backfill": False, "automatic_recommendation": False,
            "causality_claim": "not-made",
        }

    def pa_capraz_ozeti(self) -> dict:
        """PA alt türlerini TF/yön/MTF/kalite geçişiyle çapraz denetle."""
        pa = [k for k in self.kayitlar if k.kaynak == "Price Action"]
        hucreler: dict[tuple[str, str, str], list[Kayit]] = {}

        def kalite_gecisleri(k: Kayit) -> list[str]:
            kalite = [str(x.get("kalite", "") or "") for x in k.kalite_gecmisi]
            out = list(dict.fromkeys(
                f"{a}→{b}" for a, b in zip(kalite, kalite[1:])
                if a and b and a != b))
            return out or ["No Transition History"]

        for k in pa:
            turler = list(dict.fromkeys(k.setup_turleri or ["Unclassified"]))
            htf = ("conflict-filtered" if k.durum_nedeni == "htf-conflict"
                   else k.htf_yapi or "Unknown")
            boyutlar = {
                "timeframe": [k.interval or "Unknown"],
                "side": [k.taraf or "Unknown"],
                "htf": [htf],
                "ltf": [k.ltf_onay or "not-available"],
                "quality-transition": kalite_gecisleri(k),
            }
            for tur in turler:
                for boyut, degerler in boyutlar.items():
                    for deger in degerler:
                        hucreler.setdefault((tur, boyut, deger), []).append(k)

        rows = []
        for (tur, boyut, deger), kayitlar in hucreler.items():
            journal = [k for k in kayitlar if k.durum in ("TP", "STOP")]
            j_tp = sum(k.durum == "TP" for k in journal)
            j_stop = sum(k.durum == "STOP" for k in journal)
            filtreli = [k for k in kayitlar if k.durum == "Filtered"]
            cf = [k for k in filtreli if k.karsi_olgusal_sonuc in ("TP", "STOP")]
            cf_tp = sum(k.karsi_olgusal_sonuc == "TP" for k in cf)
            cf_stop = sum(k.karsi_olgusal_sonuc == "STOP" for k in cf)
            cf_kapsama = round(100 * len(cf) / len(filtreli), 1) if filtreli else 0.0
            if filtreli and len(cf) < len(filtreli):
                kilit = "locked-incomplete-counterfactual-coverage"
            elif not journal and not cf:
                kilit = "locked-no-verified-outcomes"
            else:
                kilit = "locked-minimum-threshold-undisclosed"
            rows.append({
                "tur": tur, "boyut": boyut, "deger": deger,
                "setup_sayisi": len(kayitlar),
                "journal_n": len(journal), "journal_tp": j_tp,
                "journal_stop": j_stop,
                "journal_wr": round(100 * j_tp / len(journal), 1)
                if journal else None,
                "filtered_n": len(filtreli), "counterfactual_n": len(cf),
                "counterfactual_tp": cf_tp if cf else None,
                "counterfactual_stop": cf_stop if cf else None,
                "counterfactual_kapsama_yuzde": cf_kapsama,
                "claim_state": kilit, "recommendation_allowed": False,
            })
        rows.sort(key=lambda x: (-x["setup_sayisi"], x["tur"],
                                 x["boyut"], x["deger"]))
        return {
            "hucreler": rows, "hucre_sayisi": len(rows),
            "dimensions": ["timeframe", "side", "htf", "ltf",
                           "quality-transition"],
            "minimum_sample": None,
            "minimum_sample_origin": "undisclosed-by-archive",
            "incomplete_counterfactual_claim": "locked",
            "automatic_recommendation": False,
            "multi_label": True, "rows_are_not_additive": True,
            "causality_claim": "not-made",
        }

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
            "parite_karakter": self.parite_hafiza(),
            "konsept": o_buckets if (o_buckets := self.ozet()["buckets"]) else {},
        }

    def parite_hafiza(self) -> dict:
        """Scanner Memory için pariteye özel Price Action performansı.

        Tweet 2061490944713601191 UNI 11/3 → 77 skor, XLM 5/8 → 38 skor
        örneklerini ve 20+ kaydın daha sağlıklı olacağını açıklar. Kesin skor ve
        delist formülü açıklanmadığından yalnız ampirik metrik/olgunluk üretilir;
        otomatik delist kararı verilmez.
        """
        d: dict[str, dict] = {}
        for k in self.kayitlar:
            if k.durum not in ("TP", "STOP"):
                continue
            if getattr(k, "kaynak", "Price Action") != "Price Action":
                continue
            e = d.setdefault(k.sembol, {"tp": 0, "stop": 0, "r": 0.0})
            e["tp" if k.durum == "TP" else "stop"] += 1
            e["r"] += k.r_sonuc
        for e in d.values():
            n = e["tp"] + e["stop"]
            e["n"] = n
            e["wr"] = round(100 * e["tp"] / n, 1) if n else 0.0
            e["r"] = round(e["r"], 2)
            e["ornek_durumu"] = "mature" if n >= 20 else "learning"
            e["miraz_score"] = None
            e["score_model"] = "terminalMiraz-formula-undisclosed"
            e["auto_delist"] = False
        return d

    def harmonik_parite_hafiza(self) -> dict:
        """Harmonic Memory Lab için pariteye özel, PA'dan ayrı performans."""
        d: dict[str, dict] = {}
        for k in self.kayitlar:
            if k.durum not in ("TP", "STOP") or k.kaynak != "Harmonik":
                continue
            e = d.setdefault(k.sembol, {"tp": 0, "stop": 0, "r": 0.0})
            e["tp" if k.durum == "TP" else "stop"] += 1
            e["r"] += k.r_sonuc
        for e in d.values():
            n = e["tp"] + e["stop"]
            e["n"] = n
            e["wr"] = round(100 * e["tp"] / n, 1) if n else 0.0
            e["r"] = round(e["r"], 2)
            e["ornek_durumu"] = "mature" if n >= 20 else "learning"
            e["miraz_score"] = None
            e["score_model"] = "terminalMiraz-formula-undisclosed"
            e["auto_delist"] = False
        return d

    def parite_konsept_hafiza(self) -> list:
        """Scanner Memory için PA parite×konsept sonuç matrisi."""
        d: dict[tuple[str, str], dict] = {}
        for k in self.kayitlar:
            if k.durum not in ("TP", "STOP") or k.kaynak != "Price Action":
                continue
            for konsept in dict.fromkeys(k.konseptler or []):
                e = d.setdefault((k.sembol, konsept), {
                    "sembol": k.sembol, "konsept": konsept,
                    "tp": 0, "stop": 0, "r": 0.0,
                })
                e["tp" if k.durum == "TP" else "stop"] += 1
                e["r"] += k.r_sonuc
        rows = []
        for e in d.values():
            n = e["tp"] + e["stop"]
            e["n"] = n
            e["wr"] = round(100 * e["tp"] / n, 1) if n else 0.0
            e["r"] = round(e["r"], 2)
            e["ornek_durumu"] = "mature" if n >= 20 else "learning"
            e["miraz_score"] = None
            e["auto_delist"] = False
            rows.append(e)
        return sorted(rows, key=lambda x: (-x["n"], -x["wr"],
                                           x["sembol"], x["konsept"]))

    def tf_motor_hafiza(self) -> list:
        """Sonuçlanan kayıtları PA/Harmonik motoru ve TF bazında ayır."""
        d: dict[tuple[str, str], dict] = {}
        for k in self.kayitlar:
            if k.durum not in ("TP", "STOP"):
                continue
            if k.kaynak not in ("Price Action", "Harmonik"):
                continue
            e = d.setdefault((k.kaynak, k.interval), {
                "motor": k.kaynak, "interval": k.interval,
                "tp": 0, "stop": 0, "r": 0.0,
            })
            e["tp" if k.durum == "TP" else "stop"] += 1
            e["r"] += k.r_sonuc
        rows = []
        for e in d.values():
            n = e["tp"] + e["stop"]
            e["n"] = n
            e["wr"] = round(100 * e["tp"] / n, 1) if n else 0.0
            e["r"] = round(e["r"], 2)
            e["observation_only"] = True
            e["auto_filter"] = False
            rows.append(e)
        return sorted(rows, key=lambda x: (x["motor"], x["interval"]))

    def entry_kalite_hafiza(self) -> dict:
        """Gerçek entry snapshot'ını sonuçlarla kalite/güven bazında eşle."""
        kalite: dict[tuple[str, str], dict] = {}
        guven: dict[tuple[str, str], dict] = {}
        kapsam = 0
        for k in self.kayitlar:
            if k.durum not in ("TP", "STOP"):
                continue
            if k.entry_kalite is None or k.entry_guven is None:
                continue
            kapsam += 1
            band_alt = max(0, min(90, int(k.entry_guven // 10) * 10))
            band = f"{band_alt}-{band_alt + 9}"
            for depo, anahtar, ad in (
                    (kalite, (k.kaynak, k.entry_kalite), k.entry_kalite),
                    (guven, (k.kaynak, band), band)):
                e = depo.setdefault(anahtar, {
                    "motor": k.kaynak, "ad": ad,
                    "tp": 0, "stop": 0, "r": 0.0,
                })
                e["tp" if k.durum == "TP" else "stop"] += 1
                e["r"] += k.r_sonuc
        def bitir(depo):
            rows = []
            for e in depo.values():
                n = e["tp"] + e["stop"]
                e["n"] = n
                e["wr"] = round(100 * e["tp"] / n, 1) if n else 0.0
                e["r"] = round(e["r"], 2)
                rows.append(e)
            return sorted(rows, key=lambda x: (x["motor"], x["ad"]))
        return {
            "kalite": bitir(kalite), "guven_bandi": bitir(guven),
            "snapshot_kapsami": kapsam, "legacy_backfill": False,
            "guven_bandi_origin": "BigE-observation-bucket-not-Miraz-threshold",
            "auto_filter": False,
        }

    def entry_hacim_hafiza(self) -> dict:
        """Entry barı hacim oranını sonuçlarla salt gözlem olarak eşle."""
        gruplar: dict[tuple[str, str], dict] = {}
        kapsam = 0
        for k in self.kayitlar:
            if k.durum not in ("TP", "STOP") or k.entry_hacim_oran is None:
                continue
            kapsam += 1
            oran = k.entry_hacim_oran
            if oran < 1:
                band = "<1.0x"
            elif oran < 1.5:
                band = "1.0-1.49x"
            elif oran < 2:
                band = "1.5-1.99x"
            else:
                band = ">=2.0x"
            anahtar = (k.kaynak, band)
            e = gruplar.setdefault(anahtar, {
                "motor": k.kaynak, "ad": band,
                "tp": 0, "stop": 0, "r": 0.0,
            })
            e["tp" if k.durum == "TP" else "stop"] += 1
            e["r"] += k.r_sonuc
        rows = []
        sira = {"<1.0x": 0, "1.0-1.49x": 1, "1.5-1.99x": 2, ">=2.0x": 3}
        for e in gruplar.values():
            n = e["tp"] + e["stop"]
            e["n"] = n
            e["wr"] = round(100 * e["tp"] / n, 1) if n else 0.0
            e["r"] = round(e["r"], 2)
            rows.append(e)
        rows.sort(key=lambda x: (x["motor"], sira[x["ad"]]))
        return {
            "oran_bandi": rows, "snapshot_kapsami": kapsam,
            "ratio_basis": "entry-bar-volume/prior-up-to-20-bar-median",
            "ratio_basis_origin": "BigE-observation-normalization-not-Miraz-rule",
            "band_origin": "BigE-observation-bucket-not-Miraz-threshold",
            "legacy_backfill": False, "auto_filter": False,
        }

    def adaydan_entry_kalite_hafiza(self) -> dict:
        """İlk aday snapshot'ından gerçek entry snapshot'ına kalite yolunu ölç."""
        gecisler: dict[tuple[str, str], dict] = {}
        guven_yonu: dict[tuple[str, str], dict] = {}
        kapsam = 0
        for k in self.kayitlar:
            if k.durum not in ("TP", "STOP"):
                continue
            if k.entry_kalite is None or k.entry_guven is None:
                continue
            if not k.kalite_gecmisi:
                continue
            ilk = k.kalite_gecmisi[0]
            if ilk.get("olay") != "candidate-quality-snapshot":
                continue
            if ilk.get("kalite") is None or ilk.get("guven") is None:
                continue
            kapsam += 1
            gecis = f'{ilk["kalite"]}→{k.entry_kalite}'
            delta = round(float(k.entry_guven) - float(ilk["guven"]), 2)
            yon = "YÜKSELDİ" if delta > 0 else "DÜŞTÜ" if delta < 0 else "AYNI"
            for depo, anahtar, ad in (
                    (gecisler, (k.kaynak, gecis), gecis),
                    (guven_yonu, (k.kaynak, yon), yon)):
                e = depo.setdefault(anahtar, {
                    "motor": k.kaynak, "ad": ad,
                    "tp": 0, "stop": 0, "r": 0.0,
                    "guven_delta_toplam": 0.0,
                })
                e["tp" if k.durum == "TP" else "stop"] += 1
                e["r"] += k.r_sonuc
                e["guven_delta_toplam"] += delta

        def bitir(depo):
            rows = []
            for e in depo.values():
                n = e["tp"] + e["stop"]
                e["n"] = n
                e["wr"] = round(100 * e["tp"] / n, 1) if n else 0.0
                e["r"] = round(e["r"], 2)
                e["ortalama_guven_delta"] = round(
                    e.pop("guven_delta_toplam") / n, 2) if n else 0.0
                rows.append(e)
            return sorted(rows, key=lambda x: (x["motor"], x["ad"]))

        return {
            "kalite_gecisi": bitir(gecisler),
            "guven_yonu": bitir(guven_yonu),
            "snapshot_kapsami": kapsam,
            "basis": "first-candidate-snapshot-to-real-entry-snapshot",
            "direction_origin": "exact-delta-sign-no-Miraz-threshold",
            "legacy_backfill": False, "auto_filter": False,
        }

    def entry_bekleme_hafiza(self) -> dict:
        """Gerçek entry'ye kadar gözlenen kesin bar sayısını sonuçla eşle."""
        gruplar: dict[tuple[str, str, int, int | None], dict] = {}
        kapsam = 0
        for k in self.kayitlar:
            if k.durum not in ("TP", "STOP"):
                continue
            if k.entry_bekleme_bar is None:
                continue
            kapsam += 1
            anahtar = (k.kaynak, k.interval, k.entry_bekleme_bar,
                       k.entry_bekleme_limiti)
            e = gruplar.setdefault(anahtar, {
                "motor": k.kaynak,
                "ad": f"{k.interval} · {k.entry_bekleme_bar} bar",
                "interval": k.interval,
                "bekleme_bar": k.entry_bekleme_bar,
                "bekleme_limiti": k.entry_bekleme_limiti,
                "tp": 0, "stop": 0, "r": 0.0,
            })
            e["tp" if k.durum == "TP" else "stop"] += 1
            e["r"] += k.r_sonuc
        rows = []
        for e in gruplar.values():
            n = e["tp"] + e["stop"]
            e["n"] = n
            e["wr"] = round(100 * e["tp"] / n, 1) if n else 0.0
            e["r"] = round(e["r"], 2)
            rows.append(e)
        rows.sort(key=lambda x: (
            x["motor"], x["interval"], x["bekleme_bar"],
            x["bekleme_limiti"] if x["bekleme_limiti"] is not None else -1))
        return {
            "kesin_bar": rows, "snapshot_kapsami": kapsam,
            "basis": "bars-observed-after-candidate-open-through-entry-bar",
            "bucketing": False,
            "expiry_limit_origin": "BigE-runtime-setting-not-Miraz-duration",
            "miraz_expiry_duration": "undisclosed-by-archive",
            "legacy_backfill": False, "auto_filter": False,
        }

    def takvim_veri(self) -> dict:
        """Günlük agregat: her kapanış günü için TP/STOP/R + PA/Harmonik ayrımı.

        Döndürür: {"YYYY-MM-DD": {tp, stop, expired, r, pa:{tp,stop,r},
                                   harmonik:{tp,stop,r}, satirlar:[{...}]}}
        """
        from datetime import datetime, timezone, timedelta
        gunler: dict[str, dict] = {}
        for k in self.kayitlar:
            if k.aktif or not k.kapanis_zaman:
                continue
            gun = k.kapanis_zaman[:10]
            e = gunler.setdefault(gun, {
                "tp": 0, "stop": 0, "expired": 0, "r": 0.0,
                "pa":      {"tp": 0, "stop": 0, "r": 0.0},
                "harmonik": {"tp": 0, "stop": 0, "r": 0.0},
                "satirlar": [],
            })
            if k.durum == "TP":
                e["tp"] += 1
            elif k.durum == "STOP":
                e["stop"] += 1
            else:
                e["expired"] += 1
            e["r"] += k.r_sonuc
            kaynak = getattr(k, "kaynak", "Price Action")
            if kaynak in ("Price Action", "Harmonik"):
                alt = e["pa"] if kaynak == "Price Action" else e["harmonik"]
                if k.durum == "TP":
                    alt["tp"] += 1
                elif k.durum == "STOP":
                    alt["stop"] += 1
                alt["r"] += k.r_sonuc
            e["satirlar"].append({
                "id": k.id, "sembol": k.sembol, "interval": k.interval,
                "taraf": k.taraf, "durum": k.durum, "r_sonuc": k.r_sonuc,
                "kaynak": kaynak, "giris": k.giris, "stop": k.stop,
                "hedef": k.hedef, "kapanis": k.kapanis_zaman,
            })
        for g in gunler.values():
            g["r"] = round(g["r"], 2)
            for alt in ("pa", "harmonik"):
                g[alt]["r"] = round(g[alt]["r"], 2)
        return gunler

    def perf_curve(self) -> dict:
        """Performance Intelligence bugün/dün/tüm eğrisi."""
        from datetime import datetime, timezone, timedelta
        simdi = datetime.now(timezone.utc)
        bugun_str = simdi.strftime("%Y-%m-%d")
        dun_str = (simdi - timedelta(days=1)).strftime("%Y-%m-%d")

        kapali = [k for k in self.kayitlar if k.durum in ("TP", "STOP") and k.kapanis_zaman]

        def _stats(liste):
            tp = sum(1 for k in liste if k.durum == "TP")
            stop = sum(1 for k in liste if k.durum == "STOP")
            total = tp + stop
            return {"sonuc": total, "tp": tp, "sl": stop,
                    "wr": round(100 * tp / total, 1) if total else 0.0}

        return {
            "bugun": _stats([k for k in kapali if k.kapanis_zaman.startswith(bugun_str)]),
            "dun":   _stats([k for k in kapali if k.kapanis_zaman.startswith(dun_str)]),
            "tum":   _stats(kapali),
        }

    def trade_memory(self, n: int = 24) -> list:
        """Son n kapanan trade — terminalMiraz TUMU TRADE MEMORY kartları."""
        kapali = sorted(
            [k for k in self.kayitlar if not k.aktif and k.kapanis_zaman],
            key=lambda k: k.kapanis_zaman, reverse=True,
        )[:n]
        return [{
            "sembol": k.sembol, "interval": k.interval, "durum": k.durum,
            "taraf": k.taraf, "kaynak": getattr(k, "kaynak", "Price Action"),
            "r_sonuc": round(k.r_sonuc, 2), "guven": round(k.guven, 0),
            "kalite": k.kalite, "giris": k.giris,
            "kalite_gecmisi": list(getattr(k, "kalite_gecmisi", [])),
            "kalite_degisim_sayisi": max(
                0, len(getattr(k, "kalite_gecmisi", [])) - 1),
            "kapanis": (k.kapanis_zaman or "")[:16],
        } for k in kapali]

    def aktif_trade_kartlari(self) -> list:
        """Gerçek entry olmuş tüm açık işlemler; kapanan/aday kayıtlar girmez."""
        acik = sorted(
            [k for k in self.kayitlar if k.durum == "Açık"],
            key=lambda k: k.entry_zaman or k.acilis_zaman, reverse=True,
        )
        return [{
            "id": k.id, "sembol": k.sembol, "interval": k.interval,
            "durum": k.durum, "etiket": "TRADE AKTİF",
            "taraf": k.taraf,
            "kaynak": getattr(k, "kaynak", "Price Action"),
            "kalite": k.kalite, "guven": round(k.guven, 0),
            "giris": k.giris, "stop": k.stop, "hedef": k.hedef,
            "entry_zaman": (k.entry_zaman or "")[:16],
        } for k in acik]

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
                 goreceli=False, portfoy=None, defter=None, max_bar=None):
        self.semboller = semboller
        self.intervallar = intervallar
        self.taraf = taraf
        self.rr_hedef = rr_hedef
        self.cluster_hafiza = cluster_hafiza
        self.r_dolar = r_dolar
        self.gun = gun
        self.max_bekleme = max_bekleme
        self.goreceli = goreceli
        self.max_bar = max_bar
        self.portfoy = portfoy or Portfoy(r_dolar=r_dolar)
        self.defter = defter or Defter()

    def dongu(self, ilerleme=None) -> DonguSonuc:
        """Tek bir tarama-kayıt-takip turu çalıştırır.

        ilerleme: radar_tara'ya geçer — tarama sürerken canlı yüzde için.
        """
        # 1. Tara
        rapor = radar_tara(
            self.semboller, self.intervallar, r_dolar=self.r_dolar,
            gun=self.gun, cluster_hafiza=self.cluster_hafiza,
            goreceli=self.goreceli, taraf=self.taraf, rr_hedef=self.rr_hedef,
            max_bar=self.max_bar, ilerleme=ilerleme)

        # 2. Bekleyen adayları yeni kaliteyle yeniden değerlendir.
        self.defter.adaylari_yeniden_degerlendir(rapor, self.portfoy)

        # 3. Trade sinyallerini portföye + deftere ekle
        #    (önce portföy → pozisyon id'leri oluşsun, sonra defter onları bağlasın)
        eklenen = radar_sinyallerini_ekle(self.portfoy, rapor)
        for satir in rapor.satirlar:
            if satir.kategori == "Trade":
                self.defter.setup_ekle(satir, self.portfoy)

        # 4. Açık/bekleyen pozisyonları taze veriyle güncelle
        aktif_sem = {(p.sembol, p.interval) for p in self.portfoy.aktif}
        # Filtered karşı-olgusal izleme aynı taze OHLCV havuzunu kullanır; gerçek
        # portföye pozisyon eklemez ve Result Journal sonucunu değiştirmez.
        aktif_sem.update((k.sembol, k.interval) for k in self.defter.kayitlar
                         if k.durum == "Filtered" and
                         not k.karsi_olgusal_sonuc)
        df_sozluk = {}
        for (sem, ivl) in aktif_sem:
            try:
                df_sozluk[(sem, ivl)] = veri.indir(sem, ivl, gun=self.gun,
                                                    force=True,
                                                    max_bar=self.max_bar)
            except Exception:
                continue
        degisenler = self.portfoy.guncelle_hepsi(
            df_sozluk, max_bekleme=self.max_bekleme) if df_sozluk else []
        if df_sozluk:
            self.defter.filtered_karsi_olgusal_guncelle(df_sozluk)

        # 5. Defteri portföyden senkronize et
        self.defter.senkronize(self.portfoy)

        # 6. Sayaçlar + kalıcılık
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
