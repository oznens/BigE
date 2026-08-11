# TF × motor hafızası — kanıt sınırı

Tweet '2064005426710986769', terminalMiraz'ın enstrümanları dört farklı zaman
diliminde eş zamanlı taradığını doğrular. Tweet '2060971866534138311' ise Price
Action Memory Lab ve Harmonic Memory laboratuvarlarını ayrı adlandırır.

BigE Journal kayıtları zaten setup zaman dilimini ve motor kaynağını saklar.
Memory ekranındaki eski TF karakter tablosu bütün motorları birleştirdiği için
aynı TF'deki PA ve Harmonik sonuçları ayırt edilemiyordu. Yeni TF × motor
matrisi yalnız sonuçlanan TP/STOP kayıtlarını 'Price Action' ve 'Harmonik'
olarak ayrı toplar.

Arşiv TF performansının otomatik veto/delist eşiğini açıklamaz. Bu nedenle
matris 'observation_only=true' ve 'auto_filter=false' çalışır. Late kayıtları
strateji motoru olmadığı için bu kalibrasyona dahil edilmez; genel sonuç
tablolarında ayrı izlenmeye devam eder.
