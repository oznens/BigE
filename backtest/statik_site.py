#!/usr/bin/env python3
"""Statik site üreteci — GitHub Pages için tek seferlik tarama snapshot'ı.

Sürekli açık bir sunucu yerine, GitHub Actions cron'u bu betiği her N dakikada
bir çalıştırır; çıktı statik dosyalar olarak Pages'e yayınlanır:

    <cikti>/index.html              (panel — statik moda ayarlı)
    <cikti>/durum.json              (son tarama anlık görüntüsü)
    <cikti>/grafik/<SYM>_<TF>.json  (her aday/playback işlemi için grafik verisi)

Panel `window.STATIK=true` ile bu dosyaları okur (canlı /api/* yerine).
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import urllib.request
from pathlib import Path

import pandas as pd

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "src"))

from miraz.gozlemci import Gozlemci, Defter             # noqa: E402
from miraz.portfoy import Portfoy                       # noqa: E402
from miraz.radar import (CEKIRDEK_EVREN, GENIS_EVREN,   # noqa: E402
                         TERMINALMIRAZ_TF)
from miraz.sunucu import durum_json, grafik_veri, WEB_DIZIN  # noqa: E402
from miraz import veri as miraz_veri                    # noqa: E402

PAGES_URL = "https://oznens.github.io/BigE"
# Bu değer bilinçli değiştirildiğinde önceki canlı Journal/portföy taşınmaz.
# Kanıt arşivi ve motor kuralları etkilenmez; yalnız çalışma state'i sıfırlanır.
STATE_EPOCH = "2026-08-11-clean-start-v1"
FEE_BPS_TARAF = 4.0
SLIPPAGE_BPS_TARAF = 2.0
FUNDING_BPS_TOPLAM = 0.0


def _yaz_json(yol: Path, veri: dict) -> None:
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(json.dumps(veri, ensure_ascii=False), encoding="utf-8")


def _onceki_state(cikti: Path, onceki_url: str | None) -> tuple[Defter, Portfoy]:
    """Önceki tarama hafızasını (defter+portföy) yükler."""
    d_yol = cikti / "defter.json"
    p_yol = cikti / "portfoy.json"
    e_yol = cikti / "state_epoch.json"
    if onceki_url:
        taban = onceki_url.rstrip("/")
        for ad, yol in (("defter.json", d_yol), ("portfoy.json", p_yol),
                        ("state_epoch.json", e_yol)):
            try:
                with urllib.request.urlopen(f"{taban}/{ad}", timeout=15) as r:
                    yol.write_bytes(r.read())
            except Exception:
                pass
        try:
            onceki_epoch = json.loads(e_yol.read_text(encoding="utf-8")).get("epoch")
        except Exception:
            onceki_epoch = None
        if onceki_epoch != STATE_EPOCH:
            # Eski dönemin istatistik ve pozisyonlarını yeni başlangıca taşıma.
            d_yol.unlink(missing_ok=True)
            p_yol.unlink(missing_ok=True)
    defter = Defter.yukle(d_yol) if d_yol.exists() else Defter()
    try:
        portfoy = Portfoy.yukle(p_yol) if p_yol.exists() else Portfoy()
    except Exception:
        portfoy = Portfoy()
    return defter, portfoy


def _playback_trade_memory(defter: Defter, n: int = 30) -> list[dict]:
    """Playback'e sonuçlanan trade ve kayıtlı harmonik iptalleri ver."""
    kapali = sorted(
        [k for k in defter.kayitlar
         if (k.durum in ("TP", "STOP") or
             (k.pattern and k.durum == "Cancelled")) and k.kapanis_zaman],
        key=lambda k: k.kapanis_zaman,
        reverse=True,
    )[:n]
    out = []
    for k in kapali:
        maliyet_r = _maliyet_r(k.giris, k.stop)
        out.append({
            "id": k.id,
            "sembol": k.sembol,
            "interval": k.interval,
            "durum": k.durum,
            "taraf": k.taraf,
            "kaynak": getattr(k, "kaynak", "Price Action"),
            "pattern": k.pattern,
            "r_sonuc": round(k.r_sonuc, 2),
            "maliyet_r": round(maliyet_r, 3),
            "net_r": round(k.r_sonuc - maliyet_r, 3),
            "guven": round(k.guven, 0),
            "kalite": k.kalite,
            "giris": k.giris,
            "stop": k.stop,
            "hedef": k.hedef,
            "rr": k.rr,
            "acilis": k.acilis_zaman or "",
            "kapanis": k.kapanis_zaman or "",
            "kalite_gecmisi": list(getattr(k, "kalite_gecmisi", [])),
            "kalite_degisim_sayisi": max(
                0, len(getattr(k, "kalite_gecmisi", [])) - 1),
            "harmonik_detay": dict(getattr(k, "harmonik_detay", {}) or {}),
            "harmonik_gecmisi": list(getattr(k, "harmonik_gecmisi", []) or []),
            "entry_zaman": getattr(k, "entry_zaman", "") or None,
            "entry_zaman_durumu": ("recorded-entry-touch-bar" if
                                     getattr(k, "entry_zaman", "") else
                                     "legacy-not-recorded"),
            # Arşiv tweeti 2056806486127346084 playback'in yalnız sonucu değil,
            # setup oluşumunu ve fiyatın izlediği süreci de göstermesini tarif eder.
            # Defterde bulunmayan "kararsızlık" anlarını uydurmuyoruz; yalnız
            # kaydedilmiş setup/sonuç zamanlarını ve gerçek mum akışını sunuyoruz.
            "surec": [
                {"asama": "SETUP OLUŞUMU", "zaman": k.acilis_zaman or ""},
                {"asama": "SONUÇ", "zaman": k.kapanis_zaman or "",
                 "durum": k.durum},
            ],
            "playback_kanit": {
                "tweet_id": "2056806486127346084",
                "kapsam": "setup-olusumu-fiyat-sureci-sonuc",
                "kararsizlik_etiketi": "kayit-yoksa-uretilmez",
                "harmonik_olay_politikasi": "recorded-events-only-no-backfill",
            },
        })
    return out


