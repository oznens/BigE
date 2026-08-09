#!/usr/bin/env python3
"""GitHub Pages canlı taramasına doğrulanmış edge + Miraz tetik/yönetim filtresi uygular.

Katman sırası:
  1) Çekirdek radarın HTF/Late/stop-çiğnenmiş güvenlik kuralları aynen kalır.
  2) Geçmiş doğrulanmış işlem verisi: 15m + Price Action + stop %2..%3.
  3) @tradermiraz arşivinden damıtılan operasyonel kural: trend kırılımı/onay
     (Shear/MSB) gelmeden setup gerçek Trade sayılmaz; Watch'ta bekler.
  4) Canlı paper yönetimi: TP1=1R'de %65 kar al, kalan %35'i BE stop ile
     TP2=2R'ye taşı.
  5) İstatistik baseline: yeni Miraz yönetiminin devreye girdiği andan önceki
     kayıtlar canlı performans/state hesabından çıkarılır.

Baseline öncesi veri Git geçmişinde/önceki Pages deploylarında kaybolmuş sayılmaz;
yalnız yeni sistem performansını temiz ölçmek için canlı state'e taşınmaz.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
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

# Yeni TP1→BE→TP2 canlı yönetiminin devreye alındığı commit zamanı.
# Türkiye: 2026-08-09 14:14:38 +03:00
ISTATISTIK_BASELINE_UTC = "2026-08-09T11:14:38+00:00"
_BASELINE_TS = datetime.fromisoformat(ISTATISTIK_BASELINE_UTC)

# Miraz canlı pozisyon yönetimi
TP1_R = 1.0
TP1_PAY = 0.65
RUNNER_PAY = 1.0 - TP1_PAY
TP2_R = 2.0


def _parse_ts(v: str | None):
    if not v:
        return None
    try:
        s = str(v).replace("Z", "+00:00")
        d = datetime.fromisoformat(s)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc)
    except Exception:
        return None


def _baseline_sonrasi(v: str | None) -> bool:
    t = _parse_ts(v)
    return t is not None and t >= _BASELINE_TS


# ---------------------------------------------------------------------------
# Temiz istatistik baseline
# ---------------------------------------------------------------------------
_ORJ_ONCEKI_STATE = statik_site._onceki_state


def _onceki_state_temiz(cikti, onceki_url):
    """Pages state'ini yükle; yeni sistem öncesi kayıt/pozisyonları ayıkla."""
    defter, portfoy = _ORJ_ONCEKI_STATE(cikti, onceki_url)

    eski_kayit = len(defter.kayitlar)
    eski_poz = len(portfoy.pozisyonlar)

    defter.kayitlar = [
        k for k in defter.kayitlar
        if _baseline_sonrasi(getattr(k, "acilis_zaman", ""))
    ]
    portfoy.pozisyonlar = [
        p for p in portfoy.pozisyonlar
        if _baseline_sonrasi(getattr(p, "acilis_zaman", ""))
    ]

    # Sayaçları kalan temiz state'e göre yeniden kur.
    defter.id_sayac = max((getattr(k, "id", 0) for k in defter.kayitlar), default=0)
    portfoy.id_sayac = max((getattr(p, "id", -1) for p in portfoy.pozisyonlar), default=-1) + 1
    if not defter.kayitlar:
        defter.id_sayac = 0
        defter.tarama_turu = 0
        defter.toplam_tarama = 0
        defter.son_dongu = ""
    if not portfoy.pozisyonlar:
        portfoy.id_sayac = 0

    atilan_k = eski_kayit - len(defter.kayitlar)
    atilan_p = eski_poz - len(portfoy.pozisyonlar)
    if atilan_k or atilan_p:
        print(
            f"🧹 Yeni sistem baseline reset: {atilan_k} eski kayıt + "
            f"{atilan_p} eski pozisyon canlı istatistikten çıkarıldı · "
            f"başlangıç {ISTATISTIK_BASELINE_UTC}"
        )
    return defter, portfoy


# statik_site.uret() artık her tur temiz state'i kullanır.
statik_site._onceki_state = _onceki_state_temiz


# ---------------------------------------------------------------------------
# Edge + Miraz tetik filtresi
# ---------------------------------------------------------------------------
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
            proj = f" · TP2 {h2:.6g}" if h2 is not None else ""
            detay = (
                f"15m PA · stop %{sp:.2f} · MSB/Shear onaylı · "
                f"yönetim: 1R'de %{TP1_PAY*100:.0f} al → BE → 2R{proj}"
            )
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


# ---------------------------------------------------------------------------
# Canlı TP1 → BE → TP2 yönetimi
# ---------------------------------------------------------------------------
def _r_fiyat(poz, r: float) -> float:
    risk = abs(float(poz.giris) - float(poz.stop))
    if poz.yon == "Short":
        return float(poz.giris) - r * risk
    return float(poz.giris) + r * risk


def _tp1_alindi(poz) -> bool:
    # Eski JSON şemasını değiştirmeden marker'ı son_kontrol_zaman alanında değil,
    # pozisyon nesnesine runtime attribute olarak taşıyoruz; hedefin 2R'ye
    # çevrilmiş olması kalıcı marker görevi görür.
    try:
        return abs(float(poz.hedef) - _r_fiyat(poz, TP2_R)) <= max(abs(float(poz.giris)) * 1e-8, 1e-12) \
            and abs(float(poz.stop) - float(poz.giris)) <= max(abs(float(poz.giris)) * 1e-8, 1e-12)
    except Exception:
        return False


