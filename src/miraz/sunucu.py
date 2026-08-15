"""Web Sunucu — terminalMiraz tarzı tarayıcıdan açılan canlı pano.

@tradermiraz terminalMiraz'ı bir CMD ekranında değil, sunucuda çalışan bir
**uygulama** olarak tutuyor: kendi bilgisayarından tarayıcıyla girip koyu temalı
paneli izliyor. Bu modül aynı şeyi yapar:

  • Arka planda bir iş parçacığı evreni sürekli tarar (Gözlemci döngüsü).
  • Her tarama sonrası durumu JSON'a çevirip bellekte tutar.
  • Yerleşik HTTP sunucu `/` adresinde koyu temalı paneli (web/index.html),
    `/api/durum` adresinde de canlı JSON'u sunar. Tarayıcı her birkaç saniyede
    JSON'u çekip paneli tazeler.

Sadece Python standart kütüphanesi (http.server) — ek bağımlılık yok.

Kullanım:
    from miraz.sunucu import Sunucu
    s = Sunucu(semboller=[...], intervallar=["1h"], taraf="her", port=8000)
    s.basla()   # tarayıcıda http://localhost:8000

CLI: python backtest/sunucu.py --port 8000 --mcap --mtf --taraf her
"""

from __future__ import annotations

import json
import threading
import pandas as pd
from collections import Counter
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .gozlemci import Gozlemci, Defter, DEFTER_DOSYA, PORTFOY_DOSYA
from .portfoy import Portfoy
from . import veri
from . import indikator
from . import konsept as kons
from . import yorum
from .radar import HTF_POLICY, MTF_KALIBRASYON_POLICY, mtf_kalibrasyon_kapisi

WEB_DIZIN = Path(__file__).resolve().parent / "web"


def _simdi_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Durum → JSON anlık görüntüsü (saf fonksiyon, test edilebilir)
# ---------------------------------------------------------------------------

def _satir_json(s) -> dict:
    konseptler = getattr(s, "konseptler", None) or []
    d = {
        "symbol": s.symbol, "interval": s.interval, "fiyat": s.fiyat,
        "kategori": s.kategori, "kalite": s.kalite, "guven": s.guven,
        "taraf": s.taraf, "kaynak": getattr(s, "kaynak", "Price Action"),
        "pattern": getattr(s, "pattern", None),
        "harmonik_detay": getattr(s, "harmonik_detay", None) or {},
        "risk_modu": getattr(s, "risk_modu", "legacy-unknown"),
        "risk_rr_hedef": getattr(s, "risk_rr_hedef", None),
        "risk_r_dolar": getattr(s, "risk_r_dolar", None),
        "temas_detay": dict(getattr(s, "temas_detay", None) or {}),
        "giris": s.giris,
        "stop": s.stop, "hedef": s.hedef, "rr": s.rr, "not_": s.not_,
        "konseptler": konseptler,
        "lifecycle": getattr(s, "lifecycle", "Candidate"),
        "skor_modeli": getattr(s, "skor_modeli", "BigE heuristic v1"),
        "kalite_kademe": getattr(s, "kalite_kademe", None),
        "test_asamasi": getattr(s, "test_asamasi", None),
        "asama_basi_kontrol": getattr(s, "asama_basi_kontrol", None),
        "kalite_filtre_detayi": getattr(s, "kalite_filtre_detayi", None),
        "filtre_esleme": getattr(s, "filtre_esleme", "undisclosed-by-archive"),
        "ana_tf_yapi": getattr(s, "ana_tf_yapi", ""),
        "htf_tf": getattr(s, "htf_tf", ""),
        "htf_yapi": getattr(s, "htf_yapi", ""),
        "ltf_tf": getattr(s, "ltf_tf", ""),
        "ltf_yapi": getattr(s, "ltf_yapi", "not-implemented"),
        "ltf_onay": getattr(s, "ltf_onay", "not-available"),
        "setup_turleri": list(getattr(s, "setup_turleri", None) or []),
        "setup_tur_detaylari": dict(
            getattr(s, "setup_tur_detaylari", None) or {}),
    }
    # @tradermiraz tarzı plan yorumu (her setup kartında gösterilir)
    try:
        d["miraz_yorum"] = yorum.miraz_yorum(
            s.symbol, s.interval, s.taraf, giris=s.giris, stop=s.stop,
            hedef=s.hedef, rr=s.rr, pattern=getattr(s, "pattern", None),
            konseptler=konseptler, kategori=s.kategori, guven=s.guven)
    except Exception:
        d["miraz_yorum"] = None
    return d


def _kiraz_status(rapor) -> tuple[str, str]:
    """terminalMiraz KIRAZ STATUS: EXECUTION / WATCHLIST + açıklama."""
    aday = rapor.ozet.get("Trade", 0)
    izle = rapor.ozet.get("Watch", 0)
    if aday > 0:
        return "EXECUTION MODE", f"{aday} aday işleme uygun — Kiraz emir açıyor"
    if izle > 0:
        return "WATCHLIST MODE", (
            f"{izle} aktif setup var ama risk filtresi nedeniyle emir beklemede")
    return "WATCHLIST MODE", "uygun aday yok — izlemede"


