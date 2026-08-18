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


# terminalMiraz standart TP: hedefi girişe, STOP mesafesi kadar simetrik
# uzaklığa koyar (R/R = 1R). Görsellerde (Deep Crab TAOUSDT, dashboard
# HBAR/ALGO) entry↔TP mesafesi = entry↔SL mesafesi → mor kutu/yapısal hedef
# DEĞİL, sabit R uzaklığı. Bu çarpan kaç R uzağa TP koyulacağını belirler.
RR_HEDEF = 1.0


def mesafe_hedef(giris: float, stop: float,
                 rr_carpan: float = RR_HEDEF) -> float:
    """Girişe, risk mesafesinin rr_carpan katı uzaklıkta TP (terminalMiraz tarzı).

    Long  (stop < giriş): hedef = giriş + rr_carpan·(giriş − stop)  → üstte
    Short (stop > giriş): hedef = giriş − rr_carpan·(stop − giriş)  → altta
    """
    risk = abs(giris - stop)
    return giris + rr_carpan * risk if stop < giris else giris - rr_carpan * risk


def harmonik_stop_sec(giris: float, bolge_stop: float | None,
                      harmonik_detay: dict | None, taraf: str) -> float | None:
    """Harmonik X-invalidasyonu geçerliyse PA bölge stopuna tercih et."""
    detay = harmonik_detay or {}
    aday = detay.get("sl")
    if aday is not None:
        aday = float(aday)
        if (taraf == "Long" and aday < giris) or (
                taraf == "Short" and aday > giris):
            return aday
    return float(bolge_stop) if bolge_stop is not None else None


