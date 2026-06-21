"""Veri çekme testleri — MEXC Futures (birincil) + Spot (yedek), ağ taklit."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz import veri


def test_fut_sembol():
    assert veri._fut_sembol("BTCUSDT") == "BTC_USDT"
    assert veri._fut_sembol("1000PEPEUSDT") == "1000PEPE_USDT"
    assert veri._fut_sembol("ETHUSDC") == "ETH_USDC"
    assert veri._fut_sembol("BTC_USDT") == "BTC_USDT"      # zaten dönüşmüş


class _Cevap:
    status_code = 200
    headers: dict = {}
    def __init__(self, govde):
        self._g = govde
    def raise_for_status(self):
        pass
    def json(self):
        return self._g


def test_mexc_futures_cek_dizi_yanit(monkeypatch):
    """Futures dizi yanıtı 8-kolon satıra çevrilir (ms zaman, doğru OHLC)."""
    cagri = {}

    def sahte_get(url, params=None, **k):
        cagri["url"] = url
        cagri["params"] = params
        return _Cevap({"success": True, "code": 0, "data": {
            "time": [1700000000, 1700003600], "open": [100, 101],
            "high": [102, 103], "low": [99, 100], "close": [101, 102],
            "vol": [10, 12]}})

    monkeypatch.setattr(veri.requests, "get", sahte_get)
    rows = veri._mexc_futures_cek("BTCUSDT", "1h",
                                  1700000000000, 1700007200000)
    assert "BTC_USDT" in cagri["url"]                 # sembol dönüştü
    assert cagri["params"]["interval"] == "Min60"     # TF enum
    assert len(rows) == 2
    assert rows[0][0] == 1700000000 * 1000            # ms'e çevrildi
    assert rows[0][1:5] == [100, 102, 99, 101]        # O H L C


def test_indir_futures_birincil(monkeypatch, tmp_path):
    """indir() futures kaynağını önce dener; başarılıysa spot'a düşmez."""
    monkeypatch.setattr(veri, "DATA_DIR", tmp_path)
    cagrilanlar = []

    def fut(symbol, interval, s, e):
        cagrilanlar.append("futures")
        return [[1700000000000, 100, 102, 99, 101, 10, 1700000000000, 0]]

    def spot(symbol, interval, s, e):
        cagrilanlar.append("spot")
        return []

    monkeypatch.setattr(veri, "_KAYNAKLAR",
                        [("mexc-futures", fut), ("mexc-spot", spot)])
    df = veri.indir("BTCUSDT", "1h", gun=1, force=True)
    assert cagrilanlar == ["futures"]                 # spot'a düşmedi
    assert len(df) == 1 and df["close"].iloc[0] == 101.0


def test_indir_spot_yedege_duser(monkeypatch, tmp_path):
    """Futures hata verirse spot yedeğine düşülür."""
    monkeypatch.setattr(veri, "DATA_DIR", tmp_path)
    cagrilanlar = []

    def fut(symbol, interval, s, e):
        cagrilanlar.append("futures")
        raise RuntimeError("403 Access Denied")

    def spot(symbol, interval, s, e):
        cagrilanlar.append("spot")
        return [[1700000000000, 100, 102, 99, 101, 10, 1700000000000, 0]]

    monkeypatch.setattr(veri, "_KAYNAKLAR",
                        [("mexc-futures", fut), ("mexc-spot", spot)])
    df = veri.indir("BTCUSDT", "1h", gun=1, force=True)
    assert cagrilanlar == ["futures", "spot"]         # ikisi de denendi
    assert len(df) == 1


def test_get_rate_limit_retry(monkeypatch):
    """429 → Retry-After kadar bekleyip yeniden dener, sonunda 200 döner."""
    durumlar = [429, 429, 200]
    uyku = []

    class C:
        def __init__(self, kod):
            self.status_code = kod
            self.headers = {"Retry-After": "0"}

    def sahte_get(url, params=None, timeout=None, headers=None):
        return C(durumlar.pop(0))

    monkeypatch.setattr(veri.requests, "get", sahte_get)
    monkeypatch.setattr(veri.time, "sleep", lambda s: uyku.append(s))
    r = veri._get("u", {}, deneme=4)
    assert r.status_code == 200 and len(uyku) == 2     # 2 kez bekledi


def test_max_bar_pencereyi_kisitlar(monkeypatch, tmp_path):
    """max_bar verilince start_ms en çok max_bar mum kadar geriye gider."""
    monkeypatch.setattr(veri, "DATA_DIR", tmp_path)
    yakalanan = {}

    def fut(symbol, interval, s, e):
        yakalanan["span_sec"] = (e - s) // 1000
        return [[s, 1, 2, 0.5, 1.5, 1, s, 0]]

    monkeypatch.setattr(veri, "_KAYNAKLAR", [("mexc-futures", fut)])
    # 1h, max_bar=100 → pencere ≈ 100*3600 sn
    veri.indir("BTCUSDT", "1h", gun=120, force=True, max_bar=100)
    assert yakalanan["span_sec"] <= 100 * 3600 + 5


def test_indir_hepsi_basarisiz_hata(monkeypatch, tmp_path):
    monkeypatch.setattr(veri, "DATA_DIR", tmp_path)
    monkeypatch.setattr(veri, "_KAYNAKLAR", [
        ("mexc-futures", lambda *a: (_ for _ in ()).throw(RuntimeError("x"))),
        ("mexc-spot", lambda *a: []),
    ])
    try:
        veri.indir("ZZZUSDT", "1h", gun=1, force=True)
        assert False
    except RuntimeError as e:
        assert "veri çekilemedi" in str(e)
