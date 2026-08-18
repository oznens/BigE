"""Piyasa Radar — çoklu parite/zaman dilimi setup tarayıcı (terminalMiraz tarzı).

@tradermiraz'ın terminalMiraz sistemi 118 enstrümanı 4 zaman diliminde eş
zamanlı tarayıp her setup'a Trade/Watch/Skip kararı ve A-D kalite verir; üst
zaman dilimi (HTF) aşağı olan setupları "Elenen Setup" kategorisine atar.

Bu modül aynı mantığı bizim senaryo + karar motorumuzla çoklu paritede
çalıştırır ve kategorize edilmiş bir tablo üretir.

Kullanım:
    from miraz.radar import radar_tara
    rapor = radar_tara(["BTCUSDT","ETHUSDT","SOLUSDT"], ["4h"])
    print(rapor.tablo())
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import konsept as kons
from . import senaryo as sn
from . import veri

# HTF eşlemesi (setup TF → üst zaman dilimi). Arşiv alt+üst TF kontrolünü
# kanıtlıyor; bu kesin eşleme BigE'nin uygulanmış yorumudur, Miraz'ın açıklanmış
# özel eşleme tablosu değildir.
_UST_TF = {"15m": "1h", "30m": "2h", "1h": "4h", "2h": "4h",
           "4h": "1d", "1d": "1w"}
# Gözlenen terminal TF merdivenindeki bir alt basamak. Arşiv kesin eşlemeyi
# açıklamaz; bu yüzden yalnız audit snapshot'ıdır, karar kapısı değildir.
_ALT_TF = {"30m": "15m", "1h": "30m", "2h": "1h", "4h": "2h",
           "1d": "4h"}

HTF_POLICY = {
    "archive_status": "implemented-in-testing-announced",
    "evidence_tweet_ids": ["2046218068255236383", "2052860896360480962",
                           "2064005426710986769"],
    "archive_confirmation_scope": "upper-and-lower-timeframes",
    "exact_tf_mapping": "undisclosed-by-archive",
    "current_mapping_origin": "BigE-interpretation",
    "current_implementation": "upper-veto-plus-lower-observation",
    "ltf_implementation": "observation-only",
    "ltf_mapping_origin": "BigE-adjacent-observed-TF-interpretation",
    "ltf_decision_effect": "none-until-calibrated",
    "direction_veto_origin": "BigE-safeguard-not-Miraz-rule",
}

# Arşiv minimum örnek, istatistiksel güven veya puan/veto dönüşüm formülü vermez.
# Bu kapı, gözlemsel MTF metriklerinin kendiliğinden trade kuralına dönüşmesini
# engeller. Mevcut HTF BigE güvenlik vetosu bu yeni kalibrasyon kapsamı dışındadır.
MTF_KALIBRASYON_POLICY = {
    "scope": "new-observation-derived-rules",
    "state": "locked",
    "automatic_activation": False,
    "minimum_verified_samples": None,
    "minimum_sample_origin": "undisclosed-by-archive",
    "effect_formula": "undisclosed-by-archive",
    "causal_validation": "not-established",
    "trade_effect": "none",
    "existing_htf_veto": "unchanged-BigE-safeguard",
    "unlock_requires": [
        "explicit-threshold", "documented-effect-formula",
        "out-of-sample-validation", "explicit-operator-enable",
    ],
}


def mtf_kalibrasyon_kapisi(sinif: str, dogrulanmis_n: int) -> dict:
    """Gözlemsel MTF sınıfının trade etkisini güvenli varsayılanla reddet."""
    return {
        "sinif": sinif, "dogrulanmis_n": max(int(dogrulanmis_n), 0),
        "eligible": False, "effect": 0,
        "state": MTF_KALIBRASYON_POLICY["state"],
        "reason": "threshold-formula-and-causal-validation-undisclosed",
    }

# Arşiv görsellerinde gözlenen canlı TF seti: M15/M30/H1/H2/H4. Tweet
# 2064005426710986769 aynı anda 4 TF tarandığını söyler ama dördünü adlandırmaz;
# bu liste bu yüzden "kesin Miraz kuralı" değil, BigE canlı tarama seçimidir.
TERMINALMIRAZ_TF = ["15m", "30m", "1h", "2h", "4h"]

# 3 risk modu. Doğrudan arşiv kanıtı 2062336764656677002:
# Güvenli +1R / Dengeli +2R / Riskli +3.5R.
RISK_MODLARI = {"guvenli": 1.0, "dengeli": 2.0, "riskli": 3.5}


def risk_modu_adi(rr_hedef: float) -> str:
    for ad, rr in RISK_MODLARI.items():
        if abs(float(rr_hedef) - rr) < 1e-9:
            return ad
    return "custom-bige"


def temas_snapshot(senaryo) -> dict:
    """Temas analizini Radar/Journal için sabit, JSON-uyumlu özete çevir."""
    t = getattr(senaryo, "temas", None)
    if t is None:
        return {}
    return {
        "alt": getattr(t, "alt", None), "ust": getattr(t, "ust", None),
        "toplam": getattr(t, "toplam", 0), "tepki": getattr(t, "tepki", 0),
        "kirilma": getattr(t, "kirilma", 0), "icerde": getattr(t, "icerde", 0),
        "son_davranis": getattr(t, "son_davranis", "yok"),
        "tepki_orani": getattr(t, "tepki_orani", 0.0),
        "yorgunluk": getattr(t, "yorgunluk", 0.0),
        "guven_etkisi": getattr(t, "guven_etkisi", 0.0),
        "model_origin": "BigE-heuristic-not-disclosed-by-archive",
    }

# Kanıtlar terminolojik olarak ayrıdır; içerikler açıklanmadığı için BigE
# kontrolleriyle birebir eşleme yapılmaz.
# - 2066320810545910019: PA 3 kademe, Harmonik 4 özel filtre detayı.
# - 2060346993600262442: Harmonik 5 test aşaması, her aşamada 4 kontrol.
KANITLI_KALITE_YAPISI = {
    "Price Action": {"kalite_kademe": 3},
    "Harmonik": {
        "test_asamasi": 5,
        "asama_basi_kontrol": 4,
        "kalite_filtre_detayi": 4,
    },
}

# Çekirdek evren — hızlı tarama (terminalMiraz "öncelikli takip" listesi)
CEKIRDEK_EVREN = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT",
    "AVAXUSDT", "LINKUSDT", "DOGEUSDT", "DOTUSDT",
]

# Geniş evren — terminalMiraz ölçeği (~90 likit MEXC USDT paritesi).
# MEXC'te bulunmayan semboller tarama sırasında hatalar listesine düşer, atlanır.
GENIS_EVREN = [
    # Majörler & L1
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT",
    "AVAXUSDT", "DOGEUSDT", "DOTUSDT", "LINKUSDT", "TRXUSDT", "IOTAUSDT",
    "LTCUSDT", "BCHUSDT", "NEARUSDT", "ATOMUSDT", "XLMUSDT", "ETCUSDT",
    "HBARUSDT", "ICPUSDT", "ALGOUSDT", "VETUSDT", "FILUSDT", "EGLDUSDT",
    # L2 / yeni L1
    "ARBUSDT", "OPUSDT", "SUIUSDT", "APTUSDT", "SEIUSDT", "INJUSDT",
    "TIAUSDT", "STXUSDT", "KASUSDT", "RUNEUSDT", "MINAUSDT", "FLOWUSDT",
    "STRKUSDT", "ZKUSDT", "MANTAUSDT", "DYMUSDT",
    # DeFi
    "UNIUSDT", "AAVEUSDT", "CAKEUSDT", "LDOUSDT", "CRVUSDT", "COMPUSDT",
    "SNXUSDT", "SUSHIUSDT", "DYDXUSDT", "GMXUSDT", "PENDLEUSDT", "ENAUSDT",
    "ONDOUSDT", "JUPUSDT", "PYTHUSDT", "JTOUSDT",
    # AI & DePIN
    "FETUSDT", "RENDERUSDT", "TAOUSDT", "WLDUSDT", "VIRTUALUSDT", "ARUSDT",
    "RAYUSDT", "GRTUSDT",
    # Meme
    "SHIBUSDT", "PEPEUSDT", "WIFUSDT", "BONKUSDT", "FLOKIUSDT", "BOMEUSDT",
    "MEMEUSDT", "NOTUSDT", "DOGSUSDT",
    # Gaming / Metaverse / NFT
    "SANDUSDT", "MANAUSDT", "AXSUSDT", "GALAUSDT", "IMXUSDT", "APEUSDT",
    "ENJUSDT", "BEAMUSDT", "ORDIUSDT",
    # Diğer likit
    "KAVAUSDT", "CHZUSDT", "QNTUSDT", "JASMYUSDT", "ROSEUSDT", "CFXUSDT",
    "WUSDT", "ENSUSDT", "ZROUSDT", "MOVEUSDT",
]

# Geriye dönük uyumluluk: varsayılan evren = çekirdek (hızlı).
VARSAYILAN_EVREN = CEKIRDEK_EVREN


@dataclass
class RadarSatiri:
    symbol: str
    interval: str
    fiyat: float
    kategori: str        # "Trade" / "Watch" / "Skip" / "Elenen"
    kalite: str          # A+/A/B/C/D
    guven: float
    yon: str
    giris: float | None
    hedef: float | None
    rr: float | None
    not_: str = ""
    taraf: str = "Long"   # "Long" / "Short"
    stop: float | None = None
    pattern: str | None = None   # harmonik pattern adı (Gartley/Deep Crab/...)
    risk_modu: str = "guvenli"
    risk_rr_hedef: float = 1.0
    risk_r_dolar: float = 25.0
    temas_detay: dict = None
    # terminalMiraz Result Journal motoru: Price Action / Harmonik / Late
    # (+ lifecycle nedeni Filtered / HTF). TradeFi (hisse) bizde yok.
    kaynak: str = "Price Action"
    # Karar kategorisinden bağımsız terminalMiraz yaşam döngüsü.
    # Arşiv kanıtı: 2064005426710986769 ve 2065351367544181110.
    lifecycle: str = "Candidate"
    # Sayısal güven ağırlıkları arşivde açıklanmadığı için Miraz kuralı değil.
    skor_modeli: str = "BigE heuristic v1"
    kalite_kademe: int | None = None
    test_asamasi: int | None = None
    asama_basi_kontrol: int | None = None
    kalite_filtre_detayi: int | None = None
    filtre_esleme: str = "undisclosed-by-archive"
    # MTF denetim snapshot'ı. Üst TF eşlemesi/sert veto BigE yorumudur;
    # arşivin bahsettiği alt TF kontrolü henüz uygulanmamıştır.
    ana_tf_yapi: str = ""
    htf_tf: str = ""
    htf_yapi: str = ""
    ltf_tf: str = ""
    ltf_yapi: str = "not-implemented"
    ltf_onay: str = "not-available"
    # PA alt türleri çok-etiketlidir. OB bağımsız dedektör değil, BigE kutu
    # sezgisinin proxy etiketidir; ayrıntı sözlüğü bu kökeni açıklar.
    setup_turleri: list = None
    setup_tur_detaylari: dict = None
    harmonik_detay: dict = None
    # PA konsept katmanları (Drift/Torque/Root/Shade/Strike/Cavity/Shear/
    # Ladder/Buffer/Reservoir) — bu setup'ta tetiklenen konsept isimleri.
    konseptler: list = None

    def __post_init__(self):
        motor = "Harmonik" if self.pattern else "Price Action"
        yapi = KANITLI_KALITE_YAPISI[motor]
        if self.kalite_kademe is None:
            self.kalite_kademe = yapi.get("kalite_kademe")
        if self.test_asamasi is None:
            self.test_asamasi = yapi.get("test_asamasi")
        if self.asama_basi_kontrol is None:
            self.asama_basi_kontrol = yapi.get("asama_basi_kontrol")
        if self.kalite_filtre_detayi is None:
            self.kalite_filtre_detayi = yapi.get("kalite_filtre_detayi")
        if self.setup_turleri is None:
            self.setup_turleri = []
        if self.setup_tur_detaylari is None:
            self.setup_tur_detaylari = {}
        if self.temas_detay is None:
            self.temas_detay = {}

    @property
    def _sira(self) -> tuple:
        # Trade > Watch > Skip > Elenen, sonra güven
        oncelik = {"Trade": 0, "Watch": 1, "Skip": 2, "Elenen": 3}
        return (oncelik.get(self.kategori, 4), -self.guven)


@dataclass
class RadarRapor:
    satirlar: list = field(default_factory=list)
    hatalar: list = field(default_factory=list)
    konsept_sayim: dict = field(default_factory=dict)   # {konsept: aday sayısı}

    @property
    def ozet(self) -> dict:
        o = {"Trade": 0, "Watch": 0, "Skip": 0, "Elenen": 0}
        for s in self.satirlar:
            o[s.kategori] = o.get(s.kategori, 0) + 1
        o["toplam"] = len(self.satirlar)
        return o

    def tablo(self, sadece: str | None = None) -> str:
        """Sıralı tablo metni. sadece='Trade' verilirse sadece o kategori."""
        sat = sorted(self.satirlar, key=lambda r: r._sira)
        if sadece:
            sat = [r for r in sat if r.kategori == sadece]
        ikon = {"Trade": "✅", "Watch": "👁️", "Skip": "🚫", "Elenen": "⛔"}
        bas = (f"{'':2} {'PARİTE':10} {'TF':4} {'T':2} {'KARAR':7} {'K':3} "
               f"{'GÜVEN':6} {'YÖN':9} {'R/R':5}  NOT")
        cizgi = "─" * len(bas)
        satirlar = [bas, cizgi]
        for r in sat:
            rr = f"{r.rr:.1f}" if r.rr is not None else "-"
            tarafe = "🔻" if r.taraf == "Short" else "🔼"
            satirlar.append(
                f"{ikon.get(r.kategori,'?')} {r.symbol:10} {r.interval:4} "
                f"{tarafe:2} {r.kategori:7} {r.kalite:3} %{r.guven:<4.0f} "
                f"{r.yon[:9]:9} {rr:5}  {r.not_[:40]}")
        o = self.ozet
        ozet_satir = (f"\nÖZET: {o['toplam']} tarama → "
                      f"✅ {o['Trade']} Trade · 👁️ {o['Watch']} Watch · "
                      f"🚫 {o['Skip']} Skip · ⛔ {o['Elenen']} Elenen")
        return "\n".join(satirlar) + "\n" + ozet_satir


def _kategori_belirle(s) -> tuple[str, str]:
    """Senaryodan (kategori, not) üretir; HTF engeli BigE güvenlik yorumudur."""
    karar = s.karar.karar if s.karar else "Skip"
    # Arşiv kesin eşleme/veto kuralını açıklamaz; bu BigE güvenlik yorumudur.
    if s.mtf_yapi == "problemli" and karar in ("Trade", "Watch"):
        return "Elenen", "HTF aşağı — BigE güvenlik filtresi (eşleme arşivde açıklanmadı)"
    # Miraz: "düşüş yapısında dipten alınmaz, kırılım onayı beklenir."
    # Kendi TF yapısı düşüşte ise Long karşı-trend → en fazla Watch (Trade değil).
    # Trade'e ancak yapısal dönüş (CHoCH-yukarı) onayı varsa izin ver.
    my = getattr(s, "market_yapisi", None)
    if my is not None and getattr(my, "durum", None) == "düşüş" and karar == "Trade":
        kirilim = getattr(my, "kirilim", None)
        if kirilim != "CHoCH-yukarı":
            karar = "Watch"   # karşı-trend long → teyit bekle
    notlar = []
    if getattr(s, "pamonic", False):
        notlar.append(f"🔷 PaMonic ({s.mavi_daire_isim} D)" if s.mavi_daire_isim
                      else "🔷 PaMonic")
    elif s.mavi_daire is not None:
        notlar.append(f"{s.mavi_daire_isim} D" if s.mavi_daire_isim
                      else "mavi daire")
    if s.ikili is not None and s.ikili.onayli:
        notlar.append(s.ikili.tip.lower())
    if s.kirilma_riski:
        notlar.append("hacimli geliş")
    if s.fib is not None and s.fib.fiyat_golden_icinde:
        notlar.append("golden pocket")
    return karar, ", ".join(notlar)


def _ltf_snapshot(df_alt, taraf: str) -> tuple[str, str]:
    """Alt TF yapısını gözlemle; trade puanı veya veto üretme."""
    if df_alt is None or len(df_alt) == 0:
        return "not-available", "not-available"
    try:
        from .yapi import market_yapisi
        durum = getattr(market_yapisi(df_alt), "durum", "") or "Bilinmiyor"
    except Exception:
        return "Bilinmiyor", "not-available"
    if durum == "yükseliş":
        onay = "trend-devam" if taraf == "Long" else "zayiflama"
    elif durum == "düşüş":
        onay = "trend-devam" if taraf == "Short" else "zayiflama"
    else:
        onay = "notr"
    return durum, onay


def _pa_setup_turleri(s, taraf: str) -> tuple[list[str], dict]:
    """Senaryo nesnesindeki gerçek tetikleri çok-etiketli PA audit'e dönüştür."""
    turler: list[str] = []
    detay: dict = {}
    kutu = (getattr(s, "destek_kutu", None) if taraf == "Long"
            else getattr(s, "direnc_kutu", None))
    if kutu is not None:
        turler.append("OB Proxy")
        detay["OB Proxy"] = {
            "origin": "BigE-zone-heuristic-not-exact-order-block",
            "tip": getattr(kutu, "tip", "Destek" if taraf == "Long" else "Direnç"),
            "guc": getattr(kutu, "guc", None),
        }
    div = getattr(s, "divergence", None)
    if div is not None:
        turler.append("Divergence")
        detay["Divergence"] = {"tip": getattr(div, "tip", "Bilinmiyor")}
    ikili = getattr(s, "ikili", None)
    if ikili is not None:
        turler.append("Double Top/Bottom")
        detay["Double Top/Bottom"] = {
            "tip": getattr(ikili, "tip", "Bilinmiyor"),
            "onayli": bool(getattr(ikili, "onayli", False)),
        }
    obo = getattr(s, "obo", None)
    if obo is not None:
        turler.append("OBO/TOBO")
        detay["OBO/TOBO"] = {
            "tip": getattr(obo, "tip", "Bilinmiyor"),
            "onayli": bool(getattr(obo, "onayli", False)),
        }
    fib = getattr(s, "fib", None)
    if fib is not None and bool(getattr(fib, "aktif", False)):
        turler.append("Fibonacci Retracement")
        detay["Fibonacci Retracement"] = {
            "yon": getattr(fib, "yon", "Bilinmiyor"),
            "golden_icinde": bool(getattr(fib, "fiyat_golden_icinde", False)),
        }
        if bool(getattr(fib, "fiyat_golden_icinde", False)):
            turler.append("Golden Pocket")
            detay["Golden Pocket"] = {"aralik": [
                getattr(fib, "golden_alt", None), getattr(fib, "golden_ust", None)]}
    my = getattr(s, "market_yapisi", None)
    kirilim = getattr(my, "kirilim", None) if my is not None else None
    if kirilim:
        turler.append("MSB")
        detay["MSB"] = {
            "exact_signal": kirilim,
            "origin": "BigE-market-structure-BOS-CHoCH-mapping",
        }
    return turler, detay


