#!/usr/bin/env python3
"""GitHub Pages canlı taramasına doğrulanmış edge + Miraz işlem yönetimi uygular.

Katman sırası:
  1) Çekirdek radarın HTF/Late/stop-çiğnenmiş güvenlik kuralları aynen kalır.
  2) Geçmiş doğrulanmış işlem verisi: 15m + Price Action + stop %2..%3.
  3) @tradermiraz arşivinden damıtılan operasyonel kural: trend kırılımı/onay
     (Shear/MSB) gelmeden setup gerçek Trade sayılmaz; Watch'ta bekler.
  4) Canlı paper-trade yönetimi: 1R'de %65 kâr al, kalan %35 için stopu
     breakeven'a çek, 2R'ye taşı.

Yönetim mevcut Pozisyon şemasını değiştirmez. TP1 sonrası durum mevcut alanlarda
saklanır: r_sonuc=+0.65R, stop=giriş (BE), hedef=2R, rr=1.35. Böylece Pages
snapshot'ları arasında state kaybolmaz ve eski portfoy.json dosyaları yüklenir.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "src"))
sys.path.insert(0, str(KOK / "backtest"))

import statik_site  # noqa: E402
import miraz.gozlemci as gozlemci_mod  # noqa: E402
from miraz.portfoy import Portfoy  # noqa: E402
from miraz.radar import radar_tara as _cekirdek_radar_tara  # noqa: E402

STOP_MIN_PCT = 2.0
STOP_MAX_PCT = 3.0
EDGE_TF = "15m"
EDGE_KAYNAK = "Price Action"
MIRAZ_TETIK = "Shear"  # trend kırılımı / MSB
TP1_PAY = 0.65
KALAN_PAY = 1.0 - TP1_PAY
TP2_R = 2.0
TP2_TOPLAM_R = round(TP1_PAY * 1.0 + KALAN_PAY * TP2_R, 2)  # 1.35R


def _stop_pct(satir) -> float | None:
    giris = getattr(satir, "giris", None)
    stop = getattr(satir, "stop", None)
    if giris is None or stop is None or giris <= 0:
        return None
    return 100.0 * abs(float(giris) - float(stop)) / float(giris)


def _hedef_2r(satir) -> float | None:
    giris = getattr(satir, "giris", None)
    stop = getattr(satir, "stop", None)
    if giris is None or stop is None:
        return None
    giris, stop = float(giris), float(stop)
    risk = abs(giris - stop)
    if risk <= 0:
        return None
    return giris - TP2_R * risk if getattr(satir, "taraf", "Long") == "Short" \
        else giris + TP2_R * risk


def _miraz_tetik_var(satir) -> bool:
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
            yonetim = (
                f"TP1 1R'de %{TP1_PAY*100:.0f} → BE → kalan %{KALAN_PAY*100:.0f} 2R"
            )
            proj = f" · TP2 {h2:.6g}" if h2 is not None else ""
            detay = f"15m PA · stop %{sp:.2f} · MSB/Shear onaylı · {yonetim}{proj}"
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


def _utc_ts(v):
    ts = pd.Timestamp(v)
    if ts.tzinfo is None:
        return ts.tz_localize("UTC")
    return ts.tz_convert("UTC")


def _bar_zamani(idx) -> str:
    try:
        return _utc_ts(idx).isoformat()
    except Exception:
        return str(idx)


def _miraz_yonetimli_guncelle(self: Portfoy, sembol: str, interval: str,
                               df: pd.DataFrame, max_bekleme: int = 24) -> list:
    """Canlı paper portföy: TP1 %65 @1R → BE → kalan %35 @2R.

    Muhafazakâr OHLC kuralı korunur:
      * TP1 öncesi aynı mum stop+TP görürse STOP.
      * TP1 sonrası aynı mum BE+TP2 görürse BE kabul edilir; kilitli +0.65R korunur.

    TP1 state'i Pozisyon'un mevcut alanlarında kalıcıdır:
      Açık + r_sonuc=0.65 + stop=giriş + hedef=2R + rr=1.35.
    """
    aktif = [p for p in self.pozisyonlar
             if p.sembol == sembol and p.interval == interval
             and p.durum in ("Bekliyor", "Açık")]
    if not aktif or df is None or len(df) == 0:
        return []

    degisenler = []
    son_fiyat = float(df["close"].iloc[-1])

    for poz in aktif:
        poz.son_fiyat = son_fiyat
        try:
            baslangic = _utc_ts(poz.son_kontrol_zaman) if poz.son_kontrol_zaman else None
            alt_df = df[df.index > baslangic] if baslangic is not None else df
        except Exception:
            alt_df = df
        if alt_df.empty:
            continue

        low = alt_df["low"].to_numpy()
        high = alt_df["high"].to_numpy()
        idx = alt_df.index
        short = poz.yon == "Short"
        try:
            acilis_ts = _utc_ts(poz.acilis_zaman) if poz.acilis_zaman else None
        except Exception:
            acilis_ts = None

        kapanis_oldu = False
        for j in range(len(alt_df)):
            bar_ts = _bar_zamani(idx[j])

            if poz.durum == "Bekliyor":
                if acilis_ts is not None:
                    try:
                        gecen_j = int(((df.index > acilis_ts)
                                       & (df.index <= _utc_ts(idx[j]))).sum())
                    except Exception:
                        gecen_j = 0
                    if gecen_j > max_bekleme:
                        poz.durum = "Expired"
                        poz.r_sonuc = 0.0
                        poz.kapanis_zaman = bar_ts
                        degisenler.append(poz)
                        kapanis_oldu = True
                        break
                doldu = (high[j] >= poz.giris) if short else (low[j] <= poz.giris)
                if doldu:
                    poz.durum = "Açık"
                    degisenler.append(poz)

            if poz.durum != "Açık":
                continue

            # TP1 alınmış state: r_sonuc pozitif ve stop BE'de.
            tp1_alindi = (
                poz.r_sonuc > 0
                and abs(float(poz.stop) - float(poz.giris)) <= max(abs(float(poz.giris)) * 1e-9, 1e-12)
            )

            if tp1_alindi:
                be_vurdu = (high[j] >= poz.stop) if short else (low[j] <= poz.stop)
                tp2_vurdu = (low[j] <= poz.hedef) if short else (high[j] >= poz.hedef)
                # Aynı mumda BE + TP2 belirsizse muhafazakâr BE.
                if be_vurdu:
                    poz.durum = "TP"
                    poz.r_sonuc = TP1_PAY
                    poz.kapanis_zaman = bar_ts
                    degisenler.append(poz)
                    kapanis_oldu = True
                    break
                if tp2_vurdu:
                    poz.durum = "TP"
                    poz.r_sonuc = TP2_TOPLAM_R
                    poz.kapanis_zaman = bar_ts
                    degisenler.append(poz)
                    kapanis_oldu = True
                    break
                continue

            # TP1 öncesi: mevcut stop ve 1R hedef.
            stop_vurdu = (high[j] >= poz.stop) if short else (low[j] <= poz.stop)
            tp1_vurdu = (low[j] <= poz.hedef) if short else (high[j] >= poz.hedef)
            if stop_vurdu:  # aynı mum stop+TP1 → muhafazakâr STOP
                poz.durum = "STOP"
                poz.r_sonuc = -1.0
                poz.kapanis_zaman = bar_ts
                degisenler.append(poz)
                kapanis_oldu = True
                break

            if tp1_vurdu:
                eski_stop = float(poz.stop)
                risk = abs(float(poz.giris) - eski_stop)
                if risk <= 0:
                    poz.durum = "TP"
                    poz.r_sonuc = 1.0
                    poz.kapanis_zaman = bar_ts
                    degisenler.append(poz)
                    kapanis_oldu = True
                    break

                hedef2 = (float(poz.giris) - TP2_R * risk if short
                          else float(poz.giris) + TP2_R * risk)
                # %65 kâr realize; kalan pozisyon risksiz.
                poz.r_sonuc = TP1_PAY
                poz.stop = float(poz.giris)
                poz.hedef = round(hedef2, 10)
                poz.rr = TP2_TOPLAM_R

                # Stop bu mumda vurulmadığı için, 2R de aynı yönde görüldüyse
                # fiyat yolu TP1'den geçmek zorundadır; aynı mum TP2 kabul edilir.
                tp2_ayni_bar = (low[j] <= poz.hedef) if short else (high[j] >= poz.hedef)
                if tp2_ayni_bar:
                    poz.durum = "TP"
                    poz.r_sonuc = TP2_TOPLAM_R
                    poz.kapanis_zaman = bar_ts
                    degisenler.append(poz)
                    kapanis_oldu = True
                    break
                # Açık kalır; partial state JSON'a mevcut alanlarla yazılır.

        if not kapanis_oldu:
            poz.son_kontrol_zaman = _bar_zamani(idx[-1])
            if poz.durum == "Bekliyor" and poz.acilis_zaman:
                try:
                    acilis = _utc_ts(poz.acilis_zaman)
                    gecen = int((df.index > acilis).sum())
                except Exception:
                    gecen = 0
                if gecen >= max_bekleme:
                    poz.durum = "Expired"
                    poz.r_sonuc = 0.0
                    poz.kapanis_zaman = _bar_zamani(idx[-1])
                    degisenler.append(poz)

    return degisenler


# Gozlemci modülü radar_tara'yı import-time'da bağladığı için wrapper'ı burada
# enjekte ediyoruz. Portfoy methodu da sınıf üzerinde değiştirilir; statik_site
# ve Gozlemci'nin daha önce import ettiği Portfoy referansları aynı sınıftır.
gozlemci_mod.radar_tara = radar_tara_filtreli
Portfoy.guncelle = _miraz_yonetimli_guncelle


if __name__ == "__main__":
    statik_site.main()
