# İzlenebilirlik Matrisi — Metodoloji → Kod

> @tradermiraz metodolojisinin her kavramının hangi modülde uygulandığını
> ve hangilerinin beklemede olduğunu gösteren denetim tablosu.
> Kaynak notlar: `metodoloji.md`, `kutular.md`, `risk.md` + 6 vaka çalışması.

## Uygulanan kavramlar ✅

| Metodoloji kavramı | Modül | Test |
|---|---|---|
| Swing pivot tespiti | `pivotlar.py` | (dolaylı) |
| Harmonik patternler (8 adet, XABCD) | `harmonik.py` | `test_harmonik.py` |
| Oluşmakta olan (tamamlanmamış) harmonik | `harmonik.py` `olusan_harmonik` | `test_harmonik.py` |
| Renkli kutular (Mavi/Yeşil/Turuncu/Mor/Kırmızı) | `kutular.py` | `test_kutular.py` |
| Adaptif (ATR) kümeleme toleransı | `kutular.py` | `test_kutular.py` |
| Harmonik ∩ kutu çakışması (confluence) | `cakisma.py` | `test_cakisma.py` |
| Trend çizgisi / kanal | `trend.py` | `test_trend.py` |
| Mavi daire (harmonik D ∩ destek) | `senaryo.py` | `test_trend.py` |
| Mor çizgi (ara kâr-alma) | `senaryo.py` | `test_trend.py` |
| Hacim filtresi (hacimli geliş = kırılma riski) | `senaryo.py` | `test_trend.py` |
| Kritik kapanış + fitil toleransı | `senaryo.py` | `test_trend.py` |
| Ana hedef mantığı (engelleri atla) | `senaryo.py` | `test_trend.py` |
| MTF üst zaman dilimi yapısı | `senaryo.py` `_mtf_yapi` | `test_trend.py` |
| Market yapısı (HH/HL, BOS/CHoCH) | `yapi.py` | `test_yapi.py` |
| Flama / diagonal (yakınsayan üçgen) | `flama.py` | `test_flama.py` |
| Çift Tepe / Çift Dip (boyun kırılımı + ölçülü hareket) | `ikili.py` | `test_ikili.py` |
| Karar motoru (Trade/Watch/Skip + A-D kalite + güven) | `karar.py` | `test_karar.py` |
| R-bazlı risk + kademeli giriş | `risk.py` | `test_risk.py` |
| Fibonacci retracement / golden pocket (hoca @finansalTRader) | `fib.py` | `test_fib.py` |
| İndikatörler RSI/EMA/SMA/MACD (hoca) | `indikator.py` | `test_indikator.py` |
| RSI divergence / trend yorgunluğu (hoca) | `divergence.py` | `test_indikator.py` |
| Elliott Wave itme/düzeltme (hoca) | `elliott.py` | `test_indikator.py` |
| OBO / TOBO (omuz-baş-omuz / H&S) (hoca) | `obo.py` | `test_obo.py` |
| Göreceli güç: ALT/BTC, BTC/Altın, genel RASYO | `oran.py` | `test_oran.py` |
| Çoklu-bölge yol haritası | `yol_haritasi.py` | `test_yol_haritasi.py` |
| TradingView/Miraz tarzı grafik | `grafik.py` | `test_grafik.py` |
| Miraz tarzı düz-metin yorum | `senaryo.py` `miraz_yorumu` | — |

## Beklemede / kısmen uygulanan ⏳

| Metodoloji kavramı | Durum | Not |
|---|---|---|
| **R-bazlı risk / pozisyon boyutlama** | 🔨 bu turda eklendi → `risk.py` | risk.md'deki ½R, RR, pozisyon tipleri |
| USDT/USDC Dominance barometresi | ❌ beklemede | Binance.US'ta dom. serisi gerekiyor (dış veri); arşivde 139 kez geçiyor |
| CME GAP kuralı | ❌ beklemede | Hafta sonu GAP tespiti (BTC) — mekanikleştirilebilir |
| OBO / TOBO (omuz-baş-omuz) | ✅ uygulandı | `obo.py` (hoca grafiğinde "Sol Omuz/Baş/Sağ Omuz" doğrulandı) |
| Veri kaynağı: MEXC (fallback) | ✅ uygulandı | `veri.py` — Binance.US → MEXC; 1h→60m eşlemesi, daha çok altcoin |
| Kademeli giriş (kademe kademe alım) | 🟡 kısmen | risk.py tek giriş veriyor; "birinci/ikinci kademe" çoklu giriş eklenebilir |
| Likidite süpürme (sweep) | 🟡 kısmen | fitil toleransı var; açık sweep tespiti yok |
| Eski destek → yeni direnç (flip) | 🟡 kısmen | kutu tipi var; otomatik flip etiketi yok |
| Backtest motoru (win-rate ölçümü) | ❌ beklemede | "next logical step" |
| Cluster hafızası / benzerlik öğrenmesi | ❌ beklemede | PriceActionLab'da var: geçmiş benzer setup'larla karşılaştırma |
| Temas davranışı istatistiği (0/1/2/3+ dokunuş) | ❌ beklemede | PriceActionLab "Temas Davranışı" paneli |
| GAP bölgeleri (doldurulacak fiyat boşlukları) | ❌ beklemede | "potansiyel GAP" — CME GAP ile birlikte |

## Hoca @finansalTRader — indikatör-bazlı araçlar
| Kavram | Durum | Modül / Not |
|---|---|---|
| RSI / EMA / SMA / MACD | ✅ uygulandı | `indikator.py` |
| RSI divergence (trend yorgunluğu) | ✅ uygulandı | `divergence.py` (karar motoruna da bağlı) |
| Elliott Wave (itme 1-5 / düzeltme ABC) | ✅ uygulandı | `elliott.py` |
| Wedge (takoz) | 🟡 kısmen | flama'nın yönlü varyantı; ayrı eklenebilir |
| DXY / VIX makro | ❌ veri-kısıtlı | Binance.US yalnızca kripto; DXY/VIX dış TradFi verisi gerekiyor |

## Notlar
- 8 vaka çalışması: TAO, Gümüş, ETH/BTC, BTC/Altın, MSTR, Altın/Gümüş, Arşiv,
  finansalTRader — her birinin dersleri ilgili modüllere yansıtıldı.
- Bu matris her yeni floodda/kaynakta güncellenir.
