using System;
using System.Collections.Generic;
using System.Linq;

namespace TerminalMiraz.Services;

/// <summary>
/// Klasik indikatörler — src/miraz/indikator.py portu (EMA/SMA/RSI/MACD).
/// Saf OHLC'den hesaplanır, dış veri gerekmez.
/// </summary>
public static class Indikator
{
    /// <summary>Üstel hareketli ortalama (adjust=false, span=periyot).</summary>
    public static double?[] Ema(IReadOnlyList<double> seri, int periyot)
    {
        var ciktilar = new double?[seri.Count];
        if (seri.Count == 0) return ciktilar;
        double alpha = 2.0 / (periyot + 1);
        double prev = seri[0];
        ciktilar[0] = prev;
        for (int i = 1; i < seri.Count; i++)
        {
            prev = seri[i] * alpha + prev * (1 - alpha);
            ciktilar[i] = prev;
        }
        return ciktilar;
    }

    /// <summary>Basit hareketli ortalama (min_periods=periyot).</summary>
    public static double?[] Sma(IReadOnlyList<double> seri, int periyot)
    {
        var ciktilar = new double?[seri.Count];
        double toplam = 0;
        for (int i = 0; i < seri.Count; i++)
        {
            toplam += seri[i];
            if (i >= periyot) toplam -= seri[i - periyot];
            if (i >= periyot - 1) ciktilar[i] = toplam / periyot;
        }
        return ciktilar;
    }

    /// <summary>Wilder RSI (0-100).</summary>
    public static double?[] Rsi(IReadOnlyList<double> seri, int periyot = 14)
    {
        var ciktilar = new double?[seri.Count];
        if (seri.Count <= periyot) return ciktilar;
        double alpha = 1.0 / periyot;
        double ortKazanc = 0, ortKayip = 0;
        for (int i = 1; i < seri.Count; i++)
        {
            double delta = seri[i] - seri[i - 1];
            double kazanc = Math.Max(delta, 0);
            double kayip = Math.Max(-delta, 0);
            if (i == 1) { ortKazanc = kazanc; ortKayip = kayip; }
            else
            {
                ortKazanc = kazanc * alpha + ortKazanc * (1 - alpha);
                ortKayip = kayip * alpha + ortKayip * (1 - alpha);
            }
            if (i >= periyot)
            {
                double rs = ortKayip == 0 ? 100 : ortKazanc / ortKayip;
                ciktilar[i] = 100 - 100 / (1 + rs);
            }
        }
        return ciktilar;
    }

    /// <summary>MACD çizgisi, sinyal çizgisi, histogram.</summary>
    public static (double?[] Macd, double?[] Sinyal, double?[] Hist) Macd(
        IReadOnlyList<double> seri, int hizli = 12, int yavas = 26, int sinyal = 9)
    {
        var emaHizli = Ema(seri, hizli);
        var emaYavas = Ema(seri, yavas);
        var macd = new double?[seri.Count];
        var macdDolu = new List<double>();
        for (int i = 0; i < seri.Count; i++)
        {
            if (emaHizli[i].HasValue && emaYavas[i].HasValue)
            {
                macd[i] = emaHizli[i] - emaYavas[i];
                macdDolu.Add(macd[i]!.Value);
            }
        }
        // sinyal = macd üzerinde EMA(sinyal)
        var sinyalDizi = new double?[seri.Count];
        var hist = new double?[seri.Count];
        if (macdDolu.Count > 0)
        {
            double alpha = 2.0 / (sinyal + 1);
            double prev = macd.First(x => x.HasValue)!.Value;
            for (int i = 0; i < seri.Count; i++)
            {
                if (!macd[i].HasValue) continue;
                prev = macd[i]!.Value * alpha + prev * (1 - alpha);
                sinyalDizi[i] = prev;
                hist[i] = macd[i] - prev;
            }
        }
        return (macd, sinyalDizi, hist);
    }
}
