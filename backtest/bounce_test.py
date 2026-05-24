"""Bounce trade'lerin etkisini ölç: aktif vs pasif karşılaştırma."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from bige.backtest import BacktestKonfig, calistir
from bige.strateji import StratejiParams
from bige.veri import yukle


def main():
    k = BacktestKonfig(baslangic_bakiyesi=10_000, komisyon_bps=4, slippage_bps=2)
    semboller_tf = [
        ("BTCUSDT", "4h"), ("BTCUSDT", "1d"),
        ("ETHUSDT", "4h"), ("ETHUSDT", "1d"),
        ("SOLUSDT", "4h"), ("SOLUSDT", "1d"),
        ("BNBUSDT", "4h"), ("BNBUSDT", "1d"),
    ]

    def yap_param(bounce: bool, sıkı: bool = False) -> StratejiParams:
        return StratejiParams(
            max_candle_age_after_cross=1,
            tdi_angle_min=1.0,
            near_extreme_margin=5.0,
            trend_filtresi_aktif=True,
            trend_ema_period=200,
            sl_mode="atr",
            sl_atr_multiplier=2.0,
            allow_short=False,
            bounce_aktif=bounce,
            # Sıkı: yaklaşma daha dar, daha taze, açı şartı daha sert
            bounce_yaklasma_esigi=1.5 if sıkı else 3.0,
            bounce_uzaklik_geri=5 if sıkı else 10,
            bounce_min_son_cross_yas=5 if sıkı else 3,
        )

    satirlar = []
    for sembol, aralik in semboller_tf:
        try:
            df = yukle(sembol, aralik)
        except Exception as e:
            print(f"  {sembol} {aralik}: {e}")
            continue
        bh = (df["close"].iloc[-1] / df["close"].iloc[0] - 1) * 100

        for etiket, p in [("01_no_bounce",   yap_param(False)),
                          ("02_loose_bounce", yap_param(True, sıkı=False)),
                          ("03_tight_bounce", yap_param(True, sıkı=True))]:
            s = calistir(df, p, k)
            ist = s.istatistikler()
            son = float(s.bakiye_serisi.iloc[-1])
            # Bounce vs cross sebepli dağılımı
            cross_n = sum(1 for t in s.trades if t.giris_sebebi == "cross")
            bounce_n = sum(1 for t in s.trades if t.giris_sebebi == "bounce")
            cross_pnl = sum(t.pnl_net for t in s.trades if t.giris_sebebi == "cross")
            bounce_pnl = sum(t.pnl_net for t in s.trades if t.giris_sebebi == "bounce")

            satirlar.append({
                "sembol": sembol,
                "tf": aralik,
                "mod": etiket,
                "trades": ist["trade_sayisi"],
                "cross_n": cross_n,
                "bounce_n": bounce_n,
                "wr": ist.get("win_rate", 0),
                "pf": ist.get("profit_factor", 0),
                "sharpe": ist.get("sharpe", 0),
                "dd": ist.get("max_drawdown", 0),
                "getiri_%": round((son / k.baslangic_bakiyesi - 1) * 100, 2),
                "cross_pnl": round(cross_pnl, 2),
                "bounce_pnl": round(bounce_pnl, 2),
                "bh_%": round(bh, 2),
            })

    rapor = pd.DataFrame(satirlar)
    print("\n=== Bounce trade etkisi ===")
    print(rapor.to_string(index=False))

    cikti = Path("backtest/results/bounce_test.csv")
    rapor.to_csv(cikti, index=False)

    # Mod bazında özet
    print("\n=== Ortalama (tüm pair/TF) ===")
    print(rapor.groupby("mod")[["getiri_%", "sharpe", "dd", "pf", "trades"]].mean().round(3).to_string())

    # Sadece bounce trade'lerin tek başına performansı
    print("\n=== Bounce trade'lerin tek başına PnL'i ===")
    bounce_df = rapor[rapor["mod"] == "cross+bounce"][["sembol", "tf", "bounce_n", "bounce_pnl", "cross_pnl"]]
    print(bounce_df.to_string(index=False))


if __name__ == "__main__":
    main()
