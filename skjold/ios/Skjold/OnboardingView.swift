import SwiftUI

/// 02–08: OPPSETT · n AV 4 (find amplifier, QR, Wi-Fi, room, speaker test, software).
struct OnboardingView: View {
    @Environment(AppModel.self) private var m

    var body: some View {
        GeometryReader { g in
            ScrollView(.vertical, showsIndicators: false) {
                VStack(alignment: .leading, spacing: 16) {
                    header
                    SKProgressSteps(step: m.obStep)
                    Text(m.scan ? "Skann QR-koden" : AppModel.obText[m.ob].0).sora(28, .semibold, lineHeight: 1.15)
                    Text(m.scan ? "Hold kameraet mot skjermen på forsterkeren." : AppModel.obText[m.ob].1)
                        .sora(13, .regular, .body, lineHeight: 1.5)
                        .fixedSize(horizontal: false, vertical: true)
                    if m.scan { ScanStep() }
                    else {
                        switch m.ob {
                        case 0: FindStep(browser: m.browser)
                        case 1: WifiStep()
                        case 2: RoomStep()
                        case 3: TestStep()
                        default: SoftwareStep()
                        }
                    }
                    if m.ob != 0 && !m.scan {
                        Spacer(minLength: 0)
                        SKButton(title: nextLabel, kind: m.okOb ? .primary : .disabled) { m.obNext() }
                    }
                }
                .padding(.top, 8).padding(.horizontal, 20).padding(.bottom, 18)
                .frame(minHeight: g.size.height, alignment: .top)
            }
            .scrollDismissesKeyboard(.interactively)
            .scrollBounceBehavior(.basedOnSize)
        }
        .onAppear { m.browser.start() }
    }

    private var header: some View {
        HStack {
            SKMonoLabel(text: "OPPSETT · \(m.obStep + 1) AV 4")
            Spacer()
            if m.ob > 0 || m.scan {
                SKLinkButton(title: "Tilbake") { m.obBack() }.padding(.vertical, 6)
            }
        }
        .frame(minHeight: 28)
    }

    private var nextLabel: String {
        m.ob == 1 ? "Koble til" : m.ob == 4 ? (m.obUpd >= 100 ? "Ferdig" : "Oppdaterer …") : "Neste"
    }
}

// MARK: - 02 Finn forsterker

private struct FindStep: View {
    @Environment(AppModel.self) private var m
    let browser: DeviceBrowser

    var body: some View {
        Group {
            if browser.devices.isEmpty {
                // nothing on the network: the design's two cards, which continue in demo mode
                deviceCard(name: "Skjold S1", meta: "Demo · ingen enhet funnet ennå", icon: SK.dev("s1").icon, selected: true, action: "Sett opp") { m.pickDevice("s1") }
                deviceCard(name: "Skjold Node", meta: "Demo · ingen enhet funnet ennå", icon: SK.dev("node").icon, selected: false, action: "Sett opp") { m.pickDevice("node") }
            } else {
                ForEach(Array(browser.devices.enumerated()), id: \.element.id) { i, d in
                    let type = Self.type(d)
                    let set = m.known.contains { $0.host == d.host }
                    deviceCard(name: SK.dev(type).n, meta: d.name + " · " + (d.host.map { $0 + (set ? " · lagt til" : "") } ?? "kobler til …"),
                               icon: SK.dev(type).icon, selected: i == 0, action: set ? "Åpne" : "Koble til") {
                        if let h = d.host { m.pickFound(h, type: type) } else { Haptics.warning() }
                    }
                }
            }
            TimelineView(.periodic(from: .now, by: 0.42)) { tl in
                let on = Int(tl.date.timeIntervalSinceReferenceDate / 0.42) % 2 == 0
                HStack(spacing: 8) {
                    Circle().fill(on ? Color.accent : .off).frame(width: 8, height: 8)
                    Text("Leter etter flere …").sora(12, .regular, .muted)
                }
                .padding(.vertical, 4).padding(.horizontal, 2)
            }
            if !m.obErr.isEmpty { Text(m.obErr).sora(12, .regular, .danger, lineHeight: 1.45).fixedSize(horizontal: false, vertical: true) }
            Spacer(minLength: 0)
            SKButton(title: "Skann QR-kode på skjermen", kind: .secondary, height: 50, size: 14) {
                m.startScan(simulated: !QRScannerView.isAvailable)
            }
            // Hopp over oppsettet: rett inn i appen (Skjold-enheter kan legges til senere under Rom → Legg til enhet)
            SKLinkButton(title: "Hopp over – legg til enhet senere") { m.skipSetup() }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 6)
        }
    }

    /// Model from the TXT record (product=s1|node|core), else guessed from the name.
    static func type(_ d: FoundDevice) -> String {
        if ["s1", "node", "core"].contains(d.product) { return d.product }
        if d.name.localizedCaseInsensitiveContains("core") { return "core" }
        return d.name.localizedCaseInsensitiveContains("node") ? "node" : "s1"
    }

    private func deviceCard(name: String, meta: String, icon: String, selected: Bool, action label: String, _ action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack(spacing: 12) {
                SKIcon(d: icon, size: 40, stroke: 1.1, color: selected ? .ink : .ink2)
                VStack(alignment: .leading, spacing: 2) {
                    Text(name).sora(14)
                    Text(meta).mono(10).fixedSize(horizontal: false, vertical: true)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                Text(label).sora(12, .regular, .accent2).fixedSize()
            }
            .padding(14)
            .background(RoundedRectangle(cornerRadius: 14, style: .continuous).fill(selected ? Color.selBg : .card))
            .skBorder(selected ? .accent : .line2, radius: 14)
        }
        .plain()
    }
}

