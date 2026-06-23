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
        var pencere = new MainWindow
        {
            DataContext = new MainWindowViewModel { AktifSekme = sekme },
        };
        pencere.Show();

        // veri yüklensin + layout otursun diye birkaç frame işle
        for (int i = 0; i < 60; i++)
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
