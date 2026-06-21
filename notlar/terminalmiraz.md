# terminalMiraz'a Evrim — Mimari & Yol Haritası

> Kaynak: @tradermiraz arşivinde terminalMiraz/@terminalMiraz ile ilgili 85
> tweet. Hedef: yorumcu sistemimizi terminalMiraz tarzı tam otomatik bir
> tarama/karar/yönetim terminaline evirmek.

## terminalMiraz nedir?

Miraz'ın tek başına geliştirdiği, ~96.000 satır kodlu (eskiden 130.000) otomatik
Price Action + Harmonik trade terminali:

- **Piyasa Radar**: 92 kripto + 26 hisse = **118 enstrüman × 4 TF = 472 tarama**
  eş zamanlı, fiyatlar saniyede güncelleniyor.
- **Setup kategorileri**: Aday pozisyonlar · Yaklaşan · Aktif işlemler ·
  Emirlerde bekleyen · **Elenen Setup**.
- **HTF-LTF Kontrol**: alt + üst zaman dilimi birlikte; üst TF aşağıysa setup
  "Elenen Setup"a aktarılır.
- **Kalite Kontrol (PriceActionLab)**: her setup'a Trade/Watch/Skip + A-D kalite
  + güven (confidence) + cluster hafızası + temas davranışı.
- **Price Action Labs**: TP Lab · Giriş Lab · Stop Lab — 2020-2026 arası
  binlerce gerçek setup'ı tarayıp girişin erken/geç, stop'un dar/yapısal,
  TP'nin agresif/hızlı olması gerektiğini **veriyle** belirler.
- **Canlı yönetim**: aktif işlemler, bekleyen emirler, günlük TP/STOP, R-bazlı
  P&L (ör. Haziran: 717 TP - 484 STOP).
- **Dağıtım**: Telegram (konsept görseliyle sinyal), X otomasyonu, mobil server.

## Bizim sistem ↔ terminalMiraz eşlemesi

| terminalMiraz bileşeni | Bizdeki karşılık | Durum |
|---|---|---|
| Setup tespiti (harmonik+PA) | harmonik/kutular/trend/flama/ikili/obo | ✅ |
| Kalite kontrol (Trade/Watch/Skip + A-D) | `karar.py` | ✅ |
| HTF-LTF kontrol | `senaryo._mtf_yapi` | ✅ |
| **Piyasa Radar (çoklu tarama)** | `radar.py` | ✅ **bu turda** |
| **Elenen Setup kategorisi** | `radar._kategori_belirle` (HTF aşağı→Elenen) | ✅ **bu turda** |
| R-bazlı risk | `risk.py` | ✅ |
| Yorumcu / sinyal metni | `miraz_yorumu` + `finansaltrader_yorumu` | ✅ |
| Render (konsept görseli) | `grafik.py` (harmonik+Fib+RSI) | ✅ |
| **Price Action Labs (backtest/win-rate)** | `lab.py` | ✅ **bu turda** |
| TP/Giriş/Stop Lab (parametre taraması) | `lab.lab_tara` | ✅ **bu turda** |
| **Cluster hafızası / benzerlik** | `cluster.py` | ✅ **bu turda** |
| **Temas davranışı istatistiği** | `temas.py` | ✅ **bu turda** |
| **Aktif işlem yönetimi + canlı P&L** | `portfoy.py` | ✅ **bu turda** |
| **Karar–cluster canlı entegrasyon** | `senaryo_uret(cluster_hafiza=)` | ✅ |
| **Geniş evren (~90 parite)** | `radar.GENIS_EVREN` + `--genis` | ✅ |
| **Short (kısa) pozisyon desteği** | `kisa.py` + `radar_tara(taraf=)` | ✅ **bu turda** |
| **TP = 1R mesafe hedefi (mor kutu değil)** | `risk.mesafe_hedef` | ✅ **bu turda** |
| **Görsel terminal panosu (PNG)** | `terminal.py` + `backtest/terminal.py` | ✅ |
| **Canlı terminal panosu (4 bucket + akış)** | `dashboard.py` + `backtest/dashboard.py` | ✅ **bu turda** |
| **Intraday TF (M15/M30/H1/H2)** | `veri` 2h-resample + `radar.TERMINALMIRAZ_TF` | ✅ **bu turda** |
| **Late (geç kalmış) filtresi** | `radar._gec_kalmis` | ✅ **bu turda** |
| **Expired (giriş gelmeyen emir) filtresi** | `portfoy` max_bekleme | ✅ **bu turda** |
| **PaMonic (PA + Harmonik çakışması)** | `senaryo.pamonic` + `karar` +15 | ✅ **bu turda** |
| **3 risk modu (güvenli/dengeli/riskli)** | `radar.RISK_MODLARI` | ✅ **bu turda** |
| **Mcap'e göre dinamik evren + haftalık kontrol** | `evren.py` + `backtest/evren.py` | ✅ **bu turda** |
| **Sürekli gözlemci + Learning Journal (SQL hafıza)** | `gozlemci.py` + `backtest/gozlemci.py` | ✅ **bu turda** |
| TradeFi (26 hisse) evreni | — | ⏳ (ek veri kaynağı) |
| Telegram/X otomasyon | — | ⏳ (opsiyonel) |

## Bu turda eklenen: Piyasa Radar (`radar.py`)

```
python backtest/radar.py --tf 4h
```
- N parite × M TF tarar, her birine senaryo+karar uygular.
- Kategoriler: **Trade / Watch / Skip / Elenen** (HTF aşağı → Elenen, tam
  terminalMiraz kuralı).
- Sıralı tablo + özet ("10 tarama → 0 Trade · 5 Skip · 5 Elenen").
- Not sütunu: mavi daire, çift tepe/dip, golden pocket, hacimli geliş.

## Bu turda eklenen: Price Action Labs (`lab.py`)