// MARK: - 03 QR

private struct ScanStep: View {
    @Environment(AppModel.self) private var m

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 14, style: .continuous).fill(Color(hex: 0x151517))
            if QRScannerView.isAvailable && m.camOK {
                QRScannerView { m.qrFound($0) }
                    .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
            }
            VStack(spacing: 16) {
                TimelineView(.periodic(from: .now, by: 0.14)) { tl in
                    // same motion as the design: 12 + (sin(t·0.35)·0.5 + 0.5)·160, t in 140 ms ticks
                    let t = tl.date.timeIntervalSinceReferenceDate / 0.14
                    let y = 12 + (sin(t * 0.35) * 0.5 + 0.5) * 160
                    ZStack(alignment: .topLeading) {
                        corners
                        Rectangle().fill(Color.accent)
                            .frame(width: 166, height: 2)
                            .shadow(color: .accent, radius: 6)
                            .offset(x: 12, y: y)
                    }
                    .frame(width: 190, height: 190)
                }
                Text(m.scanFound ? "Fant Skjold-Oppsett-0001 …" : "Leter etter QR-kode …").sora(13, .regular, .ink2)
            }
        }
        .frame(maxWidth: .infinity, minHeight: 360)
        .frame(maxHeight: .infinity)
    }

    private var corners: some View {
        ZStack {
            ForEach(0..<4, id: \.self) { i in
                CornerShape()
                    .stroke(Color.accent, style: StrokeStyle(lineWidth: 3))
                    .frame(width: 34, height: 34)
                    .rotationEffect(.degrees(Double(i) * 90))
                    .frame(width: 190, height: 190, alignment: [.topLeading, .topTrailing, .bottomTrailing, .bottomLeading][i])
            }
        }
        .frame(width: 190, height: 190)
    }
}

/// Top-left corner bracket with 14 pt radius (border-left + border-top).
private struct CornerShape: Shape {
    func path(in r: CGRect) -> Path {
        var p = Path()
        let i: CGFloat = 1.5
        p.move(to: CGPoint(x: i, y: r.maxY))
        p.addLine(to: CGPoint(x: i, y: 14))
        p.addArc(tangent1End: CGPoint(x: i, y: i), tangent2End: CGPoint(x: 14, y: i), radius: 12.5)
        p.addLine(to: CGPoint(x: r.maxX, y: i))
        return p
    }
}

// MARK: - 04/05 Wi-Fi

private struct WifiStep: View {
    @Environment(AppModel.self) private var m

    var body: some View {
        @Bindable var m = m
        VStack(spacing: 0) {
            ForEach(Array(m.nets.enumerated()), id: \.offset) { i, ssid in
                let on = !m.netManual && m.net == i
                row(ssid, mark: on ? "✓" : "", bg: on ? .selBg : .clear, line: i > 0 ? .line : .clear, fg: .ink) {
                    m.net = i; m.netManual = false
                }
            }
            row("Annet nettverk …", mark: m.netManual ? "✓" : "", bg: m.netManual ? .selBg : .clear, line: .line, fg: .ink2) { m.netManual = true }
        }
        .skBox(.card, .line)
        if m.netManual {
            Text("Skriv inn navnet hvis nettverket er skjult eller ikke dukker opp. Forsterkeren støtter 2,4 GHz.")
                .sora(12, .regular, .muted, lineHeight: 1.45).fixedSize(horizontal: false, vertical: true)
            SKField(placeholder: "Nettverksnavn (SSID)", text: $m.ssid, plainInput: true)
            HStack(spacing: 6) {
                ForEach(Array(["WPA2", "WPA3", "Ingen"].enumerated()), id: \.offset) { i, label in
                    let s = SelStyle.of(m.sec == i)
                    Button { m.sec = i } label: {
                        Text(label).sora(13, .regular, s.fg).lineLimit(1)
                            .frame(maxWidth: .infinity).frame(height: 38)
                            .background(Capsule().fill(s.bg)).skCapsuleBorder(s.bd)
                    }
                    .plain()
                }
            }
        }
        if m.needPw {
            SKField(placeholder: "Passord", text: $m.pw, secure: true)
        }
        if m.wifiBusy { Text("Henter nettverk fra forsterkeren …").sora(12, .regular, .muted) }
        if !m.obErr.isEmpty {
            Text(m.obErr).sora(12, .regular, m.obErr.hasPrefix("Kobler") ? .muted : .danger, lineHeight: 1.45)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private func row(_ title: String, mark: String, bg: Color, line: Color, fg: Color, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack {
                Text(title).sora(14, .regular, fg)
                Spacer()
                Text(mark).sora(12, .regular, .accent2)
            }
            .padding(.horizontal, 14)
            .frame(minHeight: 50)
            .background(bg)
            .topLine(line)
        }
        .plain()
    }
}

// MARK: - 06 Rom

private struct RoomStep: View {
    @Environment(AppModel.self) private var m

