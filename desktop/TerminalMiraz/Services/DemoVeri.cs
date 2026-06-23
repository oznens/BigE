using System;
using System.Collections.Generic;
using TerminalMiraz.Models;

namespace TerminalMiraz.Services;

/// <summary>Geliştirme/doğrulama için örnek Durum üretir (donut + takvim testi).</summary>
public static class DemoVeri
{
    public static Durum Olustur()
    {
        var bugun = DateTime.UtcNow;
        var d = new Durum
        {
            Hazir = true,
            Zaman = bugun.ToString("yyyy-MM-ddTHH:mm:ss"),
            TaramaNo = 552, ToplamTarama = 12480,
            Wr = 62.4, ToplamR = 42, AktifKayit = 22,
            PerfCurve = new PerfCurve
            {
                Bugun = new PerfStat { Sonuc = 17, Tp = 12, Sl = 5, Wr = 70.6 },
                Dun = new PerfStat { Sonuc = 14, Tp = 9, Sl = 5, Wr = 64.3 },
                Tum = new PerfStat { Sonuc = 450, Tp = 254, Sl = 196, Wr = 56.4 },
            },
            Buckets = new()
            {
                ["Price Action"] = new Bucket { Tp = 8, Stop = 1, Toplam = 9, Wr = 88.9 },
                ["Harmonik"] = new Bucket { Tp = 4, Stop = 12, Toplam = 16, Wr = 25 },
                ["Late"] = new Bucket { Tp = 6, Stop = 6, Toplam = 12, Wr = 50 },
            },
            LifecycleOzet = new() { ["No-Entry"] = 14, ["Expired"] = 2, ["Cancelled"] = 28 },
        };

        // 30 günlük takvim — değişken sonuçlar
        var rnd = new Random(7);
        for (int i = 0; i < 30; i++)
        {
            var gun = new DateTime(bugun.Year, bugun.Month, 1).AddDays(i);
            if (gun.Month != bugun.Month) break;
            int tp = rnd.Next(0, 6), stop = rnd.Next(0, 4);
            if (tp + stop == 0) continue;
            double r = tp * 2.0 - stop;
            string ds = gun.ToString("yyyy-MM-dd");
            d.Takvim[ds] = new TakvimGun
            {
                Tp = tp, Stop = stop, R = Math.Round(r, 1),
                Pa = new TakvimAlt { Tp = tp, Stop = 0, R = tp * 2.0 },
                Harmonik = new TakvimAlt { Tp = 0, Stop = stop, R = -stop },
                Satirlar = new()
                {
                    new TakvimSatir { Sembol = "BTCUSDT", Interval = "1h", Durum = tp > stop ? "TP" : "STOP",
                        RSonuc = tp > stop ? 2.0 : -1.0, Kaynak = "Price Action", Kapanis = ds + "T14:30" },
                    new TakvimSatir { Sembol = "ETHUSDT", Interval = "4h", Durum = "TP",
                        RSonuc = 2.0, Kaynak = "Harmonik", Kapanis = ds + "T09:15" },
                }
            };
        }

        // trade memory
        string[] semboller = { "ONTUSDT", "ATOMUSDT", "XRPUSDT", "DASHUSDT", "SOLUSDT", "AVAXUSDT" };
        foreach (var s in semboller)
            d.TradeMemory.Add(new TradeMemory
            {
                Sembol = s, Interval = "1h", Durum = rnd.Next(2) == 0 ? "TP" : "STOP",
                Kaynak = "Price Action", Taraf = "Long", Guven = rnd.Next(50, 90),
                RSonuc = rnd.Next(2) == 0 ? 2.0 : -1.0, Giris = 100, Kapanis = bugun.ToString("yyyy-MM-dd"),
            });

        d.Memory = new Memory
        {
            Parite = new()
            {
                ["BTCUSDT"] = new PerfKirilim { Tp = 12, Stop = 4, R = 20, Wr = 75 },
                ["ETHUSDT"] = new PerfKirilim { Tp = 8, Stop = 6, R = 10, Wr = 57.1 },
            },
            Tf = new()
            {
                ["1h"] = new PerfKirilim { Tp = 20, Stop = 10, R = 30, Wr = 66.7 },
                ["4h"] = new PerfKirilim { Tp = 6, Stop = 5, R = 7, Wr = 54.5 },
            },
        };
        return d;
    }
}
