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


def _tr_sayi(v: float, ondalik: int = 2) -> str:
    """Türkçe sayı formatı: 1722.69 → '1.722,69'."""
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
                ax.annotate(f"{et}\n{fy:,.2f}", (x[yerel], fy),
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
            ax.text(x0, seviye, f"{etiket} {seviye:,.2f} ", va="center",
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
) -> Path:
    """Senaryo planını @tradermiraz / TradingView stilinde grafiğe çizer.

    Beyaz tema, siyah/turuncu mumlar, sağ fiyat ekseni + renkli fiyat
    etiketleri, yeşil destek kutusu, mor hedef kutusu, kırmızı iptal çizgisi.
    """
    tam_uzunluk = len(df)
    ofset = max(0, tam_uzunluk - son_n)
    dfg = df.iloc[ofset:]
    x = mdates.date2num(dfg.index.to_pydatetime())
    x0, x1 = x[0], x[-1]
    bar_w = (x[1] - x[0]) if len(x) > 1 else 0.16
    x_sag = x1 + bar_w * 28   # sağda gelecek projeksiyonu (Miraz gibi)

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
            f"({'+' if degisim>=0 else ''}{_tr_sayi(yuzde)}%)",
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
