# Vaka Çalışması: TAO (Bittensor) — 4 Aylık Tam Trade Döngüsü

> Kaynak: @tradermiraz, 8 tweetlik flood (20 May – 8 Haz 2026), TAO/USDT 1G (günlük).
> Bu vaka, sistemin çekirdek konseptlerini (kutu rolleri + harmonik çakışma +
> hacim filtresi) gerçek, baştan sona planlanmış bir trade üzerinde doğruluyor.

## Kurulum (20 May) — 3 bölgeli yol haritası

Günlük grafikte ~4 aylık plan, **üç ön-işaretli bölge**:

| Bölge | Seviye | Rol |
|---|---|---|
| 🟣 **Mor kutu** | 293.47 – 302.26 | Ana direnç → **SHORT** bölgesi |
| 🟢 **Yeşil kutu** | 206.55 – 214.45 | İkincil destek → **LONG** bölgesi |
| 🔵 **Mavi daire** | 178.94 – 187.79 | En derin talep → **LONG** (en yüksek güven) |

Ek olarak grafikte **iki kırmızı harmonik pattern** (gölgeli XABCD üçgenleri)
çizili — patternlerin D noktaları talep bölgelerine işaret ediyor.

## Senaryonun gerçekleşmesi (kronoloji)

1. **20 May** — Mor direnç + Engulf mumuyla yükseliş. BTC devam ederse ivme sürer.
2. **22 May** — Fiyat mor kutuya kadar +%7 çıktı, oradan **-%8 reddedildi**. (Mor = direnç teyit)
3. **29 May** — 3 bölge netleştirildi; beklenen düşüş geldi, fiyat 246$.
4. **3 Haz** — **-%25** düşüş. "Plan çok netti, mor kutu fiyatı düşürdü." BTC'de sert satış.
5. **5 Haz** — **-%30**. (Felsefi not: piyasa gürültüsü/kalabalık.)
6. **6 Haz** — Mor'dan **-%36**. Fiyat **Mavi daireye** çekildi. Yeşil'de işlem
   ALINMADI. **"Mavide aldım. 210$ bekliyorum."** Mavi daireden zaten +%6.
7. **7 Haz** — **Kâr alımı.** Roller net: Mor → short, Yeşil + Mavi daire → long.
   Yeşil **atlandı** çünkü fiyat oraya **hacimli** geldi (kırılma riski).
8. **8 Haz** — Mavi daireden **+%20** yükseliş. Pozisyon 215–220$'a taşındı,
   220 direncinde reddedildi, kâr alındı. **Analiz bitti.**

## 🔑 Çıkarılan dersler (sistemimiz için)

### 1. Mavi DAİRE — yeni kavram
"Mavi kutu"dan farklı olarak **daire** ile işaretlenir: en derin, en yüksek
güvenli talep noktası. Tipik olarak **bullish harmonik D noktasının** tamamlandığı
yerdir. Bu, en güçlü long girişi (= bizim "çakışma" konseptimizin en saf hali:
harmonik PRZ + en güçlü destek).

### 2. Bölge rolleri YÖNLÜdür
- 🟣 Mor = **SHORT** bölgesi (direnç)
- 🟢 Yeşil + 🔵 Mavi = **LONG** bölgeleri (destek)
Bizim senaryo motoru bunu zaten yapıyor (destek→long, direnç→short) ama
çoklu-bölge yol haritası (aynı anda 3 bölge) henüz yok.

### 3. Harmonik + bölge çakışması = en kaliteli setup ✅
TAO'da ikinci bullish harmonik'in D noktası **tam mavi dairede** tamamlandı ve
Miraz orada long aldı. Bu, bizim `cakisma.py` modülünün birebir karşılığı —
gerçek bir trade'de %20 kazançla doğrulandı.

### 4. Hacim filtresi — zon atlama kuralı
"Yeşil kutuya geldiğinde işlem almadık çünkü fiyat bölgeye **hacimli** geldi."
Kural: **bir destek bölgesine yüksek hacimle gelinirse o bölge kırılma
adayıdır → işlem alma.** (notlar/kutular.md'de var, henüz mekanikleştirilmedi.)

### 5. Kâr alma = bir üst bölge
Giriş mavi daire → hedef yeşil kutu/220 direnci. Tepki, bir sonraki zona kadar.
Bizim "ana hedef" mantığımızla uyumlu.

## Sistemimize yansıması (yapılacaklar)
- [ ] **Mavi daire** = harmonik D ∩ en güçlü destek → `cakisma.py`'de özel "daire"
      işareti / en yüksek skor etiketi.
- [ ] **Hacim filtresi**: destek bölgesine geliş hacmi yüksekse senaryoda
      "kırılma riski — işlem alma" uyarısı.
- [ ] **Çoklu-bölge yol haritası**: aynı anda mor(short)/yeşil(long)/mavi(long)
      bölgelerini tek planda listele (HTF günlük).
