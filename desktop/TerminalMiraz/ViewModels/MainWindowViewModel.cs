using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Avalonia.Threading;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using TerminalMiraz.Models;
using TerminalMiraz.Services;

namespace TerminalMiraz.ViewModels;

public partial class MainWindowViewModel : ViewModelBase
{
    private readonly MirazApi _api = new();
    private readonly DispatcherTimer _timer;

    // ── sekme yönetimi ──
    [ObservableProperty] private string _aktifSekme = "performance";

    public bool PerformanceAktif => AktifSekme == "performance";
    public bool JournalAktif => AktifSekme == "journal";
    public bool AylikAktif => AktifSekme == "aylik";
    public bool MemoryAktif => AktifSekme == "memory";
    public bool ScannerAktif => AktifSekme == "scanner";
    public bool PlaybackAktif => AktifSekme == "playback";

    partial void OnAktifSekmeChanged(string value)
    {
        OnPropertyChanged(nameof(PerformanceAktif));
        OnPropertyChanged(nameof(JournalAktif));
        OnPropertyChanged(nameof(AylikAktif));
        OnPropertyChanged(nameof(MemoryAktif));
        OnPropertyChanged(nameof(ScannerAktif));
        OnPropertyChanged(nameof(PlaybackAktif));
    }

    [RelayCommand]
    private void SekmeSec(string sekme) => AktifSekme = sekme;

    // ── durum ──
    [ObservableProperty] private string _saatMetni = "bağlanıyor…";
    [ObservableProperty] private string _veriKaynagi = "";

    // ── PERFORMANCE ──
    [ObservableProperty] private string _piTarih = "";
    [ObservableProperty] private int _piBugunN;
    [ObservableProperty] private string _piWr = "%0";
    [ObservableProperty] private string _piTpSl = "TP 0 · SL 0";
    [ObservableProperty] private int _piDunN;
    [ObservableProperty] private string _piDunWr = "%0";
    [ObservableProperty] private int _piTumN;
    [ObservableProperty] private string _piTumWr = "%0";
    [ObservableProperty] private string _piReadoutBaslik = "";
    [ObservableProperty] private string _piReadoutMetin = "";
    public ObservableCollection<EngineVM> Engines { get; } = new();
    public ObservableCollection<TradeMemoryVM> TradeMemoryKartlar { get; } = new();

    // ── SCANNER ──
    [ObservableProperty] private string _execWallet = "0";
    [ObservableProperty] private int _execAktif;
    [ObservableProperty] private int _execBekleyen;
    [ObservableProperty] private string _execDailyPnl = "+0.0R";
    [ObservableProperty] private string _execRisk = "%0";
    [ObservableProperty] private string _kirazDurum = "WATCHLIST MODE";
    [ObservableProperty] private string _kirazMesaj = "";
    [ObservableProperty] private string _ozetSatir = "";
    public ObservableCollection<BucketVM> BucketKartlar { get; } = new();
    public ObservableCollection<AdayVM> Adaylar { get; } = new();
    public ObservableCollection<BildirimVM> Bildirimler { get; } = new();

    // grafik
    [ObservableProperty] private GrafikVeri? _grafik;
    [ObservableProperty] private string _grafikBaslik = "";
    [ObservableProperty] private MirazYorum? _seciliYorum;

    // ── JOURNAL / AYLIK R ──
    public ObservableCollection<TakvimGunVM> TakvimGunler { get; } = new();
    [ObservableProperty] private string _aylikBaslik = "";
    [ObservableProperty] private string _aylikToplamR = "+0.0R";
    [ObservableProperty] private int _aylikKazancGun;
    [ObservableProperty] private int _aylikZararGun;
    [ObservableProperty] private string _aylikOrtR = "+0.0R";
    public ObservableCollection<AylikSatirVM> AylikTablo { get; } = new();
    public ObservableCollection<JournalGunVM> JournalGunler { get; } = new();

    // ── MEMORY ──
    public ObservableCollection<BucketVM> MemoryKonsept { get; } = new();
    public ObservableCollection<PerfSatirVM> MemoryParite { get; } = new();
    public ObservableCollection<PerfSatirVM> MemoryTf { get; } = new();
    [ObservableProperty] private string _memoryWrHeader = "%0";

    // ── PLAYBACK ──
    public ObservableCollection<TradeMemoryVM> PlaybackListe { get; } = new();
    [ObservableProperty] private GrafikVeri? _playbackGrafik;
    [ObservableProperty] private int _playbackBar;
    [ObservableProperty] private int _playbackMaxBar;
    [ObservableProperty] private string _playbackBaslik = "TRADE PLAYBACK";
    [ObservableProperty] private string _playbackDurum = "";
    [ObservableProperty] private string _playbackInfo = "";
    [ObservableProperty] private bool _playbackOynuyor;
    private DispatcherTimer? _playbackTimer;
    private TradeMemoryVM? _playbackSecili;

