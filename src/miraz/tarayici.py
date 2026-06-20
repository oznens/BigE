"""Çoklu parite/zaman dilimi harmonik tarayıcı.

Kullanım:
    from miraz.tarayici import tara_coklu
    sonuclar = tara_coklu(["BTCUSDT", "ETHUSDT"], ["1h", "4h"])
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from . import harmonik as hrm
from . import pivotlar as pv
from . import veri


@dataclass
class TaramaSonucu:
    symbol: str
    interval: str
    pattern: hrm.HarmonikSonuc
    son_bar_zamani: pd.Timestamp


def tara_coklu(
    semboller: list[str],
    intervallar: list[str],
    pivot_n: int = 5,
    min_kalite: float = 40.0,
    son_n_pivot: int = 50,    # sadece son N pivota bak (hızlı mod)
    gun: int = 500,
) -> list[TaramaSonucu]:
    """Birden fazla sembol ve zaman diliminde harmonik tarama yapar.

    Parametreler
    ------------
    semboller    : ["BTCUSDT", "ETHUSDT", ...]
    intervallar  : ["1h", "4h", ...]
    pivot_n      : swing high/low pencere boyutu
    min_kalite   : kalite eşiği (0-100)
    son_n_pivot  : sadece son N pivot ile çalış (büyük veri için)
    gun          : kaç günlük veri
    """
    sonuclar: list[TaramaSonucu] = []

    for sembol in semboller:
        for interval in intervallar:
            try:
                df = veri.indir(sembol, interval, gun=gun)
            except Exception as e:
                print(f"  HATA {sembol}/{interval}: {e}")
                continue

            pivlar = pv.pivot_listesi(df, n=pivot_n)
            # Sadece son N pivot ile çalış
            if son_n_pivot and len(pivlar) > son_n_pivot:
                pivlar = pivlar[-son_n_pivot:]

            bulunanlar = hrm.tara(df, pivlar, min_kalite=min_kalite)
            for p in bulunanlar:
                sonuclar.append(TaramaSonucu(
                    symbol=sembol,
                    interval=interval,
                    pattern=p,
                    son_bar_zamani=df.index[-1],
                ))

    # En yeni D barına göre sırala
    sonuclar.sort(key=lambda s: s.pattern.D_idx, reverse=True)
    return sonuclar


def ozet_yazdir(sonuclar: list[TaramaSonucu]) -> None:
    """Tarama sonuçlarını terminale tablo olarak yazar."""
    if not sonuclar:
        print("  Pattern bulunamadı.")
        return

    print(f"\n{'='*80}")
    print(f"{'SEMBOL':<14} {'TF':>4}  {'PATTERN':<12} {'YÖN':<8} "
          f"{'ENTRY':>10} {'SL':>10} {'TP1':>10} {'R:R':>5} {'KAL':>5}")
    print(f"{'='*80}")
    for s in sonuclar:
        p = s.pattern
        print(f"{s.symbol:<14} {s.interval:>4}  {p.isim:<12} {p.yon:<8} "
              f"{p.entry:>10,.2f} {p.sl:>10,.2f} {p.tp1:>10,.2f} "
              f"{p.rr:>5.1f} {p.kalite:>5.1f}")
    print(f"{'='*80}")
    print(f"Toplam: {len(sonuclar)} pattern\n")