def _short_kategori(ks) -> tuple[str, str]:
    """Kısa senaryodan (kategori, not). HTF yukarı → Elenen (short aleyhine)."""
    karar = ks.karar.karar if ks.karar else "Skip"
    if ks.mtf_yapi == "sağlıklı" and karar in ("Trade", "Watch"):
        return "Elenen", "HTF yukarı — short Elenen (HTF-LTF filtresi)"
    notlar = []
    if ks.harmonik_isim is not None:
        notlar.append(f"{ks.harmonik_isim} D")
    if ks.ikili is not None and ks.ikili.onayli and ks.ikili.tip == "Çift Tepe":
        notlar.append("çift tepe")
    if ks.obo is not None and "OBO" in getattr(ks.obo, "tip", "") \
            and "TOBO" not in getattr(ks.obo, "tip", ""):
        notlar.append("obo")
    if ks.divergence is not None and ks.divergence.tip == "Bearish":
        notlar.append("bearish diverj.")
    if ks.rsi is not None and ks.rsi >= 70:
        notlar.append("aşırı alım")
    return karar, ", ".join(notlar)


# Arşiv Late filtresinin varlığını kanıtlıyor (2059325292926148742), ancak
# sayısal tespit eşiğini/formülünü açıklamıyor. Önceki %50 değeri kanıtsızdı.
# Otomatik Miraz sınıflandırması bu yüzden kapalıdır. Fonksiyon yalnız açıkça
# eşik verilen BigE deneylerinde kullanılabilir.
_LATE_ESIK = None


