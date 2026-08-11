# Entry hacim memory denetimi

## Arşiv kanıtı

- `tweetler/TERMINALMIRAZ_EVIDENCE.md` içindeki `volume_close` sınıfında 48 tweet
  ve 47 görselli tweet bulunur.
- Tweet `1950152482916651231`, kırmızı kutu üzerindeki hacimli kapanışlar yokken
  yapının görmezden gelinmemesini söyler.
- Tweet `2061893277755048212`, günlük mum hacimli kapanırsa pozisyonun
  kapatılacağını açıkça söyler.
- `tweetler/METODOLOJI.md`, hacimli kapanışı fitilden ayrı bir onay şartı olarak
  özetler.

## Koda yansıyan, fakat Miraz kuralı olmayan ölçüm

Entry'nin gerçekleştiği OHLCV barının ham hacmi ve kapanışı saklanır. Hacim,
entry barından önceki en fazla 20 tamamlanmış barın medyanına bölünür. 20 barlık
pencere ve `<1.0x / 1.0-1.49x / 1.5-1.99x / >=2.0x` bantları yalnız BigE
gözlem normalizasyonudur; arşivden çıkarılmış Miraz eşikleri değildir.

Yalnız gerçek snapshot bulunan TP/STOP kayıtları motor bazında raporlanır. Eski
kayıtlara backfill yapılmaz. Sonuçlar otomatik Trade/Watch/Skip kararı veya hacim
filtresi üretmez. Arşivin açıklamadığı kesin eşik, pencere ve bölge-kapanış
toleransı icat edilmemiştir.
