"""Parite evreni CLI — piyasa değerine göre dinamik liste (terminalMiraz tarzı).

terminalMiraz pariteleri mcap'e göre seçer ve düzenli (haftalık) kontrol eder:
mcap'i düşüp listeden çıkanları atar, yükselip girenleri ekler.

Kullanım:
    # Haftalık güncelleme — taze liste + eklenen/çıkan raporu
    python backtest/evren.py --guncelle --n 90

    # Mevcut listeyi mcap sırasıyla göster
    python backtest/evren.py --listele

Çıktı data/evren.json'a kaydedilir; radar `--mcap` ile bu evreni kullanır.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz.evren import evren_guncelle, EVREN_DOSYA


def main() -> None:
    ap = argparse.ArgumentParser(description="Mcap parite evreni yönetimi")
    ap.add_argument("--n", type=int, default=90,
                    help="ilk kaç parite (mcap sırası, vars. 90)")
    ap.add_argument("--guncelle", action="store_true",
                    help="taze mcap listesini çek, değişimi raporla, kaydet")
    ap.add_argument("--listele", action="store_true",
                    help="kayıtlı evreni mcap sırasıyla göster")
    ap.add_argument("--dosya", default=str(EVREN_DOSYA))
    args = ap.parse_args()

    dosya = Path(args.dosya)

    if args.guncelle:
        print("🌐 Mcap evreni güncelleniyor (CoinGecko + MEXC) ...")
        sonuc = evren_guncelle(n=args.n, dosya=dosya)
        print(sonuc.rapor())
        print(f"\n✅ {len(sonuc.semboller)} parite kaydedildi → {dosya.name}")
        return

    if not dosya.exists():
        print(f"⚠️  {dosya.name} yok. Önce: python backtest/evren.py --guncelle")
        return

    d = json.loads(dosya.read_text(encoding="utf-8"))
    semboller = d.get("semboller", [])
    rank = d.get("mcap_rank", {})
    print(f"🌐 MCAP EVRENİ — {len(semboller)} parite "
          f"(güncelleme: {d.get('guncelleme','?')[:10]})")
    print("─" * 40)
    for i, s in enumerate(semboller, 1):
        print(f"  {i:3}. {s:14} (mcap #{rank.get(s,'?')})")


if __name__ == "__main__":
    main()