```
python backtest/lab.py --sembol BTCUSDT --tf 4h
```
- Her karar barında (look-ahead yok) senaryo+risk üretir, giriş/stop/hedef alır.
- İleriye simüle eder: önce giriş dolar mı, sonra TP mi STOP mu (aynı bar →
  muhafazakâr STOP). Win-rate, toplam/beklenti R, **kaliteye göre** döküm.

### İlk bulgu (önemli)
BTC 4h, son 800 bar: genel %42 WR / -2.3R **ama kaliteye göre dramatik fark**:
- **A kalite: %81.8 WR, +11.2R** · A+: %50, +4.1R
- B/C/D: negatif (-11R / -3R / -3.5R)

→ Kalite motoru gerçekten ayrıştırıyor; yüksek kalite (A) belirgin kârlı.
Bu, Price Action Labs'in amacı: hangi setupların işe yaradığını **veriyle**
göstermek ve filtre/parametreleri ona göre ayarlamak.

## Bu turda eklenen: TP/Giriş/Stop Lab (`lab.lab_tara`)

```
python backtest/lab.py --sembol BTCUSDT ETHUSDT SOLUSDT --tara
```
Her boyutu (Giriş/Stop/TP) ayrı ayrı tarar; senaryo noktaları sembol başına
**bir kez** üretilip tüm modlar o cache'ten ucuzca denenir (47s/3 coin).

### Lab bulguları (3 coin, 800 bar) — veriyle parametre seçimi
- **TP Lab:** `ara` (mor çizgi/hızlı) ≫ `ana` (agresif uzak):
  WR %14.7 → **%40**, beklenti -0.307R → **-0.089R**. Hızlı kâr-al çok daha iyi.
- **Giriş Lab:** `ust` (bölge üstünden erken giriş) > orta > alt (-0.289 vs -0.434).
- **Stop Lab:** fitil ≈ yapısal (~-0.306), genis daha kötü.

→ **Öneri:** giriş `ust` + TP `ara` kombinasyonu varsayılandan (orta+ana) belirgin
daha iyi. (Tümü hâlâ hafif negatif; kalite filtresi `min_guven` ile A setuplara
daraltınca pozitife döner — bkz. lab.py ilk bulgu.)

## Bu turda eklenen: Portföy / Paper-Trading Motoru (`portfoy.py`)

```
python backtest/portfoy.py --ekle-radar --semboller BTCUSDT ETHUSDT SOLUSDT
python backtest/portfoy.py --guncelle
python backtest/portfoy.py
```

- Radar taramasındaki Trade sinyallerini `ekle()` ile Bekliyor listesine alır.
- `guncelle(sembol, interval, df)` her çalışmada: limit giriş dolar mı? → TP mi
  STOP mu? Aynı barda ikisi → muhafazakâr STOP (lab motoruyla tutarlı).
- Durum geçişleri: **Bekliyor → Açık → TP / STOP / Manuel**
- R-bazlı P&L: toplam R, günlük R, WR% — terminalMiraz tablo formatında.
- Kalıcılık: `portfoy.json`'a kaydedilir, sonraki çalışmada yüklenir.

## Bu turda eklenen: Cluster Hafızası (`cluster.py`)

```
python backtest/cluster.py --ogren --semboller BTCUSDT ETHUSDT SOLUSDT
python backtest/cluster.py --listele
python backtest/cluster.py --benzerlik BTCUSDT --tf 4h
```

- Her setup bir **imza** ile etiketlenir: `(kalite, mavi/düz, HTF, market
  yapısı, divergence, rr kovası)`. Aynı imzalı setuplar bir cluster'dır.
- Geçmiş veride (look-ahead yok, lab altyapısı) her setup ileri simüle edilir
  (TP/STOP), sonuç imzanın cluster'ına yazılır.
- `benzerlik(senaryo, hafiza)` güncel setup'ın cluster'ını bulur: "bu tip
  kurulum geçmişte %X TP yaptı" + güven düzeltmesi (+10..−10). Yetersiz örnekte
  kaba imzaya düşer (tam → kalite+mavi+HTF → kalite+mavi → kalite), kaba
  eşleşmede etki yarıya iner.

### İlk bulgu (3 coin, 800 bar, 170 setup)
Tek pozitif beklentili küme **A·yükseliş** (+0.02R); `düşüş` ve düşük kalite
(C/D) kümeleri belirgin negatif (−0.55 … −1.00R). Cluster hafızası kaliteyi
**imza düzeyinde** doğruluyor — düşüş yapısında long açma.

## Bu turda eklenen: Temas Davranışı (`temas.py`)

Miraz: "Bir destek ne kadar çok test edilirse o kadar zayıflar; taze ve her
seferinde sert tepki vermiş bölge en güçlüsüdür."

- `temas_analizi(df, alt, ust)` bir destek bandının geçmişini durum makinesiyle
  olaylara böler: **tepki** (reddedip üstte kapanış) · **kırılma** (alt sınır
  altı kapanış) · **içeride** (sürüyor).
- Özet: tepki oranı, son davranış, **yorgunluk** (çok test = zayıflama) ve
  güven etkisi (+12..−12). Son davranış kırılma → güçlü negatif; taze bölge →
  hafif pozitif; yüksek tepki oranı + az test → güçlü pozitif.
- **Senaryo + karar motoruna entegre:** `senaryo.temas` alanı, `karar.py`
  güven skoruna katkı, senaryo metninde tek satır özet.

### Canlı örnek
BTC 4h destek bölgesi 17 kez test edilmiş (15 tepki/2 kırılma, %88) — ama çok
yıpranmış olduğu için net güven +1; SOL bölgesi 8 olay %88 → temiz +1.

## Bu turda eklenen: Karar–Cluster Entegrasyonu (canlı)

