using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace TerminalMiraz.Models;

// terminalMiraz Python pipeline'ının ürettiği durum.json şemasıyla birebir eşleşir
// (src/miraz/sunucu.py · durum_json). Alan adları Türkçe — JSON anahtarlarıyla aynı.

public class Durum
{
    [JsonPropertyName("hazir")] public bool Hazir { get; set; }
    [JsonPropertyName("zaman")] public string Zaman { get; set; } = "";
    [JsonPropertyName("tarama_no")] public int TaramaNo { get; set; }
    [JsonPropertyName("toplam_tarama")] public int ToplamTarama { get; set; }
    [JsonPropertyName("ozet")] public Dictionary<string, int> Ozet { get; set; } = new();
    [JsonPropertyName("durum_cubugu")] public DurumCubugu DurumCubugu { get; set; } = new();
    [JsonPropertyName("execution")] public Execution Execution { get; set; } = new();
    [JsonPropertyName("buckets")] public Dictionary<string, Bucket> Buckets { get; set; } = new();
    [JsonPropertyName("lifecycle")] public Dictionary<string, int> Lifecycle { get; set; } = new();
    [JsonPropertyName("lifecycle_ozet")] public Dictionary<string, int> LifecycleOzet { get; set; } = new();
    [JsonPropertyName("wr")] public double Wr { get; set; }
    [JsonPropertyName("toplam_r")] public double ToplamR { get; set; }
    [JsonPropertyName("aktif_kayit")] public int AktifKayit { get; set; }
    [JsonPropertyName("adaylar")] public List<Aday> Adaylar { get; set; } = new();
    [JsonPropertyName("bildirimler")] public List<Bildirim> Bildirimler { get; set; } = new();
    [JsonPropertyName("konsept_sayim")] public Dictionary<string, int> KonseptSayim { get; set; } = new();
    [JsonPropertyName("konsept_sirasi")] public List<string> KonseptSirasi { get; set; } = new();
    [JsonPropertyName("varsayilan_grafik")] public VarsayilanGrafik? VarsayilanGrafik { get; set; }
    [JsonPropertyName("pnl")] public Pnl Pnl { get; set; } = new();
    [JsonPropertyName("memory")] public Memory Memory { get; set; } = new();
    [JsonPropertyName("perf_curve")] public PerfCurve PerfCurve { get; set; } = new();
    [JsonPropertyName("trade_memory")] public List<TradeMemory> TradeMemory { get; set; } = new();
    [JsonPropertyName("takvim")] public Dictionary<string, TakvimGun> Takvim { get; set; } = new();
}

public class DurumCubugu
{
    [JsonPropertyName("kiraz")] public bool Kiraz { get; set; }
    [JsonPropertyName("sql_memory")] public bool SqlMemory { get; set; }
    [JsonPropertyName("order_engine")] public bool OrderEngine { get; set; }
    [JsonPropertyName("binance")] public bool Binance { get; set; }
}

public class Execution
{
    [JsonPropertyName("wallet")] public double Wallet { get; set; }
    [JsonPropertyName("aktif")] public int Aktif { get; set; }
    [JsonPropertyName("bekleyen")] public int Bekleyen { get; set; }
    [JsonPropertyName("daily_pnl")] public double DailyPnl { get; set; }
    [JsonPropertyName("open_risk")] public double OpenRisk { get; set; }
    [JsonPropertyName("r_dolar")] public double RDolar { get; set; }
    [JsonPropertyName("canli")] public bool Canli { get; set; }
    [JsonPropertyName("kiraz_durum")] public string KirazDurum { get; set; } = "WATCHLIST MODE";
    [JsonPropertyName("kiraz_mesaj")] public string KirazMesaj { get; set; } = "";
}

public class Bucket
{
    [JsonPropertyName("tp")] public int Tp { get; set; }
    [JsonPropertyName("stop")] public int Stop { get; set; }
    [JsonPropertyName("toplam")] public int Toplam { get; set; }
    [JsonPropertyName("wr")] public double Wr { get; set; }
}