def _maliyet_r(giris: float, stop: float,
               fee_bps: float = FEE_BPS_TARAF,
               slippage_bps: float = SLIPPAGE_BPS_TARAF,
               funding_bps: float = FUNDING_BPS_TOPLAM) -> float:
    """Round-trip işlem maliyetini stop mesafesine göre R cinsine çevirir."""
    try:
        giris = float(giris)
        stop = float(stop)
        if giris <= 0:
            return 0.0
        risk_frac = abs(giris - stop) / giris
        if risk_frac <= 1e-9:
            return 0.0
        toplam_bps = 2.0 * (float(fee_bps) + float(slippage_bps)) + float(funding_bps)
        return (toplam_bps / 10000.0) / risk_frac
    except Exception:
        return 0.0


def _seviyeler_uyumlu(k, p) -> bool:
    """Legacy yanlış journal↔pozisyon eşleşmelerini performanstan ayıkla."""
    if p is None:
        return False
    for a, b in ((k.giris, p.giris), (k.stop, p.stop), (k.hedef, p.hedef)):
        try:
            a, b = float(a), float(b)
            ref = max(abs(a), 1e-9)
            if abs(a - b) / ref > 0.005:
                return False
        except Exception:
            return False
    return True


def _maliyet_ozeti(defter: Defter, portfoy: Portfoy) -> dict:
    """Yalnız doğrulanmış TP/STOP kayıtlarında Gross/Cost/Net R üretir."""
    poz_idx = {p.id: p for p in portfoy.pozisyonlar}
    gross = cost = 0.0
    n = tp = stop_n = legacy = 0
    for k in defter.kayitlar:
        if k.durum not in ("TP", "STOP"):
            continue
        p = poz_idx.get(getattr(k, "poz_id", -1))
        if not _seviyeler_uyumlu(k, p):
            legacy += 1
            continue
        c = _maliyet_r(k.giris, k.stop)
        gross += float(k.r_sonuc)
        cost += c
        n += 1
        if k.durum == "TP":
            tp += 1
        else:
            stop_n += 1
    net = gross - cost
    return {
        "dogrulanmis_islem": n,
        "legacy_haric": legacy,
        "tp": tp,
        "stop": stop_n,
        "wr": round(100.0 * tp / n, 2) if n else 0.0,
        "gross_r": round(gross, 2),
        "maliyet_r": round(cost, 2),
        "net_r": round(net, 2),
        "net_expectancy_r": round(net / n, 4) if n else 0.0,
        "fee_bps_taraf": FEE_BPS_TARAF,
        "slippage_bps_taraf": SLIPPAGE_BPS_TARAF,
        "funding_bps_toplam": FUNDING_BPS_TOPLAM,
    }