def durum_json(gozlemci: Gozlemci, rapor, aralik: int, borsa=None) -> dict:
    """Gözlemci + son radar raporundan tarayıcının ihtiyaç duyduğu tam durum.

    borsa verilirse (Binance Testnet) execution metrikleri gerçek testnet
    hesabından okunur; yoksa paper-trading portföyünden.
    """
    defter = gozlemci.defter
    portfoy = gozlemci.portfoy
    d_ozet = defter.ozet()
    pnl = defter.pnl_analitik()

    # execution metrikleri — gerçek testnet varsa ondan, yoksa paper portföy
    r_dolar = getattr(portfoy, "r_dolar", 25.0) or 25.0
    poz = getattr(portfoy, "pozisyonlar", [])
    aktif = [p for p in poz if p.durum == "Açık"]
    bekleyen = [p for p in poz if p.durum == "Bekliyor"]
    toplam_r = getattr(portfoy, "toplam_r", 0.0) or 0.0
    equity = 5000.0 + toplam_r * r_dolar
    aktif_n, bekleyen_n = len(aktif), len(bekleyen)
    canli = False
    if borsa is not None:
        try:
            oz = borsa.ozet()
            equity = round(oz["wallet"], 1)
            toplam_r = round(oz["unrealized"] / r_dolar, 1) if r_dolar else 0.0
            aktif_n = len(borsa.pozisyonlar())
            bekleyen_n = len(borsa.acik_emirler())
            canli = True
        except Exception:
            canli = False
    open_risk = round(aktif_n * r_dolar / equity * 100, 1) if equity else 0.0
    kiraz_durum, kiraz_mesaj = _kiraz_status(rapor)

    # canlı aday akışı (Trade + Watch, güvene göre)
    # giris=None olanlar grafik seviyesi olmadığından scanner'da işe yaramaz → filtrele
    adaylar = [s for s in rapor.satirlar
               if s.kategori in ("Trade", "Watch")
               and s.giris is not None and s.giris > 0]
    adaylar.sort(key=lambda s: (0 if s.kategori == "Trade" else 1, -s.guven))

    # grafiğin varsayılan açacağı sembol (aday yoksa bile boş kalmasın)
    if adaylar:
        vg = {"symbol": adaylar[0].symbol, "interval": adaylar[0].interval}
    elif rapor.satirlar:
        vg = {"symbol": rapor.satirlar[0].symbol,
              "interval": rapor.satirlar[0].interval}
    else:
        sem = getattr(gozlemci, "semboller", None) or ["BTCUSDT"]
        ivl = getattr(gozlemci, "intervallar", None) or ["1h"]
        vg = {"symbol": sem[0], "interval": ivl[0]}

    # sonuç bildirimleri (defterdeki son kapanan kayıtlar)
    kapanan = [k for k in defter.kayitlar if not k.aktif][-12:][::-1]
    bildirimler = [{
        "sembol": k.sembol, "interval": k.interval, "durum": k.durum,
        "taraf": k.taraf, "kaynak": getattr(k, "kaynak", "Price Action"),
        "pattern": k.pattern, "entry_zaman": getattr(k, "entry_zaman", ""),
        "giris": k.giris, "stop": k.stop,
        "hedef": k.hedef, "r_sonuc": k.r_sonuc,
        "kapanis": (k.kapanis_zaman or "")[:16],
        "kapanis_zaman": k.kapanis_zaman or "",
        "sonuc_mum_zaman": getattr(k, "sonuc_mum_zaman", ""),
        "sonuc_tetik": getattr(k, "sonuc_tetik", ""),
        "sonuc_mum_ohlc": getattr(k, "sonuc_mum_ohlc", {}) or {},
        "denetim_durumu": getattr(k, "denetim_durumu", ""),
    } for k in kapanan]

    radar_lifecycle = Counter(
        getattr(s, "lifecycle", "Candidate") for s in rapor.satirlar
    )
    return {
        "zaman": _simdi_iso(),
        "tarama_no": defter.tarama_turu,
        "toplam_tarama": defter.toplam_tarama,
        "aralik": aralik,
        "ozet": rapor.ozet,
        "durum_cubugu": {
            "kiraz": True, "sql_memory": True,
            "order_engine": portfoy is not None, "binance": canli,
        },
        "execution": {
            "wallet": round(equity, 1), "aktif": aktif_n,
            "bekleyen": bekleyen_n, "daily_pnl": round(toplam_r, 1),
            "open_risk": open_risk, "r_dolar": r_dolar, "canli": canli,
            "kiraz_durum": kiraz_durum, "kiraz_mesaj": kiraz_mesaj,
            "entry_tetik": "zone-touch",
            "stop_tetik": "candle-close",
            "tp_tetik": "target-touch",
        },
        "buckets": d_ozet["buckets"],
        # Result Journal kümülatiftir: yalnız Defter'e bir kez yazılmış kayıtlar.
        # Anlık radar snapshot'ı ayrı tutulur; aksi halde aynı setup her taramada
        # yeniden journal sonucu gibi sayılır.
        "lifecycle": {
            "Filtered": d_ozet["Filtered"],
            "Shelved": d_ozet["Shelved"],
            "No-Entry": d_ozet["No-Entry"],
            "Expired": d_ozet["Expired"],
            "Cancelled": d_ozet["Cancelled"],
        },
        "filtered_nedenleri": defter.filtered_neden_ozeti(),
        "filtered_etki": defter.filtered_etki_ozeti(),
        "filtered_kalite_gecisleri": defter.filtered_kalite_gecis_ozeti(),
        "htf_denetim": defter.htf_denetim_ozeti(),
        "ltf_gozlem": defter.ltf_gozlem_ozeti(),
        "mtf_kalibrasyon": {
            "policy": MTF_KALIBRASYON_POLICY,
            "ltf_siniflari": [
                mtf_kalibrasyon_kapisi(x["ad"], x["dogrulanmis_n"])
                for x in defter.ltf_gozlem_ozeti()["siniflar"]
            ],
            "htf_dogrulanmis_n": defter.htf_denetim_ozeti()["dogrulanmis_n"],
        },
        "pa_alt_turleri": defter.pa_alt_tur_ozeti(),
        "pa_capraz": defter.pa_capraz_ozeti(),
        "harmonik_patternler": defter.harmonik_pattern_ozeti(),
        "harmonik_capraz": defter.harmonik_capraz_ozeti(),
        "risk_modlari": defter.risk_modu_ozeti(),
        "temas_davranisi": defter.temas_davranisi_ozeti(),
        "filtered_takip": [{
            "id": k.id, "sembol": k.sembol, "interval": k.interval,
            "taraf": k.taraf, "neden": k.durum_nedeni or "legacy-unknown",
            "durum": k.karsi_olgusal_durum or "Takip Başlamadı",
            "giris": k.giris, "stop": k.stop, "hedef": k.hedef,
            "entry_zaman": k.karsi_olgusal_entry_zaman,
            "sonuc_zaman": k.karsi_olgusal_zaman,
            "journal_r": 0.0,
        } for k in reversed(defter.kayitlar) if k.durum == "Filtered"][:30],
        "radar_lifecycle": dict(radar_lifecycle),
        "wr": d_ozet["wr"], "toplam_r": d_ozet["toplam_r"],
        "sonuc_denetim": d_ozet["sonuc_denetim"],
        "toplam_r_late_haric": d_ozet["toplam_r_late_haric"],
        "late_katki_r": d_ozet["late_katki_r"],
        "aktif_kayit": d_ozet["aktif"],
        "adaylar": [_satir_json(s) for s in adaylar[:16]],
        "konsept_sayim": getattr(rapor, "konsept_sayim", {}) or {},
        "konsept_sirasi": kons.KONSEPT_SIRASI,
        "varsayilan_grafik": vg,
        "bildirimler": bildirimler,
        "pnl": pnl,
        "memory": {"parite": pnl["parite"], "tf": pnl["tf"],
                   "parite_karakter": pnl["parite_karakter"],
                   "harmonik_parite_karakter": defter.harmonik_parite_hafiza(),
                   "parite_konsept": defter.parite_konsept_hafiza(),
                   "tf_motor": defter.tf_motor_hafiza(),
                   "entry_kalite": defter.entry_kalite_hafiza(),
                   "entry_hacim": defter.entry_hacim_hafiza(),
                   "adaydan_entry_kalite": defter.adaydan_entry_kalite_hafiza(),
                   "entry_bekleme": defter.entry_bekleme_hafiza(),
                   "konsept": pnl["konsept"]},
        # Performance Intelligence + Journal + Aylık R ek verileri
        "perf_curve": defter.perf_curve(),
        "aktif_tradeler": defter.aktif_trade_kartlari(),
        "trade_memory": defter.trade_memory(24),
        "takvim": defter.takvim_veri(),
        "lifecycle_ozet": {
            "Aday": d_ozet.get("Aday", 0),
            "Açık": d_ozet.get("Açık", 0),
            "TP": d_ozet.get("TP", 0),
            "STOP": d_ozet.get("STOP", 0),
            "Filtered": d_ozet.get("Filtered", 0),
            "Shelved": d_ozet.get("Shelved", 0),
            "Expired": d_ozet.get("Expired", 0),
            "No-Entry": d_ozet.get("No-Entry", 0),
            "Cancelled": d_ozet.get("Cancelled", 0),
        },
        "result_journal_policy": {
            "mode": "verified-entry-to-first-result-candle",
            "outcomes": ["TP", "STOP"],
            "performance_includes": "verified-only",
            "legacy_label": "LEGACY / SINIRLI DOĞRULAMA",
            "required_evidence": ["entry_zaman", "sonuc_mum_zaman",
                                  "sonuc_tetik", "sonuc_mum_ohlc"],
            "other_results": ["Filtered", "Shelved", "No-Entry", "Expired", "Cancelled"],
            "engine_buckets": ["Price Action", "Harmonik", "Late"],
            "evidence_tweet_ids": ["2065351367544181110", "2059325292926148742"],
            "radar_snapshot_included": False,
            "late_detection": "undisclosed-by-archive",
            "late_auto_classification": False,
            "late_performance_comparison": "included-and-excluded",
        },
        "htf_policy": dict(HTF_POLICY),
        "dynamic_quality_policy": {
            "mode": "re-evaluate-until-entry",
            "history": "persisted-on-change",
            "open_positions_re_evaluated": False,
            "evidence_tweet_ids": ["2064005426710986769"],
            "scan_frequency": "runtime-configured-not-archive-rule",
            "check_count": "undisclosed-by-archive",
        },
        "shelved_policy": {
            "archive_label": "Rafa Kalktı",
            "evidence_tweet_ids": ["2065351367544181110"],
            "criteria": "undisclosed-by-archive",
            "automatic": False,
            "supported_transition": "pending-to-shelved-explicit",
            "reason_required_for_audit": True,
        },
        "terminal_lifecycle_policy": {
            "Cancelled": {
                "meaning": "setup-structurally-invalidated",
                "harmonic_evidence_tweet_id": "2062383146415333550",
                "automatic_harmonic_validity_check": True,
            },
            "No-Entry": {
                "meaning": "entry-zone-not-reached",
                "evidence_tweet_id": "2061490944713601191",
                "observation_horizon": "undisclosed-by-archive",
                "automatic": False,
            },
            "Expired": {
                "meaning": "time-expiry",
                "exact_archive_rule": "undisclosed-by-archive",
                "current_timeout": "24-bars-BigE-default",
            },
            "stale_target_seen": {
                "result": "Filtered",
                "not_no_entry": True,
            },
        },
        "filtered_reason_policy": {
            "journal_status": "Filtered",
            "reason_taxonomy_origin": "BigE-audit-derived-from-radar-notes",
            "miraz_exact_reason_mapping": "undisclosed-by-archive",
            "counterfactual_rule": "report-only-explicitly-verified-TP-STOP",
            "untracked_stop_claim": "forbidden",
            "tracking": "forward-only-from-first-post-filter-snapshot",
            "entry_trigger": "price-touch",
            "tp_trigger": "price-touch",
            "stop_trigger": "candle-close-beyond-invalidation",
            "tracking_expiry": "undisclosed-by-archive-no-auto-expiry",
            "result_journal_included": False,
            "breakdown_basis": "persisted-filter-time-snapshot",
            "breakdowns": ["engine", "timeframe", "quality", "audit-reason"],
            "quality_transition_basis": "persisted-consecutive-distinct-snapshots",
            "quality_transition_attribution": "descriptive-not-causal",
            "causality_claim": "not-made",
            "evidence_tweet_ids": ["2059325292926148742"],
            "reasons": [
                "htf-conflict", "quality-weakened", "stale-zone",
                "structural-invalidity", "filtered-other", "legacy-unknown",
            ],
            "evidence_tweet_ids": ["2059325292926148742", "2064005426710986769"],
        },
    }


