import SwiftUI

/// Lyd: EQ profile per source, an interactive EQ curve, preset tiles, tone controls and loudness.
struct SoundView: View {
    @Environment(AppModel.self) private var m
    @State private var band = 2

    var body: some View {
        let prof = m.prof
        sourcePicker
        eqCard(prof)
        presetStrip(prof)
        toneCard(prof)
    }

    // MARK: Source

    private var sourcePicker: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                SKMonoLabel(text: "LYDPROFIL FOR")
                Spacer()
                HStack(spacing: 5) {
                    Circle().fill(Color.ok).frame(width: 6, height: 6)
                    Text(activeName(m.actSrc) + " spiller nå").sora(11, .regular, .muted)
                }
            }
            EdgeScroll(spacing: 8) {
                ForEach(SK.eqSources, id: \.0) { k, label in
                    let on = m.eqEditing == k
                    Button {
                        guard !on else { return }
                        Haptics.tick()
                        withAnimation(.snappy) { m.eqSrc = k }
                    } label: {
                        HStack(spacing: 8) {
                            SourceGlyph(label: label, size: 24)
                            Text(label).sora(13, on ? .semibold : .regular, on ? .accent2 : .ink).fixedSize()
                            if m.actSrc == k { Circle().fill(Color.ok).frame(width: 6, height: 6) }
                        }
                        .padding(.leading, 6).padding(.trailing, 14)
                        .frame(height: 40)
                        .background(Capsule().fill(on ? Color.selBg : .card))
                        .skCapsuleBorder(on ? .accent : .line2)
                    }
                    .plain()
                }
            }
            if m.eqEditing != m.actSrc {
                Text("Du redigerer \(activeName(m.eqEditing)). Profilen brukes neste gang den inngangen spiller.")
                    .sora(11, .regular, .muted).fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private func activeName(_ k: String) -> String { SK.eqSources.first { $0.0 == k }?.1 ?? "" }

    // MARK: EQ

    private func eqCard(_ prof: EQProfile) -> some View {
        let presetName = prof.preset >= 0 && prof.preset < SK.eqPresets.count ? SK.eqPresets[prof.preset].0 : "Egendefinert"
        return VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .firstTextBaseline) {
                Text("Equalizer").sora(17, .semibold)
                Text(presetName).mono(10, .accent2, em: 0.08)
                    .padding(.horizontal, 8).frame(height: 20)
                    .background(Capsule().fill(Color.selBg2))
                Spacer()
                if prof.eq.contains(where: { $0 != 0 }) {
                    SKLinkButton(title: "Nullstill") {
                        Haptics.bump()
                        withAnimation(.spring(response: 0.4, dampingFraction: 0.8)) { m.setProf { $0.preset = 0; $0.eq = [0, 0, 0, 0, 0] } }
                    }
                }
            }
            EQGraph(eq: prof.eq, selected: $band) { i, v in m.setProf { $0.eq[i] = v; $0.preset = -1 } }
                .frame(height: 190)
            // band labels under the graph, tap to select
            HStack(spacing: 0) {
                ForEach(0..<5, id: \.self) { i in
                    Button { Haptics.tick(); withAnimation(.snappy) { band = i } } label: {
                        VStack(spacing: 2) {
                            Text(SK.eqBands[i]).mono(10, i == band ? .accent2 : .muted)
                            Text(SK.eqNames[i]).sora(10, i == band ? .semibold : .regular, i == band ? .ink : .ink2).lineLimit(1).fixedSize()
                        }
                        .frame(maxWidth: .infinity)
                    }
                    .plain()
                }
            }
            // what the selected band does (v4: «HVA BÅNDENE GJØR»)
            SKMonoLabel(text: "HVA BÅNDENE GJØR")
            HStack(alignment: .top, spacing: 12) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(dB(prof.eq[band])).font(.plexMono(20, .medium)).foregroundStyle(Color.accent2)
                        .contentTransition(.numericText(value: Double(prof.eq[band])))
                    Text(SK.eqHz[band]).mono(10)
                }
                .frame(width: 70, alignment: .leading)
                VStack(alignment: .leading, spacing: 3) {
                    Text(SK.eqNames[band]).sora(13, .semibold)
                    Text(SK.eqDesc[band]).sora(12, .regular, .body, lineHeight: 1.4).fixedSize(horizontal: false, vertical: true)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .padding(12)
            .skBox(Color.bg.opacity(0.6), .line, radius: 12)
            .animation(.snappy, value: band)
        }
        .padding(16)
        .skBox(.card, .line, radius: 18)
    }

    private func dB(_ v: Int) -> String { (v > 0 ? "+" : v < 0 ? "−" : "") + "\(abs(v)) dB" }

    // MARK: Presets

    private func presetStrip(_ prof: EQProfile) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            SKMonoLabel(text: "FORHÅNDSINNSTILLINGER")
            EdgeScroll(spacing: 10) {
                ForEach(Array(SK.eqPresets.enumerated()), id: \.offset) { i, p in
                    let on = prof.preset == i
                    Button {
                        guard !on else { return }
                        Haptics.tick()
                        withAnimation(.spring(response: 0.45, dampingFraction: 0.8)) { m.setProf { $0.preset = i; $0.eq = p.1 } }
                    } label: {
                        VStack(alignment: .leading, spacing: 8) {
                            // exaggerated so the shape reads at thumbnail size
                            EQCurve(eq: p.1.map { max(-12, min(12, $0 * 2)) }).frame(height: 30)
                            Text(p.0).sora(12, on ? .semibold : .regular, on ? .accent2 : .ink)
                        }
                        .padding(10)
                        .frame(width: 96)
                        .background(RoundedRectangle(cornerRadius: 14, style: .continuous).fill(on ? Color.selBg : .card))
                        .skBorder(on ? .accent : .line, radius: 14)
                    }
                    .plain()
                }
            }
        }
    }

    // MARK: Tone

    private func toneCard(_ prof: EQProfile) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            SKMonoLabel(text: "TONE")
            VStack(spacing: 0) {
                toneRow("Bass", "bass", -6...6, NumFormat.dB, left: "", right: "")
                toneRow("Diskant", "treb", -6...6, NumFormat.dB, left: "", right: "").topLine(.line)
                toneRow("Balanse", "bal", -5...5, NumFormat.bal, left: "V", right: "H").topLine(.line)
                HStack(spacing: 12) {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Loudness").sora(14)
                        Text("Mer bass og diskant ved lavt volum").sora(11, .regular, .muted)
                    }
                    Spacer()
                    SKToggle(on: prof.loud) { Haptics.tick(); m.setProf { $0.loud.toggle() } }
                        .accessibilityLabel("Loudness")
                }
                .padding(.vertical, 14).padding(.horizontal, 16)
                .topLine(.line)
            }
            .skBox(.card, .line, radius: 18)
        }
    }

    private func toneRow(_ n: String, _ k: String, _ r: ClosedRange<Int>, _ f: NumFormat, left: String, right: String) -> some View {
        let v = m.sset[k] ?? 0
        return VStack(spacing: 10) {
            HStack {
                Text(n).sora(14)
                Spacer()
                Text(f.format(v)).mono(12, v == 0 ? .muted : .accent2)
            }
            HStack(spacing: 10) {
                if !left.isEmpty { Text(left).mono(10) }
                SKCenterSlider(value: Binding(get: { m.sset[k] ?? 0 }, set: { m.setS(k, $0) }), range: r)
                if !right.isEmpty { Text(right).mono(10) }
            }
        }
        .padding(.vertical, 14).padding(.horizontal, 16)
    }
}

