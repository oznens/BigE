"""Setup görselleştirme — mumlar + renkli kutular + harmonik XABCD + seviyeler.

@tradermiraz tarzı grafik: fiyat aksiyonu üstüne renkli destek/direnç kutuları,
harmonik pattern'in XABCD bacakları ve entry/SL/TP çizgileri.

Kullanım:
    from miraz import grafik
    grafik.setup_ciz(df, pattern, kutular, dosya="setup.png")
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # başsız (headless) ortam — dosyaya yazar
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Rectangle

from .harmonik import HarmonikSonuc
from .kutular import Kutu
from .senaryo import Senaryo
from .yol_haritasi import YolHaritasi

# tradermiraz renk paleti → matplotlib renkleri
_RENK_HEX = {
    "Mavi": "#1f77ff",
    "Yeşil": "#2ca02c",
    "Turuncu": "#ff7f0e",
    "Mor": "#9467bd",
    "Kırmızı": "#d62728",
}

# ---------------------------------------------------------------------------
# TradingView teması (Miraz grafik stili)
# ---------------------------------------------------------------------------
_TV = {
    "bg": "#ffffff",
    "up": "#000000",          # yükselen mum (siyah gövde)
    "down": "#f7931e",        # düşen mum (turuncu gövde)
    "grid": "#e6e8ec",
    "eksen": "#787b86",
    "metin": "#131722",
    "destek": "#4caf50",      # yeşil destek kutusu
    "direnc_fc": "#c9b3e8",   # mor direnç kutusu dolgu
    "direnc_ec": "#7e57c2",   # mor direnç kenar
    "iptal": "#f23645",       # kırmızı iptal çizgisi
    "fitil": "#ff9800",       # turuncu fitil
    "fiyat_tag": "#131722",   # güncel fiyat etiketi
}
_TR_AY = ["Oca", "Şub", "Mar", "Nis", "May", "Haz",
          "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]


def _ondalik(v: float) -> int:
    """Büyüklüğe göre ondalık hane sayısı (kuruş-altı coinlerde hassasiyet)."""
    a = abs(v)
    if a >= 1:
        return 2
    if a >= 0.1:
        return 4
    if a >= 0.01:
        return 5
    if a >= 0.0001:
        return 6
    return 8


def _tr_sayi(v: float, ondalik: int | None = None) -> str:
    """Türkçe sayı formatı: 1722.69 → '1.722,69'. ondalik=None → otomatik."""
    if ondalik is None:
        ondalik = _ondalik(v)
    s = f"{v:,.{ondalik}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


class _TurkceTarih(mdates.DateFormatter):
    """Türkçe ay kısaltmalı tarih biçimi (gün + ay başında ay adı)."""

    def __init__(self):
        super().__init__("%d")

    def __call__(self, x, pos=0):
        dt = mdates.num2date(x)
        if dt.day <= 3:
            return f"{dt.day} {_TR_AY[dt.month - 1]}"
        return f"{dt.day}"


def _fiyat_etiketi(ax, y: float, renk: str, metin: str | None = None,
                   ondalik: int = 2) -> None:
    """Sağ eksen üzerine TradingView tarzı renkli fiyat etiketi koyar."""
    metin = metin if metin is not None else _tr_sayi(y, ondalik)
    ax.annotate(
        metin, xy=(1.0, y), xycoords=ax.get_yaxis_transform(),
        xytext=(7, 0), textcoords="offset points",
        va="center", ha="left", fontsize=8, color="white", fontweight="bold",
        clip_on=False, zorder=12,
        bbox=dict(boxstyle="square,pad=0.3", fc=renk, ec="none"))


def _harmonik_ciz(ax, df, pattern, ofset, x):
    """Harmonik XABCD'yi TAO tarzı kırmızı gölgeli polygon olarak çizer."""
    import numpy as np
    from matplotlib.patches import Polygon
    idxler = [pattern.X_idx, pattern.A_idx, pattern.B_idx,
              pattern.C_idx, pattern.D_idx]
    fiyatlar = [pattern.X, pattern.A, pattern.B, pattern.C, pattern.D]
    pts = []
    for gi, fy in zip(idxler, fiyatlar):
        yerel = gi - ofset
        if 0 <= yerel < len(x):
            pts.append((x[yerel], fy))
    if len(pts) < 5:
        return
    # TradingView XABCD stili: iki üçgen (X-A-B) ve (B-C-D), B'de birleşir
    for ucgen in (pts[0:3], pts[2:5]):
        ax.add_patch(Polygon(ucgen, closed=True, facecolor="#f23645",
                             alpha=0.13, edgecolor="none", zorder=2))
    # X-A-B-C-D kırılım çizgisi
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color="#f23645", linewidth=1.2, alpha=0.7, zorder=2)


