# @tradermiraz Tweet & Chart Arşivi

Bu dizin [@tradermiraz](https://x.com/tradermiraz)'ın tweetlerini ve chart
görsellerini içerir — terminalMiraz sistemini birebir kurmak ve PA/harmonik
yaklaşımını referans almak için. Xquik API ile çekildi (yalnızca herkese açık
veriler).

## İçerik

| Dosya | Açıklama |
|-------|----------|
| `tweetler.json` | Tüm tweet objeleri (tarihe göre yeni→eski): metin, tarih, etkileşim, medya URL'leri, yanıt/alıntı bilgisi |
| `tweet_gorsel.json` | tweetId → indirilen görsel dosya adları eşlemesi |
| `gorseller/` | Chart görselleri (pbs.twimg.com CDN'den, orijinal kalite) |

## Kapsam

- **5.054 tweet** · **4.045 medyalı** · **7.731 chart görseli**
- Tarih aralığı: **2021-06-19 → 2026-06-22** (~5 yıl)

> Not: X arama indeksi bu hesap için ~2021-06'dan eskisini döndürmüyor; hesabın
> 2019-2021 arası en eski tweetleri X tarafında erişime kapalı. Elde edilebilir
> tüm geçmiş çekildi.

İki kaynaktan birleştirildi (id'ye göre tekilleştirildi):
- En güncel ~6.5 ay: kullanıcı zaman-tüneli endpoint'i (metin+medya tek geçişte)
- 2021-06 → 2025-12: tarih-pencereli arama extraction'ı + batch tweet lookup ile medya

## tweetler.json şeması (tweet başına ana alanlar)

- `id`, `text`, `createdAt`, `lang`, `url`
- `media[]`: `{ media_url_https, type: photo|video, url }`
- `likeCount`, `retweetCount`, `replyCount`, `quoteCount`, `viewCount`, `bookmarkCount`
- `isReply`, `inReplyToUsername`, `isQuoteStatus`, `conversationId`, `quoted_tweet`

## Kullanım fikri

`tweetler.json` + `gorseller/` ile @tradermiraz'ın setup mantığı (harmonik PRZ,
PA konseptleri, çift tepe/OBO, golden pocket vb.) örnek chart'lar üzerinden
incelenebilir; terminalMiraz panelimizin kararlarıyla karşılaştırılabilir.
