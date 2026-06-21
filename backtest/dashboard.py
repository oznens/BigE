"""TerminalMiraz canlı terminal panosu — koyu temalı komuta ekranı.

@tradermiraz'ın terminalMiraz'ı gibi: terminalden çalıştırılan, sürekli
güncellenen, 4 result bucket'lı (Scanner/Filtered/Harmonic/Late) pano.

Kullanım:
    # Tek tur (tarar, panoyu basar)
    python backtest/dashboard.py --bir --mcap --mtf --taraf her

    # Sürekli mod (her 3 dk'da bir tarar, terminal güncellenir)
    python backtest/dashboard.py --surekli --aralik 180 --mcap --mtf --taraf her

    # Defter & portföy durumunu göster (tarama yapmaz)
    python backtest/dashboard.py --durum

Defter (Learning Journal) → defter.json, paper-trading → portfoy.json (yerel).
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz.gozlemci import Gozlemci, Defter, DEFTER_DOSYA, PORTFOY_DOSYA
from miraz.portfoy import Portfoy
from miraz.radar import (CEKIRDEK_EVREN, GENIS_EVREN, TERMINALMIRAZ_TF,
                         RISK_MODLARI)
from miraz.dashboard import pano_yazdir, console

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
        console.print("[red]⚠️  data/evren.json yok — önce:[/red] "
                      "python backtest/evren.py --guncelle")
        sys.exit(1)
    return GENIS_EVREN if args.genis else CEKIRDEK_EVREN


def _durum_goster() -> None:
    from rich.table import Table

    defter = Defter.yukle(DEFTER_DOSYA)
    d = defter.ozet()
    buckets = d.get("buckets", {})

    # başlık
    console.rule("[bold cyan]LEARNING JOURNAL DURUMU[/]")

    # özet satır
    r_renk = "green" if d["toplam_r"] >= 0 else "red"
    console.print(
        f"[cyan]{d['toplam']}[/] kayıt · "
        f"[bright_black]{defter.tarama_turu} döngü, "
        f"{defter.toplam_tarama} kümülatif tarama[/]")
    console.print(
        f"Aktif [cyan]{d['aktif']}[/] (Aday {d['Aday']} · Açık {d['Açık']}) | "
        f"[green]{d['TP']} TP[/] · [red]{d['STOP']} STOP[/] · "
        f"[yellow]{d['Expired']} Expired[/] · {d['Manuel']} Manuel")
    console.print(
        f"Win-rate [bold]%{d['wr']}[/] | "
        f"Toplam [{r_renk}]{d['toplam_r']:+.1f}R[/]")

    # bucket tablosu
    if any(b["toplam"] for b in buckets.values()):
        t = Table(title="Bucket Performansı", border_style="bright_black")
        t.add_column("Bucket", style="cyan")
        t.add_column("Kapalı", justify="right")
        t.add_column("TP", justify="right", style="green")
        t.add_column("STOP", justify="right", style="red")
        t.add_column("WR%", justify="right")
        for b, bkt in buckets.items():
            wr_s = f"[green]%{bkt['wr']:.0f}[/]" if bkt["wr"] >= 60 \
                else (f"[yellow]%{bkt['wr']:.0f}[/]" if bkt["wr"] >= 40
                      else f"[red]%{bkt['wr']:.0f}[/]")
            t.add_row(b, str(bkt["toplam"]), str(bkt["tp"]),
                      str(bkt["stop"]), wr_s)
        console.print(t)

    # portföy tablosu
    if PORTFOY_DOSYA.exists():
        console.print()
        console.print(Portfoy.yukle(PORTFOY_DOSYA).tablo())

    # son 10 kapanan kayıt
    kapanan = [k for k in defter.kayitlar if not k.aktif][-10:]
    if kapanan:
        console.rule("[dim]Son kapanan kayıtlar[/]")
        for k in kapanan:
            ikon = {"TP": "[green]✅[/]", "STOP": "[red]🔴[/]",
                    "Expired": "[yellow]⌛[/]", "Manuel": "✋"}.get(k.durum, "·")
            console.print(
                f"  {ikon} #{k.id} {k.sembol}/{k.interval} "
                f"{k.taraf} {k.kalite} → {k.durum} "
                f"[{'green' if k.r_sonuc >= 0 else 'red'}]{k.r_sonuc:+.1f}R[/]")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="TerminalMiraz canlı terminal panosu")
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
    ap.add_argument("--bir", action="store_true", help="tek tur çalıştır")
    ap.add_argument("--surekli", action="store_true",
                    help="sürekli döngü (--aralik sn)")
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

    portfoy = (Portfoy.yukle(PORTFOY_DOSYA) if PORTFOY_DOSYA.exists()
               else Portfoy(r_dolar=args.r))
    defter = Defter.yukle(DEFTER_DOSYA)

    g = Gozlemci(
        semboller=semboller, intervallar=tflar, taraf=args.taraf,
        rr_hedef=rr_hedef, cluster_hafiza=cluster_hafiza, r_dolar=args.r,
        gun=args.gun, max_bekleme=args.max_bekleme,
        goreceli=not (args.genis or args.mcap), portfoy=portfoy, defter=defter)

    console.print(
        f"[green]🟢 Dashboard başladı[/] — "
        f"[cyan]{len(semboller)}[/] parite × "
        f"[cyan]{len(tflar)}[/] TF ({' '.join(tflar)}) · "
        f"{args.taraf} · risk={args.risk_mod}")

    def _bir_tur():
        console.print("[bright_black]Taranıyor...[/]")
        sonuc = g.dongu()
        g.kaydet(DEFTER_DOSYA, PORTFOY_DOSYA)
        bilgi = (f"Tarama #{g.defter.tarama_turu} · "
                 f"{len(semboller)} parite × {len(tflar)} TF "
                 f"({' '.join(tflar)}) · {args.taraf} · +{sonuc.eklenen} yeni")
        console.clear()
        pano_yazdir(sonuc.rapor, defter=g.defter, portfoy=g.portfoy, bilgi=bilgi)
        # eklenen/değişen özet
        if sonuc.eklenen:
            console.print(f"[green]  ➕ {sonuc.eklenen} yeni setup[/]")
        for p in sonuc.degisenler:
            ikon = {"TP": "[green]✅[/]", "STOP": "[red]🔴[/]",
                    "Açık": "[cyan]🟢[/]", "Expired": "[yellow]⌛[/]"
                    }.get(p.durum, "⬜")
            rtxt = (f" [{'green' if p.r_sonuc >= 0 else 'red'}]"
                    f"{p.r_sonuc:+.1f}R[/]"
                    if p.durum in ("TP", "STOP") else "")
            console.print(f"  {ikon} {p.sembol}/{p.interval} {p.durum}{rtxt}")

    if args.surekli:
        console.print(
            f"[cyan]♾️  Sürekli mod[/] — her [bold]{args.aralik}[/] sn "
            "(durdurmak için [bold]Ctrl+C[/])\n")
        try:
            while True:
                _bir_tur()
                _bekle(args.aralik)
        except KeyboardInterrupt:
            console.print("\n[red]🛑 Durduruldu.[/] Defter & portföy kaydedildi.")
    else:
        _bir_tur()


def _bekle(aralik: int) -> None:
    """Geri sayım göstererek bekler."""
    from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                  TimeElapsedColumn(), console=console, transient=True) as prog:
        task = prog.add_task(
            f"[bright_black]Sonraki taramaya {aralik} sn...[/]", total=None)
        time.sleep(aralik)
        prog.update(task, description="[green]Taranıyor...[/]")


if __name__ == "__main__":
    main()