def _olusan_harmonik_ciz(ax, df, oh, ofset, x, x1, bar_w):
    """Oluşmakta olan harmoniği çizer: X-A-B-C kesintisiz, C→D projeksiyonu
    kesikli, D'de PRZ kutusu (Miraz'ın TAO'da D'yi ileriye çizmesi gibi)."""
    from matplotlib.patches import Polygon, Rectangle
    abcd_idx = [oh.X_idx, oh.A_idx, oh.B_idx, oh.C_idx]
    abcd_fy = [oh.X, oh.A, oh.B, oh.C]
    pts = []
    for gi, fy in zip(abcd_idx, abcd_fy):
        yerel = gi - ofset
        if 0 <= yerel < len(x):
            pts.append((x[yerel], fy))
    if len(pts) < 3:
        return
    xs, ys = zip(*pts)
    # X-A-B-C kesintisiz kırmızı çizgi
    ax.plot(xs, ys, color="#f23645", linewidth=1.3, zorder=5)
    # Projekte D (gelecekte, sağda)
    xD = x1 + bar_w * 7
    ax.plot([xs[-1], xD], [ys[-1], oh.D], color="#f23645", linewidth=1.3,
            linestyle="--", zorder=5)
    # TradingView XABCD stili: iki üçgen (X-A-B) ve (B-C-D'projeksiyon)
    tum = list(pts) + [(xD, oh.D)]
    if len(tum) >= 5:
        for ucgen in (tum[0:3], tum[2:5]):
            ax.add_patch(Polygon(ucgen, closed=True, facecolor="#f23645",
                                 alpha=0.11, edgecolor="none", zorder=2))
    # PRZ kutusu (projeksiyon belirsizliği) + D işareti
    ax.add_patch(Rectangle((xD - bar_w * 2, oh.prz_alt), bar_w * 5,
                           oh.prz_ust - oh.prz_alt, facecolor="#f23645",
                           alpha=0.18, edgecolor="#f23645", linewidth=1.0,
                           zorder=3))
    ax.scatter([xD], [oh.D], s=70, color="#f23645", marker="o", zorder=6)
    ax.annotate(f"D? ({oh.isim})\nPRZ {_tr_sayi(oh.prz_alt)}–{_tr_sayi(oh.prz_ust)}",
                (xD, oh.D), textcoords="offset points", xytext=(6, 0),
                ha="left", va="center", fontsize=7.5, color="#c0392b",
                fontweight="bold", zorder=7)


def _proje_oku_ciz(ax, noktalar):
    """TAO tarzı dalgalı projeksiyon oku — sıralı (x,y) noktalarından geçer,
    ok ucu son segmentin yönünü (yukarı/aşağı) gösterir."""
    import numpy as np
    xs_all, ys_all = [], []
    for i in range(len(noktalar) - 1):
        x0, y0 = noktalar[i]
        x1, y1 = noktalar[i + 1]
        t = np.linspace(0, 1, 45)
        taban = y0 + (y1 - y0) * t
        genlik = abs(y1 - y0) * 0.13 + abs(y0) * 0.003
        dalga = genlik * np.sin(t * np.pi * 3)
        xs_all.extend(x0 + (x1 - x0) * t)
        ys_all.extend(taban + dalga)
    ax.plot(xs_all, ys_all, color="#131722", linewidth=1.4, alpha=0.85, zorder=7)
    ax.annotate("", xy=(xs_all[-1], ys_all[-1]),
                xytext=(xs_all[-4], ys_all[-4]),
                arrowprops=dict(arrowstyle="-|>", color="#131722", lw=1.8),
                zorder=7)


