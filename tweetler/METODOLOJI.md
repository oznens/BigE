# @tradermiraz Metodolojisi — Damıtılmış Bilgi Tabanı

5.054 tweet + 7.731 chart incelenerek çıkarıldı. terminalMiraz panelimizin
@tradermiraz gibi yorum yapması için referans. Yorum motoru `src/miraz/yorum.py`
bu kuralları uygular.

## 1. Analiz iskeleti (her planın yapısı)

Her analiz şu sırayı izler:

1. **Başlık:** `COIN | <zaman dilimi> — <vade> Plan`
   (örn. "Bitcoin | Kısa Vade Plan", "BTC | 4 saatlik", "Ethereum | Uzun Vade Yeni Plan")
2. **Ana beklenti / yön:** "Ana beklenti nettir", "trend aşağı/yukarı yönlü"
3. **Bölge tanımı** (renk-kodlu kutular — aşağıdaki sözlük)
4. **Patern/yapı:** çift tepe, OBO, harmonik PRZ, Ending Channel/Takoz, MSB
5. **Yön mantığı:** "Yukarı → satış fırsatı / Aşağı → destek tepkisi"
6. **Tetik (onay):** "trend kırılımı → yeşil daire"
7. **Geçersizlik:** "X üzerinde/altında kapanışlar bu yapıyı iptal eder"
8. **R/R:** "1R Risk – 2R Reward"
9. **Disiplin mantrası**

## 2. Renk / işaret sözlüğü (chart annotasyonu)

| İşaret | Anlam |
|--------|-------|
| 🟥 Kırmızı kutu | Dağıtım / arz / çift tepe — geçersizlik genelde bunun üstü |
| 🟪 Mor kutu ("Strategy") | **Ana strateji bölgesi** — short/satış girişinin tetikleneceği alan |
| 🟦 Mavi / cyan kutu | Talep / alış bölgesi (long toplama) |
| 🟩 Yeşil daire | **Tetik/onay noktası** — trend kırılımı teyidi (bizim ENTRY) |
| ⬛ Yatay çizgi | "Direnç alanı" / "Destek alanı" |
| 〰️ El-çizimi yol | Beklenen fiyat hareketi (projeksiyon) |
| Harmonik XABCD | Gartley/Bat/Butterfly/Crab/Cypher/Shark — PRZ'de aksiyon |

## 3. Çekirdek araç seti (frekansa göre)

- **Destek/Direnç bölgeleri** (en sık) — talep/arz kutuları
- **Harmonik paternler:** Gartley, Bat, Butterfly, Crab, Cypher, Shark → PRZ'de giriş
- **Order Block (OB)** — kurumsal emir bölgesi
- **Çift tepe / çift dip** + sonrası **trend kırılımı**
- **OBO (Omuz-Baş-Omuz)** — dönüş formasyonu
- **Trend kırılımı + re-test** — kırılan seviyenin geri-testi
- **Uyumsuzluk (divergence)** — momentum zayıflaması
- **Likidite / manipülasyon** — stop avı, "her iki tarafı eleme"
- **Hacim** — "hacimli kapanış" onay şartı
- **Fibonacci:** golden pocket (0.618–0.786), uzantılar (1.618 / 2.618), "2-618 Stratejisi"
- **Fraktal / tarih tekerrürü, CME GAP, ATH, MSB, Ending Channel-Takoz**

## 4. Operasyonel kurallar (işlem yönetimi)

- **Giriş:** Patern/bölge + **trend kırılımı onayı (yeşil daire)** beklenir. Erken girilmez.
- **Onay şartı:** "X altında/üstünde **hacimli kapanış**" — fitil değil, mum kapanışı.
- **Stop:** Geçersizlik seviyesi (mor/kırmızı kutunun dışı). "Kapanış" bazlı.
- **Kar al + breakeven:** "Riskimi azaltarak kar alıp **girişe stop** koyuyorum." Kısmi kâr sonrası stop girişe çekilir.
- **R/R:** Minimum 1R:2R aranır. "Küçük risk al."
- **Kademeli:** SPOT/uzun vadede "kademeli alım", tek seferde değil.
- **Haber riski:** FED/CPI günleri "her iki tarafı eleme" — temkinli, kar al.

## 5. Vade ↔ zaman dilimi eşlemesi

| TF | Vade etiketi |
|----|--------------|
| 15m | Scalp |
| 30m | Çok Kısa Vade |
| 1h | Kısa Vade |
| 2h | Kısa-Orta Vade |
| 4h | Orta Vade |

## 6. İmza mantraları (yorum kapanışı)

- "Disiplini bozmazsan, grafik zaten sana yol gösterir."
- "Piyasa kimseye acımaz, sadece disiplinli olanı ödüllendirir."
- "Risk düşür (kar al) ve plana sadık kalmaya devam et."
- "Plan net: Yukarı → satış, Aşağı → destek tepkisi."
- "Lütfen kar almayı unutmayınız."
- "İzleyelim bakalım."
- "Kesinlikle yatırım tavsiyesi değildir; herkes kendi risk yönetimiyle hareket etmelidir."

## 7. Üslup notları

- Kısa, net cümleler; bol emoji (📍👉❗📉📈🟢🔵🟣🎯🧠🛡️⚠️).
- Koşullu kurgu: "Eğer fiyat X altında hacimli kapanış yaparsa …".
- Önce senaryo, sonra geçersizlik; her zaman bir "iptal" şartı verir.
- Duygusallığı reddeder, disiplin ve plan vurgusu yapar.
- Türkçe; ara sıra mizah ("vatana millete hayırlı olsun").
