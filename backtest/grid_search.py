"""Parametre grid search.

3 ana parametrenin (SL multiplier, trend EMA, MTF EMA) etkisini tara,
pair'ler arası ortalama Sharpe ile en iyi kombinasyonu bul.

Overfit'e karşı: tek pair'in bulgusu değil, 3 pair ortalaması raporlanır.
"""
from __future__ import annotations

import itertools
from pathlib import Path

import pandas as pd

from bige.backtest import BacktestKonfig, calistir
from bige.indikatorler import mtf_trend_ekle
from bige.strateji import StratejiParams
from bige.veri import yukle


def main():
    k = BacktestKonfig(baslangic_bakiyesi=10_000, komisyon_bps=4, slippage_bps=2)
    pairs = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

    # Veriyi bir kez yükle
    data: dict[str, tuple[pd.DataFrame, pd.DataFrame]] = {}
    for sembol in pairs:
        df_4h = yukle(sembol, "4h")
        df_1d = yukle(sembol, "1d")
        data[sembol] = (df_4h, df_1d)

    # Grid
    sl_mults = [1.5, 2.0, 2.5, 3.0]
    trend_emas = [50, 100, 200]
    mtf_emas = [20, 50, 100]

    sonuclar = []
    toplam = len(sl_mults) * len(trend_emas) * len(mtf_emas)
    sayac = 0

    for sl_mult, trend_ema, mtf_ema in itertools.product(sl_mults, trend_emas, mtf_emas):
        sayac += 1
        p = StratejiParams(
            max_candle_age_after_cross=1,
            tdi_angle_min=1.0,
            near_extreme_margin=5.0,
            trend_filtresi_aktif=True,
            trend_ema_period=trend_ema,
            sl_mode="atr",
            sl_atr_multiplier=sl_mult,
            allow_short=False,
            saat_filtresi_aktif=True,
            mtf_onay_filtresi=True,
        )

        per_pair = []
        for sembol in pairs:
            df_4h, df_1d = data[sembol]
            df = mtf_trend_ekle(df_4h, df_1d, ema_p=mtf_ema)
            s = calistir(df, p, k)
            ist = s.istatistikler()
            if ist["trade_sayisi"] == 0:
                continue
            son = float(s.bakiye_serisi.iloc[-1])
            per_pair.append({
                "sharpe": ist.get("sharpe", 0),
                "dd": ist.get("max_drawdown", 0),
                "getiri": (son / k.baslangic_bakiyesi - 1) * 100,
                "trades": ist["trade_sayisi"],
                "pf": ist.get("profit_factor", 0),
            })

        if not per_pair:
            continue
        df_pair = pd.DataFrame(per_pair)
        sonuclar.append({
            "sl_mult": sl_mult,
            "trend_ema": trend_ema,
            "mtf_ema": mtf_ema,
            "avg_sharpe": round(df_pair["sharpe"].mean(), 3),
            "min_sharpe": round(df_pair["sharpe"].min(), 3),
            "avg_dd": round(df_pair["dd"].mean(), 4),
            "worst_dd": round(df_pair["dd"].min(), 4),
            "avg_getiri": round(df_pair["getiri"].mean(), 2),
            "avg_pf": round(df_pair["pf"].mean(), 3),
            "avg_trades": int(df_pair["trades"].mean()),
        })
        print(f"  [{sayac}/{toplam}] sl={sl_mult} trend={trend_ema} mtf={mtf_ema} → "
              f"Sharpe={sonuclar[-1]['avg_sharpe']:.2f} DD={sonuclar[-1]['avg_dd']:.3f}")

    rapor = pd.DataFrame(sonuclar)
    rapor = rapor.sort_values("avg_sharpe", ascending=False)

    print("\n=== Top 10 (avg_sharpe sıralı) ===")
    print(rapor.head(10).to_string(index=False))

    print("\n=== Top 5 (avg_getiri sıralı) ===")
    print(rapor.sort_values("avg_getiri", ascending=False).head(5).to_string(index=False))

    print("\n=== Bottom 5 (en kötü kombinasyonlar) ===")
    print(rapor.tail(5).to_string(index=False))

    # En iyi (Sharpe-Sortino-style: min_sharpe da yüksek olmalı)
    print("\n=== En sağlam (min_sharpe en yüksek — worst-case pair'de bile iyi) ===")
    print(rapor.sort_values("min_sharpe", ascending=False).head(5).to_string(index=False))

    cikti = Path("backtest/results/grid_search.csv")
    rapor.to_csv(cikti, index=False)
    print(f"\nKaydedildi: {cikti}")


if __name__ == "__main__":
    main()