```
python backtest/cluster.py --ogren --giris ust --tp ara   # önce öğret
python backtest/radar.py --tf 4h --cluster                # sonra uygula
```

- `senaryo_uret(df, cluster_hafiza=...)` **iki-geçişli**: önce temel karar
  üretilir (imza için kalite gerekir), sonra `cluster.benzerlik()` ile geçmiş
  başarı bulunup `karar_uret(..., ek_guven=...)` ile nihai güven düzeltilir.
- `karar.py`: `ek_guven` / `ek_gerekce` parametreleri (cluster katkısı skora
  ve gerekçe listesine girer).
- `radar_tara(..., cluster_hafiza=...)` ve `backtest/radar.py --cluster`.
- Döngüsel import (`cluster→lab→senaryo`) fonksiyon-içi import ile çözüldü.

### Önemli: öğrenme modu ayrıştırmayı belirler
Cluster `tp ana` (agresif) ile öğrenilirse tüm WR'lar düşük (~%12-24) → etki hep
−10 (ayrıştırıcı değil). Lab'ın doğruladığı `giris ust + tp ara` (hızlı kâr-al)
ile öğrenilince WR'lar **%54-87** aralığına yayılır → cluster gerçek ayrıştırıcı
olur. Canlı: BTC %59→+5, SOL %64→+5 (A→A+). cluster.json yereldir (gitignore).

## Bu turda eklenen: Evren Genişletme (terminalMiraz ölçeği)

```
python backtest/radar.py --genis --tf 4h --cluster          # 90 parite
python backtest/radar.py --genis --cluster --sadece Trade   # sadece Trade
```

- `radar.py`: **GENIS_EVREN** (90 likit MEXC USDT paritesi — majör/L1/L2/DeFi/AI/
  meme/gaming kategorileri) + CEKIRDEK_EVREN (hızlı 10). `--genis` bayrağı.
- `radar_tara(goreceli=False)`: geniş taramada göreceli güç indirmesi atlanır
  (hız). MEXC'te olmayan semboller hata listesine düşüp atlanır (graceful skip).
- **Canlı (90 parite, 4h, cluster):** 88 başarılı tarama → **18 Trade · 6 Watch ·
  37 Skip · 27 Elenen**. En güçlüler: TRX/FLOW/UNI/JUP/WLD/ENJ A+ %100 (çift dip/
  mavi daire). HTF-LTF filtresi 27 setup'ı Elenen'e attı (BTC/ETH/SOL dahil — üst
  TF aşağı). Bozuk 4 sembol (TON/MKR/AKT/THETA) IOTA/CAKE/RAY/KAVA ile değişti.

## Bu turda eklenen: Short (Kısa) Pozisyon Desteği

```
python backtest/radar.py --taraf her --tf 4h --cluster        # long + short
python backtest/portfoy.py --ekle-radar --taraf short         # short yönet
```

Sistem artık iki yönlü — long'un tam aynası:
- **`kisa.py`** (`kisa_senaryo`): long senaryosunu yeniden yorumlar — üstteki
  ana direnç = short GİRİŞ bölgesi, alttaki destek = short HEDEF. Bearish
  skorlama (`_short_karar`): market yapısı düşüş +12, bearish divergence +10,
  çift tepe +12, OBO +10, RSI≥70 +8; MTF **tersine** (HTF aşağı = short lehine).
- **`portfoy.py`**: yön-duyarlı takip — Short'ta giriş high≥giriş'te dolar,
  STOP high≥stop (yukarıda), TP low≤hedef (aşağıda); canlı P&L yöne göre.
- **`radar_tara(taraf=)`**: long/short/her. Short için HTF **yukarı** → Elenen.

### Canlı (çekirdek 10, taraf=her): piyasa hikayesi tutarlı
HTF aşağı olduğu için **long'lar Skip/Elenen, short'lar A+ Trade**: DOT/DOGE/LINK
short A+ (çift tepe/obo). DOT aynı anda short-Trade A+ ve long-Skip D → ayna
tutarlı. Short sinyaller portföye yön=Short, stop girişin üstünde eklendi.

## Bu turda eklenen: Short Cluster/Lab Doğrulaması

```
python backtest/lab.py --sembol BTCUSDT ETHUSDT SOLUSDT --tf 4h --kisa
python backtest/cluster.py --ogren --giris ust --tp ara --yon short --semboller BTCUSDT ETHUSDT SOLUSDT BNBUSDT XRPUSDT
```

Short tarafı artık tam çift yönlü lab + cluster altyapısına sahip:
- **`_simule(yon="short")`**: giriş `high≥giriş`, STOP `high≥stop`, TP `low≤hedef` —
  long ile aynı mantık, yön tersine çevrilmiş.
- **`_kisa_noktalari`** / **`_kur_kisa`** / **`backtest_kisa`**: look-ahead yok;
  her karar barında `kisa_senaryo()` çağırır, geçerli direnç bölgesini giriş,
  fitil seviyesini stop, ara hedefi TP olarak kullanır.