# ---------------------------------------------------------------------------
# CANLI GRAFİK — mum + ZONE + SQL Memory çizgisi + MACD (terminalMiraz grafiği)
# ---------------------------------------------------------------------------

def _seviye_bul(durum: dict, symbol: str, interval: str) -> dict | None:
    """Aktif işlem öncelikli setup seviyelerini bul.

    Aynı sembol/TF için yeni aday veya eski bildirim bulunabilir. Grafikte açık
    işlemin gerçek entry/stop/TP ve harmonik pattern'i her zaman önceliklidir.
    """
    for liste in (durum.get("aktif_tradeler", []), durum.get("adaylar", []),
                  durum.get("bildirimler", [])):
        for s in liste:
            sym = s.get("symbol") or s.get("sembol")
            if sym == symbol and s.get("interval") == interval:
                return {
                    "giris": s.get("giris"), "stop": s.get("stop"),
                    "hedef": s.get("hedef"), "taraf": s.get("taraf", "Long"),
                    "durum": s.get("durum"),
                    "pattern": s.get("pattern"), "kaynak": s.get("kaynak"),
                    "rr": s.get("rr"), "entry_zaman": s.get("entry_zaman"),
                    "kapanis_zaman": s.get("kapanis_zaman"),
                    "sonuc_mum_zaman": s.get("sonuc_mum_zaman"),
                    "sonuc_tetik": s.get("sonuc_tetik"),
                    "sonuc_mum_ohlc": s.get("sonuc_mum_ohlc", {}),
                    "denetim_durumu": s.get("denetim_durumu"),
                    "konseptler": s.get("konseptler", []),
                    "harmonik_detay": s.get("harmonik_detay", {}),
                    "harmonik_gecmisi": s.get("harmonik_gecmisi", []),
                }
    return None


