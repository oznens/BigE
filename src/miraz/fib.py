"""Fibonacci Retracement bölgeleri — @finansalTRader (Miraz'ın hocası) tarzı.

finansalTRader analizlerinde "Direnç ve Fib.Retr 0,618 bölgesinden bear tepki"
gibi ifadelerle ana swing'in Fibonacci geri çekilme seviyelerini (özellikle
0.618 "golden pocket") kilit tepki bölgesi olarak kullanır. Harmonikten farkı:
tam XABCD değil, sadece son büyük hareketin (dip→tepe) geri çekilme ızgarası.

Kavramlar:
  - Yükseliş hareketi (dip→tepe): geri çekilme AŞAĞI; 0.618 = destek adayı.
  - Düşüş hareketi (tepe→dip): geri çekilme YUKARI; 0.618 = direnç adayı.
  - Golden pocket: 0.618–0.705 bandı (en güçlü tepki bölgesi).

Kullanım:
    from miraz.fib import fib_retracement
    fr = fib_retracement(df)
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .bicim import f as _f
from .pivotlar import pivot_listesi

_ORANLAR = [0.236, 0.382, 0.5, 0.618, 0.705, 0.786]


@dataclass
class FibSeviye:
    oran: float
    fiyat: float
    golden: bool = False


@dataclass
class FibRetr:
    yon: str                 # "Yükseliş" (dip→tepe) / "Düşüş" (tepe→dip)
    swing_dusuk: float
    swing_yuksek: float
    seviyeler: list = field(default_factory=list)   # list[FibSeviye]
    golden_alt: float = 0.0  # 0.618 seviyesi
    golden_ust: float = 0.0  # 0.705 seviyesi
    aktif: FibSeviye | None = None    # fiyatın yakın olduğu seviye
    fiyat_golden_icinde: bool = False
    aciklama: str = ""


def fib_retracement(df: pd.DataFrame, n: int = 5, son_n: int = 200,
                    yakinlik: float = 0.01) -> FibRetr | None:
    """Son büyük swing'in Fibonacci geri çekilme seviyelerini döndürür.

    Ana swing = son `son_n` bar içindeki en yüksek tepe ve en düşük dip;
    hangisi daha sonra oluştuysa hareketin yönünü belirler.
    yakinlik: fiyatın bir seviyeye "yakın" sayılması için oran (%1).
    """
    piv = pivot_listesi(df, n=n)
    toplam = len(df)
    bas = max(0, toplam - son_n)
    pencere = [(i, p, t) for (i, p, t) in piv if i >= bas]
    if len(pencere) < 2:
        return None

    yuksek = max(pencere, key=lambda x: x[1])      # (idx, fiyat, tip)
    dusuk = min(pencere, key=lambda x: x[1])
    hi, lo = yuksek[1], dusuk[1]
    if hi <= lo:
        return None
    aralik = hi - lo

    # Yön: tepe dipten SONRA ise yükseliş hareketi (geri çekilme aşağı)
    yukselis = yuksek[0] > dusuk[0]
    yon = "Yükseliş" if yukselis else "Düşüş"

    seviyeler = []
    for r in _ORANLAR:
        # Yükselişte 0% tepe, 100% dip (tepeden aşağı geri çekilme)
        # Düşüşte 0% dip, 100% tepe (dipten yukarı geri çekilme)
        if yukselis:
            fy = hi - r * aralik
        else:
            fy = lo + r * aralik
        seviyeler.append(FibSeviye(oran=r, fiyat=round(fy, 6),
                                   golden=(r in (0.618, 0.705))))

    g618 = next(s.fiyat for s in seviyeler if s.oran == 0.618)
    g705 = next(s.fiyat for s in seviyeler if s.oran == 0.705)
    golden_alt, golden_ust = sorted((g618, g705))

    fiyat = float(df["close"].iloc[-1])
    aktif = min(seviyeler, key=lambda s: abs(s.fiyat - fiyat))
    if abs(aktif.fiyat - fiyat) > yakinlik * fiyat:
        aktif = None
    golden_icinde = bool(golden_alt <= fiyat <= golden_ust)

    aciklama = _aciklama(yon, golden_alt, golden_ust, aktif, golden_icinde)
    return FibRetr(yon=yon, swing_dusuk=round(lo, 6), swing_yuksek=round(hi, 6),
                   seviyeler=seviyeler, golden_alt=round(golden_alt, 6),
                   golden_ust=round(golden_ust, 6), aktif=aktif,
                   fiyat_golden_icinde=golden_icinde, aciklama=aciklama)


def _aciklama(yon, g_alt, g_ust, aktif, golden_icinde) -> str:
    rol = "destek" if yon == "Yükseliş" else "direnç"
    s = (f"Fib geri çekilme ({yon} hareketi) — golden pocket "
         f"{_f(g_alt)}–{_f(g_ust)} ({rol} adayı)")
    if golden_icinde:
        s += " — FİYAT GOLDEN POCKET İÇİNDE, tepki izle."
    elif aktif is not None:
        s += f"; fiyat {aktif.oran:.3f} seviyesinde ({_f(aktif.fiyat)})."
    return s


def metin(fr: FibRetr | None) -> str:
    """Fib retracement'ı senaryo planı için tek satıra çevirir."""
    if fr is None:
        return ""
    return f"📐 {fr.aciklama}"
