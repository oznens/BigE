"""Canlı Gözlemci CLI — terminalMiraz gibi sürekli tara + kaydet + takip et.

Kullanım:
    # Tek tur (bir tarama-kayıt-takip döngüsü)
    python backtest/gozlemci.py --bir --mcap --mtf --taraf her

    # Sürekli (her 180 sn'de bir tarar) — terminalMiraz çalışma modu
    python backtest/gozlemci.py --surekli --aralik 180 --mcap --mtf --taraf her

    # Defter & portföy durumunu göster
    python backtest/gozlemci.py --durum

Defter (Learning Journal) → defter.json, paper-trading → portfoy.json (yerel).
Sürekli mod kendi makinende çalıştırılmak içindir (uygulama açık kaldıkça tarar).
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz.gozlemci import (Gozlemci, Defter, DEFTER_DOSYA, PORTFOY_DOSYA)
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


def _durum_goster() -> None:
    defter = Defter.yukle(DEFTER_DOSYA)
    d = defter.ozet()
    print(f"📓 LEARNING JOURNAL — {d['toplam']} kayıt "
          f"({defter.tarama_turu} döngü, {defter.toplam_tarama} kümülatif tarama)")
    print(f"   Aktif {d['aktif']} (Aday {d['Aday']} · Açık {d['Açık']}) | "
          f"{d['TP']} TP · {d['STOP']} STOP · {d['Expired']} Expired · "
          f"{d['Manuel']} Manuel")
    print(f"   Win-rate %{d['wr']} | Toplam {d['toplam_r']:+.1f}R")
    if PORTFOY_DOSYA.exists():
        print("\n" + Portfoy.yukle(PORTFOY_DOSYA).tablo())
    # Son 10 kapanan kayıt
    kapanan = [k for k in defter.kayitlar if not k.aktif][-10:]
    if kapanan:
        print("\n🗂️  Son kapanan kayıtlar:")
        for k in kapanan:
            ik = {"TP": "✅", "STOP": "🔴", "Expired": "⌛",
                  "Manuel": "✋"}.get(k.durum, "·")
            print(f"   {ik} #{k.id} {k.sembol}/{k.interval} {k.taraf} "
                  f"{k.kalite} → {k.durum} {k.r_sonuc:+.1f}R")


def main() -> None:
    ap = argparse.ArgumentParser(description="Canlı Gözlemci (terminalMiraz tarzı)")
    ap.add_argument("--semboller", nargs="+", default=None)
    ap.add_argument("--genis", action="store_true")
    ap.add_argument("--mcap", action="store_true",
                    help="mcap evrenini kullan (data/evren.json)")
    ap.add_argument("--tf", nargs="+", default=["4h"])
    ap.add_argument("--mtf", action="store_true",
                    help=f"terminalMiraz {len(TERMINALMIRAZ_TF)} TF: {' '.join(TERMINALMIRAZ_TF)}")
    ap.add_argument("--taraf", default="long", choices=["long", "short", "her"])
    ap.add_argument("--risk-mod", default="guvenli", choices=list(RISK_MODLARI))
    ap.add_argument("--r", type=float, default=25.0)
    ap.add_argument("--gun", type=int, default=120)
    ap.add_argument("--max-bekleme", type=int, default=24)
    ap.add_argument("--cluster", action="store_true")
    ap.add_argument("--pano", action="store_true",
                    help="her döngüde terminal.png panosunu yenile")
    ap.add_argument("--bir", action="store_true", help="tek tur çalıştır")
    ap.add_argument("--surekli", action="store_true",
                    help="sürekli döngü (--aralik sn ile)")
    ap.add_argument("--aralik", type=int, default=180,
                    help="sürekli modda döngü arası saniye (vars. 180)")
    ap.add_argument("--durum", action="store_true",
                    help="defter & portföy durumunu göster, çık")
    args = ap.parse_args()

    if args.durum:
        _durum_goster()
        return

    semboller = _evren(args)
    tflar = TERMINALMIRAZ_TF if args.mtf else args.tf
    rr_hedef = RISK_MODLARI[args.risk_mod]

    cluster_hafiza = None
    if args.cluster and CLUSTER_DOSYA.exists():
        from miraz.cluster import ClusterHafiza
        cluster_hafiza = ClusterHafiza.yukle(CLUSTER_DOSYA)

    # Önceki durumu sürdür (kaldığı yerden)
    portfoy = Portfoy.yukle(PORTFOY_DOSYA) if PORTFOY_DOSYA.exists() \
        else Portfoy(r_dolar=args.r)
    defter = Defter.yukle(DEFTER_DOSYA)

    g = Gozlemci(
        semboller=semboller, intervallar=tflar, taraf=args.taraf,
        rr_hedef=rr_hedef, cluster_hafiza=cluster_hafiza, r_dolar=args.r,
        gun=args.gun, max_bekleme=args.max_bekleme,
        goreceli=not (args.genis or args.mcap), portfoy=portfoy, defter=defter)

    print(f"🟢 Gözlemci başladı — {len(semboller)} parite × {len(tflar)} TF "
          f"({' '.join(tflar)}) · {args.taraf} · risk={args.risk_mod}")

    def _bir_tur():
        sonuc = g.dongu()
        print("\n" + sonuc.metin)
        g.kaydet(DEFTER_DOSYA, PORTFOY_DOSYA)
        if args.pano:
            try:
                from miraz.radar import radar_tara
                from miraz.terminal import panel_ciz
                rapor = radar_tara(semboller, tflar, gun=args.gun,
                                   cluster_hafiza=cluster_hafiza,
                                   goreceli=False, taraf=args.taraf,
                                   rr_hedef=rr_hedef)
                panel_ciz(rapor, portfoy=g.portfoy,
                          dosya=str(KOK / "data" / "terminal.png"))
            except Exception as e:
                print(f"   ⚠️ pano çizilemedi: {e}")

    if args.surekli:
        print(f"♾️  Sürekli mod — her {args.aralik} sn (durdurmak için Ctrl+C)\n")
        try:
            while True:
                _bir_tur()
                time.sleep(args.aralik)
        except KeyboardInterrupt:
            print("\n🛑 Gözlemci durduruldu. Defter & portföy kaydedildi.")
    else:
        _bir_tur()


if __name__ == "__main__":
    main()