    public MainWindowViewModel()
    {
        _timer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(15) };
        _timer.Tick += async (_, _) => await Yenile();
        _timer.Start();
        _ = Yenile();
    }

    private bool _ilkGrafikYuklendi;

    public async Task Yenile()
    {
        var d = await _api.DurumGetir();
        if (d == null)
        {
            SaatMetni = "bağlantı yok — yeniden deneniyor…";
            return;
        }
        VeriKaynagi = _api.Taban;
        SaatMetni = $"son güncelleme: {d.Zaman.Replace("T", " ")} UTC · " +
                    $"tarama #{d.TaramaNo} · ∑{d.ToplamTarama}";

        DoldurPerformance(d);
        DoldurScanner(d);
        DoldurTakvim(d);
        DoldurMemory(d);
        DoldurPlayback(d);

        if (!_ilkGrafikYuklendi && d.VarsayilanGrafik != null)
        {
            _ilkGrafikYuklendi = true;
            await GrafikYukle(d.VarsayilanGrafik.Symbol, d.VarsayilanGrafik.Interval);
        }
    }

    // ── PERFORMANCE doldur ──
    private void DoldurPerformance(Durum d)
    {
        var pc = d.PerfCurve;
        PiTarih = DateTime.UtcNow.ToString("dd MMMM yyyy", new CultureInfo("tr-TR"));
        PiBugunN = pc.Bugun.Sonuc;
        PiWr = $"%{pc.Bugun.Wr:0.#}";
        PiTpSl = $"TP {pc.Bugun.Tp} · SL {pc.Bugun.Sl}";
        PiDunN = pc.Dun.Sonuc;
        PiDunWr = $"%{pc.Dun.Wr:0.#} WR";
        PiTumN = pc.Tum.Sonuc;
        PiTumWr = $"%{pc.Tum.Wr:0.#}";

        double diff = pc.Bugun.Wr - pc.Dun.Wr;
        PiReadoutBaslik = pc.Bugun.Wr > pc.Dun.Wr ? "BUGÜN DÜNDEN GÜÇLÜ"
            : pc.Bugun.Wr < pc.Dun.Wr ? "DÜN BUGÜNDEN GÜÇLÜYDÜ" : "DÜNE BENZER PERFORMANS";
        PiReadoutMetin =
            $"Win rate farkı {(diff >= 0 ? "+" : "")}{diff:0.#} puan · TP/SL {pc.Bugun.Tp}/{pc.Bugun.Sl}\n" +
            $"GENEL BAŞARI %{pc.Tum.Wr:0.#} · TOPLAM TP {pc.Tum.Tp} · TOPLAM SL {pc.Tum.Sl}";

        Engines.Clear();
        var bkt = d.Buckets;
        Bucket B(string k) => bkt.TryGetValue(k, out var x) ? x : new Bucket();
        var lc = d.LifecycleOzet;
        int Lc(string k) => lc.TryGetValue(k, out var v) ? v : 0;
        AddEngine("TUMU", pc.Tum.Tp, pc.Tum.Sl, "#00e5c8");
        AddEngine("PRICE ACTION", B("Price Action").Tp, B("Price Action").Stop, "#26d07c");
        AddEngine("HARMONİK", B("Harmonik").Tp, B("Harmonik").Stop, "#9b7bd4");
        AddEngine("LATE", B("Late").Tp, B("Late").Stop, "#f5b942");
        AddEngine("NO-ENTRY", Lc("No-Entry"), 0, "#5a7a96");
        AddEngine("EXPIRED", Lc("Expired"), 0, "#5a7a96");
        AddEngine("CANCELLED", Lc("Cancelled"), 0, "#444444");

        TradeMemoryKartlar.Clear();
        foreach (var t in d.TradeMemory.Take(16))
            TradeMemoryKartlar.Add(new TradeMemoryVM(t));
    }

    private void AddEngine(string ad, int tp, int sl, string renk)
    {
        int tot = tp + sl;
        int wr = tot > 0 ? (int)Math.Round(100.0 * tp / tot) : 0;
        Engines.Add(new EngineVM { Ad = ad, Toplam = tot, Wr = wr, Renk = renk,
            WrMetin = tot > 0 ? $"%{wr}" : "0" });
    }

    // ── SCANNER doldur ──
    private void DoldurScanner(Durum d)
    {
        var e = d.Execution;
        ExecWallet = e.Wallet.ToString("N0", CultureInfo.InvariantCulture);
        ExecAktif = e.Aktif;
        ExecBekleyen = e.Bekleyen;
        ExecDailyPnl = SgnR(e.DailyPnl);
        ExecRisk = $"%{e.OpenRisk:0.#}";
        KirazDurum = e.KirazDurum;
        KirazMesaj = e.KirazMesaj;
        OzetSatir = $"Aktif: {d.AktifKayit} kayıt · WR %{d.Wr:0.#} · Toplam {SgnR(d.ToplamR)}";

        BucketKartlar.Clear();
        foreach (var ad in new[] { "Price Action", "Harmonik", "Late" })
        {
            var x = d.Buckets.TryGetValue(ad, out var b) ? b : new Bucket();
            BucketKartlar.Add(new BucketVM { Ad = ad.ToUpper(), Toplam = x.Toplam,
                Tp = x.Tp, Stop = x.Stop, Wr = x.Wr,
                Renk = ad == "Price Action" ? "#26d07c" : ad == "Harmonik" ? "#9b7bd4" : "#f5b942" });
        }

        Adaylar.Clear();
        foreach (var a in d.Adaylar) Adaylar.Add(new AdayVM(a));

        Bildirimler.Clear();
        foreach (var b in d.Bildirimler) Bildirimler.Add(new BildirimVM(b));
    }

    // ── TAKVİM (journal + aylık) doldur ──
    private void DoldurTakvim(Durum d)
    {
        var simdi = DateTime.UtcNow;
        AylikBaslik = simdi.ToString("MMMM yyyy", new CultureInfo("tr-TR"));
        string ayPrefix = simdi.ToString("yyyy-MM");

        var ayGunler = d.Takvim
            .Where(kv => kv.Key.StartsWith(ayPrefix))
            .OrderBy(kv => kv.Key).ToList();

        double topR = 0, paR = 0, hrmR = 0, cumR = 0;
        int karGun = 0, zararGun = 0, topTp = 0, topSl = 0;
        AylikTablo.Clear();
        foreach (var (gun, gv) in ayGunler)
        {
            topR += gv.R; paR += gv.Pa.R; hrmR += gv.Harmonik.R;
            topTp += gv.Tp; topSl += gv.Stop;
            if (gv.R > 0) karGun++; else if (gv.R < 0) zararGun++;
            cumR += gv.R;
            int islemN = gv.Tp + gv.Stop + gv.Expired;
            int wr = (gv.Tp + gv.Stop) > 0 ? (int)Math.Round(100.0 * gv.Tp / (gv.Tp + gv.Stop)) : 0;
            DateTime.TryParse(gun, out var dt);
            AylikTablo.Add(new AylikSatirVM {
                Tarih = dt.ToString("dd.MM"),
                Gun = dt.ToString("ddd", new CultureInfo("tr-TR")),
                Islem = islemN,
                PaR = SgnR(gv.Pa.R), HrmR = SgnR(gv.Harmonik.R), NetR = SgnR(gv.R),
                Yuzde = (gv.Tp + gv.Stop) > 0 ? $"%{wr}" : "",
                Kumulatif = SgnR(cumR),
                NetPozitif = gv.R >= 0,
            });
        }
        AylikToplamR = SgnR(topR);
        AylikKazancGun = karGun;
        AylikZararGun = zararGun;
        AylikOrtR = SgnR(ayGunler.Count > 0 ? topR / ayGunler.Count : 0);

        // Journal: günlük kartlar (son 5 kayıtlı gün)
        JournalGunler.Clear();
        foreach (var (gun, gv) in d.Takvim.OrderByDescending(kv => kv.Key).Take(5))
        {
            DateTime.TryParse(gun, out var dt);
            var jg = new JournalGunVM {
                Baslik = dt.ToString("dd MMMM, dddd", new CultureInfo("tr-TR")),
                Tp = gv.Tp, Stop = gv.Stop, Expired = gv.Expired, NetR = SgnR(gv.R),
            };
            foreach (var s in gv.Satirlar.Take(12))
                jg.Satirlar.Add(new JournalSatirVM(s));
            JournalGunler.Add(jg);
        }
    }

    // ── MEMORY doldur ──
    private void DoldurMemory(Durum d)
    {
        MemoryWrHeader = $"%{d.PerfCurve.Tum.Wr:0.#}";
        MemoryKonsept.Clear();
        foreach (var ad in new[] { "Price Action", "Harmonik", "Late" })
        {
            var x = d.Buckets.TryGetValue(ad, out var b) ? b : new Bucket();
            MemoryKonsept.Add(new BucketVM { Ad = ad.ToUpper(), Toplam = x.Toplam,
                Tp = x.Tp, Stop = x.Stop, Wr = x.Wr,
                Renk = ad == "Price Action" ? "#26d07c" : ad == "Harmonik" ? "#9b7bd4" : "#f5b942" });
        }
        MemoryParite.Clear();
        foreach (var (ad, e) in d.Memory.Parite.OrderByDescending(x => x.Value.R).Take(10))
            MemoryParite.Add(new PerfSatirVM { Ad = ad, Wr = e.Wr, Tp = e.Tp, Stop = e.Stop, R = e.R });
        MemoryTf.Clear();
        foreach (var (ad, e) in d.Memory.Tf.OrderByDescending(x => x.Value.R).Take(10))
            MemoryTf.Add(new PerfSatirVM { Ad = ad, Wr = e.Wr, Tp = e.Tp, Stop = e.Stop, R = e.R });
    }

    // ── PLAYBACK doldur ──
    private void DoldurPlayback(Durum d)
    {
        PlaybackListe.Clear();
        foreach (var t in d.TradeMemory.Take(20))
            PlaybackListe.Add(new TradeMemoryVM(t));
    }

    [RelayCommand]
    private async Task PlaybackSec(TradeMemoryVM t)
    {
        _playbackSecili = t;
        PlaybackOynatDurdur(true);
        PlaybackBaslik = $"TRADE PLAYBACK · {t.Sembol} {t.Interval}";
        PlaybackDurum = t.Durum;
        var g = await _api.GrafikGetir(t.Sembol, t.Interval);
        if (g == null) { PlaybackInfo = "grafik yüklenemedi"; return; }
        PlaybackGrafik = g;
        PlaybackMaxBar = g.Mumlar.Count;
        PlaybackBar = Math.Max(10, (int)(g.Mumlar.Count * 0.5));
        PlaybackInfoGuncelle();
    }

    [RelayCommand] private void PlaybackIleri() => PlaybackAdim(1);
    [RelayCommand] private void PlaybackGeri() => PlaybackAdim(-1);
    [RelayCommand] private void PlaybackIleri10() => PlaybackAdim(10);
    [RelayCommand] private void PlaybackGeri10() => PlaybackAdim(-10);

    private void PlaybackAdim(int n)
    {
        if (PlaybackGrafik == null) return;
        PlaybackBar = Math.Max(5, Math.Min(PlaybackMaxBar, PlaybackBar + n));
        PlaybackInfoGuncelle();
    }

    [RelayCommand]
    private void PlaybackOynat()
    {
        if (PlaybackOynuyor) { PlaybackOynatDurdur(true); return; }
        if (PlaybackGrafik == null) return;
        PlaybackOynuyor = true;
        _playbackTimer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(150) };
        _playbackTimer.Tick += (_, _) =>
        {
            if (PlaybackBar >= PlaybackMaxBar) { PlaybackOynatDurdur(true); return; }
            PlaybackBar = Math.Min(PlaybackMaxBar, PlaybackBar + 1);
            PlaybackInfoGuncelle();
        };
        _playbackTimer.Start();
    }

    private void PlaybackOynatDurdur(bool durdur)
    {
        if (durdur && _playbackTimer != null) { _playbackTimer.Stop(); _playbackTimer = null; }
        PlaybackOynuyor = false;
    }

    private void PlaybackInfoGuncelle()
    {
        PlaybackInfo = $"Bar {PlaybackBar}/{PlaybackMaxBar}";
        // GrafikVeri kopyalanmaz; MumGrafik GorunenBar property'siyle kesilir
        OnPropertyChanged(nameof(PlaybackBar));
    }

    // ── grafik yükle (aday/bildirim tıklayınca) ──
    [RelayCommand]
    public async Task GrafikYukle(string sembolInterval)
    {
        var parca = sembolInterval.Split('|');
        if (parca.Length == 2) await GrafikYukle(parca[0], parca[1]);
    }

    public async Task GrafikYukle(string sembol, string interval)
    {
        GrafikBaslik = $"· {sembol} {interval} yükleniyor…";
        var g = await _api.GrafikGetir(sembol, interval);
        if (g == null || g.Hata != null)
        {
            GrafikBaslik = $"· {sembol} {interval} — grafik yok";
            return;
        }
        Grafik = g;
        var sv = g.Seviye;
        var pat = string.Join(" · ", new[] { sv?.Kaynak, sv?.Pattern, sv?.Taraf }
            .Where(s => !string.IsNullOrEmpty(s)));
        GrafikBaslik = $"· {sembol} {interval}{(pat != "" ? $"  ({pat})" : "")}";
        SeciliYorum = g.MirazYorum;
    }

    // ── yardımcı ──
    public static string SgnR(double r) => (r >= 0 ? "+" : "") + r.ToString("0.0", CultureInfo.InvariantCulture) + "R";
}
