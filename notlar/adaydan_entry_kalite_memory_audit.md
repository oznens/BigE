# Adaydan entry'ye kalite yolu denetimi

## Arşiv kanıtı

Tweet `2064005426710986769` şunları doğrudan söyler:

- Setup bulunması işleme uygun olduğu anlamına gelmez.
- Kalite puanı zaman içinde değişir.
- Aday, entry seviyesine ulaşana kadar tekrar tekrar kontrolden geçer.
- Zayıflayan yapılar elenir; güçlenen yapılar takip edilir.

Bu kanıt daha önce kalıcı `kalite_gecmisi` ve entry anı kalite/güven snapshot'ı
ile koda taşınmıştı. Eksik olan, ilk aday snapshot'ını gerçek entry snapshot'ına
ve sonuca bağlayan özet hafızaydı.

## Uygulanan gözlem

Yalnız gerçek entry kalite/güven snapshot'ı ve açıkça
`candidate-quality-snapshot` olarak işaretlenmiş ilk aday geçmişi bulunan
TP/STOP kayıtları kullanılır. Motor bazında:

- İlk kalite → entry kalitesi geçişi,
- Güven puanının kesin fark işaretine göre `YÜKSELDİ / AYNI / DÜŞTÜ`,
- TP, STOP, WR, R ve ortalama güven farkı

raporlanır. Güven yönü için yapay bir büyüklük eşiği yoktur; yalnız gerçek puan
farkının işareti kullanılır. Eski kayıtlar doldurulmaz. Bu hafıza otomatik
Trade/Watch/Skip kararı veya Miraz'a atfedilen yeni bir filtre üretmez.
