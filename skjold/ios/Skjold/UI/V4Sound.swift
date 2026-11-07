import SwiftUI

/// Lyd (tLyd): kildechips, EQ-kort med kurve og bånd, profiler og lydbilde.
struct V4SoundTab: View {
    @Environment(AppModel.self) private var m
    @State private var band = 3
    @State private var dragging = false
    @State private var cmp: [Int]? = nil
    @AppStorage("skjold-v4-night") private var night = false
    @AppStorage("skjold-v4-hpf") private var hpf = false

    private static let XS: [CGFloat] = [0.08, 0.29, 0.5, 0.71, 0.92]
    private static let H: CGFloat = 196, PAD: CGFloat = 8
    private static let grid: [[Double]] = [[8, 0.05], [53, 0.04], [98, 0.14], [143, 0.04], [188, 0.05]]
    private static let desc = ["Den dype bassen du kjenner mer enn hører. Skru ned hvis små høyttalere dundrer.",
                               "Fylde og varme. For mye gjør lyden grøtete.",
                               "Der stemmer og instrumenter bor. Senk for en mykere, mer avslappet lyd.",
                               "Gjør vokal og detaljer tydeligere. For mye blir skarpt.",
                               "Cymbaler, glans og romfølelse."]
    private static let bn: [(String, String, String)] = [("Dypbass", "60 Hz", "60"), ("Bass", "250 Hz", "250"), ("Mellomtone", "1 kHz", "1k"),
                                                         ("Presens", "4 kHz", "4k"), ("Luft", "12 kHz", "12k")]

    var body: some View {
        HStack(spacing: 12) {
            V4Title(text: "Lyd")
            Spacer(minLength: 0)
            HStack(spacing: 8) {
                Circle().fill(V4.green).frame(width: 6, height: 6)
                Text(m.v4GroupName).sora(13).lineLimit(1)
            }
            .padding(.horizontal, 14).frame(height: 36)
            .v4DarkPill(Capsule())
        }
        srcChips
        eqCard
        profiles
        soundImage
    }

    // MARK: Kilder

    private var srcChips: some View {
        V4Shelf(spacing: 8) {
            ForEach(AppModel.v4EqSrcs, id: \.1) { s in
                let on = m.eqEditing == s.1
                Button { Haptics.tick(); m.eqSrc = s.1 } label: {
                    HStack(spacing: 7) {
                        Text(s.0).sora(13, .regular, on ? V4.gold : V4.ink)
                        if m.actSrc == s.1 { Circle().fill(V4.green).frame(width: 6, height: 6) }
                    }
                    .padding(.horizontal, 14).frame(height: 36)
                    .background(Capsule().fill(on ? V4.selBg : V4.card))
                    .overlay(Capsule().strokeBorder(on ? V4.goldDark : V4.line2, lineWidth: 1))
                }
                .plain()
            }
        }
    }

    // MARK: EQ-kort

    private var eqOn: Bool { UserDefaults.standard.array(forKey: offKey) == nil }
    private var offKey: String { "skjold-eqoff-" + m.eqEditing }
    private var live: [Int] { cmp != nil || !eqOn ? [0, 0, 0, 0, 0] : m.prof.eq }
    private var presetName: String {
        let p = m.prof.preset
        return p >= 0 && p < SK.eqPresets.count ? SK.eqPresets[p].0 : "Egendefinert"
    }
    private var srcLabel: String { AppModel.v4EqSrcs.first { $0.1 == m.eqEditing }?.0 ?? "" }

