import SwiftUI

/// CSS timing functions used by the intro keyframes.
nonisolated enum Ease {
    static let skj = (0.2, 0.7, 0.2, 1.0)       // cubic-bezier(.2,.7,.2,1)
    static let out = (0.0, 0.0, 0.58, 1.0)
    static let `in` = (0.42, 0.0, 1.0, 1.0)
    static let ease = (0.25, 0.1, 0.25, 1.0)

    static func bezier(_ c: (Double, Double, Double, Double), _ x: Double) -> Double {
        let (x1, y1, x2, y2) = c
        func bx(_ t: Double) -> Double { 3 * (1 - t) * (1 - t) * t * x1 + 3 * (1 - t) * t * t * x2 + t * t * t }
        func by(_ t: Double) -> Double { 3 * (1 - t) * (1 - t) * t * y1 + 3 * (1 - t) * t * t * y2 + t * t * t }
        var lo = 0.0, hi = 1.0, t = x
        for _ in 0..<24 { t = (lo + hi) / 2; if bx(t) < x { lo = t } else { hi = t } }
        return by(t)
    }

    /// Progress 0…1 of an animation with `fill-mode: both`.
    static func p(_ time: Double, dur: Double, delay: Double, _ c: (Double, Double, Double, Double)? = skj) -> Double {
        let x = max(0, min(1, (time - delay) / dur))
        guard let c else { return x }
        return bezier(c, x)
    }

    /// Piecewise-linear keyframes (offset, value).
    static func keys(_ x: Double, _ k: [(Double, Double)]) -> Double {
        guard let first = k.first else { return 0 }
        if x <= first.0 { return first.1 }
        for i in 1..<k.count where x <= k[i].0 {
            let a = k[i - 1], b = k[i]
            return a.1 + (b.1 - a.1) * (x - a.0) / (b.0 - a.0)
        }
        return k.last!.1
    }
}

/// Intro (introView() in the design): mountains, lightning, flash and the SKJOLD word mark. 4.7 s.
struct IntroView: View {
    @Environment(AppModel.self) private var m
    @State private var start = Date()

    var body: some View {
        TimelineView(.animation) { tl in
            let t = tl.date.timeIntervalSince(start)
            let out = Ease.p(t, dur: 0.6, delay: 4.05, Ease.in)
            GeometryReader { g in
                ZStack {
                    Color(hex: 0x060607)
                    landscape(t, g.size)
                    flash(t)
                    sky(t, g.size)
                    mark(t)
                }
                .frame(width: g.size.width, height: g.size.height)
            }
            .ignoresSafeArea()   // GeometryReader får hele skjermen – ellers ble status- og hjem-feltet stående i bakgrunnsfargen
            .opacity(1 - out)
            .scaleEffect(1 + 0.04 * out)
        }
        .ignoresSafeArea()
        .contentShape(Rectangle())
        .onTapGesture { withAnimation(.easeIn(duration: 0.3)) { m.intro = false } }
    }

    // SVG 350×760, preserveAspectRatio xMidYMax slice
    @ViewBuilder private func landscape(_ t: Double, _ size: CGSize) -> some View {
        let s = max(size.width / 350, size.height / 760)
        let ox = (size.width - 350 * s) / 2, oy = size.height - 760 * s
        let r1 = Ease.p(t, dur: 1.4, delay: 0.05, Ease.out), r2 = Ease.p(t, dur: 1.4, delay: 0.2, Ease.out)
        let f1 = Ease.p(t, dur: 1.2, delay: 0.3, Ease.out), f2 = Ease.p(t, dur: 1.2, delay: 0.4, Ease.out)
        ZStack(alignment: .topLeading) {
            SVGShape("M0 560 L40 500 L70 520 L120 430 L150 470 L190 400 L235 470 L262 445 L300 500 L350 470 L350 600 L0 600 Z", viewBoxW: 350, viewBoxH: 760)
                .fill(Color(hex: 0x10161b)).opacity(r1).offset(y: 24 * (1 - r1) * s)
            SVGShape("M0 600 L30 560 L75 585 L110 520 L150 590 L0 600 Z M200 600 L245 535 L280 570 L320 525 L350 555 L350 600 Z", viewBoxW: 350, viewBoxH: 760)
                .fill(Color(hex: 0x0b0f12)).opacity(r2).offset(y: 24 * (1 - r2) * s)
            LinearGradient(colors: [Color(hex: 0x16232a), Color(hex: 0x060607)], startPoint: .top, endPoint: .bottom)
                .frame(width: 350 * s, height: 160 * s)
                .offset(y: 600 * s + 6 * (1 - f1) * s)
                .opacity(f1)
            SVGShape("M0 600 L30 640 L75 615 L110 680 L150 610 L0 600 Z M200 600 L245 665 L280 630 L320 675 L350 645 L350 600 Z", viewBoxW: 350, viewBoxH: 760)
                .fill(Color(hex: 0x0b0f12)).opacity(0.45 * f2).offset(y: 6 * (1 - f2) * s)
            bolt("M196 0 L184 92 L200 98 L172 196 L190 202 L160 300", width: 2.4, t: t, dur: 0.9, delay: 0.6, s: s, wide: true)
            bolt("M184 92 L160 140 L166 150 L150 190", width: 1.2, t: t, dur: 0.8, delay: 0.68, s: s, wide: false)
        }
        .frame(width: 350 * s, height: 760 * s, alignment: .topLeading)
        .offset(x: ox, y: oy)
        .frame(width: size.width, height: size.height, alignment: .topLeading)
    }

