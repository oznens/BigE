"""Statik site üreteci — hafıza (defter/portföy) kalıcılığı testleri.

GitHub Actions konteynerı her run'da temiz başladığı için, statik_site önceki
snapshot'ın yayınladığı defter.json/portfoy.json'u indirip yükler. Bu round-trip
çalışmazsa her tarama sıfırdan başlar ve setuplar/lifecycle kaybolur.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import backtest.statik_site as s
from miraz.gozlemci import Defter
from miraz.portfoy import Portfoy


def _ornek_kayit(id_=1, durum="Açık"):
    return {"id": id_, "acilis_zaman": "2026-06-22T00:00:00+00:00",
            "sembol": "BTCUSDT", "interval": "1h", "taraf": "Long",
            "kalite": "A", "guven": 80.0, "giris": 100.0, "stop": 95.0,
            "hedef": 110.0, "rr": 2.0, "durum": durum}


def test_onceki_state_yayinlanani_yukler(tmp_path):
    """Yayınlanmış defter.json/portfoy.json → bir sonraki run yükler (file://)."""
    # Önceki snapshot'ı taklit et: cikti dizinine state dosyaları yaz
    defter = Defter()
    (tmp_path / "defter.json").write_text(json.dumps(
        {"id_sayac": 5, "tarama_turu": 7, "toplam_tarama": 40,
         "son_dongu": "2026-06-22T00:00:00+00:00",
         "kayitlar": [_ornek_kayit(1, "Açık"), _ornek_kayit(2, "Aday")]},
        ensure_ascii=False), encoding="utf-8")
    Portfoy(r_dolar=25.0).kaydet(tmp_path / "portfoy.json")

    taban = tmp_path.resolve().as_uri()          # file:///.../tmp
    d, p = s._onceki_state(tmp_path, taban)
    assert len(d.kayitlar) == 2                    # iki kayıt taşındı
    assert d.tarama_turu == 7                      # sayaç korundu
    assert d.kayitlar[0].sembol == "BTCUSDT"
    assert isinstance(p, Portfoy)


def test_onceki_state_yoksa_bos_baslar(tmp_path):
    """İlk run / 404 / ağ yok → boş defter+portföy (patlamaz)."""
    d, p = s._onceki_state(tmp_path, None)
    assert len(d.kayitlar) == 0
    assert len(p.pozisyonlar) == 0
    # erişilemez URL de sessizce boş başlatmalı
    d2, p2 = s._onceki_state(tmp_path, "http://127.0.0.1:0/yok")
    assert len(d2.kayitlar) == 0 and len(p2.pozisyonlar) == 0


def test_onceki_state_bozuk_portfoy_bos_doner(tmp_path):
    """Bozuk portfoy.json yüklemeyi patlatmaz, boş Portföy döner."""
    (tmp_path / "portfoy.json").write_text("{bozuk json", encoding="utf-8")
    _, p = s._onceki_state(tmp_path, None)
    assert isinstance(p, Portfoy) and len(p.pozisyonlar) == 0
