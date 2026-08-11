# Late Setup — kanıt, davranış ve bilinmeyenler

## Kanıtlananlar

- `2059325292926148742`: Geç Kalmış Setuplar özel filtrelenmiş yapılardır ve
  amaçlarından biri stop riskini azaltmaktır.
- `2065351367544181110`: Late Setup sonuçları TP/STOP olarak ayrı raporlanır.
- `2065351363828003079`: performans Late dahil ve Late hariç kıyaslanır; Late
  katkısı toplam performansta ayrıca önemlidir.

## Arşivde açıklanmayan kural

Tweet arşivi bir setup'ın hangi sayısal eşik veya formülle “Late” olduğunu
açıklamıyor. Önceki BigE kodundaki `%50 entry→hedef yolu` eşiği arşiv kanıtına
dayanmıyordu ve otomatik terminalMiraz kuralı olmaktan çıkarıldı.

## Uygulanan güvenli davranış

- Kayıtlı/import edilmiş Late işlemler TP/STOP/R olarak ayrı bucket'ta tutulur.
- Toplam R, Late katkı R ve Late hariç toplam R ayrı hesaplanır.
- Kesin tespit formülü bulunana kadar radar otomatik Late etiketi üretmez.
- `%50` hesabı yalnız açık eşik verilen BigE deneyi olarak çağrılabilir; canlı
  terminalMiraz sınıflandırmasında varsayılan değildir.
