"""OBO / TOBO (Omuz-Baş-Omuz / Head & Shoulders) — @finansalTRader tarzı.

Hoca XU100 grafiğinde "Sol Omuz / Baş / Sağ Omuz" ve "TOBO oluşumu" etiketleriyle
omuz-baş-omuz formasyonunu kullanır. Çift tepe/dip'in 3-tepeli akrabası:

  OBO (bearish tepe dönüşü): H(sol omuz)-L-H(baş, en yüksek)-L-H(sağ omuz).
    Baş iki omuzdan yüksek, omuzlar benzer. Boyun = aradaki iki dip.
    Boyun altında KAPANIŞ → düşüş. Hedef = boyun - (baş - boyun).
  TOBO (bullish dip dönüşü): L-H-L(baş, en düşük)-H-L. Boyun üstü kapanış → yükseliş.

Kullanım:
    from miraz.obo import obo_bul
    f = obo_bul(df)
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .bicim import f as _f
from .pivotlar import pivot_listesi


@dataclass
class OBO:
    tip: str            # "OBO" (tepe) / "TOBO" (dip)
    yon: str            # "Bearish" / "Bullish"
    sol_omuz: float
    bas: float
    sag_omuz: float
    boyun: float        # neckline seviyesi
    hedef: float        # ölçülü hareket hedefi
    onayli: bool        # boyun kapanışla kırıldı mı
    aciklama: str


def obo_bul(df: pd.DataFrame, n: int = 5, omuz_tol: float = 0.03,
            son_n_pivot: int = 9) -> OBO | None:
    """Son pivotlarda OBO (H-L-H-L-H) / TOBO (L-H-L-H-L) arar.

    omuz_tol: iki omuzun "benzer" sayılması için yüzde fark (≤%3).
    """
    piv = pivot_listesi(df, n=n)
    if len(piv) < 5:
        return None
    kapanis = float(df["close"].iloc[-1])
    pencere = piv[-son_n_pivot:] if len(piv) > son_n_pivot else piv

    # En yeni 5'li pencereden eskiye doğru tara
    for k in range(len(pencere) - 1, 3, -1):
        beş = pencere[k - 4:k + 1]
        tipler = tuple(p[2] for p in beş)
        f5 = [p[1] for p in beş]

        if tipler == ("H", "L", "H", "L", "H"):        # OBO (tepe)
            sol, d1, bas, d2, sag = f5
            if not (bas > sol and bas > sag):
                continue
            if abs(sol - sag) / max(sol, sag) > omuz_tol:
                continue
            boyun = min(d1, d2)
            yuk = bas - boyun
            if yuk <= 0:
                continue
            hedef = round(boyun - yuk, 6)
            onayli = bool(kapanis < boyun)
            return OBO("OBO", "Bearish", round(sol, 6), round(bas, 6),
                       round(sag, 6), round(boyun, 6), hedef, onayli,
                       _aciklama("OBO", sol, bas, sag, boyun, hedef, onayli,
                                 "altında"))

        if tipler == ("L", "H", "L", "H", "L"):        # TOBO (dip)
            sol, t1, bas, t2, sag = f5
            if not (bas < sol and bas < sag):
                continue
            if abs(sol - sag) / max(sol, sag) > omuz_tol:
                continue
            boyun = max(t1, t2)
            yuk = boyun - bas
            if yuk <= 0:
                continue
            hedef = round(boyun + yuk, 6)
            onayli = bool(kapanis > boyun)
            return OBO("TOBO", "Bullish", round(sol, 6), round(bas, 6),
                       round(sag, 6), round(boyun, 6), hedef, onayli,
                       _aciklama("TOBO", sol, bas, sag, boyun, hedef, onayli,
                                 "üstünde"))
    return None


def _aciklama(tip, sol, bas, sag, boyun, hedef, onayli, yon_soz) -> str:
    durum = (f"boyun {_f(boyun)} {yon_soz} KAPANIŞ ile ONAYLANDI" if onayli
             else f"boyun {_f(boyun)} {yon_soz} kapanış bekleniyor (onaysız)")
    return (f"{tip} (sol omuz {_f(sol)}, baş {_f(bas)}, sağ omuz {_f(sag)}) — "
            f"{durum}. Ölçülü hedef {_f(hedef)}.")


def metin(o: OBO | None) -> str:
    """OBO/TOBO'yu senaryo planı için tek satıra çevirir."""
    if o is None:
        return ""
    ikon = "👤" if o.tip == "OBO" else "🙃"
    onay = "✓ onaylı" if o.onayli else "○ onaysız"
    return f"{ikon} {o.aciklama} [{onay}]"
