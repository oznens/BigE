# @tradermiraz → BigE Uygulama Audit'i (2026)

Kaynak arşiv: `tweetler/tweetler.json` + `tweetler/gorseller/` + `METODOLOJI.md`.
Repo içindeki arşiv 5.054 tweet ve 7.731 chart kapsar. Bu audit'in amacı yeni bir
üslup özeti çıkarmak değil; damıtılmış metodolojinin **gerçek yürütme koduna** ne
ölçüde taşındığını kontrol etmektir.

## Sonuç özeti

BigE, Miraz'ın **setup bulma araçlarını** büyük ölçüde kapsıyor; fakat **işleme giriş
ve pozisyon yönetimi** tarafı aynı sadakatte değil. En önemli sapma, arşivde
vurgulanan kapanış teyidi / retest / en az 2R / kısmi kâr + BE zincirinin canlı
paper-trading lifecycle'ında tam uygulanmaması.

## 1. Arşivde açık, kodda eksik veya yarım

### A. Kapanış + hacim teyidi — YÜKSEK ÖNCELİK
Arşiv kuralı: fitil kırılımı tek başına tetik değildir; seviye ötesinde hacimli
mum kapanışı beklenir.

Mevcut durum:
- karar motoru hacmi daha çok `kirilma_riski` cezası olarak kullanıyor;
- paper execution giriş/TP/STOP tarafında high/low dokunmasıyla ilerliyor;
- gerçek bir `close crosses level AND volume confirms` giriş kapısı yoktu.

Miraz-v2: `kapanis_hacim_onayi()` eklendi.

### B. Kırılım + retest — YÜKSEK ÖNCELİK
Arşiv kuralı: trend/seviye kırılımının geri testi sık kullanılan entry teyididir.

Mevcut durum:
- çekirdek kodda genel amaçlı, işlem girişini bloke eden bir retest doğrulayıcısı
  bulunmuyordu.

Miraz-v2: `retest_onayi()` eklendi.

### C. Minimum 1:2 R/R — YÜKSEK ÖNCELİK
Arşiv kuralı: küçük risk, minimum 1R:2R.

Mevcut durum:
- `karar.py`, RR >= 2 olduğunda ekstra güven veriyor;
- buna rağmen `risk.py` varsayılan `RR_HEDEF = 1.0` ile 1R hedef üretiyor.

Bu iki katman birbirleriyle çelişiyor. Miraz-v2 varsayılan ana hedefi 2R yapar.

### D. Kısmi kâr + stop'u girişe taşıma — YÜKSEK ÖNCELİK
Arşiv ve `risk.py` açıklaması: ilk hedefte yaklaşık %60-70 kâr al, kalan
pozisyonun stop'unu entry'ye çek.

Mevcut durum:
- `RiskPlan.kar_al_birincil` ve açıklama metni bu kuralı taşıyor;
- fakat paper lifecycle gerçek anlamda kısmi pozisyon ve BE durumu işletmiyor.

Miraz-v2 varsayılanı: +1R'de %65 realize, kalan %35 BE; 2R final olursa toplam
+1.35R, BE olursa +0.65R.

### E. Kapanış bazlı invalidasyon — YÜKSEK/ORTA ÖNCELİK
Arşivde geçersizlik çoğu kez "X altında/üstünde kapanış" olarak tarif ediliyor.
`risk.py` de fitili sert stop, asıl invalidasyonu kapanış bazlı diye açıklıyor.

Mevcut lifecycle ise high/low stop dokunuşunu doğrudan STOP sayıyor. İleride
`hard emergency stop` ile `close invalidation` iki ayrı seviye olarak tutulmalı.

## 2. Arşivde var, BigE'de bağımsız motor olarak görünmeyenler

Bunlar eklenebilir fakat önce frekans/sonuç analizi yapılmalı; sırf tweetlerde
geçtiği için Trade skoruna eklenmemeli.

- 2.618 stratejisi / Fib extension hedefleri
- CME GAP
- Ending Channel / takoz
- fraktal / tarih tekerrürü
- haber rejimi: FED/CPI günleri özel risk modu
- spot/uzun vadede kademeli alım (yardımcı plan var; live execution entegrasyonu sınırlı)

## 3. BigE'de güçlü ağırlığı olan fakat Miraz'ın literal çekirdek sözlüğü olmayanlar

`Drift / Torque / Root / Shade / Strike / Cavity / Shear / Ladder / Buffer /
Reservoir` BigE'nin Price Action soyutlama etiketleridir. Miraz metodolojisindeki
likidite, CHoCH/MSB, FVG, trend, destek/direnç vb. fikirlere eşlenebilirler; fakat
bu isimler ve mevcut sabit `KONSEPT_PUAN` ağırlıkları Miraz'ın yayımlanmış bir
puanlama tablosu değildir.

Bu nedenle:
- açıklama/etiket olarak kalabilirler;
- Trade/Watch eşiklerini ±18 oynatmaları **kanıtlanana kadar** Miraz sadakati
  olarak sunulmamalı;
- P4 ablation/OOS ile katkıları pozitif değilse skor etkileri sıfırlanmalı.

## 4. Güven yüzdesi konusunda sapma

BigE'nin `%70/%80/%90 güven` değeri bir olasılık değil, heuristik skordur.
Geçmiş trade verisinde yüksek güven bandı monoton şekilde daha iyi sonuç
vermedi. Bu yüzden kullanıcıya `%90 kazanma ihtimali` gibi sunulmamalı.

Öneri: adı `Setup Skoru` olsun; gerçek olasılık ancak calibration/OOS sonucu
ayrıca gösterilsin.

## 5. Uygulama sırası

1. Miraz-v2 shadow: close+volume, retest, 2R, partial+BE.
2. Eski motor ve v2 aynı setup'larda paralel sonuç biriktirsin.
3. En az birkaç farklı piyasa rejimini kapsayan OOS örnek oluşunca Net R,
   expectancy, PF ve MDD karşılaştırılsın.
4. V2 üstünlüğü doğrulanırsa live Trade lifecycle'a geçirilsin.
5. 2.618/CME GAP/Ending Channel gibi ek modeller ancak ayrı ablation sonrası
   karar skoruna dahil edilsin.

## Neden doğrudan canlıyı değiştirmiyoruz?

Arşiv metodolojisi 2R yönetimini desteklese de elimizdeki son paper-trade veri
seti ağırlıklı olarak 1R lifecycle ile üretildi. Aynı tarihsel sonuçları 2R'ye
çevirerek varsaymak look-ahead olur. Miraz-v2'nin kendi OHLC yolu üzerinden
paralel ölçülmesi gerekir.
