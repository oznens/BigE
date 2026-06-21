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
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .gozlemci import Gozlemci, Defter, DEFTER_DOSYA, PORTFOY_DOSYA
from .portfoy import Portfoy

WEB_DIZIN = Path(__file__).resolve().parent / "web"


def _simdi_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Durum → JSON anlık görüntüsü (saf fonksiyon, test edilebilir)
# ---------------------------------------------------------------------------

def _satir_json(s) -> dict:
    return {
        "symbol": s.symbol, "interval": s.interval, "fiyat": s.fiyat,
        "kategori": s.kategori, "kalite": s.kalite, "guven": s.guven,
        "taraf": s.taraf, "kaynak": getattr(s, "kaynak", "Price Action"),
        "pattern": getattr(s, "pattern", None), "giris": s.giris,
        "stop": s.stop, "hedef": s.hedef, "rr": s.rr, "not_": s.not_,
    }


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


def durum_json(gozlemci: Gozlemci, rapor, aralik: int) -> dict:
    """Gözlemci + son radar raporundan tarayıcının ihtiyaç duyduğu tam durum."""
    defter = gozlemci.defter
    portfoy = gozlemci.portfoy
    d_ozet = defter.ozet()
    pnl = defter.pnl_analitik()

    # execution metrikleri (paper-trading portföyünden)
    r_dolar = getattr(portfoy, "r_dolar", 25.0) or 25.0
    poz = getattr(portfoy, "pozisyonlar", [])
    aktif = [p for p in poz if p.durum == "Açık"]
    bekleyen = [p for p in poz if p.durum == "Bekliyor"]
    toplam_r = getattr(portfoy, "toplam_r", 0.0) or 0.0
    equity = 5000.0 + toplam_r * r_dolar
    open_risk = round(len(aktif) * r_dolar / equity * 100, 1) if equity else 0.0
    kiraz_durum, kiraz_mesaj = _kiraz_status(rapor)

    # canlı aday akışı (Trade + Watch, güvene göre)
    adaylar = [s for s in rapor.satirlar if s.kategori in ("Trade", "Watch")]
    adaylar.sort(key=lambda s: (0 if s.kategori == "Trade" else 1, -s.guven))

    # sonuç bildirimleri (defterdeki son kapanan kayıtlar)
    kapanan = [k for k in defter.kayitlar if not k.aktif][-12:][::-1]
    bildirimler = [{
        "sembol": k.sembol, "interval": k.interval, "durum": k.durum,
        "taraf": k.taraf, "kaynak": getattr(k, "kaynak", "Price Action"),
        "pattern": k.pattern, "giris": k.giris, "stop": k.stop,
        "hedef": k.hedef, "r_sonuc": k.r_sonuc,
        "kapanis": (k.kapanis_zaman or "")[:16],
    } for k in kapanan]

    return {
        "zaman": _simdi_iso(),
        "tarama_no": defter.tarama_turu,
        "toplam_tarama": defter.toplam_tarama,
        "aralik": aralik,
        "ozet": rapor.ozet,
        "durum_cubugu": {
            "kiraz": True, "sql_memory": True,
            "order_engine": portfoy is not None,
        },
        "execution": {
            "wallet": round(equity, 1), "aktif": len(aktif),
            "bekleyen": len(bekleyen), "daily_pnl": round(toplam_r, 1),
            "open_risk": open_risk, "r_dolar": r_dolar,
            "kiraz_durum": kiraz_durum, "kiraz_mesaj": kiraz_mesaj,
        },
        "buckets": d_ozet["buckets"],
        "lifecycle": {
            "Filtered": d_ozet["Filtered"], "Shelved": d_ozet["Shelved"],
            "No-Entry": d_ozet["No-Entry"], "Expired": d_ozet["Expired"],
            "Cancelled": d_ozet["Cancelled"],
        },
        "wr": d_ozet["wr"], "toplam_r": d_ozet["toplam_r"],
        "aktif_kayit": d_ozet["aktif"],
        "adaylar": [_satir_json(s) for s in adaylar[:16]],
        "bildirimler": bildirimler,
        "pnl": pnl,
        "memory": {"parite": pnl["parite"], "tf": pnl["tf"],
                   "konsept": pnl["konsept"]},
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

def _handler_sinifi(depo: DurumDeposu):
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

        def do_GET(self):
            yol = self.path.split("?")[0]
            if yol in ("/", "/index.html"):
                try:
                    html = index_yol.read_bytes()
                except OSError:
                    html = b"<h1>index.html yok</h1>"
                self._gonder(200, html, "text/html; charset=utf-8")
            elif yol == "/api/durum":
                govde = json.dumps(depo.oku(), ensure_ascii=False).encode("utf-8")
                self._gonder(200, govde, "application/json; charset=utf-8")
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
                 portfoy=None, defter=None,
                 defter_dosya=DEFTER_DOSYA, portfoy_dosya=PORTFOY_DOSYA):
        self.gozlemci = Gozlemci(
            semboller=semboller, intervallar=intervallar, taraf=taraf,
            rr_hedef=rr_hedef, cluster_hafiza=cluster_hafiza, r_dolar=r_dolar,
            gun=gun, max_bekleme=max_bekleme, goreceli=goreceli,
            portfoy=portfoy or Portfoy(r_dolar=r_dolar), defter=defter or Defter())
        self.aralik = aralik
        self.port = port
        self.host = host
        self.defter_dosya = defter_dosya
        self.portfoy_dosya = portfoy_dosya
        self.depo = DurumDeposu()
        self._dur = threading.Event()
        self.semboller = semboller
        self.intervallar = intervallar
        self.taraf = taraf

    def _bir_tarama(self) -> None:
        sonuc = self.gozlemci.dongu()
        self.gozlemci.kaydet(self.defter_dosya, self.portfoy_dosya)
        self.depo.yaz(durum_json(self.gozlemci, sonuc.rapor, self.aralik))

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
                                    _handler_sinifi(self.depo))
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
