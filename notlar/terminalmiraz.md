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
| **Price Action Labs (TP/Giriş/Stop)** | — | ⏳ backtest motoru |
| **Cluster hafızası / benzerlik** | — | ⏳ |
| **Temas davranışı istatistiği** | — | ⏳ |
| **Aktif işlem yönetimi + canlı P&L** | — | ⏳ paper-trading motoru |
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

## Sıradaki adımlar (yol haritası)

1. **Price Action Labs (backtest motoru)** ⭐ — geçmiş setupların TP/giriş/stop
   davranışını ölçüp parametreleri veriyle ayarlamak. terminalMiraz'ın kalbi.
2. **Aktif işlem yönetimi (paper-trading)** — Trade kararlarını sanal portföyde
   açıp TP/STOP takibi, R-bazlı P&L, günlük istatistik.
3. **Cluster hafızası** — güncel setup'ı geçmiş benzerlerle karşılaştırıp güven.
4. **Temas davranışı** — bölge kaç kez dokunulmuş → TP/Skip oranı.
5. **Evren genişletme** — 92+ parite, hisse (MEXC + ek kaynak).

> terminalMiraz'a evrimin ilk büyük adımı (Piyasa Radar + Elenen kategorisi)
> atıldı. Sıradaki: Price Action Labs backtest motoru.
