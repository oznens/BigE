"""Edge teşhisi — varsaymadan ÖLÇ.

İki soruyu veriyle yanıtlar:
  1. Haftanın hangi saatlerinde (ET) BTC saatlik getirileri pozitif/negatif?
  2. "Monday Asia Open" penceresi (Pazar 19:00 ET → Pazartesi 18:00 ET)
     gerçekten geri kalan saatlerden daha mı iyi?
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from walter import veri as vr          # noqa: E402
from walter.zaman import ET, saat_ozellikleri  # noqa: E402


def main() -> None:
    df = vr.indir(symbol="BTCUSDT", interval="1h", gun=1500)
    ret = df["close"].pct_change()
    ozk = saat_ozellikleri(df.index, tz=ET)

    g = pd.DataFrame({"ret": ret, "hafta_saati": ozk["hafta_saati"],
                      "gun": ozk["haftanin_gunu"], "saat": ozk["saat"]}).dropna()

    # Günlük ortalama saatlik getiri (bps)
    print("=" * 50)
    print("HAFTANIN GÜNÜNE GÖRE ort. saatlik getiri (bps, ET)")
    print("=" * 50)
    gun_adi = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
    gunluk = g.groupby("gun")["ret"].mean() * 1e4
    for i, v in gunluk.items():
        print(f"  {gun_adi[i]} : {v:+6.2f} bps")

    # Edge penceresi vs dışı
    bas, bit = 163, 18  # Pazar 19:00 ET → Pazartesi 18:00 ET (sarmalı)
    hs = g["hafta_saati"]
    edge_mask = (hs >= bas) | (hs <= bit)
    edge_ret = g.loc[edge_mask, "ret"]
    disi_ret = g.loc[~edge_mask, "ret"]

    print("\n" + "=" * 50)
    print("EDGE PENCERESİ (Pazar 19:00 → Pzt 18:00 ET)")
    print("=" * 50)
    print(f"  Pencere içi  : {edge_ret.mean()*1e4:+6.2f} bps/saat "
          f"| n={len(edge_ret):,} | poz.oran={ (edge_ret>0).mean():.1%}")
    print(f"  Pencere dışı : {disi_ret.mean()*1e4:+6.2f} bps/saat "
          f"| n={len(disi_ret):,} | poz.oran={ (disi_ret>0).mean():.1%}")

    # Basit t-testi (Welch yaklaşık)
    m1, m2 = edge_ret.mean(), disi_ret.mean()
    s1, s2 = edge_ret.std(), disi_ret.std()
    n1, n2 = len(edge_ret), len(disi_ret)
    t = (m1 - m2) / np.sqrt(s1**2 / n1 + s2**2 / n2)
    print(f"\n  Fark t-istatistiği ≈ {t:.2f} "
          f"({'anlamlı' if abs(t) > 2 else 'anlamsız'}, |t|>2 eşik)")

    # En iyi / en kötü hafta-saatleri
    print("\n" + "=" * 50)
    print("EN İYİ 8 HAFTA-SAATİ (ET)")
    print("=" * 50)
    saatlik = g.groupby("hafta_saati")["ret"].mean() * 1e4
    for hsi, v in saatlik.sort_values(ascending=False).head(8).items():
        print(f"  {gun_adi[hsi//24]} {hsi%24:02d}:00 ET : {v:+6.2f} bps")
    print("\nEN KÖTÜ 8 HAFTA-SAATİ (ET)")
    for hsi, v in saatlik.sort_values().head(8).items():
        print(f"  {gun_adi[hsi//24]} {hsi%24:02d}:00 ET : {v:+6.2f} bps")


if __name__ == "__main__":
    main()
