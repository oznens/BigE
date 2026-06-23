using Avalonia;
using System;

namespace TerminalMiraz;

sealed class Program
{
    // Initialization code. Don't use any Avalonia, third-party APIs or any
    // SynchronizationContext-reliant code before AppMain is called: things aren't initialized
    // yet and stuff might break.
    [STAThread]
    public static void Main(string[] args)
    {
        // "capture <png> [sekme]" → headless render (geliştirme/doğrulama için)
        if (args.Length >= 2 && args[0] == "capture")
        {
            Capture.Calistir(args[1], args.Length >= 3 ? args[2] : "performance");
            return;
        }
        BuildAvaloniaApp().StartWithClassicDesktopLifetime(args);
    }

    // Avalonia configuration, don't remove; also used by visual designer.
    public static AppBuilder BuildAvaloniaApp()
        => AppBuilder.Configure<App>()
            .UsePlatformDetect()
            .WithInterFont()
            .LogToTrace();
}
