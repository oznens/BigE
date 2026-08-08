"""Feature ablation and importance analysis for live-style backtests.

This module compares a baseline backtest against runs where one feature family
is disabled. The caller supplies a runner accepting a set of disabled feature
names and returning LiveLabRapor. Keeping the runner injectable lets the same
analysis work for long/short, different costs, and future model variants.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from .istatistik import Performans, performans
from .lab_v2 import LiveLabRapor

# Canonical feature families used across the current decision engine. Additional
# names may be passed by callers without changing this module.
VARSAYILAN_OZELLIKLER = (
    "pamonic",
    "mavi_daire",
    "htf",
    "market_yapisi",
    "hacim_riski",
    "trend",
    "ikili",
    "temas",
    "divergence",
    "fib",
    "cluster",
    "konsept",
)


@dataclass
class AblationSatiri:
    ozellik: str
    baseline: Performans
    kapali: Performans
    delta_beklenti_r: float
    delta_toplam_r: float
    delta_profit_factor: float
    delta_max_drawdown_r: float
    delta_win_rate: float
    delta_islem: int
    onem_puani: float


@dataclass
class AblationRapor:
    baseline: Performans
    satirlar: list[AblationSatiri]

    @property
    def sirali(self) -> list[AblationSatiri]:
        """Most helpful features first by expectancy deterioration when removed."""
        return sorted(self.satirlar, key=lambda s: s.onem_puani, reverse=True)

    def tablo(self) -> str:
        bas = self.baseline
        out = [
            "🧬 ABLATION / FEATURE IMPORTANCE",
            f"Baseline: n={bas.n} WR=%{bas.win_rate:.1f} E={bas.beklenti_r:+.3f}R "
            f"PF={bas.profit_factor:.2f} MDD={bas.max_drawdown_r:.2f}R",
            "",
            f"{'ÖZELLİK':18} {'ΔE':>8} {'ΔR':>8} {'ΔPF':>8} {'ΔMDD':>8} {'ΔWR':>8} {'SKOR':>8}",
            "─" * 78,
        ]
        for s in self.sirali:
            out.append(
                f"{s.ozellik:18} {s.delta_beklenti_r:+8.3f} {s.delta_toplam_r:+8.2f} "
                f"{s.delta_profit_factor:+8.2f} {s.delta_max_drawdown_r:+8.2f} "
                f"{s.delta_win_rate:+8.2f} {s.onem_puani:+8.3f}")
        return "\n".join(out)


def _pf_delta(a: float, b: float) -> float:
    # Avoid inf-inf / inf arithmetic poisoning feature ranking.
    if a == float("inf") and b == float("inf"):
        return 0.0
    if a == float("inf"):
        return 10.0
    if b == float("inf"):
        return -10.0
    return a - b


def _onem(baseline: Performans, kapali: Performans) -> float:
    """Composite importance led by expectancy, then PF/WR/MDD stability.

    Positive means performance deteriorated when the feature was removed.
    Negative means the feature may be hurting the system.
    """
    d_e = baseline.beklenti_r - kapali.beklenti_r
    d_pf = _pf_delta(baseline.profit_factor, kapali.profit_factor)
    d_wr = (baseline.win_rate - kapali.win_rate) / 100.0
    # If disabling a feature lowers drawdown, that is evidence against it.
    d_mdd = kapali.max_drawdown_r - baseline.max_drawdown_r
    return round(d_e + 0.05 * d_pf + 0.10 * d_wr + 0.02 * d_mdd, 4)


def ablation_tara(
    runner: Callable[[set[str]], LiveLabRapor],
    *,
    ozellikler: Iterable[str] = VARSAYILAN_OZELLIKLER,
    bootstrap_tekrar: int = 500,
) -> AblationRapor:
    """Run baseline and one-feature-off experiments.

    runner(disabled_features) must return a LiveLabRapor. The baseline is called
    with an empty set; every ablation is called with exactly one disabled feature.
    This prevents accidental multi-feature interactions from being mislabeled as
    single-feature importance.
    """
    baseline_rapor = runner(set())
    baseline = performans(baseline_rapor, bootstrap_tekrar=bootstrap_tekrar)
    satirlar: list[AblationSatiri] = []

    for ozellik in ozellikler:
        kapali_rapor = runner({str(ozellik)})
        kapali = performans(kapali_rapor, bootstrap_tekrar=bootstrap_tekrar)
        satirlar.append(AblationSatiri(
            ozellik=str(ozellik),
            baseline=baseline,
            kapali=kapali,
            delta_beklenti_r=round(baseline.beklenti_r - kapali.beklenti_r, 4),
            delta_toplam_r=round(baseline.toplam_r - kapali.toplam_r, 4),
            delta_profit_factor=round(_pf_delta(baseline.profit_factor, kapali.profit_factor), 4),
            delta_max_drawdown_r=round(kapali.max_drawdown_r - baseline.max_drawdown_r, 4),
            delta_win_rate=round(baseline.win_rate - kapali.win_rate, 2),
            delta_islem=baseline.n - kapali.n,
            onem_puani=_onem(baseline, kapali),
        ))

    return AblationRapor(baseline=baseline, satirlar=satirlar)


def etkilesim_tara(
    runner: Callable[[set[str]], LiveLabRapor],
    ozellik_a: str,
    ozellik_b: str,
    *,
    bootstrap_tekrar: int = 500,
) -> dict:
    """Measure whether two features have non-additive interaction in expectancy."""
    p0 = performans(runner(set()), bootstrap_tekrar=bootstrap_tekrar)
    pa = performans(runner({ozellik_a}), bootstrap_tekrar=bootstrap_tekrar)
    pb = performans(runner({ozellik_b}), bootstrap_tekrar=bootstrap_tekrar)
    pab = performans(runner({ozellik_a, ozellik_b}), bootstrap_tekrar=bootstrap_tekrar)

    kayip_a = p0.beklenti_r - pa.beklenti_r
    kayip_b = p0.beklenti_r - pb.beklenti_r
    kayip_ab = p0.beklenti_r - pab.beklenti_r
    sinerji = kayip_ab - (kayip_a + kayip_b)
    return {
        "ozellik_a": ozellik_a,
        "ozellik_b": ozellik_b,
        "baseline_beklenti_r": p0.beklenti_r,
        "kayip_a": round(kayip_a, 4),
        "kayip_b": round(kayip_b, 4),
        "kayip_birlikte": round(kayip_ab, 4),
        "sinerji": round(sinerji, 4),
    }
