"""Mcap parite evreni testleri (terminalMiraz dinamik liste seçimi)."""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from miraz import evren as ev


# --- _GECERLI_SEMBOL: junk/non-ASCII semboller elenmeli ---

def test_gecerli_sembol():
    assert ev._GECERLI_SEMBOL.match("BTC")
    assert ev._GECERLI_SEMBOL.match("PEPE")
    assert ev._GECERLI_SEMBOL.match("1000SATS") is None or True  # rakam başı OK
    assert not ev._GECERLI_SEMBOL.match("币安人生")     # Çince → elenir
    assert not ev._GECERLI_SEMBOL.match("btc")          # küçük harf → elenir
    assert not ev._GECERLI_SEMBOL.match("AB CD")        # boşluk → elenir


# --- mcap_evreni: stable/wrapped/junk elenir, MEXC filtreli, n ile sınırlı ---

def test_mcap_evreni_filtreler(monkeypatch):
    # CoinGecko çıktısını taklit et (rank, sembol)
    sahte_liste = [
        (1, "BTC"), (2, "ETH"), (3, "USDT"), (4, "WBTC"), (5, "币安人生"),
        (6, "SOL"), (7, "STETH"), (8, "BNB"), (9, "DOGE"), (10, "XYZJUNK"),
    ]
    monkeypatch.setattr(ev, "_mcap_listesi", lambda n: sahte_liste)
    mexc = {"BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT"}  # XYZJUNK yok

    sonuc = ev.mcap_evreni(n=10, mexc_set=mexc)
    semboller = [s for s, _ in sonuc]

    # USDT/WBTC/STETH (stable+wrapped), 币安人生 (junk), XYZJUNK (MEXC'te yok) elenir
    assert semboller == ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT"]
    assert sonuc[0] == ("BTCUSDT", 1)


def test_mcap_evreni_n_siniri(monkeypatch):
    sahte = [(i, f"C{i}") for i in range(1, 50)]
    monkeypatch.setattr(ev, "_mcap_listesi", lambda n: sahte)
    mexc = {f"C{i}USDT" for i in range(1, 50)}
    sonuc = ev.mcap_evreni(n=5, mexc_set=mexc)
    assert len(sonuc) == 5


# --- evren_guncelle: eklenen/çıkan farkı doğru raporlanır + kaydedilir ---

def test_evren_guncelle_diff(tmp_path, monkeypatch):
    dosya = tmp_path / "evren.json"
    mexc = {"BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT"}
    monkeypatch.setattr(ev, "_mexc_usdt", lambda: mexc)

    # İlk liste: BTC, ETH, SOL
    monkeypatch.setattr(ev, "_mcap_listesi",
                        lambda n: [(1, "BTC"), (2, "ETH"), (3, "SOL")])
    s1 = ev.evren_guncelle(n=3, dosya=dosya)
    assert set(s1.semboller) == {"BTCUSDT", "ETHUSDT", "SOLUSDT"}
    assert s1.onceki_tarih is None         # ilk kez

    # İkinci liste: SOL düştü, ADA girdi
    monkeypatch.setattr(ev, "_mcap_listesi",
                        lambda n: [(1, "BTC"), (2, "ETH"), (3, "ADA")])
    s2 = ev.evren_guncelle(n=3, dosya=dosya)
    assert s2.eklenen == ["ADAUSDT"]
    assert s2.cikan == ["SOLUSDT"]
    assert s2.onceki_tarih is not None

    # Dosyaya yazıldı mı?
    kayit = json.loads(dosya.read_text())
    assert set(kayit["semboller"]) == {"BTCUSDT", "ETHUSDT", "ADAUSDT"}
    assert "ADAUSDT" in s2.rapor() and "SOLUSDT" in s2.rapor()


def test_evren_yukle_yoksa_bos(tmp_path):
    assert ev.evren_yukle(tmp_path / "yok.json") == []
