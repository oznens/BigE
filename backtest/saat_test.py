"""Saat filtresinin etkisini ölç.

Big E'nin orijinal mantığı: London/NY session'da (İstanbul 11-23) trade et.
Kripto 24/7 olsa da likidite zirvesi bu saatlerde.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from bige.backtest import BacktestKonfig, calistir
from bige.strateji import StratejiParams
from bige.veri import yukle


def main():
    k = BacktestKonfig(baslangic_bakiyesi=10_000, komisyon_bps=4, slippage_bps=2)

    konfigler = [
        ("01_24_7_no_filter", dict(saat_filtresi_aktif=False)),
        ("02_london_NY_11_23", dict(saat_filtresi_aktif=True, saat_baslangic=11, saat_bitis=23)),
        ("03_only_US_15_23",   dict(saat_filtresi_aktif=True, saat_baslangic=15, saat_bitis=23)),
        ("04_only_EU_11_19",   dict(saat_filtresi_aktif=True, saat_baslangic=11, saat_bitis=19)),
        ("05_big_e_pacific",   dict(saat_filtresi_aktif=True, saat_baslangic=9,  saat_bitis=17)),  # ~10pm-6am Pacific = ~9am-17pm Istanbul
    ]

    # 4h test (1d'de saat filtresi anlamsız — günde 1 mum var, hep 03:00 kapanır)
    semboller = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
    aralik = "4h"

    satirlar = []
    for sembol in semboller:
        df = yukle(sembol, aralik)
        for etiket, extra in konfigler:
            p = StratejiParams(
                max_candle_age_after_cross=1,
                tdi_angle_min=1.0,
                near_extreme_margin=5.0,
                trend_filtresi_aktif=True,
                trend_ema_period=200,
                sl_mode="atr",
                sl_atr_multiplier=2.0,
                allow_short=False,
                **extra,
            )
            s = calistir(df, p, k)
            ist = s.istatistikler()
            son = float(s.bakiye_serisi.iloc[-1])
            satirlar.append({
                "sembol": sembol,
                "filtre": etiket,
                "trades": ist["trade_sayisi"],
                "wr": ist.get("win_rate", 0),
                "pf": ist.get("profit_factor", 0),
                "sharpe": ist.get("sharpe", 0),
                "dd": ist.get("max_drawdown", 0),
                "getiri_%": round((son / k.baslangic_bakiyesi - 1) * 100, 2),
            })

    rapor = pd.DataFrame(satirlar)
    print("\n=== Saat filtresi etkisi (4h) ===")
    print(rapor.to_string(index=False))

    cikti = Path("backtest/results/saat_test.csv")
    rapor.to_csv(cikti, index=False)

    print("\n=== Ortalama (4 pair × filtre) ===")
    print(rapor.groupby("filtre")[["trades", "wr", "pf", "sharpe", "dd", "getiri_%"]].mean().round(3).to_string())


if __name__ == "__main__":
    main()
