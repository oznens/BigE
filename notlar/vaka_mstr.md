# Vaka Çalışması: MSTR (Strategy Inc) — Market Yapısı + Kaldıraçlı BTC Vekili

> Kaynak: @tradermiraz, 2 tweet (Kas 28 2025 – Ara 21 2025), MSTR 1G & 1H.
> Yeni kavram: **Market yapısı** (HH/HL vs LH/LL) ve hisse senedinin
> **kaldıraçlı BTC vekili** olarak okunması.

## Bağlam — MSTR nedir?

Strategy Inc (eski adıyla MicroStrategy), bilançosunda **415.000 BTC**
(~36,4 milyar $) tutan bir şirket. Arkham ekran görüntüsü bunu doğruluyor:
tek varlık BTC. Yani MSTR fiilen **kaldıraçlı bir BTC vekili** — BTC düşünce
MSTR daha sert düşer. Miraz: *"Bu şirket Strateji arkadaşlar. Ellerinde 415K
BTC var. Haftalardır satılıyor."*

## 1. Tweet — MSTR 1 Günlük (Kas 28, 2025)

> *"Önce iyiymiş gibi (Düzeltiyoruz korkmayın..), Sonra kötü.. En sonunda
> kötünün iyisi.."*

- İki **bullish harmonik** (kırmızı gölge), ikisi de aynı **mavi kutuda**
  (123,06–132,32) D noktasını tamamlıyor → çift teyit = güçlü destek.
- Fiyat 175,64. Projeksiyon: mavi kutuya in → oradan tepki.
- "Kötünün iyisi" = mavi kutudaki sıçrama.

## 2. Tweet — MSTR 1 Haftalık Güncelleme (Ara 21, 2025)

> *"Nasıl bir strateji izliyorlar bilmiyorum. Temel tarafta çok araştırmadım.
> Fakat teknik olarak **Market yapısı aşağıya dönmüş**.. Mavi kutuda bir nebze
> dinleneceğiz."*

Dört görsel:
- Günlük (aynı mavi kutu 123–132, iki bullish harmonik)
- 1H güncel: **kademeli destekler** — mavi kutu (123–132) birincil, kırılırsa
  **yeşil kutu (69,13–73,00)** derin destek. Mor kutu (285,78–319,89) direnç.
  İki senaryo: 🟢 mavi kutudan tepki VEYA 🔴 yeşil kutuya devam.
- Arkham: 415,23K BTC, 36,41B $ (temel dayanak)
- 1H "Market yapısı (Trend bölgesi)": iki kırmızı daire 231,66 seviyesinde —
  yapının kırıldığı yatay seviye.

## 🔑 Dersler

### 1. Market yapısı = HH/HL vs LH/LL (mekanikleştirilebilir) ⭐
Miraz'ın "market yapısı aşağıya dönmüş" dediği şey saf Price Action:
- **Yükseliş yapısı**: daha yüksek tepe (HH) + daha yüksek dip (HL)
- **Düşüş yapısı**: daha düşük tepe (LH) + daha düşük dip (LL)
- **BOS** (Break of Structure): trend yönünde son swing'in kırılması = devam
- **CHoCH** (Change of Character): trende ters ilk kırılım = dönüş sinyali

"Trend bölgesi" (231,66) = yapıyı tutan yatay seviye; altına kapanış = yapı
aşağı döndü.

### 2. Kademeli destekler + senaryo dallanması
Tek destek değil: mavi kutu (birincil) kırılırsa yeşil kutu (derin). Plan
şartlı: "mavide dinleniriz, kırılırsa yeşile."

### 3. Çoklu harmonik aynı PRZ'de = güçlü bölge
İki bullish harmonik aynı mavi kutuda D yapıyor → confluence, bölgeyi
güçlendiriyor. (Sistemde zaten "mavi daire" mantığıyla örtüşüyor.)

### 4. Kaldıraçlı BTC vekili — temel/teknik ayrımı
MSTR ≈ kaldıraçlı BTC. Miraz teknik okur ama temeli (415K BTC) bağlam
olarak kabul eder. BTC zayıfsa MSTR daha riskli.

## Sisteme yansıma (yapılacaklar)
- [x] **Market yapısı modülü** (`yapi.py`): `market_yapisi(df)` son iki swing
      high/low'dan yükseliş/düşüş/yatay + BOS/CHoCH kırılımı hesaplar.
- [x] **Senaryoya entegre**: plan metnine "📉 Market yapısı düşüşte (LH+LL) —
      long açısından temkinli ol" satırı eklendi; `Senaryo.market_yapisi` alanı.
- [x] **CHoCH-aşağı / BOS-aşağı** durumunda long uyarısı (MTF problemli ile aynı mantık).
- [ ] *(opsiyonel)* Kademeli destek dallanması yol haritasına daha açık
      yazılabilir; çoklu harmonik confluence skoru.

> MSTR vakasının ana dersi (market yapısı) sisteme yansıtıldı. ✅
> 49/49 test geçiyor.
