"""Miraz-v2: tweet/chart arşivindeki operasyonel kurallara sadık shadow motor.

Bu modül mevcut canlı radarın kararlarını değiştirmez. Amaç, arşivde açıkça
tekrarlanan üç kuralı ölçülebilir hale getirmektir:

1) Tetik = seviye ötesinde MUM KAPANIŞI + hacim teyidi (fitil tek başına yetmez)
2) Kırılım sonrası retest teyidi
3) Minimum 1:2 R/R; +1R'de kısmi kâr, kalan pozisyonu BE'ye taşıma

Shadow modda paralel ölçülür; yeterli OOS örnek oluşmadan canlı Trade kararını
otomatik değiştirmek için kullanılmamalıdır.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class MirazV2Ayar:
    rr_hedef: float = 2.0
    ilk_kar_r: float = 1.0
    ilk_kar_orani: float = 0.65
    hacim_pencere: int = 20
    hacim_carpan: float = 1.0
    retest_bar: int = 8
    retest_tolerans: float = 0.003


@dataclass(frozen=True)
class MirazV2Plan:
    taraf: str
    giris: float
    stop: float
    ilk_hedef: float
    ana_hedef: float
    rr: float
    ilk_kar_orani: float


@dataclass(frozen=True)
class MirazV2Sonuc:
    durum: str  # TP2 / BE / STOP / ACIK
    gross_r: float
    ilk_kar_alindi: bool
    kapanis_zaman: str = ""


def plan_uret(giris: float, stop: float, taraf: str = "Long",
              ayar: MirazV2Ayar | None = None) -> MirazV2Plan | None:
    """1R kısmi hedef + en az 2R ana hedef üretir."""
    ayar = ayar or MirazV2Ayar()
    if giris <= 0 or stop <= 0 or giris == stop:
        return None
    short = taraf == "Short"
    if short and stop <= giris:
        return None
    if not short and stop >= giris:
        return None
    risk = abs(giris - stop)
    yon = -1.0 if short else 1.0
    ilk = giris + yon * ayar.ilk_kar_r * risk
    ana = giris + yon * ayar.rr_hedef * risk
    return MirazV2Plan(
        taraf=taraf, giris=float(giris), stop=float(stop),
        ilk_hedef=float(ilk), ana_hedef=float(ana), rr=float(ayar.rr_hedef),
        ilk_kar_orani=float(ayar.ilk_kar_orani))


def kapanis_hacim_onayi(df: pd.DataFrame, seviye: float, taraf: str,
                        ayar: MirazV2Ayar | None = None) -> bool:
    """Son KAPANMIŞ mum seviyeyi close ile kırmış ve hacmi normal-altı değil mi?

    Long: önceki close <= seviye, son close > seviye.
    Short: önceki close >= seviye, son close < seviye.
    Hacim, önceki `hacim_pencere` mumun medyanının `hacim_carpan` katı olmalı.
    """
    ayar = ayar or MirazV2Ayar()
    if df is None or len(df) < max(3, ayar.hacim_pencere + 1):
        return False
    if "close" not in df or "volume" not in df:
        return False
    onceki = float(df["close"].iloc[-2])
    son = float(df["close"].iloc[-1])
    vol = float(df["volume"].iloc[-1])
    med = float(df["volume"].iloc[-(ayar.hacim_pencere + 1):-1].median())
    if med <= 0:
        return False
    hacim_ok = vol >= med * ayar.hacim_carpan
    if taraf == "Short":
        kirilim = onceki >= seviye and son < seviye
    else:
        kirilim = onceki <= seviye and son > seviye
    return bool(kirilim and hacim_ok)


def retest_onayi(df: pd.DataFrame, seviye: float, taraf: str,
                  kirilim_idx: int | None = None,
                  ayar: MirazV2Ayar | None = None) -> bool:
    """Kırılım sonrası fiyatın seviyeyi retest edip doğru tarafta kapandığını doğrular.

    Long retest: low seviyeye tolerans içinde gelir, close >= seviye.
    Short retest: high seviyeye tolerans içinde gelir, close <= seviye.
    """
    ayar = ayar or MirazV2Ayar()
    if df is None or len(df) < 2 or seviye <= 0:
        return False
    bas = (kirilim_idx + 1) if kirilim_idx is not None else max(0, len(df) - ayar.retest_bar)
    son = min(len(df), bas + ayar.retest_bar)
    tol = abs(seviye) * ayar.retest_tolerans
    for _, bar in df.iloc[bas:son].iterrows():
        if taraf == "Short":
            temas = float(bar["high"]) >= seviye - tol
            kabul = float(bar["close"]) <= seviye
        else:
            temas = float(bar["low"]) <= seviye + tol
            kabul = float(bar["close"]) >= seviye
        if temas and kabul:
            return True
    return False


def yonetim_simule(df: pd.DataFrame, plan: MirazV2Plan,
                    baslangic: int = 0) -> MirazV2Sonuc:
    """Miraz tarzı 1R kısmi kâr → BE → 2R final yönetimini OHLC ile simüle eder.

    Muhafazakâr mum-içi sıra kullanılır: aynı mumda olumsuz ve olumlu seviye
    birlikte görülürse olumsuz sonuç önce kabul edilir.

    Sonuç R hesabı:
      STOP (1R görülmeden) = -1R
      1R'de %65 kâr + kalan BE = +0.65R
      1R'de %65 kâr + kalan 2R = 0.65*1 + 0.35*2 = +1.35R
    """
    if df is None or len(df) <= baslangic:
        return MirazV2Sonuc("ACIK", 0.0, False, "")
    short = plan.taraf == "Short"
    partial = False
    pay = plan.ilk_kar_orani

    for idx, bar in df.iloc[baslangic:].iterrows():
        lo = float(bar["low"])
        hi = float(bar["high"])
        zaman = idx.isoformat() if hasattr(idx, "isoformat") else str(idx)

        if not partial:
            stop_hit = hi >= plan.stop if short else lo <= plan.stop
            one_r_hit = lo <= plan.ilk_hedef if short else hi >= plan.ilk_hedef
            if stop_hit:
                return MirazV2Sonuc("STOP", -1.0, False, zaman)
            if one_r_hit:
                partial = True

        if partial:
            # Kalan pozisyonun stop'u artık giriş (BE).
            be_hit = hi >= plan.giris if short else lo <= plan.giris
            tp2_hit = lo <= plan.ana_hedef if short else hi >= plan.ana_hedef
            if be_hit:
                return MirazV2Sonuc("BE", round(pay, 4), True, zaman)
            if tp2_hit:
                r = pay * 1.0 + (1.0 - pay) * plan.rr
                return MirazV2Sonuc("TP2", round(r, 4), True, zaman)

    r_acik = pay if partial else 0.0
    return MirazV2Sonuc("ACIK", round(r_acik, 4), partial, "")