def _harmonik_ciz(df, seviye: dict) -> dict:
    """Grafik penceresi (df) için tamamlanmış + oluşmakta olan harmonik çizimi.

    Noktalar mumlar dizisindeki **konum indeksiyle** döner (X_idx, A_idx … df'in
    0-tabanlı bar konumu = mumlar dizisindeki i). Böylece frontend i-bazlı X
    eksenine doğrudan oturtur. @tradermiraz'ın XABCD çizimini canlandırır:
      • tamamlanan: 5 nokta (X-A-B-C-D), bacaklar + Fib oranları + PRZ.
      • olusan: 4 nokta (X-A-B-C), D henüz gelmemiş → PRZ kutusu ileriye projekte.
    """
    from . import pivotlar as pv
    from . import harmonik as hrm

    out: dict = {}
    try:
        piv = pv.pivot_listesi(df, n=5)
    except Exception:
        return out
    if len(piv) < 4:
        return out

    # --- Tamamlanmış harmonik: aday pattern'iyle eşleşen en güncel, yoksa en güncel
    try:
        tamamlananlar = hrm.tara(df, piv, min_kalite=45.0)   # D_idx'e göre sıralı
    except Exception:
        tamamlananlar = []
    # İşlenen setup'a bağla: yön (taraf) + pattern adı + D'si GİRİŞE en yakın olan
    # = grafikte çizilen XABCD ile kartın ENTRY/yönü örtüşsün. Yön isteniyor ama
    # o yönde tamamlanmış pattern yoksa çelişkili ters pattern çizme (hiç çizme).
    sec = None
    if tamamlananlar:
        sv = seviye or {}
        istek_pat = sv.get("pattern")
        istek_giris = sv.get("giris")
        yon_iste = {"Long": "Bullish", "Short": "Bearish"}.get(sv.get("taraf"))
        aday = tamamlananlar
        if yon_iste:
            aday = [p for p in aday if p.yon == yon_iste]
        if aday:
            if istek_pat:
                patli = [p for p in aday if p.isim == istek_pat]
                if patli:
                    aday = patli
            sec = (min(aday, key=lambda p: abs(p.D - istek_giris))
                   if istek_giris is not None else aday[0])  # yoksa en güncel
    if sec is not None:
        out["tamamlanan"] = {
            "isim": sec.isim, "yon": sec.yon, "kalite": sec.kalite, "rr": sec.rr,
            "noktalar": [[sec.X_idx, round(sec.X, 6)], [sec.A_idx, round(sec.A, 6)],
                         [sec.B_idx, round(sec.B, 6)], [sec.C_idx, round(sec.C, 6)],
                         [sec.D_idx, round(sec.D, 6)]],
            "oranlar": {k: round(float(v), 3) for k, v in sec.oranlar.items()
                        if k in ("AB_XA", "BC_AB", "CD_BC", "XD_XA")},
            "entry": sec.entry, "sl": sec.sl, "tp1": sec.tp1, "tp2": sec.tp2,
        }

    # --- Oluşmakta olan harmonik: D projeksiyonu (PRZ) ileriye çizilir
    try:
        oh = hrm.olusan_harmonik(df, piv)
    except Exception:
        oh = None
    if oh is not None:
        out["olusan"] = {
            "isim": oh.isim, "yon": oh.yon,
            "noktalar": [[oh.X_idx, round(oh.X, 6)], [oh.A_idx, round(oh.A, 6)],
                         [oh.B_idx, round(oh.B, 6)], [oh.C_idx, round(oh.C, 6)]],
            "D_idx": len(df) - 1,            # PRZ'yi grafiğin sağ kenarına projekte et
            "D_proj": oh.D, "prz_alt": oh.prz_alt, "prz_ust": oh.prz_ust,
            "oranlar": {k: round(float(v), 3) for k, v in oh.oranlar.items()},
        }
    return out


