"""OHLCV veri çekme — MEXC Futures (birincil) + Spot (yedek), parquet cache.

Canlı scanner varsayılan olarak yalnızca KAPANMIŞ mumları döndürür. Parquet
cache, son kapanmış muma göre tazelik kontrolünden geçer; bayatsa API'den
yenilenir. Böylece uzun yaşayan scanner süreçleri eski cache ile çalışmaz ve
açık mum değiştikçe sinyalin repaint etmesi önlenir.
"""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import requests

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

_BASLIK = {"User-Agent": "Mozilla/5.0"}

# --- MEXC Futures (contract) — terminalMiraz USDT-M Futures pariteleri ---
# Sembol BTCUSDT → BTC_USDT; zaman dilimi enum; start/end saniye; dizi yanıt.
MEXC_FUT_BASE = "https://contract.mexc.com/api/v1/contract/kline"
_MEXC_FUT_IV = {
    "1m": "Min1", "5m": "Min5", "15m": "Min15", "30m": "Min30",
    "1h": "Min60", "4h": "Hour4", "8h": "Hour8", "1d": "Day1", "1w": "Week1",
}
_IV_SANIYE = {
    "1m": 60, "5m": 300, "15m": 900, "30m": 1800, "1h": 3600,
    "2h": 7200, "4h": 14400, "8h": 28800, "1d": 86400, "1w": 604800,
}

# --- MEXC Spot (yedek) — saatlik "60m" ister ---
MEXC_SPOT_BASE = "https://api.mexc.com/api/v3/klines"
_MEXC_SPOT_IV = {"1h": "60m"}

# Klines ortak satır şeması (ilk 8 kolon).
_KOLONLAR = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume",
]

# Borsada NATIF olmayan türev zaman dilimleri: alt TF'den resample edilir.
# MEXC 2h sunmaz → 60m (1h) çekip 2 saate toplarız (terminalMiraz M15/M30/H1/H2).
_TUREV = {
    "2h": ("1h", "2h"),
}


def _get(url: str, params: dict, deneme: int = 4):
    """Rate-limit/sunucu hatalarına dayanıklı GET (429/418/5xx → backoff)."""
    r = None
    for i in range(deneme):
        r = requests.get(url, params=params, timeout=15, headers=_BASLIK)
        if r.status_code in (429, 418, 500, 502, 503, 504):
            bekle = float(r.headers.get("Retry-After", 0) or 0) or 1.5 * (i + 1)
            time.sleep(min(bekle, 12))
            continue
        return r
    return r


def _resample(df: pd.DataFrame, kural: str) -> pd.DataFrame:
    """OHLCV df'i daha üst bir zaman dilimine toplar (örn. 1h → 2h)."""
    o = df.resample(kural, label="left", closed="left").agg({
        "open": "first", "high": "max", "low": "min",
        "close": "last", "volume": "sum"}).dropna()
    return o


def _fut_sembol(symbol: str) -> str:
    """BTCUSDT → BTC_USDT (MEXC futures sembol biçimi)."""
    for kote in ("USDT", "USDC"):
        if symbol.endswith(kote) and "_" not in symbol:
            return symbol[: -len(kote)] + "_" + kote
    return symbol


def _mexc_futures_cek(symbol: str, interval: str, start_ms: int,
                      end_ms: int) -> list:
    """MEXC **futures** kline (dizi yanıt) → ortak 8-kolon satır listesi."""
    iv = _MEXC_FUT_IV.get(interval)
    if iv is None:
        raise RuntimeError(f"futures TF desteklenmiyor: {interval}")
    sec = _IV_SANIYE[interval]
    sym = _fut_sembol(symbol)
    pencere = 2000 * sec                    # istek başına en çok ~2000 mum
    rows: list = []
    imlec = start_ms // 1000
    son_s = end_ms // 1000
    while imlec < son_s:
        bitis = min(imlec + pencere, son_s)
        r = _get(f"{MEXC_FUT_BASE}/{sym}", {
            "interval": iv, "start": imlec, "end": bitis})
        r.raise_for_status()
        j = r.json()
        d = j.get("data") or {}
        t = d.get("time") or []
        if not t:
            break
        o, h, low, c = d["open"], d["high"], d["low"], d["close"]
        v = d.get("vol") or d.get("amount") or [0] * len(t)
        for i in range(len(t)):
            ms = int(t[i]) * 1000
            rows.append([ms, o[i], h[i], low[i], c[i], v[i], ms, 0])
        ileri = int(t[-1]) + sec
        if ileri <= imlec:
            break
        imlec = ileri
        time.sleep(0.15)
    return rows


