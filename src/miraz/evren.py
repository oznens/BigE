"""Parite evreni — piyasa değerine (mcap) göre dinamik seçim (terminalMiraz).

@tradermiraz parite listesini piyasa değerine göre seçiyor ve düzenli aralıklarla
(haftada bir) "bu coin hâlâ listede mi?" diye kontrol ediyor: mcap'i düşüp listeden
çıkanları atıyor, yükselip girenleri ekliyor (tweet: "Yeterli performansı
gösteremeyen pariteler listeden çıkarılır").

Bu modül:
  • CoinGecko'dan ilk N coini mcap sırasına göre çeker.
  • Stablecoin / wrapped / staked türevlerini eler.
  • MEXC'te spot USDT paritesi olanları (işlem görenleri) tutar.
  • Önceki kayıtla karşılaştırıp EKLENEN / ÇIKAN paritelerini raporlar.
  • data/evren.json'a zaman damgasıyla kaydeder.

Kullanım:
    from miraz.evren import evren_guncelle, evren_yukle
    sonuc = evren_guncelle(n=90)         # haftalık taze liste + değişim raporu
    print(sonuc.rapor())
    semboller = evren_yukle()            # radar için güncel evren
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import requests

# Geçerli sembol: yalnızca ASCII büyük harf + rakam (Çince/junk sembolleri eler)
_GECERLI_SEMBOL = re.compile(r"^[A-Z0-9]{1,15}$")

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
EVREN_DOSYA = DATA_DIR / "evren.json"

_CG = "https://api.coingecko.com/api/v3/coins/markets"
_MEXC_INFO = "https://api.mexc.com/api/v3/exchangeInfo"
_MEXC_FUT_INFO = "https://contract.mexc.com/api/v1/contract/detail"
_BASLIK = {"User-Agent": "Mozilla/5.0"}

# Stablecoin / sarmalanmış (wrapped) / stake türevleri — mcap'te üst sıralarda
# ama "parite" olarak işe yaramaz; elenir.
_HARIC = {
    # stablecoinler
    "USDT", "USDC", "DAI", "FDUSD", "TUSD", "USDE", "USDS", "PYUSD", "BUSD",
    "USD1", "USDP", "GUSD", "FRAX", "LUSD", "USDD", "USDX", "USDB", "EURC",
    "BSC-USD", "USDF", "RLUSD", "USDG", "XAUT", "PAXG",
    # wrapped / staked / likit-stake türevleri (ana coinle birebir korele)
    "WBTC", "WETH", "STETH", "WSTETH", "WBETH", "WEETH", "RETH", "CBETH",
    "SOLVBTC", "LBTC", "CLBTC", "BTCB", "WBNB", "WSOL", "JITOSOL", "MSOL",
    "RSETH", "EZETH", "METH", "SUSDE", "SUSDS", "WHYPE", "BTC.B",
}


def _mcap_listesi(n: int) -> list[tuple]:
    """CoinGecko'dan ilk (n + tampon) coini (rank, sembol) olarak döndürür."""
    # Stable/wrapped eleneceği için fazladan çekip sonra kırpıyoruz.
    say = min(250, n * 2 + 30)
    r = requests.get(_CG, params={
        "vs_currency": "usd", "order": "market_cap_desc",
        "per_page": say, "page": 1, "price_change_percentage": ""},
        headers=_BASLIK, timeout=20)
    r.raise_for_status()
    out = []
    for c in r.json():
        sym = (c.get("symbol") or "").upper()
        rank = c.get("market_cap_rank")
        if sym and rank:
            out.append((rank, sym))
    return out


def _mexc_futures_usdt() -> set:
    """MEXC **futures** USDT-M kontratları (BTC_USDT → BTCUSDT biçiminde)."""
    r = requests.get(_MEXC_FUT_INFO, headers=_BASLIK, timeout=20)
    r.raise_for_status()
    out = set()
    for c in r.json().get("data", []):
        sym = c.get("symbol", "")           # "BTC_USDT"
        if sym.endswith("_USDT"):
            out.add(sym.replace("_", ""))   # "BTCUSDT"
    return out


