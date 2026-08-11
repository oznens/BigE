# TradePlayBack — arşiv kanıtı ve uygulama sınırı

## Doğrudan kanıt

- Tweet `2056806486127346084`: terminalMiraz'ın tüm trade'leri TradePlayBack ile
  tek tek izleteceğini; yalnız TP/STOP sonucunu değil, setup'ın oluşumunu, fiyatın
  geçtiği aşamaları ve süreci göstereceğini söylüyor.

## BigE'de uygulanan davranış

- Playback yalnız sonuçlanmış TP/STOP kayıtlarını açar.
- Grafik setup mumundan başlayıp gerçek mumları sırayla gösterir ve kayıtlı sonuç
  mumunda biter.
- Ekran aşamayı `SETUP OLUŞUMU`, `FİYAT SÜRECİ`, `SONUÇ` olarak bildirir.
- Entry/stop/hedef ve kayıtlı sonuç aynı ekranda korunur.

## Bilinçli sınır

Tweet “kararsız kaldığı” aşamaların da anlatıldığını söyler; fakat arşiv, bu
durumun algoritmik tespit kuralını açıklamıyor. Bu nedenle BigE kararsızlık etiketi
uydurmaz. İleride gerçek tarama anı kalite geçmişi kaydedilirse bu aşama yalnız
kayıtlı değişimlerden üretilebilir.