def _mexc_spot_cek(symbol: str, interval: str, start_ms: int,
                   end_ms: int) -> list:
    """MEXC **spot** klines (satır yanıt) — yedek kaynak."""
    iv = _MEXC_SPOT_IV.get(interval, interval)
    parcalar: list = []
    imlec = start_ms
    while imlec < end_ms:
        r = _get(MEXC_SPOT_BASE, {
            "symbol": symbol, "interval": iv,
            "startTime": imlec, "endTime": end_ms, "limit": 1000})
        r.raise_for_status()
        chunk = r.json()
        if not chunk:
            break
        parcalar.extend(satir[:8] for satir in chunk)
        son = chunk[-1][6] + 1
        if son <= imlec:
            break
        imlec = son
        time.sleep(0.2)
    return parcalar


# Kaynak sırası: futures (birincil, terminalMiraz) → spot (yedek).
_KAYNAKLAR = [
    ("mexc-futures", _mexc_futures_cek),
    ("mexc-spot", _mexc_spot_cek),
]


def _cache_oku(yol: Path):
    """Parquet cache'i okur; motor (pyarrow/fastparquet) yoksa None döner."""
    try:
        return pd.read_parquet(yol)
    except Exception:
        return None


def _cache_yaz(df: pd.DataFrame, yol: Path) -> None:
    """Parquet cache yazar; motor yoksa sessizce atlar (veri yine döner)."""
    try:
        df.to_parquet(yol)
    except Exception:
        pass


def _kapanmis_mumlar(df: pd.DataFrame, interval: str,
                     now_ms: int | None = None) -> pd.DataFrame:
    """Henüz kapanmamış son mumu çıkarır.

    DataFrame indeksi mumun AÇILIŞ zamanıdır. Bir bar ancak
    ``open_time + interval <= şimdi`` olduğunda tamamlanmış sayılır.
    """
    if df is None or df.empty:
        return df
    sec = _IV_SANIYE.get(interval)
    if not sec:
        return df
    now_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
    sinir = pd.to_datetime(now_ms - sec * 1000, unit="ms", utc=True)
    return df[df.index <= sinir]


def _cache_guncel(df: pd.DataFrame, interval: str,
                  now_ms: int | None = None) -> bool:
    """Cache'in son tamamlanmış barı kapsayıp kapsamadığını kontrol eder.

    Son kapalı barın açılışı bir sonraki bar kapanana kadar en fazla yaklaşık
    iki interval geride olabilir. Bu eşiğin aşılması yeni tamamlanmış barın
    cache'de olmadığı anlamına gelir ve yeniden indirme tetiklenir.
    """
    if df is None or df.empty:
        return False
    sec = _IV_SANIYE.get(interval)
    if not sec:
        return True
    now_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
    kapali = _kapanmis_mumlar(df, interval, now_ms=now_ms)
    if kapali is None or kapali.empty:
        return False
    son_open_ms = int(kapali.index[-1].timestamp() * 1000)
    return son_open_ms + 2 * sec * 1000 > now_ms