def _gec_kalmis(fiyat, giris, hedef, taraf: str,
                 esik: float | None = _LATE_ESIK) -> bool:
    """Fiyat, giriş→hedef yolunun esik'ten fazlasını katettiyse geç-kalmış.

    Long : katedilen = fiyat − giriş, toplam = hedef − giriş
    Short: katedilen = giriş − fiyat, toplam = giriş − hedef
    """
    if esik is None or fiyat is None or giris is None or hedef is None:
        return False
    if taraf == "Short":
        toplam, katedilen = giris - hedef, giris - fiyat
    else:
        toplam, katedilen = hedef - giris, fiyat - giris
    if toplam <= 0:
        return False
    return (katedilen / toplam) >= esik


def _lifecycle_belirle(kategori: str, notu: str, pattern: str | None) -> str:
    """Radar kararını arşivdeki ayrı setup statüsüne dönüştürür.

    `Trade/Watch/Skip/Elenen` karar katmanıdır; Late/Cancelled/No-Entry/
    Filtered ise terminalMiraz arşivinde ayrı raporlanan yaşam döngüsüdür.
    """
    n = (notu or "").lower()
    if "late" in n or "geç kalmış" in n:
        return "Late"
    if "stop bölgesi çiğnenmiş" in n:
        return "Cancelled" if pattern else "Filtered"
    # No-Entry arşivde "Entry bölgesine gelmedi" demektir (2061490944713601191).
    # Hedefin daha önce görülmesi farklı bir bayat-bölge filtresidir.
    if "entry bölgesine gelmedi" in n:
        return "No-Entry"
    if "hedef zaten görüldü" in n or "bölge çiğnenmiş" in n:
        return "Filtered"
    if kategori in ("Skip", "Elenen"):
        return "Filtered"
    if kategori == "Watch":
        return "Watch"
    return "Candidate"


