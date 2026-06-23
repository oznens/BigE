using System;
using System.Net.Http;
using System.Text.Json;
using System.Threading.Tasks;
using TerminalMiraz.Models;

namespace TerminalMiraz.Services;

/// <summary>
/// terminalMiraz veri kaynağı. Python pipeline'ının GitHub Pages'e yayınladığı
/// durum.json / grafik JSON dosyalarını okur. Böylece masaüstü uygulaması,
/// kanıtlanmış tarama motorunun (radar/harmonik/PA) çıktısını native gösterir.
///
/// TABAN_URL ortam değişkeniyle (MIRAZ_BASE) değiştirilebilir — yerel sunucu
/// (http://localhost:8000) veya başka bir Pages adresi için.
/// </summary>
public class MirazApi
{
    private static readonly string TabanUrl =
        Environment.GetEnvironmentVariable("MIRAZ_BASE")?.TrimEnd('/')
        ?? "https://oznens.github.io/BigE";

    private readonly HttpClient _http = new() { Timeout = TimeSpan.FromSeconds(20) };
    private static readonly JsonSerializerOptions _opt = new()
    {
        PropertyNameCaseInsensitive = true,
        NumberHandling = System.Text.Json.Serialization.JsonNumberHandling.AllowReadingFromString,
    };

    public string Taban => TabanUrl;

    /// <summary>Son tarama anlık görüntüsünü (durum.json) çeker.</summary>
    public async Task<Durum?> DurumGetir()
    {
        try
        {
            var json = await _http.GetStringAsync($"{TabanUrl}/durum.json");
            return JsonSerializer.Deserialize<Durum>(json, _opt);
        }
        catch
        {
            return null;
        }
    }

    /// <summary>Bir sembol/TF için grafik verisini çeker.</summary>
    public async Task<GrafikVeri?> GrafikGetir(string sembol, string interval)
    {
        try
        {
            var json = await _http.GetStringAsync(
                $"{TabanUrl}/grafik/{sembol}_{interval}.json");
            return JsonSerializer.Deserialize<GrafikVeri>(json, _opt);
        }
        catch
        {
            return null;
        }
    }
}
