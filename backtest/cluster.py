"""Cluster hafızası CLI — geçmiş veriden setup kümeleri öğrenir & raporlar.

terminalMiraz'ın "bu tip setup geçmişte %X TP yaptı" katmanı.

Kullanım:
    # Geçmiş veriden cluster hafızası öğren ve kaydet
    python backtest/cluster.py --ogren --semboller BTCUSDT ETHUSDT SOLUSDT

    # Kayıtlı hafızadaki en güçlü/zayıf clusterları listele
    python backtest/cluster.py --listele

    # Güncel bir sembol için benzerlik raporu
    python backtest/cluster.py --benzerlik BTCUSDT --tf 4h
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz import veri
from miraz import senaryo as sn
from miraz.cluster import cluster_ogren, benzerlik, ClusterHafiza
from miraz.radar import VARSAYILAN_EVREN

CLUSTER_DOSYA = Path(__file__).resolve().parents[1] / "cluster.json"


def _listele(h: ClusterHafiza, min_n: int = 8) -> None:
    kayitlar = [c for c in h.clusterlar.values()
                if (c.tp + c.stop) >= min_n]
    kayitlar.sort(key=lambda c: c.beklenti, reverse=True)
    print(f"\n🧬 CLUSTER HAFIZASI — {h.toplam_setup} setup, "
          f"{len(h.clusterlar)} farklı imza (≥{min_n} örnek):")
    print("─" * 72)
    if not kayitlar:
        print("  (yeterli örnekli cluster yok — daha çok sembol/gün ile öğret)")
        return
    print(f"  {'İmza':<46} {'N':>4} {'WR':>6} {'Beklenti':>9}")
    print("─" * 72)
    for c in kayitlar:
        imza_txt = "·".join(str(x) for x in c.imza)
        if len(imza_txt) > 45:
            imza_txt = imza_txt[:44] + "…"
        print(f"  {imza_txt:<46} {c.tp + c.stop:>4} "
              f"%{c.wr:>4} {c.beklenti:>+8.2f}R")


def main() -> None:
    ap = argparse.ArgumentParser(description="Cluster hafızası")
    ap.add_argument("--semboller", nargs="+", default=VARSAYILAN_EVREN)
    ap.add_argument("--tf", default="4h")
    ap.add_argument("--gun", type=int, default=500)
    ap.add_argument("--pencere", type=int, default=800)
    ap.add_argument("--ogren", action="store_true",
                    help="Geçmiş veriden cluster öğren ve kaydet")
    ap.add_argument("--listele", action="store_true",
                    help="Kayıtlı clusterları beklenti R'a göre listele")
    ap.add_argument("--benzerlik", default=None,
                    help="Bir sembol için güncel setup benzerlik raporu")
    ap.add_argument("--min-n", type=int, default=8)
    ap.add_argument("--giris", default="ust", choices=["ust", "orta", "alt"],
                    help="öğrenmede giriş modu (lab doğrulaması: ust)")
    ap.add_argument("--stop", default="fitil",
                    choices=["fitil", "yapisal", "genis"])
    ap.add_argument("--tp", default="rr", choices=["rr", "rr2", "ara", "ana"],
                    help="öğrenmede TP modu (terminalMiraz: rr=1R uzaklık)")
    ap.add_argument("--yon", default="long", choices=["long", "short"],
                    help="öğrenmede yön: long (varsayılan) | short")
    ap.add_argument("--dosya", default=str(CLUSTER_DOSYA))
    args = ap.parse_args()

    dosya = Path(args.dosya)

    if args.ogren:
        print(f"🧬 Öğreniliyor ({args.yon.upper()}): {args.semboller} / {args.tf} ...")
        dfs = {}
        for sym in args.semboller:
            try:
                dfs[sym] = veri.indir(sym, args.tf, gun=args.gun)
            except Exception as e:
                print(f"  ⚠️  {sym}: {e}")
        h = cluster_ogren(dfs, pencere=args.pencere, giris_mod=args.giris,
                          stop_mod=args.stop, tp_mod=args.tp, yon=args.yon)
        h.kaydet(dosya)
        print(f"✅ {h.toplam_setup} setup, {len(h.clusterlar)} imza kaydedildi "
              f"→ {dosya.name}")
        _listele(h, args.min_n)
        return

    if not dosya.exists():
        print(f"⚠️  {dosya.name} yok. Önce: python backtest/cluster.py --ogren")
        return
    h = ClusterHafiza.yukle(dosya)

    if args.listele:
        _listele(h, args.min_n)

    if args.benzerlik:
        sym = args.benzerlik
        df = veri.indir(sym, args.tf, gun=args.gun)
        s = sn.senaryo_uret(df)
        sonuc = benzerlik(s, h)
        print(f"\n=== {sym} / {args.tf} ===")
        if s.karar is not None:
            print(f"  {s.karar.metin}")
        print(f"  {sonuc.metin}")


if __name__ == "__main__":
    main()
