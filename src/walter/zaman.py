"""Saat dilimi yardımcıları.

Veri kaynağı UTC verir. Strateji "Monday Asia Open" edge'i için ET (Amerika
borsa saati) kullanır; raporlar Istanbul saatiyle de gösterilebilir.
"""

from __future__ import annotations

from zoneinfo import ZoneInfo

import pandas as pd

UTC = ZoneInfo("UTC")
ET = ZoneInfo("America/New_York")
ISTANBUL = ZoneInfo("Europe/Istanbul")


def utc_index_to(df: pd.DataFrame, tz: ZoneInfo) -> pd.DatetimeIndex:
    """UTC indeksli DataFrame'in indeksini hedef saat dilimine çevirir.

    DataFrame'i değiştirmez; sadece çevrilmiş indeksi döndürür.
    """
    idx = df.index
    if idx.tz is None:
        idx = idx.tz_localize(UTC)
    return idx.tz_convert(tz)


def saat_ozellikleri(idx: pd.DatetimeIndex, tz: ZoneInfo = ET) -> pd.DataFrame:
    """Verilen zaman indeksinden takvim özellikleri çıkarır (hedef tz'de).

    Döndürülen kolonlar:
      - haftanin_gunu : 0=Pazartesi ... 6=Pazar
      - saat          : 0-23 (hedef tz'de)
      - hafta_saati   : 0-167, haftanın başından itibaren saat (Pazartesi 00:00 = 0)
    """
    if idx.tz is None:
        idx = idx.tz_localize(UTC)
    local = idx.tz_convert(tz)
    hafta_saati = local.dayofweek * 24 + local.hour
    return pd.DataFrame(
        {
            "haftanin_gunu": local.dayofweek,
            "saat": local.hour,
            "hafta_saati": hafta_saati,
        },
        index=idx,
    )
