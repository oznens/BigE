"""Mum-bazlı backtest motoru.

Big E modeli için basit ama doğru bir simülatör:
- Bir mumun KAPANIŞINDA sinyal üretilir
- Sıradaki mumun AÇILIŞINDA giriş/çıkış olur (look-ahead bias yok)
- Stop loss intraday tetiklenebilir (high/low bazlı)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import pandas as pd

from .indikatorler import tum_indikatorler
from .strateji import (
    Pozisyon,
    StratejiParams,
    Trade,
    Yon,
    cikis_sinyali,
    giris_sinyali,
    stop_loss_hesapla,
)


@dataclass
class BacktestKonfig:
    baslangic_bakiyesi: float = 10_000.0
    komisyon_bps: float = 7.0   # 7 bps = %0.07 (Binance spot taker üst sınır)
    slippage_bps: float = 2.0
    leverage: float = 1.0       # futures için 1x'te bırakıyoruz; risk_pct ile boyutluyoruz


@dataclass
class BacktestSonuc:
    trades: list[Trade] = field(default_factory=list)
    bakiye_serisi: pd.Series | None = None

    def istatistikler(self) -> dict:
        if not self.trades:
            return {"trade_sayisi": 0}
        pnls = np.array([t.pnl_net for t in self.trades])
        kazananlar = pnls[pnls > 0]
        kaybedenler = pnls[pnls <= 0]
        toplam = float(pnls.sum())
        wr = len(kazananlar) / len(pnls)
        ort_kazanc = float(kazananlar.mean()) if len(kazananlar) else 0.0
        ort_kayip = float(kaybedenler.mean()) if len(kaybedenler) else 0.0
        pf = float(kazananlar.sum() / -kaybedenler.sum()) if len(kaybedenler) and kaybedenler.sum() < 0 else np.inf

        bs = self.bakiye_serisi
        max_dd = 0.0
        sharpe = 0.0
        if bs is not None and len(bs):
            zirve = bs.cummax()
            dd = (bs - zirve) / zirve
            max_dd = float(dd.min())
            # Bar bazlı getiriler üzerinden Sharpe (yıllıklandırılmış)
            getiriler = bs.pct_change().dropna()
            if len(getiriler) > 1 and getiriler.std() > 0:
                # 4h mum varsayımı: yılda ~2190 bar (365 × 6)
                bar_per_yil = 2190
                sharpe = float(getiriler.mean() / getiriler.std() * np.sqrt(bar_per_yil))

        return {
            "trade_sayisi": int(len(pnls)),
            "kazanan": int(len(kazananlar)),
            "kaybeden": int(len(kaybedenler)),
            "win_rate": round(wr, 4),
            "toplam_pnl": round(toplam, 2),
            "ort_kazanc": round(ort_kazanc, 2),
            "ort_kayip": round(ort_kayip, 2),
            "profit_factor": round(pf, 3) if np.isfinite(pf) else None,
            "max_drawdown": round(max_dd, 4),
            "sharpe": round(sharpe, 3),
        }


def _komisyon(notional: float, bps: float) -> float:
    return abs(notional) * bps / 10_000.0


def _slipaj_fiyat(fiyat: float, yon_isareti: int, bps: float) -> float:
    """Açılışta yön lehine kötüleşen fiyat."""
    return fiyat * (1.0 + yon_isareti * bps / 10_000.0)


def calistir(
    df: pd.DataFrame,
    p: StratejiParams | None = None,
    k: BacktestKonfig | None = None,
) -> BacktestSonuc:
    """Backtest çalıştır.

    `df` İstanbul timezone indeksli, OHLCV kolonlu DataFrame olmalı.
    """
    p = p or StratejiParams()
    k = k or BacktestKonfig()

    df = tum_indikatorler(df, trend_ema_p=p.trend_ema_period)
    n = len(df)
    bakiye = k.baslangic_bakiyesi
    pos: Pozisyon | None = None
    bekleyen_sinyal: Yon | None = None
    trades: list[Trade] = []
    bakiye_serisi = np.full(n, np.nan)
    bakiye_serisi[0] = bakiye

    for i in range(1, n):
        cur_open = float(df["open"].iat[i])
        cur_high = float(df["high"].iat[i])
        cur_low = float(df["low"].iat[i])
        cur_close = float(df["close"].iat[i])
        ts = df.index[i]

        # 1) Bekleyen giriş sinyali varsa BU mumun açılışında giriş
        if bekleyen_sinyal is not None and pos is None:
            yon = bekleyen_sinyal
            isaret = 1 if yon is Yon.LONG else -1
            giris_fiyat = _slipaj_fiyat(cur_open, isaret, k.slippage_bps)
            sl = stop_loss_hesapla(df, i, yon, p, giris_fiyat=giris_fiyat)

            risk_per_unit = abs(giris_fiyat - sl)
            if risk_per_unit > 0:
                risk_usd = bakiye * (p.risk_per_trade_pct / 100.0)
                miktar = risk_usd / risk_per_unit
                notional = miktar * giris_fiyat
                bakiye -= _komisyon(notional, k.komisyon_bps)
                pos = Pozisyon(
                    yon=yon,
                    giris_indeks=i,
                    giris_fiyati=giris_fiyat,
                    stop_loss=sl,
                    miktar=miktar,
                    giris_zamani=ts,
                )
            bekleyen_sinyal = None

        # 2) Pozisyon varsa intraday SL tetikleme kontrolü
        if pos is not None:
            sl_tetiklendi = False
            cikis_fiyat = None
            if pos.yon is Yon.LONG and cur_low <= pos.stop_loss:
                sl_tetiklendi = True
                cikis_fiyat = _slipaj_fiyat(pos.stop_loss, -1, k.slippage_bps)
            elif pos.yon is Yon.SHORT and cur_high >= pos.stop_loss:
                sl_tetiklendi = True
                cikis_fiyat = _slipaj_fiyat(pos.stop_loss, 1, k.slippage_bps)

            if sl_tetiklendi:
                trades.append(_trade_kapat(pos, i, ts, cikis_fiyat, "stop_loss", df, k))
                bakiye = _bakiyeyi_guncelle(bakiye, trades[-1])
                pos = None

        # 3) Mum kapandı; sinyal üret
        if pos is None:
            sig = giris_sinyali(df, i, p)
            if sig is not None:
                bekleyen_sinyal = sig
        else:
            if cikis_sinyali(df, i, pos, p):
                # Sıradaki mum açılışında çıkış için bekleyen exit kullanmak
                # yerine, gerçekçi olması adına bu mumun kapanışında çık
                # (Big E'nin yaptığı: yeni mum açılınca check, exit varsa
                #  resmen yeni mumda exit edilir, ama close'a yakın).
                # Daha doğru: bir sonraki açılışı bekle. Onu yapıyoruz.
                bekleyen_cikis = True
            else:
                bekleyen_cikis = False

            if bekleyen_cikis and i + 1 < n:
                nxt_open = float(df["open"].iat[i + 1])
                isaret = -1 if pos.yon is Yon.LONG else 1
                cikis_fiyat = _slipaj_fiyat(nxt_open, isaret, k.slippage_bps)
                trades.append(_trade_kapat(pos, i + 1, df.index[i + 1], cikis_fiyat, "tdi_exit", df, k))
                bakiye = _bakiyeyi_guncelle(bakiye, trades[-1])
                pos = None

        bakiye_serisi[i] = bakiye + _floating_pnl(pos, cur_close) if pos else bakiye

    # Açık pozisyon kaldıysa son mum close ile kapat
    if pos is not None:
        ts = df.index[-1]
        cikis_fiyat = float(df["close"].iat[-1])
        trades.append(_trade_kapat(pos, n - 1, ts, cikis_fiyat, "eof", df, k))
        bakiye = _bakiyeyi_guncelle(bakiye, trades[-1])
        bakiye_serisi[-1] = bakiye

    return BacktestSonuc(
        trades=trades,
        bakiye_serisi=pd.Series(bakiye_serisi, index=df.index, name="bakiye"),
    )


def _trade_kapat(
    pos: Pozisyon,
    cikis_i: int,
    cikis_ts: pd.Timestamp,
    cikis_fiyati: float,
    sebep: str,
    df: pd.DataFrame,
    k: BacktestKonfig,
) -> Trade:
    isaret = 1 if pos.yon is Yon.LONG else -1
    pnl_brut = (cikis_fiyati - pos.giris_fiyati) * pos.miktar * isaret
    notional_cikis = pos.miktar * cikis_fiyati
    komisyon_cikis = _komisyon(notional_cikis, k.komisyon_bps)
    pnl_net = pnl_brut - komisyon_cikis
    return Trade(
        yon=pos.yon,
        giris_indeks=pos.giris_indeks,
        cikis_indeks=cikis_i,
        giris_fiyati=pos.giris_fiyati,
        cikis_fiyati=cikis_fiyati,
        miktar=pos.miktar,
        giris_zamani=pos.giris_zamani,
        cikis_zamani=cikis_ts,
        sebep=sebep,
        pnl_brut=pnl_brut,
        pnl_net=pnl_net,
    )


def _bakiyeyi_guncelle(bakiye: float, t: Trade) -> float:
    return bakiye + t.pnl_net


def _floating_pnl(pos: Pozisyon | None, mark: float) -> float:
    if pos is None:
        return 0.0
    isaret = 1 if pos.yon is Yon.LONG else -1
    return (mark - pos.giris_fiyati) * pos.miktar * isaret
