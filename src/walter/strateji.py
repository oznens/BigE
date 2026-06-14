"""Session Trend stratejisi — sinyal üretimi.

Mantık (hepsi kural-tabanlı, ölçülebilir):

  1. TREND REJİMİ: hızlı EMA > yavaş EMA ise yukarı rejim (long'a izin).
     BTC'de trend-following uzun vadede al-tut'tan üstün.

  2. ZAMAN EDGE'i: "Monday Asia Open" etkisi. Pazar 19:00 ET → Pazartesi
     öğleden sonrası BTC trend getirileri belirgin pozitif. Bu pencerede
     pozisyon tam ağırlık; dışında azaltılmış ağırlık (choppy saatlerden kaç).

  3. VOLATİLİTE HEDEFLEME: pozisyon boyutu = hedef_vol / gerçekleşen_vol,
     `max_kaldirac` ile sınırlı. Sabit risk → kaldıraçla intihar yok.

Çıktı: her bar için hedef pozisyon (0..max_kaldirac arası, yalnızca long v1).
Sinyaller backtest'te 1 bar gecikmeyle uygulanır (look-ahead yok).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import indikatorler as ind
from .zaman import ET, saat_ozellikleri


@dataclass
class SessionTrendParams:
    # Ablation ile seçilmiş varsayılanlar (bkz. notlar/bulgular.md):
    # Trend (EMA 24/168) + zaman filtresi → Sharpe ~0.85, al-tut'un yarı drawdown'ı.
    ema_hizli: int = 24            # hızlı EMA periyodu (saat)
    ema_yavas: int = 168          # yavaş EMA periyodu (saat) — en sağlam/az işlem
    vol_periyot: int = 24         # realize vol penceresi (saat)
    hedef_vol: float = 0.20       # yıllık hedef volatilite (%20)
    max_kaldirac: float = 2.0     # maksimum pozisyon çarpanı
    rebalans_bant: float = 0.10   # vol-hedef pozisyonu ancak bu kadar değişince güncellenir (churn kes)
    vol_hedef_acik: bool = False  # True: düşük drawdown + kaldıraç modu; False: ayrık 0/1 trend
    seans_disi_agirlik: float = 0.35  # edge penceresi dışında ağırlık (0-1)
    momentum_acik: bool = False   # ablation: momentum filtresi churn ekleyip Sharpe'ı düşürdü → kapalı
    mom_periyot: int = 24         # momentum teyit penceresi
    mom_esik: float = 0.0         # momentum bu eşiğin üstündeyse long teyidi
    # "Monday Asia Open" edge penceresi: ET'de hafta-saati aralığı.
    # Pazar 19:00 ET = (6*24 + 19) = 163 ... Pazartesi 18:00 ET = (0*24 + 18) = 18
    # Hafta Pazartesi 00:00'da başladığı için pencere haftanın sonuna sarıyor.
    edge_baslangic_hafta_saati: int = 163  # Pazar 19:00 ET
    edge_bitis_hafta_saati: int = 18       # Pazartesi 18:00 ET (ertesi gün)


def _bantli(seri: pd.Series, bant: float) -> pd.Series:
    """Histerez: pozisyonu yalnızca `bant` kadar değişince günceller.

    Sürekli mikro-rebalansı (saat başı vol-hedef gürültüsü) keser → komisyon
    katliamını engeller. Ablation'da işlem sayısını 13k'dan yüzlere düşürdü.
    """
    vals = seri.to_numpy()
    out = np.zeros_like(vals)
    son = 0.0
    for i, v in enumerate(vals):
        if np.isnan(v):
            v = 0.0
        if abs(v - son) >= bant:
            son = v
        out[i] = son
    return pd.Series(out, index=seri.index)


def _edge_maskesi(idx: pd.DatetimeIndex, p: SessionTrendParams) -> pd.Series:
    """Edge penceresi içinde mi? (haftanın sonuna saran aralığı doğru ele alır)."""
    ozk = saat_ozellikleri(idx, tz=ET)
    hs = ozk["hafta_saati"]
    bas, bit = p.edge_baslangic_hafta_saati, p.edge_bitis_hafta_saati
    if bas <= bit:
        return (hs >= bas) & (hs <= bit)
    # sarmalı aralık: [bas, 168) veya [0, bit]
    return (hs >= bas) | (hs <= bit)


def uret(df: pd.DataFrame, p: SessionTrendParams | None = None) -> pd.DataFrame:
    """OHLCV'den hedef pozisyon serisini üretir.

    Döndürür: orijinal df + ['ema_hizli','ema_yavas','rv','rejim',
    'edge','mom','pozisyon'] kolonları.
    """
    if p is None:
        p = SessionTrendParams()
    out = df.copy()
    close = out["close"]

    out["ema_hizli"] = ind.ema(close, p.ema_hizli)
    out["ema_yavas"] = ind.ema(close, p.ema_yavas)
    out["rv"] = ind.realized_vol(close, p.vol_periyot)
    out["mom"] = ind.momentum(close, p.mom_periyot)

    # 1) Trend rejimi: hızlı EMA yavaş EMA üstünde (+ opsiyonel momentum teyidi)
    rejim = out["ema_hizli"] > out["ema_yavas"]
    if p.momentum_acik:
        rejim = rejim & (out["mom"] > p.mom_esik)
    out["rejim"] = rejim.astype(int)

    # 2) Zaman edge'i
    edge = _edge_maskesi(out.index, p)
    out["edge"] = edge.astype(int)
    seans_agirlik = np.where(edge, 1.0, p.seans_disi_agirlik)

    # 3) Volatilite hedefleme (opsiyonel risk-ayar kolu)
    if p.vol_hedef_acik:
        vol_carpan = (p.hedef_vol / out["rv"]).clip(upper=p.max_kaldirac).fillna(0.0)
        poz = rejim.astype(float) * seans_agirlik * vol_carpan
        poz = _bantli(poz.clip(lower=0.0, upper=p.max_kaldirac), p.rebalans_bant)
    else:
        # Ayrık trend: pozisyon 0 veya seans ağırlığı → çok az işlem, maliyete dayanıklı
        poz = rejim.astype(float) * seans_agirlik

    out["pozisyon"] = poz.clip(lower=0.0, upper=p.max_kaldirac).fillna(0.0)
    return out
