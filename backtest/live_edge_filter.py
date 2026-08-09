#!/usr/bin/env python3
"""GitHub Pages canlı taramasına terminalMiraz-kanıtlı PA + Harmonik filtresi uygular.

Bu katman yalnız arşivde açıkça desteklenen davranışları Trade kapısı yapar:
  1) Çekirdek radarın HTF/Late/çiğnenmiş-bölge güvenlik kararları korunur.
  2) Price Action ve Harmonik iki bağımsız setup yoludur.
  3) terminalMiraz TF'leri: 15m/30m/1h/2h/4h.
  4) Trade için geçerli stop/invalidasyon ve trend kırılımı (MSB/Shear) gerekir.
  5) Harmonik için ayrıca gerçek pattern/PRZ gerekir.
  6) Stop yüzdesi karar filtresi DEĞİLDİR; yalnız bilgi amaçlı gösterilir.
  7) Canlı paper yönetimi mevcut TP1→BE→TP2 simülasyonunu sürdürür.

Önemli: Daha önceki "yalnız 15m PA + stop %2..%3" kuralı terminalMiraz
kanıtı değildi; geçmiş BigE sonuçlarından türetilmiş bir optimizasyondu ve bu
sürümde Trade kapısından kaldırılmıştır.
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
from miraz.radar import TERMINALMIRAZ_TF
from miraz.radar import radar_tara as _cekirdek_radar_tara  # noqa: E402

PA_KAYNAK = "Price Action"
HARMONIK_KAYNAK = "Harmonik"
MIRAZ_TETIK = "Shear"  # yeşil daire / trend kırılımı / MSB temsili
MIRAZ_TF = set(TERMINALMIRAZ_TF)

# terminalMiraz-kanıtlı filtre sürümünün temiz başlangıcı.
# Türkiye: 2026-08-09 15:48:00 +03:00
ISTATISTIK_BASELINE_UTC = "2026-08-09T12:48:00+00:00"
_BASELINE_TS = datetime.fromisoformat(ISTATISTIK_BASELINE_UTC)

# Mevcut paper pozisyon yönetimi.
# Not: TP1 payı (%65) terminalMiraz'dan kanıtlanmış sabit oran değildir;
# ölçüm politikasıdır. Arşiv yalnız kısmi kar + BE + min 2R davranışını doğrular.
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
    """Pages state'ini yükle; bu sürümden önceki kayıt/pozisyonları ayıkla."""
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
            f"🧹 terminalMiraz clone baseline: {atilan_k} eski kayıt + "
            f"{atilan_p} eski pozisyon istatistikten çıkarıldı · "
            f"başlangıç {ISTATISTIK_BASELINE_UTC}"
        )
    return defter, portfoy


statik_site._onceki_state = _onceki_state_temiz


# ---------------------------------------------------------------------------
# terminalMiraz-kanıtlı Trade kapısı
# ---------------------------------------------------------------------------
def _stop_pct(satir) -> float | None:
    """Stop mesafesi yalnız gösterim/analiz içindir; Trade filtresi değildir."""
    giris = getattr(satir, "giris", None)
    stop = getattr(satir, "stop", None)
    if giris is None or stop is None or float(giris) <= 0:
        return None
    return 100.0 * abs(float(giris) - float(stop)) / float(giris)


def _stop_gecerli(satir) -> bool:
    """Invalidasyon girişin doğru tarafında ve sıfırdan farklı olmalı."""
    giris = getattr(satir, "giris", None)
    stop = getattr(satir, "stop", None)
    if giris is None or stop is None:
        return False
    try:
        giris, stop = float(giris), float(stop)
    except Exception:
        return False
    if giris <= 0 or stop <= 0 or abs(giris - stop) <= 1e-12:
        return False
    short = getattr(satir, "taraf", "Long") == "Short"
    return stop > giris if short else stop < giris


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


def _pa_uygun(satir) -> bool:
    return (
        getattr(satir, "interval", "") in MIRAZ_TF
        and getattr(satir, "kaynak", "") == PA_KAYNAK
        and _stop_gecerli(satir)
    )


def _harmonik_uygun(satir) -> bool:
    return (
        getattr(satir, "interval", "") in MIRAZ_TF
        and getattr(satir, "kaynak", "") == HARMONIK_KAYNAK
        and bool(getattr(satir, "pattern", None))
        and _stop_gecerli(satir)
    )


