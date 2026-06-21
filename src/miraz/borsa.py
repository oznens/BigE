"""Binance USDT-M Futures **Testnet** istemcisi — Kiraz execution motoru.

@tradermiraz terminalMiraz'ı Binance Futures **Testnet** (TestUSDT, sahte para)
üzerinden çalıştırıyor: "Testnet Active · Binance Connected". Bu modül aynı
bağlantıyı kurar — testnet hesabını okur ve (opt-in) testnet emri gönderir.

GÜVENLİK:
  • Yalnızca **testnet** (https://testnet.binancefuture.com) — gerçek para yok.
  • API anahtarı/secret yalnızca ortam değişkeninden ya da çağıranın verdiği
    parametreden okunur. Asla koda gömülmez, asla loglanmaz/yazdırılmaz.
  • İmza HMAC-SHA256; anahtar isteğin gövdesinde değil header'da gider.
  • Emir gönderimi çağıran tarafından açıkça tetiklenir (otomatik değil).

Kimlik bilgisi:
    export BINANCE_TESTNET_KEY=...     (Windows: setx BINANCE_TESTNET_KEY ...)
    export BINANCE_TESTNET_SECRET=...
Testnet anahtarı: https://testnet.binancefuture.com → API Key

Kullanım:
    from miraz.borsa import BinanceTestnet
    b = BinanceTestnet.ortamdan()
    print(b.bakiye())            # USDT testnet bakiyesi
    print(b.pozisyonlar())       # açık pozisyonlar
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from dataclasses import dataclass
from urllib.parse import urlencode

import requests

TESTNET_BASE = "https://testnet.binancefuture.com"
_ZAMAN_ASIMI = 10


class BorsaHata(Exception):
    """Borsa isteği başarısız (ağ / imza / API kodu)."""


@dataclass
class BinanceTestnet:
    """Binance USDT-M Futures Testnet REST istemcisi (imzalı)."""
    api_key: str
    api_secret: str
    base: str = TESTNET_BASE

    # --- kimlik ---

    @classmethod
    def ortamdan(cls, base: str = TESTNET_BASE) -> "BinanceTestnet":
        """Anahtarları ortam değişkenlerinden yükler (asla yazdırmaz)."""
        k = os.environ.get("BINANCE_TESTNET_KEY", "").strip()
        s = os.environ.get("BINANCE_TESTNET_SECRET", "").strip()
        if not k or not s:
            raise BorsaHata(
                "BINANCE_TESTNET_KEY / BINANCE_TESTNET_SECRET ortam değişkenleri "
                "tanımlı değil. testnet.binancefuture.com'dan anahtar al.")
        return cls(api_key=k, api_secret=s, base=base)

    @staticmethod
    def kimlik_var() -> bool:
        return bool(os.environ.get("BINANCE_TESTNET_KEY")
                    and os.environ.get("BINANCE_TESTNET_SECRET"))

    # --- imzalı istek ---

    def _imza(self, sorgu: str) -> str:
        return hmac.new(self.api_secret.encode(), sorgu.encode(),
                        hashlib.sha256).hexdigest()

    def _istek(self, metot: str, yol: str, imzali: bool = False, **parametre):
        p = {k: v for k, v in parametre.items() if v is not None}
        if imzali:
            p["timestamp"] = int(time.time() * 1000)
            p["recvWindow"] = 5000
            sorgu = urlencode(p)
            p_str = sorgu + "&signature=" + self._imza(sorgu)
        else:
            p_str = urlencode(p)
        url = f"{self.base}{yol}"
        basliklar = {"X-MBX-APIKEY": self.api_key}
        try:
            if metot == "GET":
                r = requests.get(url + ("?" + p_str if p_str else ""),
                                 headers=basliklar, timeout=_ZAMAN_ASIMI)
            elif metot == "DELETE":
                r = requests.delete(url + "?" + p_str, headers=basliklar,
                                    timeout=_ZAMAN_ASIMI)
            else:
                r = requests.post(url, data=p_str, headers=basliklar,
                                  timeout=_ZAMAN_ASIMI)
        except requests.RequestException as e:
            raise BorsaHata(f"ağ hatası: {e}") from e
        if r.status_code >= 400:
            # API mesajını veri olarak göster (talimat değil)
            raise BorsaHata(f"HTTP {r.status_code}: {r.text[:200]}")
        return r.json()

    # --- okuma ---

    def baglanti_testi(self) -> bool:
        self._istek("GET", "/fapi/v1/ping")
        return True

    def hesap(self) -> dict:
        return self._istek("GET", "/fapi/v2/account", imzali=True)

    def bakiye(self, varlik: str = "USDT") -> float:
        for a in self.hesap().get("assets", []):
            if a.get("asset") == varlik:
                return float(a.get("walletBalance", 0.0))
        return 0.0

    def ozet(self) -> dict:
        """Cüzdan / kullanılabilir / açık PNL — dashboard metrikleri için."""
        h = self.hesap()
        return {
            "wallet": float(h.get("totalWalletBalance", 0.0)),
            "available": float(h.get("availableBalance", 0.0)),
            "unrealized": float(h.get("totalUnrealizedProfit", 0.0)),
        }

    def pozisyonlar(self) -> list[dict]:
        """Sıfırdan farklı miktarlı açık pozisyonlar."""
        out = []
        for p in self.hesap().get("positions", []):
            miktar = float(p.get("positionAmt", 0.0))
            if miktar != 0.0:
                out.append({
                    "symbol": p.get("symbol"), "miktar": miktar,
                    "giris": float(p.get("entryPrice", 0.0)),
                    "pnl": float(p.get("unrealizedProfit", 0.0)),
                    "yon": "Long" if miktar > 0 else "Short",
                })
        return out

    def acik_emirler(self, symbol: str | None = None) -> list[dict]:
        return self._istek("GET", "/fapi/v1/openOrders", imzali=True,
                           symbol=symbol)

    # --- yazma (emir) — çağıran açıkça tetikler ---

    def emir_gonder(self, symbol: str, side: str, tip: str, miktar: float,
                    fiyat: float | None = None, stop_fiyat: float | None = None,
                    reduce_only: bool | None = None,
                    zaman_gecerlilik: str = "GTC",
                    close_position: bool | None = None) -> dict:
        """Tek bir futures emri gönderir (testnet). side: BUY/SELL.

        tip: LIMIT (fiyat) · MARKET · STOP_MARKET / TAKE_PROFIT_MARKET (stop_fiyat).
        """
        return self._istek(
            "POST", "/fapi/v1/order", imzali=True,
            symbol=symbol, side=side, type=tip, quantity=miktar,
            price=fiyat, stopPrice=stop_fiyat,
            timeInForce=(zaman_gecerlilik if tip == "LIMIT" else None),
            reduceOnly=(str(reduce_only).lower() if reduce_only is not None
                        else None),
            closePosition=(str(close_position).lower()
                           if close_position is not None else None))

    def emir_iptal(self, symbol: str, order_id: int) -> dict:
        return self._istek("DELETE", "/fapi/v1/order", imzali=True,
                           symbol=symbol, orderId=order_id)

    def tum_emirleri_iptal(self, symbol: str) -> dict:
        return self._istek("DELETE", "/fapi/v1/allOpenOrders", imzali=True,
                           symbol=symbol)
