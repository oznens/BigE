# Proje Kapsamı

## Piyasa
- **Kripto** (BTC, ETH, ana altcoinler)
- Veri kaynağı: Binance (spot/futures — kaynaklar geldikten sonra netleşecek)

## Zaman Dilimi
- **Swing**: 4h ve 1D mumlar
- Pozisyon tutuş süresi: günler ~ haftalar

## Saat
- Tüm analiz **Europe/Istanbul** (UTC+3) saatine göre
- Binance verisi UTC gelir → `src/bige/zaman.py` ile çevrilir
- Günlük mum kapanışı UTC 00:00 = İstanbul 03:00 (bunu kuralları yazarken hatırla)

## Açık sorular (kaynaklar gelince netleşecek)
- Spot mu, vadeli mi (kaldıraç var mı)?
- Hangi coinler watchlist'te?
- Pozisyon büyüklüğü / risk yönetimi (% risk per trade?)
- Stop-loss ve take-profit mantığı
- Giriş tetikleyicileri (indikatör, fiyat aksiyonu, hacim?)
