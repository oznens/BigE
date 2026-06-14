"""Session Trend backtest'ini çalıştırır ve al-tut ile karşılaştırır.

Kullanım:
    python backtest/calistir.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# src/ yolunu ekle (pip install -e . yapılmadıysa da çalışsın)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from walter import backtest as bt          # noqa: E402
from walter import strateji as st           # noqa: E402
from walter import veri as vr               # noqa: E402


def main() -> None:
    print("Veri yükleniyor (cache yoksa indiriliyor)...")
    df = vr.indir(symbol="BTCUSDT", interval="1h", gun=1500)
    print(f"  {len(df):,} mum | {df.index[0].date()} → {df.index[-1].date()}\n")

    p = st.SessionTrendParams()
    sinyal = st.uret(df, p)

    strat = bt.calistir(sinyal, komisyon=0.0006)
    bh = bt.buy_hold(df)

    print("=" * 60)
    print("SESSION TREND (strateji)")
    print("=" * 60)
    print(strat.ozet())
    print()
    print("=" * 60)
    print("BUY & HOLD (karşılaştırma)")
    print("=" * 60)
    print(bh.ozet())
    print()

    # Kıyas özeti
    s, b = strat.metrikler, bh.metrikler
    print("=" * 60)
    print("KIYAS")
    print("=" * 60)
    print(f"  Sharpe       : {s['sharpe']:.2f}  vs  {b['sharpe']:.2f}  (al-tut)")
    print(f"  Max drawdown : {s['max_drawdown']:.1%}  vs  {b['max_drawdown']:.1%}")
    print(f"  CAGR         : {s['cagr']:+.1%}  vs  {b['cagr']:+.1%}")

    # Raporu kaydet
    rapor_dir = Path(__file__).resolve().parent / "raporlar"
    rapor_dir.mkdir(exist_ok=True)
    strat.equity.to_frame("strateji").join(
        bh.equity.rename("buy_hold")
    ).to_csv(rapor_dir / "equity.csv")
    print(f"\nEquity eğrisi kaydedildi: {rapor_dir / 'equity.csv'}")


if __name__ == "__main__":
    main()
