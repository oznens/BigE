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

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "src"))

from miraz.gozlemci import Gozlemci, Defter             # noqa: E402
from miraz.portfoy import Portfoy                       # noqa: E402
from miraz.radar import (CEKIRDEK_EVREN, GENIS_EVREN,   # noqa: E402
                         TERMINALMIRAZ_TF)
from miraz.sunucu import durum_json, grafik_veri, WEB_DIZIN  # noqa: E402

PAGES_URL = "https://oznens.github.io/BigE"


def _yaz_json(yol: Path, veri: dict) -> None:
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(json.dumps(veri, ensure_ascii=False), encoding="utf-8")


def _onceki_state(cikti: Path, onceki_url: str | None) -> tuple[Defter, Portfoy]:
    """Önceki tarama hafızasını (defter+portföy) yükler."""
    d_yol = cikti / "defter.json"
    p_yol = cikti / "portfoy.json"
    if onceki_url:
        taban = onceki_url.rstrip("/")
        for ad, yol in (("defter.json", d_yol), ("portfoy.json", p_yol)):
            try:
                with urllib.request.urlopen(f"{taban}/{ad}", timeout=15) as r:
                    yol.write_bytes(r.read())
            except Exception:
                pass
    defter = Defter.yukle(d_yol) if d_yol.exists() else Defter()
    try:
        portfoy = Portfoy.yukle(p_yol) if p_yol.exists() else Portfoy()
    except Exception:
        portfoy = Portfoy()
    return defter, portfoy


def _playback_trade_memory(defter: Defter, n: int = 30) -> list[dict]:
    """Playback'e yalnız gerçekleşmiş TP/STOP işlemlerini ver.

    Expired/No-Entry/Cancelled/Manuel gibi lifecycle kayıtları playback değildir.
    Ayrıca replay'in setup anına ve sonucuna hizalanabilmesi için giriş/stop/TP
    seviyeleri ile açılış/kapanış zamanlarını eksiksiz yayınlarız.
    """
    kapali = sorted(
        [k for k in defter.kayitlar
         if k.durum in ("TP", "STOP") and k.kapanis_zaman],
        key=lambda k: k.kapanis_zaman,
        reverse=True,
    )[:n]
    return [{
        "id": k.id,
        "sembol": k.sembol,
        "interval": k.interval,
        "durum": k.durum,
        "taraf": k.taraf,
        "kaynak": getattr(k, "kaynak", "Price Action"),
        "pattern": k.pattern,
        "r_sonuc": round(k.r_sonuc, 2),
        "guven": round(k.guven, 0),
        "kalite": k.kalite,
        "giris": k.giris,
        "stop": k.stop,
        "hedef": k.hedef,
        "rr": k.rr,
        "acilis": k.acilis_zaman or "",
        "kapanis": k.kapanis_zaman or "",
    } for k in kapali]


def _grafik_hedefleri(durum: dict) -> list[tuple[str, str]]:
    """Snapshot'ta grafik gereken tüm sembol/TF çiftleri.

    Playback eski kapanmış işlemleri de açabildiği için trade_memory mutlaka
    hedeflere dahil edilir; aksi halde Pages'te grafik JSON'u bulunmaz (404).
    """
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
      pbRender();
      pbHafizaGoster(t);
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
})();
</script>
"""


def uret(cikti: Path, semboller: list[str], intervallar: list[str],
         taraf: str, max_bar: int, aralik: int, gun: int,
         onceki_url: str | None = PAGES_URL) -> None:
    cikti.mkdir(parents=True, exist_ok=True)

    defter, portfoy = _onceki_state(cikti, onceki_url)
    print(f"📓 Önceki hafıza: {len(defter.kayitlar)} kayıt · "
          f"{len(portfoy.pozisyonlar)} pozisyon")

    goz = Gozlemci(semboller=semboller, intervallar=intervallar, taraf=taraf,
                   goreceli=False, gun=gun, max_bar=max_bar,
                   defter=defter, portfoy=portfoy)
    print(f"⏳ Tarama: {len(semboller)} parite × {len(intervallar)} TF "
          f"({' '.join(intervallar)}) · {taraf}")
    sonuc = goz.dongu()
    durum = durum_json(goz, sonuc.rapor, aralik)
    durum["tarama_durumu"] = "tamam"
    durum["statik"] = True
    durum["hazir"] = True

    durum["trade_memory"] = _playback_trade_memory(goz.defter)
    _yaz_json(cikti / "durum.json", durum)
    print(f"✅ durum.json — {durum['ozet']} · playback {len(durum['trade_memory'])} TP/STOP")

    goz.defter.kaydet(cikti / "defter.json")
    goz.portfoy.kaydet(cikti / "portfoy.json")
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
    print(f"✅ index.html (statik + playback patch) → {cikti}")


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