"""Terminal Dashboard — @tradermiraz terminalMiraz tarzı canlı pano.

rich kütüphanesiyle terminal üzerinde koyu temalı komuta paneli:

  ┌─── TerminalMiraz · CANLI TARAMA PANELİ ───────────────────────────────┐
  │  SCANNER  FILTERED  HARMONIC  LATE  (kümülatif TP/STOP/WR)            │
  ├──────────────────────────────────────────┬─────────────────────────────┤
  │  CANLI ADAY AKIŞI                        │  SONUÇ BİLDİRİMLERİ        │
  │  setup kartları                          │  TP / STOP / kapanış        │
  └──────────────────────────────────────────┴─────────────────────────────┘

Kullanım:
    from miraz.dashboard import pano_yazdir, canli_dongu
    pano_yazdir(rapor, defter=defter, portfoy=portfoy, bilgi="Tarama #3")
"""

from __future__ import annotations

from datetime import datetime, timezone
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

# ── renk paleti (terminalMiraz koyu tema) ────────────────────────────────────
_C = {
    "scanner":  "green",
    "filtered": "yellow",
    "harmonic": "cyan",
    "late":     "red",
    "htf":      "bright_black",
    "long":     "green",
    "short":    "red",
    "aday":     "green",
    "izle":     "yellow",
    "atla":     "bright_black",
    "elenen":   "red",
    "tp":       "green",
    "stop":     "red",
    "expired":  "yellow",
    "dim":      "bright_black",
    "accent":   "cyan",
    "header":   "bold white",
}

_KAT_RENK = {
    "Trade":   _C["aday"],
    "Watch":   _C["izle"],
    "Skip":    _C["atla"],
    "Elenen":  _C["elenen"],
}

_BUCKET_RENK = {
    "Scanner":  _C["scanner"],
    "Harmonic": _C["harmonic"],
    "Filtered": _C["filtered"],
    "Late":     _C["late"],
    "HTF":      _C["htf"],
}


def _fmt(v: float | None) -> str:
    if v is None:
        return "—"
    a = abs(v)
    if a >= 1000:
        return f"{v:,.2f}"
    if a >= 1:
        return f"{v:.4f}".rstrip("0").rstrip(".")
    if a >= 0.01:
        return f"{v:.5f}"
    if a >= 0.0001:
        return f"{v:.6f}"
    return f"{v:.8f}"


# ── 4 komuta metriği ─────────────────────────────────────────────────────────

def _metrik_tablosu(buckets: dict) -> Table:
    """4 bucket'ı (Scanner/Filtered/Harmonic/Late) yan yana gösterir."""
    t = Table.grid(expand=True, padding=(0, 1))
    for _ in range(4):
        t.add_column(ratio=1)

    siralama = [("SCANNER RESULT", "Scanner"),
                ("FILTERED RESULT", "Filtered"),
                ("HARMONIK RESULT", "Harmonic"),
                ("LATE RESULT", "Late")]

    panels = []
    for baslik, anahtar in siralama:
        b = buckets.get(anahtar, {"tp": 0, "stop": 0, "toplam": 0, "wr": 0.0})
        renk = _BUCKET_RENK.get(anahtar, "white")
        wr_renk = "green" if b["wr"] >= 60 else ("yellow" if b["wr"] >= 40 else "red")

        icerik = Text()
        icerik.append(f"{b['toplam']}\n", style=f"bold {renk}")
        icerik.append(f"TP {b['tp']}  STOP {b['stop']}  ", style="white")
        icerik.append(f"%{b['wr']:.0f}", style=f"bold {wr_renk}")

        panels.append(Panel(icerik, title=f"[bold {renk}]{baslik}[/]",
                            border_style=renk, padding=(0, 1)))
    t.add_row(*panels)
    return t


# ── setup kartı (CANLI ADAY AKIŞI) ──────────────────────────────────────────

def _kart_metni(satir) -> Text:
    short = satir.taraf == "Short"
    yon_renk = _C["short"] if short else _C["long"]
    yon_ok = "▼" if short else "▲"
    kat_renk = _KAT_RENK.get(satir.kategori, "white")
    kaynak = getattr(satir, "kaynak", "Scanner")
    b_renk = _BUCKET_RENK.get(kaynak, "white")

    t = Text()
    # satır 1: ok + sembol + tf + [kategori]
    t.append(f"{yon_ok} ", style=f"bold {yon_renk}")
    t.append(f"{satir.symbol:<12}", style="bold white")
    t.append(f" {satir.interval:<4}", style="cyan")
    t.append(f"  [{satir.kategori.upper()}]", style=f"bold {kat_renk}")
    # satır 2: kaynak | pattern | yön
    pat = satir.pattern or ""
    kaynak_satir = (f"{kaynak} | {pat} | {satir.taraf}" if pat
                    else f"{kaynak} | {satir.taraf}")
    t.append(f"\n  {kaynak_satir}", style=f"dim {b_renk}")
    # satır 3: entry / sl / tp / rr
    if satir.giris:
        rr_txt = f"  R/R {satir.rr:.1f}" if satir.rr else ""
        t.append(
            f"\n  Entry {_fmt(satir.giris)}  SL {_fmt(satir.stop)}"
            f"  TP {_fmt(satir.hedef)}{rr_txt}",
            style="white")
    else:
        t.append("\n  —", style="bright_black")
    return t


