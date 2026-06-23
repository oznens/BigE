using System;
using System.Collections.Generic;
using System.Globalization;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Media;
using TerminalMiraz.Models;

namespace TerminalMiraz.Controls;

/// <summary>
/// terminalMiraz mum grafiği — Canvas üzerine doğrudan çizim (WPF/Avalonia
/// custom render). Mum gövde+fitil, ENTRY/SL/TP seviye çizgileri, ZONE kutusu
/// ve alt MACD paneli. @tradermiraz'ın Trade Playback / Canlı Grafik ekranı.
/// </summary>
public class MumGrafik : Control
{
    public static readonly StyledProperty<GrafikVeri?> VeriProperty =
        AvaloniaProperty.Register<MumGrafik, GrafikVeri?>(nameof(Veri));

    /// <summary>Playback için: yalnızca ilk N mumu çiz (0 = hepsi).</summary>
    public static readonly StyledProperty<int> GorunenBarProperty =
        AvaloniaProperty.Register<MumGrafik, int>(nameof(GorunenBar));

    public GrafikVeri? Veri
    {
        get => GetValue(VeriProperty);
        set => SetValue(VeriProperty, value);
    }

    public int GorunenBar
    {
        get => GetValue(GorunenBarProperty);
        set => SetValue(GorunenBarProperty, value);
    }

    static MumGrafik()
    {
        AffectsRender<MumGrafik>(VeriProperty, GorunenBarProperty);
    }

    // Palet (App.axaml ile aynı)
    private static readonly Color CYesil = Color.Parse("#26d07c");
    private static readonly Color CKirmizi = Color.Parse("#ef4d56");
    private static readonly Color CMavi = Color.Parse("#3da5ff");
    private static readonly Color CSari = Color.Parse("#f5b942");
    private static readonly Color CVurgu = Color.Parse("#00e5c8");
    private static readonly Color CSoluk = Color.Parse("#5a7a96");
    private static readonly Color CMetin = Color.Parse("#d8e8f5");
    private static readonly Color CKenar = Color.Parse("#1c2d3f");

    private static readonly Typeface Yazi = new("Inter");

