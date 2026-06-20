"""Çift Tepe / Çift Dip (Double Top/Bottom) tespiti — @tradermiraz formasyonu.

Miraz: "Fiyat, çift tepe yapısı sonrası trend kırılımını gerçekleştirmiş
durumda." (BTC, 28 Nis 2026). Klasik dönüş formasyonu:

  Çift Tepe (bearish):  iki benzer yükseğin (H-H) arasında bir boyun (L).
    Boyun altında KAPANIŞ → düşüş onayı. Hedef = boyun - (tepe - boyun).
  Çift Dip (bullish):   iki benzer dibin (L-L) arasında bir boyun (H).
    Boyun üstünde KAPANIŞ → yükseliş onayı. Hedef = boyun + (boyun - dip).

Kullanım:
    from miraz.ikili import ikili_bul
    f = ikili_bul(df)   # IkiliFormasyon veya None
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .pivotlar import pivot_listesi


@dataclass
class IkiliFormasyon:
    tip: str            # "Çift Tepe" / "Çift Dip"
    yon: str            # "Bearish" / "Bullish"
    seviye1: float      # birinci tepe/dip fiyatı
    seviye2: float      # ikinci tepe/dip fiyatı
    boyun: float        # neckline (aradaki ters pivot)
    hedef: float        # ölçülü hareket hedefi (boyun ± yükseklik)
    onayli: bool        # boyun kapanışla kırıldı mı
    aciklama: str


def ikili_bul(df: pd.DataFrame, n: int = 5,
              tolerans: float = 0.02) -> IkiliFormasyon | None:
    """Son pivotlarda çift tepe/dip arar (en yakın geçerli olanı döndürür).

    tolerans: iki tepenin/dibin "benzer" sayılması için yüzde fark (≤%2).
    """
    piv = pivot_listesi(df, n=n)
    if len(piv) < 3:
        return None
    kapanis = float(df["close"].iloc[-1])

    # Son 3'lü pencereleri yeniden eskiye tara: H-L-H veya L-H-L
    for k in range(len(piv) - 1, 1, -1):
        a, orta, c = piv[k - 2], piv[k - 1], piv[k]
        tipler = (a[2], orta[2], c[2])

        if tipler == ("H", "L", "H"):          # Çift Tepe adayı
            s1, s2, boyun = a[1], c[1], orta[1]
            if abs(s1 - s2) / max(s1, s2) > tolerans:
                continue
            yukseklik = (s1 + s2) / 2 - boyun
            if yukseklik <= 0:
                continue
            hedef = round(boyun - yukseklik, 4)
            onayli = bool(kapanis < boyun)
            return IkiliFormasyon(
                tip="Çift Tepe", yon="Bearish", seviye1=round(s1, 4),
                seviye2=round(s2, 4), boyun=round(boyun, 4), hedef=hedef,
                onayli=onayli, aciklama=_aciklama(
                    "Çift Tepe", s1, s2, boyun, hedef, onayli, "altında"))

        if tipler == ("L", "H", "L"):          # Çift Dip adayı
            s1, s2, boyun = a[1], c[1], orta[1]
            if abs(s1 - s2) / max(s1, s2) > tolerans:
                continue
            yukseklik = boyun - (s1 + s2) / 2
            if yukseklik <= 0:
                continue
            hedef = round(boyun + yukseklik, 4)
            onayli = bool(kapanis > boyun)
            return IkiliFormasyon(
                tip="Çift Dip", yon="Bullish", seviye1=round(s1, 4),
                seviye2=round(s2, 4), boyun=round(boyun, 4), hedef=hedef,
                onayli=onayli, aciklama=_aciklama(
                    "Çift Dip", s1, s2, boyun, hedef, onayli, "üstünde"))

    return None


def _aciklama(tip, s1, s2, boyun, hedef, onayli, yon_soz) -> str:
    durum = (f"boyun {boyun:,.2f} {yon_soz} KAPANIŞ ile ONAYLANDI"
             if onayli else
             f"boyun {boyun:,.2f} {yon_soz} kapanış bekleniyor (henüz onaysız)")
    return (f"{tip} ({s1:,.2f} / {s2:,.2f}) — {durum}. "
            f"Ölçülü hareket hedefi {hedef:,.2f}.")


def metin(f: IkiliFormasyon | None) -> str:
    """Çift tepe/dip'i senaryo planı için tek satıra çevirir."""
    if f is None:
        return ""
    ikon = "⛰️" if f.tip == "Çift Tepe" else "🇻"
    onay = "✓ onaylı" if f.onayli else "○ onaysız"
    return f"{ikon} {f.aciklama} [{onay}]"
