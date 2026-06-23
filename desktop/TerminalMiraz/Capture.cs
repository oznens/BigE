using System;
using System.IO;
using System.Threading;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Headless;
using Avalonia.Media.Imaging;
using Avalonia.Threading;
using TerminalMiraz.ViewModels;
using TerminalMiraz.Views;

namespace TerminalMiraz;

/// <summary>
/// Geliştirme/doğrulama yardımcısı — pencereyi headless (Skia) render edip PNG'ye
/// yazar. Gerçek X sunucusu gerektirmez; CI/sandbox'ta görsel kontrol için.
/// </summary>
internal static class Capture
{
    public static void Calistir(string pngYol, string sekme)
    {
        var sdk = AppBuilder.Configure<App>()
            .UseSkia()
            .UseHeadless(new AvaloniaHeadlessPlatformOptions { UseHeadlessDrawing = false })
            .WithInterFont();

        sdk.SetupWithoutStarting();

        WriteableBitmap? frame = null;
        bool yerel = sekme == "yerel";
        // "demo:<sekme>" → örnek veriyle render (donut/takvim doğrulaması)
        bool demo = sekme.StartsWith("demo:");
        string gercekSekme = demo ? sekme.Substring(5) : (yerel ? "scanner" : sekme);
        var vm = new MainWindowViewModel { AktifSekme = gercekSekme };
        var pencere = new MainWindow { DataContext = vm };
        pencere.Show();

        if (demo)
        {
            vm.OtoYenileKapat();   // canlı veri demo'yu ezmesin
            vm.Uygula(Services.DemoVeri.Olustur());
        }
        if (yerel)
            vm.YerelTaraCommand.Execute(null);  // native tarama tetikle

        // veri yüklensin + layout otursun diye frame işle (yerel tarama ağ ister → uzun)
        int dongu = yerel ? 400 : 60;
        for (int i = 0; i < dongu; i++)
        {
            Dispatcher.UIThread.RunJobs();
            Thread.Sleep(50);
        }
        Dispatcher.UIThread.RunJobs();

        frame = pencere.CaptureRenderedFrame();
        if (frame != null)
        {
            using var fs = File.Create(pngYol);
            frame.Save(fs);
            Console.WriteLine($"yazıldı: {pngYol}");
        }
        else
        {
            Console.WriteLine("render frame alınamadı");
        }
    }
}
