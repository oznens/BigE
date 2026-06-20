"""En güncel çakışma setup'ını grafik üzerinde çizer.

Seçim: D noktası en yeni (en sağda) olan ve kutuyla çakışan setup.
Böylece "şu anda izlenecek" setup gösterilir.

Kullanım:
    python backtest/setup_grafik.py --sembol BTCUSDT --tf 4h
    python backtest/setup_grafik.py --sembol ETHUSDT --tf 1h --cikti eth.png
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz import cakisma as ck
from miraz import grafik
from miraz import kutular as kt
from miraz import veri


def main() -> None:
    ap = argparse.ArgumentParser(description="Güncel setup grafiği")
    ap.add_argument("--sembol", default="BTCUSDT")
    ap.add_argument("--tf", default="4h")
    ap.add_argument("--pivot-n", type=int, default=5)
    ap.add_argument("--kalite", type=float, default=40.0)
    ap.add_argument("--tolerans", type=float, default=0.015)
    ap.add_argument("--son-n", type=int, default=220, help="Gösterilecek mum sayısı")
    ap.add_argument("--cikti", default=None, help="Çıktı PNG yolu")
    ap.add_argument("--gun", type=int, default=500)
    args = ap.parse_args()

    df = veri.indir(args.sembol, args.tf, gun=args.gun)

    cakismalar = ck.cakismalari_bul(
        df, pivot_n=args.pivot_n, min_kalite=args.kalite,
        tolerans=args.tolerans, sadece_cakisan=True,
    )
    if not cakismalar:
        print("Çakışan setup bulunamadı. Eşikleri gevşetmeyi deneyin.")
        return

    # En güncel D'ye sahip çakışmayı seç
    guncel = max(cakismalar, key=lambda c: c.pattern.D_idx)
    p = guncel.pattern

    # Görünür kutuları al (mesafe limiti yok, hepsini çizdir)
    kutlar = kt.kutulari_bul(df, n=args.pivot_n, tolerans=args.tolerans,
                             mesafe_limit=None)

    cikti = Path(args.cikti) if args.cikti else \
        Path("data/grafikler") / f"{args.sembol}_{args.tf}_setup.png"

    # Pencereyi pattern'i tam kapsayacak şekilde otomatik genişlet
    # (X noktasından ~40 bar önce başlasın, sona kadar göster)
    gereken = len(df) - p.X_idx + 40
    son_n = max(args.son_n, gereken)

    baslik = (f"{args.sembol} / {args.tf}  —  {p.yon} {p.isim}  "
              f"(çakışma skoru {guncel.skor:.0f})")
    yol = grafik.setup_ciz(df, p, kutlar, dosya=cikti, baslik=baslik,
                           son_n=son_n)

    print(f"✅ Grafik kaydedildi: {yol}")
    print(f"\n📌 Setup: {p.yon} {p.isim}")
    print(f"   {guncel.aciklama}")
    print(f"   Entry {p.entry:,.2f}  SL {p.sl:,.2f}  "
          f"TP1 {p.tp1:,.2f}  TP2 {p.tp2:,.2f}  R:R {p.rr}")
    print(f"   Harmonik kalite {p.kalite:.0f}/100  |  Çakışma skoru {guncel.skor:.0f}/100")


if __name__ == "__main__":
    main()
