# Vaka Çalışması: BTC/Altın Oranı — Göreceli Güç (Makro) Analizi

> Kaynak: @tradermiraz, 2 tweet (Haz 2026), BTC/Altın (XAUT) 1G.
> Yeni kavram: BTC'nin **Altın karşısındaki göreli gücü** — altcoin/BTC analiziyle aynı mantık, bir üst boyuta taşındı.

## Fikir

ETH/BTC oranı ETH'nin BTC'ye karşı gücünü gösterdiği gibi, **BTC/Altın oranı** BTC'nin emtia para birimine karşı gücünü gösterir:
- Oran **düşüyorsa** → BTC, Altın'a karşı **zayıf** (USD'de yükselse de reel değer kayıpları olabilir)
- Oran **yükseliyorsa** → BTC güçleniyor

Binance.US'ta doğrudan BTC/Altın paritesi yok; `BTCUSDT / PAXGUSDT` sentetik oranıyla hesaplanır.

## 1. Tweet — Göreceli Güç Çöküşü

- BTC/Altın oranı dirençte (kırmızı kutu / bearish harmonik D) → **geri çekilme beklentisi**
- "BTC ezilmeye devam edecek" yorumu
- Hedef: mavi kutu ve altındaki yeşil kutu

## 2. Tweet — Yol Haritası (Haz 5, 2026)

Grafik: BTC vs Gold · 1G · XAUT cinsinden

| Seviye | Bölge | Anlam |
|---|---|---|
| ~17.94 | 🔴 Kırmızı daire (bearish D) | Harmonik tepe — onaylandı, kısa/çıkış |
| 14.25–14.44 | 🔵 Mavi kutu | Güçlü destek — şu an kırılıyor |
| 12.82–13.36 | 🟢 Yeşil kutu | Bir sonraki destek hedefi |
| 18.71–20.00 | 🟣 Mor kutu | Toparlanma hedefi (direnç) |
| ~19.x (mor kutuda 🟢 daire) | Gelecek bullish D | Yeşil kutudan sıçrarsa burası hedef |

**Yön oku**: Aşağı (yeşil kutu ~12.8) → sonra yukarı (mor kutu ~18.7)

### Harmonik yapı
- Gri boyama: Tamamlanmış bearish harmonik (büyük X-A-B-C-D)
- D noktası kırmızı dairede (~17.94) → dönüş onaylandı
- Yeşil daire mor kutuda = uzak vadeli bullish harmonik D projeksiyonu

## Grafik öğeleri

| Öğe | Anlam |
|---|---|
| 🔴 Kırmızı daire (~17.94) | Bearish harmonik D (tepe onayı) |
| 🔵 Mavi kutu (14.25–14.44) | Güçlü destek (LONG tabanı) |
| 🟢 Yeşil kutu (12.82–13.36) | İkincil destek / düşüş hedefi |
| 🟣 Mor kutu (18.71–20.00) | Direnç / toparlanma hedefi |
| 🟢 Yeşil daire (mor kutuda) | Uzak vadeli bullish harmonik D |

## 🔑 Dersler

### 1. BTC/Altın = üst katman makro filtre
ALT→BTC→Altın zinciri:
- ALT'ın durumu BTC'ye göre (ETHBTC vs BTC trendi)
- BTC'nin durumu Altın'a göre (BTC/Altın oranı)
BTC/Altın zayıfsa, USD bazında yükselen BTC bile reel değer kaybediyor. Makro bağlamı anlamak için oran grafiği zorunlu.

### 2. Sentetik oran: BTCUSDT / PAXGUSDT
Binance'te doğrudan BTC/XAU paritesi yok. PAX Gold (PAXGUSDT ≈ 1 ons altın) bölerek sentetik oran üretilir.

### 3. Harmonik + renkli kutu birlikte okunur
Bearish harmonik D kırmızı dirençte tamamlandı → hedef aşağıdaki destek kutuları. Bu iki metodoloji (harmonik + kutu) birbirini teyit eder.

## Sisteme yansıma (yapılacaklar)
- [x] **BTC/Altın oran filtresi**: `oran.goreceli_guc("BTCUSDT")` → `BTCUSDT/PAXGUSDT` sentetik oranını hesaplar
- [x] **`GoreceliGuc.benchmark`** alanı eklendi: "BTC" veya "Altın"
- [x] **`metin()`** güncellendi: "Altın'a karşı ZAYIFLIYOR" formatı
- [x] **Türkçe dilbilgisi**: "BTC'ye karşı" (vokal uyumu) — "BTC'a" → "BTC'ye" düzeltildi

> BTC/Altın vakasının dersi sisteme yansıtıldı. ✅
> Haz 2026: BTC/Altın oranı ~14.05 — mavi kutu (14.25–14.44) altına gerilemiş, yeşil kutu (12.82–13.36) hedefte.
