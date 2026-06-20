"""Renkli kutu tarayıcıyı canlı veride çalıştırır.

Kullanım:
    python backtest/kutu_tara.py
    python backtest/kutu_tara.py --sembol ETHUSDT --tf 4h --tolerans 0.02
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz import kutular as kt
from miraz import veri


def main() -> None:
    ap = argparse.ArgumentParser(description="Renkli kutu (destek/direnç) tarayıcı")
    ap.add_argument("--sembol", nargs="+",
                    default=["BTCUSDT", "ETHUSDT", "SOLUSDT"])
    ap.add_argument("--tf", nargs="+", default=["4h"])
    ap.add_argument("--pivot-n", type=int, default=5)
    ap.add_argument("--tolerans", type=float, default=0.015)
    ap.add_argument("--min-dokunus", type=int, default=2)
    ap.add_argument("--min-guc", type=float, default=0.0)
    ap.add_argument("--mesafe-limit", type=float, default=35.0,
                    help="Fiyattan bu %%'den uzak bölgeleri ele")
    ap.add_argument("--max-kutu", type=int, default=12,
                    help="Sembol başına en fazla kaç kutu göster")
    ap.add_argument("--gun", type=int, default=500)
    args = ap.parse_args()

    for sembol in args.sembol:
        for tf in args.tf:
            try:
                df = veri.indir(sembol, tf, gun=args.gun)
            except Exception as e:
                print(f"  HATA {sembol}/{tf}: {e}")
                continue
            kutlar = kt.kutulari_bul(
                df, n=args.pivot_n, tolerans=args.tolerans,
                min_dokunus=args.min_dokunus, min_guc=args.min_guc,
                mesafe_limit=args.mesafe_limit, max_kutu=args.max_kutu,
            )
            kt.ozet_yazdir(f"{sembol} / {tf}", df, kutlar)


if __name__ == "__main__":
    main()
