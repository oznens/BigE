#!/usr/bin/env python3
"""GitHub Pages canlı taramasına doğrulanmış edge filtresini uygular.

Bu wrapper, çekirdek radarın güvenlik/HTF/Late/çiğnenmiş-bölge kurallarını
DEĞİŞTİRMEZ. Yalnız radarın zaten `Trade` dediği adayları geçmiş doğrulanmış
işlem verisinden çıkan daha seçici kuralla yeniden sınıflandırır:

  * Trade: 15m + Price Action + stop mesafesi %2..%3
  * Premium: yukarıdaki koşullara ek olarak kalite A+
  * Diğer eski Trade'ler: Watch (izlenmeye devam eder, portföye girmez)

Elenen/Skip/Watch adayları asla bu katman tarafından Trade'e yükseltilmez.
Böylece veri filtresi, temel risk/güvenlik kontrollerini bypass edemez.
"""
from __future__ import annotations

import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "src"))
sys.path.insert(0, str(KOK / "backtest"))

import statik_site  # noqa: E402
import miraz.gozlemci as gozlemci_mod  # noqa: E402
from miraz.radar import radar_tara as _cekirdek_radar_tara  # noqa: E402

STOP_MIN_PCT = 2.0
STOP_MAX_PCT = 3.0
EDGE_TF = "15m"
EDGE_KAYNAK = "Price Action"


def _stop_pct(satir) -> float | None:
    giris = getattr(satir, "giris", None)
    stop = getattr(satir, "stop", None)
    if giris is None or stop is None or giris <= 0:
        return None
    return 100.0 * abs(float(giris) - float(stop)) / float(giris)


def _edge_uygula(rapor):
    """Yalnız mevcut Trade satırlarını doğrulanmış filtreyle daralt."""
    for s in rapor.satirlar:
        if s.kategori != "Trade":
            continue

        sp = _stop_pct(s)
        uygun = (
            s.interval == EDGE_TF
            and s.kaynak == EDGE_KAYNAK
            and sp is not None
            and STOP_MIN_PCT <= sp <= STOP_MAX_PCT
        )

        if uygun:
            premium = str(getattr(s, "kalite", "")).strip() == "A+"
            etiket = "⭐ PREMIUM · doğrulanmış edge" if premium else "✅ doğrulanmış edge"
            detay = f"15m PA · stop %{sp:.2f}"
            s.not_ = f"{etiket} · {detay}" + (f" · {s.not_}" if s.not_ else "")
        else:
            neden = []
            if s.interval != EDGE_TF:
                neden.append(f"TF {s.interval}≠15m")
            if s.kaynak != EDGE_KAYNAK:
                neden.append(f"kaynak {s.kaynak}≠PA")
            if sp is None:
                neden.append("stop mesafesi yok")
            elif not (STOP_MIN_PCT <= sp <= STOP_MAX_PCT):
                neden.append(f"stop %{sp:.2f} ∉ [%2,%3]")
            s.kategori = "Watch"
            s.kaynak = "Filtered"
            ek = ", ".join(neden) or "edge filtresi"
            s.not_ = f"Veri filtresi → Watch ({ek})" + (f" · {s.not_}" if s.not_ else "")
    return rapor


def radar_tara_filtreli(*args, **kwargs):
    return _edge_uygula(_cekirdek_radar_tara(*args, **kwargs))


# Gozlemci modülü radar_tara'yı import-time'da bağladığı için wrapper'ı burada
# enjekte ediyoruz. Gozlemci.dongu() böylece portföye yalnız filtre sonrası
# kategori=Trade kalan adayları ekler.
gozlemci_mod.radar_tara = radar_tara_filtreli


if __name__ == "__main__":
    statik_site.main()
