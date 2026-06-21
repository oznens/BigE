"""Trend çizgisi ve kanal tespiti — @tradermiraz "trend devam formasyonu".

Yöntem (klasik "en iyi trend çizgisi" pivot-çifti taraması):
  - Destek çizgisi (yükselen trend): swing LOW'ları birleştiren, altında
    önemli bir kapanış ihlali olmayan, en çok dokunan doğru.
  - Direnç çizgisi (düşen trend): swing HIGH'ları birleştiren simetrik doğru.
  - Kanal: paralel destek + direnç çizgisi.

Bir doğru = fiyat(bar) = kesim + egim * (bar - bar0).
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .pivotlar import pivot_listesi


@dataclass
class TrendCizgisi:
    tip: str            # "Destek" (yükselen) / "Direnç" (düşen)
    egim: float         # bar başına fiyat değişimi
    bar0: int           # referans bar (kesim bu barda ölçülür)
    fiyat0: float       # bar0'daki doğru değeri
    dokunus: int        # doğruya değen pivot sayısı
    guncel_deger: float # son bardaki doğru değeri
    yon: str            # "Yükselen" / "Düşen" / "Yatay"

    def deger(self, bar: int) -> float:
        """Verilen bar indeksinde doğrunun fiyat değeri."""
        return self.fiyat0 + self.egim * (bar - self.bar0)


def _yon(egim: float, fiyat: float) -> str:
    esik = fiyat * 1e-4  # bar başına %0.01'den küçük eğim ≈ yatay
    if egim > esik:
        return "Yükselen"
    if egim < -esik:
        return "Düşen"
    return "Yatay"


def trend_cizgisi_bul(
    df: pd.DataFrame,
    tip: str = "Destek",
    n: int = 5,
    tolerans: float = 0.01,
    min_dokunus: int = 3,
    son_n: int = 300,
    ihlal_tol: float = 0.005,
) -> TrendCizgisi | None:
    """En iyi trend çizgisini bulur.

    Parametreler
    ------------
    tip        : "Destek" (swing low'lar, yükselen) veya "Direnç" (swing high'lar)
    tolerans   : pivotun doğruya "değmiş" sayılması için yakınlık (%1)
    min_dokunus: geçerli çizgi için minimum dokunuş sayısı
    son_n      : sadece son N barlık pencerede ara (trend çizgileri yereldir)
    ihlal_tol  : doğrunun yanlış tarafına bu %'den fazla taşan kapanış = ihlal

    Döndürür: en iyi TrendCizgisi veya None.
    """
    toplam = len(df)
    pencere_bas = max(0, toplam - son_n)
    pivlar = pivot_listesi(df, n=n)

    istenen = "L" if tip == "Destek" else "H"
    noktalar = [(i, p) for (i, p, t) in pivlar
                if t == istenen and i >= pencere_bas]
    if len(noktalar) < 2:
        return None

    kapanis = df["close"].to_numpy()
    son_bar = toplam - 1

    en_iyi: TrendCizgisi | None = None
    en_iyi_skor = (-1, -1.0)  # (dokunus, recency)

    for a in range(len(noktalar)):
        for b in range(a + 1, len(noktalar)):
            i, pi = noktalar[a]
            j, pj = noktalar[b]
            if j == i:
                continue
            egim = (pj - pi) / (j - i)

            def deger(bar: int) -> float:
                return pi + egim * (bar - i)

            # İhlal kontrolü: i..son_bar arasında kapanış doğrunun yanlış
            # tarafına ihlal_tol'dan fazla geçmemeli.
            gecersiz = False
            for bar in range(i, toplam):
                d = deger(bar)
                if tip == "Destek" and kapanis[bar] < d * (1 - ihlal_tol):
                    gecersiz = True
                    break
                if tip == "Direnç" and kapanis[bar] > d * (1 + ihlal_tol):
                    gecersiz = True
                    break
            if gecersiz:
                continue

            # Dokunuş sayısı: pivotlar doğruya tolerans içinde mi?
            dokunus = 0
            for (pi_idx, pp) in noktalar:
                d = deger(pi_idx)
                if abs(pp - d) <= tolerans * d:
                    dokunus += 1
            if dokunus < min_dokunus:
                continue

            recency = j / son_bar  # son nokta ne kadar yeni
            skor = (dokunus, recency)
            if skor > en_iyi_skor:
                en_iyi_skor = skor
                gd = deger(son_bar)
                en_iyi = TrendCizgisi(
                    tip=tip, egim=egim, bar0=i, fiyat0=pi,
                    dokunus=dokunus, guncel_deger=round(gd, 4),
                    yon=_yon(egim, gd))

    return en_iyi


@dataclass
class Kanal:
    destek: TrendCizgisi
    direnc: TrendCizgisi | None
    genislik: float | None   # son bardaki direnç-destek farkı


def kanal_bul(
    df: pd.DataFrame, n: int = 5, tolerans: float = 0.01,
    min_dokunus: int = 3, son_n: int = 300,
) -> Kanal | None:
    """Destek + (varsa) direnç çizgisini birlikte döndürür."""
    destek = trend_cizgisi_bul(df, "Destek", n, tolerans, min_dokunus, son_n)
    if destek is None:
        # Yükselen destek yoksa düşen direnç tek başına anlamlı olabilir
        direnc = trend_cizgisi_bul(df, "Direnç", n, tolerans, min_dokunus, son_n)
        if direnc is None:
            return None
        return Kanal(destek=direnc, direnc=None, genislik=None)

    direnc = trend_cizgisi_bul(df, "Direnç", n, tolerans, min_dokunus, son_n)
    genislik = None
    if direnc is not None:
        genislik = round(direnc.guncel_deger - destek.guncel_deger, 4)
    return Kanal(destek=destek, direnc=direnc, genislik=genislik)
