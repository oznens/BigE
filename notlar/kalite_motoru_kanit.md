# terminalMiraz kalite motoru — kanıt ve uygulama sınırı

Bu belge `tweetler/tweetler.json` ve bağlı arşiv görsellerindeki doğrudan
kanıtları BigE uygulamasından ayırır. Açıklanmayan bir filtre veya sayı Miraz
kuralı kabul edilmez.

## Doğrudan kanıtlanan davranışlar

| Davranış | Kanıt | Güven |
|---|---|---|
| Bir setup bulunması işlem almak için yeterli değildir | Tweet `2066320810545910019` | Doğrudan |
| Price Action kalite kontrolü 3 kademedir | Tweet `2066320810545910019` | Doğrudan |
| Harmonik kalite kontrolünde 4 özel filtre detayı vardır | Tweet `2066320810545910019` | Doğrudan |
| Harmonikler 5 test aşamasından, her aşamada 4 kontrolden geçer | Tweet `2060346993600262442` | Doğrudan; aşama içeriği gizli |
| Setuplar sürekli sorgulanır, filtrelenir ve yeniden değerlendirilir | Tweet `2066320810545910019` ve `2064005426710986769` | Doğrudan |
| Lifecycle filtreleri kalite motorundan önce çalışır | Tweet `2064005426710986769` | Doğrudan |
| Güçlenen yapılar takip edilir, zayıflayanlar elenir | Tweet `2064005426710986769` | Doğrudan |
| Kalite puanı entry seviyesine kadar değişebilir | Tweet `2064005426710986769` | Doğrudan |
| 31 setup içinden 17'si işleme değer bulunmuştur | Tweet `2066321868605296657` | Doğrudan örnek |

## Arşivin açıklamadığı ayrıntılar

- PA'daki üç kademenin özel adları ve kesin koşulları.
- Harmoniğin beş aşamasının ve aşama başına dört kontrolünün özel adları,
  sırası ve sayısal eşikleri; kalite kontrolündeki dört özel filtrenin bunlarla
  ilişkisi.
- Güven skorunun taban değeri ve her sinyalin puan katkısı.
- A+/A/B/C/D sınırları ile Trade/Watch/Skip yüzde eşikleri.
- Late için kullanılan kesin mesafe/yüzde eşiği.

Bu ayrıntılar tweet veya görsel kanıt bulunmadan terminalMiraz kuralı olarak
etiketlenemez.

## BigE'deki mevcut karşılık

`src/miraz/karar.py`, gözlenen kalite/güven arayüzünü çalıştırabilmek için yerel
bir heuristic kullanır. Model kimliği `BigE heuristic v1`, kanıt durumu
`weights-unverified` değeridir. Ağırlıklar `BIGE_SKOR_AGIRLIKLARI` sözlüğünde
tek yerde tutulur; backtest ile kalibre edilene kadar Miraz formülü değildir.

Harmonik tarafta Fibonacci oran uygunluğu, kalite, PRZ darlığı ve yapı
geçerliliği kontrolleri vardır. Bunlar standart harmonik literatürü ve BigE
uygulamasıdır; arşivde bahsedilen dört gizli filtrenin birebir karşılığı olduğu
iddia edilmez.

`Cancelled Harmonic` için metin+görsel doğrulama ve uygulama ayrıntıları
`notlar/harmonik_gecerlilik_kanit.md` dosyasındadır.

`Defter.adaylari_yeniden_degerlendir`, her yeni radar turunda henüz entry
olmamış adayın kalite/güvenini günceller. Aday artık Trade değilse bekleyen emir
uygun lifecycle nedeniyle (`Filtered`, `Late`, `Cancelled`, `No-Entry`) kapanır.
Entry olmuş açık pozisyon bu geriye dönük kalite kontrolünden etkilenmez.

## Klonlama kararı

1. Kanıtlı dış davranış korunur: ayrı PA/harmonik değerlendirme, dinamik kalite,
   lifecycle ön filtresi ve entry'ye kadar yeniden değerlendirme.
2. Açıklanmayan özel filtreler tahmin edilmez.
3. BigE heuristikleri sonuç üretmeye devam eder fakat köken metadatasıyla taşınır.
4. Görsel veya metin arşivinde yeni doğrudan kanıt bulunduğunda bu matris ve
   ilgili test birlikte güncellenir.
