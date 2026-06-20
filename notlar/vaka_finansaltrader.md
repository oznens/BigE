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

## İkinci tur: hoca araçlarının tamamı eklendi ✅
- [x] **İndikatörler** (`indikator.py`): RSI (Wilder), EMA, SMA, MACD —
      yalnızca OHLC'den hesaplanır.
- [x] **RSI divergence** (`divergence.py`): fiyat HH + RSI LH = bearish
      (trend yorgunluğu); fiyat LL + RSI HL = bullish. Karar motoruna da
      bağlandı (bearish −10, bullish +8 güven).
- [x] **Elliott Wave** (`elliott.py`): 5'li itme (1-2-3-4-5, klasik kurallar)
      veya 3'lü ABC düzeltme etiketlemesi.
- [x] Senaryoya entegre: plan metnine 📉/📈 divergence ve 🌊 Elliott satırları.
- [ ] **DXY / VIX makro**: Binance.US yalnızca kripto sunar; bu TradFi
      endeksleri için dış veri kaynağı gerekiyor → **veri-kısıtlı**, ertelendi.
- [ ] Wedge (takoz): flama'nın yönlü varyantı, opsiyonel.

### Felsefi not
Miraz indikatörsüz çalışır; bu araçlar **hoca kaynaklı** ve opsiyonel bir
katmandır. Senaryo planında ayrı satırlar olarak görünür; çekirdek Price
Action kararını (mavi daire, kutu, market yapısı) ezmez, yalnızca teyit/uyarı
katkısı yapar.

> Hoca @finansalTRader tamamen incelendi ve **tüm mekanikleştirilebilir
> araçları** (Fibonacci, RSI, divergence, Elliott, EMA/MACD) sisteme eklendi.
> Yalnızca DXY/VIX veri-kısıtlı olduğu için ertelendi. 87/87 test geçiyor.

---

## Grafik (görsel) incelemesi — "bitti mi" doğrulaması

824 tweet'in metni madenlendikten sonra, grafiklerden de tarih/kavram
çeşitliliğine göre temsili örneklem incelendi:

| Grafik | Gözlem | Sonuç |
|---|---|---|
| BTC Fib (8 May) | "Fibo Retr.. 0,618" etiketi 81.779'da kırmızı kutu | `fib.py` ✅ birebir |
| LONG SETUP eğitim (28 Mar) | **"PRZ İşlem giriş Bölgesi = Fibo Retr 0.618–0.786"** + Elliott + trend kırılımı + ölçülü hedef | `fib.py`+`elliott.py` ✅ |
| XU100 (22 Nis) | **"Sol Omuz / Baş / Sağ Omuz" + "TOBO oluşumu"** | 🔨 `obo.py` eklendi |

### Son eklenen: OBO/TOBO (`obo.py`)
Hocanın grafiğinde açıkça etiketlenen omuz-baş-omuz formasyonu:
- OBO (H-L-H-L-H, baş en yüksek, omuzlar benzer) → boyun altı kapanışla bearish
- TOBO (ters) → boyun üstü kapanışla bullish; ölçülü hareket hedefi
- Canlı: ETH 1d OBO, SOL 1d TOBO tespit edildi.

### Veri kaynağı genişletildi: MEXC
`veri.py` artık Binance.US başarısız/eksikse **MEXC**'e düşüyor (1h→60m
eşlemesi, 8/12 kolon farkı yönetiliyor) — çok daha geniş altcoin kapsamı.

> **"Bitti mi?"** → Hocanın erişilebilir 824 tweet'inin metni + temsili
> grafikleri incelendi; çıkan tüm mekanikleştirilebilir kavramlar (Fib, RSI,
> divergence, Elliott, OBO/TOBO) sisteme eklendi. Tüm 21.598 tweet'in tamamı
> X API geçmiş sınırı (~son 800-3200) yüzünden çekilemez; erişilebilen kısım
> ve görsel söz dağarcığı tamamlandı. Kalan: DXY/VIX (veri-kısıtlı). 91/91 test.