def _hedef_zaten_gorundu(df, hedef, taraf: str, bar: int = 40) -> bool:
    """Son `bar` mumda fiyat hedefe (veya ötesine) zaten ulaştıysa True.

    terminalMiraz'ın @tradermiraz'ın anlattığı hatası: bölge çoktan çiğnenmiş
    (hareket olmuş) olmasına rağmen setup hâlâ aktif listeleniyor. Beklenen
    hareket yakın geçmişte zaten gerçekleştiyse setup bayat → Elenen.
      Short: son düşük ≤ hedef (düşüş zaten oldu)
      Long : son yüksek ≥ hedef (yükseliş zaten oldu)
    """
    if hedef is None or df is None or len(df) == 0:
        return False
    son = df.tail(bar)
    if taraf == "Short":
        return float(son["low"].min()) <= hedef
    return float(son["high"].max()) >= hedef


def _stop_zaten_vuruldu(df, stop, taraf: str, bar: int = 40) -> bool:
    """Son `bar` mumda stop ötesinde kapanış oluştuysa True.

    @tradermiraz'ın anlattığı hatanın diğer yüzü: setup hâlâ "Trade" görünüyor
    ama stop bölgesi yakın geçmişte zaten delinmiş — yani bu işlem girilmiş olsa
    çoktan stop olurdu. Stop, fiyatın yeni geçtiği bölgenin içinde kalıyorsa
    setup geçersizdir (PENDLE short: stop 1.47 iken fiyat 1.48-1.49 görmüş).
      Short: stop GİRİŞİN ÜSTÜNDE → kapanış > stop.
      Long : stop GİRİŞİN ALTINDA → kapanış < stop.
    """
    if stop is None or df is None or len(df) == 0:
        return False
    son = df.tail(bar)
    if taraf == "Short":
        return bool((son["close"] > stop).any())
    return bool((son["close"] < stop).any())


