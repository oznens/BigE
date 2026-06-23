using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Net.Http;
using System.Text.Json;
using System.Threading.Tasks;

namespace TerminalMiraz.Services;

/// <summary>Tek OHLCV mum (UTC açılış zamanı saniye).</summary>
public record Mum(long Zaman, double Acilis, double Yuksek, double Dusuk,
                  double Kapanis, double Hacim);

/// <summary>
/// OHLCV veri çekme — MEXC Futures (birincil) + Spot (yedek).
/// src/miraz/veri.py'nin C# portu. Borsada natif olmayan TF (2h) alt TF'den
/// (1h) toplanır (resample).
/// </summary>
public class Veri
{
    private static readonly HttpClient _http = new() { Timeout = TimeSpan.FromSeconds(20) };

    private const string FutBase = "https://contract.mexc.com/api/v1/contract/kline";
    private const string SpotBase = "https://api.mexc.com/api/v3/klines";

    private static readonly Dictionary<string, string> FutIv = new()
    {
        ["1m"] = "Min1", ["5m"] = "Min5", ["15m"] = "Min15", ["30m"] = "Min30",
        ["1h"] = "Min60", ["4h"] = "Hour4", ["8h"] = "Hour8", ["1d"] = "Day1",
    };
    private static readonly Dictionary<string, int> IvSaniye = new()
    {
        ["1m"] = 60, ["5m"] = 300, ["15m"] = 900, ["30m"] = 1800, ["1h"] = 3600,
        ["2h"] = 7200, ["4h"] = 14400, ["8h"] = 28800, ["1d"] = 86400,
    };

    /// <summary>
    /// OHLCV indirir. 2h → 1h çekip 2 saate toplar (MEXC 2h sunmaz).
    /// </summary>
    public static async Task<List<Mum>> Indir(string sembol, string interval, int gun = 120)
    {
        if (interval == "2h")
        {
            var alt = await Indir(sembol, "1h", gun);
            return Resample2h(alt);
        }

        long endMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
        long startMs = endMs - (long)gun * 24 * 3600 * 1000;

        try
        {
            var fut = await FuturesCek(sembol, interval, startMs, endMs);
            if (fut.Count > 0) return fut;
        }
        catch { /* spot'a düş */ }

        return await SpotCek(sembol, interval, startMs, endMs);
    }

    private static string FutSembol(string s)
    {
        foreach (var kote in new[] { "USDT", "USDC" })
            if (s.EndsWith(kote) && !s.Contains('_'))
                return s[..^kote.Length] + "_" + kote;
        return s;
    }

    private static async Task<List<Mum>> FuturesCek(string sembol, string interval,
        long startMs, long endMs)
    {
        if (!FutIv.TryGetValue(interval, out var iv))
            throw new NotSupportedException($"futures TF: {interval}");
        int sec = IvSaniye[interval];
        string sym = FutSembol(sembol);
        long pencere = 2000L * sec;
        var rows = new List<Mum>();
        long imlec = startMs / 1000, sonS = endMs / 1000;

        while (imlec < sonS)
        {
            long bitis = Math.Min(imlec + pencere, sonS);
            var url = $"{FutBase}/{sym}?interval={iv}&start={imlec}&end={bitis}";
            var json = await _http.GetStringAsync(url);
            using var doc = JsonDocument.Parse(json);
            if (!doc.RootElement.TryGetProperty("data", out var d)) break;
            if (!d.TryGetProperty("time", out var t) || t.GetArrayLength() == 0) break;

            var time = t.EnumerateArray().Select(x => x.GetInt64()).ToArray();
            var o = Dizi(d, "open"); var h = Dizi(d, "high");
            var l = Dizi(d, "low"); var c = Dizi(d, "close");
            var v = d.TryGetProperty("vol", out var vv)
                ? vv.EnumerateArray().Select(x => x.GetDouble()).ToArray()
                : new double[time.Length];

            for (int i = 0; i < time.Length; i++)
                rows.Add(new Mum(time[i], o[i], h[i], l[i], c[i], v[i]));

            long ileri = time[^1] + sec;
            if (ileri <= imlec) break;
            imlec = ileri;
            await Task.Delay(120);
        }
        return rows;
    }

    private static double[] Dizi(JsonElement d, string ad) =>
        d.GetProperty(ad).EnumerateArray().Select(x => x.GetDouble()).ToArray();

    private static async Task<List<Mum>> SpotCek(string sembol, string interval,
        long startMs, long endMs)
    {
        string iv = interval == "1h" ? "60m" : interval;
        var rows = new List<Mum>();
        long imlec = startMs;
        while (imlec < endMs)
        {
            var url = $"{SpotBase}?symbol={sembol}&interval={iv}&startTime={imlec}&endTime={endMs}&limit=1000";
            var json = await _http.GetStringAsync(url);
            using var doc = JsonDocument.Parse(json);
            var arr = doc.RootElement;
            if (arr.GetArrayLength() == 0) break;
            foreach (var k in arr.EnumerateArray())
            {
                long ot = k[0].GetInt64();
                rows.Add(new Mum(ot / 1000,
                    Par(k[1]), Par(k[2]), Par(k[3]), Par(k[4]), Par(k[5])));
            }
            long son = arr[arr.GetArrayLength() - 1][6].GetInt64() + 1;
            if (son <= imlec) break;
            imlec = son;
            await Task.Delay(150);
        }
        return rows;
    }

    private static double Par(JsonElement e) => e.ValueKind == JsonValueKind.String
        ? double.Parse(e.GetString()!, CultureInfo.InvariantCulture)
        : e.GetDouble();

    /// <summary>1h mumları 2h'a toplar (left-label, closed-left).</summary>
    private static List<Mum> Resample2h(List<Mum> alt)
    {
        var ciktilar = new List<Mum>();
        for (int i = 0; i < alt.Count; i += 2)
        {
            var a = alt[i];
            if (i + 1 < alt.Count)
            {
                var b = alt[i + 1];
                ciktilar.Add(new Mum(a.Zaman, a.Acilis,
                    Math.Max(a.Yuksek, b.Yuksek), Math.Min(a.Dusuk, b.Dusuk),
                    b.Kapanis, a.Hacim + b.Hacim));
            }
            else ciktilar.Add(a);
        }
        return ciktilar;
    }
}
