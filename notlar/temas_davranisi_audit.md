# Temas Davranışı — kanıt ve Journal snapshot

## Doğrudan arşiv kanıtı

- Tweet '2063838608230883776' (8 Haziran 2026), TAO planında fiyatın işlem
  bölgesine iki kez temas ettikten sonra yaklaşık '%20' yükseldiğini açıkça
  anlatır.
- Aynı tweete 'tweet_gorsel.json' içinde
  'HKQ4_NFWgAEVWK2.png' ve 'HKQ5As9XkAAP1e0.png' bağlıdır. İlk grafik planı,
  ikinci grafik gerçekleşen bölge tepkisini gösterir.

Bu kanıt, bölge temaslarının analizde izlenen bir olgu olduğunu destekler.

## Uygulanan snapshot

Radar satırı ve Journal kaydı, setup üretildiği anda bölgenin toplam temas,
tepki, kırılma, içeride kalma, son davranış ve tepki oranı özetini saklar.
Memory ekranı sonuçlanan kayıtları '0', '1', '2', '3+' temas kovalarında ayrı
gösterir. Eski kayıtlar geriye dönük doldurulmaz.

## Kanıt sınırı

Arşiv temas sayımının kesin durum makinesini, dört temasta doygunluk eşiğini
ve güven puanı ağırlıklarını açıklamaz. Bunlar mevcut BigE sezgisidir ve
'BigE-heuristic-not-disclosed-by-archive' olarak etiketlenir; Miraz kuralı
olarak sunulmaz. Dokunuş kovaları gözlemsel Journal kırılımıdır ve otomatik
performans iddiası üretmez.
