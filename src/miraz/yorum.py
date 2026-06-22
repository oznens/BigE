"""Miraz yorumu — @tradermiraz tarzı setup yorumu üretici.

5.054 tweet + 7.731 chart'tan damıtılan metodolojiyi (tweetler/METODOLOJI.md)
uygular: renk-kodlu bölge dili, çift tepe/harmonik/OB yapıları, yön mantığı,
yeşil-daire tetiği, geçersizlik şartı, R/R ve disiplin mantrası.

Sistemin hesapladığı veriden (taraf, giriş/stop/hedef, harmonik patern, PA
konsept katmanları) onun sesiyle bir plan metni kurar. Saf string işi —
ağır bağımlılık yok, kolay test edilir.
"""

from __future__ import annotations

# Zaman dilimi → vade etiketi (METODOLOJI §5)
_VADE = {
    "15m": "Scalp", "30m": "Çok Kısa Vade", "1h": "Kısa Vade",
    "2h": "Kısa-Orta Vade", "4h": "Orta Vade", "1d": "Uzun Vade",
}

# PA konsept katmanı → Miraz sözlüğü (METODOLOJI §2-3)
_KONSEPT_SOZ = {
    "Cavity": "dengesizlik (FVG) bölgesi",
    "Root": "kök talep/arz (order block) bölgesi",
    "Shade": "destek/direnç gölgesi",
    "Strike": "likidite / stop-avı seviyesi",
    "Shear": "trend kırılımı (MSB)",
    "Ladder": "kademeli yapı (HH-HL / LH-LL)",
    "Buffer": "tampon bölge",
    "Reservoir": "hacim / likidite havuzu",
    "Drift": "trend eğilimi",
    "Torque": "momentum ivmesi",
}

# İmza mantraları (METODOLOJI §6) — kategoriye göre döndürülür
_MANTRA = [
    "Disiplini bozmazsan, grafik zaten sana yol gösterir.",
    "Piyasa kimseye acımaz, sadece disiplinli olanı ödüllendirir.",
    "Risk düşür (kar al) ve plana sadık kalmaya devam et.",
    "Plan net: yukarı → satış, aşağı → destek tepkisi.",
    "Küçük risk al, planı bozma.",
    "İzleyelim bakalım.",
]

_COIN_AD = {
    "BTCUSDT": "Bitcoin", "ETHUSDT": "Ethereum", "SOLUSDT": "Solana",
    "BNBUSDT": "BNB", "XRPUSDT": "XRP", "DOGEUSDT": "Dogecoin",
}


def _fmt(x) -> str:
    """Fiyatı okunaklı biçimle (binlik nokta, gereksiz sıfır yok)."""
    if x is None:
        return "—"
    try:
        x = float(x)
    except (TypeError, ValueError):
        return str(x)
    if x >= 1000:
        return f"{x:,.0f}".replace(",", ".") + "$"
    if x >= 1:
        return f"{x:.2f}".rstrip("0").rstrip(".") + "$"
    return f"{x:.6f}".rstrip("0").rstrip(".") + "$"


def _coin(symbol: str) -> str:
    return _COIN_AD.get(symbol, symbol.replace("USDT", ""))


def _yapilar(taraf: str, pattern, konsept_isimleri) -> list[str]:
    """Tespit edilen yapıları Miraz diliyle cümlelere döker."""
    short = taraf == "Short"
    c = []
    if pattern:
        c.append(f"Harmonik **{pattern}** paterni PRZ bölgesinde tamamlanıyor; "
                 f"oran teyidiyle dönüş aranır.")
    ks = set(konsept_isimleri or [])
    if "Shear" in ks:
        yon = "aşağı" if short else "yukarı"
        c.append(f"Trend kırılımı (MSB) {yon} yönde gerçekleşmiş; yapı bu yönü destekliyor.")
    if "Root" in ks:
        rol = "arz" if short else "talep"
        c.append(f"Fiyat bir kök {rol} (order block) bölgesinden tepki veriyor.")
    if "Cavity" in ks:
        c.append("Geride doldurulacak bir dengesizlik (FVG) var; fiyat oraya çekilebilir.")
    if "Strike" in ks:
        c.append("Yakında likidite / stop-avı seviyesi bulunuyor; manipülasyona dikkat.")
    if not c:
        # patern/konsept yoksa klasik S/R + kırılım anlatımı
        if short:
            c.append("Çift tepe / arz bölgesi sonrası trend kırılımı beklentisi öne çıkıyor.")
        else:
            c.append("Çift dip / talep bölgesi sonrası trend kırılımı beklentisi öne çıkıyor.")
    return c