    private var eqCard: some View {
        VStack(spacing: 12) {
            HStack(spacing: 10) {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Equalizer").sora(15, .semibold)
                    Text((eqOn ? presetName.uppercased() : "AV") + " · " + srcLabel.uppercased()).mono(10, V4.muted, em: 0.06)
                }
                Spacer(minLength: 0)
                V4Switch(on: eqOn, label: "Equalizer av/på") { toggleEq() }
            }
            graph
            bandTabs
            bandInfo
            HStack(spacing: 8) {
                compareButton
                Button { Haptics.tick(); m.setProf { $0.eq = [0, 0, 0, 0, 0]; $0.preset = 0 } } label: {
                    Text("Nullstill").sora(13).padding(.horizontal, 16).frame(height: 40)
                        .overlay(Capsule().strokeBorder(V4.line2, lineWidth: 1))
                }
                .plain()
            }
        }
        .padding(.horizontal, 16).padding(.top, 16).padding(.bottom, 14)
        .background(RoundedRectangle(cornerRadius: 26, style: .continuous)
            .fill(LinearGradient(colors: [Color(hex: 0x17171a), Color(hex: 0x111113)], startPoint: .top, endPoint: .bottom)))
        .overlay(RoundedRectangle(cornerRadius: 26, style: .continuous).strokeBorder(V4.line, lineWidth: 1))
    }

    private func yOf(_ v: CGFloat) -> CGFloat { Self.PAD + (12 - v) / 24 * (Self.H - 2 * Self.PAD) }

    private func curvePoints(_ eq: [Int], n: Int) -> [CGPoint] {
        (0...n).map { k in
            let x = CGFloat(k) / CGFloat(n)
            var v: CGFloat = 0
            for (i, g) in eq.enumerated() where i < 5 {
                let d = (x - Self.XS[i]) / 0.13
                v += CGFloat(g) * CGFloat(exp(-Double(d * d)))
            }
            return CGPoint(x: x, y: max(-12, min(12, v)))
        }
    }

    private var graph: some View {
        GeometryReader { g in
            let w = g.size.width
            let pts = curvePoints(live, n: 60)
            ZStack(alignment: .topLeading) {
                gridLines(w)
                curveFill(pts, w)
                curveLine(pts, w)
                ForEach(0..<5, id: \.self) { i in dot(i, w) }
            }
            .contentShape(Rectangle())
            .gesture(DragGesture(minimumDistance: 0)
                .onChanged { v in eqDrag(v.location, w: w) }
                .onEnded { _ in dragging = false; Haptics.sliderRelease() })
        }
        .frame(height: Self.H)
        .padding(.horizontal, -4)
        .opacity(eqOn ? 1 : 0.45)
        .animation(V4.fade, value: eqOn)
    }

    private func gridLines(_ w: CGFloat) -> some View {
        ZStack(alignment: .topLeading) {
            ForEach(Self.grid, id: \.self) { row in
                Rectangle().fill(Color.white.opacity(row[1])).frame(width: w, height: 1).offset(y: CGFloat(row[0]))
            }
            Text("+12").mono(9, V4.dim).offset(x: w - 22, y: 10)
            Text("0").mono(9, V4.dim).offset(x: w - 10, y: 100)
            Text("−12").mono(9, V4.dim).offset(x: w - 22, y: 170)
            Rectangle().fill(V4.gold.opacity(0.22)).frame(width: 1, height: Self.H - 16)
                .offset(x: Self.XS[band] * w, y: 8)
        }
    }

    private func curvePath(_ pts: [CGPoint], _ w: CGFloat) -> Path {
        var p = Path()
        for (i, pt) in pts.enumerated() {
            let q = CGPoint(x: pt.x * w, y: yOf(pt.y))
            if i == 0 { p.move(to: q) } else { p.addLine(to: q) }
        }
        return p
    }

    private func curveFill(_ pts: [CGPoint], _ w: CGFloat) -> some View {
        var p = curvePath(pts, w)
        p.addLine(to: CGPoint(x: w, y: yOf(0)))
        p.addLine(to: CGPoint(x: 0, y: yOf(0)))
        p.closeSubpath()
        return p.fill(LinearGradient(colors: [V4.goldDark.opacity(0.38), V4.goldDark.opacity(0)], startPoint: .top, endPoint: .bottom))
    }

    private func curveLine(_ pts: [CGPoint], _ w: CGFloat) -> some View {
        curvePath(pts, w)
            .stroke(V4.gold, style: StrokeStyle(lineWidth: 2.2, lineJoin: .round))
            .shadow(color: V4.gold.opacity(0.5), radius: 6)
    }

    private func dot(_ i: Int, _ w: CGFloat) -> some View {
        let sel = band == i
        let sz: CGFloat = sel ? 22 : 14
        return Circle()
            .fill(sel ? V4.gold : V4.card)
            .overlay(Circle().strokeBorder(V4.gold, lineWidth: 2))
            .frame(width: sz, height: sz)
            .background(Circle().fill(V4.gold.opacity(sel ? 0.18 : 0)).frame(width: sz + 12, height: sz + 12))
            .shadow(color: V4.gold.opacity(sel ? 0.6 : 0), radius: 8)
            .position(x: Self.XS[i] * w, y: yOf(CGFloat(live[i])))
            .animation(V4.eqDot, value: sel)
            .allowsHitTesting(false)
    }

    private func eqDrag(_ p: CGPoint, w: CGFloat) {
        if !dragging {
            dragging = true
            Haptics.prepareSlider()
            let x = p.x / max(1, w)
            var best: CGFloat = 9, idx = band
            for (j, xx) in Self.XS.enumerated() where abs(xx - x) < best { best = abs(xx - x); idx = j }
            if idx != band { Haptics.tick() }
            band = idx
        }
        let v = 12 - (p.y - Self.PAD) / (Self.H - 2 * Self.PAD) * 24
        setBand(band, Int(v.rounded()))
    }

    private func setBand(_ i: Int, _ v: Int) {
        let c = max(-12, min(12, v))
        if !eqOn { UserDefaults.standard.removeObject(forKey: offKey) }
        guard m.prof.eq.count == 5, m.prof.eq[i] != c || m.prof.preset != -1 else { return }
        Haptics.sliderStep(from: m.prof.eq[i], to: c, min: -12, max: 12)
        m.setProf { p in
            if p.eq.count != 5 { p.eq = [0, 0, 0, 0, 0] }
            p.eq[i] = c; p.preset = -1
        }
        band = i
    }

    private var bandTabs: some View {
        HStack(spacing: 4) {
            ForEach(0..<5, id: \.self) { i in
                let v = m.prof.eq.count == 5 ? m.prof.eq[i] : 0
                Button { Haptics.tick(); band = i } label: {
                    VStack(spacing: 2) {
                        Text((v > 0 ? "+" : "") + "\(v)").mono(12, v != 0 ? V4.gold : V4.muted)
                        Text(Self.bn[i].2).mono(9, V4.muted)
                    }
                    .frame(maxWidth: .infinity).frame(height: 46)
                    .background(RoundedRectangle(cornerRadius: 12, style: .continuous).fill(band == i ? V4.gold.opacity(0.12) : .clear))
                }
                .plain()
            }
        }
        .padding(.horizontal, -4)
    }

    private var bandInfo: some View {
        let cur = m.prof.eq.count == 5 ? m.prof.eq[band] : 0
        return HStack(spacing: 12) {
            VStack(alignment: .leading, spacing: 3) {
                HStack(alignment: .firstTextBaseline, spacing: 4) {
                    Text(Self.bn[band].0).sora(14, .semibold)
                    Text(Self.bn[band].1).mono(11, V4.muted)
                }
                Text(Self.desc[band]).sora(12, .regular, V4.body, lineHeight: 1.4).fixedSize(horizontal: false, vertical: true)
                    .id(band).transition(.opacity)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .animation(V4.fade, value: band)
            HStack(spacing: 6) {
                stepButton("−", "Senk") { setBand(band, cur - 1) }
                stepButton("+", "Øk") { setBand(band, cur + 1) }
            }
        }
        .padding(.vertical, 12).padding(.leading, 14).padding(.trailing, 12)
        .background(RoundedRectangle(cornerRadius: 16, style: .continuous).fill(Color.white.opacity(0.04)))
    }

    private func stepButton(_ s: String, _ label: String, _ act: @escaping () -> Void) -> some View {
        Button { Haptics.tick(); act() } label: {
            Text(s).sora(18).frame(width: 36, height: 36).background(Circle().fill(V4.ink.opacity(0.1)))
        }
        .plain()
        .accessibilityLabel(label)
    }

    private var compareButton: some View {
        let on = cmp != nil
        return Text(on ? "Uten EQ – slipp for å høre med" : "Hold for å sammenligne")
            .sora(13, .regular, on ? V4.gold : V4.ink)
            .frame(maxWidth: .infinity).frame(height: 40)
            .background(Capsule().fill(on ? V4.selBg : .clear))
            .overlay(Capsule().strokeBorder(on ? V4.goldDark : V4.line2, lineWidth: 1))
            .contentShape(Capsule())
            .gesture(DragGesture(minimumDistance: 0)
                .onChanged { _ in
                    guard cmp == nil else { return }
                    Haptics.tap()
                    let saved = m.prof.eq
                    cmp = saved
                    m.setProf { $0.eq = [0, 0, 0, 0, 0] }
                }
                .onEnded { _ in
                    guard let saved = cmp else { return }
                    cmp = nil
                    m.setProf { $0.eq = saved }
                })
            .accessibilityLabel("Hold for å sammenligne")
    }

    private func toggleEq() {
        if eqOn {
            let p = m.prof
            UserDefaults.standard.set([p.preset] + p.eq, forKey: offKey)
            m.setProf { $0.eq = [0, 0, 0, 0, 0] }
        } else {
            let a = (UserDefaults.standard.array(forKey: offKey) as? [Int]) ?? [0, 0, 0, 0, 0, 0]
            UserDefaults.standard.removeObject(forKey: offKey)
            if a.count == 6 { m.setProf { $0.preset = a[0]; $0.eq = Array(a[1...]) } }
        }
    }

    // MARK: Profiler (fliser 104)

    private var profiles: some View {
        VStack(alignment: .leading, spacing: 10) {
            V4Kicker(text: "PROFILER")
            V4Shelf(spacing: 10) {
                ForEach(Array(SK.eqPresets.enumerated()), id: \.offset) { i, p in
                    profileTile(p.0, p.1, on: eqOn && m.prof.preset == i) {
                        UserDefaults.standard.removeObject(forKey: offKey)
                        Haptics.thump()
                        m.setProf { $0.preset = i; $0.eq = p.1 }
                    }
                }
                profileTile("Egendefinert", m.prof.eq, on: eqOn && m.prof.preset < 0) {}
            }
        }
    }

    private func profileTile(_ n: String, _ eq: [Int], on: Bool, pick: @escaping () -> Void) -> some View {
        let fg = on ? V4.gold : V4.ink2
        return Button { Haptics.tick(); pick() } label: {
            VStack(alignment: .leading, spacing: 8) {
                ZStack {
                    Path { p in p.move(to: CGPoint(x: 0, y: 15)); p.addLine(to: CGPoint(x: 82, y: 15)) }
                        .stroke(Color.white.opacity(0.08), lineWidth: 1)
                    miniCurve(eq).stroke(fg, style: StrokeStyle(lineWidth: 2, lineJoin: .round))
                }
                .frame(width: 82, height: 30)
                Text(n).sora(13, .regular, fg).lineLimit(1).minimumScaleFactor(0.8)
            }
            .padding(10)
            .frame(width: 104, alignment: .leading)
            .background(RoundedRectangle(cornerRadius: 16, style: .continuous).fill(on ? V4.selBg : V4.card))
            .overlay(RoundedRectangle(cornerRadius: 16, style: .continuous).strokeBorder(on ? V4.goldDark : V4.line, lineWidth: 1))
        }
        .plain()
    }

    /// Mini-kurve i viewBox 100 × 36 skalert til 82 × 30.
    private func miniCurve(_ eq: [Int]) -> Path {
        let pts = curvePoints(eq, n: 24)
        var p = Path()
        for (i, pt) in pts.enumerated() {
            let q = CGPoint(x: pt.x * 82, y: (18 - pt.y * 2.2) / 36 * 30)
            if i == 0 { p.move(to: q) } else { p.addLine(to: q) }
        }
        return p
    }

    // MARK: Lydbilde

    private var bal: Int { m.sset["bal"] ?? 0 }
    private static let vmax = [100, 90, 80, 70]
    private var maxv: Int { Self.vmax[max(0, min(3, m.sset["vmax"] ?? 0))] }

    private var soundImage: some View {
        VStack(alignment: .leading, spacing: 10) {
            V4Kicker(text: "LYDBILDE")
            VStack(spacing: 0) {
                balanceRow
                toggleRow("Lydstyrkekorreksjon", "Mer bass og diskant på lavt volum, så musikken ikke blir tynn.", m.prof.loud) {
                    m.setProf { $0.loud.toggle() }
                }
                toggleRow("Nattmodus", "Jevner ut forskjellen mellom svake og sterke partier.", night) { night.toggle() }
                toggleRow("Små høyttalere", "Kutter den dypeste bassen så små høyttalere ikke forvrenger.", hpf) { hpf.toggle() }
                maxRow
                roomEQRow
                speakerRow
            }
            .v4Card()
        }
    }

    private var speakerRow: some View {
        Button { Haptics.tick(); m.showSpeakers = true } label: {
            HStack(spacing: 12) {
                VStack(alignment: .leading, spacing: 3) {
                    Text("Høyttalerprofil").sora(15)
                    Text("Hent en Skjold Sertifisert-profil for høyttalerne dine, eller mål dem selv.").sora(12, .regular, V4.muted)
                }
                Spacer(minLength: 8)
                Text("Åpne").sora(14, .regular, V4.gold)
            }
            .padding(.horizontal, 16).padding(.vertical, 14)
            .contentShape(Rectangle())
        }
        .plain()
    }

    private var roomEQRow: some View {
        Button { Haptics.tick(); m.showRoomEQ = true } label: {
            HStack(spacing: 12) {
                VStack(alignment: .leading, spacing: 3) {
                    Text("Romkorreksjon").sora(15)
                    Text("Mål rommet med telefonens mikrofon og demp basstopper.").sora(12, .regular, V4.muted)
                }
                Spacer(minLength: 8)
                Text("Mål").sora(14, .regular, V4.gold)
            }
            .padding(.horizontal, 16).padding(.vertical, 14)
            .contentShape(Rectangle())
        }
        .plain()
    }

    private var balanceRow: some View {
        let p = CGFloat(bal + 5) / 10
        return VStack(spacing: 10) {
            HStack(alignment: .firstTextBaseline) {
                Text("Balanse").sora(15)
                Spacer()
                Text(bal == 0 ? "Midt" : bal < 0 ? "V \(-bal)" : "H \(bal)").mono(12, bal != 0 ? V4.gold : V4.muted)
            }
            HStack(spacing: 10) {
                Text("V").mono(11, V4.muted)
                GeometryReader { g in
                    let w = g.size.width
                    ZStack(alignment: .leading) {
                        Capsule().fill(V4.track).frame(height: 8)
                        Rectangle().fill(Color(hex: 0x4a4a4c)).frame(width: 1, height: 16).offset(x: w / 2)
                        Capsule().fill(V4.goldDark).frame(width: abs(p - 0.5) * w, height: 8).offset(x: min(0.5, p) * w)
                        Circle().fill(V4.ink).frame(width: 22, height: 22).shadow(color: .black.opacity(0.5), radius: 3, y: 2)
                            .offset(x: p * w - 11)
                    }
                    .frame(height: 22)
                    .frame(maxHeight: .infinity)
                    .contentShape(Rectangle())
                    .gesture(DragGesture(minimumDistance: 0).onChanged { v in
                        let n = Int((v.location.x / max(1, w) * 10 - 5).rounded())
                        let c = max(-5, min(5, n))
                        if c != bal { Haptics.sliderStep(from: bal, to: c, min: -5, max: 5); m.setS("bal", c) }
                    })
                }
                .frame(height: 30)
                Text("H").mono(11, V4.muted)
            }
        }
        .padding(.horizontal, 16).padding(.vertical, 14)
        .accessibilityElement(children: .combine)
        .accessibilityLabel("Balanse")
    }

    private func toggleRow(_ n: String, _ hint: String, _ on: Bool, _ toggle: @escaping () -> Void) -> some View {
        HStack(spacing: 12) {
            VStack(alignment: .leading, spacing: 2) {
                Text(n).sora(15)
                Text(hint).sora(12, .regular, V4.muted, lineHeight: 1.4).fixedSize(horizontal: false, vertical: true)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            V4Switch(on: on, label: n, toggle: toggle)
        }
        .padding(.horizontal, 16).padding(.vertical, 13)
        .v4TopLine(V4.line)
    }

    private var maxRow: some View {
        VStack(spacing: 10) {
            HStack(alignment: .top, spacing: 12) {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Maks volum").sora(15)
                    Text("Volumhjulet og appen går ikke høyere").sora(12, .regular, V4.muted)
                }
                Spacer(minLength: 0)
                Text("\(maxv)").mono(12, V4.ink2)
            }
            V4Bar(value: Double(maxv - 40) / 60, height: 8, trackColor: V4.track, label: "Maks volum", haptics: false) { v in
                let want = 40 + v * 60
                let idx = Self.vmax.enumerated().min { abs(Double($0.element) - want) < abs(Double($1.element) - want) }?.offset ?? 0
                if idx != (m.sset["vmax"] ?? 0) { Haptics.tick(); m.setS("vmax", idx) }
            }
        }
        .padding(.horizontal, 16).padding(.vertical, 14)
        .v4TopLine(V4.line)
    }
}
