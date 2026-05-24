"""Türkiye saati (Europe/Istanbul) yardımcıları.

Tüm modelde tarih/saat işlemleri İstanbul saati üzerinden yapılır.
Veri kaynakları genelde UTC verir; bu modüldeki fonksiyonlarla çevrilir.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

ISTANBUL = ZoneInfo("Europe/Istanbul")
UTC = ZoneInfo("UTC")


def simdi() -> datetime:
    return datetime.now(tz=ISTANBUL)


def utc_to_istanbul(ts: pd.Timestamp | datetime) -> pd.Timestamp:
    ts = pd.Timestamp(ts)
    if ts.tzinfo is None:
        ts = ts.tz_localize(UTC)
    return ts.tz_convert(ISTANBUL)


def istanbul_index(df: pd.DataFrame) -> pd.DataFrame:
    if df.index.tz is None:
        df = df.tz_localize(UTC)
    return df.tz_convert(ISTANBUL)
