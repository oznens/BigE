#!/usr/bin/env python3
"""Zamansal Trade Sağlama — OHLCV ile kayıtlı TP/STOP sonuçlarını doğrular.

Her kapalı işlem (TP/STOP) için:
  1. Giriş zamanından itibaren OHLCV çeker.
  2. Bar bar yürür → giriş dolup dolmadığını, ardından hedef/stop'tan hangisinin
     önce vurulduğunu hesaplar.
  3. Kayıtlı durum ile karşılaştırır → uyuşmazlıkları raporlar.

Kullanım:
    python backtest/sagla.py                    # Pages'ten defter.json yükle
    python backtest/sagla.py --dosya defter.json
    python backtest/sagla.py --portfoy portfoy.json
    python backtest/sagla.py --json             # makine-okuyabilir JSON çıktısı
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "src"))

import pandas as pd
from miraz import veri as _veri

PAGES_URL = "https://oznens.github.io/BigE"

_IV_SANIYE = {
    "1m": 60, "5m": 300, "15m": 900, "30m": 1800, "1h": 3600,
    "2h": 7200, "4h": 14400, "8h": 28800, "1d": 86400, "1w": 604800,
}


# ---------------------------------------------------------------------------
# Sonuç türleri
# ---------------------------------------------------------------------------

@dataclass
class SaglaSonuc:
    id: int
    sembol: str
    interval: str
    taraf: str
    acilis_zaman: str
    giris: float
    stop: float
    hedef: float
    rr: float
    kayitli_durum: str          # defterde ne yazıyor
    gercek_durum: str           # OHLCV'ye göre ne olmalı (TP/STOP/Expired/GirisYok)
    eslesme: bool
    giris_bari: str             # giriş dolduğunda barın zamanı
    cikis_bari: str             # TP/STOP çarptığında barın zamanı
    bekleme_bar: int            # giriş dolana kadar geçen bar sayısı
    surec_bar: int              # giriş → çıkış bar sayısı
    not_: str = ""              # ek açıklama


# ---------------------------------------------------------------------------
# Yardımcı: OHLCV yükle
# ---------------------------------------------------------------------------

def _ohlcv(sembol: str, interval: str, baslangic_ms: int, bitis_ms: int,
           deneme: int = 3) -> pd.DataFrame:
    """Giriş..çıkış aralığı + %50 tampon için OHLCV çeker (hatalara dayanıklı)."""
    sure_ms = max(bitis_ms - baslangic_ms, 7 * 24 * 3600 * 1000)  # en az 7 gün
    gun = max(int(sure_ms / (24 * 3600 * 1000)) + 14, 30)         # +14 gün tampon
    for i in range(deneme):
        try:
            df = _veri.indir(sembol, interval, gun=gun, force=True)
            return df
        except Exception as e:
            if i == deneme - 1:
                raise
            time.sleep(2 ** i)
    return pd.DataFrame()


def _ts(iso: str) -> pd.Timestamp:
    return pd.Timestamp(iso).tz_convert("UTC") if iso.endswith("Z") \
        or "+" in iso[10:] or iso[-6] in ("+", "-") \
        else pd.Timestamp(iso).tz_localize("UTC")


# ---------------------------------------------------------------------------
# Çekirdek: tek işlemi doğrula
# ---------------------------------------------------------------------------

def sagla_kayit(k: dict, max_bekleme: int = 24) -> SaglaSonuc:
    """Bir Kayıt/Pozisyon sözlüğünü OHLCV ile doğrular."""
    sembol = k["sembol"]
    interval = k["interval"]
    taraf = k.get("taraf") or k.get("yon") or "Long"
    short = taraf == "Short"
    giris = float(k["giris"])
    stop = float(k["stop"])
    hedef = float(k["hedef"])
    acilis_zaman = k.get("acilis_zaman") or k.get("acilis") or ""
    kayitli = k.get("durum", "?")

    bos = SaglaSonuc(
        id=k.get("id", 0), sembol=sembol, interval=interval, taraf=taraf,
        acilis_zaman=acilis_zaman, giris=giris, stop=stop, hedef=hedef,
        rr=float(k.get("rr", 0)), kayitli_durum=kayitli,
        gercek_durum="?", eslesme=False, giris_bari="", cikis_bari="",
        bekleme_bar=0, surec_bar=0)

    if not acilis_zaman:
        bos.gercek_durum = "VeriYok"
        bos.not_ = "acilis_zaman boş"
        return bos

    try:
        baslangic = _ts(acilis_zaman)
    except Exception as e:
        bos.gercek_durum = "VeriYok"
        bos.not_ = f"zaman parse hatası: {e}"
        return bos

    # OHLCV çek (artı 30 gün güvenlik tamponu)
    baslangic_ms = int(baslangic.timestamp() * 1000)
    bitis_ms = int(time.time() * 1000)
    try:
        df = _ohlcv(sembol, interval, baslangic_ms, bitis_ms)
    except Exception as e:
        bos.gercek_durum = "VeriYok"
        bos.not_ = f"OHLCV hatası: {e}"
        return bos

    if df.empty:
        bos.gercek_durum = "VeriYok"
        bos.not_ = "OHLCV boş döndü"
        return bos

    # Giriş zamanından sonraki barları al
    alt = df[df.index >= baslangic]
    if alt.empty:
        bos.gercek_durum = "VeriYok"
        bos.not_ = "giriş zamanından sonra bar yok"
        return bos

    low = alt["low"].to_numpy(dtype=float)
    high = alt["high"].to_numpy(dtype=float)
    idx = alt.index

    acik = False
    giris_bari = ""
    bekleme_bar = 0

    for j in range(len(alt)):
        if not acik:
            # Long: fiyat girişe iner (low ≤ giriş) → limit alış dolar.
            # Short: fiyat girişe çıkar (high ≥ giriş) → limit satış dolar.
            doldu = (high[j] >= giris) if short else (low[j] <= giris)
            if doldu:
                acik = True
                giris_bari = idx[j].isoformat()
                bekleme_bar = j
            elif j >= max_bekleme:
                bos.gercek_durum = "GirisYok"
                bos.eslesme = kayitli in ("Expired", "GirisYok")
                bos.bekleme_bar = j
                bos.not_ = f"{max_bekleme} bar sonrası giriş gelmedi"
                return bos
            continue

        # Stop fitille değil, invalidasyon seviyesi ötesi kapanışla.
        kapanis = float(df["close"].iloc[j])
        stop_vurdu = (kapanis > stop) if short else (kapanis < stop)
        tp_vurdu = (low[j] <= hedef) if short else (high[j] >= hedef)

        if stop_vurdu and tp_vurdu:
            # Aynı bar hem stop hem TP: muhafazakâr → STOP
            gercek = "STOP"
            cikis_bari = idx[j].isoformat()
            surec_bar = j - bekleme_bar
            bos.gercek_durum = gercek
            bos.eslesme = kayitli == gercek
            bos.giris_bari = giris_bari
            bos.cikis_bari = cikis_bari
            bos.bekleme_bar = bekleme_bar
            bos.surec_bar = surec_bar
            bos.not_ = "aynı bar kapanış invalidasyonu + TP → muhafazakâr STOP"
            return bos
        if stop_vurdu:
            gercek = "STOP"
            bos.gercek_durum = gercek
            bos.eslesme = kayitli == gercek
            bos.giris_bari = giris_bari
            bos.cikis_bari = idx[j].isoformat()
            bos.bekleme_bar = bekleme_bar
            bos.surec_bar = j - bekleme_bar
            return bos
        if tp_vurdu:
            gercek = "TP"
            bos.gercek_durum = gercek
            bos.eslesme = kayitli == gercek
            bos.giris_bari = giris_bari
            bos.cikis_bari = idx[j].isoformat()
            bos.bekleme_bar = bekleme_bar
            bos.surec_bar = j - bekleme_bar
            return bos

    # Barlar tükendi, hâlâ açık → henüz bitmemiş
    bos.gercek_durum = "Açık"
    bos.eslesme = kayitli in ("Aday", "Açık", "Bekliyor")
    bos.giris_bari = giris_bari if acik else ""
    bos.bekleme_bar = bekleme_bar
    bos.not_ = "OHLCV sonu geldi, işlem hâlâ açık"
    return bos


# ---------------------------------------------------------------------------
# Defter / Portföy yükle
# ---------------------------------------------------------------------------

def _pages_json(yol_adi: str) -> dict | list | None:
    try:
        url = f"{PAGES_URL.rstrip('/')}/{yol_adi}"
        with urllib.request.urlopen(url, timeout=20) as r:
            return json.loads(r.read())
    except Exception:
        return None


def _yukle_kayitlar(dosya: Path | None, portfoy: bool) -> list[dict]:
    """Defter.json veya portfoy.json'dan kapalı işlemleri yükler."""
    alan = "portfoy.json" if portfoy else "defter.json"

    if dosya and dosya.exists():
        raw = json.loads(dosya.read_text(encoding="utf-8"))
    else:
        raw = _pages_json(alan)
        if raw is None:
            print(f"HATA: {alan} ne local ne de Pages'te bulunamadı.", file=sys.stderr)
            return []

    if portfoy:
        kayitlar = raw.get("pozisyonlar", [])
        # sembol alanı farlı: portfoy Pozisyon kullanır
        return [dict(id=p.get("id", 0), sembol=p.get("sembol", ""),
                     interval=p.get("interval", ""), taraf=p.get("yon", "Long"),
                     giris=p.get("giris", 0), stop=p.get("stop", 0),
                     hedef=p.get("hedef", 0), rr=p.get("rr", 0),
                     durum=p.get("durum", "?"),
                     acilis_zaman=p.get("acilis_zaman", ""))
                for p in kayitlar
                if p.get("durum") in ("TP", "STOP", "Expired", "Manuel")]
    else:
        kayitlar = raw.get("kayitlar", [])
        return [k for k in kayitlar
                if k.get("durum") in ("TP", "STOP", "Expired")]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _rapor(sonuclar: list[SaglaSonuc], json_mod: bool) -> None:
    if json_mod:
        print(json.dumps([vars(s) for s in sonuclar], ensure_ascii=False, indent=2))
        return

    eslesme = sum(1 for s in sonuclar if s.eslesme)
    uyusmaz = [s for s in sonuclar if not s.eslesme]
    tp_k = sum(1 for s in sonuclar if s.kayitli_durum == "TP")
    stop_k = sum(1 for s in sonuclar if s.kayitli_durum == "STOP")
    tp_g = sum(1 for s in sonuclar if s.gercek_durum == "TP")
    stop_g = sum(1 for s in sonuclar if s.gercek_durum == "STOP")

    W = 72
    print("═" * W)
    print("📊  ZAMANSAL SAĞLAMA RAPORU — OHLCV'ye göre TP/STOP doğrulaması")
    print("═" * W)
    print(f"  İncelenen işlem  : {len(sonuclar)}")
    print(f"  Kayıtlı          : {tp_k} TP  ·  {stop_k} STOP")
    print(f"  OHLCV gerçek     : {tp_g} TP  ·  {stop_g} STOP")
    print(f"  Eşleşme          : {eslesme}/{len(sonuclar)}"
          f"  ({'✅ tümü doğru' if not uyusmaz else f'⚠️  {len(uyusmaz)} uyuşmazlık'})")
    print("─" * W)

    if not uyusmaz:
        print("  Tüm kayıtlar OHLCV verileriyle örtüşüyor. ✅")
    else:
        print("  UYUŞMAZLIKLAR:")
        for s in uyusmaz:
            print(f"  [{s.id:>3}] {s.sembol:<12} {s.interval:<4} {s.taraf:<5} "
                  f"kayıt={s.kayitli_durum:<8} gerçek={s.gercek_durum:<8}"
                  f"{f'  → {s.not_}' if s.not_ else ''}")

    print("─" * W)
    print("  DETAY (ilk 25):")
    for s in sonuclar[:25]:
        ikon = "✅" if s.eslesme else "❌"
        giris_k = s.giris_bari[:16] if s.giris_bari else "—"
        cikis_k = s.cikis_bari[:16] if s.cikis_bari else "—"
        print(f"  {ikon} [{s.id:>3}] {s.sembol:<12} {s.interval:<4} {s.taraf:<6}"
              f" kayıt={s.kayitli_durum:<8} gerçek={s.gercek_durum:<8}"
              f" giriş@{giris_k}  çıkış@{cikis_k}"
              f"  bekleme={s.bekleme_bar}bar  süreç={s.surec_bar}bar")
    print("═" * W)


