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

from miraz.radar import (radar_tara, VARSAYILAN_EVREN, CEKIRDEK_EVREN,
                         GENIS_EVREN)
from miraz.cluster import ClusterHafiza

CLUSTER_DOSYA = Path(__file__).resolve().parents[1] / "cluster.json"


def main() -> None:
    ap = argparse.ArgumentParser(description="Piyasa Radar (terminalMiraz tarzı)")
    ap.add_argument("--sembol", nargs="+", default=None,
                    help=f"varsayılan: çekirdek {len(CEKIRDEK_EVREN)} coin")
    ap.add_argument("--genis", action="store_true",
                    help=f"geniş evren ({len(GENIS_EVREN)} parite) tara")
    ap.add_argument("--tf", nargs="+", default=["4h"])
    ap.add_argument("--r", type=float, default=25.0)
    ap.add_argument("--gun", type=int, default=400)
    ap.add_argument("--sadece", default=None,
                    choices=["Trade", "Watch", "Skip", "Elenen"],
                    help="sadece bu kategoriyi göster")
    ap.add_argument("--cluster", action="store_true",
                    help="cluster.json hafızasını güvene uygula")
    ap.add_argument("--hizli", action="store_true",
                    help="göreceli güç indirmesini atla (geniş tarama için hız)")
    ap.add_argument("--taraf", default="long",
                    choices=["long", "short", "her"],
                    help="long (varsayılan) / short / her (ikisi de)")
    args = ap.parse_args()

    semboller = args.sembol or (GENIS_EVREN if args.genis else CEKIRDEK_EVREN)
    # Geniş evrende göreceli güç varsayılan olarak atlanır (hız)
    goreceli = not (args.hizli or args.genis)

    hafiza = None
    if args.cluster and CLUSTER_DOSYA.exists():
        hafiza = ClusterHafiza.yukle(CLUSTER_DOSYA)
        print(f"🧬 Cluster hafızası yüklendi ({hafiza.toplam_setup} setup).")
    elif args.cluster:
        print("⚠️  cluster.json yok — önce: python backtest/cluster.py --ogren")

    print(f"\n📡 PİYASA RADAR — {len(semboller)} parite × "
          f"{len(args.tf)} TF taranıyor...\n")
    rapor = radar_tara(semboller, args.tf, r_dolar=args.r, gun=args.gun,
                       cluster_hafiza=hafiza, goreceli=goreceli,
                       taraf=args.taraf)
    print(rapor.tablo(sadece=args.sadece))
    if rapor.hatalar:
        print(f"\n⚠️ {len(rapor.hatalar)} hata: " +
              "; ".join(rapor.hatalar[:5]))


if __name__ == "__main__":
    main()
