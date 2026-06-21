# Vaka Çalışması: GÜMÜŞ (Silver / XAGUSD) — Kısa Vade Trade Döngüsü

> Kaynak: @tradermiraz, 5 tweetlik flood (24 May – 15 Haz 2026), Gümüş/USD 4sa.
> Metodolojinin **kripto dışı (emtia)** bir enstrümanda da çalıştığını gösterir
> + yeni bir kavram getirir: **Mor çizgi** (ara kâr-alma seviyesi).

## Kurulum (24 May)

4 saatlik grafikte, pozisyon inşa edilecek bölgeler:

| Öğe | Seviye | Rol |
|---|---|---|
| 🔴 **Kırmızı kutu** | 81.481 – 82.525 | Ana direnç / üst hedef |
| 🟣 **Mor çizgi** | ~69.000 | Ara kâr-alma seviyesi (tek fiyat çizgisi) |
| 🔵 **Mavi kutu** | 63.334 – 65.185 | Talep bölgesi / LONG girişi |
| ⬜ **Gri harmonikler** | — | İki bullish harmonik, D'leri mavi kutuda |

Not: Harmonikler bu sefer **gri** gölgeli (TAO'da kırmızıydı) — renk Miraz'ın
tercihi, anlam aynı (XABCD alanı).

## Kronoloji

1. **24 May** — Kurulum. "Mevcut bölge rahat trade alanı değil; iki ana
   bölgeyi (mavi kutu) takip ediyorum." Hedef yukarıda kırmızı kutu.
2. **5 Haz** — **-%11**. Fiyat adım adım mavi kutuya iniyor. Günlük yapı hâlâ
   problemli (üst zaman dilimi uyarısı).
3. **10 Haz** — Fiyat **mavi kutuya ulaştı**, ~-%15 düşüş. "**61$ altında
   kapanış gelmediği sürece** 70$ test ihtimali sürüyor." (kritik=61, hedef=70)
4. **11 Haz** — "**Mor çizgilerde yavaş yavaş pozisyondan ayrılmaya bakınız.**"
   (mor çizgi = kâr-alma seviyesi)
5. **15 Haz** — **Bitiş.** ~-%20 düşüşün ardından **+%11 tepki**. Mavi kutuda
   (harmonik D, pembe daire ~65) long alındı, mor çizgi (69) ve 70$ test edildi.

## 🔑 Yeni ders: MOR ÇİZGİ

- **Mor kutu** (bölge) ≠ **Mor çizgi** (tek yatay fiyat seviyesi).
- Mor çizgi = girişle ana hedef arasındaki **ara kâr-alma (scale-out) seviyesi**.
- Genelde önceki bir konsolidasyon/swing bölgesinin yatay seviyesidir.
- Kural: "Mor çizgilerde yavaş yavaş pozisyondan ayrıl" = kısmi kâr al.

## Doğrulanan dersler (mevcut sisteme)
- ✅ **Kritik kapanış** kuralı: "61$ altında KAPANIŞ gelmedikçe" → bizde var.
- ✅ **Harmonik D ∩ mavi kutu = giriş** (mavi daire) → bizde var.
- ✅ **Üst zaman dilimi uyarısı**: "günlük yapı problemli" → MTF onayı (henüz yok).
- ✅ **Çoklu hedef**: mavi kutu girişi → mor çizgi (ara) → kırmızı kutu (ana).

## Sisteme yansıma (yapılacaklar)
- [x] **Mor çizgi** = giriş ile ana hedef arasındaki ara scale-out seviyesi.
      `Senaryo.ara_hedef` (en yakın direnç, ana hedeften önce). Plan + yoruma
      "Mor çizgide kademeli kâr al" satırı eklendi.
- [x] **MTF (üst zaman dilimi) uyarısı**: `senaryo_uret(df_ust=...)` → üst zaman
      yapısı düşüşteyse `mtf_yapi="problemli"`, planda/yorumda uyarı. CLI üst
      TF'yi otomatik çekiyor (4h→1d, 1h→4h).

> Gümüş vakasının dersleri sisteme yansıtıldı. ✅

Not: Gümüş (XAGUSD) Binance'te yok; veri katmanı şimdilik kripto. Vaka
metodoloji öğrenmek için; sistem aynı mantığı kripto paritelerde uyguluyor.