def _mexc_spot_usdt() -> set:
    """MEXC'te spot işlem gören USDT paritelerinin kümesi (yedek)."""
    r = requests.get(_MEXC_INFO, headers=_BASLIK, timeout=20)
    r.raise_for_status()
    return {s["symbol"] for s in r.json().get("symbols", [])
            if s.get("symbol", "").endswith("USDT")}


def _mexc_usdt() -> set:
    """İşlem gören USDT pariteleri — önce futures (terminalMiraz), sonra spot."""
    try:
        fut = _mexc_futures_usdt()
        if fut:
            return fut
    except Exception:
        pass
    return _mexc_spot_usdt()


def mcap_evreni(n: int = 90, mexc_set: set | None = None) -> list[tuple]:
    """İlk n geçerli pariteyi (sembol, rank) olarak mcap sırasında döndürür.

    Stable/wrapped elenir; yalnızca MEXC'te USDT paritesi olanlar tutulur.
    """
    mexc = mexc_set if mexc_set is not None else _mexc_usdt()
    secilen = []
    for rank, sym in _mcap_listesi(n):
        if sym in _HARIC or not _GECERLI_SEMBOL.match(sym):
            continue
        parite = f"{sym}USDT"
        if parite in mexc:
            secilen.append((parite, rank))
        if len(secilen) >= n:
            break
    return secilen


@dataclass
class EvrenSonuc:
    semboller: list = field(default_factory=list)   # güncel parite listesi
    eklenen: list = field(default_factory=list)     # bu güncellemede giren
    cikan: list = field(default_factory=list)       # bu güncellemede düşen
    onceki_tarih: str | None = None
    n: int = 0

    def rapor(self) -> str:
        sat = [f"🌐 MCAP EVRENİ — {len(self.semboller)} parite "
               f"(ilk {self.n}, mcap sırası)"]
        if self.onceki_tarih:
            sat.append(f"   Önceki liste: {self.onceki_tarih[:10]}")
        if self.eklenen:
            sat.append(f"   ➕ Eklenen ({len(self.eklenen)}): "
                       f"{', '.join(self.eklenen)}")
        if self.cikan:
            sat.append(f"   ➖ Çıkan ({len(self.cikan)}): "
                       f"{', '.join(self.cikan)}")
        if not self.eklenen and not self.cikan and self.onceki_tarih:
            sat.append("   ✓ Değişiklik yok — liste aynı.")
        return "\n".join(sat)


def evren_yukle(dosya: str | Path = EVREN_DOSYA) -> list:
    """Kayıtlı mcap evrenini (parite listesi) döndürür; yoksa boş liste."""
    p = Path(dosya)
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8")).get("semboller", [])


def evren_guncelle(n: int = 90, dosya: str | Path = EVREN_DOSYA,
                   mexc_set: set | None = None) -> EvrenSonuc:
    """Taze mcap listesini çeker, öncekiyle karşılaştırır, kaydeder.

    Haftalık çalıştır: eklenen/çıkan pariteleri raporlar (terminalMiraz'ın
    "hâlâ listede mi?" kontrolü).
    """
    p = Path(dosya)
    eski = {}
    onceki_tarih = None
    if p.exists():
        d = json.loads(p.read_text(encoding="utf-8"))
        eski = {s: None for s in d.get("semboller", [])}
        onceki_tarih = d.get("guncelleme")

    secilen = mcap_evreni(n, mexc_set=mexc_set)
    yeni = [s for s, _ in secilen]
    rank = {s: r for s, r in secilen}

    eklenen = [s for s in yeni if s not in eski]
    cikan = [s for s in eski if s not in set(yeni)]

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({
        "guncelleme": datetime.now(timezone.utc).isoformat(),
        "n": n, "semboller": yeni, "mcap_rank": rank,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    return EvrenSonuc(semboller=yeni, eklenen=eklenen, cikan=cikan,
                      onceki_tarih=onceki_tarih, n=n)