def _aday_kartlari(satirlar) -> list[Panel]:
    """Trade ve Watch satirlarından kart listesi üretir."""
    adaylar = [s for s in satirlar if s.kategori in ("Trade", "Watch")]
    adaylar.sort(key=lambda s: (0 if s.kategori == "Trade" else 1, -s.guven))
    panels = []
    for s in adaylar[:12]:
        kat_renk = _KAT_RENK.get(s.kategori, "white")
        panels.append(Panel(_kart_metni(s), border_style=kat_renk, padding=(0, 1)))
    if not panels:
        panels.append(Panel(Text("setup yok", style="bright_black"),
                            border_style="bright_black", padding=(0, 1)))
    return panels


# ── sonuç bildirimleri ───────────────────────────────────────────────────────

def _bildirim_satiri(sembol, interval, kaynak_pat, durum, giris, stop, hedef,
                     zaman, renk) -> Panel:
    t = Text()
    t.append(f"{sembol:<12}", style="bold white")
    t.append(f" {interval:<4}", style="cyan")
    t.append(f"  [{durum}]", style=f"bold {renk}")
    t.append(f"\n  {kaynak_pat}", style="dim cyan")
    t.append(
        f"\n  Entry {_fmt(giris)}  SL {_fmt(stop)}  TP {_fmt(hedef)}",
        style="white")
    if zaman:
        t.append(f"\n  {zaman}", style="bright_black")
    return Panel(t, border_style=renk, padding=(0, 1))


def _bildirimler(portfoy, defter=None) -> list[Panel]:
    """Kapanan kayıtları (Defter'den) veya portföy pozisyonlarını gösterir."""
    panels = []
    durum_renk = {
        "TP": "green", "STOP": "red",
        "Expired": "yellow", "Manuel": "bright_black",
    }

    if defter is not None:
        # Defter'deki son 8 kapanan kayıt (en yeni önce)
        kapanan = [k for k in defter.kayitlar if not k.aktif][-8:][::-1]
        for k in kapanan:
            renk = durum_renk.get(k.durum, "bright_black")
            durum_txt = (f"{k.durum} {k.r_sonuc:+.1f}R"
                         if k.durum in ("TP", "STOP") else k.durum.upper())
            pat = k.pattern or ""
            kaynak = getattr(k, "kaynak", "Scanner")
            kaynak_pat = (f"{kaynak} | {pat} | {k.taraf}" if pat
                          else f"{kaynak} | {k.taraf}")
            panels.append(_bildirim_satiri(
                k.sembol, k.interval, kaynak_pat, durum_txt,
                k.giris, k.stop, k.hedef,
                k.kapanis_zaman[:16] if k.kapanis_zaman else "",
                renk))
        if not kapanan and portfoy is None:
            panels.append(Panel(Text("kapanan kayıt yok", style="bright_black"),
                                border_style="bright_black", padding=(0, 1)))
        return panels

    # portföy varsa oradan
    if portfoy and getattr(portfoy, "pozisyonlar", None):
        for p in portfoy.pozisyonlar[-8:][::-1]:
            renk = durum_renk.get(p.durum, "bright_black")
            rtxt = (f" {p.r_sonuc:+.1f}R" if p.durum in ("TP", "STOP")
                    and p.r_sonuc else "")
            durum_txt = f"{p.durum}{rtxt}"
            panels.append(_bildirim_satiri(
                p.sembol, p.interval,
                f"{getattr(p, 'yon', '')} pozisyon",
                durum_txt, p.giris, p.stop if hasattr(p, "stop") else None,
                p.hedef if hasattr(p, "hedef") else None,
                (p.kapanis_zaman or "")[:16], renk))
    if not panels:
        panels.append(Panel(Text("sonuç yok", style="bright_black"),
                            border_style="bright_black", padding=(0, 1)))
    return panels


# ── ana pano ─────────────────────────────────────────────────────────────────

