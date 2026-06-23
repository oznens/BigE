using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using TerminalMiraz.Models;

namespace TerminalMiraz.Services;

/// <summary>
/// Native tarama motoru — masaüstü uygulamasının kendi başına setup bulması.
/// Miraz metodolojisine sadık (METODOLOJI.md): swing pivot → destek/arz bölgesi
/// → çift tepe/dip + trend kırılımı → entry/SL/TP + R/R + güven skoru.
///
/// Python radar'ının tam kopyası değil ama aynı mantık iskeleti: bölge tepkisi,
/// yön (Long mavi kutu / Short mor kutu), 1R:2R hedef, kategori (Trade/Watch).
/// </summary>
public class Tarayici
{
    public record Pivot(int Idx, double Fiyat, char Tip);  // 'H' / 'L'

    /// <summary>Bir sembol/TF tarar; setup yoksa null.</summary>
    public static async Task<Aday?> Tara(string sembol, string interval, int gun = 120)
    {
        var mumlar = await Veri.Indir(sembol, interval, gun);
        if (mumlar.Count < 60) return null;
        return Degerlendir(sembol, interval, mumlar);
    }

    /// <summary>Önceden çekilmiş mumlarla değerlendirir (önbellekli tarama için).</summary>
    public static Aday? Degerlendir(string sembol, string interval, List<Mum> mumlar)
        => mumlar.Count >= 60 ? DegerlendirIc(sembol, interval, mumlar) : null;

    public static List<Pivot> PivotListesi(IReadOnlyList<Mum> m, int n = 5)
    {
        var raw = new List<Pivot>();
        for (int i = n; i < m.Count - n; i++)
        {
            bool sh = true, sl = true;
            for (int j = i - n; j <= i + n; j++)
            {
                if (m[j].Yuksek > m[i].Yuksek) sh = false;
                if (m[j].Dusuk < m[i].Dusuk) sl = false;
            }
            if (sh) raw.Add(new Pivot(i, m[i].Yuksek, 'H'));
            else if (sl) raw.Add(new Pivot(i, m[i].Dusuk, 'L'));
        }
        if (raw.Count == 0) return raw;

        // alternating filtre (ardışık aynı tip → daha ekstrem olan)
        var alt = new List<Pivot> { raw[0] };
        foreach (var p in raw.Skip(1))
        {
            var son = alt[^1];
            if (p.Tip == son.Tip)
            {
                if (p.Tip == 'H' && p.Fiyat > son.Fiyat) alt[^1] = p;
                else if (p.Tip == 'L' && p.Fiyat < son.Fiyat) alt[^1] = p;
            }
            else alt.Add(p);
        }
        return alt;
    }

