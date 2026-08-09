#!/usr/bin/env python3
"""terminalMiraz kanıtlı canlı Pages katmanı.

Bu giriş noktası, mevcut PA/Harmonik + MSB/Shear Trade kapısını korur fakat
kanıtsız sabit %65 TP1 payını ana performans hesabından çıkarır.

Arşiv kanıtı (2025-10-16 ve 2026-05-29):
- terminalMiraz'da 1:1 risk yönetimi ana modlardan biridir.
- +1R sonrası Miraz kişisel yönetiminde risk azaltma/kar alma + stopu girişe
  çekme davranışı vardır, ancak sabit kar-al yüzdesi yayınlarda tanımlı değildir.
- Orta Risk ve Yüksek Risk modları vardır; oranları burada uydurulmaz.

Bu yüzden temiz canlı benchmark = 1R hedef / 1R stop. Orta/Yüksek Risk ve
partial-BE ileride ayrı, kanıtlı alanlar olarak ölçülecektir.
"""
from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "src"))
sys.path.insert(0, str(KOK / "backtest"))

import live_edge_filter as edge  # noqa: E402
import statik_site  # noqa: E402
import miraz.gozlemci as gozlemci_mod  # noqa: E402

# Bu kanıtlı 1:1 benchmark sürümünden önceki state'i karıştırma.
# Türkiye: 2026-08-09 15:56 +03:00
edge.ISTATISTIK_BASELINE_UTC = "2026-08-09T12:56:00+00:00"
edge._BASELINE_TS = datetime.fromisoformat(edge.ISTATISTIK_BASELINE_UTC)

# live_edge_filter import sırasında TP1→BE→TP2 patch'i kurar. Ana benchmarkta
# bunu geri alıp çekirdek 1:1 Portfoy.guncelle davranışını kullanıyoruz.
gozlemci_mod.Portfoy.guncelle = edge._ORJ_GUNCELLE


def _notu_kanitli_yonetime_cevir(not_: str) -> str:
    """Eski wrapper'ın %65/2R açıklamasını kanıtlı 1:1 benchmark etiketiyle değiştir."""
    if not not_:
        return not_
    # ' · yönetim: ...' bölümünü bir sonraki eski nota kadar sadeleştir.
    s = re.sub(
        r" · yönetim: 1R'de %\d+ ölçüm-paylı kar → BE → 2R(?: · TP2 [^·]+)?",
        " · yönetim: 1:1 ana benchmark (Orta/Yüksek Risk ayrı izlenecek)",
        not_,
    )
    return s


def radar_tara_kanitli(*args, **kwargs):
    rapor = edge.radar_tara_filtreli(*args, **kwargs)
    for s in rapor.satirlar:
        s.not_ = _notu_kanitli_yonetime_cevir(getattr(s, "not_", ""))
    return rapor


# Gözlemci döngüsü yalnız kanıtlı Trade kapısını görsün.
gozlemci_mod.radar_tara = radar_tara_kanitli

# statik_site._onceki_state zaten edge._onceki_state_temiz'e patch'lidir ve
# yukarıdaki güncel _BASELINE_TS globalini kullanır.

if __name__ == "__main__":
    statik_site.main()
