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

# tradermiraz renk paleti → matplotlib renkleri
_RENK_HEX = {
    "Mavi": "#1f77ff",
    "Yeşil": "#2ca02c",
    "Turuncu": "#ff7f0e",
    "Mor": "#9467bd",
    "Kırmızı": "#d62728",
}


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