def _f(v: float) -> str:
    """Fiyat için hassasiyet-duyarlı format (kuruş-altı coinler)."""
    a = abs(v)
    if a >= 1:
        ond = 2
    elif a >= 0.1:
        ond = 4
    elif a >= 0.01:
        ond = 5
    elif a >= 0.0001:
        ond = 6
    else:
        ond = 8
    return f"{v:,.{ond}f}"


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
               kar_al_birincil: float = 0.65,
               rr_hedef: float = RR_HEDEF) -> RiskPlan | None:
    """Senaryodan R-bazlı uygulanabilir bir risk planı üretir.

    Giriş  = mavi daire varsa orası, yoksa destek bölgesinin ortası.
    Stop   = fitil seviyesi (kritik kapanışın hemen altı).
    Hedef  = terminalMiraz tarzı: girişe STOP mesafesi kadar uzaklık (1R).
             Mor kutu / yapısal hedef değil — sabit R çarpanı (rr_hedef).
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

    # Harmonik D girişi varsa pattern motorunun X-invalidasyon stopu kullanılır.
    # PA bölge stopuyla karıştırmak harmonik risk/1R hedefini değiştirir.
    harmonik = (getattr(senaryo, "harmonik_detay", None)
                if senaryo.mavi_daire is not None else None)
    stop = harmonik_stop_sec(giris, senaryo.fitil_seviye, harmonik, "Long")
    if stop is None:
        if senaryo.kritik_seviye is not None:
            stop = round(float(senaryo.kritik_seviye) * 0.995, 4)
        else:
            return None
    if stop >= giris:                    # stop girişin altında olmalı (long)
        return None

    # Hedef: terminalMiraz tarzı — girişe stop mesafesi kadar uzaklık (rr_hedef·R)
    hedef = round(mesafe_hedef(giris, stop, rr_hedef), 6)

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
        f"   Giriş: {_f(giris)}  |  Stop: {_f(stop)} "
        f"(kapanış bazlı, %{risk_yuzde:.2f})",
    ]
    if hedef is not None:
        rr_txt = f"  |  R/R: {rr:.2f}" if rr is not None else ""
        sat.append(f"   Hedef: {_f(hedef)}{rr_txt}")
    sat.append(
        f"   1R = {r_dolar:.0f}$" + (" (½R uygulandı)" if carpan < 1 else "") +
        f"  →  pozisyon ≈ {poz_dolar:,.2f}$ ({poz_miktar:g} adet)")
    sat.append(
        f"   Yönetim: birinci hedefte %{kar_al*100:.0f} kâr al, "
        f"kalanı girişe stop çekerek taşı (risk-free).")
    return "\n".join(sat)


# ----------------------------------------------------------------------------
# Kademeli giriş (laddered entry) — arşiv dersi: "kademe kademe alırım"
# ----------------------------------------------------------------------------

@dataclass
class Kademe:
    no: int             # kademe sırası (1, 2, ...)
    seviye: float       # bu kademenin giriş fiyatı
    agirlik: float      # toplam riskteki payı (0..1)
    poz_dolar: float    # bu kademenin nominal büyüklüğü ($)
    poz_miktar: float   # bu kademede alınacak miktar


@dataclass
class KademeliPlan:
    kademeler: list      # list[Kademe]
    ort_giris: float     # ağırlıklı ortalama giriş (miktara göre)
    stop: float
    hedef: float | None
    toplam_dolar: float  # tüm kademelerin nominal toplamı
    r_dolar: float       # toplam risk (stop olursa kayıp)
    rr_orani: float | None
    aciklama: str


def kademeli_plan(senaryo, r_dolar: float = 25.0,
                  paylar: tuple = (0.5, 0.5)) -> KademeliPlan | None:
    """Pozisyonu birden çok destek seviyesine bölen kademeli giriş planı.

    Miraz "kademe kademe alırım" / "birinci kademe, ikinci kademe" der: alımı
    tek noktaya değil, üst destekten alt desteğe yayar. Toplam risk (stop
    olursa kayıp) yine r_dolar'dır; paylar bunu kademelere böler.

    Kademe seviyeleri:
      1) üst destek: mavi daire varsa orası, yoksa bölge üstü
      2) alt destek: bölge altı (kritik seviye civarı)
    Ek paylar verilirse üst↔alt arasına eşit aralıklı dağıtılır.
    """
    if getattr(senaryo, "destek_kutu", None) is None:
        return None
    bolge_alt = senaryo.bolge_alt
    bolge_ust = senaryo.bolge_ust
    if bolge_alt is None or bolge_ust is None:
        return None

    ust = float(senaryo.mavi_daire) if senaryo.mavi_daire is not None \
        else float(bolge_ust)
    alt = float(bolge_alt)
    if ust <= alt:
        ust, alt = alt, ust * 0.999

    # Stop: fitil (yoksa kritik altı)
    if senaryo.fitil_seviye is not None:
        stop = float(senaryo.fitil_seviye)
    elif senaryo.kritik_seviye is not None:
        stop = round(float(senaryo.kritik_seviye) * 0.995, 4)
    else:
        return None
    if stop >= alt:
        return None

    paylar = tuple(paylar)
    pay_top = sum(paylar)
    if pay_top <= 0:
        return None
    paylar = tuple(p / pay_top for p in paylar)   # normalize

    # Seviyeler: üstten alta eşit aralıklı
    k = len(paylar)
    if k == 1:
        seviyeler = [ust]
    else:
        adim = (ust - alt) / (k - 1)
        seviyeler = [round(ust - i * adim, 4) for i in range(k)]

    karsi = _karsi_trend(senaryo)
    r_carpan = 0.5 if karsi else 1.0

    kademeler = []
    toplam_dolar = 0.0
    toplam_miktar = 0.0
    for i, (sev, pay) in enumerate(zip(seviyeler, paylar), start=1):
        # bu kademe pay*r_dolar kadar risk eder (stop ortak)
        pd, pm, _ = pozisyon_boyutu(sev, stop, r_dolar, carpan=r_carpan * pay)
        kademeler.append(Kademe(no=i, seviye=sev, agirlik=round(pay, 3),
                                poz_dolar=pd, poz_miktar=pm))
        toplam_dolar += pd
        toplam_miktar += pm

    ort_giris = round(toplam_dolar / toplam_miktar, 4) if toplam_miktar else 0.0

    # Hedef: ortalama girişe stop mesafesi kadar uzaklık (terminalMiraz, rr_hedef·R)
    hedef = round(mesafe_hedef(ort_giris, stop), 6) if ort_giris > stop else None

    rr = None
    if hedef is not None and hedef > ort_giris and ort_giris > stop:
        rr = round((hedef - ort_giris) / (ort_giris - stop), 2)

    aciklama = _kademe_aciklama(kademeler, ort_giris, stop, hedef,
                                toplam_dolar, r_dolar, r_carpan, rr)
    return KademeliPlan(
        kademeler=kademeler, ort_giris=ort_giris, stop=round(stop, 4),
        hedef=hedef, toplam_dolar=round(toplam_dolar, 2), r_dolar=r_dolar,
        rr_orani=rr, aciklama=aciklama)


def _kademe_aciklama(kademeler, ort_giris, stop, hedef, toplam, r_dolar,
                     r_carpan, rr) -> str:
    sat = [f"🪜 KADEMELİ GİRİŞ ({len(kademeler)} kademe"
           + (", ½R" if r_carpan < 1 else "") + ")"]
    for kd in kademeler:
        sat.append(
            f"   {kd.no}. kademe {_f(kd.seviye)}  "
            f"(%{kd.agirlik*100:.0f} pay → {kd.poz_dolar:,.2f}$)")
    rr_txt = f"  |  R/R: {rr:.2f}" if rr is not None else ""
    sat.append(
        f"   Ort. giriş {_f(ort_giris)}  |  Stop {_f(stop)}  |  "
        f"Toplam ≈ {toplam:,.2f}$ (risk {r_dolar*r_carpan:.0f}$){rr_txt}")
    if hedef is not None:
        sat.append(f"   Hedef {_f(hedef)} — kademeli kâr al, kalanı taşı.")
    return "\n".join(sat)