    var body: some View {
        @Bindable var m = m
        LazyVGrid(columns: [GridItem(.flexible(), spacing: 8), GridItem(.flexible(), spacing: 8)], spacing: 8) {
            ForEach(AppModel.roomList, id: \.self) { label in
                let on = !m.roomCustom && m.room == label
                let s = SelStyle.of(on)
                Button { m.room = label; m.roomCustom = false } label: {
                    HStack(spacing: 8) {
                        Text(label).sora(14, .regular, s.fg).lineLimit(1)
                        Spacer(minLength: 0)
                        Text(on ? "✓" : "").sora(12, .regular, .accent2)
                    }
                    .padding(.horizontal, 14).frame(height: 50)
                    .background(RoundedRectangle(cornerRadius: 12, style: .continuous).fill(s.bg))
                    .skBorder(s.bd, radius: 12)
                }
                .plain()
            }
        }
        Button {
            if !m.roomCustom { m.room = AppModel.roomList.contains(m.room) ? "" : m.room }
            m.roomCustom = true
        } label: {
            HStack(spacing: 10) {
                SKIcon(d: Icons.plus, size: 16, stroke: 2)
                Text("Skriv eget navn").sora(14, .regular, m.roomCustom ? .accent2 : .ink2)
                Spacer()
            }
            .foregroundStyle(m.roomCustom ? Color.accent2 : .ink2)
            .padding(.horizontal, 14).frame(height: 50)
            .background(RoundedRectangle(cornerRadius: 12, style: .continuous).fill(m.roomCustom ? Color.selBg : .clear))
            .skBorder(m.roomCustom ? .accent : .off, radius: 12, dash: [4, 3])
        }
        .plain()
        if m.roomCustom {
            SKField(placeholder: "For eksempel Hytta eller Runes rom", text: $m.room, border: .accent, maxLength: 20)
            Text("Maks 20 tegn. Kan endres senere under Innstillinger.").sora(12, .regular, .muted)
        }
    }
}

// MARK: - 07 Test høyttalere

private struct TestStep: View {
    @Environment(AppModel.self) private var m

    var body: some View {
        SKLinkButton(title: "Hopp over høyttalertest") { m.goOb(4) }
        HStack(spacing: 10) {
            ForEach([("L", "Venstre"), ("R", "Høyre")], id: \.0) { k, label in
                let done = m.tested.contains(k)
                let s = SelStyle.of(done)
                Button { m.testSide(k) } label: {
                    VStack(spacing: 8) {
                        Text(k).font(.sora(42, .light)).foregroundStyle(Color.ink)
                        Text(done ? "Spilt av" : label).sora(12, .regular, s.fg)
                    }
                    .frame(maxWidth: .infinity).frame(height: 150)
                    .background(RoundedRectangle(cornerRadius: 14, style: .continuous).fill(s.bg))
                    .skBorder(s.bd, radius: 14)
                }
                .plain()
            }
        }
    }
}

// MARK: - 08 Programvare

private struct SoftwareStep: View {
    @Environment(AppModel.self) private var m

    /// Installed version from the amplifier and the newest skjold-v* release on GitHub (installing is done on the device).
    private var text: String {
        guard m.live else { return m.obUpd >= 100 ? "1.4.2 installert" : "1.4.1 → 1.4.2 · \(m.obUpd) %" }
        let cur = m.dev?.version ?? "–"
        if m.obUpd < 100 || m.checking { return cur + " · ser etter oppdatering · \(min(m.obUpd, 99)) %" }
        if let rel = m.upd.latest { return cur + " → " + GitHubReleases.version(rel.tag) + " · installeres fra forsterkeren" }
        return cur + " installert"
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            GeometryReader { g in
                ZStack(alignment: .leading) {
                    Color.line
                    Color.accent.frame(width: g.size.width * CGFloat(m.obUpd) / 100)
                }
            }
            .frame(height: 6)
            .clipShape(RoundedRectangle(cornerRadius: 3))
            Text(text).mono(12)
        }
    }
}

#Preview {
    let m = AppModel()
    m.intro = false; m.welcome = false
    return OnboardingView().environment(m).background(Color.bg)
}
