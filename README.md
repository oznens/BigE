# Walter

BTC/kripto için **sistematik intraday trend** stratejisi + backtest motoru.

Walter Vanelli'nin discretionary banka-dealer yaklaşımını kopyalamak yerine,
piyasada **istatistiksel olarak kanıtlanmış yapısal edge'leri** kural-tabanlı,
ölçülebilir bir sisteme döküyoruz. Duygu yok, kural var.

## Strateji özeti (v1: "Session Trend")

1. **Trend yönü** — saatlik EMA rejimi (hızlı vs yavaş) trendi belirler.
   BTC'de trend-following uzun vadede al-tut'tan üstün (Sharpe ~1.6 vs ~0.8).
2. **Zaman edge'i** — "Monday Asia Open" etkisi: Pazar 19:00 ET → Pazartesi
   öğleden sonrası BTC trend getirileri belirgin biçimde pozitif. ABD Pazar
   sabahı gibi "choppy" pencerelerden kaçılır.
3. **Volatilite hedefleme** — pozisyon boyutu sabit yıllık vol hedefine
   (varsayılan %20) göre ölçeklenir. Kaldıraçla intihar yok.
4. **Risk** — ATR-tabanlı stop, maksimum tutma süresi.

Detaylı gerekçe ve kaynaklar: [`notlar/strateji.md`](notlar/strateji.md)

## Klasör yapısı
```
src/walter/    # Strateji + backtest motoru (Python paketi)
  veri.py        # Borsa API'den OHLCV çekme + cache
  indikatorler.py# EMA, ATR, realized vol, momentum
  strateji.py    # Sinyal üretimi (Session Trend)
  backtest.py    # Vektörize backtest + metrikler
  zaman.py       # UTC <-> ET / Istanbul saat dilimi yardımcıları
backtest/      # Çalıştırma scriptleri, parametre taramaları, raporlar
data/          # OHLCV cache (parquet) — git'e girmez
notlar/        # Strateji gerekçesi, parametreler, bulgular
tests/         # Unit testler
```

## Hızlı başlangıç
```bash
pip install -e .
python -m walter.veri              # BTC saatlik veriyi indir + cache
python backtest/calistir.py        # Backtest çalıştır, rapor üret
```

## Zaman dilimi
Veri kaynağı UTC verir. Strateji "Monday Asia Open" edge'i için **ET (Amerika)**
saatini kullanır; raporlar ayrıca **Istanbul (UTC+3)** saatiyle de gösterilir.

## Uyarı
Day trading'de uzun vadede traderların %80-95'i para kaybeder. Bu proje bir
yatırım tavsiyesi değil; bir edge'in gerçekten var olup olmadığını **veriyle
test etme** aracıdır. Backtest ≠ canlı sonuç.