def pano_olustur(rapor, defter=None, portfoy=None, bilgi: str = "") -> Group:
    """Dashboard bileşenlerini Group olarak döndürür (Live veya doğrudan yazdırma için)."""
    simdi = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    ozet = rapor.ozet

    # ── başlık ──
    baslik_satir = Text()
    baslik_satir.append("TerminalMiraz", style="bold cyan")
    baslik_satir.append("  ·  CANLI TARAMA PANELİ", style="bold white")
    baslik_satir.append(f"  {simdi}", style="bright_black")
    if bilgi:
        baslik_satir.append(f"\n{bilgi}", style="bright_black")

    baslik_paneli = Panel(baslik_satir, border_style="cyan", padding=(0, 1))

    # ── günlük özet şeridi ──
    ozet_txt = Text()
    ozet_txt.append(f"Tarama: {ozet['toplam']}  ", style="bright_black")
    ozet_txt.append(f"Aday {ozet['Trade']}  ", style="bold green")
    ozet_txt.append(f"İzle {ozet['Watch']}  ", style="yellow")
    ozet_txt.append(f"Atla {ozet['Skip']}  ", style="bright_black")
    ozet_txt.append(f"Elenen {ozet['Elenen']}", style="red")

    # ── 4 metrik kutusu ──
    buckets = (defter.ozet().get("buckets", {}) if defter is not None
               else {"Scanner": {"tp": 0, "stop": 0, "toplam": 0, "wr": 0.0},
                     "Filtered": {"tp": 0, "stop": 0, "toplam": 0, "wr": 0.0},
                     "Harmonic": {"tp": 0, "stop": 0, "toplam": 0, "wr": 0.0},
                     "Late": {"tp": 0, "stop": 0, "toplam": 0, "wr": 0.0}})
    metrik_t = _metrik_tablosu(buckets)

    metrik_panel = Panel(
        Group(ozet_txt, metrik_t),
        title="[bold cyan]MOBIL KOMUTA METRİKLERİ[/]",
        border_style="bright_black", padding=(0, 1))

    # ── 2 sütunlu ana gövde ──
    satirlar = sorted(rapor.satirlar, key=lambda r: r._sira)

    # sol: CANLI ADAY AKIŞI
    kart_listesi = _aday_kartlari(satirlar)
    sol_baslik = Text("CANLI ADAY AKIŞI", style="bold cyan")
    sol_icerik = Group(sol_baslik, *kart_listesi)
    sol_panel = Panel(sol_icerik, border_style="bright_black", padding=(0, 1))

    # sağ: SONUÇ BİLDİRİMLERİ + portföy özeti
    bildirim_listesi = _bildirimler(portfoy, defter)
    sag_baslik = Text("SONUÇ BİLDİRİMLERİ", style="bold cyan")

    pf_satir = Text()
    if portfoy is not None:
        toplam_r = getattr(portfoy, "toplam_r", 0.0) or 0.0
        wr = getattr(portfoy, "win_rate", 0.0) or 0.0
        aktif = len(getattr(portfoy, "aktif", []))
        r_renk = "green" if toplam_r >= 0 else "red"
        pf_satir.append("Portföy: ", style="bright_black")
        pf_satir.append(f"{toplam_r:+.1f}R  ", style=f"bold {r_renk}")
        pf_satir.append(f"WR %{wr:.0f}  ", style="white")
        pf_satir.append(f"Aktif {aktif}", style="cyan")
    elif defter is not None:
        d_ozet = defter.ozet()
        r_renk = "green" if d_ozet["toplam_r"] >= 0 else "red"
        pf_satir.append("Defter: ", style="bright_black")
        pf_satir.append(f"{d_ozet['toplam_r']:+.1f}R  ", style=f"bold {r_renk}")
        pf_satir.append(f"WR %{d_ozet['wr']:.0f}  ", style="white")
        pf_satir.append(f"Aktif {d_ozet['aktif']}", style="cyan")

    sag_icerik = Group(sag_baslik, pf_satir, *bildirim_listesi)
    sag_panel = Panel(sag_icerik, border_style="bright_black", padding=(0, 1))

    # sütunları yan yana koy
    ana_tablo = Table.grid(expand=True, padding=(0, 0))
    ana_tablo.add_column(ratio=3)
    ana_tablo.add_column(ratio=2)
    ana_tablo.add_row(sol_panel, sag_panel)

    return Group(baslik_paneli, metrik_panel, ana_tablo)


def pano_yazdir(rapor, defter=None, portfoy=None, bilgi: str = "") -> None:
    """Panoyu terminale bir kez yazar."""
    console.print(pano_olustur(rapor, defter=defter, portfoy=portfoy, bilgi=bilgi))
