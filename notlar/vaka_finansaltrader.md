# Vaka Çalışması: @finansalTRader — Miraz'ın Hocası (yeni öğrenme kaynağı)

> Kaynak: Xquik API ile @finansalTRader arşivi (824 benzersiz tweet,
> Eyl 2025 – Nis 2026). "Trader & Analist, Mentör & Eğitmen". Miraz'ın
> bio'sunda "🎓 Öğretmenim: @finansalTRader".

## Temel fark: HOCA İNDİKATÖR KULLANIR

Miraz saf Price Action'a (indikatörsüz) indirgemiş; hoca daha **klasik ve
geniş** bir araç seti kullanıyor. Metin madenciliğiyle çıkan, Miraz'da
OLMAYAN kavramlar:

| Kavram | Geçiş | Tür |
|---|---|---|
| **Fibonacci Retracement (0.618)** | 21 | fiyat-bazlı ⭐ |
| düzeltme / itme (Elliott) | 75 + 4 | dalga teorisi |
| **RSI** | 42 | indikatör |
| **divergence + "trend yorgunluğu"** | 10 | indikatör (RSI) |
| DXY (Dolar Endeksi) | 33 | makro |
| dalga yapıları (Elliott) | 37 | dalga teorisi |
| EMA / SMA / MACD | 13 | indikatör (hareketli ort.) |
| wedge (takoz) | 6 | formasyon |
| OBO (omuz-baş-omuz) | 5 | formasyon |
| VIX | 4 | makro |

### Örnek kullanım
- **Fib 0.618**: *"Fiyat Direnç ve Fib.Retr 0,618 bölgesinden %21'lik bear
  tepkisini vererek öngördüğümüz 66K bölgesine salındı."* (3 Haz, BTCUSD)
- **Divergence/trend yorgunluğu**: *"Teknik olarak trendin yorulduğunu,
  divergence'nin geliştiğini ve bunların Bear hareketi getirebileceğini
  yazmıştık."* (27 May, GUA)
- **Elliott dalga**: *"Fiyat çizdiğimiz dalga yapılarını şimdilik izliyor."*

## 🔑 Bu turda uygulanan: Fibonacci Retracement (`fib.py`)

Hocanın en sık ve en saf fiyat-bazlı aracı:
- `fib_retracement(df)` → son büyük swing'in (dip↔tepe) Fibonacci geri
  çekilme ızgarası: 0.236 / 0.382 / 0.5 / **0.618** / **0.705** / 0.786
- **Golden pocket** (0.618–0.705) vurgulanır: yükselişte destek, düşüşte
  direnç adayı. Fiyat golden pocket içindeyse "tepki izle" uyarısı.
- Senaryoya entegre: plan metnine "📐 Fib geri çekilme... golden pocket" satırı;
  `Senaryo.fib` alanı.
- Canlı: BTC/ETH/SOL 4h'de golden pocket direnç bölgeleri tespit edildi.

## Beklemedeki hoca-spesifik kavramlar (not)
- [ ] **RSI + divergence** (trend yorgunluğu): fiyat HH ama RSI LH = bearish
      uyumsuzluk. İndikatör gerektirir — Miraz felsefesinden sapma, ama hoca
      kaynaklı meşru ek. Mekanikleştirilebilir.
- [ ] **Elliott Wave** (itme/düzeltme, ABC, dalga yapıları): daha karmaşık.
- [ ] **Hareketli ortalamalar** (EMA/SMA) ve **MACD**.
- [ ] **DXY / VIX makro** filtreleri (dominance ile birlikte).
- [ ] Wedge (takoz) — flama'nın yönlü varyantı.

> Hoca @finansalTRader incelendi. En değerli saf-fiyat aracı (Fibonacci
> Retracement / golden pocket) sisteme eklendi. İndikatör-bazlı araçlar
> (RSI divergence, Elliott, EMA) beklemede — sistemin felsefi yönüne göre
> opsiyonel. 79/79 test geçiyor.
