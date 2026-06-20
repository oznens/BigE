"""Market yapısı (market structure) — Price Action trend okuması.

@tradermiraz MSTR güncellemesinde "teknik olarak market yapısı aşağıya
dönmüş" diyor: fiyat artık daha düşük tepe (LH) + daha düşük dip (LL)
yapıyorsa yapı düşüşte, daha yüksek tepe (HH) + daha yüksek dip (HL)
yapıyorsa yükselişte. Yapının yönü kırıldığı an (CHoCH) trend dönüşünün
ilk teknik işaretidir.

Kavramlar:
  - HH (Higher High)  / HL (Higher Low)  → yükseliş yapısı
  - LH (Lower High)   / LL (Lower Low)    → düşüş yapısı
  - BOS  (Break of Structure): trend yönünde son swing'in kırılması (devam)
  - CHoCH (Change of Character): trende ters ilk kırılım (dönüş sinyali)

Kullanım:
    from miraz.yapi import market_yapisi
    my = market_yapisi(df)   # MarketYapisi(durum=..., kirilim=..., ...)
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .bicim import f as _f
from .pivotlar import pivot_listesi


@dataclass
class MarketYapisi:
    durum: str               # "yükseliş" / "düşüş" / "yatay"
    kirilim: str | None      # "BOS-yukarı"/"BOS-aşağı"/"CHoCH-yukarı"/"CHoCH-aşağı"
    son_yuksek: float        # son swing high (yapısal direnç)
    son_dusuk: float         # son swing low (yapısal destek / "trend bölgesi")
    aciklama: str            # okunabilir özet


def _son_iki(pivotlar, tip: str):
    """Verilen tipteki (H/L) son iki pivotu (fiyat) döndürür."""
    secili = [p for p in pivotlar if p[2] == tip]
    if len(secili) < 2:
        return None, None
    return secili[-2][1], secili[-1][1]


def market_yapisi(df: pd.DataFrame, n: int = 5) -> MarketYapisi | None:
    """Güncel piyasa yapısını (yükseliş/düşüş/yatay) ve son kırılımı döndürür.

    Yöntem:
      - Son iki swing high ve son iki swing low karşılaştırılır.
      - HH+HL → yükseliş, LH+LL → düşüş, karışık → yatay.
      - Güncel KAPANIŞ son yapısal seviyeyi (HL desteği / LH direnci) kırdıysa
        BOS (trend yönünde) veya CHoCH (ters yönde) işaretlenir.
    """
    piv = pivot_listesi(df, n=n)
    onceki_h, son_h = _son_iki(piv, "H")
    onceki_l, son_l = _son_iki(piv, "L")
    if son_h is None or son_l is None:
        return None

    hh = son_h > onceki_h       # daha yüksek tepe
    hl = son_l > onceki_l       # daha yüksek dip

    if hh and hl:
        durum = "yükseliş"
    elif (not hh) and (not hl):
        durum = "düşüş"
    else:
        durum = "yatay"

    kapanis = float(df["close"].iloc[-1])

    # Kırılım: güncel kapanış son yapısal seviyeyi geçti mi?
    kirilim = None
    if kapanis < son_l:
        # Yapısal desteğin (son HL) altına KAPANIŞ
        kirilim = "BOS-aşağı" if durum == "düşüş" else "CHoCH-aşağı"
    elif kapanis > son_h:
        # Yapısal direncin (son LH) üstüne KAPANIŞ
        kirilim = "BOS-yukarı" if durum == "yükseliş" else "CHoCH-yukarı"

    aciklama = _aciklama(durum, kirilim, son_h, son_l)
    return MarketYapisi(durum=durum, kirilim=kirilim,
                        son_yuksek=round(son_h, 4), son_dusuk=round(son_l, 4),
                        aciklama=aciklama)


def _aciklama(durum, kirilim, son_h, son_l) -> str:
    yapi_txt = {
        "yükseliş": "yükselişte (HH + HL)",
        "düşüş": "düşüşte (LH + LL)",
        "yatay": "yatay/kararsız",
    }[durum]
    s = f"Market yapısı {yapi_txt}"
    if kirilim == "CHoCH-aşağı":
        s += f" — yapı AŞAĞIYA döndü (CHoCH): {_f(son_l)} altında kapanış."
    elif kirilim == "CHoCH-yukarı":
        s += f" — yapı YUKARIYA döndü (CHoCH): {_f(son_h)} üstünde kapanış."
    elif kirilim == "BOS-aşağı":
        s += f" — düşüş yönünde kırılım (BOS): {_f(son_l)} kırıldı."
    elif kirilim == "BOS-yukarı":
        s += f" — yükseliş yönünde kırılım (BOS): {_f(son_h)} kırıldı."
    return s


def metin(my: MarketYapisi | None) -> str:
    """Market yapısını senaryo planı için tek satıra çevirir."""
    if my is None:
        return ""
    ikon = {"yükseliş": "📈", "düşüş": "📉", "yatay": "↔️"}[my.durum]
    uyari = ""
    if my.kirilim in ("CHoCH-aşağı", "BOS-aşağı"):
        uyari = " — long açısından temkinli ol, yapı aşağı."
    return f"{ikon} {my.aciklama}{uyari}"
