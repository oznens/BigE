# Kaynak Özetleri

## 1. `Best of Big E I.pdf` (59 sayfa)
**Big E (forum kullanıcı adı: eelfranz, gerçek adı: Eric)** isimli emekli trader'ın
**Forex Factory** forumunda 2010 civarı açtığı *"Trading Made Simple"* başlıklı
mega-konunun en önemli mesajlarının derlemesi.

- Eric önce stocks, sonra FX trade etmiş; küçük TF'lerde çok kaybetmiş.
- 2+ yıl boyunca metodu sadeleştirmiş, fazla indikatörü atmış.
- Kendisini "%70-80 isabet" ile tanımlıyor (kendi iddiası).
- Vurgu: **simplicity, az indikatör, yüksek timeframe (4h ve üstü)**.

## 2. `Best of Big E II.pdf` (11 sayfa)
Aynı içerikten daha temiz, ayıklanmış özet. Kitapçık formatında. Başlıklar:
General Info, Timeframe, Basic Rules, Detailed Description, Psychology.
Kuralları en net haliyle bu dosya veriyor — modeli buradan çıkaracağız.

## 3. `Trading Made Simple.r.docx` (~78k karakter)
**RobinHood (Uncle R)** isimli başka bir trader'ın Big E vefat ettikten
sonra açtığı *"Trading Made Simple(r)"* konusunun derlemesi. Big E'nin
metodunu temel almış ama **TDI'ı çıkarmış**, yerine:
- HMA(12) (Hull Moving Average)
- Synergy_APB (Average Price Bars)
- RSI(14) + 50 line
- Stochastic(8,3,3) + Stochastic(14,3,3)
- 5 EMA shift+2 (Big E'den kalan tek şey)
- Heikin Ashi (Big E'den kalan tek şey)

eklemiş. **Bu varyant kullanışlı ama bizim için referans** — esas Big E'nin
orijinal kurallarını koda dökeceğiz, RobinHood'un katkıları ileri faz için.

---

## Ana fikir (üç kaynağın ortak özü)
1. **Heikin Ashi** mum kullan — psikolojik olarak çok daha sakin
2. **Yüksek timeframe** (4h ve 1D) — düşük TF'de broker seni öldürür
3. **TDI** ana sinyal: yeşil çizgi kırmızıyı kestiğinde gir
4. **Trend yönü** + **momentum** + **stochastic teyit** üçü uyuştuğunda gir
5. **Stop loss** son swing high/low'da (2 mum geri)
6. **Çıkış** yeşil çizgi düzleşince/dönünce/check-mark yapınca
7. **Pas geçilen durumlar** consolidation, küçük mumlar, S/R'a yakınlık, news
