"""Big E'nin orijinal forex pair'leri üzerinde strateji testi.

Three Amigos (EUR/USD, GBP/USD, AUD/USD) + opsiyonel JPY crosses.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from bige.backtest import BacktestKonfig, calistir
from bige.strateji import StratejiParams
from bige.veri_forex import indir_yfinance, kaydet, yukle

VERI_KLASOR = Path("data")


def veri_hazirla(pair: str, aralik: str) -> pd.DataFrame | None:
    yol = VERI_KLASOR / f"forex_{pair}_{aralik}.parquet"
    if yol.exists():
        return yukle(pair, aralik, VERI_KLASOR)
    try:
        df = indir_yfinance(pair, target_aralik=aralik)
    except Exception as e:
        print(f"    ✗ {pair} {aralik}: {e}")
        return None
    if df.empty:
        return None
    kaydet(df, pair, aralik, VERI_KLASOR)
    return df


def main():
    k = BacktestKonfig(baslangic_bakiyesi=10_000, komisyon_bps=2, slippage_bps=1)
    # Forex spread/komisyon kriptodan daha düşük (büyük broker'da ~1-2 bps)

    pairs = ["EURUSD", "GBPUSD", "AUDUSD"]  # Three Amigos
    aralıklar = ["4h", "1d"]

    # 1) Big E saatleri AÇIK (default crypto config)
    p_default = StratejiParams(
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

    # 2) Big E'nin tam orijinaline daha yakın: long+short, daha esnek
    p_big_e = StratejiParams(
        max_candle_age_after_cross=2,    # Big E "candle 1 veya 2"
        tdi_angle_min=0.5,
        near_extreme_margin=5.0,
        trend_filtresi_aktif=False,       # Big E trend filtresi yok
        sl_mode="swing",                  # Big E 2 mum geri swing SL
        sl_lookback_candles=2,
        allow_short=True,                 # Big E hem long hem short
        saat_filtresi_aktif=True,
        gun_sonu_kapat_saat=17,           # Big E 17:00'da kapatıyor
    )

    konfigler = [("default_crypto", p_default), ("big_e_orijinal", p_big_e)]
    satirlar = []

    for pair in pairs:
        for aralik in aralıklar:
            df = veri_hazirla(pair, aralik)
            if df is None or len(df) < 500:
                print(f"  ✗ {pair} {aralik}: yetersiz veri")
                continue
            print(f"  ✓ {pair} {aralik}: {len(df)} mum, {df.index.min().date()} → {df.index.max().date()}")
            bh = (df["close"].iloc[-1] / df["close"].iloc[0] - 1) * 100

            for etiket, p in konfigler:
                s = calistir(df, p, k)
                ist = s.istatistikler()
                if ist["trade_sayisi"] == 0:
                    continue
                son = float(s.bakiye_serisi.iloc[-1])
                satirlar.append({
                    "pair": pair,
                    "tf": aralik,
                    "config": etiket,
                    "trades": ist["trade_sayisi"],
                    "wr": ist.get("win_rate", 0),
                    "pf": ist.get("profit_factor", 0),
                    "sharpe": ist.get("sharpe", 0),
                    "dd": ist.get("max_drawdown", 0),
                    "getiri_%": round((son / k.baslangic_bakiyesi - 1) * 100, 2),
                    "bh_%": round(bh, 2),
                    "alpha_%": round((son / k.baslangic_bakiyesi - 1) * 100 - bh, 2),
                })

    rapor = pd.DataFrame(satirlar)
    print("\n=== Forex: Three Amigos sonuçları ===")
    print(rapor.to_string(index=False))

    cikti = Path("backtest/results/forex_test.csv")
    rapor.to_csv(cikti, index=False)

    print("\n=== Config bazında ortalama ===")
    print(rapor.groupby("config")[["wr", "pf", "sharpe", "dd", "getiri_%", "alpha_%"]].mean().round(3).to_string())


if __name__ == "__main__":
    main()
