"""R-bazlı risk yönetimi ve pozisyon boyutlama — @tradermiraz sistemi.

Miraz "1R = sabit dolar tutarı" mantığıyla çalışır: her işlemde risk edilen
para sabittir (ör. 25$). Pozisyon büyüklüğü, giriş ile stop arasındaki mesafeye
göre hesaplanır ki stop olunca tam 1R kaybedilsin. Ana trende KARŞI işlemlerde
pozisyon yarıya indirilir (½R).

Kurallar (risk.md):
  - Trend yönünde → tam R
  - Ana trende karşı (MTF problemli / market yapısı düşüş) → ½R
  - Stop kapanış bazlı (fitil seviyesi = sert stop)
  - Birinci hedefte %60–70 kâr, kalanı entry-stop ile taşı

Kullanım:
    from miraz.risk import risk_plani
    rp = risk_plani(senaryo, r_dolar=25)
    print(rp.aciklama)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RiskPlan:
    yon: str                  # "Long" / "Short" / "Nötr"
    giris: float              # planlanan giriş fiyatı
    stop: float               # sert stop (kapanış bazlı seviye)
    hedef: float | None       # ilk hedef (ana hedef alt sınırı)
    r_dolar: float            # 1R = risk edilen sabit dolar
    pozisyon_tipi: str        # "Güvenli" / "Dengeli" / "Riskli (½R)"
    poz_buyukluk_dolar: float # pozisyonun nominal büyüklüğü ($)
    poz_miktar: float         # alınacak miktar (adet/coin)
    risk_yuzde: float         # giriş→stop mesafesi (%)
    rr_orani: float | None    # risk/ödül oranı (hedef varsa)
    kar_al_birincil: float    # birinci hedefte kapatılacak oran (0.65)
    aciklama: str


def pozisyon_boyutu(giris: float, stop: float, r_dolar: float,
                    carpan: float = 1.0) -> tuple[float, float, float]:
    """(poz_dolar, poz_miktar, risk_yuzde) döndürür.

    poz_dolar  = nominal pozisyon büyüklüğü ($)
    poz_miktar = alınacak adet
    risk_yuzde = giriş→stop mesafesi (%)
    carpan     = R çarpanı (½R için 0.5)
    """
    mesafe = abs(giris - stop)
    if giris <= 0 or mesafe <= 0:
        return 0.0, 0.0, 0.0
    risk_orani = mesafe / giris          # stop olursa kayıp oranı
    riske_edilen = r_dolar * carpan
    poz_dolar = riske_edilen / risk_orani
    poz_miktar = poz_dolar / giris
    return round(poz_dolar, 2), round(poz_miktar, 6), round(risk_orani * 100, 2)


def _karsi_trend(senaryo) -> bool:
    """Long açısından ana trende karşı mıyız? (MTF problemli / yapı düşüş)."""
    if getattr(senaryo, "mtf_yapi", None) == "problemli":
        return True
    my = getattr(senaryo, "market_yapisi", None)
    if my is not None and getattr(my, "durum", None) == "düşüş":
        return True
    return False


def risk_plani(senaryo, r_dolar: float = 25.0,
               kar_al_birincil: float = 0.65) -> RiskPlan | None:
    """Senaryodan R-bazlı uygulanabilir bir risk planı üretir.

    Giriş  = mavi daire varsa orası, yoksa destek bölgesinin ortası.
    Stop   = fitil seviyesi (kritik kapanışın hemen altı).
    Hedef  = ara hedef (mor çizgi) varsa o, yoksa ana hedef kutusunun altı.
    Karşı trendde pozisyon yarıya indirilir (½R).
    """
    if getattr(senaryo, "destek_kutu", None) is None:
        return None
    bolge_alt = senaryo.bolge_alt
    bolge_ust = senaryo.bolge_ust
    if bolge_alt is None or bolge_ust is None:
        return None

    # Giriş seviyesi
    if senaryo.mavi_daire is not None:
        giris = float(senaryo.mavi_daire)
    else:
        giris = round((bolge_alt + bolge_ust) / 2, 4)

    # Stop: fitil seviyesi (yoksa kritik seviyenin biraz altı)
    if senaryo.fitil_seviye is not None:
        stop = float(senaryo.fitil_seviye)
    elif senaryo.kritik_seviye is not None:
        stop = round(float(senaryo.kritik_seviye) * 0.995, 4)
    else:
        return None
    if stop >= giris:                    # stop girişin altında olmalı (long)
        return None

    # Hedef: önce ara hedef (mor çizgi), yoksa ana hedef kutusu
    hedef = None
    if getattr(senaryo, "ara_hedef", None) is not None:
        hedef = float(senaryo.ara_hedef)
    elif getattr(senaryo, "hedef_kutu", None) is not None:
        hedef = float(senaryo.hedef_kutu.alt)

    # Karşı trend → ½R, pozisyon tipi
    karsi = _karsi_trend(senaryo)
    carpan = 0.5 if karsi else 1.0
    poz_dolar, poz_miktar, risk_yuzde = pozisyon_boyutu(
        giris, stop, r_dolar, carpan)

    rr = None
    if hedef is not None and hedef > giris:
        rr = round((hedef - giris) / (giris - stop), 2)

    if karsi:
        poz_tipi = "Riskli (½R) — ana trende karşı"
    elif rr is not None and rr >= 2.0:
        poz_tipi = "Güvenli"
    else:
        poz_tipi = "Dengeli"

    aciklama = _aciklama(giris, stop, hedef, r_dolar, carpan, poz_dolar,
                         poz_miktar, risk_yuzde, rr, poz_tipi, kar_al_birincil)

    return RiskPlan(
        yon="Long", giris=round(giris, 4), stop=round(stop, 4), hedef=hedef,
        r_dolar=r_dolar, pozisyon_tipi=poz_tipi,
        poz_buyukluk_dolar=poz_dolar, poz_miktar=poz_miktar,
        risk_yuzde=risk_yuzde, rr_orani=rr,
        kar_al_birincil=kar_al_birincil, aciklama=aciklama)


def _aciklama(giris, stop, hedef, r_dolar, carpan, poz_dolar, poz_miktar,
              risk_yuzde, rr, poz_tipi, kar_al) -> str:
    sat = [
        f"💰 RİSK PLANI ({poz_tipi})",
        f"   Giriş: {giris:,.2f}  |  Stop: {stop:,.2f} "
        f"(kapanış bazlı, %{risk_yuzde:.2f})",
    ]
    if hedef is not None:
        rr_txt = f"  |  R/R: {rr:.2f}" if rr is not None else ""
        sat.append(f"   Hedef: {hedef:,.2f}{rr_txt}")
    sat.append(
        f"   1R = {r_dolar:.0f}$" + (" (½R uygulandı)" if carpan < 1 else "") +
        f"  →  pozisyon ≈ {poz_dolar:,.2f}$ ({poz_miktar:g} adet)")
    sat.append(
        f"   Yönetim: birinci hedefte %{kar_al*100:.0f} kâr al, "
        f"kalanı girişe stop çekerek taşı (risk-free).")
    return "\n".join(sat)
