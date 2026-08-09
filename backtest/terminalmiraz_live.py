#!/usr/bin/env python3
"""terminalMiraz kanıtlı canlı Pages giriş noktası.

Asıl klon davranışı `live_edge_filter.py` içindedir:
- PA ve Harmonik ayrı yollar
- 15m/30m/1h/2h/4h
- MSB/Shear tetik
- Harmonik pattern/PRZ
- 1:1 Result Journal
- STOP = wick değil kapanış invalidasyonu
- Güvenli/Dengeli/Riskli senaryo hedefleri = 1R/2R/3.5R

Bu dosya yalnız GitHub Pages workflow giriş noktasıdır; ikinci bir eski risk
patch'i uygulamaz. Böylece canlı kod ile terminalMiraz klon katmanı tek kaynakta
kalır.
"""
from __future__ import annotations

import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "src"))
sys.path.insert(0, str(KOK / "backtest"))

import live_edge_filter as edge  # noqa: F401,E402
import statik_site  # noqa: E402


if __name__ == "__main__":
    statik_site.main()