def grafik_veri(symbol: str, interval: str, durum: dict | None = None,
                gun: int = 60, bar: int = 160, max_bar: int | None = None) -> dict:
    """Bir sembol/TF için mum + MACD + setup seviyeleri (ZONE dâhil) döndürür.

    ZONE, taze senaryo motorundan (bolge_alt/üst) hesaplanır; setup seviyeleri
    (giriş/stop/hedef) son tarama anlık görüntüsünden alınır. Ayrıca harmonik
    setup'ın XABCD çizimi (tamamlanan + oluşmakta olan) eklenir.
    """
    df = veri.indir(symbol, interval, gun=gun, max_bar=max_bar).tail(bar)
    mac = indikator.macd(df["close"])

    def _kolon(seri):
        return [None if v != v else round(float(v), 6) for v in seri]

    mumlar = [[int(ts.timestamp()), round(float(o), 6), round(float(yk), 6),
               round(float(dk), 6), round(float(c), 6)]
              for ts, o, yk, dk, c in zip(
                  df.index, df["open"], df["high"], df["low"], df["close"])]

    seviye = _seviye_bul(durum or {}, symbol, interval) or {}

    # ZONE: taze senaryodan destek bölgesi (long) — best-effort
    zone_alt = zone_ust = None
    try:
        from .senaryo import senaryo_uret
        s = senaryo_uret(df)
        zone_alt, zone_ust = s.bolge_alt, s.bolge_ust
    except Exception:
        pass

    # Harmonik XABCD çizimi (pivotlar df konum indeksiyle = mumlar i)
    try:
        harmonik = _harmonik_ciz(df, seviye)
    except Exception:
        harmonik = {}

    # XABCD koordinatları eski kayıtta tutulmadıysa nokta uydurma; yalnız
    # gerçekten kaydedilmiş PRZ merkezini kanıtlı fallback olarak göster.
    if seviye.get("pattern"):
        detay = seviye.get("harmonik_detay") or {}
        prz = detay.get("prz") or {}
        merkez = prz.get("merkez")
        if merkez is not None:
            harmonik["kayitli_prz"] = {
                "isim": seviye.get("pattern"), "merkez": merkez,
                "kaynak": prz.get("kaynak", "recorded-snapshot"),
                "yon": {"Long": "Bullish", "Short": "Bearish"}.get(
                    seviye.get("taraf")),
                "nokta_politikasi": "no-invented-xabcd",
            }

    # Harmonik fallback: seviyede giris yoksa tamamlanan harmonik'in kendi
    # entry/sl/tp1'ini kullan (destek_kutu olmadığında rp=None → giris=None olur)
    t = harmonik.get("tamamlanan")
    if t and not seviye.get("giris"):
        seviye = {
            **seviye,
            "giris": t.get("entry"),
            "stop": t.get("sl"),
            "hedef": t.get("tp1"),
            "rr": t.get("rr"),
        }

    # setup_bar: setup'ın oluştuğu bar (grafik çizgileri buradan sağa uzanır).
    # Öncelik: (1) tamamlanan harmonik D barı, (2) giriş fiyatına en yakın
    # pivot (= harmonik D / tepki noktası), (3) son pivot. Son pivot her zaman
    # en sağda olduğundan tek başına çizgiyi 9-barlık stub'a düşürür → önce
    # giriş seviyesinin oluştuğu swing noktasını ararız (asıl setup anı).
    giris_p = seviye.get("giris")
    taraf = (seviye.get("taraf") or "Long")
    setup_bar: int | None = None
    # Açık işlemde çizgilerin ve TP/STOP taramasının başlangıcı gerçek entry
    # mumudur; eski pivotlardan önceki fiyat hareketi sonuç sayılmaz.
    entry_zaman = seviye.get("entry_zaman")
    if entry_zaman:
        try:
            entry_ts = pd.Timestamp(entry_zaman)
            if entry_ts.tzinfo is None:
                entry_ts = entry_ts.tz_localize("UTC")
            else:
                entry_ts = entry_ts.tz_convert("UTC")
            idx_utc = df.index.tz_convert("UTC")
            uygun_idx = [i for i, ts in enumerate(idx_utc) if ts >= entry_ts]
            if uygun_idx:
                setup_bar = uygun_idx[0]
        except Exception:
            pass
    if (not entry_zaman and t and t.get("noktalar")
            and len(t["noktalar"]) >= 5):
        d_nokta = t["noktalar"][4]
        setup_bar = d_nokta[0] if isinstance(d_nokta, list) else int(d_nokta)
    if setup_bar is None and giris_p:
        try:
            from . import pivotlar as pv
            pivs = pv.pivot_listesi(df, n=5)
            # Long → giriş bir dip (L) pivotunda; Short → tepe (H) pivotunda.
            tip = "L" if taraf != "Short" else "H"
            uygun = [p for p in pivs if p[2] == tip] or pivs
            # Setup taze → D noktası yakın geçmişte. Girişe ±%2 yakın pivotlar
            # içinden EN GÜNCEL olanı seç (eski, fiyatı tesadüfen yakın bir
            # pivotu seçip çizgiyi grafiğin en soluna atmasın). Yoksa en yakın.
            yakin = [p for p in uygun if abs(p[1] - giris_p) <= giris_p * 0.02]
            if yakin:
                setup_bar = int(max(yakin, key=lambda p: p[0])[0])
            elif uygun:
                setup_bar = int(min(uygun, key=lambda p: abs(p[1] - giris_p))[0])
        except Exception:
            pass
    if setup_bar is None:
        setup_bar = max(0, len(mumlar) - 40)
    # Çizgi çok kısa kalmasın (en az ~25 bar uzasın) ama mumların solunu da
    # aşmasın — aşırı sağdaki pivotu makul bir başlangıca çek.
    if entry_zaman:
        setup_bar = max(0, min(setup_bar, max(0, len(mumlar) - 1)))
    else:
        setup_bar = max(0, min(setup_bar, max(0, len(mumlar) - 25)))

    def _zaman_idx(zaman):
        if not zaman:
            return None
        try:
            ts = pd.Timestamp(zaman)
            ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
            idx_utc = df.index.tz_convert("UTC")
            aday = [i for i, x in enumerate(idx_utc) if x >= ts]
            return aday[0] if aday else None
        except Exception:
            return None

    entry_idx = _zaman_idx(entry_zaman)
    # Legacy kapanış zamanı kesin sonuç mumu değildir; yalnız yeni atomik
    # sonuç_mum_zaman kaydı grafik durum makinesini kilitleyebilir.
    sonuc_zaman = seviye.get("sonuc_mum_zaman")
    sonuc_idx = _zaman_idx(sonuc_zaman)
    olaylar = {
        "setup_idx": setup_bar,
        "entry_idx": entry_idx,
        "entry_zaman": entry_zaman or "",
        "sonuc_idx": sonuc_idx,
        "sonuc_zaman": sonuc_zaman or "",
        "sonuc_tetik": seviye.get("sonuc_tetik") or "",
        "sonuc_mum_ohlc": seviye.get("sonuc_mum_ohlc") or {},
        "denetim_durumu": seviye.get("denetim_durumu") or "",
    }

    # PA konsept bölgeleri (Cavity/Root/Shade/Buffer zone kutuları + seviyeler)
    konseptler = []
    try:
        for isim, s in kons.tara_konseptler(df).items():
            konseptler.append({
                "isim": isim, "yon": s.yon, "guc": s.guc,
                "zone_alt": s.zone_alt, "zone_ust": s.zone_ust,
                "seviye": s.seviye, "idx": s.idx, "aciklama": s.aciklama})
    except Exception:
        pass

    # @tradermiraz tarzı plan yorumu (seçili setup için)
    m_yorum = None
    if seviye.get("taraf"):
        try:
            m_yorum = yorum.miraz_yorum(
                symbol, interval, seviye.get("taraf"),
                giris=seviye.get("giris"), stop=seviye.get("stop"),
                hedef=seviye.get("hedef"), rr=seviye.get("rr"),
                pattern=seviye.get("pattern"), konseptler=konseptler,
                kategori=seviye.get("kategori", "Watch"))
        except Exception:
            m_yorum = None

    return {
        "symbol": symbol, "interval": interval,
        "mumlar": mumlar,
        "macd": {"macd": _kolon(mac["macd"]), "sinyal": _kolon(mac["sinyal"]),
                 "hist": _kolon(mac["histogram"])},
        "seviye": {**seviye, "zone_alt": zone_alt, "zone_ust": zone_ust,
                   "setup_bar": setup_bar},
        "harmonik": harmonik,
        "konseptler": konseptler,
        "olaylar": olaylar,
        "miraz_yorum": m_yorum,
    }