def _kapanis_barini_bul(poz, onceki_durum: str, onceki_kontrol: str,
                        df: pd.DataFrame, max_bekleme: int = 24):
    """Bu turda kapanan pozisyonun gerçek OHLCV bar zamanını yeniden bulur."""
    if df is None or df.empty:
        return None
    try:
        bas = pd.Timestamp(onceki_kontrol or poz.acilis_zaman)
        if bas.tzinfo is None:
            bas = bas.tz_localize("UTC")
        else:
            bas = bas.tz_convert("UTC")
        alt = df[df.index > bas]
        if alt.empty:
            return None
        acilis = pd.Timestamp(poz.acilis_zaman) if poz.acilis_zaman else None
        if acilis is not None:
            acilis = acilis.tz_localize("UTC") if acilis.tzinfo is None else acilis.tz_convert("UTC")
        acik = onceki_durum == "Açık"
        short = poz.yon == "Short"
        for ts, row in alt.iterrows():
            if not acik:
                if acilis is not None:
                    gecen = int(((df.index > acilis) & (df.index <= ts)).sum())
                    if gecen > max_bekleme:
                        return ts
                doldu = float(row["high"]) >= poz.giris if short else float(row["low"]) <= poz.giris
                if doldu:
                    acik = True
            if acik:
                stop_vurdu = float(row["close"]) > poz.stop if short else float(row["close"]) < poz.stop
                tp_vurdu = float(row["low"]) <= poz.hedef if short else float(row["high"]) >= poz.hedef
                if stop_vurdu or tp_vurdu:
                    return ts
        if poz.durum == "Expired":
            return alt.index[-1]
    except Exception:
        return None
    return None


def _duzelt_kapanis_zamanlari(goz: Gozlemci, degisenler: list,
                               onceki: dict, gun: int, max_bar: int) -> int:
    """Yeni TP/STOP/Expired sonuçlarını tarama saati yerine gerçek bar saatine bağlar."""
    kapanan = {}
    for p in degisenler or []:
        if p.durum in ("TP", "STOP", "Expired"):
            kapanan[p.id] = p
    if not kapanan:
        return 0

    cache = {}
    duzeltilen = 0
    kayit_idx = {getattr(k, "poz_id", -1): k for k in goz.defter.kayitlar}
    for pid, p in kapanan.items():
        # Yeni motor TP/STOP mumunu, tetik türünü ve OHLC kanıtını atomik olarak
        # kaydeder. Bu zincirin yalnız zaman alanını sonradan yeniden yazmak
        # kanıtı tutarsızlaştırır; düzeltme yalnız legacy/Expired içindir.
        if p.durum in ("TP", "STOP") and getattr(p, "sonuc_mum_zaman", ""):
            continue
        onceki_durum, onceki_kontrol = onceki.get(pid, ("Bekliyor", p.son_kontrol_zaman))
        anahtar = (p.sembol, p.interval)
        if anahtar not in cache:
            try:
                cache[anahtar] = miraz_veri.indir(
                    p.sembol, p.interval, gun=gun, force=True, max_bar=max_bar)
            except Exception:
                cache[anahtar] = None
        ts = _kapanis_barini_bul(p, onceki_durum, onceki_kontrol, cache[anahtar])
        if ts is None:
            continue
        iso = ts.isoformat()
        p.kapanis_zaman = iso
        k = kayit_idx.get(pid)
        if k is not None:
            k.kapanis_zaman = iso
        duzeltilen += 1
    return duzeltilen


