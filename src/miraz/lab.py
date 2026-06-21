"""Price Action Labs — backtest motoru (terminalMiraz tarzı).

@tradermiraz'ın terminalMiraz'ı, kararlarını 2020-2026 arası binlerce gerçek
setup üzerinde test edip girişin/stop'un/TP'nin gerçek davranışını ölçer
(TP Lab, Giriş Lab, Stop Lab) ve win-rate / R sonuçları üretir.

Bu motor aynı mantığı bizim senaryo + risk motorumuzla uygular:
  - Her karar barında (look-ahead yok) senaryo üretir, giriş/stop/hedef alır.
  - İleriye doğru simüle eder: önce giriş dolar mı, sonra TP mi STOP mu gelir.
  - Sonuçları toplar: işlem sayısı, win-rate, toplam/ortalama R, kaliteye göre.

Kullanım:
    from miraz.lab import backtest
    rapor = backtest(df, adim=6, max_bar=60)
    print(rapor.ozet_metin())
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from . import senaryo as sn
from .risk import risk_plani


@dataclass
class Islem:
    bar: int             # setup'ın oluştuğu bar
    giris: float
    stop: float
    hedef: float
    rr: float
    kalite: str
    guven: float
    sonuc: str           # "TP" / "STOP" / "Dolmadı" / "Açık"
    r: float             # +rr (TP) / -1 (STOP) / 0


@dataclass
class LabRapor:
    islemler: list = field(default_factory=list)

    @property
    def dolan(self) -> list:
        return [i for i in self.islemler if i.sonuc in ("TP", "STOP")]

    @property
    def win_rate(self) -> float:
        d = self.dolan
        if not d:
            return 0.0
        return 100.0 * sum(1 for i in d if i.sonuc == "TP") / len(d)

    @property
    def toplam_r(self) -> float:
        return round(sum(i.r for i in self.dolan), 2)

    @property
    def beklenti_r(self) -> float:
        """İşlem başına beklenen R (expectancy)."""
        d = self.dolan
        return round(self.toplam_r / len(d), 3) if d else 0.0

    def kaliteye_gore(self) -> dict:
        out = {}
        for i in self.dolan:
            g = out.setdefault(i.kalite, {"n": 0, "tp": 0, "r": 0.0})
            g["n"] += 1
            g["tp"] += 1 if i.sonuc == "TP" else 0
            g["r"] += i.r
        for g in out.values():
            g["wr"] = round(100 * g["tp"] / g["n"], 1) if g["n"] else 0
            g["r"] = round(g["r"], 2)
        return out

    def ozet_metin(self) -> str:
        d = self.dolan
        tp = sum(1 for i in d if i.sonuc == "TP")
        st = sum(1 for i in d if i.sonuc == "STOP")
        dolmadi = sum(1 for i in self.islemler if i.sonuc == "Dolmadı")
        sat = [
            "🧪 PRICE ACTION LABS — Backtest Sonucu",
            f"   Setup: {len(self.islemler)} | Dolan: {len(d)} "
            f"(TP {tp} - STOP {st}) | Dolmadı: {dolmadi}",
            f"   Win-rate: %{self.win_rate:.1f} | Toplam: {self.toplam_r:+.1f}R "
            f"| Beklenti: {self.beklenti_r:+.3f}R/işlem",
        ]
        kg = self.kaliteye_gore()
        if kg:
            sat.append("   Kaliteye göre:")
            for k in ["A+", "A", "B", "C", "D"]:
                if k in kg:
                    g = kg[k]
                    sat.append(f"     {k:2}: {g['n']:3} işlem | "
                               f"WR %{g['wr']:<5} | {g['r']:+.1f}R")
        return "\n".join(sat)


def _simule(df, bar: int, giris: float, stop: float, hedef: float,
            max_bar: int) -> tuple[str, int]:
    """Giriş barından sonra TP/STOP/Dolmadı sonucunu döndürür (long).

    Önce giriş limitine (giris, fiyatın altında) dokunulmalı; sonra TP/STOP.
    Aynı barda hem stop hem hedef tetiklenirse STOP (muhafazakâr).
    """
    n = len(df)
    son = min(bar + max_bar, n - 1)
    low = df["low"].to_numpy()
    high = df["high"].to_numpy()

    doldu = False
    for j in range(bar + 1, son + 1):
        if not doldu:
            if low[j] <= giris:        # limit giriş doldu
                doldu = True
            else:
                continue
        # giriş dolduktan sonra (aynı bar dahil) stop/hedef kontrolü
        if low[j] <= stop:
            return "STOP", j
        if high[j] >= hedef:
            return "TP", j
    return ("Açık" if doldu else "Dolmadı"), son


def _senaryo_noktalari(df: pd.DataFrame, adim: int, pencere: int,
                       min_bar: int, r_dolar: float) -> list:
    """Karar barlarında senaryoyu BİR KEZ üretir (pahalı kısım, cache'lenir).

    Döndürür: [(bar_idx, Senaryo), ...] — destek bölgesi olanlar.
    """
    n = len(df)
    bas = max(min_bar, n - pencere)
    noktalar = []
    for i in range(bas, n - 1, adim):
        try:
            s = sn.senaryo_uret(df.iloc[:i + 1], df_ust=None, r_dolar=0.0)
        except Exception:
            continue
        if s.destek_kutu is not None:
            noktalar.append((i, s))
    return noktalar


def _kur_islem(s, giris_mod: str, stop_mod: str, tp_mod: str):
    """Senaryodan (giriş, stop, hedef) üretir — Lab modlarına göre (long).

    giris: 'orta'(mavi daire/orta) | 'ust'(bölge üstü) | 'alt'(bölge altı)
    stop : 'fitil'(dar) | 'yapisal'(bölge altı %2) | 'genis'(kritik %3 altı)
    tp   : 'ana'(ana hedef) | 'ara'(mor çizgi/hızlı) | 'rr2'(sabit 2R)
    """
    ba, bu = s.bolge_alt, s.bolge_ust
    if ba is None or bu is None:
        return None
    # Giriş
    if giris_mod == "ust":
        giris = bu
    elif giris_mod == "alt":
        giris = ba
    else:  # orta
        giris = float(s.mavi_daire) if s.mavi_daire is not None else (ba + bu) / 2
    # Stop
    if stop_mod == "yapisal":
        stop = ba * (1 - 0.02)
    elif stop_mod == "genis":
        stop = (s.kritik_seviye or ba) * (1 - 0.03)
    else:  # fitil
        stop = s.fitil_seviye if s.fitil_seviye is not None else ba * 0.985
    if stop >= giris:
        return None
    # Hedef
    if tp_mod == "ara" and s.ara_hedef is not None:
        hedef = float(s.ara_hedef)
    elif tp_mod == "rr2":
        hedef = giris + 2.0 * (giris - stop)
    else:  # ana
        hedef = s.hedef_kutu.alt if s.hedef_kutu is not None else None
    if hedef is None or hedef <= giris:
        return None
    rr = (hedef - giris) / (giris - stop)
    if rr <= 0:
        return None
    return round(giris, 6), round(stop, 6), round(hedef, 6), round(rr, 2)


def _backtest_modlu(df, noktalar, giris_mod="orta", stop_mod="fitil",
                    tp_mod="ana", max_bar=60, min_guven=0.0,
                    sadece_trade=False, adim=6) -> LabRapor:
    """Önceden üretilmiş senaryo noktalarından mod-bazlı backtest (ucuz)."""
    rapor = LabRapor()
    son_acilan = -10_000
    for i, s in noktalar:
        if sadece_trade and (s.karar is None or s.karar.karar != "Trade"):
            continue
        if s.karar is not None and s.karar.guven < min_guven:
            continue
        kur = _kur_islem(s, giris_mod, stop_mod, tp_mod)
        if kur is None:
            continue
        giris, stop, hedef, rr = kur
        if i - son_acilan < adim:
            continue
        sonuc, _ = _simule(df, i, giris, stop, hedef, max_bar)
        r = {"TP": rr, "STOP": -1.0}.get(sonuc, 0.0)
        rapor.islemler.append(Islem(
            bar=i, giris=giris, stop=stop, hedef=hedef, rr=rr,
            kalite=s.karar.kalite if s.karar else "D",
            guven=s.karar.guven if s.karar else 0.0, sonuc=sonuc, r=r))
        if sonuc in ("TP", "STOP"):
            son_acilan = i
    return rapor


def backtest(df: pd.DataFrame, adim: int = 6, max_bar: int = 60,
             pencere: int = 600, min_bar: int = 200,
             sadece_trade: bool = False, min_guven: float = 0.0,
             r_dolar: float = 25.0, giris_mod: str = "orta",
             stop_mod: str = "fitil", tp_mod: str = "ana") -> LabRapor:
    """Geçmiş veride senaryo+risk kararlarını test eder (look-ahead yok)."""
    noktalar = _senaryo_noktalari(df, adim, pencere, min_bar, r_dolar)
    return _backtest_modlu(df, noktalar, giris_mod, stop_mod, tp_mod,
                           max_bar, min_guven, sadece_trade, adim)


# ---------------------------------------------------------------------------
# TP / Giriş / Stop Lab — parametre taraması (terminalMiraz'ın ayrı Lab'ları)
# ---------------------------------------------------------------------------

_LAB_MODLAR = {
    "Giriş": ("giris_mod", ["ust", "orta", "alt"]),
    "Stop":  ("stop_mod", ["fitil", "yapisal", "genis"]),
    "TP":    ("tp_mod", ["ana", "ara", "rr2"]),
}


def _birlestir(raporlar: list) -> dict:
    """Birden çok sembolün LabRapor'unu tek istatistiğe toplar."""
    dolan = [i for r in raporlar for i in r.dolan]
    if not dolan:
        return {"n": 0, "wr": 0.0, "r": 0.0, "beklenti": 0.0}
    tp = sum(1 for i in dolan if i.sonuc == "TP")
    r = sum(i.r for i in dolan)
    return {"n": len(dolan), "wr": round(100 * tp / len(dolan), 1),
            "r": round(r, 2), "beklenti": round(r / len(dolan), 3)}


def lab_tara(df_sozluk: dict, adim: int = 6, max_bar: int = 60,
             pencere: int = 800, min_guven: float = 0.0) -> str:
    """Her Lab boyutunu (Giriş/Stop/TP) ayrı ayrı tarayıp kıyaslar.

    df_sozluk: {sembol: df}. Senaryo noktaları sembol başına BİR KEZ üretilir;
    tüm mod kombinasyonları o cache'ten ucuzca denenir.
    """
    # Pahalı kısım: her sembol için senaryo noktaları (bir kez)
    nokta_cache = {sym: _senaryo_noktalari(df, adim, pencere, 200, 0.0)
                   for sym, df in df_sozluk.items()}

    varsayilan = {"giris_mod": "orta", "stop_mod": "fitil", "tp_mod": "ana"}
    cikti = ["🔬 LAB TARAMASI — en iyi giriş/stop/TP kuralı (veriyle)"]

    for lab_ad, (anahtar, modlar) in _LAB_MODLAR.items():
        cikti.append(f"\n── {lab_ad} Lab ──")
        en_iyi = (None, -1e9)
        for mod in modlar:
            kfg = dict(varsayilan)
            kfg[anahtar] = mod
            raporlar = [
                _backtest_modlu(df_sozluk[sym], nokta_cache[sym],
                                giris_mod=kfg["giris_mod"],
                                stop_mod=kfg["stop_mod"], tp_mod=kfg["tp_mod"],
                                max_bar=max_bar, min_guven=min_guven, adim=adim)
                for sym in df_sozluk]
            st = _birlestir(raporlar)
            isaret = " ⭐" if mod == varsayilan[anahtar] else ""
            cikti.append(
                f"   {mod:8}: {st['n']:3} işlem | WR %{st['wr']:<5} | "
                f"{st['r']:+.1f}R | beklenti {st['beklenti']:+.3f}R{isaret}")
            if st["beklenti"] > en_iyi[1] and st["n"] >= 10:
                en_iyi = (mod, st["beklenti"])
        if en_iyi[0]:
            cikti.append(f"   → en iyi: {en_iyi[0]} ({en_iyi[1]:+.3f}R/işlem)")
    cikti.append("\n(⭐ = mevcut varsayılan)")
    return "\n".join(cikti)
