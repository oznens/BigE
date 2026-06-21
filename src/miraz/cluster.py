"""Cluster hafızası — setup benzerliği & geçmiş başarı (terminalMiraz katmanı).

terminalMiraz her güncel setup'ı geçmişteki BENZER setuplarla karşılaştırır:
"bu tip kurulum (A kalite + mavi daire + sağlıklı HTF) geçmişte %78 TP yaptı".
Bu, güveni teoriden değil VERİDEN besler — Price Action Labs'in cluster boyutu.

Mantık:
  • Her setup bir İMZA ile etiketlenir (kalite, mavi daire, HTF, market yapısı,
    divergence). Aynı imzalı setuplar bir "cluster"dır.
  • Geçmiş veride (look-ahead yok) her karar barında senaryo üretilir, lab
    motoruyla ileri simüle edilir (TP/STOP), sonuç imzanın cluster'ına yazılır.
  • Güncel bir setup için imzası bulunur; o cluster'ın geçmiş WR / beklenti R
    değeri raporlanır. Yetersiz örnek varsa daha kaba imzaya düşülür (fallback).

Kullanım:
    from miraz.cluster import cluster_ogren, benzerlik
    hafiza = cluster_ogren({"BTCUSDT": df_btc, "ETHUSDT": df_eth})
    sonuc = benzerlik(senaryo, hafiza)
    print(sonuc.metin)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .lab import _senaryo_noktalari, _kur_islem, _simule


# İmza yetersiz örnekliyse bu eşiğin altında kaba imzaya düşülür
_MIN_ORNEK = 8


# ---------------------------------------------------------------------------
# İmza üretimi — bir setup'ı kategorik özelliklerle etiketler
# ---------------------------------------------------------------------------

def _rr_kovasi(rr: float | None) -> str:
    if rr is None:
        return "rr?"
    if rr >= 2.5:
        return "rr≥2.5"
    if rr >= 1.5:
        return "rr1.5-2.5"
    return "rr<1.5"


def setup_imzasi(s, rr: float | None = None) -> tuple:
    """Setup'ı kategorik bir imzaya indirger (cluster anahtarı).

    Tam imza: (kalite, mavi/düz, HTF, market yapısı, divergence, rr kovası)
    """
    kalite = s.karar.kalite if getattr(s, "karar", None) is not None else "D"
    mavi = "mavi" if getattr(s, "mavi_daire", None) is not None else "düz"
    mtf = getattr(s, "mtf_yapi", None) or "nötr"
    my = getattr(s, "market_yapisi", None)
    yapi = getattr(my, "durum", "yatay") if my is not None else "yatay"
    dv = getattr(s, "divergence", None)
    diverj = getattr(dv, "tip", "yok") if dv is not None else "yok"
    return (kalite, mavi, mtf, yapi, diverj, _rr_kovasi(rr))


def _kaba_imzalar(imza: tuple) -> list:
    """Tam imzadan giderek kabalaşan fallback imza zinciri.

    Sıra: tam → (kalite, mavi, HTF) → (kalite, mavi) → (kalite,)
    """
    kalite, mavi, mtf = imza[0], imza[1], imza[2]
    return [
        imza,
        (kalite, mavi, mtf),
        (kalite, mavi),
        (kalite,),
    ]


# ---------------------------------------------------------------------------
# Cluster hafızası veri yapısı
# ---------------------------------------------------------------------------

@dataclass
class Cluster:
    imza: tuple
    n: int = 0
    tp: int = 0
    stop: int = 0
    r: float = 0.0

    @property
    def wr(self) -> float:
        d = self.tp + self.stop
        return round(100 * self.tp / d, 1) if d else 0.0

    @property
    def beklenti(self) -> float:
        d = self.tp + self.stop
        return round(self.r / d, 3) if d else 0.0


@dataclass
class ClusterHafiza:
    clusterlar: dict = field(default_factory=dict)   # imza(tuple) → Cluster
    toplam_setup: int = 0

    def kaydet_sonuc(self, imza: tuple, sonuc: str, r: float) -> None:
        c = self.clusterlar.get(imza)
        if c is None:
            c = Cluster(imza=imza)
            self.clusterlar[imza] = c
        c.n += 1
        if sonuc == "TP":
            c.tp += 1
        elif sonuc == "STOP":
            c.stop += 1
        c.r += r

    def ara(self, imza: tuple) -> tuple:
        """İmza için en spesifik yeterli-örnekli cluster'ı döndürür.

        Döndürür: (Cluster, kesinlik) — kesinlik 0(tam)..3(en kaba).
        Hiç eşleşme yoksa (None, -1).
        """
        for seviye, kaba in enumerate(_kaba_imzalar(imza)):
            # Bu kaba imzayla başlayan tüm clusterları birleştir
            birlesik = self._birlestir(kaba)
            if birlesik is not None and (birlesik.tp + birlesik.stop) >= _MIN_ORNEK:
                return birlesik, seviye
        # Yeterli örnek yoksa en kaba (kalite) yine de döndür
        kaba = (imza[0],)
        birlesik = self._birlestir(kaba)
        if birlesik is not None and (birlesik.tp + birlesik.stop) > 0:
            return birlesik, 3
        return None, -1

    def _birlestir(self, onek: tuple) -> Cluster | None:
        """Verilen önekle BAŞLAYAN tüm clusterları tek Cluster'a toplar."""
        k = len(onek)
        toplam = Cluster(imza=onek)
        bulundu = False
        for imza, c in self.clusterlar.items():
            if imza[:k] == onek:
                bulundu = True
                toplam.n += c.n
                toplam.tp += c.tp
                toplam.stop += c.stop
                toplam.r += c.r
        return toplam if bulundu else None

    # --- kalıcılık ---

    def kaydet(self, dosya: str | Path = "cluster.json") -> None:
        data = {
            "toplam_setup": self.toplam_setup,
            "clusterlar": [
                {"imza": list(c.imza), "n": c.n, "tp": c.tp,
                 "stop": c.stop, "r": round(c.r, 4)}
                for c in self.clusterlar.values()],
        }
        Path(dosya).write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def yukle(cls, dosya: str | Path = "cluster.json") -> "ClusterHafiza":
        data = json.loads(Path(dosya).read_text(encoding="utf-8"))
        h = cls(toplam_setup=data.get("toplam_setup", 0))
        for d in data.get("clusterlar", []):
            imza = tuple(d["imza"])
            h.clusterlar[imza] = Cluster(
                imza=imza, n=d["n"], tp=d["tp"], stop=d["stop"], r=d["r"])
        return h