# ---------------------------------------------------------------------------
# Durum deposu — tarama thread'i yazar, HTTP handler okur (kilitli)
# ---------------------------------------------------------------------------

class DurumDeposu:
    def __init__(self) -> None:
        self._kilit = threading.Lock()
        self._durum: dict = {"zaman": _simdi_iso(), "tarama_no": 0,
                             "hazir": False, "mesaj": "ilk tarama bekleniyor"}

    def yaz(self, durum: dict) -> None:
        durum["hazir"] = True
        with self._kilit:
            self._durum = durum

    def oku(self) -> dict:
        with self._kilit:
            return dict(self._durum)


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

def _handler_sinifi(depo: DurumDeposu, grafik_fn=None):
    index_yol = WEB_DIZIN / "index.html"

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):       # sessiz (terminali kirletme)
            pass

        def _gonder(self, kod, govde: bytes, tip: str):
            self.send_response(kod)
            self.send_header("Content-Type", tip)
            self.send_header("Content-Length", str(len(govde)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(govde)

        def _json(self, veri_, kod=200):
            self._gonder(kod, json.dumps(veri_, ensure_ascii=False).encode("utf-8"),
                         "application/json; charset=utf-8")

        def do_GET(self):
            from urllib.parse import urlparse, parse_qs
            p = urlparse(self.path)
            yol, sorgu = p.path, parse_qs(p.query)
            if yol in ("/", "/index.html"):
                try:
                    html = index_yol.read_bytes()
                except OSError:
                    html = b"<h1>index.html yok</h1>"
                self._gonder(200, html, "text/html; charset=utf-8")
            elif yol == "/api/durum":
                self._json(depo.oku())
            elif yol == "/api/grafik":
                sym = (sorgu.get("symbol") or [""])[0].upper()
                ivl = (sorgu.get("interval") or [""])[0]
                if not sym or not ivl or grafik_fn is None:
                    self._json({"hata": "symbol/interval gerekli"}, 400)
                    return
                try:
                    self._json(grafik_fn(sym, ivl))
                except Exception as e:
                    self._json({"hata": str(e)}, 500)
            else:
                self._gonder(404, b"yok", "text/plain; charset=utf-8")

    return Handler


# ---------------------------------------------------------------------------
# Sunucu — arka plan tarama + HTTP servis
# ---------------------------------------------------------------------------

class Sunucu:
    def __init__(self, semboller, intervallar, taraf="long", rr_hedef=1.0,
                 cluster_hafiza=None, r_dolar=25.0, gun=120, max_bekleme=24,
                 goreceli=False, aralik=180, port=8000, host="127.0.0.1",
                 portfoy=None, defter=None, borsa=None, otomatik=False,
                 max_bar=900,
                 defter_dosya=DEFTER_DOSYA, portfoy_dosya=PORTFOY_DOSYA):
        self.gozlemci = Gozlemci(
            semboller=semboller, intervallar=intervallar, taraf=taraf,
            rr_hedef=rr_hedef, cluster_hafiza=cluster_hafiza, r_dolar=r_dolar,
            gun=gun, max_bekleme=max_bekleme, goreceli=goreceli, max_bar=max_bar,
            portfoy=portfoy or Portfoy(r_dolar=r_dolar), defter=defter or Defter())
        self.max_bar = max_bar
        self.aralik = aralik
        self.port = port
        self.host = host
        self.borsa = borsa
        self.otomatik = otomatik and borsa is not None
        self.r_dolar = r_dolar
        self.defter_dosya = defter_dosya
        self.portfoy_dosya = portfoy_dosya
        self.depo = DurumDeposu()
        self._dur = threading.Event()
        self.semboller = semboller
        self.intervallar = intervallar
        self.taraf = taraf

    def _bir_tarama(self) -> None:
        # tarama sürerken canlı ilerleme (yüzde + akan adaylar) yaz — throttle
        son_yaz = [0.0]

        def _ilerleme(yapilan, toplam, rapor):
            import time as _t
            simdi = _t.time()
            if simdi - son_yaz[0] < 1.2 and yapilan < toplam:
                return
            son_yaz[0] = simdi
            d = durum_json(self.gozlemci, rapor, self.aralik, borsa=self.borsa)
            d["tarama_durumu"] = "taranıyor"
            d["ilerleme"] = {"yapilan": yapilan, "toplam": toplam,
                             "yuzde": round(100 * yapilan / toplam) if toplam
                             else 0}
            self.depo.yaz(d)

        sonuc = self.gozlemci.dongu(ilerleme=_ilerleme)
        self.gozlemci.kaydet(self.defter_dosya, self.portfoy_dosya)
        if self.otomatik:
            self._otomatik_emir(sonuc.rapor)
        d = durum_json(self.gozlemci, sonuc.rapor, self.aralik, borsa=self.borsa)
        d["tarama_durumu"] = "tamam"
        d["ilerleme"] = {"yapilan": len(self.semboller) * len(self.intervallar),
                         "toplam": len(self.semboller) * len(self.intervallar),
                         "yuzde": 100}
        self.depo.yaz(d)

    def _otomatik_emir(self, rapor) -> None:
        """(opt-in) Yeni Trade adayları için testnet bracket emri açar.

        Aynı sembolde açık pozisyon/emir varsa atlar (çift gönderimi önler).
        """
        from .kiraz import emir_plani, KirazMotor
        try:
            acik_sem = {p["symbol"] for p in self.borsa.pozisyonlar()}
            acik_sem |= {o.get("symbol") for o in self.borsa.acik_emirler()}
        except Exception:
            return
        motor = KirazMotor(self.borsa)
        for s in rapor.satirlar:
            if s.kategori != "Trade" or s.symbol in acik_sem:
                continue
            plan = emir_plani(s, r_dolar=self.r_dolar)
            if plan.gecerli:
                try:
                    motor.uygula(plan, kuru=False)
                    acik_sem.add(s.symbol)
                except Exception:
                    pass

    def grafik_veri(self, symbol: str, interval: str) -> dict:
        return grafik_veri(symbol, interval, durum=self.depo.oku(),
                           gun=self.gozlemci.gun, max_bar=self.max_bar)

    def _tarama_dongusu(self) -> None:
        while not self._dur.is_set():
            try:
                self._bir_tarama()
            except Exception as e:       # bir tarama patlasa da sunucu yaşasın
                self.depo.yaz({"zaman": _simdi_iso(), "hazir": False,
                              "mesaj": f"tarama hatası: {e}"})
            self._dur.wait(self.aralik)

    def basla(self) -> None:
        """Tarama thread'ini başlatır ve HTTP sunucusunu (bloklayan) çalıştırır."""
        t = threading.Thread(target=self._tarama_dongusu, daemon=True)
        t.start()
        httpd = ThreadingHTTPServer((self.host, self.port),
                                    _handler_sinifi(self.depo, self.grafik_veri))
        print(f"🟢 Sunucu çalışıyor → http://{self.host}:{self.port}")
        print(f"   {len(self.semboller)} parite × {len(self.intervallar)} TF "
              f"({' '.join(self.intervallar)}) · {self.taraf} · "
              f"her {self.aralik} sn tarama")
        print("   Tarayıcıdan yukarıdaki adresi aç. Durdurmak için Ctrl+C.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Sunucu durduruldu.")
        finally:
            self._dur.set()
            httpd.server_close()
