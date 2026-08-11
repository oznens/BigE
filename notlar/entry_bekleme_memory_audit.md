# Adaydan entry'ye bekleme memory denetimi

## Arşiv kanıtı

- Tweet `2065351363828003079`, terminalMiraz Result Journal içinde `Late`,
  `Expired` ve `No Entry - Result` durumlarını ayrı ayrı gösterir.
- `notlar/late_setup_kanit.md`, Late durumunun giriş bölgesi tüketildikten sonra
  yeniden entry kovalanmamasıyla ilgili kanıtı ayırır.
- `notlar/cancelled_expired_no_entry_kanit.md`, Expired durumunun arşivde
  kanıtlandığını fakat kesin süre veya bar sayısının açıklanmadığını kaydeder.

## Uygulanan gözlem

Portföy motoru, gerçek fill gerçekleştiğinde aday açılışından entry barına kadar
gözlenen kesin bar sayısını ve o çalıştırmada kullanılan `max_bekleme` limitini
snapshot olarak saklar. Yalnız bu snapshot bulunan TP/STOP kayıtları; motor,
zaman dilimi, kesin bar sayısı ve çalışma limitiyle raporlanır.

Bar sayıları kovalanmaz veya keyfi aralıklara bölünmez. Mevcut varsayılan 24 bar
BigE çalışma ayarıdır; Miraz süresi değildir. Eski kayıtlara backfill yapılmaz ve
bu hafıza otomatik Late/Expired/Trade filtresi üretmez.
