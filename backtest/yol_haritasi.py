"""Çoklu-bölge yol haritası (TAO tarzı HTF planı) üretir.

Kullanım:
    python backtest/yol_haritasi.py --sembol BTCUSDT --tf 1d
    python backtest/yol_haritasi.py --sembol ETHUSDT --tf 4h --grafik
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz import veri
from miraz import yol_haritasi as yh


def main() -> None:
    ap = argparse.ArgumentParser(description="Çoklu-bölge yol haritası")
    ap.add_argument("--sembol", nargs="+", default=["BTCUSDT"])
    ap.add_argument("--tf", nargs="+", default=["1d"])
    ap.add_argument("--pivot-n", type=int, default=5)
    ap.add_argument("--min-guc", type=float, default=55.0)
    ap.add_argument("--mesafe-limit", type=float, default=30.0)
    ap.add_argument("--max-yon", type=int, default=4)
    ap.add_argument("--grafik", action="store_true")
    ap.add_argument("--son-n", type=int, default=300)
    ap.add_argument("--gun", type=int, default=900)
    args = ap.parse_args()

    _ad = {"BTCUSDT": "Bitcoin / TetherUS", "ETHUSDT": "Ethereum / TetherUS",
           "SOLUSDT": "Solana / TetherUS"}
    _tf = {"1h": "1sa", "4h": "4sa", "1d": "1G", "15m": "15dk"}

    for sembol in args.sembol:
        for tf in args.tf:
            try:
                df = veri.indir(sembol, tf, gun=args.gun)
            except Exception as e:
                print(f"  HATA {sembol}/{tf}: {e}")
                continue
            harita = yh.yol_haritasi_uret(
                df, symbol=sembol, interval=tf, n=args.pivot_n,
                min_guc=args.min_guc, mesafe_limit=args.mesafe_limit,
                max_yon=args.max_yon)
            yh.yazdir(harita)

            if args.grafik:
                from miraz import grafik
                cikti = Path("data/grafikler") / f"{sembol}_{tf}_yolharitasi.png"
                yol = grafik.yol_haritasi_ciz(
                    df, harita, dosya=cikti, son_n=args.son_n,
                    symbol=_ad.get(sembol, f"{sembol[:-4]} / TetherUS"),
                    interval=_tf.get(tf, tf), borsa="Binance",
                    baslik="miraz otomatik yol haritası")
                print(f"✅ Grafik: {yol}")


if __name__ == "__main__":
    main()