def ana(args=None):
    p = argparse.ArgumentParser(description="Zamansal Trade Sağlama")
    p.add_argument("--dosya", type=Path, default=None,
                   help="defter.json veya portfoy.json yolu (yoksa Pages'ten indirilir)")
    p.add_argument("--portfoy", action="store_true",
                   help="defter.json yerine portfoy.json kullan")
    p.add_argument("--json", dest="json_mod", action="store_true",
                   help="JSON formatında çıktı ver")
    p.add_argument("--max-bekleme", type=int, default=24,
                   help="girişin dolması için beklenecek maksimum bar (varsayılan: 24)")
    p.add_argument("--limit", type=int, default=None,
                   help="en fazla bu kadar işlemi kontrol et (test için)")
    ns = p.parse_args(args)

    kayitlar = _yukle_kayitlar(ns.dosya, ns.portfoy)
    if not kayitlar:
        print("Doğrulanacak kapalı işlem bulunamadı.")
        return

    if ns.limit:
        kayitlar = kayitlar[:ns.limit]

    sonuclar: list[SaglaSonuc] = []
    for i, k in enumerate(kayitlar, 1):
        if not ns.json_mod:
            print(f"  [{i}/{len(kayitlar)}] {k.get('sembol','?')} "
                  f"{k.get('interval','?')} kontrol ediliyor...", end="\r", flush=True)
        s = sagla_kayit(k, max_bekleme=ns.max_bekleme)
        sonuclar.append(s)

    if not ns.json_mod:
        print(" " * 60, end="\r")
    _rapor(sonuclar, ns.json_mod)


if __name__ == "__main__":
    ana()
