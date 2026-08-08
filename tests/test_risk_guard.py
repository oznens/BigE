from types import SimpleNamespace

from miraz.risk_guard import RiskLimits, evaluate_candidate


class PF:
    def __init__(self, aktif=None, gunluk=-0.0, r_dolar=25.0):
        self.aktif = aktif or []
        self._gunluk = gunluk
        self.r_dolar = r_dolar

    def gunluk_r(self, tarih=None):
        return self._gunluk


def P(symbol, durum="Açık", notional=0):
    p = SimpleNamespace(sembol=symbol, durum=durum)
    p.notional_usd = notional
    return p


def test_total_open_r_limit_blocks_new_trade():
    pf = PF([P("BTCUSDT"), P("SOLUSDT"), P("XRPUSDT")])
    lim = RiskLimits(max_open_r=3.0, max_cluster_r=99, max_positions=10,
                     max_notional_usd=1e9, max_leverage=99, daily_loss_r=99)
    d = evaluate_candidate(pf, symbol="ETHUSDT", limits=lim)
    assert not d.allowed
    assert d.open_r_after == 4.0
    assert any("toplam açık risk" in r for r in d.reasons)


def test_daily_loss_lock_blocks_new_trade():
    pf = PF(gunluk=-3.2)
    lim = RiskLimits(daily_loss_r=3.0, max_open_r=99, max_cluster_r=99,
                     max_positions=99, max_notional_usd=1e9, max_leverage=99)
    d = evaluate_candidate(pf, symbol="BTCUSDT", limits=lim, tarih="2026-01-01")
    assert not d.allowed
    assert any("günlük zarar limiti" in r for r in d.reasons)


def test_correlated_cluster_limit_blocks():
    pf = PF([P("BTCUSDT")])
    lim = RiskLimits(max_cluster_r=1.5, max_open_r=99, max_positions=99,
                     max_notional_usd=1e9, max_leverage=99, daily_loss_r=99)
    d = evaluate_candidate(pf, symbol="ETHUSDT", candidate_r=1.0, limits=lim)
    assert not d.allowed
    assert d.cluster_r_after == 2.0
    assert any("korelasyon kümesi" in r for r in d.reasons)


def test_notional_and_leverage_limits_block():
    pf = PF([P("BTCUSDT", notional=4000)])
    lim = RiskLimits(max_notional_usd=7000, max_leverage=1.2,
                     max_open_r=99, max_cluster_r=99, max_positions=99,
                     daily_loss_r=99)
    d = evaluate_candidate(pf, symbol="XRPUSDT", candidate_notional_usd=4000,
                           equity_usd=5000, limits=lim)
    assert not d.allowed
    assert d.total_notional_after == 8000
    assert d.effective_leverage_after == 1.6
    assert any("notional" in r for r in d.reasons)
    assert any("leverage" in r for r in d.reasons)


def test_candidate_allowed_inside_limits():
    pf = PF([P("BTCUSDT", notional=2000)], gunluk=-0.5)
    lim = RiskLimits(max_open_r=4, max_positions=6, max_notional_usd=10000,
                     max_leverage=3, daily_loss_r=3, max_cluster_r=2)
    d = evaluate_candidate(pf, symbol="SOLUSDT", candidate_notional_usd=1500,
                           equity_usd=5000, limits=lim)
    assert d.allowed
    assert d.open_r_after == 2.0
    assert d.cluster_r_after == 1.0