    @ViewBuilder private func bolt(_ d: String, width: CGFloat, t: Double, dur: Double, delay: Double, s: CGFloat, wide: Bool) -> some View {
        let x = Ease.p(t, dur: dur, delay: delay, nil)
        let drawn = t < delay ? 0 : Ease.keys(x, [(0, 0), (0.35, 1), (1, 1)])
        let op = t < delay ? 0 : Ease.keys(x, [(0, 1), (0.35, 1), (0.55, 0.2), (0.62, 1), (1, 0)])
        SVGShape(d, viewBoxW: 350, viewBoxH: 760)
            .trim(from: 0, to: drawn)
            .stroke(Color(hex: 0xfdf3d6), style: StrokeStyle(lineWidth: width * s, lineJoin: .miter))
            .shadow(color: Color.accent2, radius: 3 * s)
            .shadow(color: wide ? Color.accent2.opacity(0.7) : .clear, radius: 8 * s)
            .opacity(op)
    }

    private func flash(_ t: Double) -> some View {
        let x = Ease.p(t, dur: 0.9, delay: 0.78, nil)
        let op = t < 0.78 ? 0 : Ease.keys(x, [(0, 0), (0.12, 0.75), (0.3, 0.1), (0.38, 0.5), (1, 0)])
        return GeometryReader { g in
            EllipticalGradient(stops: [.init(color: Color(hex: 0xfff6dc), location: 0),
                                       .init(color: Color.accent2.opacity(0.4), location: 0.6),
                                       .init(color: .clear, location: 1)],
                               center: UnitPoint(x: 0.5, y: 0.3), startRadiusFraction: 0, endRadiusFraction: 0.5)
                .frame(width: g.size.width * 1.4, height: g.size.height)
                .offset(x: -g.size.width * 0.2)
        }
        .opacity(op)
        .allowsHitTesting(false)
    }

    private func sky(_ t: Double, _ size: CGSize) -> some View {
        let p = Ease.p(t, dur: 3.6, delay: 0.1, Ease.out)
        let w = size.width * 1.6, h = size.height * 0.38
        return ZStack {
            RadialGradient(colors: [Color(.sRGB, red: 70 / 255, green: 160 / 255, blue: 140 / 255, opacity: 0.35), .clear],
                           center: UnitPoint(x: 0.4, y: 0.6), startRadius: 0, endRadius: w * 0.42)
            RadialGradient(colors: [Color(.sRGB, red: 90 / 255, green: 110 / 255, blue: 170 / 255, opacity: 0.25), .clear],
                           center: UnitPoint(x: 0.7, y: 0.4), startRadius: 0, endRadius: w * 0.28)
        }
        .frame(width: w, height: h)
        .blur(radius: 30)
        .opacity(0.55 * p)
        .offset(x: w * (-0.08 + 0.12 * p))
        .frame(width: size.width, height: size.height, alignment: .top)
        .offset(y: size.height * 0.06)
        .allowsHitTesting(false)
    }

    @ViewBuilder private func mark(_ t: Double) -> some View {
        let glow = Ease.p(t, dur: 1.8, delay: 0.85, Ease.out)
        let word = Ease.p(t, dur: 1.3, delay: 1.6)
        let line = Ease.p(t, dur: 1, delay: 2.4)
        let shake = Ease.p(t, dur: 0.35, delay: 0.82, nil)
        let sx = t < 0.82 ? 0 : Ease.keys(shake, [(0, 0), (0.2, -2), (0.4, 2), (0.6, -1), (1, 0)])
        let sy = t < 0.82 ? 0 : Ease.keys(shake, [(0, 0), (0.2, 1), (0.4, -1), (0.6, 0), (1, 0)])
        ZStack {
            Circle()
                .fill(RadialGradient(colors: [Color.accent.opacity(0.22), .clear], center: .center, startRadius: 0, endRadius: 210))
                .frame(width: 420, height: 420)
                .scaleEffect(0.8 + 0.2 * glow)
                .opacity(glow)
                .offset(y: -40)
            VStack(spacing: 0) {
                HStack(alignment: .bottom, spacing: 6) {
                    ForEach(Array([26.0, 40, 56, 40, 26].enumerated()), id: \.offset) { i, h in
                        let d = 1.05 + Double(i) * 0.1
                        let b = Ease.p(t, dur: 0.5, delay: d)
                        let bx = Ease.p(t, dur: 0.5, delay: d, nil)
                        let ink = Ease.p(t, dur: 1.6, delay: d, Ease.ease)
                        let toInk = max(0, (ink - 0.7) / 0.3)
                        RoundedRectangle(cornerRadius: 4)
                            .fill(Color.accent.mix(with: .ink, by: toInk))
                            .frame(width: 7, height: h)
                            .scaleEffect(x: 1, y: b, anchor: .bottom)
                            .opacity(t < d ? 0 : min(1, bx / 0.6))
                    }
                }
                .frame(height: 56)
                .offset(x: sx, y: sy)
                .padding(.top, -80)
                Text("SKJOLD")
                    .font(.sora(30, .semibold))
                    .tracking(30 * (0.9 - 0.66 * word))
                    .foregroundStyle(Color.ink)
                    .padding(.leading, 30 * 0.24)
                    .blur(radius: 8 * (1 - word))
                    .opacity(word)
                    .padding(.top, 30)
                LinearGradient(colors: [.clear, .accent, .clear], startPoint: .leading, endPoint: .trailing)
                    .frame(width: 150, height: 1)
                    .scaleEffect(x: line, y: 1)
                    .opacity(line)
                    .padding(.top, 18)
            }
        }
    }
}
