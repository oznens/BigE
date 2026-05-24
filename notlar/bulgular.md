# Backtest Bulguları

## En iyi default konfigürasyon (şu an)

```python
StratejiParams(
    max_candle_age_after_cross=1,    # cross'un olduğu veya sonraki mumda gir
    tdi_angle_min=1.0,               # eğim eşiği (saat 12-2 / 4-6 yaklaşımı)
    near_extreme_margin=5.0,         # 68'e/32'ye yakınken pas geç
    min_ha_body_atr_ratio=0.2,       # küçük mumlarda pas
    require_stoch_confirm=True,
    trend_filtresi_aktif=True,
    trend_ema_period=200,            # uzun trend yönü
    sl_mode="atr",
    sl_atr_multiplier=2.0,           # ATR × 2 stop loss
    sl_lookback_candles=3,           # swing modu kullanılırsa
    risk_per_trade_pct=1.0,
    bounce_aktif=False,              # bounce trade'ler default kapalı
    allow_short=False,               # kripto'da long-only daha iyi
    saat_filtresi_aktif=True,        # Big E saatleri (Istanbul 9-17)
    saat_baslangic=9,                # 4h için aktif, 1D'de auto-skip
    saat_bitis=17,
)
```

## Sonuç tablosu (2022-01-01 → 2026-04-30, 4 yıl)

Big E saatleri (Istanbul 9-17) aktif, long-only, EMA200 trend, ATR×2 SL:

| Pair | TF | Trade | WR | PF | Sharpe | Max DD | Getiri | B&H |
|---|---|---|---|---|---|---|---|---|
| BTC | 4h | 106 | 47% | 1.47 | 0.52 | **-3.9%** | +9% | +63% |
| BTC | 1d | 44 | 45% | **2.32** | **2.54** | -2.5% | +12% | +60% |
| ETH | 4h | 115 | 41% | 1.56 | 0.75 | -4.6% | **+16%** | -39% |
| ETH | 1d | 43 | 35% | 1.38 | 0.87 | -2.9% | +4% | -40% |
| SOL | 4h | 99 | 45% | **1.80** | 0.95 | -3.7% | **+17%** | -52% |
| SOL | 1d | 36 | **56%** | 1.83 | **1.41** | -1.8% | +5% | -54% |
| BNB | 4h | 121 | 38% | 0.91 | -0.26 | -8.1% | -4% | +19% |
| BNB | 1d | 38 | 37% | 1.14 | 0.32 | -3.6% | +1% | +17% |

**Saat filtresinin etkisi (24/7 vs Big E hours, ortalama):**
- Sharpe: 0.84 → **0.89**
- Max DD: -5.8% → **-3.9%** (yarıya yakın düşüş)
- Trade sayısı: 251 → **110** (kaliteli sinyal seçimi)

## Önemli içgörüler

### 1. 1D timeframe dramatik olarak 4h'den iyi
- BTC 1D Sharpe 2.54, 4h Sharpe 0.44
- 1D'de sinyal sayısı az ama kaliteli (yılda ~11 trade)
- 4h'de gürültü çok, win rate düşük

### 2. Long-only > Long+Short
- Tüm pair'lerde ortalama Sharpe 0.84 vs 0.72
- Kripto'da bull market'ta short çok zorlayıcı
- Short'lar ayı piyasalarında bile zayıf (yön değişimi çok hızlı)

### 3. Strateji ayı piyasasında çok iyi koruma sağlıyor
- ETH 4h: bizim +%21, B&H -%39 → 60 puan üstünlük
- SOL 4h: bizim +%23, B&H -%52 → 75 puan üstünlük
- Trend filtresi (EMA200) sayesinde ayı piyasasında çok az trade alıyor

### 4. Bunlar boğa piyasasında B&H'ı yakalayamıyor
- BTC 4h/1D: bizim ~+%10, B&H +%60
- Yön doğru ama trend takibi geç kalıyor (EMA200 filtresi tutucu)
- Bu trade-off'u kabul ediyoruz: az risk, daha tutarlı

### 5. BNB sorunlu — pair-spesifik
- BNB 4h: bizim -%12, B&H +%19
- BNB volatilitesi düşük, mumlar küçük, sinyal kalitesi bozuluyor
- Watch list'ten BNB'yi çıkartmak veya ona özel parametre gerekebilir

### 6. Bounce trade'ler net olarak fayda sağlamıyor
- Sıkı tanımla bile Sharpe 0.84 → 0.75
- Big E'nin manuel sezgisini mekanikleştirmek zor
- Default kapalı, opt-in parametre olarak duruyor

### 7. Stop loss en kritik parametre
- Orijinal "2 mum geri swing" crypto 4h'de hemen tetikleniyor (340 trade SL'de
  kapandı baseline'da, ortalama tutuş <1 mum)
- ATR × 2 çok daha iyi: SL'ler azaldı, kazanan trade'ler nefes aldı
- ATR × 3 daha da iyi olabilir bazı pair'lerde

## Sıradaki iyileştirmeler (denenecekler)

- [ ] Parametre grid search (overfit'e dikkat)
- [ ] Walk-forward validation (zaman dilimi bölme)
- [ ] R-multiple kademeli çıkış (RobinHood tarzı)
- [ ] Daha çok pair (10-15 altcoin)
- [ ] Pozisyon büyütme: trend güçlüyse %1 yerine %1.5 risk
- [ ] Funding rate / open interest entegrasyonu (futures için)
- [ ] Multi-timeframe filtre: 4h sinyal + 1D yön onayı

## Big E'nin %70-80 WR iddiası gerçekçi mi?
**Kripto için hayır.** En iyi WR'ımız SOL 1D'de %56. Big E forex'te trade
ediyordu — kripto'nun fiyat dağılımı (fat tails, yüksek volatilite) bu kadar
WR'ye izin vermiyor.

Ama PF (Profit Factor) ve Sharpe iyi: kazançlar kayıplardan büyük, risk-ayarlı
getiri yüksek. Yani metot çalışıyor, sadece WR sayısı yanıltıcı.
