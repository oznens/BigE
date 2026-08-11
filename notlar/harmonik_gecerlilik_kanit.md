# Harmonik geçerlilik ve Cancelled Harmonic kanıtı

## Doğrudan arşiv kanıtı

Tweet `2062383146415333550`, C bölgesi belirlendikten sonra fiyatın harmoniği
iptal edecek biçimde hareket ettiğini; buna rağmen eski setup bölgesinin
hafızada kaldığını ve fiyat günler sonra geldiğinde geçerli harmonik gibi
değerlendirildiğini anlatır.

Bağlı görseller:

- `tweetler/gorseller/HJ8GqU6W8AAA0n7.png`: ALGOUSDT 15m Harmonic Shark yanlış
  biçimde TP görünür.
- `tweetler/gorseller/HJ8KoTLWIAAHcBQ.png`: aynı kayıt geçmiş düzeltmesinden sonra
  `Cancelled Harmonic` görünür.

Tweet ayrıca mantık hatasıyla oluşan TP'nin başarı sayılmaması gerektiğini ve
harmonik geçerliliğini kaybettiği anda `Cancelled` statüsüne düşmesi gerektiğini
doğrudan söyler.

## BigE uygulaması

- Oluşmakta olan harmoniklerde C sonrası yapı ve PRZ geçerliliği
  `_olusan_gecerli` ile kontrol edilir.
- Tamamlanmış XABCD adaylarında C→D arasındaki yapı bozulması artık
  `_tamamlanmis_gecerli` ile reddedilir.
- Bekleyen harmonik kaydı sonraki başarılı taramada aynı pattern'i kaybeder veya
  başka motora/pattern'e dönüşürse emir `Cancelled` olur.
- Entry olmuş açık pozisyon, sonraki pattern değişimiyle geriye dönük kapatılmaz.

## Kanıtlanmayan ayrıntı

Arşiv yapı bozulmasının kesin fitil/kapanış toleransını açıklamaz. Kullanılan
%0.2 tolerans mevcut BigE forming kontrolüyle tutarlılık içindir; Miraz kuralı
olarak sunulmaz.
