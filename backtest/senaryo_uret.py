"""Güncel piyasa için Miraz tarzı senaryo planı üretir.

Kullanım:
    python backtest/senaryo_uret.py --sembol ETHUSDT --tf 4h
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz import senaryo as sn
from miraz import veri


def main() -> None:
    ap = argparse.ArgumentParser(description="Senaryo planı üretici")
    ap.add_argument("--sembol", nargs="+", default=["ETHUSDT"])
    ap.add_argument("--tf", nargs="+", default=["4h"])
    ap.add_argument("--pivot-n", type=int, default=5)
    ap.add_argument("--tolerans", type=float, default=0.015)
    ap.add_argument("--min-guc", type=float, default=50.0)
    ap.add_argument("--vade", default="Kısa vade",
                    help="Yorumda kullanılacak vade (ör. 'Orta vade')")
    ap.add_argument("--grafik", action="store_true",
                    help="Senaryoyu PNG grafiğe de çiz")
    ap.add_argument("--son-n", type=int, default=260,
                    help="Grafikte gösterilecek mum sayısı")
    ap.add_argument("--gun", type=int, default=500)
    ap.add_argument("--r", type=float, default=0.0,
                    help="1R dolar tutarı (>0 ise risk planı eklenir, ör. 25)")
    ap.add_argument("--kademe", type=int, default=0,
                    help="kademeli giriş sayısı (>0 ve --r ile, ör. 2)")
    args = ap.parse_args()

    for sembol in args.sembol:
        for tf in args.tf:
            try:
                df = veri.indir(sembol, tf, gun=args.gun)
            except Exception as e:
                print(f"  HATA {sembol}/{tf}: {e}")
                continue
            # Üst zaman dilimi (MTF onayı için)
            _ust_tf = {"15m": "1h", "1h": "4h", "4h": "1d"}.get(tf)
            df_ust = None
            if _ust_tf:
                try:
                    df_ust = veri.indir(sembol, _ust_tf, gun=args.gun)
                except Exception:
                    df_ust = None
            # ALT/BTC göreceli güç (makro filtre)
            from miraz import oran
            gguc = oran.goreceli_guc(sembol)
            s = sn.senaryo_uret(df, n=args.pivot_n, tolerans=args.tolerans,
                                min_guc=args.min_guc, df_ust=df_ust, gguc=gguc,
                                r_dolar=args.r)
            sn.yazdir(sembol, tf, s, vade=args.vade)

            if args.r > 0 and args.kademe > 0:
                from miraz.risk import kademeli_plan
                paylar = tuple([1.0 / args.kademe] * args.kademe)
                kp = kademeli_plan(s, r_dolar=args.r, paylar=paylar)
                if kp is not None:
                    print("\n" + kp.aciklama)

            if args.grafik:
                from miraz import grafik
                _ad = {"BTCUSDT": "Bitcoin / TetherUS",
                       "ETHUSDT": "Ethereum / TetherUS",
                       "SOLUSDT": "Solana / TetherUS"}.get(
                           sembol, f"{sembol[:-4]} / TetherUS")
                _tf = {"1h": "1sa", "4h": "4sa", "1d": "1g",
                       "15m": "15dk"}.get(tf, tf)
                cikti = Path("data/grafikler") / f"{sembol}_{tf}_senaryo.png"
                yol = grafik.senaryo_ciz(
                    df, s, dosya=cikti, son_n=args.son_n,
                    symbol=_ad, interval=_tf, borsa="Binance",
                    baslik=f"miraz otomatik senaryo — {s.yon}")
                print(f"✅ Grafik: {yol}")


if __name__ == "__main__":
    main()
