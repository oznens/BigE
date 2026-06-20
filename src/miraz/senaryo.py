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

from . import kutular as kt
from . import trend as tr
from .kutular import Kutu
from .trend import TrendCizgisi

# Fitil toleransı: kritik seviyenin bu kadar altına fitil senaryoyu bozmaz
_FITIL_TOL = 0.015  # %1.5


# Fiyatın bu kadar altındaki destekler tek "tepki bölgesi" sayılır
_BOLGE_MENZIL = 0.06  # %6


@dataclass
class Senaryo:
    fiyat: float
    yon: str                      # "Yükseliş tepkisi" / "Düşüş riski" / "Nötr"
    destek_kutu: Kutu | None      # tepki bölgesinin en yakın kutusu
    bolge_alt: float | None       # birleşik destek bölgesinin alt sınırı
    bolge_ust: float | None       # birleşik destek bölgesinin üst sınırı
    hedef_kutu: Kutu | None       # yukarı hedef (direnç)
    kritik_seviye: float | None   # altında KAPANIŞ = iptal
    fitil_seviye: float | None    # bu seviyeye fitil senaryoyu bozmaz
    trend: TrendCizgisi | None    # sadece yükselen destek çizgisi
    metin: str                    # okunabilir plan


def senaryo_uret(
    df: pd.DataFrame,
    n: int = 5,
    tolerans: float = 0.015,
    min_guc: float = 50.0,
    adaptif: bool = True,
) -> Senaryo:
    """Güncel piyasa yapısından koşullu bir plan üretir.

    adaptif=True ise kutu kümeleme toleransı ATR oynaklığına göre ayarlanır
    (Miraz'ın geniş bölgelerine daha yakın).
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

    hedef_kutu = min((k for k in direncler if k.merkez > fiyat),
                     key=lambda k: k.merkez - fiyat, default=None)

    # Trend devam formasyonu = yerel (son ~90 bar) yükselen destek çizgisi.
    # Geniş pencere genel düşüş trendini yakalar; Miraz yerel çizgi çizer.
    trend_cizgi = tr.trend_cizgisi_bul(df, "Destek", n=n, min_dokunus=2,
                                       son_n=90)
    if trend_cizgi is not None and trend_cizgi.yon != "Yükselen":
        trend_cizgi = None

    # Yön kararı: destek bölgesi varsa tepki beklentisi; yoksa nötr
    if destek_kutu is not None:
        yon = "Yükseliş tepkisi"
    else:
        yon = "Nötr"

    metin = _metin_uret(fiyat, yon, destek_kutu, bolge_alt, bolge_ust,
                        hedef_kutu, kritik, fitil, trend_cizgi)

    return Senaryo(
        fiyat=round(fiyat, 4), yon=yon, destek_kutu=destek_kutu,
        bolge_alt=bolge_alt, bolge_ust=bolge_ust,
        hedef_kutu=hedef_kutu, kritik_seviye=kritik, fitil_seviye=fitil,
        trend=trend_cizgi, metin=metin)


def _metin_uret(fiyat, yon, destek, bolge_alt, bolge_ust, hedef,
                kritik, fitil, trend) -> str:
    sat = [f"Güncel fiyat: {fiyat:,.2f}", f"Senaryo: {yon}", ""]

    if destek is not None:
        sat.append(
            f"📍 Destek bölgesi: {bolge_alt:,.2f}–{bolge_ust:,.2f} "
            f"(en güçlü kutu {destek.renk}, güç {destek.guc:.0f})")
        sat.append(
            f"   → {kritik:,.2f} altında KAPANIŞ yapılmadıkça bu bölgeden "
            f"tepki bekleniyor.")
        sat.append(
            f"   → {fitil:,.2f} bölgesine gelecek FİTİL senaryoyu bozmaz "
            f"(kapanış kritik, fitil değil).")
    else:
        sat.append("📍 Yakında güçlü destek kutusu yok — temkinli ol.")

    if hedef is not None:
        sat.append(
            f"🎯 Yukarı hedef: {hedef.alt:,.2f}–{hedef.ust:,.2f} "
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
    else:
        sat.append("Fiyat net bir destek kutusunun dışında; "
                   "yeni bölge oluşana kadar temkinli takip ediyorum.")

    if s.hedef_kutu is not None:
        sat.append("")
        sat.append(
            f"Tepki gelirse ilk hedef {_tr_para(s.hedef_kutu.alt)}$ – "
            f"{_tr_para(s.hedef_kutu.ust)}$ ({s.hedef_kutu.renk.lower()} kutu) "
            f"bölgesi olacaktır.")

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
