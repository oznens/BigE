# terminalMiraz — Masaüstü Uygulaması (C# / Avalonia)

@tradermiraz'ın terminalMiraz'ının **native masaüstü** sürümü. Miraz orijinalini
C#/WPF (Windows) ile yazmış; bu sürüm aynı dili (C# / .NET) ve aynı XAML mantığını
kullanır ama **Avalonia** ile her işletim sisteminde (Windows / macOS / Linux) çalışır.

## Ne yapar?

Python tarama motorumuzun (`src/miraz/`) GitHub Pages'e yayınladığı JSON'u okur ve
Miraz'ın ekranlarını native pencerede gösterir:

| Sekme | Karşılığı (Miraz ekranı) |
|-------|--------------------------|
| **PERFORMANCE** | Performance Intelligence — Result Engines, win rate, terminal readout, trade memory |
| **JOURNAL** | Scanner Journal — günlük TP/STOP kayıt defteri |
| **AYLIK R** | Aylık R Kazanç Hesabı — takvim + kümülatif R tablosu |
| **MEMORY** | Scanner Market Hafızası — parite/TF/konsept performansı |
| **SCANNER** | Canlı tarama — Binance execution, aday akışı, mum grafiği + MACD |
| **PLAYBACK** | Trade Playback — kapanan işlemi bar-bar oynatma |

Mum grafiği (`Controls/MumGrafik.cs`) tamamen custom çizim: mum gövde/fitil,
ENTRY/SL/TP seviye çizgileri, SQL Memory etiketi, alt MACD paneli.

## Çalıştırma

```bash
# .NET 8 SDK gerekli (https://dot.net)
cd desktop/TerminalMiraz
dotnet run
```

Varsayılan veri kaynağı: `https://oznens.github.io/BigE`. Değiştirmek için:

```bash
# yerel Python sunucusuna bağlan (backtest/sunucu.py --port 8000)
MIRAZ_BASE=http://localhost:8000 dotnet run
```

## Mimari

```
Program.cs          → giriş noktası (+ "capture" headless render modu)
App.axaml           → terminalMiraz koyu teması (renk paleti, stiller)
Models/Modeller.cs  → durum.json / grafik JSON şeması (Python pipeline ile birebir)
Services/MirazApi.cs→ JSON çekme (Pages veya yerel sunucu)
Controls/MumGrafik.cs → custom mum + MACD grafiği (Render override)
ViewModels/         → MainWindowViewModel (6 sekme) + kart VM'leri
Views/MainWindow.axaml → tüm arayüz (XAML)
```

## Doğrulama (headless render)

X sunucusu olmadan pencereyi PNG'ye render eder:

```bash
dotnet run -- capture cikti.png scanner
```
