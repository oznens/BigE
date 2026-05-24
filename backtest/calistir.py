"""İlk gerçek backtest: BTCUSDT 4h, son 3 yıl."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from bige.backtest import BacktestKonfig, calistir
from bige.strateji import StratejiParams
from bige.veri import indir_vision_aralik, kaydet, yukle

VERI_KLASOR = Path("data")


def veri_hazirla(sembol: str, aralik: str, baslangic: str, bitis: str | None = None) -> pd.DataFrame:
    yol = VERI_KLASOR / f"{sembol}_{aralik}.parquet"
    if yol.exists():
        df = yukle(sembol, aralik, VERI_KLASOR)
        bas_ts = pd.Timestamp(baslangic, tz="Europe/Istanbul")
        if df.index.min() <= bas_ts:
            return df
    df = indir_vision_aralik(sembol, aralik, baslangic, bitis)
    kaydet(df, sembol, aralik, VERI_KLASOR)
    return df


def main():
    sembol = "BTCUSDT"
    aralik = "4h"
    baslangic = "2022-01-01"
    bitis = None  # bugüne kadar

    print(f"Veri çekiliyor: {sembol} {aralik} {baslangic} → {bitis or 'bugün'}")
    df = veri_hazirla(sembol, aralik, baslangic, bitis)
    print(f"  {len(df)} mum, ilk: {df.index.min()}, son: {df.index.max()}")

    p = StratejiParams(
        allow_long=True,
        allow_short=True,
        risk_per_trade_pct=1.0,
    )
    k = BacktestKonfig(
        baslangic_bakiyesi=10_000.0,
        komisyon_bps=4.0,   # Binance futures taker ~%0.04
        slippage_bps=2.0,
    )

    print("Backtest çalışıyor...")
    sonuc = calistir(df, p, k)
    ist = sonuc.istatistikler()

    print("\n=== Sonuçlar ===")
    print(json.dumps(ist, indent=2, ensure_ascii=False))
    print(f"\nSon bakiye: {sonuc.bakiye_serisi.iloc[-1]:,.2f} USDT")
    print(f"Getiri:     %{(sonuc.bakiye_serisi.iloc[-1] / k.baslangic_bakiyesi - 1) * 100:,.2f}")

    # Buy & hold karşılaştırma
    bh = df["close"].iloc[-1] / df["close"].iloc[0]
    print(f"Buy&hold:   %{(bh - 1) * 100:,.2f}")

    # Trade detaylarını CSV'ye kaydet
    cikti_klasor = Path("backtest/results")
    cikti_klasor.mkdir(parents=True, exist_ok=True)
    trades_df = pd.DataFrame([{
        "yon": t.yon.name,
        "giris": t.giris_zamani,
        "cikis": t.cikis_zamani,
        "giris_fiyat": t.giris_fiyati,
        "cikis_fiyat": t.cikis_fiyati,
        "miktar": t.miktar,
        "pnl_net": t.pnl_net,
        "sebep": t.sebep,
    } for t in sonuc.trades])
    trades_df.to_csv(cikti_klasor / f"trades_{sembol}_{aralik}.csv", index=False)
    sonuc.bakiye_serisi.to_csv(cikti_klasor / f"bakiye_{sembol}_{aralik}.csv")
    print(f"\nÇıktılar: {cikti_klasor}/")


if __name__ == "__main__":
    main()
