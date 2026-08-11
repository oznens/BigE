# Harmonik Pattern Audit

Bu katman harmonik motoru desen bazında gözlemler; yeni bir terminalMiraz kuralı
üretmez. Arşiv harmonik sınıflandırmanın ve C→D geçerliliğinin önemini kanıtlar,
ancak Miraz'ın gizli oran filtreleri, pattern başına minimum örnek eşiği veya
otomatik aç/kapat formülü açıklanmamıştır.

## Kaydedilen kanıt

Yeni harmonik setup kayıtlarında desen adıyla birlikte yön, X-A-B-C-D fiyatları,
entry/SL/TP seviyeleri, BigE Fibonacci oranları, BigE motor kalite puanı ve
tamamlanmış D/PRZ merkezi snapshot olarak saklanır. Eski Journal kayıtları bu
alanlarla geriye dönük tahmin edilmez.

Panel her desen için gerçek Result Journal TP/STOP dağılımını, ayrı izlenmişse
Filtered karşı-olgusal sonucu, ayrıntılı snapshot kapsamını ve pattern değişmesi
veya kaybolması nedeniyle gerçekleşen C→D iptallerini gösterir. Gerçek sonuç ile
karşı-olgusal sonuç birleştirilmez.

## Sınırlar

- Desteklenen BigE desenleri: Gartley, Bat, Butterfly, Crab, Deep Crab, AB=CD,
  Shark ve Cypher.
- Oranlar ve motor kalite puanı BigE uygulamasına aittir; Miraz'ın saklı harmonik
  filtrelerinin birebir karşılığı olarak sunulmaz.
- Arşiv minimum örnek eşiği açıklamadığından pattern bazlı otomatik öneri kilitlidir.
- Tamamlanmış pattern için PRZ snapshot'ı D merkezidir; projekte edilen alt/üst PRZ
  bandıyla karıştırılmaz.

## Çapraz matris

Desenler timeframe, yön, Result Journal kalite sınıfı, BigE motorunun ham kalite
değeri, PRZ snapshot kökeni ve kaydedilmiş C→D iptal durumu ile çaprazlanır. Ham
motor kalitesi özellikle aralıklara bölünmez; yeni bir eşik icat etmemek için
snapshot'taki değer aynen kullanılır. `no-recorded-cd-cancellation`, yapının kesin
geçerli kaldığı iddiası değil, yalnız C→D iptal olayının kaydedilmediği anlamına gelir.

## Harmonik playback

Yeni harmonik kayıtlarda ilk pattern tespiti; zaman, pattern, PRZ merkezi ve mevcutsa
BigE motor kalite puanıyla olay geçmişine yazılır. Bekleyen pattern değişir veya
kaybolursa ikinci bir gerçek olay kaydedilir. Playback yalnız bu kayıtlı olayları
zaman sırasında gösterir; legacy kayıtlar için geçmiş üretmez.

Mevcut Journal entry temasının kesin zamanını saklamadığından playback entry zamanı
uydurmaz ve `not-recorded-by-current-journal` yayınlar. TP/STOP yanında kayıtlı
harmonik `Cancelled` vakaları da yaşam döngüsü incelemesi için playback listesine
alınır; bunlar trade sonucu veya R başarısı olarak sayılmaz.
