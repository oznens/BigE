"""Portföy CLI — paper-trading motoru (terminalMiraz tarzı aktif işlem takibi).

Kullanım:
    # Radar taraması yap ve Trade sinyallerini portföye ekle
    python backtest/portfoy.py --ekle-radar --semboller BTCUSDT ETHUSDT SOLUSDT

    # Açık pozisyonları gerçek veriyle güncelle
    python backtest/portfoy.py --guncelle --semboller BTCUSDT ETHUSDT

    # Sadece tabloyu göster
    python backtest/portfoy.py

    # Belirli bir pozisyonu manuel kapat
    python backtest/portfoy.py --kapat-id 3
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz import veri
from miraz.portfoy import Portfoy, radar_sinyallerini_ekle
from miraz.radar import radar_tara, VARSAYILAN_EVREN

PORTFOY_DOSYA = Path(__file__).resolve().parents[1] / "portfoy.json"


def _yukle_veya_yeni(r_dolar: float) -> Portfoy:
    if PORTFOY_DOSYA.exists():
        return Portfoy.yukle(PORTFOY_DOSYA)
    return Portfoy(r_dolar=r_dolar)


def main() -> None:
    ap = argparse.ArgumentParser(description="Paper-trading portföy yönetimi")
    ap.add_argument("--semboller", nargs="+", default=VARSAYILAN_EVREN,
                    help="Radar / güncelleme için sembol listesi")
    ap.add_argument("--tf", nargs="+", default=["4h"],
                    help="Taranacak zaman dilim(ler)i")
    ap.add_argument("--gun", type=int, default=400,
                    help="İndirilecek geçmiş bar sayısı (gün)")
    ap.add_argument("--r-dolar", type=float, default=25.0,
                    help="1R = kaç dolar?")
    ap.add_argument("--ekle-radar", action="store_true",
                    help="Radar taraması yap, Trade sinyallerini portföye ekle")
    ap.add_argument("--guncelle", action="store_true",
                    help="Açık pozisyonları gerçek veriyle güncelle (TP/STOP takibi)")
    ap.add_argument("--kapat-id", type=int, default=None,
                    help="Belirtilen ID'li pozisyonu manuel kapat")
    ap.add_argument("--sadece-aktif", action="store_true",
                    help="Tabloyu sadece aktif pozisyonlarla göster")
    ap.add_argument("--dosya", default=str(PORTFOY_DOSYA),
                    help="Portföy JSON dosyası")
    args = ap.parse_args()

    pf_dosya = Path(args.dosya)
    pf = _yukle_veya_yeni(args.r_dolar)

    # Manuel kapatma
    if args.kapat_id is not None:
        if pf.kapat_manuel(args.kapat_id):
            print(f"✅ Pozisyon #{args.kapat_id} manuel kapatıldı.")
        else:
            print(f"⚠️  Pozisyon #{args.kapat_id} bulunamadı veya zaten kapalı.")
        pf.kaydet(pf_dosya)
        print(pf.tablo(sadece_aktif=args.sadece_aktif))
        return

    # Radar → portföye ekle
    if args.ekle_radar:
        print(f"🔭 Radar taranıyor: {args.semboller} / {args.tf} ...")
        rapor = radar_tara(args.semboller, args.tf, gun=args.gun)
        print(rapor.tablo(sadece="Trade"))
        eklendi = radar_sinyallerini_ekle(pf, rapor)
        print(f"\n➕ {eklendi} yeni Trade sinyali portföye eklendi.")

    # Güncelle
    if args.guncelle:
        aktif_sembolleri = {(p.sembol, p.interval) for p in pf.aktif}
        if not aktif_sembolleri:
            print("ℹ️  Güncellenecek açık/bekleyen pozisyon yok.")
        else:
            print(f"🔄 {len(aktif_sembolleri)} sembol güncelleniyor ...")
            df_sozluk = {}
            for (sem, ivl) in aktif_sembolleri:
                try:
                    df_sozluk[(sem, ivl)] = veri.indir(sem, ivl, gun=args.gun,
                                                        force=True)
                except Exception as e:
                    print(f"  ⚠️  {sem}/{ivl}: {e}")
            degisenler = pf.guncelle_hepsi(df_sozluk)
            if degisenler:
                for p in degisenler:
                    ikon = {"TP": "✅", "STOP": "🔴", "Açık": "🟢"}.get(
                        p.durum, "⬜")
                    r_txt = (f" → {p.r_sonuc:+.1f}R"
                             if p.durum in ("TP", "STOP") else "")
                    print(f"  {ikon} {p.sembol}/{p.interval}: {p.durum}{r_txt}")
            else:
                print("  ℹ️  Değişen pozisyon yok.")

    pf.kaydet(pf_dosya)
    print(f"\n{'═'*66}")
    print(pf.tablo(sadece_aktif=args.sadece_aktif))


if __name__ == "__main__":
    main()
