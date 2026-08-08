from dataclasses import dataclass

from miraz.agirlik_kalibrasyon import plani_uret
from miraz.karar import karar_uret
from miraz.ablation import AblationRapor, AblationSatiri
from miraz.istatistik import Performans


def _perf(n=100, e=0.2, pf=1.5, wr=60, mdd=4):
    return Performans(n=n, win_rate=wr, toplam_r=e*n, beklenti_r=e,
                      profit_factor=pf, max_drawdown_r=mdd,
                      bootstrap_beklenti_ci=(e-0.1, e+0.1))


def test_pozitif_onem_agirligi_artirir_negatif_azaltir():
    b = _perf()
    iyi = AblationSatiri("htf", b, _perf(e=0.05), 0.15, 15, 0.4, 1, 5, 0, 0.5)
    kotu = AblationSatiri("fib", b, _perf(e=0.3), -0.1, -10, -0.2, -1, -3, 0, -0.4)
    plan = plani_uret(AblationRapor(baseline=b, satirlar=[iyi, kotu]))
    assert plan.agirliklar["htf"] > 1.0
    assert plan.agirliklar["fib"] < 1.0


def test_az_ornek_1e_shrink_olur():
    b = _perf(n=5)
    s = AblationSatiri("trend", b, _perf(n=5, e=-0.5), 0.7, 3.5, 1, 2, 10, 0, 2.0)
    plan = plani_uret(AblationRapor(baseline=b, satirlar=[s]), hedef_ornek=100)
    assert 1.0 < plan.agirliklar["trend"] < 1.05


@dataclass
class Kutu:
    guc: float = 100


@dataclass
class Yapi:
    durum: str = "yükseliş"


class Senaryo:
    destek_kutu = Kutu()
    mavi_daire = 1.0
    pamonic = False
    mtf_yapi = "sağlıklı"
    market_yapisi = Yapi()
    kirilma_riski = False
    trend = None
    ikili = None
    temas = None
    divergence = None
    hedef_kutu = None


def test_agirlik_yoksa_eski_skor_davranisi_korunur():
    s = Senaryo()
    a = karar_uret(s, rr=1.0)
    b = karar_uret(s, rr=1.0, agirliklar={})
    assert a.guven == b.guven
    assert a.karar == b.karar


def test_agirlik_karar_skorunu_degistirebilir():
    s = Senaryo()
    normal = karar_uret(s, rr=None)
    dusuk = karar_uret(s, rr=None, agirliklar={"mavi_daire": 0.0, "htf": 0.0,
                                               "market_yapisi": 0.0, "destek": 0.0})
    assert dusuk.guven < normal.guven