// MARK: - Interactive EQ graph

/// Five draggable band nodes on a smooth curve with a dB grid. Drag anywhere: the nearest band follows the finger.
struct EQGraph: View {
    let eq: [Int]
    @Binding var selected: Int
    let onChange: (Int, Int) -> Void
    @State private var dragging = false

    private let pad: CGFloat = 16

    var body: some View {
        GeometryReader { g in
            let w = g.size.width, h = g.size.height
            let pts = (0..<5).map { CGPoint(x: x($0, w), y: y(eq[$0], h)) }
            ZStack(alignment: .topLeading) {
                grid(w, h)
                // selected band guide
                Rectangle().fill(Color.accent.opacity(dragging ? 0.25 : 0.12))
                    .frame(width: 1, height: h)
                    .offset(x: pts[selected].x)
                // area + line
                curve(pts, w, closeTo: h / 2)
                    .fill(LinearGradient(colors: [Color.accent.opacity(0.32), Color.accent.opacity(0.02)], startPoint: .top, endPoint: .bottom))
                curve(pts, w, closeTo: nil)
                    .stroke(Color.accent, style: StrokeStyle(lineWidth: 2.5, lineCap: .round, lineJoin: .round))
                    .shadow(color: Color.accent.opacity(0.5), radius: 6)
                // nodes
                ForEach(0..<5, id: \.self) { i in
                    let on = i == selected
                    Circle()
                        .fill(on ? Color.ink : Color.card)
                        .overlay(Circle().strokeBorder(Color.accent, lineWidth: on ? 3 : 2))
                        .frame(width: on ? 22 : 14, height: on ? 22 : 14)
                        .shadow(color: .black.opacity(0.4), radius: 3, y: 1)
                        .position(pts[i])
                }
                // value bubble while dragging
                if dragging {
                    let v = eq[selected]
                    Text((v > 0 ? "+" : v < 0 ? "−" : "") + "\(abs(v)) dB")
                        .mono(11, .bg, weight: .medium)
                        .padding(.horizontal, 8).frame(height: 22)
                        .background(Capsule().fill(Color.accent2))
                        .position(x: min(max(pts[selected].x, 30), w - 30), y: pts[selected].y > 50 ? pts[selected].y - 34 : pts[selected].y + 34)
                        .transition(.opacity.combined(with: .scale(scale: 0.8)))
                }
            }
            .contentShape(Rectangle())
            .gesture(
                DragGesture(minimumDistance: 0)
                    .onChanged { d in
                        if !dragging {
                            let i = nearest(d.startLocation.x, w)
                            if i != selected { Haptics.tick() }
                            withAnimation(.snappy(duration: 0.15)) { selected = i; dragging = true }
                        }
                        let raw = (h / 2 - d.location.y) / (h / 2 - pad) * 12
                        let v = max(-12, min(12, Int(raw.rounded())))
                        if v != eq[selected] {
                            if v == 0 || abs(v) == 12 { Haptics.bump() } else { Haptics.tick() }
                            onChange(selected, v)
                        }
                    }
                    .onEnded { _ in withAnimation(.snappy) { dragging = false } }
            )
            .animation(.spring(response: 0.35, dampingFraction: 0.8), value: eq)
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Equalizer, \(SK.eqNames[selected])")
        .accessibilityValue("\(eq[selected]) dB")
        .accessibilityAdjustableAction { dir in
            let v = eq[selected] + (dir == .increment ? 1 : -1)
            if (-12...12).contains(v) { onChange(selected, v) }
        }
    }

    private func x(_ i: Int, _ w: CGFloat) -> CGFloat { w * (CGFloat(i) + 0.5) / 5 }
    private func y(_ v: Int, _ h: CGFloat) -> CGFloat { h / 2 - CGFloat(v) * (h / 2 - pad) / 12 }
    private func nearest(_ px: CGFloat, _ w: CGFloat) -> Int { max(0, min(4, Int(px / (w / 5)))) }

    private func grid(_ w: CGFloat, _ h: CGFloat) -> some View {
        ZStack(alignment: .topLeading) {
            ForEach([12, 6, 0, -6, -12], id: \.self) { v in
                let yy = y(v, h)
                Path { p in p.move(to: CGPoint(x: 0, y: yy)); p.addLine(to: CGPoint(x: w, y: yy)) }
                    .stroke(Color.ink.opacity(v == 0 ? 0.16 : 0.06), style: StrokeStyle(lineWidth: 1, dash: v == 0 ? [] : [3, 4]))
                Text(v > 0 ? "+\(v)" : "\(v)").mono(8, Color.muted.opacity(0.7))
                    .position(x: 10, y: yy - 7)
            }
        }
    }

    /// Smooth curve through the nodes, flat to both edges; optionally closed down to the 0 dB line for the area fill.
    private func curve(_ pts: [CGPoint], _ w: CGFloat, closeTo base: CGFloat?) -> Path {
        var p = Path()
        p.move(to: CGPoint(x: 0, y: pts[0].y))
        p.addLine(to: pts[0])
        for i in 0..<4 {
            let mx = (pts[i].x + pts[i + 1].x) / 2
            p.addCurve(to: pts[i + 1], control1: CGPoint(x: mx, y: pts[i].y), control2: CGPoint(x: mx, y: pts[i + 1].y))
        }
        p.addLine(to: CGPoint(x: w, y: pts[4].y))
        if let base {
            p.addLine(to: CGPoint(x: w, y: base))
            p.addLine(to: CGPoint(x: 0, y: base))
            p.closeSubpath()
        }
        return p
    }
}

/// Small EQ curve, viewBox 0 0 300 90 (curve() in the design). Used for preset previews.
struct EQCurve: View {
    let eq: [Int]

