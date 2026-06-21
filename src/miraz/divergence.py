"""RSI Divergence ("trend yorgunluğu") — @finansalTRader tarzı.

Hoca: "Teknik olarak trendin yorulduğunu, divergence'nin geliştiğini ve
bunların Bear hareketi getirebileceğini yazmıştık." (GUA, 27 May)

  - Bearish divergence: fiyat daha yüksek tepe (HH) yaparken RSI daha düşük
    tepe (LH) → yükseliş yoruluyor, düşüş riski.
  - Bullish divergence: fiyat daha düşük dip (LL) yaparken RSI daha yüksek dip
    (HL) → düşüş yoruluyor, tepki/yükseliş ihtimali.

Kullanım:
    from miraz.divergence import divergence_bul
    d = divergence_bul(df)
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .bicim import f as _f
from .indikator import rsi as _rsi
from .pivotlar import pivot_listesi


@dataclass
class Divergence:
    tip: str            # "Bearish" / "Bullish"
    fiyat1: float       # önceki pivot fiyatı
    fiyat2: float       # son pivot fiyatı
    rsi1: float
    rsi2: float
    aciklama: str


def divergence_bul(df: pd.DataFrame, n: int = 5, rsi_periyot: int = 14,
                   son_n_pivot: int = 6) -> Divergence | None:
    """Son pivotlarda fiyat–RSI uyumsuzluğu (divergence) arar.

    Son iki tepe (bearish) veya son iki dip (bullish) karşılaştırılır.
    """
    if len(df) < rsi_periyot + 5:
        return None
    r = _rsi(df["close"], rsi_periyot)
    piv = pivot_listesi(df, n=n)
    if len(piv) < 2:
        return None
    piv = piv[-son_n_pivot:]

    def rsi_at(idx):
        v = r.iloc[idx]
        return float(v) if pd.notna(v) else None

    # Bearish: son iki H pivotu (fiyat HH, RSI LH)
    tepeler = [(i, p) for (i, p, t) in piv if t == "H"]
    if len(tepeler) >= 2:
        (i1, p1), (i2, p2) = tepeler[-2], tepeler[-1]
        rv1, rv2 = rsi_at(i1), rsi_at(i2)
        if rv1 is not None and rv2 is not None:
            if p2 > p1 and rv2 < rv1:        # fiyat HH, RSI LH
                return Divergence(
                    "Bearish", round(p1, 6), round(p2, 6),
                    round(rv1, 1), round(rv2, 1),
                    _aciklama("Bearish", p1, p2, rv1, rv2))

    # Bullish: son iki L pivotu (fiyat LL, RSI HL)
    dipler = [(i, p) for (i, p, t) in piv if t == "L"]
    if len(dipler) >= 2:
        (i1, p1), (i2, p2) = dipler[-2], dipler[-1]
        rv1, rv2 = rsi_at(i1), rsi_at(i2)
        if rv1 is not None and rv2 is not None:
            if p2 < p1 and rv2 > rv1:        # fiyat LL, RSI HL
                return Divergence(
                    "Bullish", round(p1, 6), round(p2, 6),
                    round(rv1, 1), round(rv2, 1),
                    _aciklama("Bullish", p1, p2, rv1, rv2))

    return None


def _aciklama(tip, p1, p2, rv1, rv2) -> str:
    if tip == "Bearish":
        return (f"Bearish divergence (trend yorgunluğu): fiyat HH "
                f"{_f(p1)}→{_f(p2)} ama RSI LH {rv1:.0f}→{rv2:.0f} "
                f"— yükseliş yoruluyor, düşüş riski.")
    return (f"Bullish divergence: fiyat LL {_f(p1)}→{_f(p2)} ama RSI HL "
            f"{rv1:.0f}→{rv2:.0f} — düşüş yoruluyor, tepki ihtimali.")


def metin(d: Divergence | None) -> str:
    """Divergence'ı senaryo planı için tek satıra çevirir."""
    if d is None:
        return ""
    ikon = "📉" if d.tip == "Bearish" else "📈"
    return f"{ikon} {d.aciklama}"
