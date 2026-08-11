# HTF / Multi Timeframe filtresi — kanıt sınırı

## Arşiv kanıtı

- Tweet `2046218068255236383`, Multi Timeframe Onayı'nı **yakında gelecek özellik**
  olarak duyurur. Verilen tek somut örnek: 15m işlem alınırken üst ve alt zaman
  dilimlerinin onaylayıp onaylamadığının kontrol edilmesi.
- Tweet `2052860896360480962`, daha sonraki aşamada HTF-LTF Kontrol Sistemi'ni
  ciddi test sürecine eklenmiş yeni filtreleme mekanizması olarak anlatır. Bu
  nedenle arşiv durumu artık yalnız `announced-as-upcoming` değildir;
  `implemented-in-testing-announced` olarak işaretlenir.
- Tweet `2064005426710986769`, sistemin dört farklı zaman dilimini eşzamanlı
  taradığını söyler; bu dört TF'nin adlarını açıklamaz.
- Tweet `2051315135843574259`, farklı vadelerde sinyal ve hedef karıştırılmaması
  gerektiğini açıklar; “1 saatlik bearish sinyalle haftalık hedef kovalanmaz.”

## Kanıtlanmayan ayrıntılar

- Kesin setup TF → üst TF eşleme tablosu.
- Hangi alt TF'nin kontrol edileceği.
- Uyumsuzluğun güven puanı cezası mı yoksa kesin eleme mi olduğu.
- Kullanılan trend/yön tespit formülü ve eşikleri.

## BigE'deki mevcut davranış

- `15m→1h`, `30m→2h`, `1h→4h`, `2h→4h`, `4h→1d`, `1d→1w` eşlemesi
  BigE yorumudur; Miraz'ın açıklanmış tablosu değildir.
- Uygulama üst TF'yi BigE güvenlik vetosu olarak kullanır. Alt TF artık gözlem
  snapshot'ı üretir ancak puan/veto uygulamaz; kesin karar etkisi açıklanmadığı
  için özellik hâlâ “tam klon” olarak işaretlenmez.
- Problemli üst TF'de sert yön engeli BigE güvenlik filtresidir; Miraz kuralı
  olarak sunulmaz.

## Denetim ekranı

Radar snapshot'ı artık ana TF market yapısını, kullanılan üst TF'yi, üst TF yapı
sonucunu ve alt TF uygulama durumunu kayıt defterine taşır. HTF çatışmasıyla
filtrelenen setuplar TF eşlemesi, motor, kalite, kalite geçişi ve doğrulanmış
karşı-olgusal TP/STOP sonucu ile birlikte gösterilir.

Alt TF gözlemi, terminalde görülen TF merdiveninin bir alt basamağını kullanır:
`30m→15m`, `1h→30m`, `2h→1h`, `4h→2h`, `1d→4h`. En düşük `15m` için kanıtsız
bir `5m` eşlemesi yapılmaz. Bu tablo `BigE-adjacent-observed-TF-interpretation`,
kesin Miraz eşlemesi ise `undisclosed-by-archive` olarak yayınlanır.

LTF market yapısı setup yönüyle aynıysa `trend-devam`, tersiyse `zayiflama`,
yatay/belirsizse `notr` snapshot'ı üretilir. Bu alan `observation-only` çalışır;
trade kategorisini, güven puanını veya Result Journal'ı değiştirmez. Denetim
tablosu betimseldir ve nedensel başarı iddiasında bulunmaz.

## LTF gözlem sonucu

Filtered kayıtlar `trend-devam`, `zayiflama` ve `notr` LTF snapshot'larına göre
ayrılır. Her sınıfta toplam setup sayısı ile sonradan doğrulanmış karşı-olgusal
TP/STOP dağılımı gösterilir. LTF snapshot kapsamı ve sonuç doğrulama kapsamı ayrı
metriklerdir; eski kayıtlardaki `not-implemented` / `not-available` değerleri
gözlemli örnek sayılmaz.

Bu metrik `verified-counterfactual-distribution-not-win-rate` adını taşır.
LTF henüz işlem seçmediğinden değerler “filtrenin engellediği STOP” veya Win Rate
olarak sunulmaz; yalnız gelecekteki kalibrasyon için gözlemsel ilişki sağlar.

## Kalibrasyon güvenlik kapısı

Arşiv LTF/HTF gözlemini otomatik puan veya veto kuralına çevirmek için gereken
minimum doğrulanmış örnek sayısını, etki formülünü ve istatistiksel güven eşiğini
açıklamaz. Bu değerler tahmin edilmez. `MTF_KALIBRASYON_POLICY` bu nedenle:

- `state: locked`
- `automatic_activation: false`
- `minimum_verified_samples: null`
- `effect_formula: undisclosed-by-archive`
- `trade_effect: none`

olarak çalışır. Örnek sayısı ne kadar büyürse büyüsün kapı kendiliğinden açılmaz.
Kilidin kaldırılması için açık eşik, belgelenmiş etki formülü, örneklem dışı
doğrulama ve operatörün açık aktivasyonu birlikte gerekir.

Bu güvenlik kapısı yeni gözlem-türevli kuralları kapsar. Önceden var olan HTF
sert vetosu ayrı biçimde `unchanged-BigE-safeguard` olarak kalır ve Miraz'ın
açıklanmış kesin kuralı olduğu iddia edilmez.
