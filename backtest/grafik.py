"""Backtest sonuçları için equity curve grafiği."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from bige.backtest import BacktestKonfig, calistir
from bige.indikatorler import mtf_trend_ekle
from bige.strateji import StratejiParams
from bige.veri import yukle


def ciz(
    sembol: str,
    aralik: str,
    p: StratejiParams,
    k: BacktestKonfig,
    cikti_yol: Path,
    baslik_eki: str = "",
):
    df = yukle(sembol, aralik)
    # 4h için MTF (1D) trend kolonu ekle
    if aralik == "4h":
        try:
            df_1d = yukle(sembol, "1d")
            df = mtf_trend_ekle(df, df_1d, ema_p=20)
        except Exception:
            pass
    sonuc = calistir(df, p, k)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 9), sharex=True, gridspec_kw={"height_ratios": [2, 1]})

    # Üst: bakiye + fiyat
    bakiye = sonuc.bakiye_serisi
    bh_baslangic = df["close"].iloc[0]
    bh = df["close"] / bh_baslangic * k.baslangic_bakiyesi

    ax1.plot(bakiye.index, bakiye.values, label="BigE strateji", color="#1f77b4", linewidth=2)
    ax1.plot(bh.index, bh.values, label="Buy & hold", color="#aaaaaa", linewidth=1, linestyle="--")
    ax1.axhline(k.baslangic_bakiyesi, color="black", linewidth=0.5, alpha=0.3)
    ax1.set_ylabel("Bakiye (USDT)")
    ax1.set_title(f"{sembol} {aralik} — BigE strateji vs Buy & hold {baslik_eki}")
    ax1.legend(loc="upper left")
    ax1.grid(True, alpha=0.3)

    # Alt: drawdown
    zirve = bakiye.cummax()
    dd = (bakiye - zirve) / zirve * 100
    ax2.fill_between(dd.index, dd.values, 0, color="red", alpha=0.3)
    ax2.set_ylabel("Drawdown (%)")
    ax2.set_xlabel("Tarih")
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))

    # Trade işaretleri
    for t in sonuc.trades:
        renk = "green" if t.pnl_net > 0 else "red"
        marker = "^" if t.yon.name == "LONG" else "v"
        if t.giris_indeks < len(bakiye):
            ax1.scatter(bakiye.index[t.giris_indeks], bakiye.iloc[t.giris_indeks],
                        color=renk, marker=marker, s=20, alpha=0.5, zorder=5)

    ist = sonuc.istatistikler()
    son_bakiye = float(bakiye.iloc[-1])
    getiri = (son_bakiye / k.baslangic_bakiyesi - 1) * 100
    bh_getiri = (df["close"].iloc[-1] / df["close"].iloc[0] - 1) * 100
    metin = (
        f"Trade: {ist['trade_sayisi']}  |  "
        f"WR: {ist['win_rate']:.0%}  |  "
        f"PF: {ist['profit_factor']}  |  "
        f"Sharpe: {ist['sharpe']}  |  "
        f"Max DD: {ist['max_drawdown']:.1%}\n"
        f"Strateji getiri: %{getiri:+.1f}  |  Buy&hold: %{bh_getiri:+.1f}"
    )
    fig.text(0.5, 0.01, metin, ha="center", fontsize=10, family="monospace")

    plt.tight_layout(rect=[0, 0.04, 1, 1])
    cikti_yol.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(cikti_yol, dpi=110, bbox_inches="tight")
    plt.close()
    return cikti_yol


def main():
    k = BacktestKonfig(baslangic_bakiyesi=10_000, komisyon_bps=4, slippage_bps=2)
    p_best = StratejiParams(
        max_candle_age_after_cross=1,
        tdi_angle_min=1.0,
        near_extreme_margin=5.0,
        trend_filtresi_aktif=True,
        trend_ema_period=200,
        sl_mode="atr",
        sl_atr_multiplier=2.0,
        allow_short=False,
    )

    cikti_klasor = Path("backtest/results")
    for sembol in ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]:
        for aralik in ["4h", "1d"]:
            try:
                yol = ciz(
                    sembol, aralik, p_best, k,
                    cikti_klasor / f"equity_{sembol}_{aralik}.png",
                    baslik_eki=" (long-only, trend+ATR)",
                )
                print(f"  ✓ {yol}")
            except Exception as e:
                print(f"  ✗ {sembol} {aralik}: {e}")


if __name__ == "__main__":
    main()
