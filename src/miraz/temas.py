"""Temas davranışı istatistiği — bir bölge geçmişte nasıl davrandı? (terminalMiraz).

@tradermiraz: "Bir destek ne kadar çok test edilirse o kadar zayıflar; her
dokunuş bir miktar likidite yer. Taze (1-2 kez dokunulmuş) ve her seferinde
sert tepki vermiş bölge en güçlüsüdür." terminalMiraz bunu "temas davranışı"
olarak istatistiklendirir: bölge kaç kez dokunulmuş, kaçında tepki verip
kaçında kırılmış → TP/Skip kararına katkı.

Bu modül bir fiyat bandı [alt, ust] için geçmişi tarar; her "temas olayını"
tepki / kırılma / içeride (sürüyor) olarak sınıflar ve özet + güven etkisi
üretir.

Kullanım:
    from miraz.temas import temas_analizi
    t = temas_analizi(df, alt=95000, ust=97000)
    print(t.metin)
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .bicim import f as _f


@dataclass
class TemasOlayi:
    basla_idx: int        # bölgeye girilen bar
    bitis_idx: int        # olayın kapandığı bar
    tip: str              # "tepki" / "kırılma" / "içeride"
    dip: float            # olay boyunca görülen en düşük fiyat


@dataclass
class TemasSonuc:
    alt: float
    ust: float
    olaylar: list = field(default_factory=list)   # list[TemasOlayi]
    tepki: int = 0
    kirilma: int = 0
    icerde: int = 0
    son_davranis: str = "yok"     # son kapanan olayın tipi
    tepki_orani: float = 0.0      # tepki / (tepki + kırılma)
    yorgunluk: float = 0.0        # 0..1 — bölge ne kadar yıpranmış
    guven_etkisi: float = 0.0     # önerilen güven düzeltmesi (puan)
    metin: str = ""

    @property
    def toplam(self) -> int:
        return self.tepki + self.kirilma + self.icerde


def temas_olaylari(df: pd.DataFrame, alt: float, ust: float) -> list:
    """Fiyatın [alt, ust] bandıyla geçmiş etkileşimini olaylara böler (destek).

    Durum makinesi (yukarıdan gelen destek bakışı):
      • 'ust'  : fiyat bölgenin üstünde (son kapanış > ust)
      • 'ic'   : bölge test ediliyor (low ≤ ust, henüz kırılmadı/sekmedi)
      • 'alt'  : bölge aşağı kırıldı (kapanış < alt)
    Geçişler:
      ust→ic  : low ≤ ust            (bölgeye girildi)
      ic→tepki: close > ust          (reddedip üstte kapandı = tepki)
      ic→kırıl: close < alt          (aşağı kapanış = kırılma)
      alt→ust : close > ust          (toparlanma — yeni temas için hazır)
    """
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()
    n = len(df)
    if n == 0:
        return []

    olaylar: list[TemasOlayi] = []
    durum = "ust" if close[0] > ust else ("alt" if close[0] < alt else "ic")
    basla = 0 if durum == "ic" else None
    dip = low[0] if durum == "ic" else None

    for i in range(n):
        if durum == "ust":
            if low[i] <= ust:
                durum = "ic"
                basla = i
                dip = low[i]
        elif durum == "ic":
            dip = min(dip, low[i])
            if close[i] < alt:
                olaylar.append(TemasOlayi(basla, i, "kırılma", float(dip)))
                durum = "alt"
            elif close[i] > ust:
                olaylar.append(TemasOlayi(basla, i, "tepki", float(dip)))
                durum = "ust"
        elif durum == "alt":
            if close[i] > ust:
                durum = "ust"

    # Hâlâ bölge içindeyse açık (içeride) olay
    if durum == "ic" and basla is not None:
        olaylar.append(TemasOlayi(basla, n - 1, "içeride", float(dip)))

    return olaylar


def _guven_etkisi(tepki: int, kirilma: int, icerde: int,
                  son_davranis: str, tepki_orani: float,
                  yorgunluk: float) -> float:
    """Temas geçmişinden güven düzeltmesi (puan) önerir (long açısından).

    • Son davranış kırılma → bölge çürük, güçlü negatif (−12).
    • Hiç dokunulmamış (taze) → küçük pozitif (+3) belirsizlik.
    • Her seferinde tepki (kırılma yok) + az dokunuş → güçlü pozitif.
    • Çok dokunuş (yorgun) → tepki olsa bile zayıflama cezası.
    """
    if son_davranis == "kırılma":
        return -12.0
    toplam = tepki + kirilma
    if toplam == 0:
        return 3.0                      # taze bölge — hafif olumlu

    etki = 0.0
    # Tepki oranı katkısı (0.5 nötr civarı)
    etki += (tepki_orani - 0.5) * 24    # %100 tepki → +12, %0 → −12
    # Yorgunluk cezası (çok test edilmiş bölge zayıflar)
    etki -= yorgunluk * 8
    return round(max(-12.0, min(12.0, etki)), 1)


def temas_analizi(df: pd.DataFrame, alt: float, ust: float) -> TemasSonuc:
    """[alt, ust] destek bandının geçmiş temas davranışını özetler."""
    if alt > ust:
        alt, ust = ust, alt
    olaylar = temas_olaylari(df, alt, ust)

    tepki = sum(1 for o in olaylar if o.tip == "tepki")
    kirilma = sum(1 for o in olaylar if o.tip == "kırılma")
    icerde = sum(1 for o in olaylar if o.tip == "içeride")

    kapanan = [o for o in olaylar if o.tip in ("tepki", "kırılma")]
    son_davranis = kapanan[-1].tip if kapanan else "yok"
    tepki_orani = round(tepki / (tepki + kirilma), 3) if (tepki + kirilma) else 0.0
    # Yorgunluk: dokunuş sayısıyla artar (4 dokunuşta doygunluk)
    yorgunluk = round(min(tepki + kirilma, 4) / 4.0, 3)

    etki = _guven_etkisi(tepki, kirilma, icerde, son_davranis,
                         tepki_orani, yorgunluk)

    if not olaylar:
        metin = (f"👆 Temas: {_f(alt)}–{_f(ust)} bandı geçmişte hiç test "
                 f"edilmemiş (taze bölge).")
    else:
        son_txt = {"tepki": "son sefer tepki verdi ✅",
                   "kırılma": "son sefer KIRILDI 🔴",
                   "yok": "henüz kapanmadı"}.get(son_davranis, son_davranis)
        metin = (
            f"👆 Temas davranışı ({tepki + kirilma + icerde} olay): "
            f"{tepki} tepki · {kirilma} kırılma"
            + (f" · {icerde} sürüyor" if icerde else "")
            + f" → tepki oranı %{tepki_orani*100:.0f}, {son_txt} "
            f"(güven {etki:+.0f})")

    return TemasSonuc(
        alt=round(alt, 6), ust=round(ust, 6), olaylar=olaylar,
        tepki=tepki, kirilma=kirilma, icerde=icerde,
        son_davranis=son_davranis, tepki_orani=tepki_orani,
        yorgunluk=yorgunluk, guven_etkisi=etki, metin=metin)


def senaryo_temas(senaryo, df: pd.DataFrame) -> TemasSonuc | None:
    """Bir senaryonun destek bölgesi için temas analizi (kısa yol)."""
    alt = getattr(senaryo, "bolge_alt", None)
    ust = getattr(senaryo, "bolge_ust", None)
    if alt is None or ust is None:
        return None
    return temas_analizi(df, float(alt), float(ust))