def _grafik_hedefleri(durum: dict) -> list[tuple[str, str]]:
    """Snapshot'ta grafik gereken tüm sembol/TF çiftleri."""
    cift = set()
    for a in durum.get("adaylar", []):
        if a.get("symbol") and a.get("interval"):
            cift.add((a["symbol"], a["interval"]))
    for b in durum.get("bildirimler", []):
        if b.get("sembol") and b.get("interval"):
            cift.add((b["sembol"], b["interval"]))
    for t in durum.get("trade_memory", []):
        if t.get("sembol") and t.get("interval"):
            cift.add((t["sembol"], t["interval"]))
    # Entry olmuş açık işlemler önceki taramalardan taşınabilir ve güncel aday
    # listesinde bulunmayabilir. Kartları tıklanınca grafik açılabilmesi için
    # bunların sembol/TF dosyalarını da her statik yayında yeniden üret.
    for t in durum.get("aktif_tradeler", []):
        if t.get("sembol") and t.get("interval"):
            cift.add((t["sembol"], t["interval"]))
    vg = durum.get("varsayilan_grafik") or {}
    if vg.get("symbol"):
        cift.add((vg["symbol"], vg["interval"]))
    return sorted(cift)


_PLAYBACK_PATCH = r"""
<script>
(function(){
  const _pbListe = pbRenderListe;
  pbRenderListe = function(tms){
    const done=(tms||[]).filter(t=>t && (t.durum==="TP" || t.durum==="STOP"));
    _pbListe(done);
  };

  function barIdx(m, iso){
    if(!m || !m.length || !iso) return -1;
    const ts=Date.parse(iso);
    if(!Number.isFinite(ts)) return -1;
    const sec=ts/1000;
    let best=0, fark=Infinity;
    for(let i=0;i<m.length;i++){
      const d=Math.abs((m[i]?.[0]||0)-sec);
      if(d<fark){fark=d;best=i;}
    }
    return best;
  }

  pbSec = async function(idx){
    pbSecili=idx; pbBar=0;
    if(pbOynatTimer){clearInterval(pbOynatTimer);pbOynatTimer=null;$("#pb-oynat").textContent="▶ OYNAT";}
    const t=pbTrades[idx];
    if(!t || (t.durum!=="TP" && t.durum!=="STOP")) return;
    $("#pb-baslik").textContent=`TRADE PLAYBACK · ${t.sembol} ${t.interval}`;
    $("#pb-durum").textContent=t.durum;
    $("#pb-durum").className=`badge ${t.durum==="TP"?"b-trade":"b-watch"}`;
    pbRenderListe(pbTrades);
    try{
      pbGrafVeri=await(await fetch(API_GRAFIK(t.sembol,t.interval),{cache:"no-store"})).json();
      if(pbGrafVeri.hata) throw new Error(pbGrafVeri.hata);
      const m=pbGrafVeri.mumlar||[];
      const setup=barIdx(m,t.acilis);
      const kapanis=barIdx(m,t.kapanis);
      pbGrafVeri.seviye={
        ...(pbGrafVeri.seviye||{}),
        giris:t.giris, stop:t.stop, hedef:t.hedef, rr:t.rr,
        taraf:t.taraf||"Long", pattern:t.pattern||null,
        kaynak:t.kaynak||"Price Action",
        setup_bar:setup>=0?setup:Math.max(0,Math.floor(m.length*.35))
      };
      pbBar=Math.max(5, Math.min(m.length, (setup>=0?setup:0)+1));
      pbGrafVeri._playbackSon = kapanis>=0 ? Math.min(m.length,kapanis+1) : m.length;
      pbHafizaGoster(t);
      pbRender();
    }catch(e){ $("#pb-info").textContent="grafik yüklenemedi: "+(e.message||e); }
  };

  pbAdim=function(n){
    if(!pbGrafVeri) return;
    const max=pbGrafVeri._playbackSon || (pbGrafVeri.mumlar||[]).length;
    pbBar=Math.max(5,Math.min(max,pbBar+n));
    pbRender();
  };

  pbOynat=function(){
    if(pbOynatTimer){clearInterval(pbOynatTimer);pbOynatTimer=null;$("#pb-oynat").textContent="▶ OYNAT";return;}
    if(!pbGrafVeri) return;
    $("#pb-oynat").textContent="⏸ DURDUR";
    pbOynatTimer=setInterval(()=>{
      const max=pbGrafVeri._playbackSon || (pbGrafVeri.mumlar||[]).length;
      if(pbBar>=max){clearInterval(pbOynatTimer);pbOynatTimer=null;$("#pb-oynat").textContent="▶ OYNAT";return;}
      pbBar=Math.min(max,pbBar+1); pbRender();
    },180);
  };

  // Gross/Net ayrımı: kullanıcıya paper sonucu gerçek net kâr gibi gösterme.
  const ozet=document.getElementById("ozetsatir");
  if(ozet && !document.getElementById("net-r-ozet")){
    const n=document.createElement("div");
    n.id="net-r-ozet";
    n.style.cssText="margin:6px 0 10px;padding:8px 10px;border:1px solid var(--kenar);border-radius:6px;background:var(--panel2);font-size:11px;color:var(--soluk)";
    ozet.insertAdjacentElement("afterend",n);
  }
  setInterval(()=>{
    const m=(typeof sonDurum!=="undefined" && sonDurum && sonDurum.maliyet)||null;
    const el=document.getElementById("net-r-ozet");
    if(!m||!el) return;
    const sg=v=>(v>=0?"+":"")+(+v).toFixed(2)+"R";
    el.innerHTML=`DOĞRULANMIŞ ${m.dogrulanmis_islem} işlem · WR %${m.wr} · `+
      `Gross <b style="color:var(--metin)">${sg(m.gross_r)}</b> · `+
      `Maliyet <b style="color:var(--kirmizi)">-${(+m.maliyet_r).toFixed(2)}R</b> · `+
      `Net <b style="color:${m.net_r>=0?'var(--yesil)':'var(--kirmizi)'}">${sg(m.net_r)}</b> · `+
      `Expectancy ${sg(m.net_expectancy_r)} · `+
      `${m.legacy_haric} eski uyumsuz kayıt hariç · maliyet: ${m.fee_bps_taraf}+${m.slippage_bps_taraf} bps/side`;
  },1000);
})();
</script>
"""


