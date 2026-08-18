#!/usr/bin/env python3
"""GitHub Pages canlı taraması — terminalMiraz kanıtlı klon katmanı.

Kanıtlanan ana davranışlar:
  - Price Action ve Harmonik ayrı setup/result yollarıdır.
  - terminalMiraz TF'leri: 15m/30m/1h/2h/4h.
  - Trade için bölge/pattern + trend kırılımı (MSB/Shear) teyidi gerekir.
  - Harmonik için gerçek pattern/PRZ gerekir.
  - Invalidasyon/stop fitille değil kapanışla değerlendirilir.
  - terminalMiraz'ın kendi test Result Journal'ı 1:1 RR ile yürütülür.

Kanıtlanmamış kurallar Trade kapısı yapılmaz. Eski %2-%3 stop filtresi,
yalnız-15m kuralı ve %65 TP1→BE→2R paper politikası bu klon sürümünde yoktur.
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
import miraz.radar as radar_mod  # noqa: E402
from miraz.radar import TERMINALMIRAZ_TF
from miraz.radar import radar_tara as _cekirdek_radar_tara  # noqa: E402

PA_KAYNAK = "Price Action"
HARMONIK_KAYNAK = "Harmonik"
MIRAZ_TETIK = "Shear"  # yeşil daire / trend kırılımı / MSB temsili
MIRAZ_TF = set(TERMINALMIRAZ_TF)

# Tweetlerde açıkça paylaşılan risk senaryoları. Ana Result Journal 1R'de kalır;
# bunlar ayrı senaryo/risk modu içindir.
radar_mod.RISK_MODLARI.update({"guvenli": 1.0, "dengeli": 2.0, "riskli": 3.5})

# Bu terminalMiraz-uyumlu 1R + close-invalidasyon sürümünün temiz başlangıcı.
ISTATISTIK_BASELINE_UTC = "2026-08-09T16:04:00+00:00"
_BASELINE_TS = datetime.fromisoformat(ISTATISTIK_BASELINE_UTC)


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
    """Pages state'ini yükle; klon sürümü öncesi kayıtları canlı istatistikten ayıkla."""
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
            f"🧹 terminalMiraz 1R baseline: {atilan_k} eski kayıt + "
            f"{atilan_p} eski pozisyon istatistikten çıkarıldı · "
            f"başlangıç {ISTATISTIK_BASELINE_UTC}"
        )
    return defter, portfoy


statik_site._onceki_state = _onceki_state_temiz


# ---------------------------------------------------------------------------
# terminalMiraz kanıtlı Trade kapısı
# ---------------------------------------------------------------------------
def _stop_pct(satir) -> float | None:
    """Stop mesafesi yalnız gösterim/analiz içindir; filtre değildir."""
    giris = getattr(satir, "giris", None)
    stop = getattr(satir, "stop", None)
    if giris is None or stop is None or float(giris) <= 0:
        return None
    return 100.0 * abs(float(giris) - float(stop)) / float(giris)


def _stop_gecerli(satir) -> bool:
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


def _hedef_1r(satir) -> float | None:
    giris = getattr(satir, "giris", None)
    stop = getattr(satir, "stop", None)
    if giris is None or stop is None:
        return None
    giris, stop = float(giris), float(stop)
    risk = abs(giris - stop)
    if risk <= 0:
        return None
    return giris - risk if getattr(satir, "taraf", "Long") == "Short" else giris + risk


def _miraz_tetik_var(satir) -> bool:
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
    for s in rapor.satirlar:
        if s.kategori != "Trade":
            continue

        sp = _stop_pct(s)
        tetik = _miraz_tetik_var(s)
        pa_uygun = _pa_uygun(s)
        harmonik_uygun = _harmonik_uygun(s)

        if tetik and (pa_uygun or harmonik_uygun):
            premium = str(getattr(s, "kalite", "")).strip() == "A+"
            h1 = _hedef_1r(s)
            if h1 is not None:
                s.hedef = round(h1, 10)
                s.rr = 1.0
            stop_bilgi = f" · stop %{sp:.2f}" if sp is not None else ""

            if harmonik_uygun:
                pat = str(getattr(s, "pattern", "Harmonik"))
                etiket = "⭐ PREMIUM HARMONİK" if premium else "🔷 HARMONİK TRADE"
                detay = f"{pat} PRZ · {s.interval} · MSB/Shear onaylı{stop_bilgi}"
            else:
                etiket = "⭐ PREMIUM PA" if premium else "✅ PA TRADE"
                detay = f"{s.interval} PA · MSB/Shear onaylı{stop_bilgi}"

            s.not_ = (
                f"{etiket} · {detay} · Result Journal 1:1 · "
                f"STOP kapanış-invalidasyon"
            ) + (f" · {s.not_}" if s.not_ else "")
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
        ek = ", ".join(neden) or "terminalMiraz tetik/onayı bekleniyor"
        s.not_ = f"Onay bekle → Watch ({ek})" + (f" · {s.not_}" if s.not_ else "")
    return rapor


