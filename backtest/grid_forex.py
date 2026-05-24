"""Big E'nin forex pair'leri (Three Amigos) üzerinde parametre grid search.

EUR/USD, GBP/USD, AUD/USD ortalaması üzerinden en iyi kombinasyonu bul.
4h (2.7 yıl yfinance verisi) ve 1D (20+ yıl) ayrı ayrı.
"""
from __future__ import annotations

import itertools
from pathlib import Path

import pandas as pd

from bige.backtest import BacktestKonfig, calistir
from bige.indikatorler import mtf_trend_ekle
from bige.strateji import StratejiParams
from bige.veri_forex import indir_yfinance, kaydet, yukle

VERI_KLASOR = Path("data")
PAIRS = ["EURUSD", "GBPUSD", "AUDUSD"]


def veri_hazirla(pair: str, aralik: str) -> pd.DataFrame | None:
    yol = VERI_KLASOR / f"forex_{pair}_{aralik}.parquet"
    if yol.exists():
        return yukle(pair, aralik, VERI_KLASOR)
    df = indir_yfinance(pair, target_aralik=aralik)
    if df.empty:
        return None
    kaydet(df, pair, aralik, VERI_KLASOR)
    return df


def grid_for_tf(aralik: str, k: BacktestKonfig) -> pd.DataFrame:
    # Veriyi bir kez yükle
    data: dict[str, tuple[pd.DataFrame, pd.DataFrame | None]] = {}
    for pair in PAIRS:
        df_main = veri_hazirla(pair, aralik)
        if df_main is None or len(df_main) < 300:
            print(f"  ✗ {pair} {aralik}: yetersiz veri")
            continue
        # MTF için 1D verisi (4h backtest'i için)
        df_1d = None
        if aralik == "4h":
            df_1d = veri_hazirla(pair, "1d")
        data[pair] = (df_main, df_1d)

    if not data:
        return pd.DataFrame()

    # Grid
    sl_mults = [1.5, 2.0, 2.5, 3.0]
    trend_emas = [50, 100, 200]
    mtf_emas = [20, 50, 100]

    sonuclar = []
    toplam = len(sl_mults) * len(trend_emas) * len(mtf_emas)
    sayac = 0

    for sl_mult, trend_ema, mtf_ema in itertools.product(sl_mults, trend_emas, mtf_emas):
        sayac += 1
        # 1D'de MTF anlamsız (zaten en yüksek TF), bir kez döner
        if aralik == "1d" and mtf_ema != mtf_emas[0]:
            continue

        p = StratejiParams(
            max_candle_age_after_cross=1,
            tdi_angle_min=1.0,
            near_extreme_margin=5.0,
            trend_filtresi_aktif=True,
            trend_ema_period=trend_ema,
            sl_mode="atr",
            sl_atr_multiplier=sl_mult,
            allow_short=False,
            saat_filtresi_aktif=(aralik == "4h"),
            mtf_onay_filtresi=(aralik == "4h"),
        )

        per_pair = []
        for pair, (df_main, df_1d) in data.items():
            df = df_main
            if aralik == "4h" and df_1d is not None:
                df = mtf_trend_ekle(df_main, df_1d, ema_p=mtf_ema)
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
                "wr": ist.get("win_rate", 0),
            })

        if not per_pair:
            continue
        df_pair = pd.DataFrame(per_pair)
        sonuclar.append({
            "sl_mult": sl_mult,
            "trend_ema": trend_ema,
            "mtf_ema": mtf_ema if aralik == "4h" else "-",
            "avg_sharpe": round(df_pair["sharpe"].mean(), 3),
            "min_sharpe": round(df_pair["sharpe"].min(), 3),
            "avg_dd": round(df_pair["dd"].mean(), 4),
            "avg_getiri": round(df_pair["getiri"].mean(), 2),
            "avg_pf": round(df_pair["pf"].mean(), 3),
            "avg_wr": round(df_pair["wr"].mean(), 3),
            "avg_trades": int(df_pair["trades"].mean()),
        })

    return pd.DataFrame(sonuclar)


def main():
    k = BacktestKonfig(baslangic_bakiyesi=10_000, komisyon_bps=2, slippage_bps=1)

    for aralik in ["4h", "1d"]:
        print(f"\n=== Grid search: {aralik} (3 Big E pair: EUR/USD, GBP/USD, AUD/USD) ===")
        rapor = grid_for_tf(aralik, k)
        if rapor.empty:
            print("  Sonuç yok")
            continue
        rapor = rapor.sort_values("avg_sharpe", ascending=False)
        print(f"\nTop 10 (avg_sharpe sıralı):")
        print(rapor.head(10).to_string(index=False))
        print(f"\nEn sağlam (min_sharpe en yüksek):")
        print(rapor.sort_values("min_sharpe", ascending=False).head(5).to_string(index=False))
        print(f"\nEn yüksek getiri:")
        print(rapor.sort_values("avg_getiri", ascending=False).head(5).to_string(index=False))

        cikti = Path(f"backtest/results/grid_forex_{aralik}.csv")
        rapor.to_csv(cikti, index=False)
        print(f"\nKaydedildi: {cikti}")


if __name__ == "__main__":
    main()