    private static Aday? DegerlendirIc(string sembol, string interval, List<Mum> m)
    {
        double fiyat = m[^1].Kapanis;
        var piv = PivotListesi(m, 5);
        if (piv.Count < 4) return null;

        var sonPiv = piv.TakeLast(12).ToList();
        var tepeler = sonPiv.Where(p => p.Tip == 'H').Select(p => p.Fiyat).ToList();
        var dipler = sonPiv.Where(p => p.Tip == 'L').Select(p => p.Fiyat).ToList();
        if (tepeler.Count < 2 || dipler.Count < 2) return null;

        double sonTepe = tepeler[^1], oncekiTepe = tepeler[^2];
        double sonDip = dipler[^1], oncekiDip = dipler[^2];

        // trend yapısı: HH/HL → yukarı, LH/LL → aşağı
        bool yukariYapi = sonTepe > oncekiTepe && sonDip > oncekiDip;
        bool asagiYapi = sonTepe < oncekiTepe && sonDip < oncekiDip;

        // çift tepe/dip toleransı (%0.8)
        bool ciftTepe = Math.Abs(sonTepe - oncekiTepe) / oncekiTepe < 0.008;
        bool ciftDip = Math.Abs(sonDip - oncekiDip) / oncekiDip < 0.008;

        string taraf;
        double giris, stop, hedef;
        string pattern;
        var konseptler = new List<string>();

        // En yakın arz (tepe) ve talep (dip) bölgesi
        double arz = tepeler.Where(t => t >= fiyat).DefaultIfEmpty(sonTepe).Min();
        double talep = dipler.Where(t => t <= fiyat).DefaultIfEmpty(sonDip).Max();

        if (ciftTepe || asagiYapi)
        {
            // SHORT — mor kutu (arz) tepkisi, aşağı hedef
            taraf = "Short";
            giris = arz;
            stop = arz * 1.012;                 // bölge üstü
            hedef = talep;                       // alt talep bölgesi
            pattern = ciftTepe ? "Çift Tepe" : null!;
            konseptler.Add("Root");
            if (asagiYapi) konseptler.Add("Shear");
        }
        else if (ciftDip || yukariYapi)
        {
            // LONG — mavi kutu (talep) tepkisi, yukarı hedef
            taraf = "Long";
            giris = talep;
            stop = talep * 0.988;
            hedef = arz;
            pattern = ciftDip ? "Çift Dip" : null!;
            konseptler.Add("Root");
            if (yukariYapi) konseptler.Add("Shear");
        }
        else
        {
            return null;  // net yapı yok → setup yok
        }

        // R/R
        double risk = Math.Abs(giris - stop);
        double odul = Math.Abs(hedef - giris);
        if (risk <= 0) return null;
        double rr = Math.Round(odul / risk, 2);
        if (rr < 1.2) return null;  // zayıf R/R → ele

        // güven skoru (0-100): R/R + yapı netliği + bölgeye yakınlık
        double yakinlik = 1 - Math.Min(1, Math.Abs(fiyat - giris) / fiyat / 0.05);
        double guven = 40 + Math.Min(30, rr * 8) + yakinlik * 25
                       + (pattern != null ? 5 : 0);
        guven = Math.Round(Math.Min(95, guven), 0);

        // kategori: yakın + iyi R/R → Trade, aksi Watch
        string kategori = (yakinlik > 0.6 && rr >= 2 && guven >= 65) ? "Trade" : "Watch";

        string kalite = guven >= 78 ? "A" : guven >= 65 ? "B" : "C";

        return new Aday
        {
            Symbol = sembol, Interval = interval, Fiyat = fiyat,
            Kategori = kategori, Kalite = kalite, Guven = guven,
            Taraf = taraf, Kaynak = "Price Action", Pattern = pattern,
            Giris = Math.Round(giris, 6), Stop = Math.Round(stop, 6),
            Hedef = Math.Round(hedef, 6), Rr = rr, Konseptler = konseptler,
        };
    }

    /// <summary>Mumlardan grafik verisi (mum dizisi + MACD) üretir.</summary>
    public static GrafikVeri GrafikUret(IReadOnlyList<Mum> mumlar, Aday? aday, int barSayisi = 160)
    {
        var son = mumlar.Count > barSayisi
            ? mumlar.Skip(mumlar.Count - barSayisi).ToList()
            : mumlar.ToList();

        var gv = new GrafikVeri();
        foreach (var c in son)
            gv.Mumlar.Add(new List<double> { c.Zaman, c.Acilis, c.Yuksek, c.Dusuk, c.Kapanis });

        var kapanislar = son.Select(c => c.Kapanis).ToList();
        var (macd, sinyal, hist) = Indikator.Macd(kapanislar);
        gv.Macd = new Macd
        {
            MacdLine = macd.ToList(),
            Sinyal = sinyal.ToList(),
            Hist = hist.ToList(),
        };

        if (aday != null)
        {
            gv.Seviye = new Seviye
            {
                Giris = aday.Giris, Stop = aday.Stop, Hedef = aday.Hedef,
                Taraf = aday.Taraf, Pattern = aday.Pattern, Kaynak = aday.Kaynak, Rr = aday.Rr,
            };
        }
        return gv;
    }
}
