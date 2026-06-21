"""Price Action Labs CLI — backtest motoru (terminalMiraz tarzı).

Kullanım:
    python backtest/lab.py --sembol BTCUSDT --tf 4h
    python backtest/lab.py --sembol BTCUSDT ETHUSDT --tf 4h --min-guven 70
    python backtest/lab.py --sembol BTCUSDT --tf 4h --sadece-trade
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz import veri
from miraz.lab import backtest, lab_tara


def main() -> None:
    ap = argparse.ArgumentParser(description="Price Action Labs backtest")
    ap.add_argument("--sembol", nargs="+", default=["BTCUSDT"])
    ap.add_argument("--tf", nargs="+", default=["4h"])
    ap.add_argument("--adim", type=int, default=6)
    ap.add_argument("--max-bar", type=int, default=60)
    ap.add_argument("--pencere", type=int, default=800)
    ap.add_argument("--min-guven", type=float, default=0.0)
    ap.add_argument("--sadece-trade", action="store_true")
    ap.add_argument("--tara", action="store_true",
                    help="TP/Giriş/Stop Lab parametre taraması yap")
    ap.add_argument("--giris", default="orta", choices=["ust", "orta", "alt"])
    ap.add_argument("--stop", default="fitil",
                    choices=["fitil", "yapisal", "genis"])
    ap.add_argument("--tp", default="ana", choices=["ana", "ara", "rr2"])
    ap.add_argument("--gun", type=int, default=500)
    args = ap.parse_args()

    if args.tara:
        tf = args.tf[0]
        dfs = {}
        for sym in args.sembol:
            try:
                dfs[sym] = veri.indir(sym, tf, gun=args.gun)
            except Exception as e:
                print(f"  HATA {sym}: {e}")
        print(lab_tara(dfs, adim=args.adim, max_bar=args.max_bar,
                       pencere=args.pencere, min_guven=args.min_guven))
        return

    g_dolan = g_tp = 0
    g_r = 0.0
    for sym in args.sembol:
        for tf in args.tf:
            try:
                df = veri.indir(sym, tf, gun=args.gun)
            except Exception as e:
                print(f"  HATA {sym}/{tf}: {e}")
                continue
            r = backtest(df, adim=args.adim, max_bar=args.max_bar,
                         pencere=args.pencere, min_guven=args.min_guven,
                         sadece_trade=args.sadece_trade, giris_mod=args.giris,
                         stop_mod=args.stop, tp_mod=args.tp)
            print(f"\n=== {sym} / {tf} ===")
            print(r.ozet_metin())
            g_dolan += len(r.dolan)
            g_tp += sum(1 for i in r.dolan if i.sonuc == "TP")
            g_r += r.toplam_r

    if len(args.sembol) * len(args.tf) > 1 and g_dolan:
        wr = 100 * g_tp / g_dolan
        print(f"\n{'═'*48}")
        print(f"GENEL: {g_dolan} dolan işlem | WR %{wr:.1f} | {g_r:+.1f}R")


if __name__ == "__main__":
    main()
