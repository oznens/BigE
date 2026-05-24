# Model Parametreleri

Backtest sırasında bunlar değiştirilip optimize edilebilir. İlk default'lar Big E'nin söylediği değerler.

## İndikatör parametreleri

| Parametre               | Default | Kaynak / Not |
|-------------------------|---------|--------------|
| `rsi_period`            | 13      | Big E'nin TDI'ının RSI baz periyodu |
| `tdi_fast_ma`           | 2       | Yeşil çizgi: SMA(RSI, 2) |
| `tdi_slow_ma`           | 7       | Kırmızı çizgi: SMA(RSI, 7) |
| `tdi_oversold`          | 32      | Long üstüne yaklaşılırsa tetik |
| `tdi_mid`               | 50      | Yön ayraç |
| `tdi_overbought`        | 68      | Short üstüne yaklaşılırsa tetik |
| `tdi_bb_period`         | 34      | Bilgi amaçlı (sinyal değil) |
| `tdi_bb_stddev`         | 1.6185  | Bilgi amaçlı |
| `stoch_k`               | 8       | Stochastic K periyodu |
| `stoch_d`               | 3       | Stochastic %K smoothing |
| `stoch_slowing`         | 3       | Stochastic %D smoothing |
| `stoch_lower`           | 20      | Stoch güvenli alt sınır |
| `stoch_upper`           | 80      | Stoch güvenli üst sınır |
| `ema_period`            | 5       | 5 EMA |
| `ema_shift`             | 2       | Sağa kaydırma (görsel) |

## Sinyal kuralları

| Parametre                      | Default | Açıklama |
|--------------------------------|---------|----------|
| `max_candle_age_after_cross`   | 2       | TDI cross sonrası girilebilecek max mum (Big E: 1-2) |
| `tdi_angle_min_strong`         | 0.5     | TDI yeşilin son N mumdaki eğimi (heuristik, ayarlanabilir) |
| `min_ha_body_atr_ratio`        | 0.3     | HA gövdesi/ATR oranı — daha küçükse consolidation say |
| `near_sr_lookback`             | 50      | Yakındaki S/R için geriye bakış mum sayısı |
| `near_sr_threshold_atr`        | 1.0     | S/R'a ATR cinsinden yakınlık eşiği |

## Risk / pozisyon

| Parametre                | Default | Açıklama |
|--------------------------|---------|----------|
| `risk_per_trade_pct`     | 1.0     | Her trade'de hesabın %1'i risk |
| `sl_lookback_candles`    | 2       | Stop = girilen mumdan N mum geri swing |
| `tp_strategy`            | "tdi_exit" | TDI sinyali ile çıkış (alternatif: r_multiple, fixed_pct) |
| `r_multiple_targets`     | [1, 2, 3] | RobinHood tarzı kademeli çıkış (alt mod) |
| `atr_period`             | 10      | Stop için alternatif (ATR × multiplier) |
| `atr_sl_multiplier`      | 2.0     | ATR tabanlı SL için |

## Backtest

| Parametre              | Default        | Açıklama |
|------------------------|----------------|----------|
| `sembol`               | `BTCUSDT`      | Binance spot |
| `aralik`               | `4h`           | Big E ana TF |
| `baslangic`            | `2020-01-01`   | Yeterli tarihsel veri |
| `bitis`                | `bugün`        | |
| `komisyon_bps`         | 7              | Binance taker ~0.07% (üst sınır) |
| `slippage_bps`         | 2              | Mum açılışında giriş için makul tahmin |
| `baslangic_bakiyesi`   | 10000          | USDT |
