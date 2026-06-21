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

from . import senaryo as sn
from . import veri

# HTF eşlemesi (setup TF → üst zaman dilimi). terminalMiraz HTF-LTF kontrolü:
# alt TF setup'ı üst TF onaylamazsa Elenen'e düşer.
_UST_TF = {"15m": "1h", "30m": "2h", "1h": "4h", "2h": "4h",
           "4h": "1d", "1d": "1w"}

# terminalMiraz'ın kullandığı 4 zaman dilimi (tweet: "M15, M30, H1, H2").
TERMINALMIRAZ_TF = ["15m", "30m", "1h", "2h"]

# 3 risk modu (tweet: "Aşırı Güvenli / Dengeli / Tamamen Riskli").
# rr_hedef = hedefin kaç R uzağa konacağı: güvenli erken kâr-al, riskli koşturur.
RISK_MODLARI = {"guvenli": 1.0, "dengeli": 1.5, "riskli": 2.0}

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
    # terminalMiraz Result Journal motoru: Price Action / Harmonik / Late
    # (+ lifecycle nedeni Filtered / HTF). TradeFi (hisse) bizde yok.
    kaynak: str = "Price Action"

    @property
    def _sira(self) -> tuple:
        # Trade > Watch > Skip > Elenen, sonra güven
        oncelik = {"Trade": 0, "Watch": 1, "Skip": 2, "Elenen": 3}
        return (oncelik.get(self.kategori, 4), -self.guven)


@dataclass
class RadarRapor:
    satirlar: list = field(default_factory=list)
    hatalar: list = field(default_factory=list)

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
    """Senaryodan (kategori, not) üretir. HTF aşağı → Elenen (terminalMiraz)."""
    karar = s.karar.karar if s.karar else "Skip"
    # terminalMiraz kuralı: üst zaman dilimi problemli → Elenen Setup
    if s.mtf_yapi == "problemli" and karar in ("Trade", "Watch"):
        return "Elenen", "HTF aşağı — Elenen Setup (HTF-LTF filtresi)"
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


# Geç-kalmış (Late) eşiği: giriş→hedef hareketinin ne kadarı zaten gitmişse
# setup "geç" sayılır (terminalMiraz Late filtresi — stop riskini azaltır).
_LATE_ESIK = 0.5


def _gec_kalmis(fiyat, giris, hedef, taraf: str, esik: float = _LATE_ESIK) -> bool:
    """Fiyat, giriş→hedef yolunun esik'ten fazlasını katettiyse geç-kalmış.

    Long : katedilen = fiyat − giriş, toplam = hedef − giriş
    Short: katedilen = giriş − fiyat, toplam = giriş − hedef
    """
    if fiyat is None or giris is None or hedef is None:
        return False
    if taraf == "Short":
        toplam, katedilen = giris - hedef, giris - fiyat
    else:
        toplam, katedilen = hedef - giris, fiyat - giris
    if toplam <= 0:
        return False
    return (katedilen / toplam) >= esik


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
            try:
                df = veri.indir(sym, tf, gun=gun, max_bar=max_bar)
                ust_tf = _UST_TF.get(tf)
                df_ust = (veri.indir(sym, ust_tf, gun=gun, max_bar=max_bar)
                          if ust_tf else None)
            except Exception as e:
                rapor.hatalar.append(f"{sym}/{tf}: {e}")
                df = None

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
                    kategori, notu = _kategori_belirle(s)
                    from .risk import risk_plani
                    rp = (risk_plani(s, r_dolar=r_dolar, rr_hedef=rr_hedef)
                          if s.destek_kutu else None)
                    # Late filtresi: hareketin çoğu gitmişse Trade/Watch → Elenen
                    if rp and kategori in ("Trade", "Watch") and _gec_kalmis(
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
                        pattern=_pat, kaynak=_kaynak))
                except Exception as e:
                    rapor.hatalar.append(f"{sym}/{tf} (long): {e}")

            if df is not None and short_acik:
                try:
                    from .kisa import kisa_senaryo
                    from .risk import mesafe_hedef
                    ks = kisa_senaryo(df, df_ust=df_ust)
                    kategori, notu = _short_kategori(ks)
                    # terminalMiraz tarzı short TP: girişe stop mesafesi kadar (1R)
                    # giriş = harmonik D varsa orası (kisa_senaryo çözdü), yoksa bölge altı
                    s_giris = ks.giris
                    s_hedef = s_rr = None
                    if (s_giris is not None and ks.fitil_seviye is not None
                            and ks.fitil_seviye > s_giris):
                        s_hedef = round(
                            mesafe_hedef(s_giris, ks.fitil_seviye, rr_hedef), 6)
                        s_rr = rr_hedef
                    # Late filtresi (short): düşüşün çoğu gitmişse → Elenen
                    if kategori in ("Trade", "Watch") and _gec_kalmis(
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
                        not_=notu, taraf="Short", stop=ks.fitil_seviye,
                        pattern=_s_pat, kaynak=_s_kaynak))
                except Exception as e:
                    rapor.hatalar.append(f"{sym}/{tf} (short): {e}")

            yapilan += 1
            if ilerleme is not None:
                try:
                    ilerleme(yapilan, toplam, rapor)
                except Exception:
                    pass
    return rapor
