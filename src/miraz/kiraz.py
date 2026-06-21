"""Kiraz — execution/karar motoru (Miraz bulur, Kiraz açar).

@tradermiraz: "Miraz setup'ı bulur, Kiraz risk yönetir ve emir açar." Kiraz
Status: WATCHLIST (izle) ↔ EXECUTION. Bu modül bir Trade adayını alır,
**R bazlı pozisyon boyutu** hesaplar ve bir **bracket emir** planı (giriş LIMIT
+ SL STOP_MARKET + TP TAKE_PROFIT_MARKET) kurar; isteğe bağlı olarak Binance
**Testnet**'e gönderir.

GÜVENLİK: gönderim varsayılan **kuru çalıştırma** (dry-run). Gerçek testnet
emri yalnızca `kuru=False` ile ve testnet istemcisi verilince atılır. Mainnet
desteklenmez (borsa.py testnet sabitli).

Kullanım:
    from miraz.kiraz import emir_plani
    plan = emir_plani(aday, r_dolar=25)   # saf hesap, ağ yok
    # Testnet'e göndermek için:
    from miraz.borsa import BinanceTestnet
    KirazMotor(BinanceTestnet.ortamdan()).uygula(plan, kuru=False)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


def pozisyon_miktari(r_dolar: float, giris: float, stop: float,
                     ondalik: int = 3) -> float:
    """R (dolar risk) ve giriş–stop mesafesinden pozisyon miktarı (adet).

    miktar = risk / |giriş − stop|  → stop olursa tam r_dolar kaybedilir.
    """
    mesafe = abs(giris - stop)
    if mesafe <= 0:
        return 0.0
    ham = r_dolar / mesafe
    # aşağı yuvarla (riski aşma)
    kat = 10 ** ondalik
    return math.floor(ham * kat) / kat


@dataclass
class KirazPlan:
    symbol: str
    taraf: str            # "Long" / "Short"
    miktar: float
    giris: float
    stop: float
    hedef: float
    rr: float = 1.0
    # Binance taraf eşlemesi
    @property
    def giris_side(self) -> str:
        return "BUY" if self.taraf == "Long" else "SELL"

    @property
    def kapanis_side(self) -> str:
        return "SELL" if self.taraf == "Long" else "BUY"

    @property
    def gecerli(self) -> bool:
        return self.miktar > 0 and self.giris > 0 and self.stop > 0

    def emirler(self) -> list[dict]:
        """Bracket emir listesi: giriş LIMIT + SL + TP (testnet payload)."""
        out = [{
            "rol": "ENTRY", "symbol": self.symbol, "side": self.giris_side,
            "tip": "LIMIT", "miktar": self.miktar, "fiyat": self.giris,
        }]
        if self.stop > 0:
            out.append({
                "rol": "SL", "symbol": self.symbol, "side": self.kapanis_side,
                "tip": "STOP_MARKET", "stop_fiyat": self.stop,
                "close_position": True,
            })
        if self.hedef > 0:
            out.append({
                "rol": "TP", "symbol": self.symbol, "side": self.kapanis_side,
                "tip": "TAKE_PROFIT_MARKET", "stop_fiyat": self.hedef,
                "close_position": True,
            })
        return out


def emir_plani(aday, r_dolar: float = 25.0, ondalik: int = 3) -> KirazPlan:
    """Bir radar adayından (symbol/taraf/giris/stop/hedef) KirazPlan üretir.

    `aday` RadarSatiri ya da sözlük olabilir (web snapshot uyumlu).
    """
    def al(ad, vars=None):
        if isinstance(aday, dict):
            return aday.get(ad, vars)
        return getattr(aday, ad, vars)

    symbol = al("symbol") or al("sembol")
    taraf = al("taraf", "Long")
    giris = float(al("giris") or 0.0)
    stop = float(al("stop") or 0.0)
    hedef = float(al("hedef") or 0.0)
    rr = float(al("rr") or 1.0)
    miktar = pozisyon_miktari(r_dolar, giris, stop, ondalik) if (giris and stop) \
        else 0.0
    return KirazPlan(symbol=symbol, taraf=taraf, miktar=miktar, giris=giris,
                     stop=stop, hedef=hedef, rr=rr)


@dataclass
class KirazMotor:
    """KirazPlan'ı testnet'e uygular (varsayılan kuru çalıştırma)."""
    borsa: object = None        # BinanceTestnet (yoksa sadece dry-run)
    gonderilenler: list = field(default_factory=list)

    def uygula(self, plan: KirazPlan, kuru: bool = True) -> dict:
        """Planı işler. kuru=True → sadece emir listesini döndürür, göndermez."""
        if not plan.gecerli:
            return {"durum": "atlandı", "neden": "geçersiz plan",
                    "emirler": []}
        emirler = plan.emirler()
        if kuru or self.borsa is None:
            return {"durum": "kuru", "symbol": plan.symbol,
                    "miktar": plan.miktar, "emirler": emirler}
        sonuc = []
        for e in emirler:
            cevap = self.borsa.emir_gonder(
                symbol=e["symbol"], side=e["side"], tip=e["tip"],
                miktar=e.get("miktar", plan.miktar),
                fiyat=e.get("fiyat"), stop_fiyat=e.get("stop_fiyat"),
                close_position=e.get("close_position"))
            sonuc.append({"rol": e["rol"], "orderId": cevap.get("orderId"),
                          "status": cevap.get("status")})
            self.gonderilenler.append(cevap)
        return {"durum": "gönderildi", "symbol": plan.symbol,
                "miktar": plan.miktar, "emirler": sonuc}
