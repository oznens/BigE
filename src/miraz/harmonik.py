"""Harmonik pattern tespiti — Fibonacci oran kontrolleri.

Desteklenen patternler:
  Gartley, Bat, Butterfly, Crab, Deep Crab, AB=CD, Shark, Cypher

Her pattern iki yönde çalışır:
  Bullish  → X(L) → A(H) → B(L) → C(H) → D(L)  — D'de LONG
  Bearish  → X(H) → A(L) → B(H) → C(L) → D(H)  — D'de SHORT

Referans: @tradermiraz tweet arşivi + standart harmonik literatürü.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Pattern tanımları — {oran_adı: (min, max)}
# ---------------------------------------------------------------------------
TOL = 0.05  # sabit Fibonacci noktaları için ±5% tolerans


def _alik(deger: float, tol: float = TOL) -> tuple[float, float]:
    """Sabit Fibonacci değeri etrafında toleranslı aralık."""
    return (deger * (1 - tol), deger * (1 + tol))


PATTERN_TANIMLARI: dict[str, dict[str, tuple[float, float]]] = {
    "Gartley": {
        "AB_XA": _alik(0.618),
        "BC_AB": (0.382, 0.886),
        "CD_BC": (1.13, 1.618),
        "XD_XA": _alik(0.786),
    },
    "Bat": {
        "AB_XA": (0.332, 0.550),     # 0.382–0.5 + tolerans
        "BC_AB": (0.382, 0.886),
        "CD_BC": (1.618, 2.618),
        "XD_XA": _alik(0.886),
    },
    "Butterfly": {
        "AB_XA": _alik(0.786),
        "BC_AB": (0.382, 0.886),
        "CD_BC": (1.618, 2.24),
        "XD_XA": (1.17, 1.68),       # 1.27 veya 1.618
    },
    "Crab": {
        "AB_XA": (0.332, 0.668),     # 0.382–0.618 + tolerans
        "BC_AB": (0.382, 0.886),
        "CD_BC": (2.24, 3.618),
        "XD_XA": _alik(1.618, 0.03),
    },
    "Deep Crab": {
        "AB_XA": _alik(0.886),
        "BC_AB": (0.382, 0.886),
        "CD_BC": (2.0, 3.618),
        "XD_XA": _alik(1.618, 0.03),
    },
    "Shark": {
        # Shark: 0-X-A-B-C yapısı (5 nokta ama farklı oran)
        # Burada standart XABCD eşlemesiyle temsil:
        # AB/XA: 1.13–1.618 (AB XA'yı aşar)
        # BC/XC: 0.886 (C, XC'nin 0.886'sında)
        "AB_XA": (1.10, 1.68),
        "BC_AB": (0.382, 0.886),
        "CD_BC": (1.618, 2.24),
        "XD_XA": _alik(0.886),
    },
    "Cypher": {
        # Cypher: AB/XA 0.382–0.618, BC XA'yı 1.13–1.414 uzatır
        "AB_XA": (0.332, 0.668),
        "BC_AB": (1.13, 1.414),      # BC, AB'yi aşar (extension)
        "CD_BC": (1.272, 2.00),
        "XD_XA": _alik(0.786),
    },
}

# AB=CD ayrı kontrol (CD uzunluğu ≈ AB uzunluğu)
ABCD_TOL = 0.10


# ---------------------------------------------------------------------------
# Veri sınıfı
# ---------------------------------------------------------------------------

@dataclass
class HarmonikSonuc:
    isim: str              # pattern adı (ör. "Gartley")
    yon: str               # "Bullish" veya "Bearish"
    X_idx: int
    A_idx: int
    B_idx: int
    C_idx: int
    D_idx: int
    X: float               # fiyatlar
    A: float
    B: float
    C: float
    D: float               # PRZ merkezi (giriş bölgesi)
    entry: float           # önerilen giriş (≈D)
    sl: float              # stop loss (X ötesi)
    tp1: float             # hedef 1: CD'nin 0.382 geri çekilmesi
    tp2: float             # hedef 2: B seviyesi
    rr: float              # risk/reward (tp1 bazında)
    oranlar: dict = field(default_factory=dict)
    kalite: float = 0.0    # 0–100 kalite puanı (ideal Fib oranlarına yakınlık)


# ---------------------------------------------------------------------------
# Oran hesaplamaları
# ---------------------------------------------------------------------------

def _bullish_oranlar(X: float, A: float, B: float, C: float, D: float
                     ) -> Optional[dict[str, float]]:
    """Bullish (X=düşük) XABCD için Fibonacci oranları."""
    XA = A - X
    if XA <= 0:
        return None
    AB = A - B
    if AB <= 0:
        return None
    BC = C - B
    if BC <= 0:
        return None
    CD = C - D
    if CD <= 0:
        return None
    return {
        "AB_XA": AB / XA,
        "BC_AB": BC / AB,
        "CD_BC": CD / BC,
        "XD_XA": (A - D) / XA,
        "AB_CD": AB / CD,            # AB=CD kontrolü için
        "XA": XA, "AB": AB, "BC": BC, "CD": CD,
    }


def _bearish_oranlar(X: float, A: float, B: float, C: float, D: float
                     ) -> Optional[dict[str, float]]:
    """Bearish (X=yüksek) XABCD için Fibonacci oranları."""
    XA = X - A
    if XA <= 0:
        return None
    AB = B - A
    if AB <= 0:
        return None
    BC = B - C
    if BC <= 0:
        return None
    CD = D - C
    if CD <= 0:
        return None
    return {
        "AB_XA": AB / XA,
        "BC_AB": BC / AB,
        "CD_BC": CD / BC,
        "XD_XA": (D - A) / XA,
        "AB_CD": AB / CD,
        "XA": XA, "AB": AB, "BC": BC, "CD": CD,
    }


def _oran_iceride(deger: float, aralik: tuple[float, float]) -> bool:
    return aralik[0] <= deger <= aralik[1]


def _kalite_puani(oranlar: dict, tanimlar: dict) -> float:
    """Oranların ideal Fibonacci değerlerine yakınlığına göre 0–100 puan."""
    puan = 0.0
    ideal_map = {
        "AB_XA": [0.382, 0.500, 0.618, 0.786, 0.886],
        "BC_AB": [0.382, 0.500, 0.618, 0.786, 0.886],
        "CD_BC": [1.272, 1.414, 1.618, 2.0, 2.618],
        "XD_XA": [0.786, 0.886, 1.272, 1.618],
    }
    n = 0
    for oran_adi, (lo, hi) in tanimlar.items():
        if oran_adi not in oranlar:
            continue
        deger = oranlar[oran_adi]
        alik = hi - lo
        if alik <= 0:
            continue
        # 0–25 puan: ne kadar ortada ise o kadar yüksek
        orta = (lo + hi) / 2
        uzaklik = abs(deger - orta) / (alik / 2)
        puan += max(0.0, 25.0 * (1 - uzaklik))
        n += 1
    return round(puan / n * 4, 1) if n else 0.0


# ---------------------------------------------------------------------------
# Tek XABCD kombinasyonunu test et
# ---------------------------------------------------------------------------

def _kontrol_et(
    X_idx: int, A_idx: int, B_idx: int, C_idx: int, D_idx: int,
    X: float, A: float, B: float, C: float, D: float,
    yon: str,  # "Bullish" veya "Bearish"
) -> list[HarmonikSonuc]:
    """Bir XABCD kombinasyonunu tüm pattern tanımlarına karşı test eder."""
    if yon == "Bullish":
        oranlar = _bullish_oranlar(X, A, B, C, D)
    else:
        oranlar = _bearish_oranlar(X, A, B, C, D)

    if oranlar is None:
        return []

    sonuclar = []
    for isim, tanimlar in PATTERN_TANIMLARI.items():
        eslesme = all(
            _oran_iceride(oranlar.get(k, -1), v)
            for k, v in tanimlar.items()
            if k in oranlar
        )
        if not eslesme:
            continue

        kalite = _kalite_puani(oranlar, tanimlar)

        # TP / SL hesapla
        if yon == "Bullish":
            entry = D
            sl    = X * (1 - 0.005)           # X'in biraz altı
            tp1   = D + oranlar["CD"] * 0.382  # CD'nin %38.2 geri çekilmesi
            tp2   = B                           # B seviyesi
        else:
            entry = D
            sl    = X * (1 + 0.005)
            tp1   = D - oranlar["CD"] * 0.382
            tp2   = B

        risk = abs(entry - sl)
        kazan = abs(tp1 - entry)
        rr = round(kazan / risk, 2) if risk > 0 else 0.0

        sonuclar.append(HarmonikSonuc(
            isim=isim, yon=yon,
            X_idx=X_idx, A_idx=A_idx, B_idx=B_idx, C_idx=C_idx, D_idx=D_idx,
            X=X, A=A, B=B, C=C, D=D,
            entry=round(entry, 4), sl=round(sl, 4),
            tp1=round(tp1, 4), tp2=round(tp2, 4),
            rr=rr, oranlar=oranlar, kalite=kalite,
        ))

    # AB=CD ayrı kontrol
    if _oran_iceride(oranlar.get("AB_CD", -1), (1 - ABCD_TOL, 1 + ABCD_TOL)):
        if yon == "Bullish":
            entry = D; sl = X * 0.995; tp1 = D + oranlar["CD"] * 0.382; tp2 = B
        else:
            entry = D; sl = X * 1.005; tp1 = D - oranlar["CD"] * 0.382; tp2 = B
        risk = abs(entry - sl); kazan = abs(tp1 - entry)
        sonuclar.append(HarmonikSonuc(
            isim="AB=CD", yon=yon,
            X_idx=X_idx, A_idx=A_idx, B_idx=B_idx, C_idx=C_idx, D_idx=D_idx,
            X=X, A=A, B=B, C=C, D=D,
            entry=round(entry, 4), sl=round(sl, 4),
            tp1=round(tp1, 4), tp2=round(tp2, 4),
            rr=round(kazan / risk, 2) if risk > 0 else 0.0,
            oranlar=oranlar,
            kalite=_kalite_puani(oranlar, {"AB_CD": (0.9, 1.1), "BC_AB": (0.382, 0.886)}),
        ))

    return sonuclar


# ---------------------------------------------------------------------------
# Ana fonksiyon: DataFrame üzerinde tüm pivotları tara
# ---------------------------------------------------------------------------

def tara(
    df,                      # pd.DataFrame (open/high/low/close)
    pivotlar: list,          # pivot_listesi() çıktısı
    min_kalite: float = 40.0,
) -> list[HarmonikSonuc]:
    """Alternating pivot listesindeki tüm 5'li kombinasyonları tarar.

    Sadece `min_kalite` üzerindeki patternleri döndürür.
    """
    sonuclar: list[HarmonikSonuc] = []
    n = len(pivotlar)
    if n < 5:
        return sonuclar

    for i in range(n - 4):
        p = pivotlar[i: i + 5]
        tipler = [x[2] for x in p]

        # Bullish: L-H-L-H-L
        if tipler == ["L", "H", "L", "H", "L"]:
            X, A, B, C, D = p[0][1], p[1][1], p[2][1], p[3][1], p[4][1]
            bulunanlar = _kontrol_et(
                p[0][0], p[1][0], p[2][0], p[3][0], p[4][0],
                X, A, B, C, D, "Bullish",
            )
            sonuclar.extend(b for b in bulunanlar if b.kalite >= min_kalite)

        # Bearish: H-L-H-L-H
        elif tipler == ["H", "L", "H", "L", "H"]:
            X, A, B, C, D = p[0][1], p[1][1], p[2][1], p[3][1], p[4][1]
            bulunanlar = _kontrol_et(
                p[0][0], p[1][0], p[2][0], p[3][0], p[4][0],
                X, A, B, C, D, "Bearish",
            )
            sonuclar.extend(b for b in bulunanlar if b.kalite >= min_kalite)

    # D en yakın olan (en yeni) üste gelsin
    sonuclar.sort(key=lambda s: s.D_idx, reverse=True)
    return sonuclar
