"""Piyasa Radar CLI — terminalMiraz tarzı çoklu parite tarama.

Kullanım:
    python backtest/radar.py --tf 4h
    python backtest/radar.py --sembol BTCUSDT ETHUSDT SOLUSDT --tf 4h 1d
    python backtest/radar.py --tf 4h --sadece Trade
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz.radar import radar_tara, VARSAYILAN_EVREN


def main() -> None:
    ap = argparse.ArgumentParser(description="Piyasa Radar (terminalMiraz tarzı)")
    ap.add_argument("--sembol", nargs="+", default=None,
                    help=f"varsayılan: {len(VARSAYILAN_EVREN)} coin")
    ap.add_argument("--tf", nargs="+", default=["4h"])
    ap.add_argument("--r", type=float, default=25.0)
    ap.add_argument("--gun", type=int, default=400)
    ap.add_argument("--sadece", default=None,
                    choices=["Trade", "Watch", "Skip", "Elenen"],
                    help="sadece bu kategoriyi göster")
    args = ap.parse_args()

    print(f"\n📡 PİYASA RADAR — {len(args.sembol or VARSAYILAN_EVREN)} parite × "
          f"{len(args.tf)} TF taranıyor...\n")
    rapor = radar_tara(args.sembol, args.tf, r_dolar=args.r, gun=args.gun)
    print(rapor.tablo(sadece=args.sadece))
    if rapor.hatalar:
        print(f"\n⚠️ {len(rapor.hatalar)} hata: " +
              "; ".join(rapor.hatalar[:5]))


if __name__ == "__main__":
    main()