def uret(cikti: Path, semboller: list[str], intervallar: list[str],
         taraf: str, max_bar: int, aralik: int, gun: int,
         onceki_url: str | None = PAGES_URL) -> None:
    cikti.mkdir(parents=True, exist_ok=True)

    defter, portfoy = _onceki_state(cikti, onceki_url)
    onceki_poz = {p.id: (p.durum, p.son_kontrol_zaman) for p in portfoy.pozisyonlar}
    print(f"📓 Önceki hafıza: {len(defter.kayitlar)} kayıt · "
          f"{len(portfoy.pozisyonlar)} pozisyon")

    goz = Gozlemci(semboller=semboller, intervallar=intervallar, taraf=taraf,
                   goreceli=False, gun=gun, max_bar=max_bar,
                   defter=defter, portfoy=portfoy)
    print(f"⏳ Tarama: {len(semboller)} parite × {len(intervallar)} TF "
          f"({' '.join(intervallar)}) · {taraf}")
    sonuc = goz.dongu()

    duz_n = _duzelt_kapanis_zamanlari(
        goz, sonuc.degisenler, onceki_poz, gun=gun, max_bar=max_bar)
    if duz_n:
        print(f"🕒 {duz_n} kapanış gerçek OHLCV bar zamanına düzeltildi")

    durum = durum_json(goz, sonuc.rapor, aralik)
    durum["tarama_durumu"] = "tamam"
    durum["statik"] = True
    durum["hazir"] = True
    durum["maliyet"] = _maliyet_ozeti(goz.defter, goz.portfoy)
    durum["trade_memory"] = _playback_trade_memory(goz.defter)
    durum["playback_policy"] = {
        "mode": "candle-by-candle",
        "scope": "closed-tp-stop",
        "evidence_tweet_ids": ["2056806486127346084"],
        "shows": ["setup-formation", "price-process", "result"],
        "undisclosed": ["indecision-detection-rule"],
    }
    _yaz_json(cikti / "durum.json", durum)
    print(f"✅ durum.json — {durum['ozet']} · playback {len(durum['trade_memory'])} TP/STOP · "
          f"net {durum['maliyet']['net_r']:+.2f}R")

    goz.defter.kaydet(cikti / "defter.json")
    goz.portfoy.kaydet(cikti / "portfoy.json")
    _yaz_json(cikti / "state_epoch.json", {"epoch": STATE_EPOCH})
    print(f"✅ defter.json + portfoy.json — {len(goz.defter.kayitlar)} kayıt taşındı")

    grafik_dizin = cikti / "grafik"
    if grafik_dizin.exists():
        shutil.rmtree(grafik_dizin)
    hedefler = _grafik_hedefleri(durum)
    basarili = 0
    for sym, ivl in hedefler:
        try:
            g = grafik_veri(sym, ivl, durum=durum, gun=gun, bar=320,
                            max_bar=max_bar)
            _yaz_json(grafik_dizin / f"{sym}_{ivl}.json", g)
            basarili += 1
        except Exception as e:
            print(f"  ⚠️ grafik {sym}/{ivl}: {e}")
    print(f"✅ grafik/ — {basarili}/{len(hedefler)} dosya")

    html = (WEB_DIZIN / "index.html").read_text(encoding="utf-8")
    html, n = re.subn(r"window\.STATIK\s*=\s*false",
                      "window.STATIK = true", html)
    if n == 0:
        raise SystemExit("HATA: index.html'de 'window.STATIK = false' bulunamadı")
    if "</body>" not in html:
        raise SystemExit("HATA: index.html body kapanışı bulunamadı")
    html = html.replace("</body>", _PLAYBACK_PATCH + "\n</body>", 1)
    (cikti / "index.html").write_text(html, encoding="utf-8")
    (cikti / ".nojekyll").write_text("", encoding="utf-8")
    print(f"✅ index.html (statik + playback/net patch) → {cikti}")


