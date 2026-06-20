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


_ALTIN_PARITE = "PAXGUSDT"   # PAX Gold ≈ 1 ons altın


@dataclass
class GoreceliGuc:
    parite: str          # ör. "ETHBTC" veya "BTC/Altın"
    benchmark: str       # "BTC" veya "Altın"
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


def _oran_serisi(symbol: str, interval: str, gun: int):
    """(oran_serisi, parite_adı, benchmark) döndürür.

    - Altcoin → doğrudan ALT/BTC paritesi (ör. ETHBTC).
    - BTC → BTCUSDT / PAXGUSDT (BTC'nin altın karşısındaki değeri).
    """
    if symbol == "BTCUSDT":
        b = veri.indir("BTCUSDT", interval, gun=gun)["close"]
        g = veri.indir(_ALTIN_PARITE, interval, gun=gun)["close"]
        df = pd.concat([b, g], axis=1, keys=["b", "g"]).dropna()
        return df["b"] / df["g"], "BTC/Altın", "Altın"
    parite = _btc_paritesi(symbol)
    if parite is None:
        return None, None, None
    return veri.indir(parite, interval, gun=gun)["close"], parite, "BTC"


def goreceli_guc(symbol: str, interval: str = "1d", n: int = 30,
                 esik: float = 0.04, gun: int = 400) -> GoreceliGuc | None:
    """Bir varlığın benchmark'ına (alt→BTC, BTC→Altın) göreceli gücü.

    n     : kaç barlık değişime bakılır
    esik  : bu %'den fazla değişim "güçleniyor/zayıflıyor" sayılır
    """
    try:
        seri, parite, benchmark = _oran_serisi(symbol, interval, gun)
    except Exception:
        return None
    if seri is None or len(seri) < n + 1:
        return None

    son = float(seri.iloc[-1])
    onceki = float(seri.iloc[-n])
    if onceki <= 0:
        return None
    degisim = (son - onceki) / onceki

    if degisim > esik:
        durum = "güçleniyor"
    elif degisim < -esik:
        durum = "zayıflıyor"
    else:
        durum = "nötr"

    return GoreceliGuc(parite=parite, benchmark=benchmark, deger=round(son, 8),
                       degisim_yuzde=round(degisim * 100, 2), durum=durum)


def metin(gg: GoreceliGuc | None) -> str:
    """Göreceli gücü okunabilir bir satıra çevirir."""
    if gg is None:
        return ""
    ikon = {"güçleniyor": "💪", "zayıflıyor": "📉", "nötr": "•"}[gg.durum]
    ek = {"BTC": "BTC'ye", "Altın": "Altın'a"}.get(gg.benchmark,
                                                   f"{gg.benchmark}'a")
    return (f"{ikon} {ek} karşı {gg.durum.upper()} "
            f"({gg.parite} son dönem {gg.degisim_yuzde:+.1f}%)")
