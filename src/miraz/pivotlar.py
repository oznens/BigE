"""Swing pivot tespiti — harmonik tarayıcının temeli.

Yöntem:
  - Swing High: sol ve sağ `n` barda en yüksek high olan bar.
  - Swing Low : sol ve sağ `n` barda en düşük low olan bar.
  - Alternating filtreleme: ardışık aynı tip pivot varsa daha ekstrem olanı tut.
    Harmonik patternler XABCD yapısı gerektirdiğinden pivotlar sıralı
    H-L-H-L-H veya L-H-L-H-L olmalıdır.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def swing_high_maske(df: pd.DataFrame, n: int = 5) -> np.ndarray:
    """Her bar için swing high ise True, aksi halde False (numpy bool array)."""
    h = df["high"].to_numpy()
    size = len(h)
    mask = np.zeros(size, dtype=bool)
    for i in range(n, size - n):
        pencere = h[i - n: i + n + 1]
        if h[i] == pencere.max():
            mask[i] = True
    return mask


def swing_low_maske(df: pd.DataFrame, n: int = 5) -> np.ndarray:
    """Her bar için swing low ise True, aksi halde False (numpy bool array)."""
    lo = df["low"].to_numpy()
    size = len(lo)
    mask = np.zeros(size, dtype=bool)
    for i in range(n, size - n):
        pencere = lo[i - n: i + n + 1]
        if lo[i] == pencere.min():
            mask[i] = True
    return mask


def pivot_listesi(
    df: pd.DataFrame, n: int = 5
) -> list[tuple[int, float, str]]:
    """Alternating (H/L sıralı) pivot listesi döndürür.

    Her eleman: (bar_indeksi, fiyat, "H" veya "L")
    Ardışık aynı tip pivotlarda daha ekstrem (H→daha yüksek, L→daha düşük) olan tutulur.
    """
    sh = swing_high_maske(df, n)
    sl = swing_low_maske(df, n)
    h_arr = df["high"].to_numpy()
    l_arr = df["low"].to_numpy()

    raw: list[tuple[int, float, str]] = []
    for i in range(len(df)):
        if sh[i]:
            raw.append((i, h_arr[i], "H"))
        elif sl[i]:
            raw.append((i, l_arr[i], "L"))

    if not raw:
        return []

    alt: list[tuple[int, float, str]] = [raw[0]]
    for p in raw[1:]:
        if p[2] == alt[-1][2]:
            # aynı tip → daha ekstrem olanı tut
            if p[2] == "H" and p[1] > alt[-1][1]:
                alt[-1] = p
            elif p[2] == "L" and p[1] < alt[-1][1]:
                alt[-1] = p
        else:
            alt.append(p)

    return alt
