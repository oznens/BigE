"""Harmonik tarayıcıyı BTC + seçili altcoinlerde çalıştırır.

Kullanım:
    python backtest/harmonik_scan.py
    python backtest/harmonik_scan.py --sembol ETHUSDT --tf 1h 4h --kalite 60
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz import tarayici as tr


def main() -> None:
    ap = argparse.ArgumentParser(description="Harmonik pattern tarayıcı")
    ap.add_argument("--sembol", nargs="+",
                    default=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
                    help="Taranacak semboller")
    ap.add_argument("--tf", nargs="+",
                    default=["1h", "4h"],
                    help="Zaman dilimleri (ör. 15m 1h 4h)")
    ap.add_argument("--kalite", type=float, default=40.0,
                    help="Minimum kalite puanı (0-100)")
    ap.add_argument("--pivot-n", type=int, default=5,
                    help="Swing pivot pencere boyutu")
    ap.add_argument("--gun", type=int, default=500,
                    help="Kaç günlük veri kullanılacak")
    args = ap.parse_args()

    print(f"Taranan semboller : {args.sembol}")
    print(f"Zaman dilimleri   : {args.tf}")
    print(f"Min kalite        : {args.kalite}")
    print(f"Pivot penceresi   : {args.pivot_n}")
    print()

    sonuclar = tr.tara_coklu(
        semboller=args.sembol,
        intervallar=args.tf,
        pivot_n=args.pivot_n,
        min_kalite=args.kalite,
        gun=args.gun,
    )
    tr.ozet_yazdir(sonuclar)

    # En iyi pattern'i detaylı göster
    if sonuclar:
        best = sonuclar[0]
        p = best.pattern
        print(f"📌 En güncel pattern: {best.symbol} / {best.interval}")
        print(f"   {p.yon} {p.isim}")
        print(f"   XABCD: {p.X:.2f} → {p.A:.2f} → {p.B:.2f} → {p.C:.2f} → {p.D:.2f}")
        print(f"   Entry: {p.entry:.2f}  SL: {p.sl:.2f}  TP1: {p.tp1:.2f}  TP2: {p.tp2:.2f}")
        print(f"   R:R: {p.rr}  Kalite: {p.kalite}/100")
        print(f"   AB/XA: {p.oranlar.get('AB_XA', 0):.3f}  "
              f"BC/AB: {p.oranlar.get('BC_AB', 0):.3f}  "
              f"CD/BC: {p.oranlar.get('CD_BC', 0):.3f}  "
              f"XD/XA: {p.oranlar.get('XD_XA', 0):.3f}")


if __name__ == "__main__":
    main()