- **`cluster_ogren(yon="short")`** / **`backtest/cluster.py --yon short`**:
  short imzalar ayrı öğrenilir (long cluster'ı bozmaz).
- **166 test geçiyor** — short `_simule`, `_kur_kisa` mod/geçerlilik testleri dahil.

### Short backtest ilk bulgular (3 coin, 4h, 500 gün)
BTC/ETH/SOL genel: **%34.2 WR / -19.6R** — beklenebilir; boğa döneminde short
setuplarda TP hedefleri uzak kalıyor. Kalite sıralaması uzun yönden **tersine** çıktı
(D'ler daha yüksek WR) → short karar motorunun gelecekte iyileştirilmesi gerektiğini
veriyle kanıtlıyor.

### Short cluster ilk bulgular (5 coin, 500 gün, 116 setup)
Cluster belleği çalışıyor ve imzaları ayrıştırıyor:
- `D·düz·nötr·yükseliş·yok·rr<1.5` → **%81.8 WR** (+0.23R beklenti) — kısa hedefli düz
  short'lar boğa tepkilerinde çok sık hedge fırsatı buluyor
- `D·düz·nötr·yükseliş·yok·rr1.5-2.5` → %12.5 WR (−0.68R) — hedef uzadı, başarı düşüyor
- `A+·düz·nötr·düşüş·yok·rr≥2.5` → **%0 WR** (−1.00R) — yüksek RR short setuplarda bile
  piyasa dip yapıyor; long yönlü küre sinyali

→ Cluster, short tarafında da uyarıcı sinyaller üretiyor; karar motoruna entegre
edilince A+ short setuplarda güven −10 baskısı uygulanacak.

## Bu turda eklenen: TP = 1R Mesafe Hedefi (mor kutu kaldırıldı)

terminalMiraz görselleri incelendi — TP'yi **yapısal mor kutu/mor çizgi değil**,
girişe STOP mesafesi kadar simetrik uzaklığa koyuyor:
- **Deep Crab TAOUSDT (short):** SL 243.295 · ENTRY 233.069 · TP 222.843 →
  entry↔SL = entry↔TP = 10.226 → **R/R = 1R** (kartta yazılı)
- **Dashboard HBAR (long):** Entry 0.0865 · SL 0.0853 · TP 0.0878 → ~1.01R
- **Dashboard ALGO (short):** Entry 0.1174 · SL 0.1205 · TP 0.1143 → ~1.00R

→ `risk.mesafe_hedef(giris, stop, rr=1.0)`: hedef = giriş ± rr·|giriş−stop|.
`risk_plani` / `kademeli_plan` / radar short / lab (`tp_mod="rr"`, varsayılan) hepsi
artık 1R mesafe hedefi kullanıyor. `rr_hedef` parametresiyle çarpan ayarlanabilir;
yapısal hedefler (`ara`/`ana`) Lab karşılaştırması için duruyor.

## Bu turda eklenen: Görsel Terminal Panosu (`terminal.py`)

```
python backtest/terminal.py --semboller BTCUSDT ETHUSDT SOLUSDT --tf 4h --taraf her
python backtest/terminal.py --genis --cluster --taraf her    # 90 parite panosu
python backtest/terminal.py --portfoy                         # portföyü panoda göster
```

@tradermiraz'ın terminalMiraz arayüzünün **birebir koyu temalı kopyası** (PNG):
- **Başlık + günlük özet şeridi:** tarama sayısı · Aday/İzle/Atla/Elenen.
- **Üst komuta metrikleri:** SCANNER / FILTERED / SKIP / ELENEN kutuları
  (terminalMiraz'ın Scanner/Filtered/Harmonik/Late Result kartları).
- **Sağ büyük sayaçlar:** AKTİF · SONUÇ · bugün TP/STOP/R (portföyden).
- **CANLI ADAY AKIŞI:** her setup bir kart — kalite **skor donut'u**, sembol/TF,
  ▲Long/▼Short rozeti, kategori, not, R/R ve **SL—ENTRY—TP kaydırıcısı** (Deep
  Crab kartının aynısı).
- **SONUÇ BİLDİRİMLERİ:** portföy varsa kapanan/aktif pozisyonlar, yoksa radar
  Aday/İzle sinyalleri.

`panel_ciz(rapor, portfoy=None, dosya=...)` → PNG. Çıktı `data/terminal.png`.

## Bu turda eklenen: Harmonik — Short tarafı + Kart Pattern Adı

terminalMiraz kartları harmonik pattern adını ön planda gösterir (Gartley+,
Deep Crab...). İki eksik kapatıldı:

- **Short bearish harmonik** (`kisa._bearish_harmonik_bul`): long'un "mavi
  daire"sinin aynası — **bearish harmonik D ∩ direnç** = en yüksek güvenli short.
  `kisa_senaryo` bunu tarar, `_short_karar` +12 güven verir, metinde 🟣 satırı
  gösterir. Canlı: BNBUSDT 4h dirençte **AB=CD** yakaladı → A kalite Trade.
- **Kart/tablo pattern adı:** `RadarSatiri.pattern` (long `mavi_daire_isim`,
  short `harmonik_isim`). Radar notu artık "Gartley D" / "AB=CD D" yazıyor;
  terminal kartında sembol altında **mor renkte pattern adı** (`4h · AB=CD`) —
  birebir terminalMiraz görünümü.

Böylece harmonik motoru (8 pattern: Gartley/Bat/Butterfly/Crab/Deep Crab/AB=CD/
Shark/Cypher) artık **hem long hem short** akışında ve panoda görünür.

**Short giriş = harmonik D (PRZ).** terminalMiraz entry'yi harmonik D noktasına
koyar. Long zaten `mavi_daire`'yi giriş yapıyordu; short da artık simetrik:
`KisaSenaryo.giris` = harmonik D varsa orası (stop'un altında & hedefin üstünde
geçerliyse), yoksa direnç bandı alt kenarı. Radar/lab/kart slider'ı bu net girişi
kullanır. Canlı: BNB short girişi band kenarı (629.6) yerine **D=632.94**'e çekildi.

## Bu turda eklenen: Tweet analizi sonrası 5 metodoloji uyumu

@tradermiraz'ın terminalMiraz tweetlerini (Xquik ile çekildi) okuyup 5 fark
kapatıldı:

1. **Intraday zaman dilimleri (M15/M30/H1/H2).** Tweet: *"yaklaşık 75 parite;
   M15, M30, H1 ve H2 zaman dilimlerinde taranıyor"*. MEXC 2h sunmadığı için
   `veri.py` 1h→2h **resample** ediyor (`_TUREV`). `radar.TERMINALMIRAZ_TF` +
   tüm CLI'larda `--mtf` bayrağı. HTF eşlemesi: 15m→1h, 30m→2h, 1h→4h, 2h→4h.
2. **Late (geç kalmış) filtresi.** Tweet: *"Geç kalmış setuplarda 12 setup
   filtrelendi, 9 stop'tan korunuldu"*. `_gec_kalmis`: fiyat giriş→hedef
   yolunun ≥%50'sini katettiyse Trade/Watch → **Elenen** ("Late"). Hareketin
   çoğu gittiyse kovalamayı engeller.
3. **Expired filtresi.** Bekliyor bir limit emir `max_bekleme` (vars. 24) bar
   içinde dolmazsa → **Expired** (`portfoy.guncelle`). Giriş gelmeyen emirler
   otomatik iptal.
4. **PaMonic (Price Action + Harmonic).** Tweet: *"Harmoniklerin D bölgesinde
   neden Price Action aramıyoruz? Gartley D'de OrderBlock..."*. `senaryo.pamonic`
   = harmonik D, **güçlü** bir PA destek kutusuyla (güç≥70, harmonik kalite≥60)
   çakışınca True → karar motoruna **+15 güven**, kartta 🔷 PaMonic rozeti.
5. **3 risk modu.** Tweet: *"Aşırı Güvenli / Dengeli / Tamamen Riskli... şu an
   1:1 RR"*. `RISK_MODLARI` = güvenli 1R · dengeli 1.5R · riskli 2R; tüm
   CLI'larda `--risk-mod`. `mesafe_hedef(rr_hedef)` ve short hedefi buna uyar.

Ayrıca tweet verileri: terminalMiraz **92 parite + 26 hisse = 118 enstrüman ×
4 TF = 472 tarama**; 2 aylık 590 TP/430 STOP (~%58 WR); R=25$ (test 10$).
Hisse (TradeFi) evreni bizde henüz yok (ek veri kaynağı gerekir).

## Bu turda eklenen: Mcap Evreni — Dinamik Parite Seçimi (`evren.py`)

terminalMiraz pariteleri **piyasa değerine (mcap) göre** seçer ve düzenli
(haftalık) "bu coin hâlâ listede mi?" kontrolü yapar; mcap'i düşeni atar,
yükseleni ekler.

```
python backtest/evren.py --guncelle --n 90    # haftalık: taze liste + değişim
python backtest/evren.py --listele            # mcap sıralı liste
python backtest/radar.py --mcap --mtf         # mcap evrenini tara
python backtest/terminal.py --mcap --taraf her
```

- **Kaynak:** CoinGecko (mcap sırası) ∩ MEXC (spot USDT paritesi olanlar).
- **Eleme:** stablecoin (USDT/USDC/DAI...), wrapped/staked türevleri (WBTC/
  stETH...), ASCII olmayan junk semboller (ör. `币安人生`) regex ile elenir.
- **Değişim raporu:** önceki `data/evren.json` ile karşılaştırıp **eklenen /
  çıkan** pariteleri yazar (haftalık kontrol). Canlı: ilk 90 → BTC#1, ETH#2,
  BNB#4 (USDT#3, USDC#5 stablecoin atlandı).
- `radar.py --mcap` ve `terminal.py --mcap` bu evreni kullanır (data/evren.json
  yereldir, gitignore).

## Bu turda eklenen: Canlı Gözlemci + Learning Journal (`gozlemci.py`)

terminalMiraz'ın asıl çalışma şekli: evreni **sürekli tarar**, bulduğu her setup'ı
bir **Learning Journal**'a (SQL hafıza) kaydeder, yaşam döngüsünü izler ve canlı
P&L tutar (tweet: "her 3 dakikada setup", "Journal & SQL tarafı karakterini
oluşturdu").

```
# Tek tur (tara → kaydet → takip et)
python backtest/gozlemci.py --bir --mcap --mtf --taraf her --cluster

# Sürekli (terminalMiraz modu — her 180 sn tarar, kendi makinende)
python backtest/gozlemci.py --surekli --aralik 180 --mcap --mtf --taraf her --pano

# Defter & portföy durumu
python backtest/gozlemci.py --durum
```

Her döngü: `radar_tara` → Trade sinyalleri **portföye (paper-trading) + deftere**
işlenir → açık/bekleyen pozisyonlar taze veriyle güncellenir (TP/STOP/Expired) →
defter kayıtları portföyden senkronize edilir → her şey diske yazılır.

- **`Defter` (Learning Journal):** her Trade setup'ı `Kayit` olarak tutar
  (sembol/TF/taraf/kalite/giriş/stop/hedef/pattern + durum). Aynı setup aktifken
  tekrar yazılmaz (dedup). Durum: **Aday → Açık → TP/STOP/Expired/Manuel**.
  `defter.json`'a kümülatif tarama sayısı + zaman damgasıyla kalıcı.
- **Canlı özet (her döngü):** "🔭 TARAMA #N | Aday/İzle/Atla/Elenen · ➕ yeni
  Trade · ✅/🔴 kapananlar · 📓 Defter WR · 💰 Portföy R" — terminalMiraz nabzı.
- `--pano` ile her döngüde `terminal.png` panosu yenilenir. Önceki durum yüklenip
  kaldığı yerden sürer. (defter.json/portfoy.json yereldir, gitignore.)

## Bu turda eklenen: Canlı Terminal Panosu (`dashboard.py`)

terminalMiraz **terminal üzerinden kullanılıyor**: "TerminalMiraz Mobile"
ekranında üstte **4 result bucket** (SCANNER / FILTERED / HARMONIK / LATE —
her biri kendi kümülatif TP/STOP/WR'siyle), solda **CANLI ADAY AKIŞI**
kartları, sağda **SONUÇ BİLDİRİMLERİ** (kapanan trade'ler Entry/SL/TP +
sonuç). `terminal.png` statik PNG'ydi; bu modül aynı düzeni **canlı terminal
ekranı** olarak (`rich`) çizer — gözlemci döngüsüne bağlı, kendini yeniler.

```
# Tek tur (tara → kaydet → panoyu bas)
python backtest/dashboard.py --bir --mcap --mtf --taraf her --cluster

# Sürekli mod (terminalMiraz ekranı — her 180 sn yeniler)
python backtest/dashboard.py --surekli --aralik 180 --mcap --mtf --taraf her

# Defter & bucket performans durumu (tarama yapmaz)
python backtest/dashboard.py --durum
```

- **4 bucket = kaynak etiketi:** her setup taranırken bir `kaynak` alır —
  **Harmonic** (harmonik D'li Trade), **Scanner** (saf PA Trade), **Filtered**
  (Watch), **Late** (geç-kalmış elenen). `RadarSatiri.kaynak` → `Kayit.kaynak`
  taşınır; `Defter.ozet()["buckets"]` her bucket'ın kapalı TP/STOP/WR'sini ayrı
  hesaplar. Böylece "hangi kaynak daha iyi çalışıyor?" canlı görünür
  (tweet: SCANNER %87.5, HARMONIK %66.7, LATE %25 gibi).
- **CANLI ADAY AKIŞI:** Trade/Watch kartları — ok (▲/▼) + sembol/TF + kategori
  rozeti, `kaynak | pattern | yön`, `Entry / SL / TP / R/R`. terminalMiraz'ın
  "Scanner | Harmonic Gartley+ | Bullish" kart satırının birebir karşılığı.
- **SONUÇ BİLDİRİMLERİ:** defterdeki son kapanan kayıtlar (Entry/SL/TP + `±R`
  + zaman) — terminalMiraz'ın sağ "SONUC BILDIRIMLERI" sütunu.
- Eski `defter.json` (kaynaksız) geriye dönük uyumlu: `kaynak` yoksa Price Action.

## Tweet+ekran arşivi derin inceleme (Xquik, Haziran 2026)

@tradermiraz + @terminalMiraz tweet'leri ve 5 terminal ekranı tek tek
incelendi. **@terminalMiraz ayrı bir bot hesabı** (builder), kendi setup
tweet'lerini atıyor ("terminalMiraz | SEMBOL TF" + Harmonik/PA + D bölgesi).
Netleşen mimari aşağıya işlendi; kodu buna göre hizaladık.

### İki ayrı terminal ekranı (tweet görselleri)

1. **TERMINALMIRAZ PRO — Binance Execution Dashboard** (icra ekranı):
   sol menü *Dashboard / Trade / Pozisyonlar / Geçmiş / Cüzdan / PNL / Sistem
   Günlüğü / API / Risk*; üst durum çubuğu *Testnet Active · Binance Connected
   · **Kiraz Online** · **SQL Memory Online***; metrik satırı *Account Equity
   (W) · Available Balance (A) · Active Positions (P) · Pending Orders (O) ·
   Daily PNL (D)*; *Execution Overview* (Testnet/Isolated/One-way/Order Engine
   Ready); *Recent Execution Activity* (Entry filled→**OPEN**, Stop loss→
   **STOP**, Manual close→**MANUAL**, Blocked→**BLOCK**); *Kiraz Execution
   Verdict* → **WATCHLIST MODE**.
2. **PERFORMANCE INTELLIGENCE — Live Setup Result Memory** (sonuç hafızası):
   BUGÜN/DÜN/TÜM GEÇMİŞ WR donut'ları, **RESULT JOURNAL** bucket'ları, *Engine
   Quality Heatmap*, *Month Result Distribution*, *TradeFi PA Performance Curve*.

### Kiraz = ayrı karar/icra motoru

**Miraz** setup'ı *bulur*; **Kiraz** *onaylar/risk yönetir/emir açar* (tweet:
"Kiraz karar motoru"). Kiraz Status: WATCHLIST MODE (sadece izle) ↔ Execution
Mode. Risk standardı **R = 25$ (last 10$)**, Binance **TestFutures** 5000$.

### Gerçek RESULT JOURNAL kategorileri (ekran t3 + tweet [14])

Strateji motorları (her biri ayrı WR): **Price Action · Harmonik · Late ·
TradeFi PA · TradeFi Harmonik**. (Bizde TradeFi=hisse verisi yok → 0.)

Lifecycle/eleme durumları (Setup → filtre hattı, tweet "Bu gördüğünüz ekran"):
**Rafakalkan/Shelved · Expired · Cancelled · Late · No-Entry (Entry Olmadı)**.
Tespit edilen her SETUP bu hattan geçer; geçenler **Kalite Motoru**'na
(6-7 yıllık birikim) girer; setup bulununca **bildirim sesi**. Filtrelenen
setup'lar entry'ye kadar **sürekli yeniden sınanır**; şart sağlarsa "Filtreli"
etiketi kalkar, listeye geri döner (tweet [7] "mülakata defalarca girmek").

Mayıs özeti (tweet [14]): 862 üretildi · 190 Late · 45 filtre · 18 rafa · 15
iptal · 177 No-Entry (0:0) · +39R net. Genel: 2.678 sonuçlanan, %59.7 WR.

### Tüm terminal ekranları tek tek incelendi (152 görsel → ~13 UI ekranı)

@tradermiraz'ın attığı **bütün** terminalMiraz görselleri çekildi (152 benzersiz
görsel; ~13'ü gerçek terminal UI, gerisi trade grafiği/AI görsel). Modül haritası:

**Ana uygulama üst menüsü:** `LAB · BACKTEST · SCANNER · MEMORY · SETUP`
(slogan: *KNOWLEDGE INTO ACTION*). Ortada **CANLI GRAFİK** — "Execution-grade
candle stream": mum akışı + ZONE kutusu + SQL Memory çizgisi + SL + MACD +
İŞLEM ÖZETİ (Aday rozeti).

**Execution (Binance) sol menüsü:** Dashboard · Trade · Pozisyonlar · Geçmiş ·
Cüzdan · PNL · Sistem Günlüğü · API · Risk. Keşfedilen ekranlar:

1. **Dashboard** — 6 metrik: Wallet Balance · Available Balance · Active
   Positions · Pending Orders · Daily PNL · **Open Risk %** (günlük risk
   limitine göre). Recent Execution Activity: **FILLED / BLOCK** (Kiraz risk
   filtresi bloklar). **KIRAZ STATUS: WATCHLIST MODE** — *"Aktif setup var
   ancak risk filtresi nedeniyle otomatik emir beklemede."*
2. **PNL ANALYTICS** — Net/Closed/Open PNL · Win Rate · **Profit Factor 2.55** ·
   Total Trades · TP/STOP/Cancelled Count · **Performance Curve** (Equity/
   Balance/Growth, Today→All Time) · **Concept/Pair/Timeframe Performance**.
3. **Geçmiş (Trade History)** — Total/TP/SL/Cancelled/WR · **Best Day / Worst
   Day** · Trade Timeline ("Hedef alındı"/"Zarar kesildi"/"Manuel kazanç") ·
   Concept Performance Snapshot · **Trade Memory Summary** (Most Profitable/Used
   Concept, Most Traded Pair, Highest RR=**1R**, Longest Trade, Best Month).
4. **MEMORY** — Parite Hafıza Şeridi (parite başına skor + Stop riski) · **Konsept
   Katmanları** (kod adlı PA konseptleri: VOID/Absorb/Ask/Cavity/Root/Fault…,
   her biri TP/STOP) · MEMORY FLOW takvimi (günlük TP/STOP) · Zaman Dilimi
   Karakteri (konsept hangi TF'de daha sağlıklı). = *Price/Harmonic Memory Lab*.

Harmonik konseptler gerçek isimlerle: **Harmonic Shark / Cypher / Gartley /
Butterfly / Deep Crab**. Highest RR = 1R → TP=1R doğrulandı (yine).

### Koda yansıttıklarımız (bu inceleme sonrası)

- **`kaynak` etiketleri gerçek isimlere çevrildi:** `Scanner` → **Price Action**;
  `Harmonik`, `Late` korunur. Bucket WR'leri Price Action / Harmonik / Late.
- **Lifecycle sayaçları:** `Defter.ozet()` artık No-Entry / Cancelled / Shelved /
  Expired / Filtered'ı ayrı sayar (RESULT JOURNAL satırı).
- **Dashboard execution başlığı:** durum çubuğu (Kiraz / SQL Memory) + Wallet
  Balance / Aktif Pozisyon / Bekleyen Emir / Günlük PNL / **Open Risk %** +
  **KIRAZ STATUS** (gerçek WATCHLIST/EXECUTION semantiğiyle).
- **PNL ANALYTICS ekranı (`--pnl`):** `Defter.pnl_analitik()` → Net/Open PNL,
  **Profit Factor**, Win Rate, En İyi/Kötü Gün, **Parite / TF / Konsept
  performans tabloları**. terminalMiraz PNL modülünün birebir karşılığı.

## Bu turda eklenen: Web Sunucu — tarayıcıdan açılan pano (`sunucu.py`)

@tradermiraz terminalMiraz'ı **CMD ekranında değil**, bir sunucuda çalışan
**web uygulaması** olarak tutuyor; kendi bilgisayarından tarayıcıyla girip
izliyor (ekran görüntüleri zaten tarayıcı/masaüstü GUI). Bizimkini de aynı
şekle getirdik: `rich` CMD panosunun yanına gerçek bir **web sunucu** eklendi.

```
# Sunucuyu başlat (arka planda sürekli tarar)
python backtest/sunucu.py --mcap --mtf --taraf her
# → tarayıcıda http://localhost:8000

# Özel port / aralık
python backtest/sunucu.py --port 8080 --aralik 120 --mcap --mtf --taraf her

# Aynı ağdaki telefondan da bak (güvenlik yok, dikkat)
python backtest/sunucu.py --host 0.0.0.0 --port 8000 --mcap --mtf
```

- **Mimari:** `Sunucu` arka planda bir iş parçacığında Gözlemci döngüsünü her
  `--aralik` sn çalıştırır; sonucu `durum_json()` ile JSON'a çevirip kilitli bir
  `DurumDeposu`'ya yazar. Yerleşik `http.server` `/` adresinde koyu temalı
  paneli (`web/index.html`), `/api/durum`'da canlı JSON'u sunar. Tarayıcı 4
  sn'de bir JSON'u çekip paneli tazeler. **Ek bağımlılık yok** (stdlib).
- **Panel sekmeleri:** **DASHBOARD** (durum çubuğu + Binance Execution metrikleri
  + KIRAZ STATUS + Result Journal bucket/lifecycle + CANLI ADAY AKIŞI kartları +
  SONUÇ BİLDİRİMLERİ), **PNL ANALYTICS** (Net PNL / Profit Factor / WR / en
  iyi-kötü gün + parite/TF/konsept tabloları), **MEMORY** (konsept katmanları +
  parite hafıza şeridi + zaman dilimi karakteri).
- Önceki `defter.json`/`portfoy.json` durumundan sürer; her tarama diske yazar.
- Aday kartları terminalMiraz'ın skor donut'u + SL—ENTRY—TP + Long/Short rozeti
  düzenini birebir taklit eder (CSS conic-gradient donut).

## Bu turda eklenen: CANLI GRAFİK + Binance Testnet (Kiraz execution)

terminalMiraz'ın ana terminalindeki **CANLI GRAFİK** ("Execution-grade candle
stream") ve **Binance Testnet bağlantısı** ("Testnet Active · Binance
Connected") web paneline eklendi.

**CANLI GRAFİK** (`sunucu.grafik_veri` + `/api/grafik` + canvas):
- Mum akışı (yeşil/kırmızı), **ZONE** kutusu (taze senaryodan destek bölgesi),
  **ENTRY / SL / TP** çizgileri, **SQL Memory** etiketi, **MACD** alt paneli.
- Aday/bildirim kartına tıkla → o sembolün grafiği yüklenir; ilk aday otomatik.

**Binance Testnet** (`borsa.py` + `kiraz.py`):
- `BinanceTestnet` — USDT-M Futures **testnet** istemcisi (imzalı HMAC-SHA256).
  Anahtarlar yalnızca ortam değişkeninden (`BINANCE_TESTNET_KEY/SECRET`), asla
  kodda/log'da. Sadece testnet (gerçek para yok).
- `kiraz.py` — **Kiraz** execution motoru: R bazlı pozisyon boyutu
  (`pozisyon_miktari`), **bracket emir** planı (giriş LIMIT + SL STOP_MARKET +
  TP TAKE_PROFIT_MARKET). `KirazMotor.uygula(plan, kuru=True)` varsayılan
  **dry-run**; `kuru=False` ile testnet'e gönderir.
- Web sunucu `--borsa` ile execution metriklerini gerçek testnet hesabından
  okur (Binance Connected rozeti); `--otomatik` (opt-in, sadece --borsa ile)
  yeni Trade adaylarına testnet bracket emri açar (çift gönderim önlemeli).
- CLI: `python backtest/borsa.py --hesap | --plan ... | --test-emir ... --onayla`

```
# Testnet anahtarını tanımla (testnet.binancefuture.com → API Key)
export BINANCE_TESTNET_KEY=...   ;  export BINANCE_TESTNET_SECRET=...

# Canlı testnet metrikleriyle pano
python backtest/sunucu.py --mcap --mtf --taraf her --borsa

# (DİKKAT) Kiraz otomatik testnet emri açsın (sahte para)
python backtest/sunucu.py --mcap --mtf --taraf her --borsa --otomatik
```

## Bu turda eklenen: Veri kaynağı → MEXC Futures (terminalMiraz pariteleri)

terminalMiraz **USDT-M Futures** üzerinde çalışıyor. Veri kaynağı MEXC **spot**
klines'tan MEXC **futures** (contract) klines'a çevrildi; spot yedek kaldı.

- `veri.py`: `_mexc_futures_cek` — `contract.mexc.com/api/v1/contract/kline/
  {BTC_USDT}` (sembol `BTCUSDT→BTC_USDT`, TF enum `Min60/Hour4/…`, start/end
  **saniye**, **dizi** yanıt → 8-kolon satır). Kaynak sırası: **futures →
  spot**. `indir(borsa="mexc-futures"|"mexc-spot")` ile zorlanabilir.
- `evren.py`: `_mexc_usdt()` artık önce futures kontratlarını
  (`contract/detail`, `BTC_USDT→BTCUSDT`) dener, sonra spot'a düşer — evren
  gerçekten futures'ta işlem gören paritelerden oluşur.
- Neden: bazı bölgelerde (ör. TR) MEXC **spot** kısıtlı olabilir → tarama hiç
  veri çekemiyordu; futures erişilebilir. (Sandbox'ta tam tersi: spot 200,
  futures 403 — bu yüzden çift kaynak + yedek.)
- Web grafik: aday yokken bile boş kalmasın diye snapshot'a `varsayilan_grafik`
  (ilk taranan sembol) eklendi; ilk scan yavaşken bile grafik bir şey gösterir.

## Bu turda eklenen: Rate-limit dayanıklılık + bayat bölge filtresi

- **Rate-limit retry** (`veri._get`): 429/418/5xx → `Retry-After` kadar backoff,
  4 deneme. 90 parite × 4 TF taramada MEXC limitine takılmayı önler.
- **max_bar sınırı** (`veri.indir(max_bar=)`): pencereyi en çok N mumla
  sınırlar. Web sunucu canlı taramada **900 mum** kullanır → intraday TF'lerde
  (15m/30m) 120 gün yerine ~9 gün indirir, ilk tarama çok hızlanır. radar_tara
  / Gözlemci üzerinden geçer; backtest'te varsayılan None (tam geçmiş).
- **Bayat bölge filtresi** (`radar._hedef_zaten_gorundu`): @tradermiraz'ın
  bizzat anlattığı hata — "Short bölgesi çoktan çiğnenmiş olmasına rağmen
  tarama hâlâ aktif setup listeliyor; oysa bölge artık direnç değil destek".
  Hedef yakın geçmişte (son 40 mum) zaten görülmüşse (short: düşük ≤ hedef,
  long: yüksek ≥ hedef) hareket olmuş demektir → setup **Elenen** ("bölge
  çiğnenmiş (hedef zaten görüldü)"). Late filtresinin tamamlayıcısı.

## Sıradaki adımlar (yol haritası)

1. **Telegram/X otomasyon** — sinyal dağıtımı (opsiyonel).
2. **Hisse evreni** — terminalMiraz'ın 26 hissesi (ek veri kaynağı gerekir).
3. **Short karar motoru iyileştirme** — cluster bulgularına göre `kisa.py`
   skorlarını kalibre et (RR≥2.5 short için ek ceza, boğa HTF'de zayıflatma).

> Sistem şu an terminalMiraz'ın temel bileşenlerinin tamamını karşılıyor;
> hem statik PNG panosu (`terminal.py`) hem de **canlı terminal ekranı**
> (`dashboard.py`) ile terminalMiraz gibi terminalden kullanılıyor.
> 203 test · ~90 parite · iki yönlü lab + cluster hafızası + Learning Journal.
