# Filtered etki raporu

Arşivdeki `2059325292926148742` numaralı tweet, filtrelenen ve late kalan
setupların sonradan oluşan sonuçları üzerinden kaç STOP'tan korunduğunun
raporlandığını kanıtlar. Bu tweet, güncel BigE kayıtlarının sonucunu kanıtlamaz.

Bu nedenle terminal iki veriyi birbirine karıştırmaz:

- `setup_sayisi` ve `nedenler`: Kalıcı Filtered kayıtlarının denetlenebilir hacmi.
- `engellenen_stop` / `olasi_tp`: Yalnız aynı kayıt için sonradan açıkça TP veya
  STOP karşı-olgusal sonucu kaydedilmişse hesaplanır.

Karşı-olgusal takip yoksa `engellenen_stop` değeri `null`, arayüz değeri `—` ve
`claim_allowed` değeri `false` olur. Arşivdeki geçmiş günün 2 STOP sayısı canlı
veriye taşınmaz. Karşı-olgusal sonuç Result Journal'a ve R toplamına eklenmez.

Canlı takip yalnız ileri doğrudur. Filtre kararı sonrası motorun ilk gördüğü son
mum başlangıç çizgisi olarak kaydedilir; bu mum ve öncesi sonuç sayılmaz. Sonraki
mumlarda giriş ve TP temasla, STOP ise invalidasyon ötesindeki mum kapanışıyla
doğrulanır. Arşiv karşı-olgusal takip penceresini açıklamadığından otomatik expiry
uygulanmaz; bu davranış Miraz kuralı değil, veri sızıntısını önleyen BigE takip
politikasıdır.

## Kırılımlar

Terminal, filtre etkisini motor (`Price Action` / `Harmonik`), timeframe,
filtre anındaki kalite ve BigE denetim nedeni bazında ayırır. Hacim tüm kayıtlar
üzerinden, TP/STOP dağılımı yalnız doğrulanmış kayıtlar üzerinden hesaplanır.
Her satırın doğrulama kapsamı ayrıca gösterilir. `stop_payi_yuzde`, yalnız izlenen
örneklerdeki STOP payıdır; filtrenin nedensel başarı oranı veya Miraz'ın açıklanmış
bir skoru değildir. Arşiv bu özel kırılım formülünü açıklamadığından API politikası
`causality_claim: not-made` olarak yayınlanır.

## Kalite geçiş playback'i

`kalite_gecmisi` içindeki ardışık ve birbirinden farklı snapshotlar `A→B`,
`B→C` gibi geçişlere dönüştürülür. Aynı setup aynı geçişi tekrar yaşarsa o
geçiş satırında bir kez sayılır. Aynı setup farklı geçişlerde görünebilir;
dolayısıyla satırlar toplanarak benzersiz setup toplamı elde edilmez.

Geçiş yönü yalnız `A+ > A > B > C > D` sırasına göre `guclendi` veya
`zayifladi` olarak etiketlenir. Karşı-olgusal TP/STOP dağılımı yalnız doğrulanmış
setuplardan gelir. Bu tablo hangi geçişlerin hangi sonuçlarla birlikte görüldüğünü
anlatır; geçişin sonucu nedensel olarak oluşturduğunu veya bunun terminalMiraz'ın
gizli kalite formülü olduğunu iddia etmez.

Filtered alt nedenleri BigE'nin radar notlarından üretilen denetim taksonomisidir;
terminalMiraz'ın arşivde açıklanmış birebir neden eşlemesi değildir.
