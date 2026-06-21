"""TerminalMiraz Web Sunucu CLI — tarayıcıdan açılan canlı pano.

@tradermiraz gibi: terminalMiraz'ı bir sunucuda çalıştır, kendi bilgisayarından
tarayıcıyla http://localhost:PORT adresine girip izle. CMD ekranı değil, gerçek
web uygulaması. Arka planda sürekli tarar; tarayıcı kendini tazeler.

Kullanım:
    # Mcap evreni, 4 TF, çift yön — 8000 portunda
    python backtest/sunucu.py --mcap --mtf --taraf her

    # Özel port / tarama aralığı (sn)
    python backtest/sunucu.py --port 8080 --aralik 120 --mcap --mtf --taraf her

    # Dışarıdan erişim (aynı ağdaki telefondan vs.) — DİKKAT: güvenlik yok
    python backtest/sunucu.py --host 0.0.0.0 --port 8000 --mcap --mtf

Defter → defter.json, paper-trading → portfoy.json. Önceki durumdan sürer.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz.sunucu import Sunucu
from miraz.gozlemci import Defter, DEFTER_DOSYA, PORTFOY_DOSYA
from miraz.portfoy import Portfoy
from miraz.radar import (CEKIRDEK_EVREN, GENIS_EVREN, TERMINALMIRAZ_TF,
                         RISK_MODLARI)

KOK = Path(__file__).resolve().parents[1]
CLUSTER_DOSYA = KOK / "cluster.json"


def _evren(args) -> list:
    if args.semboller:
        return args.semboller
    if args.mcap:
        from miraz.evren import evren_yukle
        liste = evren_yukle()
        if liste:
            return liste
        print("⚠️  data/evren.json yok — önce: python backtest/evren.py --guncelle")
        sys.exit(1)
    return GENIS_EVREN if args.genis else CEKIRDEK_EVREN


def main() -> None:
    ap = argparse.ArgumentParser(description="TerminalMiraz web sunucu")
    ap.add_argument("--semboller", nargs="+", default=None)
    ap.add_argument("--genis", action="store_true")
    ap.add_argument("--mcap", action="store_true",
                    help="mcap evrenini kullan (data/evren.json)")
    ap.add_argument("--tf", nargs="+", default=["4h"])
    ap.add_argument("--mtf", action="store_true",
                    help=f"terminalMiraz 4 TF: {' '.join(TERMINALMIRAZ_TF)}")
    ap.add_argument("--taraf", default="long", choices=["long", "short", "her"])
    ap.add_argument("--risk-mod", default="guvenli", choices=list(RISK_MODLARI))
    ap.add_argument("--r", type=float, default=25.0)
    ap.add_argument("--gun", type=int, default=120)
    ap.add_argument("--max-bekleme", type=int, default=24)
    ap.add_argument("--cluster", action="store_true")
    ap.add_argument("--aralik", type=int, default=180,
                    help="tarama arası saniye (vars. 180)")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="127.0.0.1",
                    help="0.0.0.0 → ağdaki diğer cihazlardan erişim (dikkat)")
    args = ap.parse_args()

    semboller = _evren(args)
    tflar = TERMINALMIRAZ_TF if args.mtf else args.tf
    rr_hedef = RISK_MODLARI[args.risk_mod]

    cluster_hafiza = None
    if args.cluster and CLUSTER_DOSYA.exists():
        from miraz.cluster import ClusterHafiza
        cluster_hafiza = ClusterHafiza.yukle(CLUSTER_DOSYA)

    portfoy = (Portfoy.yukle(PORTFOY_DOSYA) if PORTFOY_DOSYA.exists()
               else Portfoy(r_dolar=args.r))
    defter = Defter.yukle(DEFTER_DOSYA)

    s = Sunucu(
        semboller=semboller, intervallar=tflar, taraf=args.taraf,
        rr_hedef=rr_hedef, cluster_hafiza=cluster_hafiza, r_dolar=args.r,
        gun=args.gun, max_bekleme=args.max_bekleme,
        goreceli=not (args.genis or args.mcap), aralik=args.aralik,
        port=args.port, host=args.host, portfoy=portfoy, defter=defter)
    s.basla()


if __name__ == "__main__":
    main()
