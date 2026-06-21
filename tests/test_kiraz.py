"""Kiraz execution motoru + Binance Testnet istemci testleri (ağ taklit)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz.kiraz import pozisyon_miktari, emir_plani, KirazPlan, KirazMotor
from miraz import borsa as bz


# --- pozisyon boyutlandırma ---

def test_pozisyon_miktari():
    # R=25$, giriş 100, stop 95 → mesafe 5 → 25/5 = 5 adet
    assert pozisyon_miktari(25, 100, 95) == 5.0
    # aşağı yuvarlama (riski aşma): 25/3 = 8.333 → 8.333
    assert pozisyon_miktari(25, 100, 97, ondalik=3) == 8.333
    # geçersiz mesafe
    assert pozisyon_miktari(25, 100, 100) == 0.0


def test_emir_plani_long():
    aday = {"symbol": "BTCUSDT", "taraf": "Long", "giris": 100.0,
            "stop": 95.0, "hedef": 110.0, "rr": 2.0}
    p = emir_plani(aday, r_dolar=25)
    assert p.gecerli and p.miktar == 5.0
    assert p.giris_side == "BUY" and p.kapanis_side == "SELL"
    emirler = p.emirler()
    assert emirler[0]["rol"] == "ENTRY" and emirler[0]["tip"] == "LIMIT"
    assert emirler[1]["rol"] == "SL" and emirler[1]["side"] == "SELL"
    assert emirler[2]["rol"] == "TP" and emirler[2]["stop_fiyat"] == 110.0


def test_emir_plani_short():
    aday = {"symbol": "ETHUSDT", "taraf": "Short", "giris": 100.0,
            "stop": 105.0, "hedef": 90.0}
    p = emir_plani(aday, r_dolar=25)
    assert p.giris_side == "SELL" and p.kapanis_side == "BUY"
    assert p.miktar == 5.0


def test_kiraz_motor_kuru():
    """kuru=True → emir gönderilmez, sadece plan döner."""
    p = KirazPlan("BTCUSDT", "Long", 5.0, 100, 95, 110)
    sonuc = KirazMotor(borsa=None).uygula(p, kuru=True)
    assert sonuc["durum"] == "kuru" and len(sonuc["emirler"]) == 3


def test_kiraz_motor_gonderim_taklit():
    """kuru=False → borsa.emir_gonder her emir için çağrılır."""
    cagrilar = []

    class SahteBorsa:
        def emir_gonder(self, **kw):
            cagrilar.append(kw)
            return {"orderId": len(cagrilar), "status": "NEW"}

    p = KirazPlan("BTCUSDT", "Long", 5.0, 100, 95, 110)
    sonuc = KirazMotor(SahteBorsa()).uygula(p, kuru=False)
    assert sonuc["durum"] == "gönderildi"
    assert len(cagrilar) == 3                     # ENTRY + SL + TP
    assert cagrilar[0]["side"] == "BUY"


def test_kiraz_motor_gecersiz_plan():
    p = KirazPlan("BTCUSDT", "Long", 0.0, 0, 0, 0)
    assert KirazMotor().uygula(p)["durum"] == "atlandı"


# --- Binance Testnet istemci (ağ taklit) ---

def test_imza_belirli():
    b = bz.BinanceTestnet(api_key="k", api_secret="secret")
    # HMAC-SHA256 deterministik olmalı
    assert b._imza("a=1&b=2") == b._imza("a=1&b=2")
    assert len(b._imza("x")) == 64


def test_ortamdan_anahtar_yok(monkeypatch):
    monkeypatch.delenv("BINANCE_TESTNET_KEY", raising=False)
    monkeypatch.delenv("BINANCE_TESTNET_SECRET", raising=False)
    assert bz.BinanceTestnet.kimlik_var() is False
    try:
        bz.BinanceTestnet.ortamdan()
        assert False
    except bz.BorsaHata:
        pass


def test_bakiye_taklit(monkeypatch):
    b = bz.BinanceTestnet(api_key="k", api_secret="s")
    monkeypatch.setattr(b, "hesap", lambda: {
        "totalWalletBalance": "5000.0", "availableBalance": "4800.0",
        "totalUnrealizedProfit": "12.5",
        "assets": [{"asset": "USDT", "walletBalance": "5000.0"}],
        "positions": [
            {"symbol": "BTCUSDT", "positionAmt": "0.01", "entryPrice": "95000",
             "unrealizedProfit": "12.5"},
            {"symbol": "ETHUSDT", "positionAmt": "0", "entryPrice": "0",
             "unrealizedProfit": "0"}],
    })
    assert b.bakiye() == 5000.0
    oz = b.ozet()
    assert oz["wallet"] == 5000.0 and oz["unrealized"] == 12.5
    poz = b.pozisyonlar()
    assert len(poz) == 1 and poz[0]["symbol"] == "BTCUSDT"   # sıfır olan atlandı
    assert poz[0]["yon"] == "Long"


def test_emir_gonder_imzali_istek(monkeypatch):
    """emir_gonder doğru endpoint + imzalı parametre üretir (POST taklit)."""
    yakalanan = {}

    class SahteCevap:
        status_code = 200
        text = "{}"
        def json(self):
            return {"orderId": 7, "status": "NEW"}

    def sahte_post(url, data=None, headers=None, timeout=None):
        yakalanan["url"] = url
        yakalanan["data"] = data
        yakalanan["key"] = headers.get("X-MBX-APIKEY")
        return SahteCevap()

    monkeypatch.setattr(bz.requests, "post", sahte_post)
    b = bz.BinanceTestnet(api_key="anahtar", api_secret="gizli")
    cevap = b.emir_gonder("BTCUSDT", "BUY", "LIMIT", 0.01, fiyat=95000)
    assert cevap["orderId"] == 7
    assert "/fapi/v1/order" in yakalanan["url"]
    assert "signature=" in yakalanan["data"]       # imzalı
    assert yakalanan["key"] == "anahtar"           # header'da key


def test_http_hata_yukseltir(monkeypatch):
    class SahteCevap:
        status_code = 400
        text = '{"code":-1100,"msg":"bad"}'
        def json(self):
            return {}

    monkeypatch.setattr(bz.requests, "get",
                        lambda *a, **k: SahteCevap())
    b = bz.BinanceTestnet(api_key="k", api_secret="s")
    try:
        b.hesap()
        assert False
    except bz.BorsaHata as e:
        assert "400" in str(e)
