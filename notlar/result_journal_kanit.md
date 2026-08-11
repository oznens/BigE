# Result Journal — kanıtlı sınıflandırma

## Ana toplu kanıt

Tweet `2065351367544181110`, 2.200 taranmış setup için iki ayrı grup verir:

- Sonuçlanan işlemler: Price Action, Harmonik, Late Setup, TradeFiPA ve
  TradeFiHarmonic altında TP/STOP.
- Diğer sonuçlar: `Filtrelendi`, `Rafa Kalktı`, `Entry Olmadı`, `Expired`,
  `Cancelled`.

Tweet `2059325292926148742`, `Geç Kalmış Setuplar` ve `Filtrelenen Setuplar`ı
özel filtrelenmiş yapılar olarak ayrıca doğrular.

## BigE karşılığı

- TP/STOP motor sonuçları `Price Action`, `Harmonik` ve `Late` bucket'larında
  birbirinden ayrı tutulur.
- Diğer sonuçlar `Filtered`, `Shelved`, `No-Entry`, `Expired`, `Cancelled` olarak
  kalıcı journal kayıtlarından sayılır.
- UI arşiv dilini `FİLTRELENDİ`, `RAFA KALKTI`, `ENTRY OLMADI`, `EXPIRED`,
  `CANCELLED` şeklinde gösterir.
- Anlık radar lifecycle sayıları `radar_lifecycle` alanındadır ve kümülatif
  Result Journal'a eklenmez. Böylece aynı setup sonraki taramalarda tekrar sayılmaz.

## Kapsam sınırı

TradeFi motorları bu repoda bulunmadığından TradeFiPA/TradeFiHarmonic isimleri
sahte boş motorlar olarak eklenmemiştir.
