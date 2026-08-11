# Filtered — denetlenebilir alt nedenler

## Arşiv kanıtı

- `2059325292926148742`: Filtrelenen setupların stop riskini azaltmak için özel
  filtrelerden geçtiğini söyler.
- `2064005426710986769`: setup puanının entry'ye kadar değiştiğini, zayıflayan
  yapıların elendiğini ve filtre aşamalarını doğrular.

Arşiv `Filtered` sonucunu kanıtlar; bütün filtrelerin kesin ad→algoritma eşlemesini
açıklamaz.

## BigE denetim alt nedenleri

Ana journal statüsü değişmeden `durum_nedeni` alanında şunlar tutulur:

- `htf-conflict`: radar notunda üst zaman/HTF uyuşmazlığı.
- `quality-weakened`: entry öncesi güven puanı geriledi ve aday filtrelendi.
- `stale-zone`: bölge/hedეფ geçmişte tüketilmiş.
- `structural-invalidity`: stop/yapı bölgesi önceden geçersizleşmiş.
- `filtered-other`: bilinen özel sınıfa girmeyen yeni filtre.
- `legacy-unknown`: eski kayıtta neden tutulmamış.

Bu adlar Miraz'ın açıklanmış özel taksonomisi değil, BigE'nin radar kanıtlarından
ürettiği denetim etiketleridir. API bu kökeni açıkça bildirir.
