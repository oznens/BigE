"""Out-of-sample validation, calibration and risk statistics for live-style labs."""

from __future__ import annotations

from dataclasses import dataclass, field
import random

import pandas as pd

from .lab_v2 import ExecutionCosts, LiveLabRapor, backtest_live_pipeline


@dataclass
class Performans:
    n: int
    win_rate: float
    toplam_r: float
    beklenti_r: float
    profit_factor: float
    max_drawdown_r: float
    bootstrap_beklenti_ci: tuple[float, float]


@dataclass
class KalibrasyonDilimi:
    alt: float
    ust: float
    n: int
    ort_guven: float
    gercek_wr: float
    fark: float


@dataclass
class DonemSonucu:
    ad: str
    baslangic: str
    bitis: str
    rapor: LiveLabRapor
    performans: Performans
    kalibrasyon: list[KalibrasyonDilimi] = field(default_factory=list)


@dataclass
class WalkForwardRapor:
    train: DonemSonucu
    validation: DonemSonucu
    oos: DonemSonucu


def _kapali(rapor: LiveLabRapor):
    return [i for i in rapor.islemler if i.sonuc in ("TP", "STOP")]


def max_drawdown_r(rler: list[float]) -> float:
    equity = 0.0
    zirve = 0.0
    dd = 0.0
    for r in rler:
        equity += r
        zirve = max(zirve, equity)
        dd = max(dd, zirve - equity)
    return round(dd, 4)


def profit_factor(rler: list[float]) -> float:
    kazanc = sum(r for r in rler if r > 0)
    zarar = -sum(r for r in rler if r < 0)
    if zarar == 0:
        return float("inf") if kazanc > 0 else 0.0
    return round(kazanc / zarar, 4)


def bootstrap_beklenti_ci(rler: list[float], *, tekrar: int = 2000,
                          seed: int = 42, alpha: float = 0.05) -> tuple[float, float]:
    """Trade-level bootstrap CI for mean net R."""
    if not rler:
        return (0.0, 0.0)
    rng = random.Random(seed)
    n = len(rler)
    ort = []
    for _ in range(max(100, tekrar)):
        ornek = [rler[rng.randrange(n)] for _ in range(n)]
        ort.append(sum(ornek) / n)
    ort.sort()
    lo_i = int((alpha / 2) * (len(ort) - 1))
    hi_i = int((1 - alpha / 2) * (len(ort) - 1))
    return (round(ort[lo_i], 4), round(ort[hi_i], 4))


def performans(rapor: LiveLabRapor, *, bootstrap_tekrar: int = 2000) -> Performans:
    kapali = _kapali(rapor)
    rler = [i.r for i in kapali]
    tp = sum(i.sonuc == "TP" for i in kapali)
    return Performans(
        n=len(kapali),
        win_rate=round(100 * tp / len(kapali), 2) if kapali else 0.0,
        toplam_r=round(sum(rler), 4),
        beklenti_r=round(sum(rler) / len(rler), 4) if rler else 0.0,
        profit_factor=profit_factor(rler),
        max_drawdown_r=max_drawdown_r(rler),
        bootstrap_beklenti_ci=bootstrap_beklenti_ci(rler, tekrar=bootstrap_tekrar),
    )


def kalibrasyon(rapor: LiveLabRapor, *, bin_genislik: int = 10) -> list[KalibrasyonDilimi]:
    """Compare heuristic confidence score with observed TP frequency."""
    kapali = _kapali(rapor)
    out = []
    for alt in range(0, 100, bin_genislik):
        ust = min(100, alt + bin_genislik)
        sec = [i for i in kapali if alt <= float(i.guven) < ust or (ust == 100 and i.guven == 100)]
        if not sec:
            continue
        avg = sum(float(i.guven) for i in sec) / len(sec)
        wr = 100 * sum(i.sonuc == "TP" for i in sec) / len(sec)
        out.append(KalibrasyonDilimi(
            alt=float(alt), ust=float(ust), n=len(sec),
            ort_guven=round(avg, 2), gercek_wr=round(wr, 2),
            fark=round(wr - avg, 2),
        ))
    return out


def _donem(df: pd.DataFrame, bas, bit, *, ad: str,
           df_ust: pd.DataFrame | None, costs: ExecutionCosts,
           yon: str, rr_hedef: float, adim: int, max_bar: int,
           min_bar: int, warmup_bar: int) -> DonemSonucu:
    bas_ts = pd.Timestamp(bas)
    bit_ts = pd.Timestamp(bit)
    asil = df[(df.index >= bas_ts) & (df.index < bit_ts)]
    if asil.empty:
        raise ValueError(f"{ad} dönemi boş")

    # Historical indicators need context before the scored period. Keep a warmup
    # prefix, run the live pipeline, then retain only decisions inside the period.
    bas_pos = df.index.searchsorted(asil.index[0])
    warm_bas = max(0, bas_pos - warmup_bar)
    pencere_df = df.iloc[warm_bas: df.index.searchsorted(bit_ts)]
    ust = None
    if df_ust is not None:
        ust = df_ust[df_ust.index < bit_ts]

    rapor = backtest_live_pipeline(
        pencere_df, df_ust=ust, yon=yon, adim=adim, max_bar=max_bar,
        pencere=len(pencere_df), min_bar=min(min_bar, max(20, warmup_bar // 2)),
        rr_hedef=rr_hedef, costs=costs,
    )
    ilk_global = warm_bas
    donem_bas_global = bas_pos
    donem_bit_global = df.index.searchsorted(bit_ts)
    rapor.islemler = [
        i for i in rapor.islemler
        if donem_bas_global <= ilk_global + i.bar < donem_bit_global
    ]
    return DonemSonucu(
        ad=ad, baslangic=asil.index[0].isoformat(), bitis=asil.index[-1].isoformat(),
        rapor=rapor, performans=performans(rapor), kalibrasyon=kalibrasyon(rapor),
    )


def walk_forward_3way(
    df: pd.DataFrame,
    *,
    train_end,
    validation_end,
    df_ust: pd.DataFrame | None = None,
    yon: str = "long",
    rr_hedef: float = 1.0,
    costs: ExecutionCosts | None = None,
    adim: int = 6,
    max_bar: int = 60,
    min_bar: int = 200,
    warmup_bar: int = 250,
) -> WalkForwardRapor:
    """Chronological train/validation/OOS split with no shuffled observations.

    The current heuristic engine does not fit parameters on train yet; therefore
    train is a development benchmark, validation is for rule/threshold choices,
    and OOS is the untouched final estimate. Future learned components can be
    trained only on the first segment without changing this API.
    """
    if df.empty:
        raise ValueError("df boş")
    costs = costs or ExecutionCosts()
    start = df.index[0]
    end_exclusive = df.index[-1] + pd.Timedelta(nanoseconds=1)
    t_end = pd.Timestamp(train_end)
    v_end = pd.Timestamp(validation_end)
    if not (start < t_end < v_end < end_exclusive):
        raise ValueError("train_end < validation_end ve veri aralığı içinde olmalı")

    ortak = dict(df_ust=df_ust, costs=costs, yon=yon, rr_hedef=rr_hedef,
                 adim=adim, max_bar=max_bar, min_bar=min_bar, warmup_bar=warmup_bar)
    return WalkForwardRapor(
        train=_donem(df, start, t_end, ad="train", **ortak),
        validation=_donem(df, t_end, v_end, ad="validation", **ortak),
        oos=_donem(df, v_end, end_exclusive, ad="oos", **ortak),
    )
