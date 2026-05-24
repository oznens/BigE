"""Birden fazla konfigürasyonu yan yana koş, sonuçları tabloda göster.

İyileştirme döngüsü için: her değişiklikten sonra bunu çalıştırıp baseline'a
göre fark görüyoruz.
"""
from __future__ import annotations

import json
from dataclasses import asdict, replace
from pathlib import Path

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


def tek_kosu(df: pd.DataFrame, p: StratejiParams, k: BacktestKonfig, etiket: str) -> dict:
    sonuc = calistir(df, p, k)
    ist = sonuc.istatistikler()
    son_bakiye = float(sonuc.bakiye_serisi.iloc[-1])
    ist["etiket"] = etiket
    ist["son_bakiye"] = round(son_bakiye, 2)
    ist["getiri_pct"] = round((son_bakiye / k.baslangic_bakiyesi - 1) * 100, 2)
    return ist


def main():
    sembol = "BTCUSDT"
    aralik = "4h"
    baslangic = "2022-01-01"

    print(f"Veri: {sembol} {aralik} {baslangic}+")
    df = veri_hazirla(sembol, aralik, baslangic)
    print(f"  {len(df)} mum")

    k = BacktestKonfig(baslangic_bakiyesi=10_000, komisyon_bps=4, slippage_bps=2)

    # Buy & hold benchmark
    bh = (df["close"].iloc[-1] / df["close"].iloc[0] - 1) * 100

    konfigler = [
        ("01_baseline_eski", StratejiParams(
            max_candle_age_after_cross=2,
            tdi_angle_min=0.5,
            min_ha_body_atr_ratio=0.15,
            near_extreme_margin=3.0,
            trend_filtresi_aktif=False,
            sl_mode="swing",
            sl_lookback_candles=2,
        )),
        ("02_sl_atr_x2", StratejiParams(
            max_candle_age_after_cross=2,
            tdi_angle_min=0.5,
            min_ha_body_atr_ratio=0.15,
            near_extreme_margin=3.0,
            trend_filtresi_aktif=False,
            sl_mode="atr",
            sl_atr_multiplier=2.0,
        )),
        ("03_sl_atr_x3", StratejiParams(
            trend_filtresi_aktif=False,
            sl_mode="atr",
            sl_atr_multiplier=3.0,
        )),
        ("04_siki_cross_ang_atr", StratejiParams(
            max_candle_age_after_cross=1,
            tdi_angle_min=1.0,
            near_extreme_margin=5.0,
            trend_filtresi_aktif=False,
            sl_mode="atr",
            sl_atr_multiplier=2.0,
        )),
        ("05_trend_ema50_+atr", StratejiParams(
            max_candle_age_after_cross=1,
            tdi_angle_min=1.0,
            near_extreme_margin=5.0,
            trend_filtresi_aktif=True,
            trend_ema_period=50,
            sl_mode="atr",
            sl_atr_multiplier=2.0,
        )),
        ("06_trend_ema200_+atr", StratejiParams(
            max_candle_age_after_cross=1,
            tdi_angle_min=1.0,
            near_extreme_margin=5.0,
            trend_filtresi_aktif=True,
            trend_ema_period=200,
            sl_mode="atr",
            sl_atr_multiplier=2.0,
        )),
        ("07_long_only_trend200", StratejiParams(
            max_candle_age_after_cross=1,
            tdi_angle_min=1.0,
            near_extreme_margin=5.0,
            trend_filtresi_aktif=True,
            trend_ema_period=200,
            sl_mode="atr",
            sl_atr_multiplier=2.0,
            allow_short=False,
        )),
        ("08_hybrid_sl_trend200", StratejiParams(
            max_candle_age_after_cross=1,
            tdi_angle_min=1.0,
            near_extreme_margin=5.0,
            trend_filtresi_aktif=True,
            trend_ema_period=200,
            sl_mode="hybrid",
            sl_atr_multiplier=2.0,
            sl_lookback_candles=3,
        )),
    ]

    rapor = []
    for etiket, p in konfigler:
        ist = tek_kosu(df, p, k, etiket)
        rapor.append(ist)
        print(f"\n--- {etiket} ---")
        print(f"  trades={ist['trade_sayisi']}, wr={ist['win_rate']:.3f}, "
              f"pf={ist['profit_factor']}, pnl={ist['toplam_pnl']}, "
              f"dd={ist['max_drawdown']:.3f}, getiri=%{ist['getiri_pct']}")

    print("\n" + "=" * 80)
    print(f"Buy & hold (referans): %{bh:.2f}")
    print("=" * 80)

    # Özet tablo
    rapor_df = pd.DataFrame(rapor).set_index("etiket")
    kolonlar = ["trade_sayisi", "win_rate", "profit_factor",
                "toplam_pnl", "max_drawdown", "getiri_pct"]
    rapor_df = rapor_df[kolonlar]
    print("\n=== Karşılaştırma tablosu ===")
    print(rapor_df.to_string())

    cikti = Path("backtest/results/karsilastirma.csv")
    cikti.parent.mkdir(parents=True, exist_ok=True)
    rapor_df.to_csv(cikti)
    print(f"\nKaydedildi: {cikti}")


if __name__ == "__main__":
    main()
