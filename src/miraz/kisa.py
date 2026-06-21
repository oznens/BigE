"""Kısa (Short) senaryo motoru — direnç reddi = long'un aynası (terminalMiraz).

@tradermiraz long tepki kadar SHORT da işler: "fiyat dirence gelir, reddedilir,
aşağı bir sonraki desteğe kadar düşer." Bu, long senaryosunun simetriğidir:
  • Long  : alttaki desteğe tepki → yukarı hedef.
  • Short : üstteki dirençten ret → aşağı hedef.

Zarif içgörü: long senaryosunun **hedef_kutu**'su (üstteki ana direnç) = short
GİRİŞ bölgesidir; long senaryosunun **destek bölgesi** = short HEDEF'idir. Bu
modül mevcut Senaryo'yu yeniden yorumlar ve bearish sinyallerle (market yapısı
düşüş, bearish divergence, çift tepe, OBO, aşırı alım RSI) skorlar.

Kullanım:
    from miraz.kisa import kisa_senaryo
    ks = kisa_senaryo(df)
    print(ks.metin)
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from . import senaryo as sn
from .bicim import f as _f
from .karar import _kalite


@dataclass
class KisaKarar:
    karar: str           # "Trade" / "Watch" / "Skip"
    kalite: str
    guven: float
    gerekceler: list = field(default_factory=list)
    metin: str = ""


@dataclass
class KisaSenaryo:
    fiyat: float
    yon: str = "Nötr"              # "Düşüş (Short)" / "Nötr"
    direnc_kutu: object = None     # short giriş bölgesi (üstteki direnç)
    bolge_alt: float | None = None # direnç bandının alt sınırı (giriş)
    bolge_ust: float | None = None # direnç bandının üst sınırı
    kritik_seviye: float | None = None  # üstünde KAPANIŞ = iptal
    fitil_seviye: float | None = None   # bu seviyeye fitil senaryoyu bozmaz
    hedef: float | None = None     # aşağı ana hedef (destek)
    ara_hedef: float | None = None # ilk kâr-alma (en yakın destek)
    market_yapisi: object = None
    divergence: object = None
    ikili: object = None
    obo: object = None
    rsi: float | None = None
    mtf_yapi: str | None = None
    karar: object = None
    metin: str = ""


def _short_karar(ks: KisaSenaryo, rr: float | None) -> KisaKarar:
    """Bearish sinyallerden Trade/Watch/Skip + kalite + güven (short bakışı)."""
    if ks.direnc_kutu is None:
        return KisaKarar("Skip", "D", 0.0, ["Yakında satılacak direnç yok"],
                         "🚫 KARAR: Skip — direnç bölgesi yok (D).")
    guven = 50.0
    ger: list[str] = []

    g = getattr(ks.direnc_kutu, "guc", 50)
    katki = (g - 50) / 50 * 15
    guven += katki
    ger.append(f"Direnç gücü {g:.0f} ({katki:+.0f})")

    # Market yapısı — short için düşüş İYİ (long'un tersi)
    my = ks.market_yapisi
    if my is not None:
        durum = getattr(my, "durum", None)
        if durum == "düşüş":
            guven += 12; ger.append("Market yapısı düşüş — short lehine (+12)")
        elif durum == "yükseliş":
            guven -= 15; ger.append("Market yapısı yükseliş — short aleyhine (−15)")

    # MTF: long bakışı "problemli" (HTF aşağı) = short için İYİ
    if ks.mtf_yapi == "problemli":
        guven += 10; ger.append("Üst zaman dilimi aşağı — short lehine (+10)")
    elif ks.mtf_yapi == "sağlıklı":
        guven -= 12; ger.append("Üst zaman dilimi yukarı — short aleyhine (−12)")

    # Bearish divergence — short lehine
    dv = ks.divergence
    if dv is not None:
        if dv.tip == "Bearish":
            guven += 10; ger.append("Bearish divergence — short lehine (+10)")
        elif dv.tip == "Bullish":
            guven -= 8; ger.append("Bullish divergence — short aleyhine (−8)")

    # Çift tepe (onaylı) — short lehine; çift dip aleyhine
    ik = ks.ikili
    if ik is not None:
        if ik.tip == "Çift Tepe" and ik.onayli:
            guven += 12; ger.append("Onaylı çift tepe — short lehine (+12)")
        elif ik.tip == "Çift Dip" and ik.onayli:
            guven -= 10; ger.append("Onaylı çift dip — short aleyhine (−10)")

    # OBO (omuz-baş-omuz, bearish) lehine; TOBO aleyhine
    ob = ks.obo
    if ob is not None:
        tip = getattr(ob, "tip", "")
        if "TOBO" in tip:
            guven -= 8; ger.append("TOBO (bullish) — short aleyhine (−8)")
        elif "OBO" in tip:
            guven += 10; ger.append("OBO (bearish) — short lehine (+10)")

    # Aşırı alım RSI (>70) — short lehine
    if ks.rsi is not None:
        if ks.rsi >= 70:
            guven += 8; ger.append(f"RSI {ks.rsi:.0f} aşırı alım (+8)")
        elif ks.rsi <= 35:
            guven -= 8; ger.append(f"RSI {ks.rsi:.0f} aşırı satım — short riskli (−8)")

    # Risk/Ödül
    if rr is not None:
        if rr >= 2.0:
            guven += 10; ger.append(f"R/R {rr:.1f} ≥ 2 (+10)")
        elif rr >= 1.0:
            guven += 3; ger.append(f"R/R {rr:.1f} (+3)")
        else:
            guven -= 5; ger.append(f"R/R {rr:.1f} < 1 (−5)")

    guven = max(0.0, min(100.0, guven))
    kalite = _kalite(guven)
    if guven >= 70:
        karar = "Trade"
    elif guven >= 50:
        karar = "Watch"
    else:
        karar = "Skip"
    ikon = {"Trade": "✅", "Watch": "👁️", "Skip": "🚫"}[karar]
    metin = (f"{ikon} KARAR: {karar} (SHORT)  |  Kalite: {kalite}  |  "
             f"Güven: %{guven:.0f}")
    return KisaKarar(karar=karar, kalite=kalite, guven=round(guven, 1),
                     gerekceler=ger, metin=metin)


def kisa_senaryo(df: pd.DataFrame, n: int = 5,
                 hedef_min_mesafe: float = 4.0,
                 df_ust: pd.DataFrame | None = None) -> KisaSenaryo:
    """Direnç reddi short senaryosu üretir (long Senaryo'sunu yeniden yorumlar).

    Giriş  = üstteki ana direnç bandının alt kenarı (dirence satış).
    Stop   = direnç bandının üstü + fitil toleransı (üstünde kapanış = iptal).
    Hedef  = aşağıdaki ilk güçlü destek (long senaryosunun destek bölgesi).
    """
    s = sn.senaryo_uret(df, n=n, df_ust=df_ust, r_dolar=0.0)
    fiyat = s.fiyat

    direnc = s.hedef_kutu          # üstteki ana direnç = short giriş bölgesi
    ks = KisaSenaryo(fiyat=fiyat, yon="Nötr",
                     market_yapisi=s.market_yapisi, divergence=s.divergence,
                     ikili=s.ikili, obo=s.obo, rsi=s.rsi, mtf_yapi=s.mtf_yapi)

    if direnc is not None and direnc.merkez > fiyat:
        ks.direnc_kutu = direnc
        ks.bolge_alt = round(direnc.alt, 6)      # dirence satış kenarı (giriş)
        ks.bolge_ust = round(direnc.ust, 6)
        ks.kritik_seviye = ks.bolge_ust          # üstünde KAPANIŞ = iptal
        ks.fitil_seviye = round(ks.bolge_ust * 1.015, 6)  # fitil toleransı
        ks.yon = "Düşüş (Short)"

        # Hedef = aşağıdaki destek (long senaryosunun destek bölgesi üstü)
        if s.bolge_ust is not None:
            ks.hedef = round(s.bolge_ust, 6)
        elif s.destek_kutu is not None:
            ks.hedef = round(s.destek_kutu.ust, 6)
        # Ara hedef = en yakın destek tepesi (varsa, hedefin üstünde)
        if s.bolge_ust is not None and s.bolge_ust < ks.bolge_alt:
            ks.ara_hedef = round(s.bolge_ust, 6)

    # R/R: giriş→stop (yukarı) vs giriş→hedef (aşağı)
    rr = None
    if ks.bolge_alt is not None and ks.fitil_seviye is not None \
            and ks.hedef is not None:
        giris = ks.bolge_alt
        risk = ks.fitil_seviye - giris
        odul = giris - ks.hedef
        if risk > 0 and odul > 0:
            rr = round(odul / risk, 2)

    ks.karar = _short_karar(ks, rr)
    ks.metin = _metin(ks, rr)
    return ks


def _metin(ks: KisaSenaryo, rr: float | None) -> str:
    sat = [ks.karar.metin if ks.karar else "", f"Güncel fiyat: {_f(ks.fiyat)}"]
    if ks.direnc_kutu is None:
        sat.append("Satılacak yakın direnç yok — short için uygun değil.")
        return "\n".join(s for s in sat if s)
    sat.append(f"Senaryo: {ks.yon}")
    sat.append(f"🔻 Giriş (dirence satış): {_f(ks.bolge_alt)}–{_f(ks.bolge_ust)}")
    sat.append(f"   Stop (üstünde kapanış): {_f(ks.kritik_seviye)} "
               f"(fitil {_f(ks.fitil_seviye)})")
    if ks.hedef is not None:
        rr_txt = f"  |  R/R: {rr:.2f}" if rr is not None else ""
        sat.append(f"   Hedef (aşağı destek): {_f(ks.hedef)}{rr_txt}")
    if ks.ara_hedef is not None:
        sat.append(f"   Ara hedef: {_f(ks.ara_hedef)}")
    return "\n".join(s for s in sat if s)
