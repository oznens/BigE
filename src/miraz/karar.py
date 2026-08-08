"""Karar motoru (Setup Intelligence) — terminalMiraz "PriceActionLab" katmanı.

Her setup'a Trade / Watch / Skip, kalite ve güven skoru üretir. P5 ile sinyal
katkıları opsiyonel özellik ağırlıklarıyla kalibre edilebilir. ``agirliklar``
verilmezse tüm çarpanlar 1.0'dır ve eski davranış aynen korunur.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class KararSonuc:
    karar: str
    kalite: str
    guven: float
    gerekceler: list = field(default_factory=list)
    metin: str = ""


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


def _w(agirliklar: dict[str, float] | None, ad: str) -> float:
    """Özellik çarpanını güvenli aralıkta döndürür.

    Kalibrasyon katmanı normalde 0.5–1.5 üretir. Buradaki daha geniş 0–2 sınırı
    elle verilen kötü bir ayarın skoru patlatmasını engeller.
    """
    if not agirliklar:
        return 1.0
    try:
        return max(0.0, min(2.0, float(agirliklar.get(ad, 1.0))))
    except (TypeError, ValueError):
        return 1.0


def karar_uret(senaryo, rr: float | None = None,
               ek_guven: float = 0.0, ek_gerekce: str | None = None,
               agirliklar: dict[str, float] | None = None) -> KararSonuc:
    """Senaryoyu Trade/Watch/Skip kararına ve A-D kalitesine bağlar.

    ``agirliklar`` yalnız katkı büyüklüğünü değiştirir; sert engellerin anlamını
    değiştirmez. Böylece validation döneminde seçilen ağırlıklar OOS/canlıda
    aynı karar motoruna uygulanabilir.
    """
    guven = 50.0
    ger: list[str] = []

    if getattr(senaryo, "destek_kutu", None) is None:
        return KararSonuc(
            karar="Skip", kalite="D", guven=0.0,
            gerekceler=["Yakında güçlü destek kutusu yok"],
            metin="🚫 KARAR: Skip — destek bölgesi yok (D).")

    def ekle(ad: str, temel: float, aciklama: str) -> float:
        nonlocal guven
        katki = temel * _w(agirliklar, ad)
        guven += katki
        ger.append(f"{aciklama} ({katki:+.1f})")
        return katki

    d = senaryo.destek_kutu
    g = getattr(d, "guc", 50)
    ekle("destek", (g - 50) / 50 * 15, f"Destek gücü {g:.0f}")

    if getattr(senaryo, "mavi_daire", None) is not None:
        ekle("mavi_daire", 15, "Mavi daire (harmonik D ∩ destek)")

    if getattr(senaryo, "pamonic", False):
        ekle("pamonic", 15, "🔷 PaMonic (harmonik D ∩ güçlü PA kutusu)")

    mtf = getattr(senaryo, "mtf_yapi", None)
    if mtf == "sağlıklı":
        ekle("htf", 10, "Üst zaman dilimi sağlıklı")
    elif mtf == "problemli":
        ekle("htf", -15, "Üst zaman dilimi problemli")

    my = getattr(senaryo, "market_yapisi", None)
    if my is not None:
        durum = getattr(my, "durum", None)
        if durum == "yükseliş":
            ekle("market_yapisi", 10, "Market yapısı yükseliş")
        elif durum == "düşüş":
            ekle("market_yapisi", -15, "Market yapısı düşüş")

    hacim_riski = bool(getattr(senaryo, "kirilma_riski", False))
    if hacim_riski:
        ekle("hacim_riski", -12, "Hacimli geliş — kırılma riski")

    if getattr(senaryo, "trend", None) is not None:
        ekle("trend", 6, "Yükselen trend çizgisi")

    ik = getattr(senaryo, "ikili", None)
    if ik is not None:
        if ik.tip == "Çift Dip" and ik.onayli:
            ekle("ikili", 10, "Onaylı çift dip")
        elif ik.tip == "Çift Tepe" and ik.onayli:
            ekle("ikili", -12, "Onaylı çift tepe — long aleyhine")

    tm = getattr(senaryo, "temas", None)
    if tm is not None and getattr(tm, "guven_etkisi", 0):
        etki = float(tm.guven_etkisi) * _w(agirliklar, "temas")
        guven += etki
        if tm.son_davranis == "kırılma":
            ger.append(f"Temas: bölge son sefer kırıldı ({etki:+.1f})")
        elif tm.toplam == 0:
            ger.append(f"Temas: taze bölge ({etki:+.1f})")
        else:
            ger.append(f"Temas: %{tm.tepki_orani*100:.0f} tepki, "
                       f"{tm.tepki + tm.kirilma} test ({etki:+.1f})")

    dv = getattr(senaryo, "divergence", None)
    if dv is not None:
        if dv.tip == "Bullish":
            ekle("divergence", 8, "Bullish divergence — long lehine")
        elif dv.tip == "Bearish":
            ekle("divergence", -10, "Bearish divergence — long aleyhine")

    if rr is not None:
        if rr >= 2.0:
            ekle("rr", 10, f"R/R {rr:.1f} ≥ 2")
        elif rr >= 1.0:
            ekle("rr", 3, f"R/R {rr:.1f}")
        else:
            ekle("rr", -5, f"R/R {rr:.1f} < 1")

    if getattr(senaryo, "hedef_kutu", None) is not None:
        ekle("hedef", 4, "Ana hedef tanımlı")

    if ek_guven:
        etki = float(ek_guven) * _w(agirliklar, "cluster")
        guven += etki
        ger.append(ek_gerekce or f"Cluster hafızası ({etki:+.1f})")

    guven = max(0.0, min(100.0, guven))
    kalite = _kalite(guven)

    if guven >= 70 and not hacim_riski:
        karar = "Trade"
    elif guven >= 50:
        karar = "Watch"
    else:
        karar = "Skip"
    if hacim_riski and karar == "Trade":
        karar = "Watch"

    ikon = {"Trade": "✅", "Watch": "👁️", "Skip": "🚫"}[karar]
    metin = (f"{ikon} KARAR: {karar}  |  Kalite: {kalite}  |  "
             f"Güven: %{guven:.0f}")
    return KararSonuc(karar=karar, kalite=kalite, guven=round(guven, 1),
                      gerekceler=ger, metin=metin)
