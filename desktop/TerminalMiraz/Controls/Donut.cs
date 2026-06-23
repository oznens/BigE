using System;
using System.Globalization;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Media;

namespace TerminalMiraz.Controls;

/// <summary>
/// Donut (halka) gösterge — Performance Intelligence'taki WR donutları.
/// Yüzdeyi renkli yay olarak çizer, ortada değer + etiket.
/// </summary>
public class Donut : Control
{
    public static readonly StyledProperty<double> YuzdeProperty =
        AvaloniaProperty.Register<Donut, double>(nameof(Yuzde));
    public static readonly StyledProperty<string> EtiketProperty =
        AvaloniaProperty.Register<Donut, string>(nameof(Etiket), "");
    public static readonly StyledProperty<Color> RenkProperty =
        AvaloniaProperty.Register<Donut, Color>(nameof(Renk), Color.Parse("#00e5c8"));

    public double Yuzde { get => GetValue(YuzdeProperty); set => SetValue(YuzdeProperty, value); }
    public string Etiket { get => GetValue(EtiketProperty); set => SetValue(EtiketProperty, value); }
    public Color Renk { get => GetValue(RenkProperty); set => SetValue(RenkProperty, value); }

    static Donut()
    {
        AffectsRender<Donut>(YuzdeProperty, EtiketProperty, RenkProperty);
    }

    private static readonly Color CKenar = Color.Parse("#1c2d3f");
    private static readonly Color CSoluk = Color.Parse("#5a7a96");
    private static readonly Typeface Yazi = new("Inter");

    public override void Render(DrawingContext ctx)
    {
        double w = Bounds.Width, h = Bounds.Height;
        double cx = w / 2, cy = h / 2;
        double r = Math.Min(w, h) / 2 - 4;
        if (r < 6) return;
        double kalin = Math.Max(4, r * 0.22);

        // taban halka
        ctx.DrawEllipse(null, new Pen(new SolidColorBrush(CKenar), kalin),
            new Point(cx, cy), r, r);

        // yüzde yayı
        double oran = Math.Clamp(Yuzde / 100.0, 0, 1);
        if (oran > 0)
        {
            var pen = new Pen(new SolidColorBrush(Renk), kalin)
            { LineCap = PenLineCap.Round };
            double bas = -Math.PI / 2;                 // tepeden başla
            double bit = bas + oran * 2 * Math.PI;
            var fig = new PathFigure
            {
                StartPoint = new Point(cx + r * Math.Cos(bas), cy + r * Math.Sin(bas)),
                IsClosed = false,
            };
            fig.Segments!.Add(new ArcSegment
            {
                Point = new Point(cx + r * Math.Cos(bit), cy + r * Math.Sin(bit)),
                Size = new Size(r, r),
                RotationAngle = 0,
                IsLargeArc = oran > 0.5,
                SweepDirection = SweepDirection.Clockwise,
            });
            var geo = new PathGeometry();
            geo.Figures!.Add(fig);
            ctx.DrawGeometry(null, pen, geo);
        }

        // merkez metin (değer + etiket)
        var deger = new FormattedText($"%{Yuzde:0}", CultureInfo.InvariantCulture,
            FlowDirection.LeftToRight, new Typeface("Inter", weight: FontWeight.Bold),
            r * 0.42, new SolidColorBrush(Renk));
        ctx.DrawText(deger, new Point(cx - deger.Width / 2, cy - deger.Height / 2 - r * 0.12));

        if (!string.IsNullOrEmpty(Etiket))
        {
            var et = new FormattedText(Etiket, CultureInfo.InvariantCulture,
                FlowDirection.LeftToRight, Yazi, r * 0.24, new SolidColorBrush(CSoluk));
            ctx.DrawText(et, new Point(cx - et.Width / 2, cy + r * 0.18));
        }
    }
}
