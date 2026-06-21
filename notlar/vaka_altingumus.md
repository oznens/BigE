# Vaka Çalışması: Altın/Gümüş RASYO — Genel Oran + Flama Formasyonu

> Kaynak: @tradermiraz, 3 tweet (May 5 – Haz 12, 2026), Gold/Silver (XTVXAG) 1G.
> Yeni kavramlar: **RASYO grafiği** (genel göreceli güç) ve **flama / diagonal**
> (yakınsayan üçgen formasyonu).

## Fikir — RASYO grafiği

> *"RASYO grafiği, bize hangi paritenin daha güçlü kaldığını ve hangi tarafta
> pozisyonlanmanın daha mantıklı olabileceğini gösterir."*

ALT/BTC ve BTC/Altın oranlarının **genelleştirilmiş hali**: herhangi iki
varlığın A/B oranı. Burada **Altın/Gümüş**. Oran yükselirse Altın güçleniyor
(Gümüş zayıflıyor), düşerse tersi. "Rasyo bize paranın hangi tarafta olduğunu
gösterir."

## Çağrı ve sonuç (çalıştı ✅)

- **May 5**: Oran ~62,3. Bir **flama yapısı** (simetrik üçgen) gözlemliyor.
  Mor kutu (72,67–76,51) = Haftalık Fraktal direnç; Mavi kutu (48,20–52,70) =
  Haftalık Alıcılı bölge (destek). Beklenti: oran mavi bölgeye iner.
- **May 14 (güncelleme)**: *"Fiyat manipülasyon yaptı, alıcılı bölgeye çekildi,
  Gümüş bir süre güç kazandı. Bu alanda Gümüş'ün güç kaybettiğini göreceğiz."*
  Oran mavi kutuya (52,7) indi → 🟢 yeşil daire (bullish dönüş). "Diagonal" +
  "Trend devam" çizgileri.
- **Haz 12 (güncelleme)**: *"Fiyat mavi alandan ~%25 yükseldi. Beklediğimiz gibi
  Gümüş Altın karşısında değer kaybetti. Gümüş'ün yeniden cazip olacağı bölge
  mor kutu."* Oran 52,7 → 63,27 (+%25,08, ölçülü hareket gösterildi). ✅

## Grafik öğeleri

| Öğe | Anlam |
|---|---|
| 🟣 Mor kutu (72,67–76,51) | Haftalık fraktal direnç (Gümüş yeniden cazip) |
| 🔵 Mavi kutu (48,20–52,70) | Haftalık alıcılı bölge (destek) |
| "Diagonal" çizgi | Düşen üst trend çizgisi (flama tavanı) |
| "Trend devam" çizgi | Yükselen alt çizgi / kırılım sonrası devam |
| 🟢 Yeşil daire (mavi kutuda) | Bullish dönüş noktası |
| 🔴 Kırmızı kutu (projeksiyon) | Ölçülü hareket hedef bölgesi (+%25) |

## 🔑 Dersler

### 1. RASYO = genel göreceli güç (mekanikleştirilebilir) ⭐
ALT/BTC ve BTC/Altın özel hallerdi; asıl kavram **herhangi iki varlığın oranı**.
A/B trendi yükseliyorsa A güçlü. `oran.rasyo("ETHUSDT", "SOLUSDT")` gibi.

### 2. Flama / Diagonal = yakınsayan üçgen ⭐
Düşen üst (direnç) + yükselen alt (destek) çizgi bir **apekse** yakınsıyor.
Kırılım çoğunlukla önceki trend yönünde ("Trend devam"). Kırılım sonrası hedef:
formasyon yüksekliği kadar **ölçülü hareket** (measured move) — burada ~%25.

### 3. Fraktal bölge + ölçülü hareket hedefi
Haftalık fraktal direnç (mor) hedef; kırılımdan sonra yükseklik kadar projeksiyon.

### 4. "Manipülasyon" = alıcılı bölgeye fitil/sahte kırılım
Fiyat alıcılı bölgeye çekilip dönüş yaptı; bu, fitil toleransı/likidite
süpürme mantığıyla örtüşür (kapanış değil, fitil).

## Sisteme yansıma (yapılacaklar)
- [x] **Genel RASYO**: `oran.rasyo(a, b)` — herhangi iki Binance sembolünün
      A/B oranının göreceli gücünü hesaplar (ALT/BTC, BTC/Altın artık özel hal).
- [x] **Flama modülü** (`flama.py`): `flama_bul(df)` düşen direnç + yükselen
      destek çizgisini bulur, apeks barını ve **ölçülü hareket hedefini**
      (yukarı/aşağı) projelendirir.
- [x] **Senaryoya entegre**: plan metnine "🔻 Flama (yakınsayan üçgen)... ölçülü
      hareket ≈ X" satırı; `Senaryo.flama` alanı.
- [ ] *(opsiyonel)* Flamayı grafiğe iki çizgi + apeks olarak çizmek.

> Altın/Gümüş rasyo vakasının dersleri (genel RASYO + flama) sisteme yansıtıldı. ✅
> 53/53 test geçiyor.
