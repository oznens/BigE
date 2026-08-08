from miraz.ablation import ablation_tara, etkilesim_tara
from miraz.lab import Islem
from miraz.lab_v2 import LiveLabRapor


def _rapor(rler, guven=75):
    islemler = []
    for i, r in enumerate(rler):
        sonuc = "TP" if r > 0 else "STOP"
        islemler.append(Islem(
            bar=i, giris=100, stop=95, hedef=105, rr=1.0,
            kalite="A", guven=guven, sonuc=sonuc, r=float(r),
        ))
    return LiveLabRapor(islemler=islemler)


def test_ablation_helpful_feature_ranks_positive():
    def runner(disabled):
        if "htf" in disabled:
            return _rapor([1, -1, -1, -1])
        if "fib" in disabled:
            return _rapor([1, 1, -1, -1])
        return _rapor([1, 1, 1, -1])

    r = ablation_tara(runner, ozellikler=["htf", "fib"], bootstrap_tekrar=100)
    sirali = r.sirali
    assert sirali[0].ozellik == "htf"
    assert sirali[0].delta_beklenti_r > sirali[1].delta_beklenti_r
    assert sirali[0].onem_puani > 0


def test_ablation_harmful_feature_can_be_negative():
    def runner(disabled):
        if "cluster" in disabled:
            return _rapor([1, 1, 1, 1])
        return _rapor([1, -1, 1, -1])

    r = ablation_tara(runner, ozellikler=["cluster"], bootstrap_tekrar=100)
    row = r.satirlar[0]
    assert row.delta_beklenti_r < 0
    assert row.onem_puani < 0


def test_interaction_synergy_detected():
    def runner(disabled):
        if disabled == {"a", "b"}:
            return _rapor([-1, -1, -1, -1])
        if disabled in ({"a"}, {"b"}):
            return _rapor([1, 1, -1, -1])
        return _rapor([1, 1, 1, -1])

    out = etkilesim_tara(runner, "a", "b", bootstrap_tekrar=100)
    assert out["sinerji"] > 0
