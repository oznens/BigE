# @tradermiraz Tweet & Chart Arşivi

Bu dizin [@tradermiraz](https://x.com/tradermiraz)'ın tweetlerini ve chart
görsellerini içerir — terminalMiraz sistemini birebir kurmak ve PA/harmonik
yaklaşımını referans almak için. Xquik API ile çekildi (yalnızca herkese açık
veriler).

## İçerik

| Dosya | Açıklama |
|-------|----------|
| `tweetler.json` | Tüm tweet objeleri: metin, tarih, etkileşim (like/RT/view), medya URL'leri, yanıt/alıntı bilgisi |
| `tweet_gorsel.json` | tweetId → indirilen görsel dosya adları eşlemesi |
| `gorseller/` | Chart görselleri (pbs.twimg.com CDN'den, orijinal kalite) |

## Mevcut kapsam (1. parti)

- **833 tweet** · **753 medyalı** · **1437 benzersiz chart**
- Tarih aralığı: **2025-12-07 → 2026-06-22** (en güncel ~6.5 ay)

> Not: X kullanıcı-zaman-tüneli endpoint'i ~833 tweette pencereleniyor. Daha eski
> geçmiş (2019'a kadar, toplam ~7.849 tweet / ~4.989 medya) tarih-pencereli
> arama extraction'ı ile ayrıca eklenecek.

## tweetler.json şeması (tweet başına ana alanlar)

- `id`, `text`, `createdAt`, `lang`, `url`
- `media[]`: `{ media_url_https, type: photo|video, url }`
- `likeCount`, `retweetCount`, `replyCount`, `quoteCount`, `viewCount`, `bookmarkCount`
- `isReply`, `isQuoteStatus`, `conversationId`, `quoted_tweet`
