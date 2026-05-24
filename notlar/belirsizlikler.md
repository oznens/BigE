# Belirsizlikler / Sana Soracaklarım

Kaynaklarda netleşmeyen, koda dökerken karar vermemiz gereken noktalar.
Backtest çalışmadan önce bunları konuşalım.

## 1. Piyasa farkı — FX → Kripto
Big E forex'te trade ediyor. Kripto için bazı şeyler doğal olarak farklı:
- "Pip" yok → biz **%** veya **ATR** birimleri kullanacağız
- "London Open / NY Open" yok → 24/7, ama yine de likidite saatleri var
- Spread çok daha düşük → bu lehimize
- **Karar**: Pip yerine yüzde, "session" filtreleri kaldırılacak

## 2. TDI cross "açısı" (saat 12-2, 4-6) — nasıl ölçülecek?
Big E öznel olarak "saat kollarına bak" diyor. Otomatize etmek için:
- (A) Son N mumdaki yeşil çizginin eğimi (slope) ≥ threshold
- (B) Yeşil çizginin son hareket miktarı (örn. son 2 mum farkı)
- (C) Açı filtresini hiç koyma, sadece cross + diğer şartlara bak

**Default tercih**: (A) ile başlayalım, threshold ayarlanabilir parametre olsun.

## 3. "S/R'a yakınlık" filtresi — nasıl tanımlayacağız?
"Sola bak, eski hi/lo varsa pas" diyor. Algoritma:
- (A) Son N mumdaki swing high/low'ları bul; mevcut fiyat ATR×k içindeyse pas
- (B) Skip et, tamamen TDI'a bırak

**Default tercih**: (A), N=50, k=1.0 ile başlayalım.

## 4. "Consolidation / küçük mumlar" — nasıl tespit?
- HA gövde boyu / ATR oranı eşiğinden küçükse consolidation say
- Default: gövde < 0.3 × ATR(14) → "küçük mum"

## 5. Long/short ikisi de mi?
- Big E FX'te ikisini de yapıyor (short da uzun da)
- Kripto spot'ta short yapılamaz; futures veya margin gerekir
- **Soru sana**: Backtest'i spot mu (sadece long), futures mı (long+short) yapalım?

## 6. Exit sinyali otomasyonu
TDI yeşil için 3 exit tetiği var (flat / hook / check-mark). Otomatik karar için:
- **Flat**: Son 2-3 mumda yeşilin eğimi |slope| < eşik
- **Hook**: Yeşil pozitif eğimden negatife döndü (long için)
- **Check-mark**: Yeşil kırmızıyı tekrar kesti (asıl resmi exit)

İlk versiyonda 3'ünü de tek formülle birleştirip "yeşil kırmızıyı ters
kesti VEYA momentum kayboldu" diye kullanabiliriz. Sonra ayırırız.

## 7. R-multiple ölçekli çıkış mı, tek seferde mi?
RobinHood 3 birime bölüp +1R/+2R/+3R'da kademeli çıkıyor. Big E full lot
girip TDI exit'te full çıkıyor. İkisini de mod olarak ekleyebiliriz.

**Default tercih**: Önce basit (tek seferde TDI exit), karşılaştırma için
R-multiple modunu da ekleyelim.

## 8. Multi-symbol mu, tek sembol mü?
Big E aynı anda "Three Amigos" trade ediyor. Kripto'da BTC-ETH-SOL gibi
korelasyonlu sepet düşünülebilir. Önce **tek sembol** (BTCUSDT) ile
başlayıp doğrulayalım, sonra multi-symbol ekleriz.

## 9. Komisyon ve slipaj
Binance spot taker: %0.075 (BNB indirim %25 ile ~%0.056). Futures taker %0.04.
- Default: 7 bps komisyon (her bacak), 2 bps slipaj
- Sana göre değiştirilir.

## 10. Bunlar dışında merak ettiğin/eklemek istediğin bir şey?
- Big E daha çok bahsetmediği bir kural?
- Senin görüşünce kritik bir filtre/parametre?
