"""Binance Testnet bağlantı/emir aracı — Kiraz execution motoru testi.

GÜVENLİK: yalnızca testnet (sahte para). Anahtarlar ortam değişkeninden:
    BINANCE_TESTNET_KEY · BINANCE_TESTNET_SECRET
    (testnet.binancefuture.com → API Key)

Kullanım:
    python backtest/borsa.py --hesap            # bakiye + pozisyon + emirler
    python backtest/borsa.py --plan BTCUSDT Long 95000 93000 97000   # kuru plan
    python backtest/borsa.py --test-emir BTCUSDT Long 95000 93000 97000 --onayla
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz.kiraz import emir_plani, KirazMotor


def _borsa():
    from miraz.borsa import BinanceTestnet, BorsaHata
    try:
        b = BinanceTestnet.ortamdan()
        b.baglanti_testi()
        return b
    except BorsaHata as e:
        print(f"⚠️  {e}")
        sys.exit(1)


def _aday(symbol, taraf, giris, stop, hedef):
    return {"symbol": symbol, "taraf": taraf, "giris": float(giris),
            "stop": float(stop), "hedef": float(hedef), "rr": 1.0}


def main() -> None:
    ap = argparse.ArgumentParser(description="Binance Testnet aracı")
    ap.add_argument("--hesap", action="store_true",
                    help="bakiye + açık pozisyon + açık emirler")
    ap.add_argument("--plan", nargs=5, metavar=("SYM", "TARAF", "GIRIS",
                    "STOP", "HEDEF"), help="kuru emir planı (ağa emir atmaz)")
    ap.add_argument("--test-emir", nargs=5, metavar=("SYM", "TARAF", "GIRIS",
                    "STOP", "HEDEF"), help="TESTNET bracket emri (—onayla şart)")
    ap.add_argument("--r", type=float, default=25.0, help="R (dolar risk)")
    ap.add_argument("--onayla", action="store_true",
                    help="--test-emir için gerçek testnet gönderimini onayla")
    args = ap.parse_args()

    if args.plan:
        sym, taraf, g, s, h = args.plan
        plan = emir_plani(_aday(sym, taraf, g, s, h), r_dolar=args.r)
        print(f"📋 Kuru plan — {plan.symbol} {plan.taraf} miktar={plan.miktar}")
        for e in plan.emirler():
            print(f"   {e['rol']:6} {e['side']:4} {e['tip']:18} "
                  f"{e.get('fiyat') or e.get('stop_fiyat')}")
        return

    b = _borsa()

    if args.hesap:
        oz = b.ozet()
        print(f"💰 Cüzdan {oz['wallet']:.2f} USDT · kullanılabilir "
              f"{oz['available']:.2f} · açık PNL {oz['unrealized']:+.2f}")
        poz = b.pozisyonlar()
        print(f"📌 Açık pozisyon: {len(poz)}")
        for p in poz:
            print(f"   {p['yon']:5} {p['symbol']:12} miktar {p['miktar']} "
                  f"giriş {p['giris']} PNL {p['pnl']:+.2f}")
        emir = b.acik_emirler()
        print(f"⏳ Açık emir: {len(emir)}")
        return

    if args.test_emir:
        sym, taraf, g, s, h = args.test_emir
        plan = emir_plani(_aday(sym, taraf, g, s, h), r_dolar=args.r)
        print(f"📋 {plan.symbol} {plan.taraf} miktar={plan.miktar}")
        for e in plan.emirler():
            print(f"   {e['rol']:6} {e['side']:4} {e['tip']:18} "
                  f"{e.get('fiyat') or e.get('stop_fiyat')}")
        if not args.onayla:
            print("⚠️  Gönderim için --onayla ekle (TESTNET, sahte para).")
            return
        sonuc = KirazMotor(b).uygula(plan, kuru=False)
        print(f"✅ {sonuc['durum']} — {sonuc.get('emirler')}")
        return

    ap.print_help()


if __name__ == "__main__":
    main()
