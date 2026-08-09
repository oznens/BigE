#!/usr/bin/env python3
"""GitHub Pages canlı taramasına doğrulanmış edge + Miraz tetik filtresi uygular.

Katman sırası:
  1) Çekirdek radarın HTF/Late/stop-çiğnenmiş güvenlik kuralları aynen kalır.
  2) Geçmiş doğrulanmış işlem verisi: 15m + Price Action + stop %2..%3.
  3) @tradermiraz arşivinden damıtılan operasyonel kural: trend kırılımı/onay
     (Shear/MSB) gelmeden setup gerçek Trade sayılmaz; Watch'ta bekler.

1:2 hedef arşiv metodolojisinde ana kuraldır; ancak mevcut canlı performans
serisi 1R hedefle oluştuğu için hedefi körlemesine 2R'ye çevirmiyoruz. Bunun
yerine her doğrulanmış setup için 2R projeksiyonunu notta yayınlıyoruz; yeni
OHLC yol verisi biriktikçe 1R/2R yönetimi OOS olarak karşılaştırılabilir.
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
MIRAZ_TETIK = "Shear"  # trend kırılımı / MSB


def _stop_pct(satir) -> float | None:
    giris = getattr(satir, "giris", None)
    stop = getattr(satir, "stop", None)
    if giris is None or stop is None or giris <= 0:
        return None
    return 100.0 * abs(float(giris) - float(stop)) / float(giris)


def _hedef_2r(satir) -> float | None:
    """Miraz minimum 1:2 için yalnız gölge/projeksiyon hedefi üret."""
    giris = getattr(satir, "giris", None)
    stop = getattr(satir, "stop", None)
    if giris is None or stop is None:
        return None
    giris, stop = float(giris), float(stop)
    risk = abs(giris - stop)
    if risk <= 0:
        return None
    return giris - 2.0 * risk if getattr(satir, "taraf", "Long") == "Short" \
        else giris + 2.0 * risk


def _miraz_tetik_var(satir) -> bool:
    """Arşivdeki yeşil-daire/trend-kırılımı onayını Shear/MSB ile temsil et."""
    return MIRAZ_TETIK in set(getattr(satir, "konseptler", None) or [])


def _edge_uygula(rapor):
    """Yalnız mevcut Trade satırlarını veri + Miraz tetik filtresiyle daralt."""
    for s in rapor.satirlar:
        if s.kategori != "Trade":
            continue

        sp = _stop_pct(s)
        veri_uygun = (
            s.interval == EDGE_TF
            and s.kaynak == EDGE_KAYNAK
            and sp is not None
            and STOP_MIN_PCT <= sp <= STOP_MAX_PCT
        )
        tetik = _miraz_tetik_var(s)

        if veri_uygun and tetik:
            premium = str(getattr(s, "kalite", "")).strip() == "A+"
            etiket = "⭐ PREMIUM · edge + Miraz tetik" if premium else "✅ edge + Miraz tetik"
            h2 = _hedef_2r(s)
            proj = f" · Miraz 2R proj. {h2:.6g}" if h2 is not None else ""
            detay = f"15m PA · stop %{sp:.2f} · MSB/Shear onaylı{proj}"
            s.not_ = f"{etiket} · {detay}" + (f" · {s.not_}" if s.not_ else "")
            continue

        neden = []
        if s.interval != EDGE_TF:
            neden.append(f"TF {s.interval}≠15m")
        if s.kaynak != EDGE_KAYNAK:
            neden.append(f"kaynak {s.kaynak}≠PA")
        if sp is None:
            neden.append("stop mesafesi yok")
        elif not (STOP_MIN_PCT <= sp <= STOP_MAX_PCT):
            neden.append(f"stop %{sp:.2f} ∉ [%2,%3]")
        if veri_uygun and not tetik:
            neden.append("Miraz tetik/MSB henüz yok")

        s.kategori = "Watch"
        s.kaynak = "Filtered"
        ek = ", ".join(neden) or "edge/Miraz filtresi"
        s.not_ = f"Onay bekle → Watch ({ek})" + (f" · {s.not_}" if s.not_ else "")
    return rapor


def radar_tara_filtreli(*args, **kwargs):
    return _edge_uygula(_cekirdek_radar_tara(*args, **kwargs))


# Gozlemci modülü radar_tara'yı import-time'da bağladığı için wrapper'ı burada
# enjekte ediyoruz. Gozlemci.dongu() böylece yalnız filtre sonrası Trade'leri
# paper portföye ekler.
gozlemci_mod.radar_tara = radar_tara_filtreli


if __name__ == "__main__":
    statik_site.main()
