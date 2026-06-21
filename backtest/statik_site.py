#!/usr/bin/env python3
"""Statik site üreteci — GitHub Pages için tek seferlik tarama snapshot'ı.

Sürekli açık bir sunucu yerine, GitHub Actions cron'u bu betiği her N dakikada
bir çalıştırır; çıktı statik dosyalar olarak Pages'e yayınlanır:

    <cikti>/index.html              (panel — statik moda ayarlı)
    <cikti>/durum.json              (son tarama anlık görüntüsü)
    <cikti>/grafik/<SYM>_<TF>.json  (her aday için grafik verisi)

Panel `window.STATIK=true` ile bu dosyaları okur (canlı /api/* yerine).

Kullanım:
    python backtest/statik_site.py --cikti site --mtf
    python backtest/statik_site.py --cikti site --genis --taraf her
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "src"))

from miraz.gozlemci import Gozlemci                     # noqa: E402
from miraz.radar import (CEKIRDEK_EVREN, GENIS_EVREN,   # noqa: E402
                         TERMINALMIRAZ_TF)
from miraz.sunucu import durum_json, grafik_veri, WEB_DIZIN  # noqa: E402


def _yaz_json(yol: Path, veri: dict) -> None:
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(json.dumps(veri, ensure_ascii=False), encoding="utf-8")


def _grafik_hedefleri(durum: dict) -> list[tuple[str, str]]:
    """Snapshot'ta tıklanabilir (grafik gereken) tüm sembol/TF çiftleri."""
    cift = set()
    for a in durum.get("adaylar", []):
        if a.get("symbol") and a.get("interval"):
            cift.add((a["symbol"], a["interval"]))
    for b in durum.get("bildirimler", []):
        if b.get("sembol") and b.get("interval"):
            cift.add((b["sembol"], b["interval"]))
    vg = durum.get("varsayilan_grafik") or {}
    if vg.get("symbol"):
        cift.add((vg["symbol"], vg["interval"]))
    return sorted(cift)


def uret(cikti: Path, semboller: list[str], intervallar: list[str],
         taraf: str, max_bar: int, aralik: int, gun: int) -> None:
    cikti.mkdir(parents=True, exist_ok=True)

    # 1) Tek tur tarama (sunucunun _bir_tarama'sının statik karşılığı)
    goz = Gozlemci(semboller=semboller, intervallar=intervallar, taraf=taraf,
                   goreceli=False, gun=gun, max_bar=max_bar)
    print(f"⏳ Tarama: {len(semboller)} parite × {len(intervallar)} TF "
          f"({' '.join(intervallar)}) · {taraf}")
    sonuc = goz.dongu()
    durum = durum_json(goz, sonuc.rapor, aralik)
    durum["tarama_durumu"] = "tamam"
    durum["statik"] = True
    durum["hazir"] = True          # canlı sunucuda DurumDeposu.yaz() set eder; statik
                                   # snapshot'ta elle işaretle, yoksa panel sonsuza
                                   # dek "tarama bekleniyor" gösterir
    _yaz_json(cikti / "durum.json", durum)
    print(f"✅ durum.json — {durum['ozet']}")

    # 2) Her tıklanabilir sembol/TF için grafik verisi
    grafik_dizin = cikti / "grafik"
    if grafik_dizin.exists():
        shutil.rmtree(grafik_dizin)
    hedefler = _grafik_hedefleri(durum)
    basarili = 0
    for sym, ivl in hedefler:
        try:
            g = grafik_veri(sym, ivl, durum=durum, gun=gun, max_bar=max_bar)
            _yaz_json(grafik_dizin / f"{sym}_{ivl}.json", g)
            basarili += 1
        except Exception as e:                          # bir sembol patlasa diğerleri sürsün
            print(f"  ⚠️ grafik {sym}/{ivl}: {e}")
    print(f"✅ grafik/ — {basarili}/{len(hedefler)} dosya")

    # 3) Paneli statik moda ayarlayıp kopyala
    html = (WEB_DIZIN / "index.html").read_text(encoding="utf-8")
    html = html.replace("window.STATIK=false", "window.STATIK=true")
    (cikti / "index.html").write_text(html, encoding="utf-8")
    # Pages Jekyll'i atlasın (alt dizinler/altçizgi korunsun)
    (cikti / ".nojekyll").write_text("", encoding="utf-8")
    print(f"✅ index.html (statik) → {cikti}")


def main() -> None:
    ap = argparse.ArgumentParser(description="GitHub Pages statik tarama snapshot'ı")
    ap.add_argument("--cikti", default="site", help="çıktı dizini (varsayılan: site)")
    ap.add_argument("--genis", action="store_true", help="geniş evren (92 parite)")
    ap.add_argument("--mtf", action="store_true",
                    help=f"terminalMiraz {len(TERMINALMIRAZ_TF)} TF: "
                         f"{' '.join(TERMINALMIRAZ_TF)}")
    ap.add_argument("--tf", nargs="+", default=["1h"], help="--mtf yoksa TF listesi")
    ap.add_argument("--taraf", default="her", choices=["long", "short", "her"])
    ap.add_argument("--max-bar", type=int, default=900)
    ap.add_argument("--gun", type=int, default=120)
    ap.add_argument("--aralik", type=int, default=1800, help="snapshot tarama aralığı (sn)")
    args = ap.parse_args()

    semboller = GENIS_EVREN if args.genis else CEKIRDEK_EVREN
    intervallar = TERMINALMIRAZ_TF if args.mtf else args.tf
    uret(Path(args.cikti), semboller, intervallar, args.taraf,
         args.max_bar, args.aralik, args.gun)


if __name__ == "__main__":
    main()
