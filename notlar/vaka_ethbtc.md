# Vaka Çalışması: ETH/BTC Oranı — Göreceli Güç (Makro) Analizi

> Kaynak: @tradermiraz, 3 tweet (16 Ara 2025 – 19 Mar 2026), ETH/BTC 1G.
> Yeni kavram: **ALT/BTC oran grafiği** ile göreceli güç okuması (makro filtre).

## Fikir

Fiyatı USDT yerine **BTC cinsinden** (ETH/BTC oranı) izlemek, altcoin'in
Bitcoin'e karşı **güç kazanıp kaybetmediğini** gösterir:
- Oran **düşüyorsa** → ETH, BTC'ye karşı **zayıf** (USD'de yükselse bile geride)
- Oran **yükseliyorsa** → ETH güçleniyor

## Çağrı ve sonuç

- **16 Ara 2025**: ETH/BTC grafiğinde "ETH bir süre güç kaybedecek; 0.041
  üzerinde günlük kapanış olmazsa düşüş" dedi. ETH o an **3000$**.
- **4 Şub 2026**: "Kırmızı kutu / mavi daireden düşüş olacağını belirtmiştik."
  ETH **2240$**'a inmiş.
- **19 Mar 2026**: Oran 0.0363 → ~0.0255 fraktal bölgesine düştü; ETH **1800$**
  bandını test etti. **Çağrı aynen tuttu.** ✅

## Grafik öğeleri

| Öğe | Anlam |
|---|---|
| 🔴 Kırmızı kutu (0.0363–0.0370) | Oran direnci (ETH zirvesi) |
| 🔵 Mavi daire (dirençte) | Harmonik D — bearish dönüş (tepe) |
| 🟢 Yeşil daire (destekte) | Harmonik D — bullish dönüş (dip) |
| 🟪 Mor harmonikler | İki büyük XABCD |
| 🔵 "Önemli fraktal bölgesi" (0.0255–0.0262) | Tekrarlayan kilit S/R |

## 🔑 Dersler

### 1. ALT/BTC oranı = göreceli güç filtresi (mekanikleştirilebilir)
Binance'te doğrudan pariteler var (ETHBTC, SOLBTC...). Oranın trendi, bir
altcoin'in USDT senaryosuna **makro yön** verir: oran düşüyorsa long'a temkinli.

### 2. Daire rengi ≈ dönüş yönü
- 🟢 Yeşil daire = destekte bullish dönüş (long)
- 🔵 Mavi daire = dirençte bearish dönüş (short) VEYA destekte long (TAO)
Renk Miraz'ın stili; özü "harmonik D = dönüş noktası (PRZ)".

### 3. Fraktal bölge = tekrarlayan kilit S/R
Geçmişte defalarca tepki vermiş, fraktal olarak önemli yatay bölge.

## Sisteme yansıma (yapılacaklar)
- [x] **ALT/BTC oran filtresi**: `oran.goreceli_guc(symbol)` ETHBTC/SOLBTC
      paritesinin trendini hesaplar (güçleniyor/zayıflıyor/nötr); senaryoya
      makro bağlam satırı olarak eklendi. CLI otomatik hesaplıyor.

> ETH/BTC vakasının dersi sisteme yansıtıldı. ✅
> İlginç: bugün ETHBTC ≈ 0.0271 — Miraz'ın işaret ettiği fraktal bölgeye
> (0.0255–0.0262) yaklaşmış, çağrısı tutmuş.
