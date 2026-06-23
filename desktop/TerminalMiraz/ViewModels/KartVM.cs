using System.Collections.ObjectModel;
using System.Globalization;
using System.Linq;
using TerminalMiraz.Models;

namespace TerminalMiraz.ViewModels;

// Performance — Result Engine kutusu
public class EngineVM
{
    public string Ad { get; set; } = "";
    public int Toplam { get; set; }
    public int Wr { get; set; }
    public string WrMetin { get; set; } = "%0";
    public string Renk { get; set; } = "#00e5c8";
    public double BarGenislik => Wr * 1.2; // görsel
}

// Performance — Trade Memory kartı
public class TradeMemoryVM
{
    public string Sembol { get; }
    public string Interval { get; }
    public string Durum { get; }
    public string Kaynak { get; }
    public string Taraf { get; }
    public int Guven { get; }
    public string Giris { get; }
    public string Kapanis { get; }
    public string RSonuc { get; }
    public string SembolInterval => $"{Sembol}|{Interval}";
    public bool Tp => Durum == "TP";
    public string DurumRenk => Durum == "TP" ? "#26d07c" : Durum == "STOP" ? "#ef4d56" : "#5a7a96";

    public TradeMemoryVM(TradeMemory t)
    {
        Sembol = t.Sembol; Interval = t.Interval; Durum = t.Durum;
        Kaynak = t.Kaynak; Taraf = t.Taraf; Guven = (int)t.Guven;
        Giris = Bicim.Fmt(t.Giris);
        Kapanis = t.Kapanis.Length >= 10 ? t.Kapanis.Substring(0, 10) : t.Kapanis;
        RSonuc = MainWindowViewModel.SgnR(t.RSonuc);
    }
}

// Scanner — bucket (motor) kartı
public class BucketVM
{
    public string Ad { get; set; } = "";
    public int Toplam { get; set; }
    public int Tp { get; set; }
    public int Stop { get; set; }
    public double Wr { get; set; }
    public string Renk { get; set; } = "#26d07c";
    public string Alt => $"TP {Tp} · STOP {Stop} · %{Wr:0.#}";
}

// Scanner — aday kartı
public class AdayVM
{
    public string Symbol { get; }
    public string Interval { get; }
    public string Kategori { get; }
    public int Guven { get; }
    public string Taraf { get; }
    public string Kaynak { get; }
    public string Kaynaklar { get; }
    public string Seviyeler { get; }
    public string SembolInterval => $"{Symbol}|{Interval}";
    public bool Short => Taraf == "Short";
    public string YonOk => Short ? "▼" : "▲";
    public string KategoriRenk => Kategori == "Trade" ? "#26d07c" : "#f5b942";
    public string YonRenk => Short ? "#ef4d56" : "#26d07c";

    public AdayVM(Aday a)
    {
        Symbol = a.Symbol; Interval = a.Interval; Kategori = a.Kategori;
        Guven = (int)a.Guven; Taraf = a.Taraf; Kaynak = a.Kaynak;
        Kaynaklar = string.Join(" | ", new[] { a.Kaynak, a.Pattern, a.Taraf }
            .Where(s => !string.IsNullOrEmpty(s)));
        Seviyeler = a.Giris.HasValue
            ? $"SL {Bicim.Fmt(a.Stop)} · ENTRY {Bicim.Fmt(a.Giris)} · TP {Bicim.Fmt(a.Hedef)}"
              + (a.Rr.HasValue ? $" · {a.Rr:0.0}R" : "")
            : "—";
    }
}

// Scanner — bildirim kartı
public class BildirimVM
{
    public string Sembol { get; }
    public string Interval { get; }
    public string Durum { get; }
    public string Kaynaklar { get; }
    public string Seviyeler { get; }
    public string RMetni { get; }
    public string SembolInterval => $"{Sembol}|{Interval}";
    public string DurumRenk => Durum switch
    {
        "TP" => "#26d07c", "STOP" => "#ef4d56", "Expired" => "#f5b942",
        "Cancelled" => "#9b7bd4", _ => "#5a7a96"
    };

    public BildirimVM(Bildirim b)
    {
        Sembol = b.Sembol; Interval = b.Interval; Durum = b.Durum;
        Kaynaklar = string.Join(" | ", new[] { b.Kaynak, b.Pattern, b.Taraf }
            .Where(s => !string.IsNullOrEmpty(s)));
        Seviyeler = $"SL {Bicim.Fmt(b.Stop)} · ENTRY {Bicim.Fmt(b.Giris)} · TP {Bicim.Fmt(b.Hedef)}";
        RMetni = (b.Durum == "TP" || b.Durum == "STOP") ? MainWindowViewModel.SgnR(b.RSonuc) : "";
    }
}

