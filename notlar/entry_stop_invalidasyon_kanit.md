# Entry / stop / invalidasyon — kanıt matrisi

## Doğrudan kanıtlananlar

- Tweet `2040822394990858425`: Trade Scanner her setup için Entry, Stop, TP,
  Kalite ve trade edilir/edilmez kararı üretir.
- Tweet `2026743854096068846`: SOL long düşüncesi yalnız `76$ altında mum
  kapanışı` ile iptal olur; fiyat fitil hareketine rağmen kapanış yapmadığı için
  senaryo korunmuştur.
- Tweet `1907119000632402098` ve `1907120092963364982`: ETH short düşüncesi
  `2100 üstünde kapanışlar` ile tamamen iptal olur; stop bölgesi kapanışa göre
  ayarlanmalıdır.
- Tweet `2033896239251522041`: manuel pozisyon yönetimi örneğinde short işlemin
  %50'sinde kâr alıp kalan stopu entry'ye çekmek önerilir.
- Tweet `2060346993600262442`: terminalMiraz testlerinde 1:1 risk yönetimi ayrı
  model olarak kullanılmıştır.

## Uygulanan davranış

- Limit entry bölge temasında dolar: long `low <= entry`, short `high >= entry`.
- TP hedef temasında sonuçlanır.
- STOP yalnız mum stop seviyesinin ötesinde kapandığında sonuçlanır:
  - Long: `close < stop`
  - Short: `close > stop`
- Stop fitili tek başına STOP değildir. Aynı mum hedefe de değerse ve kapanış
  stop ötesinde değilse TP yazılır.
- Bu davranış canlı portföy, radar geçerlilik kontrolü, backtest laboratuvarı,
  sonuç doğrulayıcı ve statik journal kapanış-zamanı çözümünde aynıdır.

## Kanıt/yorum sınırı

Arşiv kapanış invalidasyonunu açıkça kanıtlar. Buna karşılık limit entry'nin
fitil temasıyla dolması ve TP'nin temasla sonuçlanması BigE execution yorumudur;
tweetler kesin borsa emir-fill ayrıntısını açıklamaz.

%50 kâr alıp stopu entry'ye çekme, manuel metodoloji kanıtıdır. Güncel BigE
Result Journal sabit 1R TP/−1R STOP sonucunu kullanır; bu manuel yönetim kuralı
kanıt olmadan otomatik journal politikasına eklenmez.
