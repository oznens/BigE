"""TerminalMiraz görsel paneli CLI — @tradermiraz terminal arayüzü kopyası.

Radar taramasını koyu temalı bir komuta panosu (PNG) olarak üretir:
üst komuta metrikleri + CANLI ADAY AKIŞI kartları + SONUÇ BİLDİRİMLERİ.

Kullanım:
    python backtest/terminal.py --semboller BTCUSDT ETHUSDT SOLUSDT --tf 4h
    python backtest/terminal.py --taraf her --genis --cluster
    python backtest/terminal.py --portfoy            # portföyü panoda göster
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz.radar import (radar_tara, VARSAYILAN_EVREN, GENIS_EVREN,
                         TERMINALMIRAZ_TF, RISK_MODLARI)
from miraz.terminal import panel_ciz

KOK = Path(__file__).resolve().parents[1]
CLUSTER_DOSYA = KOK / "cluster.json"
PORTFOY_DOSYA = KOK / "portfoy.json"


def main() -> None:
    ap = argparse.ArgumentParser(description="TerminalMiraz görsel paneli")
    ap.add_argument("--semboller", nargs="+", default=None)
    ap.add_argument("--tf", nargs="+", default=["4h"])
    ap.add_argument("--mtf", action="store_true",
                    help=f"terminalMiraz {len(TERMINALMIRAZ_TF)} TF: {' '.join(TERMINALMIRAZ_TF)}")
    ap.add_argument("--risk-mod", default="guvenli", choices=list(RISK_MODLARI),
                    help="TP uzaklığı: guvenli=1R · dengeli=1.5R · riskli=2R")
    ap.add_argument("--gun", type=int, default=400)
    ap.add_argument("--taraf", default="long", choices=["long", "short", "her"])
    ap.add_argument("--genis", action="store_true",
                    help="GENIS_EVREN (~90 parite) tara")
    ap.add_argument("--mcap", action="store_true",
                    help="mcap evrenini kullan (data/evren.json)")
    ap.add_argument("--hizli", action="store_true",
                    help="göreceli güç indirmesini atla (hız)")
    ap.add_argument("--cluster", action="store_true",
                    help="cluster.json varsa güveni cluster ile düzelt")
    ap.add_argument("--portfoy", action="store_true",
                    help="portfoy.json'ı panoda (aktif/sonuç) göster")
    ap.add_argument("--cikti", default=str(KOK / "data" / "terminal.png"))
    args = ap.parse_args()

    if args.mcap and not args.semboller:
        from miraz.evren import evren_yukle
        semboller = evren_yukle() or VARSAYILAN_EVREN
    else:
        semboller = args.semboller or (GENIS_EVREN if args.genis
                                       else VARSAYILAN_EVREN)
    tflar = TERMINALMIRAZ_TF if args.mtf else args.tf
    rr_hedef = RISK_MODLARI[args.risk_mod]

    cluster_hafiza = None
    if args.cluster and CLUSTER_DOSYA.exists():
        from miraz.cluster import ClusterHafiza
        cluster_hafiza = ClusterHafiza.yukle(CLUSTER_DOSYA)
        print(f"🧬 Cluster hafızası yüklendi ({len(cluster_hafiza.clusterlar)} imza)")

    print(f"🔭 Taranıyor ({args.taraf}): {len(semboller)} parite × "
          f"{len(tflar)} TF ({' '.join(tflar)}) · risk={args.risk_mod} ...")
    rapor = radar_tara(semboller, tflar, gun=args.gun,
                       cluster_hafiza=cluster_hafiza,
                       goreceli=not (args.hizli or args.genis or args.mcap),
                       taraf=args.taraf, rr_hedef=rr_hedef)

    portfoy = None
    if args.portfoy and PORTFOY_DOSYA.exists():
        from miraz.portfoy import Portfoy
        portfoy = Portfoy.yukle(PORTFOY_DOSYA)

    cikti = Path(args.cikti)
    cikti.parent.mkdir(parents=True, exist_ok=True)
    yol = panel_ciz(rapor, portfoy=portfoy, dosya=cikti)
    o = rapor.ozet
    print(f"✅ Panel çizildi → {yol}")
    print(f"   {o['toplam']} tarama → Aday {o['Trade']} · İzle {o['Watch']} · "
          f"Atla {o['Skip']} · Elenen {o['Elenen']}")
    if rapor.hatalar:
        print(f"   ⚠️  {len(rapor.hatalar)} sembol atlandı")


if __name__ == "__main__":
    main()