    var body: some View {
        let (line, area) = Self.paths(eq)
        ZStack {
            SVGShape("M0 45 L300 45", viewBoxW: 300, viewBoxH: 90).stroke(Color(hex: 0x2a2a28), lineWidth: 1)
            SVGShape(area, viewBoxW: 300, viewBoxH: 90).fill(Color.accent.opacity(0.18))
            SVGShape(line, viewBoxW: 300, viewBoxH: 90).stroke(Color.accent, lineWidth: 1.5)
        }
    }

    static func paths(_ eq: [Int]) -> (String, String) {
        let xs: [Double] = [15, 82.5, 150, 217.5, 285]
        let ys = eq.map { 45 - Double($0) * 3.2 }
        func f(_ v: Double) -> String { String(format: "%.1f", v) }
        var d = "M0 \(f(ys[0])) L\(xs[0]) \(f(ys[0]))"
        for i in 0..<4 {
            let mx = (xs[i] + xs[i + 1]) / 2
            d += " C\(mx) \(f(ys[i])) \(mx) \(f(ys[i + 1])) \(xs[i + 1]) \(f(ys[i + 1]))"
        }
        d += " L300 \(f(ys[4]))"
        return (d, d + " L300 45 L0 45 Z")
    }
}

// MARK: - Center slider

/// Slider for ± values: fills from the centre, detent at 0.
struct SKCenterSlider: View {
    @Binding var value: Int
    let range: ClosedRange<Int>

