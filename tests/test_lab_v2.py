import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz.lab_v2 import ExecutionCosts, _maliyet_r, _ust_pencere


def test_execution_cost_roundtrip_bps():
    c = ExecutionCosts(fee_bps=4, slippage_bps=2, funding_bps=3)
    assert c.roundtrip_bps == pytest.approx(15.0)


def test_cost_converts_to_r_by_stop_distance():
    # 100 -> 99 = %1 risk. 12 bps round-trip = %0.12 = 0.12R.
    c = ExecutionCosts(fee_bps=4, slippage_bps=2, funding_bps=0)
    assert _maliyet_r(100.0, 99.0, c) == pytest.approx(0.12)


def test_zero_cost_keeps_gross_r():
    c = ExecutionCosts(fee_bps=0, slippage_bps=0, funding_bps=0)
    assert _maliyet_r(100.0, 98.0, c) == 0.0


def test_htf_window_is_cut_at_decision_time():
    idx = pd.date_range("2026-01-01", periods=5, freq="4h", tz="UTC")
    df = pd.DataFrame({"close": [1, 2, 3, 4, 5]}, index=idx)
    cut = _ust_pencere(df, idx[2])
    assert len(cut) == 3
    assert cut.index[-1] == idx[2]