def _miraz_guncelle(orj_guncelle, self, sembol, interval, df, max_bekleme=24):
    """Aktif işlemleri Miraz TP1→BE→TP2 mantığıyla güncelle.

    Yeni sistem pozisyonlarında ilk hedef başlangıçta 1R'dir. 1R görüldüğünde
    işlem kapanmaz: +0.65R realize edilir, stop entry'ye çekilir, hedef 2R olur.
    Runner 2R görürse toplam +1.35R; BE'ye dönerse +0.65R ile kapanır.
    TP1 öncesi hard stop -1R'dir.
    """
    aktif = [p for p in self.pozisyonlar
             if p.sembol == sembol and p.interval == interval
             and p.durum in ("Bekliyor", "Açık")]
    if not aktif or df is None or df.empty:
        return []

    # Baseline öncesi pozisyon wrapper'da zaten ayıklanır. Burada yalnız yeni sistem.
    degisenler = []
    son_fiyat = float(df["close"].iloc[-1])

    for poz in aktif:
        poz.son_fiyat = son_fiyat
        if poz.son_kontrol_zaman:
            try:
                import pandas as pd
                baslangic = pd.Timestamp(poz.son_kontrol_zaman)
                baslangic = baslangic.tz_localize("UTC") if baslangic.tzinfo is None else baslangic.tz_convert("UTC")
                alt_df = df[df.index > baslangic]
            except Exception:
                alt_df = df
        else:
            alt_df = df
        if alt_df.empty:
            continue

        short = poz.yon == "Short"
        acilis_ts = None
        try:
            import pandas as pd
            acilis_ts = pd.Timestamp(poz.acilis_zaman)
            acilis_ts = acilis_ts.tz_localize("UTC") if acilis_ts.tzinfo is None else acilis_ts.tz_convert("UTC")
        except Exception:
            pass

        kapandi = False
        for ts, row in alt_df.iterrows():
            hi = float(row["high"]); lo = float(row["low"])

            if poz.durum == "Bekliyor":
                if acilis_ts is not None:
                    gecen = int(((df.index > acilis_ts) & (df.index <= ts)).sum())
                    if gecen > max_bekleme:
                        poz.durum = "Expired"; poz.r_sonuc = 0.0
                        poz.kapanis_zaman = ts.isoformat(); degisenler.append(poz)
                        kapandi = True; break
                doldu = hi >= poz.giris if short else lo <= poz.giris
                if doldu:
                    poz.durum = "Açık"; degisenler.append(poz)

            if poz.durum != "Açık":
                continue

            tp1_done = _tp1_alindi(poz)
            if not tp1_done:
                tp1 = _r_fiyat(poz, TP1_R)
                stop_hit = hi >= poz.stop if short else lo <= poz.stop
                tp1_hit = lo <= tp1 if short else hi >= tp1

                # Aynı mumda stop ve TP1 varsa muhafazakâr STOP.
                if stop_hit:
                    poz.durum = "STOP"; poz.r_sonuc = -1.0
                    poz.kapanis_zaman = ts.isoformat(); degisenler.append(poz)
                    kapandi = True; break
                if tp1_hit:
                    # %65 realize, kalan %35 risk-free runner.
                    poz.r_sonuc = round(TP1_PAY * TP1_R, 4)
                    poz.stop = float(poz.giris)
                    poz.hedef = round(_r_fiyat(poz, TP2_R), 10)
                    poz.rr = TP2_R
                    degisenler.append(poz)
                    # Aynı mum içinde TP2'yi saymıyoruz: mum içi sıra bilinmiyor.
                    # Runner değerlendirmesi bir sonraki mumdan başlar.
                    continue
            else:
                be_hit = hi >= poz.stop if short else lo <= poz.stop
                tp2_hit = lo <= poz.hedef if short else hi >= poz.hedef
                # Aynı mumda BE ve TP2 varsa muhafazakâr BE.
                if be_hit:
                    poz.durum = "TP"
                    poz.r_sonuc = round(TP1_PAY * TP1_R, 4)  # +0.65R
                    poz.kapanis_zaman = ts.isoformat(); degisenler.append(poz)
                    kapandi = True; break
                if tp2_hit:
                    poz.durum = "TP"
                    poz.r_sonuc = round(TP1_PAY * TP1_R + RUNNER_PAY * TP2_R, 4)  # +1.35R
                    poz.kapanis_zaman = ts.isoformat(); degisenler.append(poz)
                    kapandi = True; break

        if not kapandi:
            poz.son_kontrol_zaman = alt_df.index[-1].isoformat()

    return degisenler


_ORJ_GUNCELLE = gozlemci_mod.Portfoy.guncelle


def _guncelle_patch(self, sembol, interval, df, max_bekleme=24):
    return _miraz_guncelle(_ORJ_GUNCELLE, self, sembol, interval, df, max_bekleme)


gozlemci_mod.Portfoy.guncelle = _guncelle_patch

# Gozlemci modülü radar_tara'yı import-time'da bağladığı için wrapper'ı burada
# enjekte ediyoruz. Gozlemci.dongu() böylece yalnız filtre sonrası Trade'leri
# paper portföye ekler.
gozlemci_mod.radar_tara = radar_tara_filtreli


if __name__ == "__main__":
    statik_site.main()