def _mum_ciz_tv(ax, df: pd.DataFrame) -> None:
    """TradingView stili mum: yükselen siyah, düşen turuncu."""
    x = mdates.date2num(df.index.to_pydatetime())
    genislik = (x[1] - x[0]) * 0.62 if len(x) > 1 else 0.02
    for xi, (_, satir) in zip(x, df.iterrows()):
        o, h, l, c = satir["open"], satir["high"], satir["low"], satir["close"]
        renk = _TV["up"] if c >= o else _TV["down"]
        ax.plot([xi, xi], [l, h], color=renk, linewidth=0.7, zorder=2)
        ax.add_patch(Rectangle(
            (xi - genislik / 2, min(o, c)), genislik, abs(c - o) or h * 1e-5,
            facecolor=renk, edgecolor=renk, linewidth=0.5, zorder=3))


def _mum_ciz(ax, df: pd.DataFrame) -> None:
    """Basit mum grafiği (candlestick)."""
    x = mdates.date2num(df.index.to_pydatetime())
    genislik = (x[1] - x[0]) * 0.7 if len(x) > 1 else 0.02
    for xi, (_, satir) in zip(x, df.iterrows()):
        o, h, l, c = satir["open"], satir["high"], satir["low"], satir["close"]
        renk = "#26a69a" if c >= o else "#ef5350"
        ax.plot([xi, xi], [l, h], color=renk, linewidth=0.6, zorder=1)
        ax.add_patch(Rectangle(
            (xi - genislik / 2, min(o, c)), genislik, abs(c - o) or h * 1e-5,
            facecolor=renk, edgecolor=renk, linewidth=0.4, zorder=2))


def setup_ciz(
    df: pd.DataFrame,
    pattern: HarmonikSonuc | None,
    kutular: list[Kutu],
    dosya: str | Path,
    baslik: str = "",
    son_n: int = 220,
) -> Path:
    """Setup'ı çizip PNG olarak kaydeder.

    df       : OHLCV DataFrame (UTC indeksli)
    pattern  : çizilecek harmonik pattern (None ise sadece kutular)
    kutular  : çizilecek renkli kutular
    dosya    : çıktı yolu
    baslik   : grafik başlığı
    son_n    : son kaç mum gösterilsin
    """
    tam_uzunluk = len(df)
    ofset = max(0, tam_uzunluk - son_n)   # kırpma offseti (global → yerel)
    df = df.iloc[ofset:]
    x = mdates.date2num(df.index.to_pydatetime())
    x0, x1 = x[0], x[-1]

    fig, ax = plt.subplots(figsize=(15, 8))
    _mum_ciz(ax, df)

    # --- Renkli kutular (yatay bantlar) ---
    for k in kutular:
        if k.ust < df["low"].min() * 0.9 or k.alt > df["high"].max() * 1.1:
            continue  # görünür alanın çok dışı
        renk = _RENK_HEX.get(k.renk, "#888888")
        ax.add_patch(Rectangle(
            (x0, k.alt), x1 - x0, k.ust - k.alt,
            facecolor=renk, alpha=0.13, edgecolor=renk, linewidth=1.0,
            zorder=0))
        ax.text(x1, k.merkez, f" {k.renk} {k.tip} (güç {k.guc:.0f})",
                va="center", ha="left", fontsize=8, color=renk)

    # --- Harmonik XABCD ---
    if pattern is not None:
        idxler = [pattern.X_idx, pattern.A_idx, pattern.B_idx,
                  pattern.C_idx, pattern.D_idx]
        fiyatlar = [pattern.X, pattern.A, pattern.B, pattern.C, pattern.D]
        etiketler = ["X", "A", "B", "C", "D"]

        # Pattern indeksleri orijinal (kırpılmamış) df'ye ait → ofset ile yerele çevir
        px, py = [], []
        for gi, fy, et in zip(idxler, fiyatlar, etiketler):
            yerel = gi - ofset
            if 0 <= yerel < len(x):
                px.append(x[yerel]); py.append(fy)
                ax.scatter(x[yerel], fy, s=45, color="black", zorder=5)
                ax.annotate(f"{et}\n{_tr_sayi(fy)}", (x[yerel], fy),
                            textcoords="offset points", xytext=(0, 10),
                            ha="center", fontsize=9, fontweight="bold")
        if len(px) >= 2:
            ax.plot(px, py, color="black", linewidth=1.4,
                    linestyle="--", zorder=4,
                    label=f"{pattern.yon} {pattern.isim} (kalite {pattern.kalite:.0f})")

        # --- Entry / SL / TP çizgileri ---
        for seviye, etiket, renk in [
            (pattern.entry, "Entry", "#000000"),
            (pattern.sl, "SL", "#d62728"),
            (pattern.tp1, "TP1", "#2ca02c"),
            (pattern.tp2, "TP2", "#1f77ff"),
        ]:
            ax.axhline(seviye, color=renk, linewidth=1.0, linestyle=":",
                       alpha=0.8, zorder=3)
            ax.text(x0, seviye, f"{etiket} {_tr_sayi(seviye)} ", va="center",
                    ha="right", fontsize=8, color=renk, fontweight="bold")

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    ax.set_title(baslik or "Setup", fontsize=13, fontweight="bold")
    ax.set_ylabel("Fiyat")
    ax.grid(True, alpha=0.15)
    if pattern is not None:
        ax.legend(loc="upper left", fontsize=9)
    fig.autofmt_xdate()
    fig.tight_layout()

    dosya = Path(dosya)
    dosya.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(dosya, dpi=130)
    plt.close(fig)
    return dosya