public class Aday
{
    [JsonPropertyName("symbol")] public string Symbol { get; set; } = "";
    [JsonPropertyName("interval")] public string Interval { get; set; } = "";
    [JsonPropertyName("fiyat")] public double? Fiyat { get; set; }
    [JsonPropertyName("kategori")] public string Kategori { get; set; } = "";
    [JsonPropertyName("kalite")] public string Kalite { get; set; } = "";
    [JsonPropertyName("guven")] public double Guven { get; set; }
    [JsonPropertyName("taraf")] public string Taraf { get; set; } = "Long";
    [JsonPropertyName("kaynak")] public string Kaynak { get; set; } = "Price Action";
    [JsonPropertyName("pattern")] public string? Pattern { get; set; }
    [JsonPropertyName("giris")] public double? Giris { get; set; }
    [JsonPropertyName("stop")] public double? Stop { get; set; }
    [JsonPropertyName("hedef")] public double? Hedef { get; set; }
    [JsonPropertyName("rr")] public double? Rr { get; set; }
    [JsonPropertyName("konseptler")] public List<string> Konseptler { get; set; } = new();
    [JsonPropertyName("miraz_yorum")] public MirazYorum? MirazYorum { get; set; }
}

public class Bildirim
{
    [JsonPropertyName("sembol")] public string Sembol { get; set; } = "";
    [JsonPropertyName("interval")] public string Interval { get; set; } = "";
    [JsonPropertyName("durum")] public string Durum { get; set; } = "";
    [JsonPropertyName("taraf")] public string Taraf { get; set; } = "Long";
    [JsonPropertyName("kaynak")] public string Kaynak { get; set; } = "Price Action";
    [JsonPropertyName("pattern")] public string? Pattern { get; set; }
    [JsonPropertyName("giris")] public double? Giris { get; set; }
    [JsonPropertyName("stop")] public double? Stop { get; set; }
    [JsonPropertyName("hedef")] public double? Hedef { get; set; }
    [JsonPropertyName("r_sonuc")] public double RSonuc { get; set; }
    [JsonPropertyName("kapanis")] public string Kapanis { get; set; } = "";
}

public class MirazYorum
{
    [JsonPropertyName("baslik")] public string Baslik { get; set; } = "";
    [JsonPropertyName("ozet")] public string Ozet { get; set; } = "";
    [JsonPropertyName("govde")] public List<string> Govde { get; set; } = new();
    [JsonPropertyName("mantra")] public string Mantra { get; set; } = "";
    [JsonPropertyName("metin")] public string Metin { get; set; } = "";
}

public class VarsayilanGrafik
{
    [JsonPropertyName("symbol")] public string Symbol { get; set; } = "";
    [JsonPropertyName("interval")] public string Interval { get; set; } = "";
}

public class Pnl
{
    [JsonPropertyName("net_pnl")] public double NetPnl { get; set; }
    [JsonPropertyName("wr")] public double Wr { get; set; }
    [JsonPropertyName("profit_factor")] public double ProfitFactor { get; set; }
    [JsonPropertyName("tp")] public int Tp { get; set; }
    [JsonPropertyName("stop")] public int Stop { get; set; }
    [JsonPropertyName("en_iyi_gun")] public double EnIyiGun { get; set; }
    [JsonPropertyName("en_kotu_gun")] public double EnKotuGun { get; set; }
    [JsonPropertyName("kazanc_gun")] public int KazancGun { get; set; }
    [JsonPropertyName("zarar_gun")] public int ZararGun { get; set; }
    [JsonPropertyName("parite")] public Dictionary<string, PerfKirilim> Parite { get; set; } = new();
    [JsonPropertyName("tf")] public Dictionary<string, PerfKirilim> Tf { get; set; } = new();
}

public class PerfKirilim
{
    [JsonPropertyName("tp")] public int Tp { get; set; }
    [JsonPropertyName("stop")] public int Stop { get; set; }
    [JsonPropertyName("r")] public double R { get; set; }
    [JsonPropertyName("wr")] public double Wr { get; set; }
}

public class Memory
{
    [JsonPropertyName("parite")] public Dictionary<string, PerfKirilim> Parite { get; set; } = new();
    [JsonPropertyName("tf")] public Dictionary<string, PerfKirilim> Tf { get; set; } = new();
    [JsonPropertyName("konsept")] public Dictionary<string, Bucket> Konsept { get; set; } = new();
}

public class PerfCurve
{
    [JsonPropertyName("bugun")] public PerfStat Bugun { get; set; } = new();
    [JsonPropertyName("dun")] public PerfStat Dun { get; set; } = new();
    [JsonPropertyName("tum")] public PerfStat Tum { get; set; } = new();
}