def radar_tara_filtreli(*args, **kwargs):
    return _edge_uygula(_cekirdek_radar_tara(*args, **kwargs))


# ---------------------------------------------------------------------------
# terminalMiraz Result Journal: 1R TP / close-based STOP
# ---------------------------------------------------------------------------
def _miraz_guncelle(self, sembol, interval, df, max_bekleme=24):
    """1:1 journal.

    Entry: mevcut paper emrinin giriş seviyesine temas etmesiyle Açık olur.
    TP: 1R fiyatına temas.
    STOP: invalidasyon seviyesinin ötesinde MUM KAPANIŞI.

    Tweetlerde sık geçen 'hacimli kapanış' için sayısal hacim eşiği henüz
    arşivden kesinleştirilmediğinden burada uydurma katsayı kullanılmaz.
    """
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
        risk = abs(float(poz.giris) - float(poz.stop))
        if risk <= 0:
            continue
        hedef = float(poz.giris) - risk if short else float(poz.giris) + risk
        poz.hedef = round(hedef, 10)
        poz.rr = 1.0

        acilis_ts = None
        try:
            import pandas as pd
            acilis_ts = pd.Timestamp(poz.acilis_zaman)
            acilis_ts = acilis_ts.tz_localize("UTC") if acilis_ts.tzinfo is None else acilis_ts.tz_convert("UTC")
        except Exception:
            pass

        kapandi = False
        for ts, row in alt_df.iterrows():
            open_ = float(row["open"])
            hi = float(row["high"])
            lo = float(row["low"])
            close = float(row["close"])

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
                    poz.entry_zaman = ts.isoformat()
                    poz.entry_bekleme_bar = (
                        int(((df.index > acilis_ts) & (df.index <= ts)).sum())
                        if acilis_ts is not None else None)
                    poz.entry_bekleme_limiti = max_bekleme
                    poz.entry_kapanis = close
                    if "volume" in df.columns:
                        hacim = float(row["volume"])
                        if hacim == hacim:
                            onceki = df.loc[df.index < ts, "volume"].tail(20)
                            onceki = onceki[onceki > 0]
                            poz.entry_hacim = hacim
                            poz.entry_hacim_pencere = int(len(onceki))
                            if len(onceki):
                                poz.entry_hacim_oran = round(
                                    hacim / float(onceki.median()), 4)
                    degisenler.append(poz)

            if poz.durum != "Açık":
                continue

            # Miraz invalidasyonu: wick değil kapanış.
            stop_close = close > float(poz.stop) if short else close < float(poz.stop)
            tp_hit = lo <= hedef if short else hi >= hedef

            # Kapanış invalidasyonun ötesindeyse STOP önceliklidir.
            if stop_close:
                poz.durum = "STOP"
                poz.r_sonuc = -1.0
                poz.kapanis_zaman = ts.isoformat()
                poz.sonuc_mum_zaman = ts.isoformat()
                poz.sonuc_tetik = "candle-close"
                poz.sonuc_mum_ohlc = {
                    "open": open_, "high": hi, "low": lo, "close": close}
                poz.denetim_durumu = (
                    "verified-entry-to-result" if poz.entry_zaman
                    else "legacy-limited-no-entry-time")
                degisenler.append(poz)
                kapandi = True
                break
            if tp_hit:
                poz.durum = "TP"
                poz.r_sonuc = 1.0
                poz.kapanis_zaman = ts.isoformat()
                poz.sonuc_mum_zaman = ts.isoformat()
                poz.sonuc_tetik = "target-touch"
                poz.sonuc_mum_ohlc = {
                    "open": open_, "high": hi, "low": lo, "close": close}
                poz.denetim_durumu = (
                    "verified-entry-to-result" if poz.entry_zaman
                    else "legacy-limited-no-entry-time")
                degisenler.append(poz)
                kapandi = True
                break

        if not kapandi:
            poz.son_kontrol_zaman = alt_df.index[-1].isoformat()

    return degisenler


def _guncelle_patch(self, sembol, interval, df, max_bekleme=24):
    return _miraz_guncelle(self, sembol, interval, df, max_bekleme)


gozlemci_mod.Portfoy.guncelle = _guncelle_patch
gozlemci_mod.radar_tara = radar_tara_filtreli


if __name__ == "__main__":
    statik_site.main()