def main() -> None:
    ap = argparse.ArgumentParser(description="GitHub Pages statik tarama snapshot'ı")
    ap.add_argument("--cikti", default="site", help="çıktı dizini (varsayılan: site)")
    ap.add_argument("--genis", action="store_true", help="geniş evren (92 parite)")
    ap.add_argument("--mtf", action="store_true",
                    help=f"terminalMiraz {len(TERMINALMIRAZ_TF)} TF: "
                         f"{' '.join(TERMINALMIRAZ_TF)}")
    ap.add_argument("--tf", nargs="+", default=["1h"], help="--mtf yoksa TF listesi")
    ap.add_argument("--taraf", default="her", choices=["long", "short", "her"])
    ap.add_argument("--max-bar", type=int, default=900)
    ap.add_argument("--gun", type=int, default=120)
    ap.add_argument("--aralik", type=int, default=1800, help="snapshot tarama aralığı (sn)")
    ap.add_argument("--onceki-url", default=PAGES_URL,
                    help="önceki hafızanın indirileceği canlı Pages tabanı")
    args = ap.parse_args()

    semboller = GENIS_EVREN if args.genis else CEKIRDEK_EVREN
    intervallar = TERMINALMIRAZ_TF if args.mtf else args.tf
    uret(Path(args.cikti), semboller, intervallar, args.taraf,
         args.max_bar, args.aralik, args.gun, onceki_url=args.onceki_url or None)


if __name__ == "__main__":
    main()
