"""En iyi konfigürasyonu birden fazla pair ve timeframe'de test et.

Cross-validation amaçlı: BTC'de iyi olan ETH/SOL/ADA'da da çalışıyor mu?
1D timeframe'de daha mı iyi?
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from bige.backtest import BacktestKonfig, calistir
from bige.strateji import StratejiParams
from bige.veri import indir_vision_aralik, kaydet, yukle

VERI_KLASOR = Path("data")


def veri_hazirla(sembol: str, aralik: str, baslangic: str) -> pd.DataFrame:
    yol = VERI_KLASOR / f"{sembol}_{aralik}.parquet"
    if yol.exists():
        df = yukle(sembol, aralik, VERI_KLASOR)
        if df.index.min() <= pd.Timestamp(baslangic, tz="Europe/Istanbul"):
            return df
    df = indir_vision_aralik(sembol, aralik, baslangic)
    kaydet(df, sembol, aralik, VERI_KLASOR)
    return df


def main():
    baslangic = "2022-01-01"
    semboller = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
    aralıklar = ["4h", "1d"]
    k = BacktestKonfig(baslangic_bakiyesi=10_000, komisyon_bps=4, slippage_bps=2)

    # En iyi config (önceki karşılaştırmadan)
    p_long_only = StratejiParams(
        max_candle_age_after_cross=1,
        tdi_angle_min=1.0,
        near_extreme_margin=5.0,
        trend_filtresi_aktif=True,
        trend_ema_period=200,
        sl_mode="atr",
        sl_atr_multiplier=2.0,
        allow_short=False,
    )
    p_long_short = StratejiParams(
        max_candle_age_after_cross=1,
        tdi_angle_min=1.0,
        near_extreme_margin=5.0,
        trend_filtresi_aktif=True,
        trend_ema_period=200,
        sl_mode="atr",
        sl_atr_multiplier=2.0,
    )

    satirlar = []
    for sembol in semboller:
        for aralik in aralıklar:
            try:
                df = veri_hazirla(sembol, aralik, baslangic)
            except Exception as e:
                print(f"  {sembol} {aralik}: veri çekilemedi ({e})")
                continue
            if len(df) < 500:
                continue
            bh = (df["close"].iloc[-1] / df["close"].iloc[0] - 1) * 100

            for etiket, p in [("long_only", p_long_only), ("long_short", p_long_short)]:
                s = calistir(df, p, k)
                ist = s.istatistikler()
                son = float(s.bakiye_serisi.iloc[-1])
                satirlar.append({
                    "sembol": sembol,
                    "aralik": aralik,
                    "mod": etiket,
                    "trades": ist["trade_sayisi"],
                    "wr": ist.get("win_rate", 0),
                    "pf": ist.get("profit_factor", 0),
                    "dd": ist.get("max_drawdown", 0),
                    "sharpe": ist.get("sharpe", 0),
                    "getiri_%": round((son / k.baslangic_bakiyesi - 1) * 100, 2),
                    "bh_%": round(bh, 2),
                })

    rapor = pd.DataFrame(satirlar)
    print("\n=== Çoklu pair / timeframe sonuçları ===")
    print(rapor.to_string(index=False))

    cikti = Path("backtest/results/coklu_pair.csv")
    rapor.to_csv(cikti, index=False)
    print(f"\nKaydedildi: {cikti}")

    # Özet: hangi mod ortalama daha iyi?
    print("\n=== Mod bazında ortalama ===")
    print(rapor.groupby("mod")[["getiri_%", "sharpe", "dd", "pf"]].mean().round(3).to_string())


if __name__ == "__main__":
    main()