def _edge_uygula(rapor):
    """Çekirdek Trade'leri terminalMiraz kanıtına göre doğrula.

    PA: terminalMiraz TF + Price Action + geçerli invalidasyon + MSB/Shear.
    Harmonik: terminalMiraz TF + pattern/PRZ + geçerli invalidasyon + MSB/Shear.

    HTF/Late/çiğnenmiş bölge vb. çekirdek kararlar burada yükseltilmez.
    """
    for s in rapor.satirlar:
        if s.kategori != "Trade":
            continue

        sp = _stop_pct(s)
        tetik = _miraz_tetik_var(s)
        pa_uygun = _pa_uygun(s)
        harmonik_uygun = _harmonik_uygun(s)

        if tetik and (pa_uygun or harmonik_uygun):
            premium = str(getattr(s, "kalite", "")).strip() == "A+"
            h2 = _hedef_2r(s)
            proj = f" · TP2 {h2:.6g}" if h2 is not None else ""
            stop_bilgi = f" · stop %{sp:.2f}" if sp is not None else ""

            if harmonik_uygun:
                pat = str(getattr(s, "pattern", "Harmonik"))
                etiket = "⭐ PREMIUM HARMONİK" if premium else "🔷 HARMONİK TRADE"
                detay = f"{pat} PRZ · {s.interval} · MSB/Shear onaylı{stop_bilgi}"
            else:
                etiket = "⭐ PREMIUM PA" if premium else "✅ PA TRADE"
                detay = f"{s.interval} PA · MSB/Shear onaylı{stop_bilgi}"

            detay += (
                f" · yönetim: 1R'de %{TP1_PAY*100:.0f} ölçüm-paylı kar → BE → 2R{proj}"
            )
            s.not_ = f"{etiket} · {detay}" + (f" · {s.not_}" if s.not_ else "")
            continue

        neden = []
        if getattr(s, "interval", "") not in MIRAZ_TF:
            neden.append(f"TF {getattr(s, 'interval', '?')} terminalMiraz setinde değil")

        if s.kaynak == HARMONIK_KAYNAK:
            if not getattr(s, "pattern", None):
                neden.append("harmonik pattern/PRZ eksik")
            if not _stop_gecerli(s):
                neden.append("harmonik invalidasyon geçersiz")
            if harmonik_uygun and not tetik:
                neden.append("Harmonik PRZ var, trend kırılımı/MSB henüz yok")
        elif s.kaynak == PA_KAYNAK:
            if not _stop_gecerli(s):
                neden.append("PA invalidasyon geçersiz")
            if pa_uygun and not tetik:
                neden.append("PA bölgesi var, trend kırılımı/MSB henüz yok")
        else:
            neden.append(f"kaynak {s.kaynak} PA/Harmonik değil")

        s.kategori = "Watch"
        # Kaynak kimliğini koru; analytics PA/Harmonik ayrımını kaybetmesin.
        ek = ", ".join(neden) or "terminalMiraz tetik/onayı bekleniyor"
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
    try:
        return abs(float(poz.hedef) - _r_fiyat(poz, TP2_R)) <= max(abs(float(poz.giris)) * 1e-8, 1e-12) \
            and abs(float(poz.stop) - float(poz.giris)) <= max(abs(float(poz.giris)) * 1e-8, 1e-12)
    except Exception:
        return False


def _miraz_guncelle(orj_guncelle, self, sembol, interval, df, max_bekleme=24):
    """Aktif işlemleri TP1→BE→TP2 paper politikasıyla güncelle."""
    aktif = [p for p in self.pozisyonlar
             if p.sembol == sembol and p.interval == interval
             and p.durum in ("Bekliyor", "Açık")]
    if not aktif or df is None or df.empty:
        return []

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
            hi = float(row["high"])
            lo = float(row["low"])

            if poz.durum == "Bekliyor":
                if acilis_ts is not None:
                    gecen = int(((df.index > acilis_ts) & (df.index <= ts)).sum())
                    if gecen > max_bekleme:
                        poz.durum = "Expired"
                        poz.r_sonuc = 0.0
                        poz.kapanis_zaman = ts.isoformat()
                        degisenler.append(poz)
                        kapandi = True
                        break
                doldu = hi >= poz.giris if short else lo <= poz.giris
                if doldu:
                    poz.durum = "Açık"
                    degisenler.append(poz)

            if poz.durum != "Açık":
                continue

            tp1_done = _tp1_alindi(poz)
            if not tp1_done:
                tp1 = _r_fiyat(poz, TP1_R)
                stop_hit = hi >= poz.stop if short else lo <= poz.stop
                tp1_hit = lo <= tp1 if short else hi >= tp1

                if stop_hit:
                    poz.durum = "STOP"
                    poz.r_sonuc = -1.0
                    poz.kapanis_zaman = ts.isoformat()
                    degisenler.append(poz)
                    kapandi = True
                    break
                if tp1_hit:
                    poz.r_sonuc = round(TP1_PAY * TP1_R, 4)
                    poz.stop = float(poz.giris)
                    poz.hedef = round(_r_fiyat(poz, TP2_R), 10)
                    poz.rr = TP2_R
                    degisenler.append(poz)
                    continue
            else:
                be_hit = hi >= poz.stop if short else lo <= poz.stop
                tp2_hit = lo <= poz.hedef if short else hi >= poz.hedef
                if be_hit:
                    poz.durum = "TP"
                    poz.r_sonuc = round(TP1_PAY * TP1_R, 4)
                    poz.kapanis_zaman = ts.isoformat()
                    degisenler.append(poz)
                    kapandi = True
                    break
                if tp2_hit:
                    poz.durum = "TP"
                    poz.r_sonuc = round(TP1_PAY * TP1_R + RUNNER_PAY * TP2_R, 4)
                    poz.kapanis_zaman = ts.isoformat()
                    degisenler.append(poz)
                    kapandi = True
                    break

        if not kapandi:
            poz.son_kontrol_zaman = alt_df.index[-1].isoformat()

    return degisenler


_ORJ_GUNCELLE = gozlemci_mod.Portfoy.guncelle


def _guncelle_patch(self, sembol, interval, df, max_bekleme=24):
    return _miraz_guncelle(_ORJ_GUNCELLE, self, sembol, interval, df, max_bekleme)


gozlemci_mod.Portfoy.guncelle = _guncelle_patch

gozlemci_mod.radar_tara = radar_tara_filtreli


if __name__ == "__main__":
    statik_site.main()
