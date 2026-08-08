"""Portföy-seviyesi risk guardrails.

Tekil setup riskinden bağımsız olarak toplam açık riski, notional/leverage,
günlük zarar ve korelasyon kümesi yoğunlaşmasını sınırlar.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class RiskLimits:
    max_open_r: float = 4.0
    max_positions: int = 6
    max_notional_usd: float = 25_000.0
    max_leverage: float = 5.0
    daily_loss_r: float = 3.0
    max_cluster_r: float = 2.0


@dataclass
class RiskDecision:
    allowed: bool
    reasons: list[str] = field(default_factory=list)
    open_r_before: float = 0.0
    open_r_after: float = 0.0
    cluster_r_after: float = 0.0
    total_notional_after: float = 0.0
    effective_leverage_after: float = 0.0


# Basit varsayılan korelasyon kümeleri. Bilinmeyen semboller kendi kümesine düşer.
DEFAULT_CLUSTERS = {
    "BTCUSDT": "majors", "ETHUSDT": "majors",
    "SOLUSDT": "l1", "AVAXUSDT": "l1", "ADAUSDT": "l1", "DOTUSDT": "l1",
    "ARBUSDT": "l2", "OPUSDT": "l2", "STRKUSDT": "l2",
    "DOGEUSDT": "meme", "SHIBUSDT": "meme", "PEPEUSDT": "meme",
    "WIFUSDT": "meme", "BONKUSDT": "meme", "FLOKIUSDT": "meme",
}


def _risk_r(p, r_dolar: float) -> float:
    """Aktif pozisyonun stop riskini R cinsinden tahmin et.

    Portfoy motorunda standart işlem 1R, ancak karşı-trend/özel boyutlandırma
    için nominal pozisyon bilgisi tutulmadığından mevcut aktif pozisyon başına
    konservatif 1R kabul edilir.
    """
    return 1.0 if getattr(p, "durum", None) in ("Bekliyor", "Açık") else 0.0


def _poz_notional(p) -> float:
    """Pozisyon nesnesinde explicit notional varsa kullan; yoksa 0."""
    for ad in ("notional_usd", "poz_buyukluk_dolar", "pozisyon_dolar"):
        v = getattr(p, ad, None)
        if v is not None:
            try:
                return max(0.0, float(v))
            except (TypeError, ValueError):
                pass
    return 0.0


def _cluster(symbol: str, clusters: dict[str, str]) -> str:
    return clusters.get(symbol, symbol)


def evaluate_candidate(
    portfoy,
    *,
    symbol: str,
    candidate_r: float = 1.0,
    candidate_notional_usd: float = 0.0,
    equity_usd: float | None = None,
    limits: RiskLimits | None = None,
    clusters: dict[str, str] | None = None,
    tarih: str | None = None,
) -> RiskDecision:
    """Yeni işlem açılmadan önce portföy-level risk kontrolü yapar."""
    limits = limits or RiskLimits()
    clusters = clusters or DEFAULT_CLUSTERS
    aktif = list(getattr(portfoy, "aktif", []))
    r_dolar = float(getattr(portfoy, "r_dolar", 25.0) or 25.0)

    open_r = sum(_risk_r(p, r_dolar) for p in aktif)
    open_after = open_r + max(0.0, float(candidate_r))

    total_notional = sum(_poz_notional(p) for p in aktif) + max(0.0, float(candidate_notional_usd))
    lev = total_notional / equity_usd if equity_usd and equity_usd > 0 else 0.0

    aday_cluster = _cluster(symbol, clusters)
    cluster_r = max(0.0, float(candidate_r))
    for p in aktif:
        if _cluster(getattr(p, "sembol", ""), clusters) == aday_cluster:
            cluster_r += _risk_r(p, r_dolar)

    if tarih is None:
        tarih = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    gunluk_r = float(portfoy.gunluk_r(tarih)) if hasattr(portfoy, "gunluk_r") else 0.0

    nedenler: list[str] = []
    if len(aktif) + 1 > limits.max_positions:
        nedenler.append(f"maksimum aktif pozisyon ({limits.max_positions}) aşılıyor")
    if open_after > limits.max_open_r:
        nedenler.append(f"toplam açık risk {open_after:.2f}R > {limits.max_open_r:.2f}R")
    if total_notional > limits.max_notional_usd:
        nedenler.append(
            f"toplam notional ${total_notional:,.0f} > ${limits.max_notional_usd:,.0f}")
    if equity_usd and equity_usd > 0 and lev > limits.max_leverage:
        nedenler.append(f"efektif leverage {lev:.2f}x > {limits.max_leverage:.2f}x")
    if gunluk_r <= -abs(limits.daily_loss_r):
        nedenler.append(
            f"günlük zarar limiti tetiklenmiş ({gunluk_r:.2f}R <= -{abs(limits.daily_loss_r):.2f}R)")
    if cluster_r > limits.max_cluster_r:
        nedenler.append(
            f"korelasyon kümesi riski {cluster_r:.2f}R > {limits.max_cluster_r:.2f}R")

    return RiskDecision(
        allowed=not nedenler,
        reasons=nedenler,
        open_r_before=round(open_r, 3),
        open_r_after=round(open_after, 3),
        cluster_r_after=round(cluster_r, 3),
        total_notional_after=round(total_notional, 2),
        effective_leverage_after=round(lev, 3),
    )


def guarded_add(
    portfoy,
    *,
    symbol: str,
    interval: str,
    giris: float,
    stop: float,
    hedef: float,
    rr: float,
    kalite: str,
    guven: float,
    yon: str = "Long",
    candidate_r: float = 1.0,
    candidate_notional_usd: float = 0.0,
    equity_usd: float | None = None,
    limits: RiskLimits | None = None,
    clusters: dict[str, str] | None = None,
    zaman: str | None = None,
):
    """RiskGuard onaylarsa Portfoy.ekle çağır; (pozisyon, karar) döndür."""
    karar = evaluate_candidate(
        portfoy,
        symbol=symbol,
        candidate_r=candidate_r,
        candidate_notional_usd=candidate_notional_usd,
        equity_usd=equity_usd,
        limits=limits,
        clusters=clusters,
        tarih=(zaman or "")[:10] or None,
    )
    if not karar.allowed:
        return None, karar
    poz = portfoy.ekle(
        symbol, interval, giris, stop, hedef, rr, kalite, guven,
        yon=yon, zaman=zaman,
    )
    if poz is not None and candidate_notional_usd > 0:
        # Dataclass dinamik attribute kabul eder; mevcut JSON serializer asdict
        # bunu yazmaz. Bu alan runtime risk hesabında kullanılır, kalıcı modele
        # explicit alan eklemek ayrı migration olarak yapılabilir.
        setattr(poz, "notional_usd", float(candidate_notional_usd))
    return poz, karar
