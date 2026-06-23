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

    // ── Harmonik XABCD oranları (her pattern için toleranslı aralıklar) ──
    // AB/XA, BC/AB, CD/BC, XD/XA — %12 tolerans
    private static readonly (string Ad, double AB_Min, double AB_Max,
        double BC_Min, double BC_Max, double CD_Min, double CD_Max,
        double XD_Min, double XD_Max)[] _harmonikler =
    {
        ("Gartley",  0.541, 0.695,  0.344, 0.964,  1.144, 1.800,  0.748, 0.824),
        ("Bat",      0.344, 0.560,  0.344, 0.964,  1.456, 2.970,  0.840, 0.932),
        ("Butterfly",0.716, 0.856,  0.344, 0.964,  1.456, 2.970,  1.144, 1.456),
        ("Crab",     0.344, 0.674,  0.344, 0.964,  2.350, 4.100,  1.456, 1.800),
    };

    // Oran kontrolü — toleranslı karşılaştırma
    private static bool OranUyar(double oran, double min, double max, double tol = 0.12)
        => oran >= min * (1 - tol) && oran <= max * (1 + tol);

    /// <summary>
    /// Harmonik XABCD tespiti — son pivotlardan 5'li gruplar denenir.
    /// Bullish: X(L)→A(H)→B(L)→C(H)→D(L) veya Bearish: X(H)→A(L)→B(H)→C(L)→D(H).
    /// D noktasına yakın fiyat → PRZ (Potential Reversal Zone) sinyali.
    /// </summary>
    public static Aday? HarmonikTara(string sembol, string interval,
        IReadOnlyList<Mum> m, IReadOnlyList<Pivot> pivotlar)
    {
        double fiyat = m[^1].Kapanis;
        if (pivotlar.Count < 5) return null;

        // Son 14 pivotu tara — içten dışa her 5'li grup
        var son = pivotlar.TakeLast(14).ToList();
        Aday? enIyi = null;
        double enIyiGuven = 0;

        for (int i = son.Count - 5; i >= 0; i--)
        {
            var grup = son.Skip(i).Take(5).ToList();
            // Alternating kontrol: H-L-H-L-H veya L-H-L-H-L
            bool alternan = true;
            for (int j = 1; j < grup.Count; j++)
                if (grup[j].Tip == grup[j-1].Tip) { alternan = false; break; }
            if (!alternan) continue;

            double X = grup[0].Fiyat, A = grup[1].Fiyat,
                   B = grup[2].Fiyat, C = grup[3].Fiyat, D = grup[4].Fiyat;

            bool bullish = grup[0].Tip == 'L';  // X=dip → Bullish setup
            // Oranlar (mutlak hareket büyüklükleri)
            double XA = Math.Abs(A - X);
            double AB = Math.Abs(B - A);
            double BC = Math.Abs(C - B);
            double CD = Math.Abs(D - C);
            double XD = Math.Abs(D - X);
            if (XA < 1e-9 || AB < 1e-9 || BC < 1e-9 || CD < 1e-9) continue;

            double ratioAB = AB / XA;
            double ratioBC = BC / AB;
            double ratioCD = CD / BC;
            double ratioXD = XD / XA;

            // Yön tutarlılığı (bullish: X<A>B<C>D↓ son noktada dip)
            bool yonTutarli = bullish
                ? X < A && B < A && B < C && D < C   // L-H-L-H-L
                : X > A && B > A && B > C && D > C;  // H-L-H-L-H

            if (!yonTutarli) continue;

            foreach (var (ad, ab_min, ab_max, bc_min, bc_max, cd_min, cd_max, xd_min, xd_max) in _harmonikler)
            {
                if (!OranUyar(ratioAB, ab_min, ab_max)) continue;
                if (!OranUyar(ratioBC, bc_min, bc_max)) continue;
                if (!OranUyar(ratioCD, cd_min, cd_max)) continue;
                if (!OranUyar(ratioXD, xd_min, xd_max)) continue;

                // D noktasına yakınlık — fiyat PRZ içinde mi?
                double pRZ_tol = D * 0.04;  // D'nin %4 yakınında
                double yakinlik = 1 - Math.Min(1, Math.Abs(fiyat - D) / pRZ_tol);
                if (yakinlik < 0.1) continue;  // çok uzakta

                string taraf = bullish ? "Long" : "Short";
                double giris = D;
                double stop = bullish ? X * 0.992 : X * 1.008;  // X'in altı/üstü
                double hedef = bullish ? C : C;  // C noktası ilk hedef

                double risk = Math.Abs(giris - stop);
                double odul = Math.Abs(hedef - giris);
                if (risk <= 1e-9) continue;
                double rr = Math.Round(odul / risk, 2);
                if (rr < 1.0) continue;

                // Oran mükemmelliği skoru (her oran ne kadar ideal?)
                double oranScore = (
                    (1 - Math.Abs(ratioAB - (ab_min + ab_max) / 2) / ab_max) +
                    (1 - Math.Abs(ratioBC - (bc_min + bc_max) / 2) / bc_max) +
                    (1 - Math.Abs(ratioCD - (cd_min + cd_max) / 2) / cd_max) +
                    (1 - Math.Abs(ratioXD - (xd_min + xd_max) / 2) / xd_max)
                ) / 4;

                double guven = 45 + oranScore * 30 + yakinlik * 20 + Math.Min(5, rr * 2);
                guven = Math.Round(Math.Min(93, guven), 0);

                if (guven > enIyiGuven)
                {
                    enIyiGuven = guven;
                    string kategori = (yakinlik > 0.5 && rr >= 1.5 && guven >= 60) ? "Trade" : "Watch";
                    string kalite = guven >= 75 ? "A" : guven >= 62 ? "B" : "C";
                    enIyi = new Aday
                    {
                        Symbol = sembol, Interval = interval, Fiyat = fiyat,
                        Kategori = kategori, Kalite = kalite, Guven = guven,
                        Taraf = taraf, Kaynak = "Harmonik", Pattern = ad,
                        Giris = Math.Round(giris, 6),
                        Stop  = Math.Round(stop, 6),
                        Hedef = Math.Round(hedef, 6),
                        Rr = rr, Konseptler = new List<string> { "Harmonik", ad },
                    };
                }
            }
        }
        return enIyi;
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
            // Price Action setup bulunamadı → harmonik dene
            return HarmonikTara(sembol, interval, m, piv);
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
