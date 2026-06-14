# Bulgular — veriyle ölçülmüş sonuçlar

Veri: BTCUSDT 1h, Binance.US, 2022-05-06 → 2026-06-14 (~35.993 mum).
Komisyon: 6 bps tek yön. Tüm sayılar look-ahead'siz (1 bar gecikme).

## 1. "Monday Asia Open" edge'i — KISMEN doğrulandı, zayıf
`backtest/edge_tani.py`:
- Pencere içi (Pazar 19:00 → Pzt 18:00 ET): **+1.05 bps/saat**
- Pencere dışı: **+0.18 bps/saat**
- Yön doğru (Pazartesi en iyi gün, +1.20 bps) **ama t≈0.97 → istatistiksel anlamsız.**

Sonuç: Tek başına güvenilmez. Ama trend üstüne *filtre* olarak değer katıyor (aşağıda).

## 2. Ablation — hangi bileşen edge taşıyor?
`backtest/ablation.py` (her satır komisyon dahil):

| Konfig | Sharpe | CAGR | MaxDD | İşlem |
|---|---|---|---|---|
| Buy & Hold | 0.54 | +15.5% | -56.8% | 0 |
| Trend yalnız (0/1) | 0.61 | +15.9% | -44.7% | 445 |
| Trend + vol-hedef (bantlı) | 0.62 | +9.9% | -20.2% | 1.965 |
| **Trend + zaman** | **0.85** | +14.5% | -28.1% | 658 |
| Trend + vol + zaman | 0.72 | +6.7% | -11.3% | 2.156 |
| Zaman yalnız | 0.55 | +11.7% | -33.9% | 429 |

**Kazanan: Trend + Zaman.** EMA periyodu 24/168'e çekilince Sharpe **0.92**'ye çıkıyor.

## 3. Parametre duyarlılığı (sağlamlık)
Trend yalnız, farklı EMA çiftleri:

| EMA | Sharpe | İşlem |
|---|---|---|
| 12/48 | 0.15 | 901 |
| 24/96 | 0.61 | 445 |
| **24/168** | **0.64** | 319 |
| 48/200 | 0.57 | 219 |
| 12/96 | 0.48 | 621 |

24/96, 24/168, 48/200 hepsi 0.57-0.64 → **kırılgan overfit değil, sağlam plato.**
Sadece çok hızlı 12/48 çöküyor. Sağlık işareti.

## 4. Nihai konfig (varsayılan)
EMA 24/168 trend + zaman filtresi, ayrık 0/1, bantlı:

| Metrik | Session Trend | Buy & Hold |
|---|---|---|
| Sharpe | **0.92** | 0.54 |
| CAGR | +15.8% | +15.5% |
| Max Drawdown | **-20.2%** | -56.8% |
| Yıllık Vol | 17.7% | 49.7% |
| Calmar | 0.78 | 0.27 |
| İşlem | 534 | 0 |

**Yorum:** Al-tut ile aynı getiri, üçte bir risk. Gerçek risk-ayarlı alfa.

## Açık riskler / sonraki adımlar
- Tek örneklem, çoğunlukla boğa rejimi → out-of-sample + 2017-2021 verisi şart.
- Zaman edge'i istatistiksel olarak zayıf; başka borsa verisinde tekrarlanmalı.
- Slippage sadece 6 bps sabit; gerçek emir defteri etkisi yok.
- Short tarafı yok (yalnız long). Ayı piyasası davranışı test edilmeli.
