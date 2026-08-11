"""Karar motoru (Setup Intelligence) — terminalMiraz benzeri karar katmanı.

Miraz'ın yazılım ekranında (PriceActionLab) her setup'a bir KARAR etiketi
(Trade / Watch / Skip), bir KALİTE notu (A+/A/B/C/D) ve bir GÜVEN yüzdesi
atanıyor. Arşiv sayısal ağırlıkları ve eşikleri açıklamaz. Bu modül gözlenen
arayüzü, BigE'ye ait kalibre edilmemiş bir heuristic skorla mekanikleştirir:
senaryoda zaten hesaplanan
tüm sinyalleri (mavi daire, MTF, market yapısı, hacim riski, RR, çift tepe/dip,
trend) tek bir güven skoruna ve karara bağlar.

Kullanım:
    from miraz.karar import karar_uret
    k = karar_uret(senaryo, rr=1.9)
    print(k.metin)
"""

from __future__ import annotations

from dataclasses import dataclass, field


SKOR_MODELI = "BigE heuristic v1"
SKOR_KANIT_DURUMU = "weights-unverified"

# Bu sayılar tweetlerden çıkarılmış Miraz kuralları değildir. Davranışı geriye
# dönük uyumlu tutmak ve ileride backtest ile kalibre etmek için tek yerde
# açıkça tutulurlar. Kanıtlanan kısım yalnız kalite/güven çıktısının varlığıdır.
BIGE_SKOR_AGIRLIKLARI = {
    "taban": 50.0,
    "destek_olcek": 15.0,
    "mavi_daire": 15.0,
    "pamonic": 15.0,
    "mtf_saglikli": 10.0,
    "mtf_problemli": -15.0,
    "yapi_yukselis": 10.0,
    "yapi_dusus": -15.0,
    "hacim_riski": -12.0,
    "trend": 6.0,
    "cift_dip": 10.0,
    "cift_tepe": -12.0,
    "bull_div": 8.0,
    "bear_div": -10.0,
    "rr_2": 10.0,
    "rr_1": 3.0,
    "rr_zayif": -5.0,
    "hedef": 4.0,
    "trade_esik": 70.0,
    "watch_esik": 50.0,
}


@dataclass
class KararSonuc:
    karar: str           # "Trade" / "Watch" / "Skip"
    kalite: str          # "A+" / "A" / "B" / "C" / "D"
    guven: float         # 0–100 güven yüzdesi
    gerekceler: list = field(default_factory=list)  # +/− katkı açıklamaları
    metin: str = ""
    skor_modeli: str = SKOR_MODELI
    skor_kanit_durumu: str = SKOR_KANIT_DURUMU


def _kalite(guven: float) -> str:
    if guven >= 85:
        return "A+"
    if guven >= 75:
        return "A"
    if guven >= 65:
        return "B"
    if guven >= 50:
        return "C"
    return "D"


