# Renkli Kutu Konsepti — @tradermiraz

> "indikatör kullanmıyorum" — grafik analizinde saf fiyat aksiyonu + renkli kutular.

Kutular TradingView'da çizilen renkli dikdörtgen bölgelerdir.
Her rengin farklı bir anlamı var.

## 🔵 Mavi Kutu (Cyan/Blue Box)
- **Anlam**: Birincil giriş bölgesi, güçlü talep alanı
- **Kullanım**: Fiyat bu bölgeye geldiğinde long fırsatı aranır
- **Kural**: Alt zaman diliminde dönüş yapısı beklenir, direkt dalmak yok
- **Örnek tweet**: "Mavide aldım. 210$ seviyelerine kadar yükselmesini ön görüyorum."
- **Örnek**: SOL'da $68.18-$70.83 arası mavi kutu, fiyat bölgeye gelince long

## 🟣 Mor Kutu (Purple Box)
- **Anlam**: Güçlü direnç bölgesi, kar alma alanı
- **Kullanım**: Long pozisyon bu bölgede hafifletilir / kısmen kapatılır
- **Kural**: Mor kutuya ulaşınca %60-70 kar alımı, kalan kısım entry'e stop çekilerek taşınır
- **Dikkat**: Mor kutuda "yeni ATH geliyor" yorumlarına karşı temkinli olunur
- **Örnek tweet**: "Mor kutudan yeşil ve mavi bölgeye kadar sarkacağını öngör."

## 🟢 Yeşil Kutu (Green Box)
- **Anlam**: İkincil destek, bazen sağlam bazen kırılır
- **Kullanım**: Dikkatli değerlendirme gerekir — fiyat hacimli geliyorsa işlem alınmaz
- **Kural**: Yeşil kutuda bile hacime bakılır; hacimli geliyorsa bölgeyi geçebilir
- **Örnek tweet**: "Yeşil kutuya kadar düşüş öngörülebilir."

## 🔴 Kırmızı Kutu (Red Box)
- **Anlam**: (a) Güçlü direnç VEYA (b) Uzun vadeli dip bölgesi (varlığa göre değişir)
- **Uzun vade long için**: Kırmızı kutuda fiyat dinlenince, alt zamanda dönüş görününce giriş
- **Short için**: Fiyat kırmızı kutuya gelince satış fırsatı
- **Kural**: Kırmızı kutuda direkt dalmak yok — önce fiyatın bölgede "dinlenmesi" beklenir

## 🟠 Turuncu Kutu (Orange Box)
- **Anlam**: Ara nefes bölgesi, geçici destek
- **Örnek tweet**: "Turuncu bölge ara bir nefes alanı olarak çalışacaktır."

## 🟤 Kahverengi/Sarı Shading (Yellow/Beige Area)
- **Anlam**: Harmonik pattern alanı (PRZ - Potential Reversal Zone)
- Sarı shaded triangle = harmonik X-A-B-C-D kolu gösterimi

## Genel Kurallar
1. Fiyat destek bölgesine ne kadar sert ve hacimli gelirse, kırılma ihtimali o kadar artar
2. Bölgede kalıcılık = bölgenin çalıştığının onayı
3. Kapanış önemli — "X$ altında KAPANIŞ" kriteri vardır (fitil yetmez)
4. Bölge kaybedilince direnç görevi görür (eski destek → yeni direnç)
5. Alt zaman diliminde dönüş yapısı görülmeden büyük pozisyon alınmaz

## Otomatik Tespit (src/miraz/kutular.py)
Elle çizilen kutuları mekanikleştirmek için:
1. **Pivot kümeleme**: swing high/low pivotları fiyat bandına göre (%1.5 tol.)
   gruplanır; ≥2 pivotun değdiği band = aday bölge.
2. **Güç puanı (0–100)**: dokunuş sayısı (%50) + tazelik (%25) + bölge hacmi
   (%25). Çok dokunulan + taze + hacimli bölge = güçlü.
3. **Renge çevirme** (mevcut fiyata göre):
   - Fiyatın altı, güç≥65 → 🔵 Mavi | 45–65 → 🟢 Yeşil | <45 → 🟠 Turuncu
   - Fiyatın altı, >%25 uzak + güçlü → 🔴 Kırmızı (uzun vade dip)
   - Fiyatın üstü, ≤%25 + güç≥55 → 🟣 Mor (kar alma) | <55 → 🟠 Turuncu
   - Fiyatın üstü, >%25 uzak → 🔴 Kırmızı
4. **Mesafe filtresi**: ±%35'ten uzak bölgeler elenir (işlem yapılabilir
   bölgelere odak). Çıktı fiyata yakınlığa göre sıralanır.

> Uyarı: orijinal kutular elle çizildiğinden bu sınıflandırma sezgiseldir;
> amaç tradermiraz mantığını otomatikleştirmek, birebir taklit değil.

Çalıştırma: `python backtest/kutu_tara.py --sembol BTCUSDT --tf 4h --min-guc 50`
