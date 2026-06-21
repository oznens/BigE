"""Flama / Diagonal (yakınsayan üçgen) tespiti — @tradermiraz formasyonu.

Altın/Gümüş rasyo floodunda Miraz "bir flama yapısı gözlemliyorum" diyor:
düşen bir üst (direnç) çizgisi + yükselen bir alt (destek) çizgisi bir
apekse doğru yakınsıyor (simetrik üçgen / flama). Kırılım yönü, çoğu zaman
önceki trendin devamı yönünde olur ("Trend devam"). Kırılım sonrası hedef,
formasyon yüksekliği kadar ölçülü hareket (measured move) ile projelendirilir.

Kullanım:
    from miraz.flama import flama_bul
    f = flama_bul(df)   # Flama veya None
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .bicim import f as _f
from .trend import TrendCizgisi, trend_cizgisi_bul


@dataclass
class Flama:
    direnc: TrendCizgisi    # düşen üst çizgi (Diagonal)
    destek: TrendCizgisi    # yükselen alt çizgi (Trend devam)
    apeks_bar: int          # iki çizginin kesişeceği bar (gelecekte)
    daralma: bool           # çizgiler yakınsıyor mu (gerçek flama)
    yukseklik: float        # formasyon başındaki dikey aralık (measured move)
    hedef_yukari: float     # yukarı kırılımda ölçülü hareket hedefi
    hedef_asagi: float      # aşağı kırılımda ölçülü hareket hedefi
    aciklama: str


def _kesisim_bar(direnc: TrendCizgisi, destek: TrendCizgisi) -> float | None:
    """İki doğrunun kesiştiği bar indeksini döndürür (yakınsamıyorsa None)."""
    fark_egim = direnc.egim - destek.egim
    if abs(fark_egim) < 1e-12:
        return None                       # paralel → kesişmez
    # direnc.deger(x) = destek.deger(x)  →  x çöz
    x = (destek.fiyat0 - destek.egim * destek.bar0
         - direnc.fiyat0 + direnc.egim * direnc.bar0) / fark_egim
    return x


def flama_bul(
    df: pd.DataFrame,
    n: int = 5,
    son_n: int = 140,
    min_dokunus: int = 2,
    tolerans: float = 0.012,
) -> Flama | None:
    """Yakınsayan üçgen (flama) tespit eder.

    Düşen direnç çizgisi + yükselen destek çizgisi bir apekse yakınsıyorsa
    flama kabul edilir. Apeks gelecekte (son bardan sonra) olmalıdır.
    """
    direnc = trend_cizgisi_bul(df, "Direnç", n=n, tolerans=tolerans,
                               min_dokunus=min_dokunus, son_n=son_n)
    destek = trend_cizgisi_bul(df, "Destek", n=n, tolerans=tolerans,
                               min_dokunus=min_dokunus, son_n=son_n)
    if direnc is None or destek is None:
        return None
    # Gerçek flama: üst çizgi düşen, alt çizgi yükselen (ya da en azından
    # üst aşağı, alt yukarı eğimli → yakınsama).
    if direnc.egim >= 0 or destek.egim <= 0:
        # Simetrik değil; en azından çizgiler birbirine yaklaşıyor mu bak.
        if direnc.egim - destek.egim >= 0:
            return None

    apeks = _kesisim_bar(direnc, destek)
    if apeks is None:
        return None

    son_bar = len(df) - 1
    # Apeks gelecekte ve makul yakınlıkta olmalı (çok uzaksa flama değil).
    if apeks <= son_bar or apeks > son_bar + son_n:
        return None

    daralma = bool(direnc.egim < destek.egim)  # üst düşüyor, alt yükseliyor
    ust = direnc.guncel_deger
    alt = destek.guncel_deger
    yukseklik = round(max(ust - alt, 0.0), 4)

    fiyat = float(df["close"].iloc[-1])
    hedef_yukari = round(ust + yukseklik, 4)
    hedef_asagi = round(alt - yukseklik, 4)

    aciklama = (
        f"Flama (yakınsayan üçgen): üst {_f(ust)} ↘ / alt {_f(alt)} ↗, "
        f"apekse ~{int(apeks - son_bar)} bar. "
        f"Kırılımla ölçülü hareket ≈ {_f(yukseklik)} "
        f"(yukarı hedef {_f(hedef_yukari)}, aşağı hedef {_f(hedef_asagi)}).")

    return Flama(direnc=direnc, destek=destek, apeks_bar=int(round(apeks)),
                 daralma=daralma, yukseklik=yukseklik,
                 hedef_yukari=hedef_yukari, hedef_asagi=hedef_asagi,
                 aciklama=aciklama)


def metin(f: Flama | None) -> str:
    """Flamayı senaryo planı için tek satıra çevirir."""
    if f is None:
        return ""
    return f"🔻 {f.aciklama}"
