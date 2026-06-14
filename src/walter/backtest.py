"""Vektörize backtest motoru + performans metrikleri.

Gerçekçilik kuralları:
  - Sinyal 1 bar GECİKMEYLE uygulanır: bar t'deki pozisyon, bar t-1'in kapanışında
    bilinen bilgiyle belirlenir → look-ahead bias yok.
  - İşlem maliyeti: pozisyon değişiminin mutlak değeri × komisyon (tek yön).
  - Getiriler basit (close-to-close) bar getirisi üzerinden hesaplanır.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

BAR_YIL = 24 * 365  # saatlik veri için yıllık bar sayısı


@dataclass
class BacktestSonuc:
    getiriler: pd.Series       # stratejinin bar getirileri (maliyet sonrası)
    equity: pd.Series          # kümülatif equity eğrisi (1.0'dan başlar)
    pozisyon: pd.Series        # uygulanan (gecikmeli) pozisyon
    metrikler: dict            # özet metrikler

    def ozet(self) -> str:
        m = self.metrikler
        satirlar = [
            f"  Dönem            : {m['baslangic']} → {m['bitis']}",
            f"  Bar sayısı       : {m['bar_sayisi']:,}",
            f"  Toplam getiri    : {m['toplam_getiri']:+.1%}",
            f"  CAGR             : {m['cagr']:+.1%}",
            f"  Yıllık vol       : {m['yillik_vol']:.1%}",
            f"  Sharpe           : {m['sharpe']:.2f}",
            f"  Sortino          : {m['sortino']:.2f}",
            f"  Max drawdown     : {m['max_drawdown']:.1%}",
            f"  Calmar           : {m['calmar']:.2f}",
            f"  Kazanan bar %    : {m['kazanan_bar']:.1%}",
            f"  İşlem sayısı     : {m['islem_sayisi']:,}",
            f"  Piyasada kalma % : {m['piyasada_kalma']:.1%}",
        ]
        return "\n".join(satirlar)


def _metrikler(strat_ret: pd.Series, equity: pd.Series, pozisyon: pd.Series,
               islem: pd.Series) -> dict:
    n = len(strat_ret)
    toplam = equity.iloc[-1] - 1.0
    yil = n / BAR_YIL
    cagr = equity.iloc[-1] ** (1 / yil) - 1.0 if yil > 0 else np.nan

    mean = strat_ret.mean()
    std = strat_ret.std()
    yillik_vol = std * np.sqrt(BAR_YIL)
    sharpe = (mean / std * np.sqrt(BAR_YIL)) if std > 0 else 0.0

    negatif = strat_ret[strat_ret < 0]
    downside = negatif.std()
    sortino = (mean / downside * np.sqrt(BAR_YIL)) if downside > 0 else 0.0

    run_max = equity.cummax()
    drawdown = equity / run_max - 1.0
    max_dd = drawdown.min()
    calmar = (cagr / abs(max_dd)) if max_dd < 0 else np.nan

    aktif = strat_ret[pozisyon > 0]
    kazanan = (aktif > 0).mean() if len(aktif) else np.nan

    return {
        "baslangic": str(equity.index[0].date()),
        "bitis": str(equity.index[-1].date()),
        "bar_sayisi": n,
        "toplam_getiri": toplam,
        "cagr": cagr,
        "yillik_vol": yillik_vol,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": max_dd,
        "calmar": calmar,
        "kazanan_bar": kazanan,
        "islem_sayisi": int((islem > 0).sum()),
        "piyasada_kalma": (pozisyon > 0).mean(),
    }


def calistir(df: pd.DataFrame, pozisyon_kolonu: str = "pozisyon",
             komisyon: float = 0.0006) -> BacktestSonuc:
    """Backtest'i çalıştırır.

    Parametreler
    ------------
    df : 'close' ve `pozisyon_kolonu` içeren DataFrame (strateji.uret çıktısı).
    komisyon : İşlem başına tek yön maliyet (varsayılan 6 bps ~ taker fee).

    Döndürür : BacktestSonuc
    """
    close = df["close"]
    bar_ret = close.pct_change().fillna(0.0)

    # 1 bar gecikme: bugünkü getiriye dünden bilinen pozisyon uygulanır
    poz = df[pozisyon_kolonu].shift(1).fillna(0.0)

    # İşlem maliyeti: pozisyon değişimi kadar
    islem = poz.diff().abs().fillna(poz.abs())
    maliyet = islem * komisyon

    strat_ret = poz * bar_ret - maliyet
    equity = (1.0 + strat_ret).cumprod()

    metrikler = _metrikler(strat_ret, equity, poz, islem)
    return BacktestSonuc(strat_ret, equity, poz, metrikler)


def buy_hold(df: pd.DataFrame) -> BacktestSonuc:
    """Karşılaştırma için al-tut (her zaman %100 long, maliyetsiz)."""
    close = df["close"]
    bar_ret = close.pct_change().fillna(0.0)
    poz = pd.Series(1.0, index=df.index)
    equity = (1.0 + bar_ret).cumprod()
    metrikler = _metrikler(bar_ret, equity, poz, pd.Series(0.0, index=df.index))
    return BacktestSonuc(bar_ret, equity, poz, metrikler)
