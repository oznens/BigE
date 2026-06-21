"""Price-Action Konsept Katmanları — terminalMiraz'ın sol panel dedektörleri.

@tradermiraz terminalMiraz'da sol şeritte Drift / Torque / Root / Shade / Strike
/ Cavity / Shear / Ladder / Buffer / Reservoir / Harmonic gibi kendine özgü PA
konsept isimleri kullanıyor ama tweetlerinde ne olduklarını açıklamıyor. Biz bu
isimler altında TUTARLI, uygulanabilir price-action dedektörleri kuruyoruz
(anlamlar bizim tanımımız; saf PA/SMC karşılıkları):

  Drift     → düşük oynaklıklı yönlü sürüklenme kanalı (HH/HL veya LH/LL)
  Torque    → momentum patlaması (geniş gövde + hacim, yapıyı kırar)
  Root      → birikim tabanı / güçlü destek kökü (Long)
  Shade     → tepe arzı / üst-fitil reddi olan direnç (Short)
  Strike    → seviye kırılımı + retest (kırılım yönü)
  Cavity    → dengesizlik/boşluk (FVG — fair value gap)
  Shear     → karakter değişimi (CHoCH — yapı tersine döner)
  Ladder    → merdiven/basamak trendi (ardışık HH-HL / LH-LL)
  Buffer    → konsolidasyon/soğurma bandı (büzülen dar range)
  Reservoir → likidite havuzu (eşit dip/tepe) + süpürme → dönüş
  Harmonic  → mevcut harmonik motoru (harmonik.py) — burada referans amaçlı

Her dedektör df alır, tetiklerse KonseptSinyal döndürür, yoksa None.
`tara_konseptler(df)` hepsini çalıştırıp tetikleyenleri {isim: sinyal} verir.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import pandas as pd

from . import kutular as kt
from . import yapi as yp
from .pivotlar import pivot_listesi

# Konsept sırası (sol panel şeridi sırası)
KONSEPT_SIRASI = ["Drift", "Torque", "Root", "Shade", "Strike",
                  "Cavity", "Shear", "Ladder", "Buffer", "Reservoir", "Harmonic"]


@dataclass
class KonseptSinyal:
    isim: str                      # "Cavity", "Root", ...
    yon: str                       # "Long" / "Short" / "Nötr"
    guc: float                     # 0–100 güven/kalite
    aciklama: str                  # tek satır açıklama
    zone_alt: float | None = None  # ilgili bölge alt sınırı (çizim)
    zone_ust: float | None = None  # ilgili bölge üst sınırı
    seviye: float | None = None    # tetik/giriş referans seviyesi
    idx: int | None = None         # ilgili bar konumu (grafikte işaret)


# ---------------------------------------------------------------------------
# Ortak yardımcılar
# ---------------------------------------------------------------------------

def _govde(df) -> pd.Series:
    return (df["close"] - df["open"]).abs()


def _ort_govde(df, n: int = 20) -> float:
    g = _govde(df)
    return float(g.tail(n).mean()) if len(g) else 0.0


def _son_iki(piv, tip: str):
    s = [p for p in piv if p[2] == tip]
    return (s[-2], s[-1]) if len(s) >= 2 else (None, None)


# ---------------------------------------------------------------------------
# 1) Drift — düşük oynaklıklı yönlü sürüklenme
# ---------------------------------------------------------------------------

def drift(df, n: int = 5, atr_esik: float = 0.012) -> Optional[KonseptSinyal]:
    """Dar ATR + düzgün yapı (HH/HL veya LH/LL) = sakin yönlü sürüklenme."""
    if len(df) < 30:
        return None
    atr = kt.atr_yuzde(df)
    if atr > atr_esik:                       # oynaklık yüksekse drift değil
        return None
    my = yp.market_yapisi(df, n=n)
    if my is None or my.durum == "yatay":
        return None
    yon = "Long" if my.durum == "yükseliş" else "Short"
    # düşük oynaklık ne kadar belirginse güç o kadar yüksek
    guc = round(max(0.0, min(100.0, (atr_esik - atr) / atr_esik * 60 + 40)), 1)
    return KonseptSinyal(
        isim="Drift", yon=yon, guc=guc,
        seviye=round(float(df["close"].iloc[-1]), 6),
        aciklama=f"Düşük oynaklık (ATR %{atr*100:.1f}) {my.durum} sürüklenmesi")


# ---------------------------------------------------------------------------
# 2) Torque — momentum patlaması (impuls)
# ---------------------------------------------------------------------------

def torque(df, carpan: float = 1.8, hacim_carpan: float = 1.5,
           bak: int = 5) -> Optional[KonseptSinyal]:
    """Son `bak` barda ort. gövdenin `carpan`× üstü + hacim sıçraması = impuls."""
    if len(df) < 30:
        return None
    ortg = _ort_govde(df, 20)
    if ortg <= 0:
        return None
    vol = df["volume"]
    ort_vol = float(vol.tail(20).mean()) or 1.0
    govde = _govde(df)
    son = df.tail(bak)
    en_iyi = None
    for i in range(len(df) - bak, len(df)):
        if i < 1:
            continue
        g = float(govde.iloc[i])
        v = float(vol.iloc[i])
        if g >= carpan * ortg and v >= hacim_carpan * ort_vol:
            yon = "Long" if df["close"].iloc[i] >= df["open"].iloc[i] else "Short"
            guc = round(min(100.0, (g / ortg) * 25 + (v / ort_vol) * 10), 1)
            if en_iyi is None or guc > en_iyi.guc:
                en_iyi = KonseptSinyal(
                    isim="Torque", yon=yon, guc=guc, idx=i,
                    seviye=round(float(df["close"].iloc[i]), 6),
                    aciklama=(f"Momentum patlaması: gövde {g/ortg:.1f}× · "
                              f"hacim {v/ort_vol:.1f}× ortalama"))
    return en_iyi


# ---------------------------------------------------------------------------
# 3) Root — birikim tabanı / güçlü destek kökü (Long)
# ---------------------------------------------------------------------------

def root(df, n: int = 5, min_dokunus: int = 3,
         min_guc: float = 60.0) -> Optional[KonseptSinyal]:
    """Fiyatın altındaki, çok temaslı en güçlü destek kutusu = taban kökü."""
    if len(df) < 30:
        return None
    fiyat = float(df["close"].iloc[-1])
    kutular = kt.kutulari_bul(df, n=n, min_guc=min_guc, adaptif=True)
    destekler = [k for k in kutular if k.tip == "Destek" and k.ust <= fiyat * 1.01
                 and k.dokunus >= min_dokunus]
    if not destekler:
        return None
    k = max(destekler, key=lambda x: (x.guc, x.dokunus))
    return KonseptSinyal(
        isim="Root", yon="Long", guc=round(k.guc, 1),
        zone_alt=k.alt, zone_ust=k.ust, seviye=k.merkez,
        idx=k.son_idx,
        aciklama=(f"Birikim tabanı {k.alt:g}–{k.ust:g} "
                  f"({k.dokunus} temas, güç {k.guc:.0f})"))


# ---------------------------------------------------------------------------
# 4) Shade — tepe arzı / üst-fitil reddi olan direnç (Short)
# ---------------------------------------------------------------------------

def shade(df, n: int = 5, min_dokunus: int = 2,
          min_guc: float = 60.0) -> Optional[KonseptSinyal]:
    """Fiyatın üstündeki güçlü direnç + bölgede üst-fitil reddi = arz gölgesi."""
    if len(df) < 30:
        return None
    fiyat = float(df["close"].iloc[-1])
    kutular = kt.kutulari_bul(df, n=n, min_guc=min_guc, adaptif=True)
    direncler = [k for k in kutular if k.tip == "Direnç" and k.alt >= fiyat * 0.99
                 and k.dokunus >= min_dokunus]
    if not direncler:
        return None
    k = min(direncler, key=lambda x: x.alt)          # en yakın tavan
    # üst-fitil reddi kanıtı: bölgeye giren barlarda uzun üst fitil
    son = df.tail(40)
    deger = son[(son["high"] >= k.alt)]
    if len(deger) == 0:
        return None
    ust_fitil = (deger["high"] - deger[["open", "close"]].max(axis=1))
    govde = (deger["close"] - deger["open"]).abs() + 1e-9
    red_oran = float((ust_fitil > govde).mean())     # fitil>gövde olan bar oranı
    if red_oran < 0.25:
        return None
    guc = round(min(100.0, k.guc * 0.7 + red_oran * 40), 1)
    return KonseptSinyal(
        isim="Shade", yon="Short", guc=guc,
        zone_alt=k.alt, zone_ust=k.ust, seviye=k.merkez, idx=k.son_idx,
        aciklama=(f"Tepe arzı {k.alt:g}–{k.ust:g} — üst-fitil reddi "
                  f"%{red_oran*100:.0f}"))


# ---------------------------------------------------------------------------
# 5) Strike — seviye kırılımı + retest (kırılım yönü)
# ---------------------------------------------------------------------------

def strike(df, n: int = 5, retest_tol: float = 0.004) -> Optional[KonseptSinyal]:
    """Yapısal seviye BOS ile kırıldı ve fiyat o seviyeyi retest ediyor."""
    if len(df) < 30:
        return None
    my = yp.market_yapisi(df, n=n)
    if my is None or my.kirilim is None or "BOS" not in my.kirilim:
        return None
    fiyat = float(df["close"].iloc[-1])
    if "yukarı" in my.kirilim:
        seviye = my.son_yuksek                       # kırılan direnç → yeni destek
        yon = "Long"
    else:
        seviye = my.son_dusuk
        yon = "Short"
    # retest: fiyat kırılan seviyeye yeniden yaklaşmış mı?
    if seviye <= 0 or abs(fiyat - seviye) / seviye > retest_tol * 6:
        return None
    yakinlik = 1 - min(1.0, abs(fiyat - seviye) / (seviye * retest_tol * 6))
    guc = round(50 + yakinlik * 45, 1)
    return KonseptSinyal(
        isim="Strike", yon=yon, guc=guc, seviye=round(seviye, 6),
        aciklama=f"{my.kirilim} kırılımı + {seviye:g} retesti")


# ---------------------------------------------------------------------------
# 6) Cavity — dengesizlik/boşluk (FVG — fair value gap)
# ---------------------------------------------------------------------------

def cavity(df, bak: int = 50, min_carpan: float = 0.3) -> Optional[KonseptSinyal]:
    """3-mum imbalance (FVG): mum1 ile mum3 arasında doldurulmamış boşluk.

      Bullish: high[i-1] < low[i+1] → boşluk üstte, Long destek bölgesi.
      Bearish: low[i-1]  > high[i+1] → boşluk altta, Short direnç bölgesi.
    Fiyatın henüz doldurmadığı, güncele en yakın boşluğu seçer.
    """
    if len(df) < 5:
        return None
    h = df["high"].to_numpy(); l = df["low"].to_numpy()
    c = df["close"]; fiyat = float(c.iloc[-1])
    atr = kt.atr_yuzde(df) * fiyat or (fiyat * 0.01)
    son = max(1, len(df) - bak)
    en_yakin = None
    for i in range(len(df) - 2, son, -1):            # ortadaki mum i
        # bullish FVG
        if h[i - 1] < l[i + 1]:
            alt, ust = float(h[i - 1]), float(l[i + 1])
            if (ust - alt) >= min_carpan * atr and fiyat >= alt:
                en_yakin = ("Long", alt, ust, i)
                break
        # bearish FVG
        if l[i - 1] > h[i + 1]:
            alt, ust = float(h[i + 1]), float(l[i - 1])
            if (ust - alt) >= min_carpan * atr and fiyat <= ust:
                en_yakin = ("Short", alt, ust, i)
                break
    if en_yakin is None:
        return None
    yon, alt, ust, i = en_yakin
    guc = round(min(100.0, 45 + (ust - alt) / atr * 20), 1)
    return KonseptSinyal(
        isim="Cavity", yon=yon, guc=guc, zone_alt=round(alt, 6),
        zone_ust=round(ust, 6), seviye=round((alt + ust) / 2, 6), idx=i,
        aciklama=f"{yon} FVG boşluğu {alt:g}–{ust:g} (doldurulmamış)")


# ---------------------------------------------------------------------------
# 7) Shear — karakter değişimi (CHoCH)
# ---------------------------------------------------------------------------

def shear(df, n: int = 5) -> Optional[KonseptSinyal]:
    """Market yapısı CHoCH ile ters yöne döndü = trend makaslaması."""
    if len(df) < 30:
        return None
    my = yp.market_yapisi(df, n=n)
    if my is None or my.kirilim is None or "CHoCH" not in my.kirilim:
        return None
    if "yukarı" in my.kirilim:
        yon, seviye = "Long", my.son_yuksek
    else:
        yon, seviye = "Short", my.son_dusuk
    return KonseptSinyal(
        isim="Shear", yon=yon, guc=70.0, seviye=round(seviye, 6),
        aciklama=f"{my.kirilim}: yapı ters yöne döndü (karakter değişimi)")


# ---------------------------------------------------------------------------
# 8) Ladder — merdiven/basamak trendi
# ---------------------------------------------------------------------------

def ladder(df, n: int = 5, min_basamak: int = 2) -> Optional[KonseptSinyal]:
    """Ardışık HH-HL (Long) veya LH-LL (Short) basamakları = merdiven trendi."""
    if len(df) < 30:
        return None
    piv = pivot_listesi(df, n=n)
    highs = [p for p in piv if p[2] == "H"]
    lows = [p for p in piv if p[2] == "L"]
    if len(highs) < min_basamak + 1 or len(lows) < min_basamak + 1:
        return None

    def _artan(seri):     # son (min_basamak+1) eleman hep artıyor mu
        s = [p[1] for p in seri[-(min_basamak + 1):]]
        return all(s[k] < s[k + 1] for k in range(len(s) - 1))

    def _azalan(seri):
        s = [p[1] for p in seri[-(min_basamak + 1):]]
        return all(s[k] > s[k + 1] for k in range(len(s) - 1))

    if _artan(highs) and _artan(lows):
        yon = "Long"
    elif _azalan(highs) and _azalan(lows):
        yon = "Short"
    else:
        return None
    return KonseptSinyal(
        isim="Ladder", yon=yon, guc=68.0,
        seviye=round(float(lows[-1][1] if yon == "Long" else highs[-1][1]), 6),
        aciklama=f"{yon} merdiven: ardışık {'HH-HL' if yon=='Long' else 'LH-LL'}")


# ---------------------------------------------------------------------------
# 9) Buffer — konsolidasyon/soğurma bandı (büzülen dar range)
# ---------------------------------------------------------------------------

def buffer(df, pencere: int = 12, onceki: int = 24,
           buzulme: float = 0.6) -> Optional[KonseptSinyal]:
    """Son `pencere` barın aralığı, önceki döneme göre belirgin daraldıysa sıkışma."""
    if len(df) < pencere + onceki:
        return None
    son = df.tail(pencere)
    onc = df.iloc[-(pencere + onceki):-pencere]
    son_aralik = float(son["high"].max() - son["low"].min())
    onc_aralik = float(onc["high"].max() - onc["low"].min())
    if onc_aralik <= 0:
        return None
    oran = son_aralik / onc_aralik
    if oran > buzulme:                               # yeterince büzülmemiş
        return None
    # kapsayan trend yönünü bias olarak ver
    my = yp.market_yapisi(df)
    yon = ("Long" if my and my.durum == "yükseliş"
           else "Short" if my and my.durum == "düşüş" else "Nötr")
    guc = round(min(100.0, (buzulme - oran) / buzulme * 60 + 40), 1)
    return KonseptSinyal(
        isim="Buffer", yon=yon, guc=guc,
        zone_alt=round(float(son["low"].min()), 6),
        zone_ust=round(float(son["high"].max()), 6),
        seviye=round(float(son["close"].iloc[-1]), 6),
        aciklama=f"Sıkışma bandı (aralık {oran:.0%} daraldı) — kırılım beklentisi")


# ---------------------------------------------------------------------------
# 10) Reservoir — likidite havuzu (eşit dip/tepe) + süpürme → dönüş
# ---------------------------------------------------------------------------

def reservoir(df, n: int = 5, esit_tol: float = 0.003,
              bak: int = 8) -> Optional[KonseptSinyal]:
    """Eşit highs/lows = likidite havuzu; fitil süpürüp geri kapanırsa dönüş.

      Eşit tepeler süpürüldü (üstüne fitil, altına kapanış) → Short.
      Eşit dipler  süpürüldü (altına fitil, üstüne kapanış) → Long.
    """
    if len(df) < 30:
        return None
    piv = pivot_listesi(df, n=n)
    (h0, h1) = _son_iki(piv, "H")
    (l0, l1) = _son_iki(piv, "L")
    fiyat = float(df["close"].iloc[-1])
    son = df.tail(bak)

    # eşit tepeler → likidite üstte → süpürme + ters kapanış = Short
    if h0 and h1 and abs(h0[1] - h1[1]) / max(h1[1], 1e-9) <= esit_tol:
        havuz = max(h0[1], h1[1])
        if float(son["high"].max()) > havuz and fiyat < havuz:
            return KonseptSinyal(
                isim="Reservoir", yon="Short", guc=72.0, seviye=round(havuz, 6),
                aciklama=f"Eşit tepe likiditesi {havuz:g} süpürüldü → dönüş (Short)")
    # eşit dipler → likidite altta → süpürme + ters kapanış = Long
    if l0 and l1 and abs(l0[1] - l1[1]) / max(l1[1], 1e-9) <= esit_tol:
        havuz = min(l0[1], l1[1])
        if float(son["low"].min()) < havuz and fiyat > havuz:
            return KonseptSinyal(
                isim="Reservoir", yon="Long", guc=72.0, seviye=round(havuz, 6),
                aciklama=f"Eşit dip likiditesi {havuz:g} süpürüldü → dönüş (Long)")
    return None


# ---------------------------------------------------------------------------
# Kayıt defteri + toplu tarama
# ---------------------------------------------------------------------------

DEDEKTORLER: dict[str, Callable] = {
    "Drift": drift, "Torque": torque, "Root": root, "Shade": shade,
    "Strike": strike, "Cavity": cavity, "Shear": shear, "Ladder": ladder,
    "Buffer": buffer, "Reservoir": reservoir,
}


def tara_konseptler(df, n: int = 5,
                    secili: list[str] | None = None) -> dict[str, KonseptSinyal]:
    """Tüm (veya `secili`) konsept dedektörlerini çalıştırır.

    Döndürür: tetikleyen konseptlerin {isim: KonseptSinyal} sözlüğü.
    `secili` verilirse yalnız o konseptler taranır (sol panel filtresi).
    """
    sonuc: dict[str, KonseptSinyal] = {}
    for isim, fn in DEDEKTORLER.items():
        if secili is not None and isim not in secili:
            continue
        try:
            s = fn(df, n=n) if _n_kabul(fn) else fn(df)
        except Exception:
            s = None
        if s is not None:
            sonuc[isim] = s
    return sonuc


def _n_kabul(fn) -> bool:
    """Dedektör imzasında `n` parametresi var mı (varsa n=n geçilir)."""
    import inspect
    try:
        return "n" in inspect.signature(fn).parameters
    except (ValueError, TypeError):
        return False
