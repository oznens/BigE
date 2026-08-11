# Price Action alt tür denetimi

## Arşiv ve kod karşılığı

Arşiv Price Action içinde tek tip setup yerine farklı yapıların kullanıldığını
doğrular. Örnek metin kanıtları:

- Order Block / PaMonic bağlamı: `2045324061207576694`, `1992343978746769850`
- Çift tepe/dip ve trend kırılımı: `2049159622800318808`
- OBO/TOBO: `2022085742004949176`, `1976760568556945784`
- Golden Pocket / 0.618: `2046318047426969922`
- MSB: `2013655162355884136`
- RSI/uyumsuzluk: `2019384637836198041`, `1909150960141648192`

Arşiv terminalMiraz'ın alt tür sınıflandırma formülünü ve her türün kesin işlem
kapısını açıklamaz. BigE bu nedenle yalnız kendi dedektörlerinin gerçek çıktılarını
audit etiketi olarak saklar.

## Uygulanan çoklu etiketler

- `OB Proxy`: Long için destek, Short için direnç kutusu. Bağımsız Order Block
  dedektörü olmadığı için kesin `Order Block` denmez; kökeni
  `BigE-zone-heuristic-not-exact-order-block` olarak yayınlanır.
- `Divergence`: `Divergence` nesnesi gerçekten üretildiyse.
- `Double Top/Bottom`: `IkiliFormasyon` bulunduysa; onay durumu ayrıntıda saklanır.
- `OBO/TOBO`: formasyon bulunduysa; boyun kırılım onayı ayrıca saklanır.
- `Fibonacci Retracement`: aktif Fib geri çekilmesi varsa.
- `Golden Pocket`: fiyat 0.618–0.705 bölgesindeyse.
- `MSB`: market yapısı gerçek `BOS-*` veya `CHoCH-*` kırılımı ürettiyse; kesin
  sinyal ayrıntıda korunur.

Bir setup birden fazla etikete sahip olabilir. Bu yüzden alt tür satırları
toplanarak benzersiz setup toplamı elde edilmez.

## Sonuç ayrımı

Her alt türde gerçek `Result Journal` TP/STOP ve Filtered karşı-olgusal TP/STOP
ayrı raporlanır. Eski etiketsiz Price Action kayıtları `Unclassified` kalır;
geçmişten tür tahmin edilmez. Sonuçlar betimseldir, nedensellik veya Miraz'ın
gizli setup sınıflandırıcısının birebir kopyası iddia edilmez.

## Çapraz denetim matrisi

Her PA alt türü aşağıdaki boyutlarla ayrı hücrelerde karşılaştırılır:

- Timeframe
- Long / Short tarafı
- HTF snapshot'ı veya `conflict-filtered`
- LTF `trend-devam` / `zayiflama` / `notr` snapshot'ı
- Kalıcı kalite geçişi (`A→B` gibi)

Hücreler gerçek Journal ve Filtered karşı-olgusal sonuçlarını yine ayrı tutar.
Karşı-olgusal kayıtların tamamı sonuçlanmamışsa hücre
`locked-incomplete-counterfactual-coverage`; sonuçlar tam olsa bile arşiv minimum
örnek eşiğini açıklamadığı için `locked-minimum-threshold-undisclosed` olur.
Hiç doğrulanmış sonuç yoksa `locked-no-verified-outcomes` kullanılır.

Tüm hücrelerde `recommendation_allowed: false` kalır. Matris betimsel audit'tir;
otomatik setup kapatma, puan değiştirme veya “en iyi kombinasyon” önerisi üretmez.
Çoklu etiket ve çoklu kalite geçişi nedeniyle hücreler birbirine eklenemez.
