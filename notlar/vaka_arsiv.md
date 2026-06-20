# Vaka Çalışması: Tam Arşiv Taraması — @tradermiraz (Xquik API)

> Kaynak: Xquik API ile @tradermiraz kullanıcı tweet'leri toplu çekildi.
> Erişilebilir arşiv: **823 benzersiz tweet** (3 Nis – 27 May 2026,
> yoğun analiz dönemi). 670'i grafikli orijinal analiz postu.
> (X API geçmiş derinliği ~800–3200 son tweet ile sınırlı; toplam 7.846'nın
> erişilebilen en güncel kesiti.)

## Yöntem

1. `GET /x/users/tradermiraz` → profil (ID 1204155231115853827, 7846 tweet).
2. `GET /x/users/{id}/tweets` cursor sayfalama ile arşiv JSONL'e indirildi.
3. Metinler kod ile madenlendi (kavram/terim frekansı), metodolojide
   **olmayan** kavramlar çıkarıldı.

## Metin madenciliğinden çıkan yeni kavramlar

| Terim | Geçiş | Durum |
|---|---|---|
| dominance (USDT/USDC) | 139 | beklemede (dış veri) |
| geri çekilme / retest | 58 + 2 | mevcut (fitil/bölge) |
| kademe (kademeli giriş) | 57 | kısmen (risk.py tek giriş) |
| dalga | 53 | — (Elliott değil, genel "hareket") |
| manipülasyon (sweep) | 31 | kısmen (fitil toleransı) |
| arz/talep | 45 | mevcut (kutular) |
| **çift tepe / çift dip / M formasyon** | 26 | 🔨 **bu turda eklendi** |
| dca | 11 | kısmen (kademeli) |
| OBO (omuz-baş-omuz) | birkaç | beklemede |

### Örnek tweet'ler
- **Çift tepe** (28 Nis): *"Fiyat, çift tepe yapısı sonrası trend kırılımını
  gerçekleştirmiş durumda. Bu tarz senaryo..."* → klasik dönüş formasyonu.
- **OBO** (12 Şub): *"En tepelerde bu grafiğin bir tepe yaptığını ve OBO
  yaptığını belirtmiştim."* → omuz-baş-omuz tepe.
- **Kademe** (4 Haz): *"Kırmızı ve Yeşil kutuda Kademe Kademe Bitcoin alırım."*
  (24–27 May BRENT: "Birinci kademe / İkinci kademe") → çoklu giriş.

## 🔑 Bu turda uygulanan ders: Çift Tepe / Çift Dip

Klasik dönüş formasyonu, Miraz açıkça kullanıyor:
- **Çift Tepe** (bearish): iki benzer yüksek (H-H) + aradaki boyun (L).
  Boyun altında KAPANIŞ → onay. Hedef = boyun − yükseklik.
- **Çift Dip** (bullish): iki benzer dip (L-L) + aradaki boyun (H).
  Boyun üstünde KAPANIŞ → onay. Hedef = boyun + yükseklik.

## Sisteme yansıma
- [x] **`ikili.py`**: `ikili_bul(df)` son pivotlarda H-L-H / L-H-L arar,
      benzerlik toleransı + boyun kırılım onayı + ölçülü hareket hedefi.
- [x] **Senaryoya entegre**: plan metnine "⛰️ Çift Tepe ... ONAYLANDI/onaysız"
      satırı; `Senaryo.ikili` alanı.
- [x] **Test**: `test_ikili.py` (4 test). Gerçek veride ETH/SOL günlükte
      onaylı çift tepe tespit edildi.
- [ ] *(beklemede)* OBO/TOBO, kademeli giriş (risk.py çoklu giriş),
      USDT/USDC dominance.

> Tam arşiv tarandı; en değerli yeni mekanikleştirilebilir formasyon
> (çift tepe/dip) sisteme yansıtıldı. ✅ 65/65 test geçiyor.

---

## Grafik (görsel) incelemesi

Metin madenciliğine ek olarak, arşivdeki **1.344 grafik** içinden tarih ve
varlık çeşitliliğine göre temsili bir örneklem (16 grafik) indirilip görsel
olarak incelendi (medya URL'leri tweet verisinde; ekstra API maliyeti yok).

### Doğrulanan görsel kavramlar (sistemde mevcut)
| Grafik | Gözlem | Modül |
|---|---|---|
| BTC çift tepe (28 Nis) | "Çift tepe" kutusu + "Trend kırılımı" boyun + ölçülü düşüş | `ikili.py` ✅ birebir |
| Spot Altın üçgen (27 Kas) | İki kesikli diagonal apekse yakınsıyor | `flama.py` ✅ |
| ETH Dominance (1 Mar) | "Diagonal" düşen kanal + harmonik D + kutular | `flama.py`/`kutular.py` ✅ |
| BTC/Gold OBO (15 Eki) | Harmonik + kutu + daire projeksiyon | `harmonik.py`/`grafik.py` ✅ |
| Altın (3 Mar) | Bullish harmonik + "Fraktal tepesi!" + projeksiyon oku | mevcut ✅ |

### Yeni görsel öğeler (niş — uygulanmadı)
- **Divergence + momentum osilatörü**: yalnızca **Dominance** (USDT/ETH dom.)
  makro grafiğinde görüldü; fiyat-aksiyon setuplarında yok. "İndikatör
  kullanmıyorum" ilkesine makroya özel istisna. → dominance entegre edilirse
  birlikte değerlendirilebilir.
- **"2-618 Stratejisi"**: Fibonacci 2.618 uzantı seviyesine dayalı isimli
  strateji (g05/g13'te etiket). Tekil hedef seviyesi olarak eklenebilir.

> Sonuç: Görsel söz dağarcığı sistemde mevcut. `ikili.py` ve `flama.py`,
> Miraz'ın gerçek grafik etiketleriyle ("Çift tepe", "Trend kırılımı",
> "Diagonal") birebir örtüşüyor. Eksik kalan öğeler makro/niş.
