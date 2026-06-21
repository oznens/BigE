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


def backtest(df: pd.DataFrame, adim: int = 6, max_bar: int = 60,
             pencere: int = 600, min_bar: int = 200,
             sadece_trade: bool = False, min_guven: float = 0.0,
             r_dolar: float = 25.0) -> LabRapor:
    """Geçmiş veride senaryo+risk kararlarını test eder (look-ahead yok).

    adim       : kaç barda bir karar noktası (4h'de 6 ≈ günde 1)
    max_bar    : bir setup'a kaç bar sonuç şansı verilir
    pencere    : son kaç barı test et
    min_bar    : senaryo için gereken minimum geçmiş
    sadece_trade: yalnızca karar=='Trade' olanları işleme al
    min_guven  : bu güvenin altındaki setuplar atlanır
    """
    rapor = LabRapor()
    n = len(df)
    bas = max(min_bar, n - pencere)
    son_acilan = -10_000

    for i in range(bas, n - 1, adim):
        gecmis = df.iloc[:i + 1]
        try:
            s = sn.senaryo_uret(gecmis, df_ust=None, r_dolar=r_dolar)
        except Exception:
            continue
        if s.destek_kutu is None:
            continue
        if sadece_trade and (s.karar is None or s.karar.karar != "Trade"):
            continue
        if s.karar is not None and s.karar.guven < min_guven:
            continue
        rp = risk_plani(s, r_dolar=r_dolar)
        if rp is None or rp.hedef is None or rp.rr_orani is None:
            continue
        if rp.rr_orani <= 0:
            continue
        # üst üste aynı setup'ı açma (çözülene dek bekle)
        if i - son_acilan < adim:
            continue

        sonuc, _ = _simule(df, i, rp.giris, rp.stop, rp.hedef, max_bar)
        r = {"TP": rp.rr_orani, "STOP": -1.0}.get(sonuc, 0.0)
        rapor.islemler.append(Islem(
            bar=i, giris=rp.giris, stop=rp.stop, hedef=rp.hedef,
            rr=rp.rr_orani, kalite=s.karar.kalite if s.karar else "D",
            guven=s.karar.guven if s.karar else 0.0, sonuc=sonuc, r=r))
        if sonuc in ("TP", "STOP"):
            son_acilan = i
    return rapor
