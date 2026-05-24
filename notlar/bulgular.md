# Backtest Bulguları

## En iyi default konfigürasyon (grid search sonucu)

```python
StratejiParams(
    max_candle_age_after_cross=1,    # cross'un olduğu veya sonraki mumda gir
    tdi_angle_min=1.0,               # eğim eşiği (saat 12-2 / 4-6 yaklaşımı)
    near_extreme_margin=5.0,         # 68'e/32'ye yakınken pas geç
    min_ha_body_atr_ratio=0.2,       # küçük mumlarda pas
    require_stoch_confirm=True,
    trend_filtresi_aktif=True,
    trend_ema_period=50,             # GRID: 50 > 100 > 200
    sl_mode="atr",
    sl_atr_multiplier=3.0,           # GRID: 3.0 en yüksek Sharpe + en düşük DD
    sl_lookback_candles=3,
    risk_per_trade_pct=1.0,
    mtf_onay_filtresi=True,          # 1D trend uyumu — Sharpe %57 arttırdı
    # mtf_trend kolonu mtf_trend_ekle(df_4h, df_1d, ema_p=20) ile eklenir
    bounce_aktif=False,
    allow_short=False,
    saat_filtresi_aktif=True,
    saat_baslangic=9,
    saat_bitis=17,
)
```

## Sonuç tablosu (2022-01-01 → 2026-04-30, 4 yıl)

Grid-searched config: trend_ema=50, sl_atr_mult=3.0, mtf_ema=20

| Pair | TF | Trade | WR | PF | Sharpe | Max DD | Getiri | B&H |
|---|---|---|---|---|---|---|---|---|
| BTC | 4h | 98 | **50%** | 1.77 | **0.77** | -3.3% | +13% | +63% |
| BTC | 1d | 44 | 45% | **2.32** | **2.54** | -2.5% | +12% | +60% |
| ETH | 4h | 98 | 47% | **2.35** | **1.27** | -3.9% | **+27%** | -39% |
| ETH | 1d | 43 | 35% | 1.38 | 0.87 | -2.9% | +4% | -40% |
| SOL | 4h | 88 | 48% | **2.18** | **1.18** | -3.5% | +20% | -52% |
| SOL | 1d | 36 | **56%** | 1.83 | **1.41** | **-1.8%** | +5% | -54% |
| BNB | 4h | 104 | 43% | 1.25 | 0.25 | -5.5% | +3% | +19% |
| BNB | 1d | 38 | 37% | 1.14 | 0.32 | -3.6% | +1% | +17% |

**Toplam iyileştirme yolculuğu (BTC 4h baseline → final):**
- Win rate: 33% → 49% (+16 puan)
- Sharpe: -∞ (kayıp) → 0.69
- Max DD: -82% → -3.9% (95% düzeldi)
- Toplam getiri: -82% → +11%

**Filtre etki sıralaması (en etkili → en az etkili):**
1. ATR stop loss (en kritik)
2. EMA200 trend filtresi
3. MTF (1D) onayı (Sharpe 0.49 → 0.77 fark yarattı)
4. Big E saatleri (DD'yi yarıladı)
5. Long-only (kripto'da)
6. Sıkı TDI cross + açı filtresi

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

### 7. Big E'nin "17:00'da kapat" mantığı kripto'da ÇALIŞMIYOR
Big E forex'te 6am Pacific'te (Istanbul 17:00) tüm 4h trade'leri kapatıyordu.
Sebep: forex broker overnight rollover komisyonları. Kripto 24/7 olduğu için
bu sorun yok ve trade'leri yarıda kesmek zararlı.

| Kapatma saati | Sharpe | DD | Getiri |
|---|---|---|---|
| Hold (kapatma yok) | **0.49** | -5.1% | **+9.2%** |
| Kapa 15:00 | -1.05 | -7.3% | -6.5% |
| Kapa 19:00 | -0.36 | -6.5% | -3.8% |
| Kapa 23:00 | 0.23 | -5.1% | +3.9% |
| Kapa 03:00 | 0.46 | -4.9% | +8.1% |

Default `gun_sonu_kapat_saat=None`. Bu Big E'nin kuralından bilinçli ayrılış.

### 8. Stop loss en kritik parametre
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