# Konsept confluence puanları (teyit/çelişki için taban ağırlık; guç ile ölçeklenir)
KONSEPT_PUAN = {"Reservoir": 6, "Shear": 6, "Strike": 5, "Root": 5, "Shade": 5,
                "Torque": 5, "Cavity": 4, "Drift": 4, "Ladder": 4, "Buffer": 3}
KONSEPT_TAVAN = 18.0   # net konsept etkisinin ± sınırı (güçlü mod)


def _konsept_etki(kons_sinyal: dict, yon: str) -> tuple[float, str | None]:
    """Konsept teyidi/çelişkisinden net güven etkisi (±KONSEPT_TAVAN).

    Setupla aynı yöndeki konseptler güveni artırır (confluence), ters yöndeki
    güçlü konsept düşürür. Katkı = taban_puan × (konsept gücü/100). Nötr katkısız.
    """
    ters = "Short" if yon == "Long" else "Long"
    etki = 0.0
    teyit, celiski = [], []
    for isim, s in (kons_sinyal or {}).items():
        puan = KONSEPT_PUAN.get(isim, 3) * (getattr(s, "guc", 0) / 100.0)
        if s.yon == yon:
            etki += puan
            teyit.append(isim)
        elif s.yon == ters:
            etki -= puan
            celiski.append(isim)
    etki = max(-KONSEPT_TAVAN, min(KONSEPT_TAVAN, etki))
    if not (teyit or celiski):
        return 0.0, None
    parcalar = []
    if teyit:
        parcalar.append("teyit " + "+".join(teyit))
    if celiski:
        parcalar.append("çelişki " + "+".join(celiski))
    return round(etki, 1), f"Konsept {', '.join(parcalar)} ({etki:+.0f})"


