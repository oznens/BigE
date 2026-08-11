# Scanner Memory / parite karakteri — kanıt matrisi

## Doğrudan kanıt

Tweet `2061490944713601191` Price Action tarafında her paritenin geçmişte
konseptlere verdiği tepkinin Scanner Memory Laboratuvarı'nda kaydedildiğini
söyler.

Verilen örnekler:

- UNIUSDT: 11 TP / 3 STOP, `77 skor`, üst sıralar.
- XLMUSDT: 5 TP / 8 STOP, `38 skor`, delist adayı.
- İlk ay konsept başına yaklaşık 5–10 kayıt vardır.
- İkinci ay 20+ kayıt beklendiği ve kararların o zaman istatistiksel olarak daha
  sağlıklı olacağı belirtilir.

Tweet `2065351371017134220`, PA testlerini geçemeyen 21 parite bulunduğunu, en
az 15 paritenin daha delist edileceğini ve amacın yalnız konseptlere istikrarlı
tepki veren paritelerde işlem aramak olduğunu doğrular.

## Açıklanmayan ayrıntılar

- `77` ve `38` skorlarının kesin formülü.
- Kesin delist skor/WR/expectancy eşiği.
- Minimum kayıt sayısının sert engel mi, yalnız güven ölçüsü mü olduğu.
- Delist kararının otomatik mi yoksa manuel onaylı mı olduğu.

UNI'nin 11/3 ampirik WR'ı `%78,6` iken skorun `77` olması, skorun yalnızca
yuvarlanmış WR olmadığını gösterir.

## BigE uygulaması

- `Defter.parite_hafiza()` yalnız Price Action TP/STOP sonuçlarını sembol bazında
  toplar; harmonik sonuçları Scanner Memory'ye karıştırmaz.
- TP, STOP, ampirik WR, toplam R ve örnek sayısı API'ye taşınır.
- 20 altı kayıt `learning`, 20+ kayıt `mature` olarak gösterilir. Bu, tweet'teki
  istatistiksel olgunluk açıklamasıdır; işlem/delist eşiği değildir.
- Kesin formül açıklanmadığından `miraz_score=null` ve
  `score_model=terminalMiraz-formula-undisclosed` döner.
- `auto_delist=false`; kanıtsız eşik kullanılarak parite otomatik silinmez.
- MEMORY ekranındaki parite tablosu PA karakter hafızasını ve örnek olgunluğunu
  gösterir. Genel PNL parite tablosu ayrı kalır.

Mevcut `ClusterHafiza`, sembolden bağımsız setup-benzerliği hafızasıdır ve
Scanner Memory parite karakteriyle aynı şey değildir.