def senaryo_ciz(
    df: pd.DataFrame,
    senaryo: Senaryo,
    dosya: str | Path,
    baslik: str = "",
    son_n: int = 260,
    symbol: str = "Ethereum / TetherUS",
    interval: str = "4sa",
    borsa: str = "Binance",
    indikator: bool = False,
) -> Path:
    """Senaryo planını @tradermiraz / TradingView stilinde grafiğe çizer.

    Beyaz tema, siyah/turuncu mumlar, sağ fiyat ekseni + renkli fiyat
    etiketleri, yeşil destek kutusu, mor hedef kutusu, kırmızı iptal çizgisi.

    indikator=True ise @finansalTRader katmanı eklenir: fiyat üzerine Fib
    golden pocket (0.618–0.786) çizgileri + altına RSI paneli.
    """
    tam_uzunluk = len(df)
    ofset = max(0, tam_uzunluk - son_n)
    dfg = df.iloc[ofset:]
    x = mdates.date2num(dfg.index.to_pydatetime())
    x0, x1 = x[0], x[-1]
    bar_w = (x[1] - x[0]) if len(x) > 1 else 0.16
    x_sag = x1 + bar_w * 28   # sağda gelecek projeksiyonu (Miraz gibi)

    ax_rsi = None
    if indikator:
        fig, (ax, ax_rsi) = plt.subplots(
            2, 1, figsize=(16, 9.6), sharex=True,
            gridspec_kw={"height_ratios": [4.2, 1], "hspace": 0.06})
        ax_rsi.set_facecolor(_TV["bg"])
    else:
        fig, ax = plt.subplots(figsize=(16, 8.5))
    fig.patch.set_facecolor(_TV["bg"])
    ax.set_facecolor(_TV["bg"])

    _mum_ciz_tv(ax, dfg)

    # --- Destek tepki bölgesi (yeşil kutu) ---
    if senaryo.bolge_alt is not None and senaryo.bolge_ust is not None:
        ax.add_patch(Rectangle(
            (x0, senaryo.bolge_alt), x_sag - x0,
            senaryo.bolge_ust - senaryo.bolge_alt,
            facecolor=_TV["destek"], alpha=0.32,
            edgecolor=_TV["destek"], linewidth=1.2, zorder=1))
        _fiyat_etiketi(ax, senaryo.bolge_ust, _TV["destek"])
        _fiyat_etiketi(ax, senaryo.bolge_alt, _TV["destek"])

    # --- Hedef direnç kutusu (mor) ---
    h = senaryo.hedef_kutu
    if h is not None:
        ax.add_patch(Rectangle(
            (x1 - bar_w * 6, h.alt), x_sag - (x1 - bar_w * 6), h.ust - h.alt,
            facecolor=_TV["direnc_fc"], alpha=0.55,
            edgecolor=_TV["direnc_ec"], linewidth=1.2, zorder=1))
        _fiyat_etiketi(ax, h.ust, _TV["direnc_ec"])
        _fiyat_etiketi(ax, h.alt, _TV["direnc_ec"])

    # --- Kritik kapanış çizgisi (kırmızı) ---
    if senaryo.kritik_seviye is not None:
        ax.axhline(senaryo.kritik_seviye, color=_TV["iptal"], linewidth=1.4,
                   linestyle="-", zorder=4)
        _fiyat_etiketi(ax, senaryo.kritik_seviye, _TV["iptal"])
        ax.text(x0 + bar_w, senaryo.kritik_seviye,
                f"{_tr_sayi(senaryo.kritik_seviye)} altı KAPANIŞ = İPTAL",
                va="bottom", ha="left", fontsize=8.5, color=_TV["iptal"],
                fontweight="bold", zorder=5)

    # --- Fitil toleransı (turuncu kesikli) ---
    if senaryo.fitil_seviye is not None:
        ax.axhline(senaryo.fitil_seviye, color=_TV["fitil"], linewidth=1.0,
                   linestyle=(0, (5, 3)), zorder=4)
        ax.text(x0 + bar_w, senaryo.fitil_seviye,
                f"fitil OK {_tr_sayi(senaryo.fitil_seviye)}",
                va="bottom", ha="left", fontsize=7.5, color=_TV["fitil"],
                zorder=5)

    # --- Yükselen trend çizgisi (ince siyah) ---
    # Sadece çizginin kendi anchor barından itibaren çiz (geriye taşma yok).
    t = senaryo.trend
    if t is not None:
        basla = max(ofset, t.bar0)
        gx0 = mdates.date2num(df.index[basla].to_pydatetime())
        y0, y1 = t.deger(basla), t.deger(tam_uzunluk - 1)
        egim = (y1 - y0) / (x1 - gx0) if x1 > gx0 else 0
        ax.plot([gx0, x_sag], [y0, y1 + egim * (x_sag - x1)],
                color="#131722", linewidth=1.2, linestyle="-", zorder=4)

    # --- Mavi daire (harmonik D ∩ destek = en yüksek güvenli giriş) ---
    if senaryo.mavi_daire is not None:
        if senaryo.mavi_daire_idx is not None and senaryo.mavi_daire_idx >= ofset:
            mx = mdates.date2num(df.index[senaryo.mavi_daire_idx].to_pydatetime())
        else:
            mx = x1
        ax.scatter([mx], [senaryo.mavi_daire], s=520, facecolor="#26c6da",
                   edgecolor="#0097a7", linewidth=1.6, alpha=0.65, zorder=6)
        _fiyat_etiketi(ax, senaryo.mavi_daire, "#0097a7")

    # --- Oluşmakta olan harmonik (X-A-B-C + kesikli D projeksiyonu + PRZ) ---
    oh = getattr(senaryo, "olusan", None)
    if oh is not None:
        try:
            _olusan_harmonik_ciz(ax, df, oh, ofset, x, x1, bar_w)
        except Exception:
            pass

    # --- @finansalTRader katmanı: Fib golden pocket çizgileri ---
    if indikator and getattr(senaryo, "fib", None) is not None:
        fr = senaryo.fib
        # golden pocket bandı (0.618–0.705/0.786)
        gp_alt, gp_ust = sorted((fr.golden_alt, fr.golden_ust))
        ax.add_patch(Rectangle(
            (x0, gp_alt), x_sag - x0, gp_ust - gp_alt,
            facecolor="#9b59b6", alpha=0.13, edgecolor="none", zorder=1))
        for sv in fr.seviyeler:
            if sv.oran in (0.5, 0.618, 0.786):
                ax.axhline(sv.fiyat, color="#8e44ad", linewidth=0.9,
                           linestyle=(0, (4, 3)), alpha=0.7, zorder=3)
                ax.text(x0 + bar_w, sv.fiyat,
                        f"Fib {sv.oran:.3f}".rstrip("0").rstrip("."),
                        va="bottom", ha="left", fontsize=7,
                        color="#8e44ad", zorder=5)
        _fiyat_etiketi(ax, fr.golden_alt, "#8e44ad")

    # --- Güncel fiyat etiketi (koyu) ---
    ax.axhline(senaryo.fiyat, color=_TV["fiyat_tag"], linewidth=0.7,
               linestyle=(0, (1, 2)), alpha=0.7, zorder=4)
    _fiyat_etiketi(ax, senaryo.fiyat, _TV["fiyat_tag"])

    # --- Eksenler / grid (TradingView görünümü) ---
    ax.set_xlim(x0 - bar_w, x_sag)
    ax.yaxis.tick_right()
    ax.yaxis.set_label_position("right")
    ax.tick_params(axis="y", colors=_TV["eksen"], labelsize=8, length=0)
    ax.tick_params(axis="x", colors=_TV["eksen"], labelsize=8, length=0)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, p: _tr_sayi(v)))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(_TurkceTarih())
    ax.grid(True, color=_TV["grid"], linewidth=0.8, zorder=0)
    for kenar in ("top", "left", "bottom", "right"):
        ax.spines[kenar].set_visible(False)

    # --- RSI paneli (@finansalTRader katmanı) ---
    if ax_rsi is not None:
        from .indikator import rsi as _rsi_f
        r = _rsi_f(df["close"]).iloc[ofset:]
        ax_rsi.plot(x, r.to_numpy(), color="#8e44ad", linewidth=1.2, zorder=3)
        for sv, dur in [(70, "#f23645"), (50, "#b0b3b8"), (30, "#26a69a")]:
            ax_rsi.axhline(sv, color=dur, linewidth=0.8,
                           linestyle=(0, (4, 3)), alpha=0.7, zorder=2)
        ax_rsi.axhspan(70, 100, color="#f23645", alpha=0.06, zorder=1)
        ax_rsi.axhspan(0, 30, color="#26a69a", alpha=0.06, zorder=1)
        son_rsi = float(r.iloc[-1]) if pd.notna(r.iloc[-1]) else 50
        ax_rsi.scatter([x1], [son_rsi], s=24, color="#8e44ad", zorder=4)
        ax_rsi.text(x_sag, son_rsi, f" RSI {son_rsi:.0f}", va="center",
                    ha="left", fontsize=8, color="#8e44ad", fontweight="bold")
        ax_rsi.set_ylim(0, 100)
        ax_rsi.set_yticks([30, 50, 70])
        ax_rsi.set_xlim(x0 - bar_w, x_sag)
        ax_rsi.yaxis.tick_right()
        ax_rsi.tick_params(axis="y", colors=_TV["eksen"], labelsize=7, length=0)
        ax_rsi.tick_params(axis="x", colors=_TV["eksen"], labelsize=8, length=0)
        ax_rsi.xaxis.set_major_locator(mdates.AutoDateLocator())
        ax_rsi.xaxis.set_major_formatter(_TurkceTarih())
        ax_rsi.grid(True, color=_TV["grid"], linewidth=0.6, zorder=0)
        for kenar in ("top", "left", "bottom", "right"):
            ax_rsi.spines[kenar].set_visible(False)
        ax_rsi.text(0.006, 0.88, "RSI (14)", transform=ax_rsi.transAxes,
                    fontsize=8, color="#8e44ad", fontweight="bold", va="top")
        plt.setp(ax.get_xticklabels(), visible=False)

    # --- Üst-sol başlık satırı (sembol + OHLC) ---
    son = dfg.iloc[-1]
    onceki = dfg.iloc[-2] if len(dfg) > 1 else son
    degisim = son["close"] - onceki["close"]
    yuzde = degisim / onceki["close"] * 100 if onceki["close"] else 0
    fark_renk = _TV["up"] if degisim >= 0 else _TV["down"]
    ax.text(0.006, 1.025, f"{symbol} · {interval} · {borsa}",
            transform=ax.transAxes, fontsize=10.5, fontweight="bold",
            color=_TV["metin"], va="bottom", ha="left")
    ax.text(0.006, 0.995,
            f"A{_tr_sayi(son['open'])}  Y{_tr_sayi(son['high'])}  "
            f"D{_tr_sayi(son['low'])}  K{_tr_sayi(son['close'])}   "
            f"{'+' if degisim>=0 else ''}{_tr_sayi(degisim)} "
            f"({'+' if degisim>=0 else ''}{_tr_sayi(yuzde, 2)}%)",
            transform=ax.transAxes, fontsize=8.5, color=fark_renk,
            va="top", ha="left")
    ax.text(1.0, 1.025, "USDT", transform=ax.transAxes, fontsize=8.5,
            color=_TV["eksen"], va="bottom", ha="right")

    # --- Alt-sol kaynak / logo ---
    fig.text(0.012, 0.022, "₸ TradingView", fontsize=11, fontweight="bold",
             color=_TV["metin"])
    if baslik:
        fig.text(0.012, 0.975, baslik, fontsize=8.5, color=_TV["eksen"],
                 style="italic")

    fig.subplots_adjust(left=0.01, right=0.93, top=0.9, bottom=0.07)

    dosya = Path(dosya)
    dosya.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(dosya, dpi=140, facecolor=_TV["bg"])
    plt.close(fig)
    return dosya


