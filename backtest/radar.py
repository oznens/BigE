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
                         GENIS_EVREN, TERMINALMIRAZ_TF, RISK_MODLARI)
from miraz.cluster import ClusterHafiza

CLUSTER_DOSYA = Path(__file__).resolve().parents[1] / "cluster.json"


def main() -> None:
    ap = argparse.ArgumentParser(description="Piyasa Radar (terminalMiraz tarzı)")
    ap.add_argument("--sembol", nargs="+", default=None,
                    help=f"varsayılan: çekirdek {len(CEKIRDEK_EVREN)} coin")
    ap.add_argument("--genis", action="store_true",
                    help=f"geniş evren ({len(GENIS_EVREN)} parite) tara")
    ap.add_argument("--mcap", action="store_true",
                    help="mcap evrenini kullan (data/evren.json — bkz. evren.py)")
    ap.add_argument("--tf", nargs="+", default=["4h"])
    ap.add_argument("--mtf", action="store_true",
                    help=f"terminalMiraz {len(TERMINALMIRAZ_TF)} zaman dilimi: {' '.join(TERMINALMIRAZ_TF)}")
    ap.add_argument("--risk-mod", default="guvenli",
                    choices=list(RISK_MODLARI),
                    help="TP uzaklığı: guvenli=1R · dengeli=1.5R · riskli=2R")
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

    if args.mcap and not args.sembol:
        from miraz.evren import evren_yukle
        mcap_liste = evren_yukle()
        if not mcap_liste:
            print("⚠️  data/evren.json yok — önce: python backtest/evren.py --guncelle")
            return
        semboller = mcap_liste
    else:
        semboller = args.sembol or (GENIS_EVREN if args.genis else CEKIRDEK_EVREN)
    tflar = TERMINALMIRAZ_TF if args.mtf else args.tf
    rr_hedef = RISK_MODLARI[args.risk_mod]
    # Geniş/mcap evrende göreceli güç varsayılan olarak atlanır (hız)
    goreceli = not (args.hizli or args.genis or args.mcap)

    hafiza = None
    if args.cluster and CLUSTER_DOSYA.exists():
        hafiza = ClusterHafiza.yukle(CLUSTER_DOSYA)
        print(f"🧬 Cluster hafızası yüklendi ({hafiza.toplam_setup} setup).")
    elif args.cluster:
        print("⚠️  cluster.json yok — önce: python backtest/cluster.py --ogren")

    print(f"\n📡 PİYASA RADAR — {len(semboller)} parite × "
          f"{len(tflar)} TF ({' '.join(tflar)}) · risk={args.risk_mod} "
          f"({rr_hedef:g}R) taranıyor...\n")
    rapor = radar_tara(semboller, tflar, r_dolar=args.r, gun=args.gun,
                       cluster_hafiza=hafiza, goreceli=goreceli,
                       taraf=args.taraf, rr_hedef=rr_hedef)
    print(rapor.tablo(sadece=args.sadece))
    if rapor.hatalar:
        print(f"\n⚠️ {len(rapor.hatalar)} hata: " +
              "; ".join(rapor.hatalar[:5]))


if __name__ == "__main__":
    main()
