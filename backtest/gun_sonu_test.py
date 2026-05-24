"""Big E'nin "17:00'da tüm 4h trade'leri kapat" kuralının etkisi.

Orijinalde forex broker rollover problemleri için yapılıyordu. Kripto 24/7
olduğu için bunun mantığı zayıf; yine de test edelim.
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
        ("01_hold_pozisyonu",  dict(gun_sonu_kapat_saat=None)),
        ("02_kapa_15",         dict(gun_sonu_kapat_saat=15)),  # 4h candle bitişi
        ("03_kapa_19",         dict(gun_sonu_kapat_saat=19)),
        ("04_kapa_23",         dict(gun_sonu_kapat_saat=23)),
        ("05_kapa_03",         dict(gun_sonu_kapat_saat=3)),   # tam gece yarısı UTC
    ]

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
                saat_filtresi_aktif=True,  # default: Big E saatleri
                **extra,
            )
            s = calistir(df, p, k)
            ist = s.istatistikler()
            son = float(s.bakiye_serisi.iloc[-1])
            # Gun_sonu vs tdi_exit dağılımı
            gun_sonu_n = sum(1 for t in s.trades if t.sebep == "gun_sonu")
            tdi_exit_n = sum(1 for t in s.trades if t.sebep == "tdi_exit")
            sl_n = sum(1 for t in s.trades if t.sebep == "stop_loss")
            gun_sonu_pnl = sum(t.pnl_net for t in s.trades if t.sebep == "gun_sonu")

            satirlar.append({
                "sembol": sembol,
                "mod": etiket,
                "trades": ist["trade_sayisi"],
                "gun_sonu_n": gun_sonu_n,
                "tdi_n": tdi_exit_n,
                "sl_n": sl_n,
                "wr": ist.get("win_rate", 0),
                "pf": ist.get("profit_factor", 0),
                "sharpe": ist.get("sharpe", 0),
                "dd": ist.get("max_drawdown", 0),
                "getiri_%": round((son / k.baslangic_bakiyesi - 1) * 100, 2),
                "gun_sonu_pnl": round(gun_sonu_pnl, 2),
            })

    rapor = pd.DataFrame(satirlar)
    print("\n=== Gün-sonu kapatma testi (4h) ===")
    print(rapor.to_string(index=False))

    cikti = Path("backtest/results/gun_sonu_test.csv")
    rapor.to_csv(cikti, index=False)

    print("\n=== Ortalama (4 pair) ===")
    print(rapor.groupby("mod")[["trades", "wr", "pf", "sharpe", "dd", "getiri_%"]].mean().round(3).to_string())


if __name__ == "__main__":
    main()
