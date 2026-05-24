# Big E Modeli — Kural Seti

Birincil kaynak: `Best of Big E II.pdf` (kuralların en net halini içeren özet).
İkincil destek: `Best of Big E I.pdf` (forum yazıları), `Trading Made Simple.r.docx` (RobinHood türevi).

## 1. Kullanılan İndikatörler

### 1.1 Heikin Ashi mumlar (zorunlu)
- Normal Japon mumları yerine HA mumları kullanılır.
- HA formülü:
  - `HA_close = (open + high + low + close) / 4`
  - `HA_open = (önceki HA_open + önceki HA_close) / 2`
  - `HA_high = max(high, HA_open, HA_close)`
  - `HA_low  = min(low,  HA_open, HA_close)`
- Renk: `HA_close >= HA_open` → yeşil (yukarı), `<` → kırmızı (aşağı).

### 1.2 TDI — Traders Dynamic Index (ana sinyal)
Big E'nin sadeleştirilmiş versiyonu. İki çizgi + üç referans seviye:

- **RSI baz**: `RSI(close, 13)`
- **Yeşil çizgi (Price Line)**: `SMA(RSI, 2)` — hızlı
- **Kırmızı çizgi (Signal Line)**: `SMA(RSI, 7)` — yavaş
- **Referans seviyeler**: 32 (oversold), 50 (orta), 68 (overbought)
- **Volatility bandı** (opsiyonel, bilgi amaçlı): RSI üzerine `BB(34, 1.6185)`
  — Big E "extra crap" diye anlatıyor ama paylaştığı chart'larda noktalı
  bantlar görünüyor. Biz koda bilgi amaçlı koyacağız, **sinyal üretmeyecek**.

> Notalı bantlar nadiren yorumda işe yarayabilir (RSI'ın "açtığı/kapandığı"
> momentum okuması). Big E aktif olarak kullanmıyor.

### 1.3 Stochastic (8, 3, 3) — sadece teyit
- Periyot 8, %K smoothing 3, %D smoothing 3.
- 20-80 aralığında ne yöne bakıyorsa o yönde teyit verir.
- TDI ile aynı yönü göstermiyorsa **pas geç**.

### 1.4 5 EMA shift +2 — bilgi amaçlı
- `EMA(close, 5)` 2 mum sağa kaydırılmış.
- Big E giriş için kullanmıyor; sadece "fiyat 5EMA çevresinde nasıl
  davranıyor" göstergesi olarak ekranda tutuyor.

## 2. Entry Kuralları

### 2.1 Normal Cross Entry (LONG)
Hepsi aynı anda doğru olmalı:
1. TDI yeşil çizgi kırmızı çizgiyi **YUKARI** kesmiş (cross)
2. Bu cross **HA reversal'ının 1. veya 2. mumunda** olmalı (3. mum ve sonrası pas)
3. HA mum rengi yeşile döndü
4. TDI yeşil çizginin açısı "saat 12-2" arası (dik yukarı) — zayıfsa (2-4 arası) pas
5. Stochastic(8,3,3) yukarı yönü teyit ediyor (yukarı bakan, 20-80 arası)
6. **Tetikleyici an**: Yeni mum açılışında gir (mum kapanışını bekleme — ama isteğe göre teyit için kapanış da kullanılabilir)

### 2.2 Normal Cross Entry (SHORT) — Aynalı
1. TDI yeşil kırmızıyı **AŞAĞI** keser
2. HA reversal'ının 1-2. mumunda
3. HA mum rengi kırmızıya döndü
4. TDI yeşil açısı "saat 4-6" arası (dik aşağı)
5. Stochastic aşağı teyit ediyor

### 2.3 Bounce Entry (devam trade'i)
- Trend zaten var, TDI yeşil kırmızıya yaklaştı ama **kesmeden geri sekti**.
- Yeşilin geri seken açısı 12-2 (long) / 4-6 (short) ise gir.
- Cross trade'inden daha riskli, ama yine de geçerli.

## 3. Skip Filtreleri (girmediği durumlar)

Aşağıdakilerden HERHANGİ BİRİ varsa pas geçer:

- HA mumları küçük → consolidation → pas
- TDI yeşil açısı zayıf (2-4 arası, "saat") → pas
- Long düşünülüyorsa TDI 68'e çok yakın / Short düşünülüyorsa 32'ye çok yakın → pas
- Yakında önemli S/R seviyesi var (sola bakınca) → pas
- Stochastic TDI ile çelişiyor → pas
- Major news yaklaşıyor (FF Calendar kırmızı) → news sonrası bekle
- Cross olduktan 3+ mum geçmişse → pas, başka kurulum ara

## 4. Exit Kuralları

TDI yeşil çizgi şunlardan birini yaparsa **çık**:
1. Düzleşir (flat)
2. Eğilmeye başlar (hook over)
3. Check-mark dönüş (V şeklinde kırılma) yapar

Ek (Big E forumda söylüyor):
- Trade aleyhine 10-15 pip giderse hemen çık, dönüş olursa tekrar gir (bounce).
- Yeşil "worm" gibi kırmızıyı geçmeden üstünde dalgalanırsa pozisyonda kal,
  kırmızıyı resmi olarak kesene kadar.

## 5. Stop Loss

- **Long**: Girilen mumdan **2 mum geri** swing low'un hemen altı
- **Short**: Girilen mumdan **2 mum geri** swing high'ın hemen üstü
- Hard SL koymadan önce: Big E uyandığı zaman manuel çıkış yapıyor;
  ama 4h gece tradelerinde son swing'e SL koyup uyuyor.

> Alternatif: ATR(10) × 2 (RobinHood'un katkısı, fena değil — backtest'te
> her ikisini de deneyeceğiz).

## 6. Pozisyon Yönetimi

### 6.1 Re-entry
- Trade kâra geçtikten sonra geri çekilirse ve TDI yeniden sinyal verirse
  tekrar gir.
- Güçlü trendlerde aynı yönde 2-4 lot kademeli ekleme yapıyor.

### 6.2 R-multiple (RobinHood ekledi, faydalı)
- 3 birime böl
- +1R'da 1 birim çık, kalan 2 birimi BE'ye taşı
- +2R'da 1 birim daha çık, kalan 1 birimi +1R'a taşı
- Son birim trail edilir, TDI exit gelene kadar

## 7. Zaman / Trade Saatleri (Big E orijinali, FX için)

- 4h trade gece (Big E Pasifik saatiyle 22:00 — TR saatiyle 08:00)
- Mum yenilenmesi UTC 00/04/08/12/16/20 → İstanbul 03/07/11/15/19/23
- London open en iyi seans

**Bizim için (kripto):**
- Binance 24/7; UTC 00:00 günlük mum kapanışı = İstanbul 03:00
- 4h mumlar UTC 00/04/08/12/16/20 = İstanbul 03/07/11/15/19/23
- Sinyal kontrolü mum kapanışından hemen sonra yapılır
