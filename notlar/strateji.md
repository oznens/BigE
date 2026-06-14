# Strateji: Session Trend (v1)

## Felsefe
Walter Vanelli'nin discretionary banka-dealer sezgisini **kopyalamaya çalışmıyoruz** —
o edge 40 yıllık insan tecrübesi, kodla taklit edilemez. Bunun yerine piyasada
**istatistiksel olarak ölçülebilir, kural-tabanlı** edge'leri arıyoruz. Her şey
backtest edilebilir, duygu yok.

## Bileşenler
1. **Trend rejimi** — saatlik EMA(24) > EMA(168) ise yukarı rejim, long'a izin.
   Trend-following BTC'de uzun vadede al-tut'tan üstün (özellikle drawdown'da).
2. **Zaman filtresi** — "Monday Asia Open" hipotezi. Pazar 19:00 ET → Pazartesi
   18:00 ET penceresinde tam ağırlık, dışında %35. Tek başına marjinal ama
   trend üstüne **filtre** olarak risk-ayarlı getiriyi belirgin iyileştiriyor.
3. **Vol-hedefleme (ops.)** — `vol_hedef_acik=True` ile pozisyon = hedef_vol/realize_vol.
   Drawdown'ı ~%11'e indirir ama getiriyi kısar; kaldıraçla birleştirilecek
   bir "risk kolu". Varsayılan kapalı (ayrık 0/1 trend, daha az işlem).

## Over-trading dersi
İlk naif versiyon sürekli vol-rebalans yüzünden **13.048 işlem** yaptı, komisyon
her şeyi yedi (Sharpe -0.04). Çözüm: **bantlı rebalans (histerez)** + ayrık trend
pozisyonu → işlem 534'e düştü, Sharpe 0.92'ye çıktı. *Devir hızı, edge kadar önemli.*

## Look-ahead koruması
- İndikatörler yalnızca geçmiş barı kullanır.
- Backtest pozisyonu **1 bar gecikmeyle** uygular (`shift(1)`).
- İşlem maliyeti pozisyon değişimine uygulanır (6 bps, taker).

## Risk uyarısı
4 yıllık tek örneklem (2022-2026), çoğunlukla toparlanma/boğa rejimi. Backtest ≠
canlı. Out-of-sample ve daha uzun geçmiş test edilmeden canlıya alınmamalı.
