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

# HTF eşlemesi (setup TF → üst zaman dilimi)
_UST_TF = {"15m": "1h", "1h": "4h", "4h": "1d", "1d": "1w"}

# terminalMiraz çekirdek evreni (örnek; genişletilebilir)
VARSAYILAN_EVREN = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT",
    "AVAXUSDT", "LINKUSDT", "DOGEUSDT", "DOTUSDT",
]


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
        bas = (f"{'':2} {'PARİTE':10} {'TF':4} {'KARAR':7} {'K':3} "
               f"{'GÜVEN':6} {'YÖN':9} {'R/R':5}  NOT")
        cizgi = "─" * len(bas)
        satirlar = [bas, cizgi]
        for r in sat:
            rr = f"{r.rr:.1f}" if r.rr is not None else "-"
            satirlar.append(
                f"{ikon.get(r.kategori,'?')} {r.symbol:10} {r.interval:4} "
                f"{r.kategori:7} {r.kalite:3} %{r.guven:<4.0f} "
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
    if s.mavi_daire is not None:
        notlar.append("mavi daire")
    if s.ikili is not None and s.ikili.onayli:
        notlar.append(s.ikili.tip.lower())
    if s.kirilma_riski:
        notlar.append("hacimli geliş")
    if s.fib is not None and s.fib.fiyat_golden_icinde:
        notlar.append("golden pocket")
    return karar, ", ".join(notlar)


def radar_tara(semboller: list[str] | None = None,
               intervallar: list[str] | None = None,
               r_dolar: float = 25.0, gun: int = 400) -> RadarRapor:
    """Çoklu parite × TF tarar, kategorize edilmiş RadarRapor döndürür."""
    semboller = semboller or VARSAYILAN_EVREN
    intervallar = intervallar or ["4h"]
    rapor = RadarRapor()

    for sym in semboller:
        for tf in intervallar:
            try:
                df = veri.indir(sym, tf, gun=gun)
                ust_tf = _UST_TF.get(tf)
                df_ust = veri.indir(sym, ust_tf, gun=gun) if ust_tf else None
                from . import oran
                try:
                    gguc = oran.goreceli_guc(sym)
                except Exception:
                    gguc = None
                s = sn.senaryo_uret(df, df_ust=df_ust, gguc=gguc,
                                    r_dolar=r_dolar)
            except Exception as e:
                rapor.hatalar.append(f"{sym}/{tf}: {e}")
                continue

            kategori, notu = _kategori_belirle(s)
            from .risk import risk_plani
            rp = risk_plani(s, r_dolar=r_dolar) if s.destek_kutu else None
            rapor.satirlar.append(RadarSatiri(
                symbol=sym, interval=tf, fiyat=s.fiyat, kategori=kategori,
                kalite=s.karar.kalite if s.karar else "D",
                guven=s.karar.guven if s.karar else 0.0, yon=s.yon,
                giris=rp.giris if rp else None,
                hedef=rp.hedef if rp else None,
                rr=rp.rr_orani if rp else None, not_=notu))
    return rapor
