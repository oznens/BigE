"""Çoklu-bölge yol haritası — TAO tarzı HTF planı.

@tradermiraz TAO vakasında olduğu gibi: aynı anda tüm anlamlı bölgeleri
yönlü rolleriyle tek planda listeler.
  - Fiyatın ÜSTÜ (direnç) → SHORT bölgeleri
  - Fiyatın ALTI (destek)  → LONG bölgeleri
  - Destekte harmonik D çakışması varsa → 🔵 MAVİ DAİRE (en yüksek güven)

Referans: notlar/vaka_tao.md
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from . import harmonik as hrm
from . import kutular as kt
from . import pivotlar as pv

_COIN_AD = {
    "BTCUSDT": "BTC", "ETHUSDT": "ETH", "SOLUSDT": "SOL",
    "BNBUSDT": "BNB", "XRPUSDT": "XRP", "AVAXUSDT": "AVAX",
}


@dataclass
class Bolge:
    alt: float
    ust: float
    merkez: float
    renk: str
    tip: str            # "Destek" / "Direnç"
    rol: str            # "LONG" / "SHORT"
    guc: float
    mesafe_yuzde: float
    mavi_daire: float | None = None   # harmonik D (varsa)
    daire_isim: str | None = None     # harmonik pattern adı


@dataclass
class YolHaritasi:
    symbol: str
    interval: str
    fiyat: float
    bolgeler: list[Bolge]   # fiyata göre azalan (üst→alt) sıralı
    metin: str
    patternler: list = None  # grafikte gösterilecek harmonik patternler (HarmonikSonuc)
    hedef: float | None = None  # projeksiyon oku hedefi (en yakın long üstü direnç)
    olusan: object = None    # oluşmakta olan harmonik (OlusanHarmonik | None)


def yol_haritasi_uret(
    df: pd.DataFrame,
    symbol: str = "",
    interval: str = "",
    n: int = 5,
    min_guc: float = 55.0,
    mesafe_limit: float = 30.0,
    max_yon: int = 4,
    min_kalite: float = 40.0,
) -> YolHaritasi:
    """Çoklu-bölge yol haritası üretir.

    max_yon : her yön (long/short) için en fazla bölge sayısı.
    """
    fiyat = float(df["close"].iloc[-1])

    kutular = kt.kutulari_bul(df, n=n, adaptif=True, mesafe_limit=mesafe_limit,
                              min_guc=min_guc)

    # Harmonik D noktaları (mavi daire tespiti için)
    pivlar = pv.pivot_listesi(df, n=n)
    patternler = hrm.tara(df, pivlar, min_kalite=min_kalite)
    bullish_D = [(p.D, p.isim) for p in patternler if p.yon == "Bullish"]

    bolgeler: list[Bolge] = []
    for k in kutular:
        rol = "SHORT" if k.tip == "Direnç" else "LONG"
        md = md_isim = None
        if k.tip == "Destek":
            pay = max((k.ust - k.alt) * 0.5, k.alt * 0.01)
            iceride = [(d, ad) for (d, ad) in bullish_D
                       if (k.alt - pay) <= d <= (k.ust + pay)]
            if iceride:
                md, md_isim = max(iceride, key=lambda x: x[0])
        bolgeler.append(Bolge(
            alt=round(k.alt, 4), ust=round(k.ust, 4), merkez=round(k.merkez, 4),
            renk=k.renk, tip=k.tip, rol=rol, guc=k.guc,
            mesafe_yuzde=k.mesafe_yuzde,
            mavi_daire=round(md, 4) if md else None, daire_isim=md_isim))

    # Her yön için en güçlü max_yon bölge
    shortlar = sorted([b for b in bolgeler if b.rol == "SHORT"],
                      key=lambda b: b.guc, reverse=True)[:max_yon]
    longlar = sorted([b for b in bolgeler if b.rol == "LONG"],
                     key=lambda b: b.guc, reverse=True)[:max_yon]
    secili = sorted(shortlar + longlar, key=lambda b: b.merkez, reverse=True)

    # Grafikte gösterilecek harmonik: sadece en kaliteli/güncel TEK pattern
    # (çok pattern üst üste gelince kırmızı alan grafiği kaplıyor).
    en_iyi_pat = sorted(patternler, key=lambda p: (p.kalite, p.D_idx),
                        reverse=True)[:1]

    # Projeksiyon oku hedefi: fiyatın üstündeki en yakın SHORT bölgesi
    ust_shortlar = sorted([b for b in shortlar if b.merkez > fiyat],
                          key=lambda b: b.merkez)
    hedef = ust_shortlar[0].alt if ust_shortlar else None

    # Oluşmakta olan (D henüz tamamlanmamış) harmonik
    olusan = hrm.olusan_harmonik(df, pivlar)

    metin = _metin_uret(symbol, interval, fiyat, secili, olusan)
    return YolHaritasi(symbol=symbol, interval=interval, fiyat=fiyat,
                       bolgeler=secili, metin=metin, patternler=en_iyi_pat,
                       hedef=hedef, olusan=olusan)


def _metin_uret(symbol, interval, fiyat, bolgeler, olusan=None) -> str:
    coin = _COIN_AD.get(symbol, symbol.replace("USDT", "")) if symbol else ""
    sat = [f"{coin} | Yol haritası ({interval})".strip(" |"),
           f"Güncel fiyat: {fiyat:,.4f}", ""]

    if olusan is not None:
        sat.append(
            f"🔶 OLUŞMAKTA OLAN {olusan.yon} {olusan.isim}: D henüz tamamlanmadı, "
            f"PRZ projeksiyonu {olusan.prz_alt:,.2f}–{olusan.prz_ust:,.2f} "
            f"(merkez {olusan.D:,.2f}). Fiyat buraya gelirse pattern tamamlanır.")
        sat.append("")

    shortlar = [b for b in bolgeler if b.rol == "SHORT"]
    longlar = [b for b in bolgeler if b.rol == "LONG"]

    if shortlar:
        sat.append("🔴 SHORT bölgeleri (fiyatın üstü — direnç):")
        for b in shortlar:
            sat.append(f"   {b.ust:,.2f}–{b.alt:,.2f}  {b.renk} "
                       f"(güç {b.guc:.0f}, {b.mesafe_yuzde:+.1f}%)")
    sat.append(f"   ── güncel fiyat: {fiyat:,.4f} ──")
    if longlar:
        sat.append("🟢 LONG bölgeleri (fiyatın altı — destek):")
        for b in longlar:
            ek = ""
            if b.mavi_daire is not None:
                ek = f"  🔵 MAVİ DAİRE {b.mavi_daire:,.2f} ({b.daire_isim} harmonik D)"
            sat.append(f"   {b.ust:,.2f}–{b.alt:,.2f}  {b.renk} "
                       f"(güç {b.guc:.0f}, {b.mesafe_yuzde:+.1f}%){ek}")

    return "\n".join(sat)


def yazdir(yh: YolHaritasi) -> None:
    print(f"\n{'='*68}\n{yh.symbol} / {yh.interval} — Yol Haritası\n{'='*68}")
    print(yh.metin)
    print("=" * 68)
