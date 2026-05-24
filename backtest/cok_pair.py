"""15+ pair üzerinde performans testi.

Big E orijinalde 'Three Amigos' (EUR/USD, GBP/USD, AUD/USD) trade ediyordu.
Kripto karşılığı için top 15 altcoin'de stratejinin nasıl çalıştığına bakalım.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from bige.backtest import BacktestKonfig, calistir
from bige.strateji import StratejiParams
from bige.veri import indir_vision_aralik, kaydet, yukle

VERI_KLASOR = Path("data")

# Top 15 altcoin USDT pair'leri (büyük pazar değeri, yeterli geçmiş veri)
PAIRS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT",
    "XRPUSDT", "ADAUSDT", "DOGEUSDT", "AVAXUSDT",
    "DOTUSDT", "LINKUSDT", "MATICUSDT", "LTCUSDT",
    "ATOMUSDT", "NEARUSDT", "ARBUSDT", "OPUSDT",
    "TRXUSDT", "UNIUSDT", "AAVEUSDT", "FILUSDT",
]


def veri_hazirla(sembol: str, aralik: str, baslangic: str) -> pd.DataFrame | None:
    yol = VERI_KLASOR / f"{sembol}_{aralik}.parquet"
    if yol.exists():
        df = yukle(sembol, aralik, VERI_KLASOR)
        if df.index.min() <= pd.Timestamp(baslangic, tz="Europe/Istanbul"):
            return df
    try:
        df = indir_vision_aralik(sembol, aralik, baslangic)
    except Exception as e:
        return None
    if df.empty:
        return None
    kaydet(df, sembol, aralik, VERI_KLASOR)
    return df


def main():
    baslangic = "2022-01-01"
    k = BacktestKonfig(baslangic_bakiyesi=10_000, komisyon_bps=4, slippage_bps=2)
    p = StratejiParams(
        max_candle_age_after_cross=1,
        tdi_angle_min=1.0,
        near_extreme_margin=5.0,
        trend_filtresi_aktif=True,
        trend_ema_period=200,
        sl_mode="atr",
        sl_atr_multiplier=2.0,
        allow_short=False,
        saat_filtresi_aktif=True,  # Big E saatleri (4h'de aktif, 1D'de auto-skip)
    )

    satirlar = []
    for sembol in PAIRS:
        for aralik in ["4h", "1d"]:
            df = veri_hazirla(sembol, aralik, baslangic)
            if df is None or len(df) < 500:
                print(f"  ✗ {sembol} {aralik}: yetersiz veri")
                continue

            bh = (df["close"].iloc[-1] / df["close"].iloc[0] - 1) * 100
            s = calistir(df, p, k)
            ist = s.istatistikler()
            son = float(s.bakiye_serisi.iloc[-1])
            satirlar.append({
                "sembol": sembol.replace("USDT", ""),
                "tf": aralik,
                "trades": ist["trade_sayisi"],
                "wr": ist.get("win_rate", 0),
                "pf": ist.get("profit_factor", 0),
                "sharpe": ist.get("sharpe", 0),
                "dd": ist.get("max_drawdown", 0),
                "getiri_%": round((son / k.baslangic_bakiyesi - 1) * 100, 2),
                "bh_%": round(bh, 2),
                "alpha_%": round((son / k.baslangic_bakiyesi - 1) * 100 - bh, 2),
            })
            print(f"  ✓ {sembol} {aralik}: sharpe={ist['sharpe']:.2f}, getiri=%{satirlar[-1]['getiri_%']:.1f}, B&H=%{bh:.1f}")

    rapor = pd.DataFrame(satirlar)
    print("\n=== 4h sonuçları (alpha = strateji - B&H) ===")
    print(rapor[rapor["tf"] == "4h"].sort_values("sharpe", ascending=False).to_string(index=False))

    print("\n=== 1D sonuçları ===")
    print(rapor[rapor["tf"] == "1d"].sort_values("sharpe", ascending=False).to_string(index=False))

    cikti = Path("backtest/results/cok_pair.csv")
    rapor.to_csv(cikti, index=False)

    print("\n=== Genel istatistikler ===")
    for tf in ["4h", "1d"]:
        alt = rapor[rapor["tf"] == tf]
        if len(alt) == 0:
            continue
        kazanan = (alt["getiri_%"] > 0).sum()
        toplam = len(alt)
        alpha_kazanan = (alt["alpha_%"] > 0).sum()
        print(f"\n{tf}: {toplam} pair test edildi")
        print(f"  Kârlı pair: {kazanan}/{toplam}  ({kazanan/toplam:.0%})")
        print(f"  B&H'ı yenen: {alpha_kazanan}/{toplam}  ({alpha_kazanan/toplam:.0%})")
        print(f"  Ortalama Sharpe:    {alt['sharpe'].mean():.2f}")
        print(f"  Ortalama Max DD:    {alt['dd'].mean():.2%}")
        print(f"  Ortalama getiri:    %{alt['getiri_%'].mean():.1f}")
        print(f"  Ortalama B&H:       %{alt['bh_%'].mean():.1f}")
        print(f"  Ortalama alpha:     %{alt['alpha_%'].mean():.1f}")


if __name__ == "__main__":
    main()