def indir(symbol: str = "BTCUSDT", interval: str = "4h",
          gun: int = 500, force: bool = False,
          borsa: str | None = None, max_bar: int | None = None,
          sadece_kapanmis: bool = True) -> pd.DataFrame:
    """OHLCV veriyi indirir, parquet cache kullanır.

    Kaynaklar sırayla denenir: **MEXC Futures → MEXC Spot**; biri başarısız olur
    veya sembolü sunmazsa diğerine geçilir. borsa verilirse ("mexc-futures" /
    "mexc-spot") yalnızca o kaynak kullanılır.

    Cache yalnız güncelse kullanılır; yeni kapanmış bar varsa API'den yenilenir.
    ``sadece_kapanmis=True`` varsayılandır ve canlı sinyallerin açık mum nedeniyle
    değişmesini/repaint etmesini önler. Gelişmekte olan mumu özellikle isteyen
    çağıranlar ``sadece_kapanmis=False`` verebilir.

    max_bar verilirse pencere en çok o kadar mumla sınırlanır (intraday TF'lerde
    120 günlük 15m gibi devasa indirmeleri önler — canlı tarama hızlanır).

    Döndürür: UTC indeksli, float kolonlu OHLCV DataFrame.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    now_ms = int(time.time() * 1000)

    # Borsada natif olmayan TF (örn. 2h) → alt TF'i çekip resample et.
    # Türev TF'in kendi cache'ini körlemesine kullanmak yerine alt TF cache
    # tazeliğine güvenip yeniden resample ederiz; böylece yarım 2h bar sızmaz.
    if interval in _TUREV:
        alt_iv, kural = _TUREV[interval]
        yol_t = DATA_DIR / f"{symbol}_{interval}.parquet"
        if yol_t.exists() and not force:
            onbellek = _cache_oku(yol_t)
            if onbellek is not None:
                aday = (_kapanmis_mumlar(onbellek, interval, now_ms)
                        if sadece_kapanmis else onbellek)
                if _cache_guncel(onbellek, interval, now_ms):
                    return aday
        alt_bar = None
        if max_bar:
            oran = _IV_SANIYE[interval] // _IV_SANIYE[alt_iv]
            alt_bar = max_bar * max(oran, 1)
        alt = indir(symbol, alt_iv, gun=gun, force=force, borsa=borsa,
                    max_bar=alt_bar, sadece_kapanmis=False)
        df_t = _resample(alt, kural)
        _cache_yaz(df_t, yol_t)
        return (_kapanmis_mumlar(df_t, interval, now_ms)
                if sadece_kapanmis else df_t)

    yol = DATA_DIR / f"{symbol}_{interval}.parquet"
    if yol.exists() and not force:
        onbellek = _cache_oku(yol)
        if onbellek is not None and _cache_guncel(onbellek, interval, now_ms):
            return (_kapanmis_mumlar(onbellek, interval, now_ms)
                    if sadece_kapanmis else onbellek)

    end_ms = now_ms
    start_ms = end_ms - gun * 24 * 3600 * 1000
    # mum sayısı sınırı: pencereyi kısaltarak intraday indirmeyi bound'la
    if max_bar:
        sec = _IV_SANIYE.get(interval)
        if sec:
            start_ms = max(start_ms, end_ms - max_bar * sec * 1000)

    kaynaklar = [k for k in _KAYNAKLAR if borsa is None or k[0] == borsa]
    parcalar: list = []
    hatalar: list = []
    for ad, cekici in kaynaklar:
        try:
            parcalar = cekici(symbol, interval, start_ms, end_ms)
        except Exception as e:               # geo-engel, 4xx, ağ vb.
            hatalar.append(f"{ad}: {e}")
            parcalar = []
        if parcalar:
            break

    if not parcalar:
        detay = " | ".join(hatalar) if hatalar else "veri yok"
        raise RuntimeError(f"{symbol}/{interval} veri çekilemedi ({detay}).")

    df = pd.DataFrame(parcalar, columns=_KOLONLAR)
    df = df.drop_duplicates("open_time")
    df.index = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df.index.name = "zaman"
    for k in ["open", "high", "low", "close", "volume"]:
        df[k] = df[k].astype(float)
    df = df[["open", "high", "low", "close", "volume"]].sort_index()

    # Ham cache açık son mumu da tutabilir; bu sayede isteyen canlı geliştirme
    # modunu kullanabilir. Varsayılan dönüş ise yalnız kapanmış mumlardır.
    _cache_yaz(df, yol)
    return (_kapanmis_mumlar(df, interval, now_ms)
            if sadece_kapanmis else df)


if __name__ == "__main__":
    df = indir(force=True)
    print(f"{len(df)} mum | {df.index[0].date()} → {df.index[-1].date()}")
    print(df.tail(3))
