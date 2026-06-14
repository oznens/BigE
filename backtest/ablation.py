"""Ablation — hangi bileşen gerçekten edge taşıyor? Tek tek aç/kapat ölç.

Over-trading'i kesmek için iki teknik:
  - Trend pozisyonu AYRIK (0/1), sadece rejim değişince işlem.
  - Vol-hedefleme BANTLI: hedef pozisyon ancak yeterince değişince güncellenir
    (sürekli mikro-rebalans → komisyon ölümü engellenir).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from walter import backtest as bt          # noqa: E402
from walter import indikatorler as ind      # noqa: E402
from walter import veri as vr               # noqa: E402
from walter.zaman import ET, saat_ozellikleri  # noqa: E402


def bantli(seri: pd.Series, bant: float = 0.10) -> pd.Series:
    """Pozisyonu yalnızca `bant` kadar değişince günceller (histerez)."""
    vals = seri.to_numpy()
    out = np.zeros_like(vals)
    son = 0.0
    for i, v in enumerate(vals):
        if np.isnan(v):
            v = 0.0
        if abs(v - son) >= bant:
            son = v
        out[i] = son
    return pd.Series(out, index=seri.index)


def kur(df: pd.DataFrame, *, trend=True, vol_hedef=True, zaman=True,
        ema_h=24, ema_y=96, hedef_vol=0.20, max_kald=2.0,
        vol_per=24, bant=0.10) -> pd.Series:
    """Bileşenleri seçmeli açıp pozisyon serisi üretir."""
    close = df["close"]
    poz = pd.Series(1.0, index=df.index)

    if trend:
        rejim = (ind.ema(close, ema_h) > ind.ema(close, ema_y)).astype(float)
        poz = poz * rejim

    if vol_hedef:
        rv = ind.realized_vol(close, vol_per)
        carpan = (hedef_vol / rv).clip(upper=max_kald).fillna(0.0)
        poz = poz * carpan
        poz = bantli(poz, bant=bant)  # churn kes
    # vol_hedef kapalıysa poz zaten 0/1, ayrık → düşük işlem

    if zaman:
        ozk = saat_ozellikleri(df.index, tz=ET)
        hs = ozk["hafta_saati"]
        edge = ((hs >= 163) | (hs <= 18)).to_numpy()
        poz = poz * np.where(edge, 1.0, 0.35)

    return poz.clip(lower=0.0, upper=max_kald).fillna(0.0)


def rapor(ad: str, df: pd.DataFrame, poz: pd.Series, komisyon=0.0006) -> dict:
    d = df.copy()
    d["pozisyon"] = poz
    r = bt.calistir(d, komisyon=komisyon)
    m = r.metrikler
    print(f"{ad:<34} Sharpe={m['sharpe']:+.2f}  CAGR={m['cagr']:+6.1%}  "
          f"MaxDD={m['max_drawdown']:6.1%}  işlem={m['islem_sayisi']:>6,}  "
          f"piyasada={m['piyasada_kalma']:.0%}")
    return m


def main() -> None:
    df = vr.indir(symbol="BTCUSDT", interval="1h", gun=1500)
    print(f"Veri: {len(df):,} mum | {df.index[0].date()} → {df.index[-1].date()}\n")

    bh = bt.buy_hold(df).metrikler
    print(f"{'BUY & HOLD':<34} Sharpe={bh['sharpe']:+.2f}  "
          f"CAGR={bh['cagr']:+6.1%}  MaxDD={bh['max_drawdown']:6.1%}\n")

    print("--- ABLATION (komisyon 6 bps) ---")
    rapor("Trend yalniz (0/1)", df, kur(df, trend=True, vol_hedef=False, zaman=False))
    rapor("Trend + vol-hedef (bantli)", df, kur(df, trend=True, vol_hedef=True, zaman=False))
    rapor("Trend + zaman", df, kur(df, trend=True, vol_hedef=False, zaman=True))
    rapor("Trend + vol + zaman (tam)", df, kur(df, trend=True, vol_hedef=True, zaman=True))
    rapor("Zaman yalniz (long/azalt)", df, kur(df, trend=False, vol_hedef=False, zaman=True))

    print("\n--- TREND PARAMETRE DUYARLILIĞI (trend yalniz, 0/1) ---")
    for eh, ey in [(12, 48), (24, 96), (24, 168), (48, 200), (12, 96)]:
        rapor(f"EMA {eh}/{ey}", df, kur(df, trend=True, vol_hedef=False,
                                        zaman=False, ema_h=eh, ema_y=ey))


if __name__ == "__main__":
    main()
