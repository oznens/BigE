"""Sayı biçimlendirme — büyüklüğe göre ondalık hassasiyeti.

Kuruş-altı coinlerde (DOGE 0.083, SHIB 0.00002...) 2 ondalık hassasiyeti
yetersiz; bu yardımcılar ondalık hane sayısını fiyat büyüklüğüne göre seçer.
"""

from __future__ import annotations


def ondalik(v: float) -> int:
    """Fiyat büyüklüğüne göre ondalık hane sayısı."""
    a = abs(v)
    if a >= 1:
        return 2
    if a >= 0.1:
        return 4
    if a >= 0.01:
        return 5
    if a >= 0.0001:
        return 6
    return 8


def f(v: float) -> str:
    """Hassasiyet-duyarlı sayı (İngilizce ayraç): 0.0834 → '0.08340'."""
    return f"{v:,.{ondalik(v)}f}"