def miraz_yorum(symbol: str, interval: str, taraf: str,
                giris=None, stop=None, hedef=None, rr=None,
                pattern: str | None = None,
                konseptler=None, kategori: str = "Watch",
                guven: float | None = None) -> dict:
    """Bir setup için @tradermiraz tarzı yorum üretir.

    Döndürür: {"baslik", "ozet", "govde": [str], "mantra", "metin"}.
    `konseptler` — konsept isimleri listesi (örn. ["Shear","Root"]) veya
    {"isim": ...} sözlükleri listesi.
    """
    short = taraf == "Short"
    coin = _coin(symbol)
    vade = _VADE.get(interval, "Plan")
    tf_et = interval if interval not in ("1d",) else "Günlük"

    # konsept isimlerini normalize et
    knames = []
    for k in (konseptler or []):
        knames.append(k.get("isim") if isinstance(k, dict) else k)
    knames = [k for k in knames if k]

    baslik = f"{coin} | {tf_et} — {vade} Plan"

    # 1) ana beklenti / yön
    if short:
        ozet = ("Ana beklenti **aşağı yönlü**. Yükselişler satış fırsatı olarak "
                "değerlendirilir.")
    else:
        ozet = ("Ana beklenti **yukarı yönlü**. Geri çekilmeler alım fırsatı olarak "
                "değerlendirilir.")

    govde: list[str] = []

    # 2) bölge tanımı (renk-kodlu)
    if short:
        govde.append(f"📍 Mor kutu (strateji bölgesi): **{_fmt(giris)}** — short'un "
                     f"tetikleneceği arz alanı.")
    else:
        govde.append(f"📍 Mavi kutu (talep bölgesi): **{_fmt(giris)}** — long için "
                     f"toplama alanı.")

    # 3) yapı / patern
    govde.extend(_yapilar(taraf, pattern, knames))

    # 4) yön mantığı
    if short:
        govde.append(f"👉 Yukarı → **{_fmt(giris)}** mor kutudan satış · "
                     f"Aşağı → **{_fmt(hedef)}** hedef bölgesi.")
    else:
        govde.append(f"👉 Aşağı → **{_fmt(giris)}** mavi kutudan alım · "
                     f"Yukarı → **{_fmt(hedef)}** hedef bölgesi.")

    # 5) tetik (yeşil daire) + onay şartı
    govde.append("🟢 Tetik: fiyat içerisinde trend kırılımı → yeşil daire (onay). "
                 "Hacimli mum kapanışı beklenir, fitil yanıltır.")

    # 6) geçersizlik
    yon_kelime = "üzerinde" if short else "altında"
    govde.append(f"❗ Geçersizlik: **{_fmt(stop)}** {yon_kelime} hacimli kapanışlar "
                 f"bu yapıyı iptal eder.")

    # 7) R/R + yönetim
    if rr:
        govde.append(f"⚖️ Yaklaşık **{float(rr):.1f}R** ödül/risk. Kâr alınca girişe "
                     f"stop çek (breakeven), riski azalt.")

    # kategori notu
    if kategori == "Trade":
        ozet = "✅ " + ozet + " Yapı olgun, tetik yakın."
    elif kategori == "Watch":
        ozet = "👀 İzleme: " + ozet + " Tetik/onay henüz gelmedi."
    else:
        ozet = "⏭️ " + ozet + " Şartlar tam oluşmadı, beklemede."

    # mantra seçimi (kategori + tarafa göre deterministik)
    idx = (len(knames) + (1 if short else 0) + (0 if kategori == "Trade" else 2)) % len(_MANTRA)
    mantra = _MANTRA[idx]

    metin = (f"{baslik}\n\n{ozet}\n\n" + "\n".join(govde) +
             f"\n\n🧠 {mantra}\n⚠️ Yatırım tavsiyesi değildir.")

    return {"baslik": baslik, "ozet": ozet, "govde": govde,
            "mantra": mantra, "metin": metin}
