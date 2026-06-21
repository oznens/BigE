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
| **Geniş evren (~90 parite)** | `radar.GENIS_EVREN` + `--genis` | ✅ **bu turda** |
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

## Sıradaki adımlar (yol haritası)

1. **Kısa pozisyon desteği** — Short sinyalleri portföye ekle (short senaryo motoru).
2. **Telegram/X otomasyon** — sinyal dağıtımı (opsiyonel).
3. **Hisse evreni** — terminalMiraz'ın 26 hissesi (ek veri kaynağı gerekir).

> terminalMiraz'a evrimin ilk büyük adımı (Piyasa Radar + Elenen kategorisi)
> atıldı. Sıradaki: Price Action Labs backtest motoru.
