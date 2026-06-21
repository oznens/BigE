# Yedek Noktaları (Restore Points)

> Bu dosya, projenin kararlı yedek sürümlerini kaydeder. "yorumcu yedek"
> dendiğinde aşağıdaki sürüm kastedilir.

## 🔖 `yorumcu-yedek` — Yorumcu Sürümü (kararlı)

- **Dal:** `yorumcu-yedek` (GitHub: `oznens/BigE`)
- **Commit:** `1cdffc8`
- **Tarih:** 2026-06-21
- **Durum:** Kararlı. Sistem **yorumcu** olarak tamamlandı.

### Bu sürümde ne var
- **İki ayrı hoca yorumu:** `@tradermiraz` (saf Price Action) +
  `@finansalTRader` (indikatör/Fib/RSI) — `senaryo.miraz_yorumu` /
  `senaryo.finansaltrader_yorumu`
- **Veri:** yalnızca **MEXC** (`veri.py`, sayfalama düzeltmeli, güncel)
- **4 yön tespiti:** harmonik (XABCD + oluşan/PRZ, geçerlilik filtreli) ·
  renkli kutu · trend/flama · çift tepe-dip / OBO-TOBO
- **Hoca araçları:** Fibonacci golden pocket, RSI/EMA/SMA/MACD, divergence,
  Elliott (itme/düzeltme)
- **Karar motoru:** Trade/Watch/Skip + A-D kalite + güven
- **Risk:** R-bazlı + kademeli giriş
- **Render:** TradingView stili grafik + finansalTRader katmanı (Fib + RSI paneli)
- **23 modül, 92 test (hepsi geçiyor), 12 not**

### Geri dönüş (restore)
İleride sorun olursa bu sürüme dönmek için:
```bash
git checkout yorumcu-yedek            # bu sürümü incele
# veya çalışma dalını bu noktaya almak için:
git reset --hard origin/yorumcu-yedek
```

> Not: Bu ortamın git proxy'si tag push'u desteklemediğinden yedek, **dal**
> olarak tutulur (kalıcı). Yeni kararlı sürümlerde bu dosyaya yeni bölüm eklenir.
