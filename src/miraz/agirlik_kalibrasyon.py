"""Validation-only feature weight calibration.

Ablation sonuçlarından özellik çarpanları üretir. Tasarımın kritik kuralı:
OOS verisi ağırlık seçimine ASLA girmez. Ağırlıklar validation sonucundan
üretilir, dondurulur ve daha sonra OOS/canlı karar motoruna uygulanır.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .ablation import AblationRapor


@dataclass(frozen=True)
class AgirlikPlani:
    agirliklar: dict[str, float]
    kaynak: str = "validation"
    min_carpan: float = 0.5
    max_carpan: float = 1.5
    notlar: tuple[str, ...] = field(default_factory=tuple)

    def get(self, ad: str, default: float = 1.0) -> float:
        return float(self.agirliklar.get(ad, default))


def _shrink(n: int, hedef_n: int) -> float:
    """Az örnekli ablation etkisini 1.0'a doğru küçültür."""
    if hedef_n <= 0:
        return 1.0
    return max(0.0, min(1.0, n / hedef_n))


def plani_uret(
    rapor: AblationRapor,
    *,
    min_carpan: float = 0.5,
    max_carpan: float = 1.5,
    hassasiyet: float = 0.35,
    hedef_ornek: int = 80,
) -> AgirlikPlani:
    """Validation ablation raporunu bounded feature multipliers'a çevirir.

    Pozitif önem → ağırlık > 1, negatif önem → ağırlık < 1.
    Önem puanı doğrudan kullanılmaz; tanh-benzeri bounded dönüşüm yerine
    basit rasyonel sıkıştırma uygulanır ki tek bir gürültülü özellik aşırı
    ağırlık kazanmasın. Az işlemli sonuçlar 1.0'a shrink edilir.
    """
    if min_carpan <= 0 or max_carpan < min_carpan:
        raise ValueError("geçersiz çarpan sınırları")

    agirliklar: dict[str, float] = {}
    notlar: list[str] = []
    for sat in rapor.satirlar:
        raw = float(sat.onem_puani)
        # [-1,1] aralığına yumuşak sıkıştırma
        sikisik = raw / (1.0 + abs(raw))
        hedef = 1.0 + hassasiyet * sikisik
        n = min(int(sat.baseline.n), int(sat.kapali.n))
        shrink = _shrink(n, hedef_ornek)
        carpan = 1.0 + (hedef - 1.0) * shrink
        carpan = max(min_carpan, min(max_carpan, carpan))
        agirliklar[sat.ozellik] = round(carpan, 4)
        notlar.append(
            f"{sat.ozellik}: önem={raw:+.4f}, n={n}, shrink={shrink:.2f}, "
            f"çarpan={carpan:.3f}")

    return AgirlikPlani(
        agirliklar=agirliklar,
        kaynak="validation",
        min_carpan=min_carpan,
        max_carpan=max_carpan,
        notlar=tuple(notlar),
    )


def plan_ozeti(plan: AgirlikPlani) -> str:
    sat = ["⚖️ VALIDATION AĞIRLIK PLANI"]
    for ad, carpan in sorted(plan.agirliklar.items(), key=lambda kv: kv[1], reverse=True):
        yon = "↑" if carpan > 1.0 else ("↓" if carpan < 1.0 else "=")
        sat.append(f"  {yon} {ad:18} ×{carpan:.3f}")
    sat.append("  Not: OOS bu seçimde kullanılmadı; plan validation sonrası dondurulur.")
    return "\n".join(sat)