    var body: some View {
        GeometryReader { g in
            let w = g.size.width, h = g.size.height, thumb: CGFloat = 22
            let span = CGFloat(range.upperBound - range.lowerBound)
            let px = { (v: Int) in thumb / 2 + (w - thumb) * CGFloat(v - range.lowerBound) / span }
            let cx = px(0), vx = px(value)
            ZStack(alignment: .topLeading) {
                Capsule().fill(Color(hex: 0x2a2a2c)).frame(width: w, height: 6).position(x: w / 2, y: h / 2)
                // ticks
                ForEach(Array(range), id: \.self) { t in
                    Rectangle().fill(Color.ink.opacity(t == 0 ? 0.35 : 0.1))
                        .frame(width: t == 0 ? 2 : 1, height: t == 0 ? 14 : 8)
                        .position(x: px(t), y: h / 2)
                }
                Capsule().fill(Color.accent)
                    .frame(width: abs(vx - cx), height: 6)
                    .position(x: (vx + cx) / 2, y: h / 2)
                Circle().fill(Color.ink)
                    .overlay(Circle().strokeBorder(value == 0 ? Color.line2 : Color.accent, lineWidth: 2))
                    .frame(width: thumb, height: thumb)
                    .shadow(color: .black.opacity(0.35), radius: 3, y: 1)
                    .position(x: vx, y: h / 2)
            }
            .contentShape(Rectangle())
            .gesture(DragGesture(minimumDistance: 0).onChanged { d in
                let f = max(0, min(1, (d.location.x - thumb / 2) / (w - thumb)))
                let v = range.lowerBound + Int((f * span).rounded())
                if v != value {
                    if v == 0 || v == range.lowerBound || v == range.upperBound { Haptics.bump() } else { Haptics.tick() }
                    value = v
                }
            })
            .animation(.snappy(duration: 0.12), value: value)
        }
        .frame(height: 28)
        .accessibilityElement()
        .accessibilityValue("\(value)")
        .accessibilityAdjustableAction { dir in
            let v = value + (dir == .increment ? 1 : -1)
            if range.contains(v) { value = v }
        }
    }
}
