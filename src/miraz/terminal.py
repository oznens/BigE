"""TerminalMiraz görsel paneli — @tradermiraz'ın terminal arayüzünün kopyası.

@tradermiraz'ın terminalMiraz'ı koyu temalı bir komuta panelidir: üstte günlük
özet + komuta metrikleri (Scanner / Filtered / Harmonik / Late result), solda
CANLI ADAY AKIŞI (her setup bir kart: skor donut'u, Long/Short, SL—ENTRY—TP
kaydırıcısı, R/R), sağda SONUÇ BİLDİRİMLERİ. Bu modül aynı düzeni bir PNG olarak
üretir — radar taramasını ve (varsa) portföyü görselleştirir.

Kullanım:
    from miraz.terminal import panel_ciz
    from miraz.radar import radar_tara
    rapor = radar_tara(["BTCUSDT", "ETHUSDT"], ["4h"], taraf="her")
    panel_ciz(rapor, dosya="terminal.png")

CLI: python backtest/terminal.py --semboller BTCUSDT ETHUSDT --tf 4h --taraf her
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, Wedge


# terminalMiraz koyu tema paleti (dashboard görselinden örneklendi)
_T = {
    "bg": "#0a121d",          # ana arka plan (koyu lacivert)
    "panel": "#0f1b2a",       # kart/panel zemini
    "panel2": "#13212f",      # ikincil panel
    "kenar": "#1d3346",       # ince kenar çizgisi
    "metin": "#dce6f0",       # ana metin
    "soluk": "#6f8194",       # ikincil metin
    "vurgu": "#1fb6a8",       # turkuaz vurgu (başlıklar)
    "yesil": "#26d07c",       # TP / Long / pozitif
    "kirmizi": "#ef4d56",     # STOP / Short / negatif
    "sari": "#f5b942",        # Watch / uyarı
    "mavi": "#3da5ff",        # nötr / bilgi
    "mor": "#9b7bd4",
}

# kategori → renk + ikon
_KAT = {
    "Trade":  ("#26d07c", "ADAY"),
    "Watch":  ("#f5b942", "İZLE"),
    "Skip":   ("#6f8194", "ATLA"),
    "Elenen": ("#ef4d56", "ELENEN"),
}

# kalite → 0..100 skor (donut için) ve renk
_KALITE_SKOR = {"A+": 95, "A": 85, "B": 70, "C": 55, "D": 40}


def _fmt(v: float | None) -> str:
    """Fiyatı büyüklüğe göre formatlar (kuruş-altı coinler için hassas)."""
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


def _yuvarlak_kutu(ax, x, y, w, h, fc, ec=None, lw=0, r=0.02, z=1, alpha=1.0):
    """Yuvarlak köşeli panel/kart çizer (eksen koordinatında)."""
    box = FancyBboxPatch(
        (x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}",
        facecolor=fc, edgecolor=ec or fc, linewidth=lw, zorder=z, alpha=alpha,
        mutation_aspect=1.0)
    ax.add_patch(box)
    return box


def _donut(ax, cx, cy, skor, renk, rp=0.026):
    """Kalite skoru için halka (donut) — terminalMiraz kart skoru."""
    # arka halka
    ax.add_patch(Wedge((cx, cy), rp, 0, 360, width=rp * 0.32,
                       facecolor=_T["kenar"], edgecolor="none", zorder=5))
    # dolu yay (skor oranı)
    ac = 90
    ax.add_patch(Wedge((cx, cy), rp, ac, ac - 360 * (skor / 100.0),
                       width=rp * 0.32, facecolor=renk, edgecolor="none",
                       zorder=6))
    ax.text(cx, cy, f"{skor:.0f}", color=_T["metin"], fontsize=9,
            ha="center", va="center", fontweight="bold", zorder=7)


def _slider(ax, x, y, w, satir):
    """SL — ENTRY — TP yatay kaydırıcısı (terminalMiraz kart alt şeridi)."""
    sl, giris, tp = satir.stop, satir.giris, satir.hedef
    short = satir.taraf == "Short"
    # çizgi
    ax.plot([x, x + w], [y, y], color=_T["kenar"], lw=2.2, zorder=4,
            solid_capstyle="round")
    if giris is None:
        ax.text(x + w / 2, y, "plan yok", color=_T["soluk"], fontsize=7.5,
                ha="center", va="center", zorder=6)
        return
    # değerleri uçlara yerleştir: long → SL solda(düşük), TP sağda(yüksek)
    #                              short → SL solda(yüksek), TP sağda(düşük)
    sol_lbl, sol_val = ("SL", sl)
    sag_lbl, sag_val = ("TP", tp)
    # noktalar
    ax.scatter([x], [y], s=42, color=_T["kirmizi"], zorder=6,
               edgecolors="none")             # SL
    ax.scatter([x + w / 2], [y], s=46, color=_T["metin"], zorder=6,
               edgecolors="none")             # ENTRY
    ax.scatter([x + w], [y], s=42, color=_T["yesil"], zorder=6,
               edgecolors="none")             # TP
    # etiketler (üstte ad, altta değer)
    for px, lbl, val, c in [
            (x, sol_lbl, sol_val, _T["kirmizi"]),
            (x + w / 2, "ENTRY", giris, _T["metin"]),
            (x + w, sag_lbl, sag_val, _T["yesil"])]:
        ha = "left" if px == x else ("right" if px == x + w else "center")
        ax.text(px, y + 0.013, lbl, color=_T["soluk"], fontsize=6.5,
                ha=ha, va="bottom", zorder=6)
        ax.text(px, y - 0.013, _fmt(val), color=c, fontsize=7,
                ha=ha, va="top", zorder=6, fontweight="bold")


def _kart(ax, x, y, w, h, satir):
    """Tek setup kartı — terminalMiraz CANLI ADAY AKIŞI kartı."""
    renk, _ = _KAT.get(satir.kategori, ("#6f8194", "?"))
    short = satir.taraf == "Short"
    yon_renk = _T["kirmizi"] if short else _T["yesil"]
    skor = _KALITE_SKOR.get(satir.kalite, satir.guven or 40)

    _yuvarlak_kutu(ax, x, y, w, h, _T["panel"], ec=_T["kenar"], lw=1.0,
                   r=0.012, z=2)
    # sol renk şeridi (kategori)
    ax.add_patch(Rectangle((x, y), 0.004, h, facecolor=renk,
                           edgecolor="none", zorder=3))
    # skor donut'u
    _donut(ax, x + 0.028, y + h - 0.045, skor, renk)
    # sembol + TF
    ax.text(x + 0.062, y + h - 0.028, satir.symbol, color=_T["metin"],
            fontsize=11, fontweight="bold", va="center", zorder=5)
    ax.text(x + 0.062, y + h - 0.052, f"{satir.interval}", color=_T["soluk"],
            fontsize=8, va="center", zorder=5)
    # yön rozeti (sağ üst)
    ok = "▼ Short" if short else "▲ Long"
    ax.text(x + w - 0.012, y + h - 0.028, ok, color=yon_renk, fontsize=8.5,
            ha="right", va="center", fontweight="bold", zorder=5)
    # kategori rozeti (sağ, ikinci satır)
    ax.text(x + w - 0.012, y + h - 0.052, satir.kategori.upper(), color=renk,
            fontsize=7.5, ha="right", va="center", fontweight="bold", zorder=5)
    # not satırı
    notu = satir.not_ or "—"
    if len(notu) > 38:
        notu = notu[:37] + "…"
    ax.text(x + 0.012, y + 0.052, notu, color=_T["soluk"], fontsize=7,
            va="center", zorder=5)
    # R/R rozeti
    rr_txt = f"R/R {satir.rr:.1f}" if satir.rr is not None else "R/R —"
    ax.text(x + w - 0.012, y + 0.052, rr_txt, color=_T["mavi"], fontsize=7.5,
            ha="right", va="center", fontweight="bold", zorder=5)
    # SL—ENTRY—TP kaydırıcısı (alt)
    _slider(ax, x + 0.04, y + 0.024, w - 0.09, satir)


def _metrik_karti(ax, x, y, w, h, baslik, deger, alt, renk):
    """Üst komuta metriği kutusu (Scanner / Filtered / Harmonik / Late)."""
    _yuvarlak_kutu(ax, x, y, w, h, _T["panel2"], ec=_T["kenar"], lw=1.0,
                   r=0.012, z=2)
    ax.add_patch(Rectangle((x, y), 0.004, h, facecolor=renk,
                           edgecolor="none", zorder=3))
    ax.text(x + 0.016, y + h - 0.02, baslik, color=renk, fontsize=8.5,
            va="center", fontweight="bold", zorder=4)
    ax.text(x + 0.016, y + 0.028, str(deger), color=_T["metin"], fontsize=20,
            va="center", fontweight="bold", zorder=4)
    ax.text(x + w - 0.014, y + 0.026, alt, color=_T["soluk"], fontsize=7.5,
            ha="right", va="center", zorder=4)


def _ozet_panel(ax, x, y, w, h, baslik, deger, renk):
    """Sağ üst büyük sayaç (AKTİF / SONUÇ / BUGÜN)."""
    _yuvarlak_kutu(ax, x, y, w, h, _T["panel2"], ec=_T["kenar"], lw=1.0,
                   r=0.014, z=2)
    ax.add_patch(Rectangle((x, y + h - 0.006), w, 0.006, facecolor=renk,
                           edgecolor="none", zorder=3))
    ax.text(x + 0.012, y + h - 0.02, baslik, color=_T["soluk"], fontsize=8,
            va="center", zorder=4)
    ax.text(x + w - 0.012, y + h / 2 - 0.012, str(deger), color=renk,
            fontsize=23, ha="right", va="center", fontweight="bold", zorder=4)


def panel_ciz(rapor, portfoy=None, dosya: str | Path = "terminal.png",
              baslik: str = "TerminalMiraz") -> str:
    """Radar raporunu (ve varsa portföyü) terminalMiraz panosu olarak çizer."""
    sat = sorted(rapor.satirlar, key=lambda r: r._sira)
    ozet = rapor.ozet

    # --- günlük / portföy istatistikleri ---
    if portfoy is not None:
        ist = portfoy.istatistik() if hasattr(portfoy, "istatistik") else {}
        aktif_n = len([p for p in getattr(portfoy, "pozisyonlar", [])
                       if p.durum in ("Açık", "Bekliyor")])
        tp_n = len([p for p in getattr(portfoy, "pozisyonlar", [])
                    if p.durum == "TP"])
        stop_n = len([p for p in getattr(portfoy, "pozisyonlar", [])
                      if p.durum == "STOP"])
        toplam_r = sum(p.r_sonuc or 0 for p in getattr(portfoy, "pozisyonlar", [])
                       if p.durum in ("TP", "STOP"))
    else:
        aktif_n, tp_n, stop_n, toplam_r = ozet["Trade"], 0, 0, 0.0

    # tuval
    fig = plt.figure(figsize=(15.5, 9.6), dpi=130)
    fig.patch.set_facecolor(_T["bg"])
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_facecolor(_T["bg"])

    # ---------------- başlık ----------------
    ax.text(0.018, 0.965, baslik, color=_T["metin"], fontsize=23,
            fontweight="bold", va="center")
    ax.text(0.019, 0.935, "canlı tarama · setup akışı · sonuç merkezi",
            color=_T["vurgu"], fontsize=9.5, va="center")
    simdi = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    ax.text(0.982, 0.965, simdi, color=_T["soluk"], fontsize=9,
            ha="right", va="center")
    # günlük özet şeridi
    ozet_txt = (f"Bugün: {ozet['toplam']} tarama   "
                f"●  Aday {ozet['Trade']}   ●  İzle {ozet['Watch']}   "
                f"●  Atla {ozet['Skip']}   ●  Elenen {ozet['Elenen']}")
    ax.text(0.019, 0.905, ozet_txt, color=_T["soluk"], fontsize=9, va="center")

    # ---------------- üst komuta metrikleri (sol alan genişliği) ----------------
    y_m, h_m = 0.80, 0.075
    metr = [
        ("SCANNER", ozet["Trade"], "ADAY", _T["yesil"]),
        ("FILTERED", ozet["Watch"], "İZLE", _T["sari"]),
        ("SKIP", ozet["Skip"], "zayıf", _T["soluk"]),
        ("ELENEN", ozet["Elenen"], "HTF", _T["kirmizi"]),
    ]
    x0, gap = 0.018, 0.012
    wm = (0.64 - 3 * gap) / 4
    for i, (b, d, a, c) in enumerate(metr):
        _metrik_karti(ax, x0 + i * (wm + gap), y_m, wm, h_m, b, d, a, c)

    # ---------------- sol: CANLI ADAY AKIŞI ----------------
    ax.text(0.018, 0.755, "CANLI ADAY AKIŞI", color=_T["vurgu"], fontsize=11,
            fontweight="bold", va="center")
    ax.text(0.018, 0.733, "panoya düşen aktif setup kartları", color=_T["soluk"],
            fontsize=8, va="center")

    # kart grid'i (2 sütun)
    kart_alani_x, kart_alani_w = 0.018, 0.64
    kart_w = (kart_alani_w - 0.014) / 2
    kart_h = 0.135
    y_bas = 0.70
    satir_gap = 0.016
    # en çok 8 kart (4 satır × 2)
    gosterilecek = sat[:8]
    for i, s in enumerate(gosterilecek):
        col = i % 2
        row = i // 2
        kx = kart_alani_x + col * (kart_w + 0.014)
        ky = y_bas - (row + 1) * kart_h - row * satir_gap
        _kart(ax, kx, ky, kart_w, kart_h, s)
    if not gosterilecek:
        ax.text(kart_alani_x + kart_alani_w / 2, 0.45, "setup yok",
                color=_T["soluk"], fontsize=12, ha="center", va="center")

    # ---------------- sağ: SONUÇ BİLDİRİMLERİ + sayaçlar ----------------
    sx = 0.69
    sw = 0.292
    # büyük sayaçlar
    _ozet_panel(ax, sx, 0.80, (sw - 0.012) / 2, 0.075, "AKTİF",
                aktif_n, _T["mavi"])
    _ozet_panel(ax, sx + (sw + 0.012) / 2, 0.80, (sw - 0.012) / 2, 0.075,
                "SONUÇ", tp_n + stop_n, _T["vurgu"])
    # bugün TP/STOP/R mini
    _yuvarlak_kutu(ax, sx, 0.715, sw, 0.07, _T["panel2"], ec=_T["kenar"],
                   lw=1.0, r=0.012, z=2)
    for j, (lbl, val, c) in enumerate([
            ("TP", tp_n, _T["yesil"]), ("STOP", stop_n, _T["kirmizi"]),
            (f"{'+' if toplam_r>=0 else ''}{toplam_r:.1f}R", "", _T["sari"])]):
        cx = sx + 0.02 + j * (sw / 3)
        ax.text(cx, 0.762, lbl, color=_T["soluk"], fontsize=8, va="center")
        if val != "":
            ax.text(cx, 0.735, str(val), color=c, fontsize=15,
                    va="center", fontweight="bold")
        else:
            ax.text(cx, 0.74, lbl, color=c, fontsize=14, va="center",
                    fontweight="bold")

    # başlık
    ax.text(sx, 0.685, "SONUÇ BİLDİRİMLERİ", color=_T["vurgu"], fontsize=11,
            fontweight="bold", va="center")
    ax.text(sx, 0.663, "TP / STOP / giriş olmayan kapanışlar", color=_T["soluk"],
            fontsize=8, va="center")

    # bildirim listesi: portföyden kapalı/aktif, yoksa radar Trade/Watch
    bildirimler = _bildirimler(portfoy, sat)
    by = 0.63
    bh = 0.066
    for i, (sym, tf, durum, alt, c) in enumerate(bildirimler[:7]):
        yy = by - (i + 1) * bh - i * 0.008
        _yuvarlak_kutu(ax, sx, yy, sw, bh, _T["panel"], ec=_T["kenar"],
                       lw=0.8, r=0.01, z=2)
        ax.add_patch(Rectangle((sx, yy), 0.004, bh, facecolor=c,
                               edgecolor="none", zorder=3))
        ax.text(sx + 0.016, yy + bh - 0.022, sym, color=_T["metin"],
                fontsize=9.5, fontweight="bold", va="center", zorder=4)
        ax.text(sx + 0.016, yy + 0.018, alt, color=_T["soluk"], fontsize=7,
                va="center", zorder=4)
        ax.text(sx + sw - 0.014, yy + bh - 0.022, durum, color=c, fontsize=8.5,
                ha="right", va="center", fontweight="bold", zorder=4)
        ax.text(sx + sw - 0.014, yy + 0.018, tf, color=_T["soluk"],
                fontsize=7.5, ha="right", va="center", zorder=4)

    # alt bilgi
    ax.text(0.018, 0.018, "miraz sistemi · saf price action + harmonik · "
            "TP = 1R (terminalMiraz)", color=_T["soluk"], fontsize=7.5,
            va="center")

    fig.savefig(dosya, facecolor=_T["bg"])
    plt.close(fig)
    return str(dosya)


def _bildirimler(portfoy, sat) -> list:
    """Sağ panel bildirim satırları üretir (portföy varsa ondan, yoksa radar)."""
    out = []
    if portfoy is not None and getattr(portfoy, "pozisyonlar", None):
        durum_renk = {"TP": _T["yesil"], "STOP": _T["kirmizi"],
                      "Açık": _T["mavi"], "Bekliyor": _T["soluk"]}
        for p in portfoy.pozisyonlar[-12:][::-1]:
            d = p.durum
            c = durum_renk.get(d, _T["soluk"])
            rtxt = (f"{p.r_sonuc:+.1f}R" if d in ("TP", "STOP")
                    and p.r_sonuc is not None else p.yon)
            alt = f"{p.yon} · giriş {_fmt(p.giris)} · {rtxt}"
            out.append((p.sembol, p.interval, d.upper(), alt, c))
        return out
    # portföy yoksa: radar Trade/Watch sinyalleri "ENTRY BEKLİYOR" gibi
    for s in sat:
        if s.kategori not in ("Trade", "Watch"):
            continue
        c = _KAT.get(s.kategori, ("#6f8194",))[0]
        durum = "ADAY" if s.kategori == "Trade" else "İZLE"
        rr = f"R/R {s.rr:.1f}" if s.rr is not None else ""
        alt = f"{s.taraf} · {s.kalite} · giriş {_fmt(s.giris)} {rr}"
        out.append((s.symbol, s.interval, durum, alt, c))
    return out
