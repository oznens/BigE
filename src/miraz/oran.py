"""ALT/BTC oranı — göreceli güç (makro) filtresi.

@tradermiraz ETH/BTC oran grafiğiyle Ethereum'un Bitcoin'e karşı güç
kazanıp kaybetmediğini okuyor. Burada aynı mantığı otomatikleştiriyoruz:
bir altcoin'in BTC paritesinin (ör. ETHBTC) trendi yükseliyorsa altcoin
BTC'ye karşı güçlü, düşüyorsa zayıf.

Kullanım:
    from miraz.oran import goreceli_guc
    sonuc = goreceli_guc("ETHUSDT")   # → ETHBTC oranını değerlendirir
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from . import veri


@dataclass
class GoreceliGuc:
    parite: str          # ör. "ETHBTC"
    deger: float         # güncel oran
    degisim_yuzde: float # son N barlık % değişim
    durum: str           # "güçleniyor" / "zayıflıyor" / "nötr"


def _btc_paritesi(symbol: str) -> str | None:
    """USDT paritesini BTC paritesine çevirir (ETHUSDT → ETHBTC)."""
    if symbol.endswith("USDT"):
        taban = symbol[:-4]
        if taban == "BTC":
            return None          # BTC'nin kendisi
        return f"{taban}BTC"
    return None


def goreceli_guc(symbol: str, interval: str = "1d", n: int = 30,
                 esik: float = 0.04, gun: int = 400) -> GoreceliGuc | None:
    """Altcoin'in BTC'ye karşı göreceli gücünü değerlendirir.

    n     : kaç barlık değişime bakılır
    esik  : bu %'den fazla değişim "güçleniyor/zayıflıyor" sayılır

    Döndürür: GoreceliGuc veya None (BTC ise / veri yoksa).
    """
    parite = _btc_paritesi(symbol)
    if parite is None:
        return None
    try:
        df = veri.indir(parite, interval, gun=gun)
    except Exception:
        return None
    if len(df) < n + 1:
        return None

    son = float(df["close"].iloc[-1])
    onceki = float(df["close"].iloc[-n])
    if onceki <= 0:
        return None
    degisim = (son - onceki) / onceki

    if degisim > esik:
        durum = "güçleniyor"
    elif degisim < -esik:
        durum = "zayıflıyor"
    else:
        durum = "nötr"

    return GoreceliGuc(parite=parite, deger=round(son, 8),
                       degisim_yuzde=round(degisim * 100, 2), durum=durum)


def metin(gg: GoreceliGuc | None) -> str:
    """Göreceli gücü okunabilir bir satıra çevirir."""
    if gg is None:
        return ""
    ikon = {"güçleniyor": "💪", "zayıflıyor": "📉", "nötr": "•"}[gg.durum]
    return (f"{ikon} BTC'ye karşı {gg.durum.upper()} "
            f"({gg.parite} son dönem {gg.degisim_yuzde:+.1f}%)")
