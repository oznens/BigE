# miraz

@tradermiraz metodolojisini öğrenme, belgeleme ve koda dökme projesi.

## Aşamalar
1. **Öğrenme** — Tweet analizi → `notlar/metodoloji.md`
2. **Modelleme** — Kuralları Python'a çevir → `src/miraz/`
3. **Backtest** — Geçmiş veriyle test → `backtest/`

## Canlı pano (terminalMiraz tarzı)

Sistemi tarayıcıdan açılan canlı bir web paneli olarak çalıştır:

```bash
pip install -e .
python backtest/evren.py --guncelle --n 90        # mcap evrenini bir kez kur
python backtest/sunucu.py --mcap --mtf --taraf her  # → http://localhost:8000
```

Sunucu arka planda sürekli tarar; tarayıcı paneli kendi tazeler. Sekmeler:
**Dashboard** (execution metrikleri + Kiraz status + aday akışı + sonuçlar),
**PNL Analytics**, **Memory**. CMD panosu isteyenler için: `backtest/dashboard.py`.

## Klasörler
```
notlar/          # Metodoloji belgeleri (tweet analizinden çıkarılan)
  metodoloji.md  # Ana kural kitabı
  kutular.md     # Renkli kutu konsepti
  harmonik.md    # Harmonik pattern kuralları
  risk.md        # Risk yönetimi
  grafikler/     # Referans grafik örnekleri
src/miraz/       # Python implementasyonu
backtest/        # Backtest scriptleri
data/            # Fiyat verisi cache
tests/           # Unit testler
```
