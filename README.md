# BigE

Big E trader'ın trading modelini koda dökme + backtest projesi.

## Klasör yapısı
```
kaynak/      # Big E'ye ait kaynaklar (PDF, video, görsel, not) — sen yüklüyorsun
notlar/      # Kaynaklardan çıkarılmış kurallar, özetler, model taslağı
src/bige/    # Modelin Python implementasyonu
backtest/    # Geçmiş veri üzerinde test, sonuç raporları
data/        # Fiyat verisi (OHLCV vs.) — büyük dosyalar git'e girmez
tests/       # Unit testler
```

## Zaman dilimi
Tüm tarih/saat işlemleri **Türkiye saati (Europe/Istanbul, UTC+3)** üzerinden yapılır.
Veri kaynağı UTC veriyorsa, koddaki yardımcı fonksiyon ile İstanbul saatine çevrilir.

## Akış
1. **Kaynak toplama** — `kaynak/` klasörüne dosyaları at
2. **Öğrenme** — kaynaklar incelenir, `notlar/model_kurallari.md` çıkarılır
3. **Modelleme** — `src/bige/` altında kural motoru yazılır
4. **Backtest** — geçmiş veri üzerinde performans ölçülür
5. **İyileştirme** — sonuca göre parametre/kural revizyonu
