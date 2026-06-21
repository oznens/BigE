"""Elliott Wave (itme/düzeltme) — basitleştirilmiş etiketleme.

@finansalTRader "dalga yapıları", "itme" (impulse 1-2-3-4-5) ve "düzeltme"
(corrective A-B-C) dilini kullanır. Bu modül alternating pivotlardan basit
bir dalga sayımı dener (kesin Elliott değil; pratik bir yapı okuması).

İtme kuralları (klasik):
  - 2. dalga 1. dalganın başlangıcını geçmez
  - 3. dalga en kısa olamaz
  - 4. dalga 1. dalganın bölgesine girmez (overlap yok)

Kullanım:
    from miraz.elliott import elliott_bul
    e = elliott_bul(df)
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .pivotlar import pivot_listesi


@dataclass
class ElliottSayim:
    tip: str            # "İtme-Bullish" / "İtme-Bearish" / "Düzeltme-ABC"
    noktalar: list      # [(bar, fiyat, etiket), ...] etiket: 0,1,2,3,4,5 / A,B,C
    aciklama: str


def _itme_gecerli(p, bull: bool) -> bool:
    """6 nokta (0,1,2,3,4,5) itme kurallarını sağlıyor mu?"""
    f = [x[1] for x in p]
    w1 = abs(f[1] - f[0]); w3 = abs(f[3] - f[2]); w5 = abs(f[5] - f[4])
    if bull:
        if not (f[1] > f[0] and f[2] > f[0] and f[3] > f[1]
                and f[4] > f[1] and f[5] > f[3]):
            return False
    else:
        if not (f[1] < f[0] and f[2] < f[0] and f[3] < f[1]
                and f[4] < f[1] and f[5] < f[3]):
            return False
    if w3 < w1 and w3 < w5:      # 3. dalga en kısa olamaz
        return False
    return True


def elliott_bul(df: pd.DataFrame, n: int = 5) -> ElliottSayim | None:
    """Son pivotlarda 5'li itme veya 3'lü (ABC) düzeltme yapısı arar."""
    piv = pivot_listesi(df, n=n)
    if len(piv) < 4:
        return None

    # 5'li itme: son 6 pivot (0-1-2-3-4-5)
    if len(piv) >= 6:
        p = piv[-6:]
        for bull in (True, False):
            if _itme_gecerli(p, bull):
                etk = ["0", "1", "2", "3", "4", "5"]
                noktalar = [(p[i][0], round(p[i][1], 6), etk[i])
                            for i in range(6)]
                yon = "Bullish" if bull else "Bearish"
                return ElliottSayim(
                    tip=f"İtme-{yon}", noktalar=noktalar,
                    aciklama=f"5'li itme dalgası ({yon}) tamamlanıyor — "
                             f"sonrasında ABC düzeltmesi beklenir.")

    # 3'lü ABC düzeltme: son 4 pivot (başlangıç-A-B-C)
    p = piv[-4:]
    f = [x[1] for x in p]
    etk = ["X", "A", "B", "C"]
    # zigzag: A-B-C dönüşümlü, C genelde A yönünde uzar
    if (f[1] - f[0]) * (f[2] - f[1]) < 0 and (f[2] - f[1]) * (f[3] - f[2]) < 0:
        noktalar = [(p[i][0], round(p[i][1], 6), etk[i]) for i in range(4)]
        return ElliottSayim(
            tip="Düzeltme-ABC", noktalar=noktalar,
            aciklama="ABC düzeltme yapısı — C dalgası sonunda ana trend "
                     "yönünde hareket beklenir.")
    return None


def metin(e: ElliottSayim | None) -> str:
    """Elliott sayımını senaryo planı için tek satıra çevirir."""
    if e is None:
        return ""
    return f"🌊 Elliott: {e.aciklama}"