def yol_haritasi_ciz(
    df: pd.DataFrame,
    yh: YolHaritasi,
    dosya: str | Path,
    baslik: str = "",
    son_n: int = 300,
    symbol: str = "Bittensor / TetherUS",
    interval: str = "1G",
    borsa: str = "Binance",
) -> Path:
    """Çoklu-bölge yol haritasını TAO tarzı çizer: LONG (yeşil) + SHORT (mor)
    bölgeleri, mavi daireler ve güncel fiyat — hepsi tek grafikte."""
    tam = len(df)
    ofset = max(0, tam - son_n)
    dfg = df.iloc[ofset:]
    x = mdates.date2num(dfg.index.to_pydatetime())
    x0, x1 = x[0], x[-1]
    bar_w = (x[1] - x[0]) if len(x) > 1 else 0.16
    x_sag = x1 + bar_w * 30

    fig, ax = plt.subplots(figsize=(16, 8.5))
    fig.patch.set_facecolor(_TV["bg"])
    ax.set_facecolor(_TV["bg"])
    _mum_ciz_tv(ax, dfg)

    # Kırmızı gölgeli harmonik patternler (TAO tarzı)
    for p in (yh.patternler or []):
        _harmonik_ciz(ax, df, p, ofset, x)

    # Oluşmakta olan harmonik (D projeksiyonu — TAO'da olduğu gibi)
    if yh.olusan is not None:
        _olusan_harmonik_ciz(ax, df, yh.olusan, ofset, x, x1, bar_w)

    for b in yh.bolgeler:
        if b.rol == "SHORT":
            fc, ec = _TV["direnc_fc"], _TV["direnc_ec"]
        else:
            fc, ec = _TV["destek"], _TV["destek"]
        ax.add_patch(Rectangle(
            (x0, b.alt), x_sag - x0, b.ust - b.alt,
            facecolor=fc, alpha=0.30, edgecolor=ec, linewidth=1.1, zorder=1))
        _fiyat_etiketi(ax, b.ust, ec)
        _fiyat_etiketi(ax, b.alt, ec)
        ax.text(x0 + bar_w, b.merkez, f"{b.rol} · {b.renk} (güç {b.guc:.0f})",
                va="center", ha="left", fontsize=8, color=ec,
                fontweight="bold", zorder=5)
        if b.mavi_daire is not None:
            ax.scatter([x1], [b.mavi_daire], s=480, facecolor="#26c6da",
                       edgecolor="#0097a7", linewidth=1.6, alpha=0.65, zorder=6)

    ax.axhline(yh.fiyat, color=_TV["fiyat_tag"], linewidth=0.8,
               linestyle=(0, (1, 2)), alpha=0.75, zorder=4)
    _fiyat_etiketi(ax, yh.fiyat, _TV["fiyat_tag"])

    # TAO tarzı dalgalı projeksiyon oku — yöne göre
    oh = yh.olusan
    if oh is not None:
        # Fiyat önce PRZ'ye (D) gider, sonra dönüş yönüne hareket eder.
        xD = x1 + bar_w * 7
        if oh.yon == "Bullish":
            # D aşağıda → in, sonra YUKARI dön (en yakın direnç üstü hedef)
            ust = [b.merkez for b in yh.bolgeler if b.merkez > yh.fiyat]
            rev = min(ust) if ust else yh.fiyat * 1.06
            stop = oh.prz_alt * 0.995          # Bull: stop PRZ ALTI
        else:
            # D yukarıda → çık, sonra AŞAĞI dön (en yakın destek altı hedef)
            alt = [b.merkez for b in yh.bolgeler if b.merkez < yh.fiyat]
            rev = max(alt) if alt else yh.fiyat * 0.94
            stop = oh.prz_ust * 1.005          # Bear: stop PRZ ÜSTÜ
        _proje_oku_ciz(ax, [(x1 + bar_w * 2, yh.fiyat), (xD, oh.D),
                            (xD + bar_w * 12, rev)])
        # Stop çizgisi (PRZ'nin ters tarafı)
        ax.plot([xD - bar_w * 2, xD + bar_w * 3], [stop, stop],
                color="#d62728", linewidth=1.3, linestyle=(0, (4, 2)), zorder=6)
        ax.annotate(f"stop {stop:,.0f}", (xD + bar_w * 3, stop),
                    textcoords="offset points", xytext=(4, 0), ha="left",
                    va="center", fontsize=7.5, color="#d62728",
                    fontweight="bold", zorder=7)
    elif yh.hedef is not None:
        _proje_oku_ciz(ax, [(x1 + bar_w * 3, yh.fiyat),
                            (x1 + bar_w * 22, yh.hedef)])

    ax.set_xlim(x0 - bar_w, x_sag)
    ax.yaxis.tick_right()
    ax.tick_params(axis="y", colors=_TV["eksen"], labelsize=8, length=0)
    ax.tick_params(axis="x", colors=_TV["eksen"], labelsize=8, length=0)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, p: _tr_sayi(v)))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(_TurkceTarih())
    ax.grid(True, color=_TV["grid"], linewidth=0.8, zorder=0)
    for kenar in ("top", "left", "bottom", "right"):
        ax.spines[kenar].set_visible(False)

    ax.text(0.006, 1.025, f"{symbol} · {interval} · {borsa}",
            transform=ax.transAxes, fontsize=10.5, fontweight="bold",
            color=_TV["metin"], va="bottom", ha="left")
    ax.text(1.0, 1.025, "USDT", transform=ax.transAxes, fontsize=8.5,
            color=_TV["eksen"], va="bottom", ha="right")
    fig.text(0.012, 0.022, "₸ TradingView", fontsize=11, fontweight="bold",
             color=_TV["metin"])
    if baslik:
        fig.text(0.012, 0.975, baslik, fontsize=8.5, color=_TV["eksen"],
                 style="italic")
    fig.subplots_adjust(left=0.01, right=0.93, top=0.9, bottom=0.07)

    dosya = Path(dosya)
    dosya.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(dosya, dpi=140, facecolor=_TV["bg"])
    plt.close(fig)
    return dosya