# ---------------------------------------------------------------------------
# Öğrenme — geçmiş veriden cluster istatistiği çıkarır (look-ahead yok)
# ---------------------------------------------------------------------------

def cluster_ogren(df_sozluk: dict, adim: int = 6, max_bar: int = 60,
                  pencere: int = 800, min_bar: int = 200,
                  giris_mod: str = "orta", stop_mod: str = "fitil",
                  tp_mod: str = "ana") -> ClusterHafiza:
    """Geçmiş veride setupları imzalarına göre kümeleyip TP/STOP öğrenir.

    df_sozluk: {sembol: df}. Lab motorunun look-ahead-free altyapısını kullanır.
    """
    hafiza = ClusterHafiza()
    for sym, df in df_sozluk.items():
        noktalar = _senaryo_noktalari(df, adim, pencere, min_bar, 0.0)
        for i, s in noktalar:
            kur = _kur_islem(s, giris_mod, stop_mod, tp_mod)
            if kur is None:
                continue
            giris, stop, hedef, rr = kur
            sonuc, _ = _simule(df, i, giris, stop, hedef, max_bar)
            if sonuc not in ("TP", "STOP"):
                continue
            hafiza.toplam_setup += 1
            imza = setup_imzasi(s, rr)
            r = rr if sonuc == "TP" else -1.0
            hafiza.kaydet_sonuc(imza, sonuc, r)
    return hafiza


# ---------------------------------------------------------------------------
# Sorgu — güncel setup'ı geçmiş cluster ile karşılaştırır
# ---------------------------------------------------------------------------

@dataclass
class ClusterSonuc:
    bulundu: bool
    imza: tuple
    n: int = 0
    wr: float = 0.0
    beklenti: float = 0.0
    kesinlik: int = -1        # 0 tam imza .. 3 en kaba (kalite)
    guven_etkisi: float = 0.0 # önerilen güven düzeltmesi (puan)
    metin: str = ""


def benzerlik(senaryo, hafiza: ClusterHafiza,
              rr: float | None = None) -> ClusterSonuc:
    """Güncel setup'ın geçmiş benzerlerindeki başarısını raporlar.

    guven_etkisi: cluster WR'ına göre öneri (+/− puan), karar motoruna eklenebilir.
      WR ≥ 65 → +10 · ≥ 55 → +5 · ≤ 35 → −10 · ≤ 45 → −5 · arası 0
    Kaba eşleşmede (kesinlik yüksek) etki yarıya iner.

    rr verilmezse imza rr boyutu olmadan ('rr?') eşleşir; ara() zaten kaba
    imzaya düşebildiği için bu güvenlidir.
    """
    imza = setup_imzasi(senaryo, rr)
    cluster, kesinlik = hafiza.ara(imza)

    if cluster is None:
        return ClusterSonuc(
            bulundu=False, imza=imza,
            metin="🧬 Cluster: bu tip setup için yeterli geçmiş örnek yok.")

    wr = cluster.wr
    bek = cluster.beklenti
    n = cluster.tp + cluster.stop

    if wr >= 65:
        etki = 10.0
    elif wr >= 55:
        etki = 5.0
    elif wr <= 35:
        etki = -10.0
    elif wr <= 45:
        etki = -5.0
    else:
        etki = 0.0
    # Kaba eşleşmede güven düzeltmesini yumuşat
    if kesinlik >= 2:
        etki *= 0.5

    kesinlik_etiket = {0: "tam imza", 1: "kalite+mavi+HTF",
                       2: "kalite+mavi", 3: "kalite"}.get(kesinlik, "?")
    metin = (
        f"🧬 Cluster hafızası ({kesinlik_etiket}, {n} benzer): "
        f"WR %{wr} · beklenti {bek:+.2f}R → güven {etki:+.0f}")
    return ClusterSonuc(
        bulundu=True, imza=imza, n=n, wr=wr, beklenti=bek,
        kesinlik=kesinlik, guven_etkisi=round(etki, 1), metin=metin)
