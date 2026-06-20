"""Renkli kutu (destek/direnç bölgesi) tespiti — @tradermiraz metodolojisi.

tradermiraz kutuları TradingView'da elle çizer. Burada aynı mantığı
otomatikleştiriyoruz: swing pivotlarını fiyat bandına göre kümeleyip
(birden fazla pivotun değdiği bölge = bölge), her bölgeye dokunuş sayısı +
hacim + tazelik bazlı bir güç puanı veriyoruz. Sonra bölgeyi mevcut fiyata
göre renge çeviriyoruz:

  🔵 Mavi    → güçlü talep bölgesi (birincil long girişi)         [fiyatın altı]
  🟢 Yeşil   → ikincil destek                                     [fiyatın altı]
  🟠 Turuncu → ara nefes / zayıf geçici destek                    [fiyatın altı]
  🟣 Mor     → en yakın güçlü direnç (kar alma)                   [fiyatın üstü]
  🔴 Kırmızı → uzak/güçlü direnç VEYA uzun vade dip               [uzak bölge]

NOT: Orijinal kutular elle çizildiği için bu otomatik sınıflandırma
sezgiseldir; amaç tradermiraz mantığını mekanikleştirmek, birebir taklit değil.

Referans: notlar/kutular.md
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .pivotlar import pivot_listesi


@dataclass
class Kutu:
    alt: float          # band alt sınır (fiyat)
    ust: float          # band üst sınır (fiyat)
    merkez: float       # band orta noktası
    renk: str           # "Mavi" / "Yeşil" / "Turuncu" / "Mor" / "Kırmızı"
    tip: str            # "Destek" veya "Direnç"
    dokunus: int        # kaç pivot bu banda değdi
    guc: float          # 0–100 güç puanı
    hacim_orani: float  # bölge ort. hacmi / genel ort. hacim
    son_idx: int        # en son dokunulan bar indeksi
    mesafe_yuzde: float # mevcut fiyata göre % mesafe (+ üstte, − altta)


# ---------------------------------------------------------------------------
# Kümeleme
# ---------------------------------------------------------------------------

def _kumeler(
    pivotlar: list[tuple[int, float, str]],
    tolerans: float,
) -> list[list[tuple[int, float, str]]]:
    """Pivotları fiyat yakınlığına göre kümeler.

    Fiyata göre sıralanır; ardışık iki pivot arasındaki boşluk
    `tolerans * fiyat`'ı aşınca yeni küme başlar.
    """
    if not pivotlar:
        return []
    sirali = sorted(pivotlar, key=lambda p: p[1])
    kumeler: list[list[tuple[int, float, str]]] = [[sirali[0]]]
    for piv in sirali[1:]:
        son = kumeler[-1]
        ortalama = np.mean([p[1] for p in son])
        if abs(piv[1] - ortalama) <= tolerans * ortalama:
            son.append(piv)
        else:
            kumeler.append([piv])
    return kumeler


# ---------------------------------------------------------------------------
# Güç puanı
# ---------------------------------------------------------------------------

def _guc_puani(dokunus: int, son_idx: int, toplam_bar: int,
               hacim_orani: float) -> float:
    """Dokunuş sayısı + tazelik + hacim ağırlıklı 0–100 güç puanı."""
    t_skor = min(dokunus, 5) / 5.0                 # dokunuş (doygunluk: 5)
    r_skor = son_idx / max(toplam_bar - 1, 1)      # tazelik (sona yakın = 1)
    v_skor = min(hacim_orani, 2.0) / 2.0           # hacim (2x'te doygunluk)
    return round(100 * (0.5 * t_skor + 0.25 * r_skor + 0.25 * v_skor), 1)


# ---------------------------------------------------------------------------
# Renk sınıflandırması
# ---------------------------------------------------------------------------

def _renk_ata(tip: str, guc: float, mesafe_yuzde: float) -> str:
    """Bölgeyi tip + güç + mesafeye göre renge çevirir.

    Destek (fiyatın altı):
      güçlü → Mavi, orta → Yeşil, zayıf → Turuncu
      çok uzak (>%25 altta) + güçlü → Kırmızı (uzun vade dip)
    Direnç (fiyatın üstü):
      yakın & güçlü → Mor, çok uzak → Kırmızı, zayıf → Turuncu
    """
    if tip == "Destek":
        if mesafe_yuzde < -25 and guc >= 55:
            return "Kırmızı"
        if guc >= 65:
            return "Mavi"
        if guc >= 45:
            return "Yeşil"
        return "Turuncu"
    else:  # Direnç
        if mesafe_yuzde > 25:
            return "Kırmızı"
        if guc >= 55:
            return "Mor"
        return "Turuncu"


# ---------------------------------------------------------------------------
# Ana fonksiyon
# ---------------------------------------------------------------------------

def kutulari_bul(
    df: pd.DataFrame,
    n: int = 5,
    tolerans: float = 0.015,
    min_dokunus: int = 2,
    min_guc: float = 0.0,
    mesafe_limit: float = 35.0,
    max_kutu: int | None = None,
) -> list[Kutu]:
    """OHLCV verisinden renkli destek/direnç kutularını çıkarır.

    Parametreler
    ------------
    df           : open/high/low/close/volume kolonlu UTC indeksli DataFrame
    n            : swing pivot pencere boyutu
    tolerans     : kümeleme fiyat toleransı (0.015 = %1.5 band)
    min_dokunus  : bir bölgenin geçerli olması için minimum pivot sayısı
    min_guc      : güç eşiği (altındakiler elenir)
    mesafe_limit : mevcut fiyattan bu %'den uzak bölgeler elenir
                   (işlem yapılabilir bölgelere odaklanmak için; None = sınırsız)
    max_kutu     : döndürülecek maksimum kutu sayısı (None = hepsi)

    Döndürür: mevcut fiyata yakınlığa göre sıralı Kutu listesi (yakın → uzak).
    """
    pivlar = pivot_listesi(df, n=n)
    if not pivlar:
        return []

    toplam_bar = len(df)
    fiyat = float(df["close"].iloc[-1])
    genel_hacim = float(df["volume"].mean()) or 1.0
    vol = df["volume"].to_numpy()

    kutular: list[Kutu] = []
    for kume in _kumeler(pivlar, tolerans):
        if len(kume) < min_dokunus:
            continue

        fiyatlar = [p[1] for p in kume]
        idxler = [p[0] for p in kume]
        alt, ust = min(fiyatlar), max(fiyatlar)
        merkez = (alt + ust) / 2
        son_idx = max(idxler)

        bolge_hacim = float(np.mean([vol[i] for i in idxler]))
        hacim_orani = bolge_hacim / genel_hacim

        guc = _guc_puani(len(kume), son_idx, toplam_bar, hacim_orani)
        if guc < min_guc:
            continue

        mesafe = (merkez - fiyat) / fiyat * 100
        if mesafe_limit is not None and abs(mesafe) > mesafe_limit:
            continue
        tip = "Direnç" if merkez > fiyat else "Destek"
        renk = _renk_ata(tip, guc, mesafe)

        kutular.append(Kutu(
            alt=round(alt, 4), ust=round(ust, 4), merkez=round(merkez, 4),
            renk=renk, tip=tip, dokunus=len(kume), guc=guc,
            hacim_orani=round(hacim_orani, 2), son_idx=son_idx,
            mesafe_yuzde=round(mesafe, 2),
        ))

    # Mevcut fiyata yakınlığa göre sırala (işlem yapılabilir bölgeler önce)
    kutular.sort(key=lambda k: abs(k.mesafe_yuzde))
    if max_kutu is not None:
        kutular = kutular[:max_kutu]
    return kutular


def ozet_yazdir(symbol: str, df: pd.DataFrame, kutular: list[Kutu]) -> None:
    """Kutuları terminale tablo olarak yazar."""
    fiyat = float(df["close"].iloc[-1])
    renk_emoji = {"Mavi": "🔵", "Yeşil": "🟢", "Turuncu": "🟠",
                  "Mor": "🟣", "Kırmızı": "🔴"}
    print(f"\n{symbol}  —  güncel fiyat: {fiyat:,.4f}")
    if not kutular:
        print("  Kutu bulunamadı.")
        return
    print(f"{'RENK':<10} {'TİP':<7} {'BAND':>24} {'DOK':>4} "
          f"{'GÜÇ':>5} {'HAC':>5} {'MESAFE':>8}")
    print("-" * 70)
    for k in kutular:
        e = renk_emoji.get(k.renk, "  ")
        band = f"{k.alt:,.2f}–{k.ust:,.2f}"
        print(f"{e} {k.renk:<7} {k.tip:<7} {band:>24} {k.dokunus:>4} "
              f"{k.guc:>5.1f} {k.hacim_orani:>5.2f} {k.mesafe_yuzde:>+7.2f}%")