def karar_uret(senaryo, rr: float | None = None,
               ek_guven: float = 0.0, ek_gerekce: str | None = None
               ) -> KararSonuc:
    """Senaryoyu Trade/Watch/Skip kararına ve A-D kalitesine bağlar.

    Güven skoru BigE heuristic tabanından başlar; her sinyal +/− katkı yapar. Sert
    engeller (destek yok / hacimli kırılma riski) kararı sınırlar.

    ek_guven: dışarıdan (ör. cluster hafızası) gelen güven düzeltmesi. İki-geçişli
    akış için: önce ek_guven=0 ile temel karar üretilir, imzaya göre cluster
    bulunur, sonra ek_guven verilerek nihai karar üretilir.
    """
    w = BIGE_SKOR_AGIRLIKLARI
    guven = w["taban"]
    ger: list[str] = []

    if getattr(senaryo, "destek_kutu", None) is None:
        return KararSonuc(
            karar="Skip", kalite="D", guven=0.0,
            gerekceler=["Yakında güçlü destek kutusu yok"],
            metin="🚫 KARAR: Skip — destek bölgesi yok (D).")

    # Destek gücü
    d = senaryo.destek_kutu
    g = getattr(d, "guc", 50)
    katki = (g - 50) / 50 * w["destek_olcek"]
    guven += katki
    ger.append(f"Destek gücü {g:.0f} ({katki:+.0f})")

    # Mavi daire (harmonik D ∩ destek)
    if getattr(senaryo, "mavi_daire", None) is not None:
        guven += w["mavi_daire"]
        ger.append("Mavi daire (harmonik D ∩ destek) (+15)")

    # PaMonic (Price Action + Harmonic): harmonik D, GÜÇLÜ bir PA destek kutusuyla
    # (OrderBlock) çakışıyorsa nadir ama güçlü kombinasyon — ekstra güven.
    if getattr(senaryo, "pamonic", False):
        guven += w["pamonic"]
        ger.append("🔷 PaMonic (harmonik D ∩ güçlü PA kutusu) (+15)")

    # MTF üst zaman dilimi
    mtf = getattr(senaryo, "mtf_yapi", None)
    if mtf == "sağlıklı":
        guven += w["mtf_saglikli"]; ger.append("Üst zaman dilimi sağlıklı (+10)")
    elif mtf == "problemli":
        guven += w["mtf_problemli"]; ger.append("Üst zaman dilimi problemli (−15)")

    # Market yapısı (bu TF)
    my = getattr(senaryo, "market_yapisi", None)
    if my is not None:
        durum = getattr(my, "durum", None)
        if durum == "yükseliş":
            guven += w["yapi_yukselis"]; ger.append("Market yapısı yükseliş (+10)")
        elif durum == "düşüş":
            guven += w["yapi_dusus"]; ger.append("Market yapısı düşüş (−15)")

    # Hacimli geliş = kırılma riski
    hacim_riski = bool(getattr(senaryo, "kirilma_riski", False))
    if hacim_riski:
        guven += w["hacim_riski"]; ger.append("Hacimli geliş — kırılma riski (−12)")

    # Trend çizgisi desteği
    if getattr(senaryo, "trend", None) is not None:
        guven += w["trend"]; ger.append("Yükselen trend çizgisi (+6)")

    # Çift tepe/dip
    ik = getattr(senaryo, "ikili", None)
    if ik is not None:
        if ik.tip == "Çift Dip" and ik.onayli:
            guven += w["cift_dip"]; ger.append("Onaylı çift dip (+10)")
        elif ik.tip == "Çift Tepe" and ik.onayli:
            guven += w["cift_tepe"]; ger.append("Onaylı çift tepe — long aleyhine (−12)")

    # Temas davranışı (bölge geçmişte tepki mi verdi, kırıldı mı?)
    tm = getattr(senaryo, "temas", None)
    if tm is not None and getattr(tm, "guven_etkisi", 0):
        etki = tm.guven_etkisi
        guven += etki
        if tm.son_davranis == "kırılma":
            ger.append(f"Temas: bölge son sefer kırıldı ({etki:+.0f})")
        elif tm.toplam == 0:
            ger.append(f"Temas: taze bölge ({etki:+.0f})")
        else:
            ger.append(
                f"Temas: %{tm.tepki_orani*100:.0f} tepki, "
                f"{tm.tepki + tm.kirilma} test ({etki:+.0f})")

    # RSI divergence (hoca dersi — trend yorgunluğu)
    dv = getattr(senaryo, "divergence", None)
    if dv is not None:
        if dv.tip == "Bullish":
            guven += w["bull_div"]; ger.append("Bullish divergence — long lehine (+8)")
        elif dv.tip == "Bearish":
            guven += w["bear_div"]; ger.append("Bearish divergence — long aleyhine (−10)")

    # Risk/Ödül
    if rr is not None:
        if rr >= 2.0:
            guven += w["rr_2"]; ger.append(f"R/R {rr:.1f} ≥ 2 (+10)")
        elif rr >= 1.0:
            guven += w["rr_1"]; ger.append(f"R/R {rr:.1f} (+3)")
        else:
            guven += w["rr_zayif"]; ger.append(f"R/R {rr:.1f} < 1 (−5)")

    # Hedef tanımlı
    if getattr(senaryo, "hedef_kutu", None) is not None:
        guven += w["hedef"]; ger.append("Ana hedef tanımlı (+4)")

    # Dışarıdan gelen düzeltme (cluster hafızası — geçmiş benzer setup başarısı)
    if ek_guven:
        guven += ek_guven
        ger.append(ek_gerekce or f"Cluster hafızası ({ek_guven:+.0f})")

    guven = max(0.0, min(100.0, guven))
    kalite = _kalite(guven)

    # Karar: güven + sert engeller
    if guven >= w["trade_esik"] and not hacim_riski:
        karar = "Trade"
    elif guven >= w["watch_esik"]:
        karar = "Watch"
    else:
        karar = "Skip"
    # Hacimli kırılma riski varken en fazla Watch (önce teyit)
    if hacim_riski and karar == "Trade":
        karar = "Watch"

    ikon = {"Trade": "✅", "Watch": "👁️", "Skip": "🚫"}[karar]
    metin = (f"{ikon} KARAR: {karar}  |  Kalite: {kalite}  |  "
             f"Güven: %{guven:.0f}")
    return KararSonuc(karar=karar, kalite=kalite, guven=round(guven, 1),
                      gerekceler=ger, metin=metin)
