"""Senaryo motoru — kutular + trend + "kapanış altında iptal" kuralı.

@tradermiraz'ın planlarını mekanikleştirir. Örnek (ETH, 18 Haz):
  "1652$ altında kapanış yapmadığımız sürece destek bölgesinden tepki
   bekliyorum. 1629$ fitili senaryoyu bozmaz."

Mantık:
  - Fiyatın altındaki en yakın güçlü destek kutusu = tepki bölgesi.
  - O kutunun ALT sınırı = kritik seviye (altında KAPANIŞ = iptal).
  - Kritik seviyenin biraz altı = fitil toleransı (fitil iptal etmez).
  - Fiyatın üstündeki en yakın güçlü direnç (Mor) = yukarı hedef.
  - Varsa yükselen trend çizgisi senaryoyu destekler.

Kural kaynağı: notlar/kutular.md → "X$ altında KAPANIŞ, fitil yetmez".
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from . import harmonik as hrm
from . import kutular as kt
from . import pivotlar as pv
from . import trend as tr
from .kutular import Kutu
from .trend import TrendCizgisi

# Fitil toleransı: kritik seviyenin bu kadar altına fitil senaryoyu bozmaz
_FITIL_TOL = 0.015  # %1.5


# Fiyatın bu kadar altındaki destekler tek "tepki bölgesi" sayılır
_BOLGE_MENZIL = 0.06  # %6

# Hacim filtresi: destek bölgesine geliş hacmi bu kattan fazlaysa kırılma riski
_HACIM_ESIK = 1.5
_HACIM_GELIS_N = 8     # son kaç bar "geliş" sayılır
_HACIM_TABAN_N = 60    # uzun dönem hacim ortalaması penceresi


def gelis_hacim_orani(df, gelis_n: int = _HACIM_GELIS_N,
                      taban_n: int = _HACIM_TABAN_N) -> float:
    """Fiyatın bölgeye gelişindeki hacmin uzun dönem ortalamaya oranı.

    Son `gelis_n` barın ortalama hacmi / son `taban_n` barın ortalama hacmi.
    >1 = normalden hacimli geliş (TAO'da yeşil kutuya hacimli geliş gibi).
    """
    vol = df["volume"]
    if len(vol) < gelis_n + 1:
        return 1.0
    son = float(vol.iloc[-gelis_n:].mean())
    taban = float(vol.iloc[-taban_n:].mean()) if len(vol) >= taban_n \
        else float(vol.mean())
    return son / taban if taban else 1.0


def _mavi_daire_bul(df, n: int, bolge_alt: float, bolge_ust: float,
                    min_kalite: float = 40.0):
    """Destek bölgesinde tamamlanan bullish harmonik D = en yüksek güvenli giriş.

    TAO'daki "mavi daire" kavramı: harmonik PRZ (D) ∩ en güçlü destek.
    Döndürür: en kaliteli HarmonikSonuc veya None.
    """
    pivlar = pv.pivot_listesi(df, n=n)
    patternler = hrm.tara(df, pivlar, min_kalite=min_kalite)
    pay = max((bolge_ust - bolge_alt) * 0.5, bolge_alt * 0.01)
    adaylar = [p for p in patternler if p.yon == "Bullish"
               and (bolge_alt - pay) <= p.D <= (bolge_ust + pay)]
    if not adaylar:
        return None
    return max(adaylar, key=lambda p: (p.kalite, p.D_idx))


def _mtf_yapi(df_ust, n: int = 20) -> str:
    """Üst zaman dilimi yapısını değerlendirir (long açısından).

    Döndürür: "sağlıklı" / "problemli" / "nötr".
    """
    kapanis = df_ust["close"]
    if len(kapanis) < n + 1:
        return "nötr"
    son = float(kapanis.iloc[-1])
    onceki = float(kapanis.iloc[-n])
    if onceki <= 0:
        return "nötr"
    degisim = (son - onceki) / onceki
    if degisim < -0.04:
        return "problemli"     # üst zaman aşağı yapıda → long riskli
    if degisim > 0.04:
        return "sağlıklı"
    return "nötr"


@dataclass
class Senaryo:
    fiyat: float
    yon: str                      # "Yükseliş tepkisi" / "Düşüş riski" / "Nötr"
    destek_kutu: Kutu | None      # tepki bölgesinin en yakın kutusu
    bolge_alt: float | None       # birleşik destek bölgesinin alt sınırı
    bolge_ust: float | None       # birleşik destek bölgesinin üst sınırı
    hedef_kutu: Kutu | None       # ana yukarı hedef (büyük direnç)
    kritik_seviye: float | None   # altında KAPANIŞ = iptal
    fitil_seviye: float | None    # bu seviyeye fitil senaryoyu bozmaz
    trend: TrendCizgisi | None    # sadece yükselen destek çizgisi
    gelis_hacim: float = 1.0      # bölgeye geliş hacim oranı
    kirilma_riski: bool = False   # hacimli geliş → kırılma adayı, işlem alma
    mavi_daire: float | None = None       # harmonik D ∩ destek = en yüksek güven
    mavi_daire_idx: int | None = None     # D barı (grafikte daire konumu)
    mavi_daire_isim: str | None = None    # harmonik pattern adı
    ara_hedef: float | None = None        # 🟣 mor çizgi — ilk kâr-alma seviyesi
    mtf_yapi: str | None = None           # üst zaman dilimi yapısı
    metin: str = ""               # okunabilir plan


def senaryo_uret(
    df: pd.DataFrame,
    n: int = 5,
    tolerans: float = 0.015,
    min_guc: float = 50.0,
    adaptif: bool = True,
    hedef_min_mesafe: float = 6.0,
    hedef_min_guc: float = 80.0,
    df_ust: pd.DataFrame | None = None,
) -> Senaryo:
    """Güncel piyasa yapısından koşullu bir plan üretir.

    adaptif=True ise kutu kümeleme toleransı ATR oynaklığına göre ayarlanır
    (Miraz'ın geniş bölgelerine daha yakın).

    Hedef = "ana hedef" mantığı: yakın küçük dirençleri (engeller) atlayıp,
    fiyattan ≥ hedef_min_mesafe % uzak VE güç ≥ hedef_min_guc olan ilk büyük
    direnç bölgesini seçer. Miraz'ın kar-alma hedefiyle örtüşür.
    """
    fiyat = float(df["close"].iloc[-1])

    kutular = kt.kutulari_bul(df, n=n, tolerans=tolerans, mesafe_limit=30,
                              min_guc=min_guc, adaptif=adaptif)
    direncler = [k for k in kutular if k.tip == "Direnç"]
    destekler = [k for k in kutular if k.tip == "Destek"]

    # Tepki bölgesi: fiyatın hemen altındaki en GÜÇLÜ destek = birincil.
    # Bölge, birincil kutuyla ÖRTÜŞEN (bitişik) kutularla genişletilir;
    # uzaktaki zayıf kutular katılmaz (kritik seviye aşağı kaymasın).
    alt_sinir = fiyat * (1 - _BOLGE_MENZIL)
    ust_sinir = fiyat * 1.005
    yakin = [k for k in destekler if k.alt <= ust_sinir and k.ust >= alt_sinir]

    destek_kutu = bolge_alt = bolge_ust = kritik = fitil = None
    if yakin:
        birincil = max(yakin, key=lambda k: k.guc)
        grup = [k for k in destekler
                if k.alt <= birincil.ust and k.ust >= birincil.alt]
        bolge_alt = round(min(k.alt for k in grup), 4)
        bolge_ust = round(min(max(k.ust for k in grup), fiyat), 4)
        destek_kutu = birincil
        kritik = bolge_alt                          # bitişik zonun dibi
        fitil = round(kritik * (1 - _FITIL_TOL), 4)

    # Ana hedef: yakın küçük dirençleri atla, ilk büyük güçlü zonu seç.
    ust_direncler = sorted((k for k in direncler if k.merkez > fiyat),
                           key=lambda k: k.merkez)
    hedef_kutu = next(
        (k for k in ust_direncler
         if k.mesafe_yuzde >= hedef_min_mesafe and k.guc >= hedef_min_guc),
        None)
    if hedef_kutu is None:                 # uygun büyük zon yoksa en yakını
        hedef_kutu = ust_direncler[0] if ust_direncler else None

    # 🟣 Mor çizgi (ara kâr-alma): en yakın direnç, ana hedeften ÖNCE ise
    ara_hedef = None
    if ust_direncler:
        en_yakin = ust_direncler[0]
        if hedef_kutu is None or en_yakin.merkez < hedef_kutu.merkez:
            ara_hedef = round(en_yakin.alt, 4)   # ilk dokunulacak seviye

    # Trend devam formasyonu = yerel (son ~90 bar) yükselen destek çizgisi.
    # Geniş pencere genel düşüş trendini yakalar; Miraz yerel çizgi çizer.
    trend_cizgi = tr.trend_cizgisi_bul(df, "Destek", n=n, min_dokunus=2,
                                       son_n=90)
    if trend_cizgi is not None and trend_cizgi.yon != "Yükselen":
        trend_cizgi = None

    # Mavi daire: destek bölgesinde tamamlanan bullish harmonik D = en yüksek güven
    mavi_daire = mavi_daire_idx = mavi_daire_isim = None
    if bolge_alt is not None:
        md = _mavi_daire_bul(df, n, bolge_alt, bolge_ust)
        if md is not None:
            mavi_daire = round(md.D, 4)
            mavi_daire_idx = md.D_idx
            mavi_daire_isim = md.isim

    # Hacim filtresi: bölgeye hacimli geliş = kırılma adayı (TAO yeşil kutu dersi)
    hacim_orani = round(gelis_hacim_orani(df), 2)
    kirilma_riski = (destek_kutu is not None and hacim_orani >= _HACIM_ESIK)

    # MTF: üst zaman dilimi yapısı (Gümüş dersi — "günlük yapı problemli")
    mtf = _mtf_yapi(df_ust) if df_ust is not None else None

    # Yön kararı: destek bölgesi varsa tepki beklentisi; yoksa nötr
    if destek_kutu is None:
        yon = "Nötr"
    elif kirilma_riski:
        yon = "Tepki (kırılma riski)"
    else:
        yon = "Yükseliş tepkisi"

    metin = _metin_uret(fiyat, yon, destek_kutu, bolge_alt, bolge_ust,
                        hedef_kutu, kritik, fitil, trend_cizgi,
                        hacim_orani, kirilma_riski, mavi_daire, mavi_daire_isim,
                        ara_hedef, mtf)

    return Senaryo(
        fiyat=round(fiyat, 4), yon=yon, destek_kutu=destek_kutu,
        bolge_alt=bolge_alt, bolge_ust=bolge_ust,
        hedef_kutu=hedef_kutu, kritik_seviye=kritik, fitil_seviye=fitil,
        trend=trend_cizgi, gelis_hacim=hacim_orani,
        kirilma_riski=kirilma_riski, mavi_daire=mavi_daire,
        mavi_daire_idx=mavi_daire_idx, mavi_daire_isim=mavi_daire_isim,
        ara_hedef=ara_hedef, mtf_yapi=mtf, metin=metin)


def _metin_uret(fiyat, yon, destek, bolge_alt, bolge_ust, hedef,
                kritik, fitil, trend, hacim_orani=1.0, kirilma_riski=False,
                mavi_daire=None, mavi_daire_isim=None, ara_hedef=None,
                mtf=None) -> str:
    sat = [f"Güncel fiyat: {fiyat:,.2f}", f"Senaryo: {yon}"]
    if mtf is not None:
        ikon = {"problemli": "⚠️", "sağlıklı": "✅", "nötr": "•"}.get(mtf, "•")
        sat.append(f"{ikon} Üst zaman dilimi yapısı: {mtf.upper()}" +
                   (" — long açısından temkinli ol, küçük pozisyon."
                    if mtf == "problemli" else ""))
    sat.append("")

    if destek is not None:
        sat.append(
            f"📍 Destek bölgesi: {bolge_alt:,.2f}–{bolge_ust:,.2f} "
            f"(en güçlü kutu {destek.renk}, güç {destek.guc:.0f})")
        if mavi_daire is not None:
            sat.append(
                f"   🔵 MAVİ DAİRE {mavi_daire:,.2f} — burada Bullish "
                f"{mavi_daire_isim} harmonik D noktası tamamlanıyor "
                f"(PRZ ∩ destek = EN YÜKSEK GÜVENLİ long girişi).")
        if kirilma_riski:
            sat.append(
                f"   ⚠️ Fiyat bu bölgeye HACİMLİ geliyor "
                f"(geliş hacmi {hacim_orani:.1f}× ortalama) — KIRILMA RİSKİ. "
                f"İşlem alma, önce bölgede dönüş/teyit bekle.")
        sat.append(
            f"   → {kritik:,.2f} altında KAPANIŞ yapılmadıkça bu bölgeden "
            f"tepki bekleniyor.")
        sat.append(
            f"   → {fitil:,.2f} bölgesine gelecek FİTİL senaryoyu bozmaz "
            f"(kapanış kritik, fitil değil).")
    else:
        sat.append("📍 Yakında güçlü destek kutusu yok — temkinli ol.")

    if ara_hedef is not None:
        sat.append(
            f"🟣 Mor çizgi (ilk kâr-alma): {ara_hedef:,.2f} — burada "
            f"kademeli kâr al, kalanı ana hedefe taşı.")

    if hedef is not None:
        sat.append(
            f"🎯 Ana hedef: {hedef.alt:,.2f}–{hedef.ust:,.2f} "
            f"({hedef.renk} direnç, güç {hedef.guc:.0f})")

    if trend is not None:
        sat.append(
            f"📈 {trend.yon} trend çizgisi {trend.guncel_deger:,.2f} "
            f"seviyesinde ({trend.dokunus} dokunuş) — yapıyı destekliyor.")

    if kritik is not None:
        sat.append("")
        sat.append(
            f"❌ İPTAL: {kritik:,.2f} altında KAPANIŞ → yükseliş senaryosu "
            f"geçersiz, aşağı risk açılır.")

    return "\n".join(sat)


# Coin sembol → Türkçe konuşma dilindeki ad
_COIN_AD = {
    "BTCUSDT": "BTC", "ETHUSDT": "ETH", "SOLUSDT": "SOL",
    "BNBUSDT": "BNB", "XRPUSDT": "XRP", "AVAXUSDT": "AVAX",
}


def _tr_para(v: float) -> str:
    """1728.53 → '1.728,53' (Türkçe biçim, $ ile)."""
    s = f"{v:,.2f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def miraz_yorumu(symbol: str, s: Senaryo, vade: str = "Kısa vade") -> str:
    """Senaryoyu @tradermiraz üslubunda düz metin (tweet) yorumuna çevirir."""
    coin = _COIN_AD.get(symbol, symbol.replace("USDT", ""))
    renk = s.destek_kutu.renk.lower() if s.destek_kutu else "destek"

    sat = [f"{coin} | {vade} plan - Güncelleme", ""]

    if s.destek_kutu is not None:
        sat.append(
            f"Fiyatın {renk} kutuya kadar geri çekilmesini bekliyorduk. "
            f"Bu bölgede ({_tr_para(s.bolge_alt)}$ – {_tr_para(s.bolge_ust)}$) "
            f"fiyatın dönüş yapısı oluşturabileceğini takip ediyoruz.")
        if s.mavi_daire is not None:
            sat.append("")
            sat.append(
                f"Mavi daire ({_tr_para(s.mavi_daire)}$) bölgesinde Bullish "
                f"{s.mavi_daire_isim} harmonik yapısı tamamlanıyor — burası en "
                f"güvendiğim long girişi. Mavide alım düşünüyorum.")
        sat.append("")
        sat.append(
            f"Bu bölgede aranacak dönüşlerin {_tr_para(s.kritik_seviye)}$ "
            f"altında iptal olması gerekir.")
        sat.append(
            f"{_tr_para(s.kritik_seviye)}$ altında KAPANIŞ gelmediği sürece "
            f"yükseliş senaryosunu koruyorum.")
        if s.fitil_seviye is not None:
            sat.append(
                f"Fitil ihtimalini de hesaba kattığımızda, "
                f"{_tr_para(s.fitil_seviye)}$ bölgesine gelecek bir fitil "
                f"senaryoyu bozmaz (kapanış kritik, fitil değil).")
        if s.kirilma_riski:
            sat.append("")
            sat.append(
                f"Ancak dikkat: fiyat bu bölgeye oldukça hacimli geliyor "
                f"(geliş hacmi ~{s.gelis_hacim:.1f}× ortalama). Bu yüzden "
                f"direkt işlem almıyorum; bölgede dönüş yapısı teyit edilmeden "
                f"pozisyon açmam (hacimli geliş kırılma getirebilir).")
        if s.mtf_yapi == "problemli":
            sat.append("")
            sat.append(
                "Ancak büyük resimde dikkatli olmamız gereken bir nokta var: "
                "üst zaman dilimi yapısı hâlâ problemli görünüyor. Bu yüzden "
                "pozisyonu büyük tutmuyorum.")
    else:
        sat.append("Fiyat net bir destek kutusunun dışında; "
                   "yeni bölge oluşana kadar temkinli takip ediyorum.")

    if s.ara_hedef is not None:
        sat.append("")
        sat.append(
            f"Mor çizgide ({_tr_para(s.ara_hedef)}$) yavaş yavaş pozisyondan "
            f"ayrılmaya, kademeli kâr almaya bakarım.")

    if s.hedef_kutu is not None:
        sat.append(
            f"Ana hedef {_tr_para(s.hedef_kutu.alt)}$ – "
            f"{_tr_para(s.hedef_kutu.ust)}$ ({s.hedef_kutu.renk.lower()} kutu) "
            f"bölgesidir.")

    if s.trend is not None:
        sat.append(
            f"Yükselen trend çizgisi ({_tr_para(s.trend.guncel_deger)}$) "
            f"yapıyı destekliyor.")

    return "\n".join(sat)


def yazdir(symbol: str, interval: str, s: Senaryo,
           yorum: bool = True, vade: str = "Kısa vade") -> None:
    print(f"\n{'='*64}\n{symbol} / {interval} — Senaryo Planı\n{'='*64}")
    print(s.metin)
    print("=" * 64)
    if yorum:
        print("\n--- @tradermiraz tarzı yorum ---\n")
        print(miraz_yorumu(symbol, s, vade=vade))
        print()