public class PerfStat
{
    [JsonPropertyName("sonuc")] public int Sonuc { get; set; }
    [JsonPropertyName("tp")] public int Tp { get; set; }
    [JsonPropertyName("sl")] public int Sl { get; set; }
    [JsonPropertyName("wr")] public double Wr { get; set; }
}

public class TradeMemory
{
    [JsonPropertyName("sembol")] public string Sembol { get; set; } = "";
    [JsonPropertyName("interval")] public string Interval { get; set; } = "";
    [JsonPropertyName("durum")] public string Durum { get; set; } = "";
    [JsonPropertyName("taraf")] public string Taraf { get; set; } = "Long";
    [JsonPropertyName("kaynak")] public string Kaynak { get; set; } = "Price Action";
    [JsonPropertyName("r_sonuc")] public double RSonuc { get; set; }
    [JsonPropertyName("guven")] public double Guven { get; set; }
    [JsonPropertyName("kalite")] public string Kalite { get; set; } = "";
    [JsonPropertyName("giris")] public double? Giris { get; set; }
    [JsonPropertyName("kapanis")] public string Kapanis { get; set; } = "";
}

public class TakvimGun
{
    [JsonPropertyName("tp")] public int Tp { get; set; }
    [JsonPropertyName("stop")] public int Stop { get; set; }
    [JsonPropertyName("expired")] public int Expired { get; set; }
    [JsonPropertyName("r")] public double R { get; set; }
    [JsonPropertyName("pa")] public TakvimAlt Pa { get; set; } = new();
    [JsonPropertyName("harmonik")] public TakvimAlt Harmonik { get; set; } = new();
    [JsonPropertyName("satirlar")] public List<TakvimSatir> Satirlar { get; set; } = new();
}

public class TakvimAlt
{
    [JsonPropertyName("tp")] public int Tp { get; set; }
    [JsonPropertyName("stop")] public int Stop { get; set; }
    [JsonPropertyName("r")] public double R { get; set; }
}

public class TakvimSatir
{
    [JsonPropertyName("id")] public int Id { get; set; }
    [JsonPropertyName("sembol")] public string Sembol { get; set; } = "";
    [JsonPropertyName("interval")] public string Interval { get; set; } = "";
    [JsonPropertyName("taraf")] public string Taraf { get; set; } = "Long";
    [JsonPropertyName("durum")] public string Durum { get; set; } = "";
    [JsonPropertyName("r_sonuc")] public double RSonuc { get; set; }
    [JsonPropertyName("kaynak")] public string Kaynak { get; set; } = "Price Action";
    [JsonPropertyName("giris")] public double? Giris { get; set; }
    [JsonPropertyName("stop")] public double? Stop { get; set; }
    [JsonPropertyName("hedef")] public double? Hedef { get; set; }
    [JsonPropertyName("kapanis")] public string Kapanis { get; set; } = "";
}

// Grafik verisi (grafik/<SYM>_<TF>.json)
public class GrafikVeri
{
    [JsonPropertyName("mumlar")] public List<List<double>> Mumlar { get; set; } = new();
    [JsonPropertyName("seviye")] public Seviye? Seviye { get; set; }
    [JsonPropertyName("macd")] public Macd? Macd { get; set; }
    [JsonPropertyName("miraz_yorum")] public MirazYorum? MirazYorum { get; set; }
    [JsonPropertyName("hata")] public string? Hata { get; set; }
}

public class Seviye
{
    [JsonPropertyName("giris")] public double? Giris { get; set; }
    [JsonPropertyName("stop")] public double? Stop { get; set; }
    [JsonPropertyName("hedef")] public double? Hedef { get; set; }
    [JsonPropertyName("taraf")] public string Taraf { get; set; } = "Long";
    [JsonPropertyName("pattern")] public string? Pattern { get; set; }
    [JsonPropertyName("kaynak")] public string? Kaynak { get; set; }
    [JsonPropertyName("rr")] public double? Rr { get; set; }
    /// <summary>Setup'ın tespit edildiği bar indeksi — bu bardan itibaren çizgiler görünür.</summary>
    [JsonPropertyName("setup_bar")] public int? SetupBar { get; set; }
}

public class Macd
{
    [JsonPropertyName("macd")] public List<double?> MacdLine { get; set; } = new();
    [JsonPropertyName("sinyal")] public List<double?> Sinyal { get; set; } = new();
    [JsonPropertyName("hist")] public List<double?> Hist { get; set; } = new();
}