// Memory / PNL — perf satırı
public class PerfSatirVM
{
    public string Ad { get; set; } = "";
    public double Wr { get; set; }
    public int Tp { get; set; }
    public int Stop { get; set; }
    public double R { get; set; }
    public string WrMetni => $"%{Wr:0.#}";
    public string TpStop => $"{Tp}/{Stop}";
    public string RMetni => (R >= 0 ? "+" : "") + R.ToString("0.0", CultureInfo.InvariantCulture);
    public string RRenk => R >= 0 ? "#26d07c" : "#ef4d56";
}

// Aylık R tablo satırı
public class AylikSatirVM
{
    public string Tarih { get; set; } = "";
    public string Gun { get; set; } = "";
    public int Islem { get; set; }
    public string PaR { get; set; } = "";
    public string HrmR { get; set; } = "";
    public string NetR { get; set; } = "";
    public string Yuzde { get; set; } = "";
    public string Kumulatif { get; set; } = "";
    public bool NetPozitif { get; set; }
    public string NetRenk => NetPozitif ? "#26d07c" : "#ef4d56";
}

// Journal günlük kart
public class JournalGunVM
{
    public string Baslik { get; set; } = "";
    public int Tp { get; set; }
    public int Stop { get; set; }
    public int Expired { get; set; }
    public string NetR { get; set; } = "";
    public ObservableCollection<JournalSatirVM> Satirlar { get; } = new();
}

public class JournalSatirVM
{
    public string Durum { get; }
    public string Sembol { get; }
    public string Interval { get; }
    public string Kaynak { get; }
    public string RSonuc { get; }
    public string Saat { get; }
    public string DurumRenk => Durum == "TP" ? "#26d07c" : Durum == "STOP" ? "#ef4d56" : "#5a7a96";

    public JournalSatirVM(TakvimSatir s)
    {
        Durum = s.Durum; Sembol = s.Sembol; Interval = s.Interval; Kaynak = s.Kaynak;
        RSonuc = MainWindowViewModel.SgnR(s.RSonuc);
        Saat = s.Kapanis.Length >= 16 ? s.Kapanis.Substring(11, 5) : "";
    }
}

// Takvim hücresi — Journal mini takvim + Aylık R takvim
public class TakvimHucreVM
{
    public string GunNo { get; set; } = "";
    public string RMetni { get; set; } = "";
    public string Yuzde { get; set; } = "";
    public bool Bos_ { get; set; }
    public bool Dolu => !Bos_;
    public bool Kar { get; set; }
    public bool Zarar { get; set; }
    public bool IslemVar { get; set; }

    // renkler
    public string ArkaRenk => Bos_ ? "Transparent"
        : Kar ? "#0e1a06" : Zarar ? "#1a0606" : "#0a0e14";
    public string KenarRenk => Bos_ ? "Transparent"
        : Kar ? "#3326d07c" : Zarar ? "#33ef4d56" : "#1c2d3f";
    public string GunRenk => Kar ? "#26d07c" : Zarar ? "#ef4d56" : "#5a7a96";

    public static TakvimHucreVM Bos() => new() { Bos_ = true };

    public static TakvimHucreVM Olustur(int gun, TerminalMiraz.Models.TakvimGun? gv, bool aylik)
    {
        var h = new TakvimHucreVM { GunNo = gun.ToString() };
        if (gv == null) return h;
        h.IslemVar = true;
        h.Kar = gv.R > 0; h.Zarar = gv.R < 0;
        h.RMetni = (gv.R >= 0 ? "+" : "") + gv.R.ToString("0.0", CultureInfo.InvariantCulture) + "R";
        int tot = gv.Tp + gv.Stop;
        h.Yuzde = tot > 0 ? $"%{(int)System.Math.Round(100.0 * gv.Tp / tot)}" : "";
        return h;
    }
}

// ── biçimleyici ──
public static class Bicim
{
    public static string Fmt(double? v)
    {
        if (!v.HasValue) return "—";
        double a = System.Math.Abs(v.Value);
        if (a >= 1000) return v.Value.ToString("N0", CultureInfo.InvariantCulture);
        if (a >= 1) return v.Value.ToString("0.####", CultureInfo.InvariantCulture);
        if (a >= 0.01) return v.Value.ToString("0.#####", CultureInfo.InvariantCulture);
        return v.Value.ToString("0.########", CultureInfo.InvariantCulture);
    }
}
