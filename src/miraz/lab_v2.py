"""Live-style backtest pipeline with execution costs.

This module intentionally reuses the radar's live decision/validity rules so
historical tests and the scanner agree on Trade/Watch/Elenen semantics.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from . import konsept as kons
from . import senaryo as sn
from .kisa import kisa_senaryo
from .lab import Islem, _kur_islem, _kur_kisa, _simule
from .radar import (
    _kategori_belirle,
    _short_kategori,
    _konsept_etki,
    _konsept_skor_uygula,
    _stop_zaten_vuruldu,
    _gec_kalmis,
    _hedef_zaten_gorundu,
)


@dataclass(frozen=True)
class ExecutionCosts:
    """Simple futures execution-cost model expressed in basis points.

    fee_bps and slippage_bps are applied on both entry and exit. funding_bps
    is a total holding-period charge. Zero values reproduce the old gross-R
    behaviour.
    """

    fee_bps: float = 4.0
    slippage_bps: float = 2.0
    funding_bps: float = 0.0

    @property
    def roundtrip_bps(self) -> float:
        return 2.0 * (self.fee_bps + self.slippage_bps) + self.funding_bps


@dataclass
class LiveLabRapor:
    islemler: list[Islem] = field(default_factory=list)
    elenen: int = 0
    watch: int = 0
    skip: int = 0
    maliyet_r: float = 0.0

    @property
    def dolan(self):
        return [i for i in self.islemler if i.sonuc in ("TP", "STOP")]

    @property
    def win_rate(self) -> float:
        d = self.dolan
        return 100.0 * sum(i.sonuc == "TP" for i in d) / len(d) if d else 0.0

    @property
    def toplam_r(self) -> float:
        return round(sum(i.r for i in self.dolan), 3)

    @property
    def beklenti_r(self) -> float:
        return round(self.toplam_r / len(self.dolan), 4) if self.dolan else 0.0


def _maliyet_r(giris: float, stop: float, costs: ExecutionCosts) -> float:
    """Convert notional execution costs to R using entry-stop risk distance."""
    if giris <= 0:
        return 0.0
    risk_pct = abs(giris - stop) / giris
    if risk_pct <= 0:
        return 0.0
    cost_pct = costs.roundtrip_bps / 10_000.0
    return cost_pct / risk_pct


def _ust_pencere(df_ust: pd.DataFrame | None, karar_zamani) -> pd.DataFrame | None:
    if df_ust is None:
        return None
    return df_ust[df_ust.index <= karar_zamani]


def _live_long(prefix: pd.DataFrame, ust: pd.DataFrame | None, r_dolar: float,
               rr_hedef: float):
    s = sn.senaryo_uret(prefix, df_ust=ust, r_dolar=r_dolar)
    from .risk import risk_plani
    rp = risk_plani(s, r_dolar=r_dolar, rr_hedef=rr_hedef) if s.destek_kutu else None
    if rp is None:
        return s, None, "Skip"

    try:
        ks = kons.tara_konseptler(prefix)
    except Exception:
        ks = {}
    etki, _ = _konsept_etki(ks, "Long")
    _konsept_skor_uygula(s.karar, etki, trade_engeli=bool(s.kirilma_riski))
    kategori, _ = _kategori_belirle(s)

    if kategori in ("Trade", "Watch") and _stop_zaten_vuruldu(prefix, rp.stop, "Long"):
        kategori = "Elenen"
    elif kategori in ("Trade", "Watch") and _gec_kalmis(s.fiyat, rp.giris, rp.hedef, "Long"):
        kategori = "Elenen"
    elif kategori in ("Trade", "Watch") and _hedef_zaten_gorundu(prefix, rp.hedef, "Long"):
        kategori = "Elenen"
    return s, (rp.giris, rp.stop, rp.hedef, rp.rr_orani), kategori


def _live_short(prefix: pd.DataFrame, ust: pd.DataFrame | None, rr_hedef: float):
    from .risk import mesafe_hedef

    ks = kisa_senaryo(prefix, df_ust=ust)
    try:
        kons_sinyal = kons.tara_konseptler(prefix)
    except Exception:
        kons_sinyal = {}
    etki, _ = _konsept_etki(kons_sinyal, "Short")
    _konsept_skor_uygula(ks.karar, etki)
    kategori, _ = _short_kategori(ks)

    giris = ks.giris
    if giris is None or ks.fitil_seviye is None or ks.fitil_seviye <= giris:
        return ks, None, "Skip"
    hedef = mesafe_hedef(giris, ks.fitil_seviye, rr_hedef)
    rr = rr_hedef

    if kategori in ("Trade", "Watch") and _stop_zaten_vuruldu(prefix, ks.fitil_seviye, "Short"):
        kategori = "Elenen"
    elif kategori in ("Trade", "Watch") and _gec_kalmis(ks.fiyat, giris, hedef, "Short"):
        kategori = "Elenen"
    elif kategori in ("Trade", "Watch") and _hedef_zaten_gorundu(prefix, hedef, "Short"):
        kategori = "Elenen"
    return ks, (giris, ks.fitil_seviye, hedef, rr), kategori


def backtest_live_pipeline(
    df: pd.DataFrame,
    *,
    df_ust: pd.DataFrame | None = None,
    yon: str = "long",
    adim: int = 6,
    max_bar: int = 60,
    pencere: int = 600,
    min_bar: int = 200,
    r_dolar: float = 25.0,
    rr_hedef: float = 1.0,
    costs: ExecutionCosts | None = None,
) -> LiveLabRapor:
    """Backtest the same live radar validity pipeline without look-ahead.

    Each decision sees only df[:i+1], and HTF data is truncated at that bar's
    timestamp. Only final live-category Trade setups are simulated.
    """
    costs = costs or ExecutionCosts()
    rapor = LiveLabRapor()
    n = len(df)
    bas = max(min_bar, n - pencere)
    son_acilan = -10_000

    for i in range(bas, n - 1, adim):
        prefix = df.iloc[: i + 1]
        ust = _ust_pencere(df_ust, prefix.index[-1])
        try:
            if yon == "short":
                s, kur, kategori = _live_short(prefix, ust, rr_hedef)
            else:
                s, kur, kategori = _live_long(prefix, ust, r_dolar, rr_hedef)
        except Exception:
            continue

        if kategori == "Elenen":
            rapor.elenen += 1
            continue
        if kategori == "Watch":
            rapor.watch += 1
            continue
        if kategori != "Trade" or kur is None:
            rapor.skip += 1
            continue
        if i - son_acilan < adim:
            continue

        giris, stop, hedef, rr = kur
        sonuc, _ = _simule(df, i, giris, stop, hedef, max_bar, yon=yon)
        gross_r = {"TP": rr, "STOP": -1.0}.get(sonuc, 0.0)
        cost_r = _maliyet_r(giris, stop, costs) if sonuc in ("TP", "STOP") else 0.0
        net_r = gross_r - cost_r
        rapor.maliyet_r += cost_r
        karar = getattr(s, "karar", None)
        rapor.islemler.append(Islem(
            bar=i, giris=giris, stop=stop, hedef=hedef, rr=rr,
            kalite=getattr(karar, "kalite", "D"),
            guven=getattr(karar, "guven", 0.0), sonuc=sonuc, r=round(net_r, 4),
        ))
        if sonuc in ("TP", "STOP"):
            son_acilan = i

    rapor.maliyet_r = round(rapor.maliyet_r, 4)
    return rapor
