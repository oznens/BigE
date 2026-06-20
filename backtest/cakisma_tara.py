"""Harmonik + renkli kutu çakışma (confluence) tarayıcı.

Bir harmonik pattern'in D noktası güçlü bir destek/direnç kutusuna denk
geliyorsa = yüksek kaliteli setup. tradermiraz mantığının özü.

Kullanım:
    python backtest/cakisma_tara.py
    python backtest/cakisma_tara.py --sembol ETHUSDT --tf 4h --sadece-cakisan
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz import cakisma as ck
from miraz import veri


def main() -> None:
    ap = argparse.ArgumentParser(description="Harmonik + kutu çakışma tarayıcı")
    ap.add_argument("--sembol", nargs="+",
                    default=["BTCUSDT", "ETHUSDT", "SOLUSDT"])
    ap.add_argument("--tf", nargs="+", default=["1h", "4h"])
    ap.add_argument("--pivot-n", type=int, default=5)
    ap.add_argument("--kalite", type=float, default=40.0)
    ap.add_argument("--tolerans", type=float, default=0.015)
    ap.add_argument("--min-dokunus", type=int, default=2)
    ap.add_argument("--sadece-cakisan", action="store_true",
                    help="Sadece kutuyla çakışan setup'ları göster")
    ap.add_argument("--gun", type=int, default=500)
    args = ap.parse_args()

    toplam_cakisma = 0
    for sembol in args.sembol:
        for tf in args.tf:
            try:
                df = veri.indir(sembol, tf, gun=args.gun)
            except Exception as e:
                print(f"  HATA {sembol}/{tf}: {e}")
                continue
            cakismalar = ck.cakismalari_bul(
                df, pivot_n=args.pivot_n, min_kalite=args.kalite,
                tolerans=args.tolerans, min_dokunus=args.min_dokunus,
                sadece_cakisan=args.sadece_cakisan,
            )
            ck.ozet_yazdir(sembol, tf, cakismalar)
            toplam_cakisma += sum(1 for c in cakismalar if c.cakisma_var)

    print(f"\n{'='*78}")
    print(f"⭐ Toplam çakışan (confluence) setup: {toplam_cakisma}")


if __name__ == "__main__":
    main()