def _konsept_skor_uygula(karar_obj, etki: float, trade_engeli: bool = False) -> None:
    """Temel karara konsept etkisini ekler; karar/kalite/güveni yeniden türetir.

    Eşikler karar motoruyla aynı: Trade ≥70, Watch ≥50, aksi Skip. trade_engeli
    (ör. hacimli kırılma riski) varken konsept güveni Trade'e terfi ettirmez.
    """
    from .karar import _kalite
    if not etki or karar_obj is None:
        return
    g = max(0.0, min(100.0, getattr(karar_obj, "guven", 0.0) + etki))
    karar_obj.guven = round(g, 1)
    karar_obj.kalite = _kalite(g)
    if g >= 70 and not trade_engeli:
        karar_obj.karar = "Trade"
    elif g >= 50:
        karar_obj.karar = "Watch"
    else:
        karar_obj.karar = "Skip"


def radar_tara(semboller: list[str] | None = None,
               intervallar: list[str] | None = None,
               r_dolar: float = 25.0, gun: int = 400,
               cluster_hafiza: object = None,
               goreceli: bool = True, taraf: str = "long",
               rr_hedef: float = 1.0, max_bar: int | None = None,
               ilerleme=None) -> RadarRapor:
    """Çoklu parite × TF tarar, kategorize edilmiş RadarRapor döndürür.

    cluster_hafiza verilirse her senaryonun güveni geçmiş benzer setupların
    başarısına göre düzeltilir (terminalMiraz cluster katmanı).
    goreceli=False geniş evren taramasında göreceli güç indirmesini atlar (hız).
    taraf: "long" (varsayılan) | "short" | "her" (ikisi de).
    ilerleme: verilirse her parite/TF sonrası ilerleme(yapilan, toplam, rapor)
              çağrılır (canlı yüzde göstergesi için).
    """
    semboller = semboller or VARSAYILAN_EVREN
    intervallar = intervallar or ["4h"]
    rapor = RadarRapor()
    long_acik = taraf in ("long", "her")
    short_acik = taraf in ("short", "her")
    toplam = len(semboller) * len(intervallar)
    yapilan = 0

    for sym in semboller:
        for tf in intervallar:
            ust_tf = _UST_TF.get(tf)
            alt_tf = _ALT_TF.get(tf)
            df = df_ust = df_alt = None
            try:
                df = veri.indir(sym, tf, gun=gun, max_bar=max_bar)
            except Exception as e:
                rapor.hatalar.append(f"{sym}/{tf}: {e}")
            if df is not None and ust_tf:
                try:
                    df_ust = veri.indir(sym, ust_tf, gun=gun, max_bar=max_bar)
                except Exception as e:
                    rapor.hatalar.append(f"{sym}/{tf} HTF {ust_tf}: {e}")
            if df is not None and alt_tf:
                try:
                    df_alt = veri.indir(sym, alt_tf, gun=gun, max_bar=max_bar)
                except Exception as e:
                    rapor.hatalar.append(f"{sym}/{tf} LTF {alt_tf}: {e}")

            # PA konsept katmanları (Drift…Reservoir) — TF başına bir kez
            kons_sinyal = {}
            if df is not None:
                try:
                    kons_sinyal = kons.tara_konseptler(df)
                except Exception:
                    kons_sinyal = {}

            def _konsept_etiketleri(taraf_yon: str) -> list:
                """Setup yönüyle uyumlu (aynı yön veya Nötr) konsept isimleri."""
                uygun = [isim for isim, s in kons_sinyal.items()
                         if s.yon in (taraf_yon, "Nötr")]
                for isim in uygun:                  # global sayım (sol şerit)
                    rapor.konsept_sayim[isim] = rapor.konsept_sayim.get(isim, 0) + 1
                return uygun

            if df is not None and long_acik:
                try:
                    gguc = None
                    if goreceli:
                        from . import oran
                        try:
                            gguc = oran.goreceli_guc(sym)
                        except Exception:
                            gguc = None
                    s = sn.senaryo_uret(df, df_ust=df_ust, gguc=gguc,
                                        r_dolar=r_dolar,
                                        cluster_hafiza=cluster_hafiza)
                    ltf_yapi, ltf_onay = _ltf_snapshot(df_alt, "Long")
                    setup_turleri, setup_tur_detaylari = _pa_setup_turleri(s, "Long")
                    from .risk import risk_plani
                    rp = (risk_plani(s, r_dolar=r_dolar, rr_hedef=rr_hedef)
                          if s.destek_kutu else None)
                    # Konsept confluence: teyit/çelişki güveni ±18 oynatır,
                    # Watch↔Trade eşiğini gerçekten değiştirebilir
                    k_etki, k_metin = _konsept_etki(kons_sinyal, "Long")
                    _konsept_skor_uygula(s.karar, k_etki,
                                         trade_engeli=bool(s.kirilma_riski))
                    kategori, notu = _kategori_belirle(s)
                    if k_metin:
                        notu = (notu + " · " if notu else "") + k_metin
                    # Stop çiğnenmiş: stop bölgesi yakın geçmişte zaten delinmiş
                    # → setup geçersiz (girilmiş olsa çoktan stop olurdu)
                    if rp and kategori in ("Trade", "Watch") and \
                            _stop_zaten_vuruldu(df, rp.stop, "Long"):
                        kategori = "Elenen"
                        notu = "stop bölgesi çiğnenmiş (setup geçersiz)" + (
                            f" · {notu}" if notu else "")
                    # Late filtresi: hareketin çoğu gitmişse Trade/Watch → Elenen
                    elif rp and kategori in ("Trade", "Watch") and _gec_kalmis(
                            s.fiyat, rp.giris, rp.hedef, "Long"):
                        kategori = "Elenen"
                        notu = "Late (geç kalmış)" + (f" · {notu}" if notu else "")
                    # Bayat bölge: hedef yakın geçmişte zaten görüldü → Elenen
                    elif rp and kategori in ("Trade", "Watch") and \
                            _hedef_zaten_gorundu(df, rp.hedef, "Long"):
                        kategori = "Elenen"
                        notu = "bölge çiğnenmiş (hedef zaten görüldü)" + (
                            f" · {notu}" if notu else "")
                    # kaynak motoru belirleme (terminalMiraz Result Journal)
                    _pat = s.mavi_daire_isim
                    if "Late" in notu:
                        _kaynak = "Late"
                    elif _pat:
                        _kaynak = "Harmonik"      # harmonik D'li setup
                    elif kategori == "Watch":
                        _kaynak = "Filtered"      # eleme/lifecycle nedeni
                    elif kategori == "Trade":
                        _kaynak = "Price Action"  # saf PA setup
                    else:
                        _kaynak = "HTF"
                    rapor.satirlar.append(RadarSatiri(
                        symbol=sym, interval=tf, fiyat=s.fiyat, kategori=kategori,
                        kalite=s.karar.kalite if s.karar else "D",
                        guven=s.karar.guven if s.karar else 0.0, yon=s.yon,
                        giris=rp.giris if rp else None,
                        hedef=rp.hedef if rp else None,
                        rr=rp.rr_orani if rp else None, not_=notu,
                        taraf="Long", stop=rp.stop if rp else None,
                        pattern=_pat, kaynak=_kaynak,
                        risk_modu=risk_modu_adi(rr_hedef),
                        risk_rr_hedef=rr_hedef, risk_r_dolar=r_dolar,
                        temas_detay=temas_snapshot(s),
                        harmonik_detay=getattr(s, "harmonik_detay", None),
                        lifecycle=_lifecycle_belirle(kategori, notu, _pat),
                        ana_tf_yapi=getattr(
                            getattr(s, "market_yapisi", None), "durum", ""),
                        htf_tf=ust_tf or "", htf_yapi=s.mtf_yapi or "",
                        ltf_tf=alt_tf or "", ltf_yapi=ltf_yapi,
                        ltf_onay=ltf_onay,
                        setup_turleri=setup_turleri,
                        setup_tur_detaylari=setup_tur_detaylari,
                        konseptler=_konsept_etiketleri("Long")))
                except Exception as e:
                    rapor.hatalar.append(f"{sym}/{tf} (long): {e}")

            if df is not None and short_acik:
                try:
                    from .kisa import kisa_senaryo
                    from .risk import mesafe_hedef, harmonik_stop_sec
                    ks = kisa_senaryo(df, df_ust=df_ust)
                    ltf_yapi, ltf_onay = _ltf_snapshot(df_alt, "Short")
                    setup_turleri, setup_tur_detaylari = _pa_setup_turleri(ks, "Short")
                    # Konsept confluence (short): teyit/çelişki güveni ±18 oynatır
                    k_etki, k_metin = _konsept_etki(kons_sinyal, "Short")
                    _konsept_skor_uygula(ks.karar, k_etki)
                    kategori, notu = _short_kategori(ks)
                    if k_metin:
                        notu = (notu + " · " if notu else "") + k_metin
                    # terminalMiraz tarzı short TP: girişe stop mesafesi kadar (1R)
                    # giriş = harmonik D varsa orası (kisa_senaryo çözdü), yoksa bölge altı
                    s_giris = ks.giris
                    s_stop = (harmonik_stop_sec(
                        s_giris, ks.fitil_seviye,
                        getattr(ks, "harmonik_detay", None), "Short")
                        if s_giris is not None and ks.harmonik_isim
                        else ks.fitil_seviye)
                    s_hedef = s_rr = None
                    if (s_giris is not None and s_stop is not None
                            and s_stop > s_giris):
                        s_hedef = round(
                            mesafe_hedef(s_giris, s_stop, rr_hedef), 10)
                        s_rr = rr_hedef
                    # Stop çiğnenmiş (short): fitil/stop bölgesi yakın geçmişte
                    # zaten delinmiş → setup geçersiz (PENDLE: stop 1.47, fiyat 1.49)
                    if kategori in ("Trade", "Watch") and \
                            _stop_zaten_vuruldu(df, s_stop, "Short"):
                        kategori = "Elenen"
                        notu = "stop bölgesi çiğnenmiş (setup geçersiz)" + (
                            f" · {notu}" if notu else "")
                    # Late filtresi (short): düşüşün çoğu gitmişse → Elenen
                    elif kategori in ("Trade", "Watch") and _gec_kalmis(
                            ks.fiyat, s_giris, s_hedef, "Short"):
                        kategori = "Elenen"
                        notu = "Late (geç kalmış)" + (f" · {notu}" if notu else "")
                    # Bayat bölge (short): hedef yakın geçmişte zaten görüldü
                    elif kategori in ("Trade", "Watch") and \
                            _hedef_zaten_gorundu(df, s_hedef, "Short"):
                        kategori = "Elenen"
                        notu = "bölge çiğnenmiş (hedef zaten görüldü)" + (
                            f" · {notu}" if notu else "")
                    # kaynak motoru belirleme (short)
                    _s_pat = ks.harmonik_isim
                    if "Late" in notu:
                        _s_kaynak = "Late"
                    elif _s_pat:
                        _s_kaynak = "Harmonik"
                    elif kategori == "Watch":
                        _s_kaynak = "Filtered"
                    elif kategori == "Trade":
                        _s_kaynak = "Price Action"
                    else:
                        _s_kaynak = "HTF"
                    rapor.satirlar.append(RadarSatiri(
                        symbol=sym, interval=tf, fiyat=ks.fiyat,
                        kategori=kategori,
                        kalite=ks.karar.kalite if ks.karar else "D",
                        guven=ks.karar.guven if ks.karar else 0.0, yon=ks.yon,
                        giris=s_giris, hedef=s_hedef, rr=s_rr,
                        not_=notu, taraf="Short", stop=s_stop,
                        pattern=_s_pat, kaynak=_s_kaynak,
                        risk_modu=risk_modu_adi(rr_hedef),
                        risk_rr_hedef=rr_hedef, risk_r_dolar=r_dolar,
                        temas_detay=temas_snapshot(ks),
                        harmonik_detay=getattr(ks, "harmonik_detay", None),
                        lifecycle=_lifecycle_belirle(kategori, notu, _s_pat),
                        ana_tf_yapi=getattr(
                            getattr(ks, "market_yapisi", None), "durum", ""),
                        htf_tf=ust_tf or "", htf_yapi=ks.mtf_yapi or "",
                        ltf_tf=alt_tf or "", ltf_yapi=ltf_yapi,
                        ltf_onay=ltf_onay,
                        setup_turleri=setup_turleri,
                        setup_tur_detaylari=setup_tur_detaylari,
                        konseptler=_konsept_etiketleri("Short")))
                except Exception as e:
                    rapor.hatalar.append(f"{sym}/{tf} (short): {e}")

            yapilan += 1
            if ilerleme is not None:
                try:
                    ilerleme(yapilan, toplam, rapor)
                except Exception:
                    pass
    return rapor
