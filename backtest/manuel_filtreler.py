"""Big E'nin manuel filtrelerinin mekanik karşılıklarını test et.

Her filtreyi tek tek açıp etkisini ölç. Sonra hepsi birlikte.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from bige.backtest import BacktestKonfig, calistir
from bige.indikatorler import mtf_trend_ekle
from bige.strateji import StratejiParams
from bige.veri import yukle


def yap_p(**extra) -> StratejiParams:
    base = dict(
        max_candle_age_after_cross=1,
        tdi_angle_min=1.0,
        near_extreme_margin=5.0,
        trend_filtresi_aktif=True,
        trend_ema_period=200,
        sl_mode="atr",
        sl_atr_multiplier=2.0,
        allow_short=False,
        saat_filtresi_aktif=True,
    )
    base.update(extra)
    return StratejiParams(**base)


def main():
    k = BacktestKonfig(baslangic_bakiyesi=10_000, komisyon_bps=4, slippage_bps=2)
    semboller = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
    aralik = "4h"

    konfigler = [
        ("01_baseline",        {}),
        ("02_konsolidasyon",   dict(konsolidasyon_filtresi=True)),
        ("03_sr_yakinlik",     dict(sr_filtresi=True)),
        ("04_wick_filtre",     dict(wick_filtresi=True)),
        ("05_mtf_onay_1d",     dict(mtf_onay_filtresi=True)),
        ("06_hepsi_birlikte",  dict(
            konsolidasyon_filtresi=True,
            sr_filtresi=True,
            wick_filtresi=True,
            mtf_onay_filtresi=True,
        )),
    ]

    satirlar = []
    for sembol in semboller:
        df_4h = yukle(sembol, "4h")
        # MTF için 1D verisi gerekli — varsa yükle, yoksa MTF filtresi atla
        try:
            df_1d = yukle(sembol, "1d")
            df_4h_mtf = mtf_trend_ekle(df_4h, df_1d, ema_p=50)
        except Exception:
            df_4h_mtf = df_4h

        for etiket, extra in konfigler:
            df_kullan = df_4h_mtf if extra.get("mtf_onay_filtresi") else df_4h
            p = yap_p(**extra)
            s = calistir(df_kullan, p, k)
            ist = s.istatistikler()
            if ist["trade_sayisi"] == 0:
                satirlar.append({
                    "sembol": sembol.replace("USDT", ""),
                    "config": etiket, "trades": 0, "wr": 0, "pf": 0,
                    "sharpe": 0, "dd": 0, "getiri_%": 0,
                })
                continue
            son = float(s.bakiye_serisi.iloc[-1])
            satirlar.append({
                "sembol": sembol.replace("USDT", ""),
                "config": etiket,
                "trades": ist["trade_sayisi"],
                "wr": ist.get("win_rate", 0),
                "pf": ist.get("profit_factor", 0),
                "sharpe": ist.get("sharpe", 0),
                "dd": ist.get("max_drawdown", 0),
                "getiri_%": round((son / k.baslangic_bakiyesi - 1) * 100, 2),
            })

    rapor = pd.DataFrame(satirlar)
    print("\n=== Manuel filtre testi (4h, 4 pair × 6 config) ===")
    pivot = rapor.pivot_table(
        index="config",
        columns="sembol",
        values="sharpe",
    ).round(2)
    print("\nSharpe matrisi:")
    print(pivot.to_string())

    pivot_dd = rapor.pivot_table(
        index="config", columns="sembol", values="dd",
    ).round(3)
    print("\nMax DD matrisi:")
    print(pivot_dd.to_string())

    pivot_getiri = rapor.pivot_table(
        index="config", columns="sembol", values="getiri_%",
    ).round(2)
    print("\nGetiri (%) matrisi:")
    print(pivot_getiri.to_string())

    print("\n=== Ortalama (4 pair) ===")
    print(rapor.groupby("config")[["trades", "wr", "pf", "sharpe", "dd", "getiri_%"]].mean().round(3).to_string())

    cikti = Path("backtest/results/manuel_filtreler.csv")
    rapor.to_csv(cikti, index=False)


if __name__ == "__main__":
    main()