    public override void Render(DrawingContext ctx)
    {
        var w = Bounds.Width;
        var h = Bounds.Height;
        if (w < 20 || h < 20) return;

        // arkaplan
        ctx.FillRectangle(new SolidColorBrush(Color.Parse("#0a0e14")),
            new Rect(0, 0, w, h));

        var v = Veri;
        if (v?.Mumlar == null || v.Mumlar.Count == 0)
        {
            CizMetin(ctx, "veri yok", 12, 20, CSoluk, 12);
            return;
        }

        var tumMum = v.Mumlar;
        int n = GorunenBar > 0 ? Math.Min(GorunenBar, tumMum.Count) : tumMum.Count;
        if (n < 1) n = tumMum.Count;
        var mumlar = tumMum.GetRange(0, n);

        double padL = 8, padR = 72, padT = 10;
        double mainH = h * 0.68;
        double macdH = h * 0.18;
        double macdY = padT + mainH + 16;

        // fiyat aralığı (mum + seviyeler)
        double lo = double.MaxValue, hi = double.MinValue;
        foreach (var c in mumlar)
        {
            lo = Math.Min(lo, c[3]); // low
            hi = Math.Max(hi, c[2]); // high
        }
        var sv = v.Seviye;
        if (sv != null)
        {
            foreach (var p in new[] { sv.Giris, sv.Stop, sv.Hedef })
                if (p.HasValue) { lo = Math.Min(lo, p.Value); hi = Math.Max(hi, p.Value); }
        }
        if (hi <= lo) { hi = lo + 1; }
        double pad = (hi - lo) * 0.06;
        lo -= pad; hi += pad;

        double Xc(int i) => padL + i * (w - padL - padR) / mumlar.Count;
        double Yc(double p) => padT + (hi - p) / (hi - lo) * mainH;
        double cw = Math.Max(1, (w - padL - padR) / mumlar.Count * 0.62);

        // ZONE kutusu (varsa)
        // mumlar
        for (int i = 0; i < mumlar.Count; i++)
        {
            var c = mumlar[i];
            double o = c[1], high = c[2], low = c[3], close = c[4];
            bool up = close >= o;
            var renk = new SolidColorBrush(up ? CYesil : CKirmizi);
            double x = Xc(i) + cw / 2;
            // fitil
            ctx.DrawLine(new Pen(renk, 1),
                new Point(x, Yc(high)), new Point(x, Yc(low)));
            // gövde
            double yo = Yc(o), yclose = Yc(close);
            double top = Math.Min(yo, yclose);
            double bh = Math.Max(1, Math.Abs(yclose - yo));
            ctx.FillRectangle(renk, new Rect(Xc(i), top, cw, bh));
        }

        // seviye çizgileri
        void Cizgi(double? p, Color renk, string etk)
        {
            if (!p.HasValue) return;
            double y = Yc(p.Value);
            var pen = new Pen(new SolidColorBrush(renk), 1, new DashStyle(new double[] { 5, 4 }, 0));
            ctx.DrawLine(pen, new Point(padL, y), new Point(w - padR, y));
            CizMetin(ctx, etk, w - padR + 3, y - 6, renk, 10);
        }
        if (sv != null)
        {
            Cizgi(sv.Giris, CMetin, "ENTRY " + Fmt(sv.Giris));
            Cizgi(sv.Stop, CKirmizi, "SL " + Fmt(sv.Stop));
            Cizgi(sv.Hedef, CYesil, "TP " + Fmt(sv.Hedef));
            if (sv.Giris.HasValue)
                CizMetin(ctx, "SQL Memory", padL + 4, Yc(sv.Giris.Value) - 14, CMavi, 10);
        }

        // MACD paneli
        var mc = v.Macd;
        if (mc != null && mc.Hist.Count > 0)
        {
            double mlo = 0, mhi = 0;
            foreach (var lst in new[] { mc.Hist, mc.MacdLine, mc.Sinyal })
                foreach (var val in lst)
                    if (val.HasValue) { mlo = Math.Min(mlo, val.Value); mhi = Math.Max(mhi, val.Value); }
            double mr = (mhi - mlo); if (mr <= 0) mr = 1;
            double My(double val) => macdY + (mhi - val) / mr * macdH;

            ctx.DrawLine(new Pen(new SolidColorBrush(CKenar), 1),
                new Point(padL, My(0)), new Point(w - padR, My(0)));
            CizMetin(ctx, "MACD 12 26 9", padL, macdY - 14, CSoluk, 10);

            for (int i = 0; i < mc.Hist.Count && i < mumlar.Count; i++)
            {
                if (!mc.Hist[i].HasValue) continue;
                double val = mc.Hist[i]!.Value;
                var renk = new SolidColorBrush(val >= 0 ? CYesil : CKirmizi, 0.55);
                double y0 = My(0), y1 = My(val);
                ctx.FillRectangle(renk, new Rect(Xc(i), Math.Min(y0, y1), cw, Math.Max(1, Math.Abs(y1 - y0))));
            }
            CizSeri(ctx, mc.MacdLine, mumlar.Count, Xc, My, cw, CMavi);
            CizSeri(ctx, mc.Sinyal, mumlar.Count, Xc, My, cw, CSari);
        }
    }

    private static void CizSeri(DrawingContext ctx, List<double?> arr, int max,
        Func<int, double> Xc, Func<double, double> My, double cw, Color renk)
    {
        var pen = new Pen(new SolidColorBrush(renk), 1.2);
        Point? onceki = null;
        for (int i = 0; i < arr.Count && i < max; i++)
        {
            if (!arr[i].HasValue) { onceki = null; continue; }
            var p = new Point(Xc(i) + cw / 2, My(arr[i]!.Value));
            if (onceki.HasValue) ctx.DrawLine(pen, onceki.Value, p);
            onceki = p;
        }
    }

    private static void CizMetin(DrawingContext ctx, string s, double x, double y,
        Color renk, double boyut)
    {
        var ft = new FormattedText(s, CultureInfo.InvariantCulture,
            FlowDirection.LeftToRight, Yazi, boyut, new SolidColorBrush(renk));
        ctx.DrawText(ft, new Point(x, y));
    }

    private static string Fmt(double? v)
    {
        if (!v.HasValue) return "—";
        double a = Math.Abs(v.Value);
        if (a >= 1000) return v.Value.ToString("N0", CultureInfo.InvariantCulture);
        if (a >= 1) return v.Value.ToString("0.####", CultureInfo.InvariantCulture);
        if (a >= 0.01) return v.Value.ToString("0.#####", CultureInfo.InvariantCulture);
        return v.Value.ToString("0.########", CultureInfo.InvariantCulture);
    }
}
