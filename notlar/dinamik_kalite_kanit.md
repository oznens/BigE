# Dinamik Kalite Motoru — kanıt ve uygulama

## Arşiv kanıtı

Tweet `2064005426710986769` şunları doğrudan söyler:

- Setup bulunması işleme uygun olduğu anlamına gelmez.
- Kalite puanı zaman içinde değişir.
- Entry seviyesine ulaşana kadar aday tekrar tekrar kontrolden geçer.
- Zayıflayan yapılar elenir, güçlenen yapılar takip edilir.

## BigE davranışı

- Yalnız `Bekliyor/Aday` setup'lar her başarılı radar turunda yeniden değerlendirilir.
- Entry gerçekleşmiş açık pozisyonun geçmiş kararı geriye dönük değiştirilmez.
- Kalite veya güven değiştiğinde zaman, kalite, güven, karar kategorisi ve lifecycle
  kalıcı `kalite_gecmisi` dizisine eklenir.
- Aynı puanın tekrar görülmesi geçmişi şişirmez.
- Bu geçmiş Result Journal ve TradePlayBack verisine taşınır.

## Kanıt sınırı

Tweet “saniye saniye” ve “onlarca kontrol” ifadelerini kullanır; kesin tarama
frekansı ve kontrol sayısını açıklamaz. BigE çalışma aralığını yapılandırmadan alır
ve uydurma sabit kontrol sayısı üretmez.
