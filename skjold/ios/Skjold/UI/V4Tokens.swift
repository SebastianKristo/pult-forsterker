import SwiftUI

/// Design-tokens fra «Skjold App v4.dc.html» (platform = ios). 1 CSS-px = 1 pt.
/// Fargene, radiene og kurvene er hentet rett fra malen og objektene G / L / P i renderVals().
enum V4 {
    // MARK: Farger
    static let bg = Color(hex: 0x0b0b0c)
    static let searchBg = Color(hex: 0x050506)
    static let ink = Color(hex: 0xf2f2ee)
    static let ink2 = Color(hex: 0xc9c9c4)
    static let body = Color(hex: 0xa9a9a3)
    static let muted = Color(hex: 0x8b8b86)
    static let dim = Color(hex: 0x55554f)
    static let sub = Color(hex: 0xd0d0cb)
    static let chev = Color(hex: 0x6a6a65)
    static let tabIdle = Color(hex: 0xe4e4df)
    static let gold = Color(hex: 0xf0c46a)
    static let goldDark = Color(hex: 0xd9a441)
    static let green = Color(hex: 0x6fcf7f)
    static let red = Color(hex: 0xe8564a)
    static let selBg = Color(hex: 0x1c170d)
    static let card = Color(hex: 0x141415)
    static let card2 = Color(hex: 0x151517)
    static let sheet = Color(hex: 0x1a1a1c)
    static let row = Color(hex: 0x232326)
    static let line = Color(hex: 0x242426)
    static let line2 = Color(hex: 0x2e2e30)
    static let track = Color(hex: 0x2a2a2c)
    static let knobOff = Color(hex: 0x3a3a3c)
    static let mosaicEmpty = Color(hex: 0x1b1b1d)

    // MARK: Kurver (README → Animasjoner)
    static let lens = Animation.timingCurve(0.3, 1.35, 0.45, 1, duration: 0.5)
    static let tabColor = Animation.easeInOut(duration: 0.25)
    static let dock = Animation.timingCurve(0.2, 0.7, 0.2, 1, duration: 0.35)
    static let segLens = Animation.timingCurve(0.3, 1.3, 0.45, 1, duration: 0.4)
    static let segText = Animation.easeInOut(duration: 0.2)
    static let cover = Animation.easeInOut(duration: 0.35)
    static let panel = Animation.timingCurve(0.2, 0.7, 0.2, 1, duration: 0.45)
    static let pinSheet = Animation.timingCurve(0.2, 0.7, 0.2, 1, duration: 0.4)
    static let moreSheet = Animation.timingCurve(0.2, 0.8, 0.2, 1, duration: 0.42)
    static let scrim = Animation.easeInOut(duration: 0.3)
    static let toggle = Animation.easeInOut(duration: 0.2)
    static let eqDot = Animation.easeInOut(duration: 0.15)
    static let fade = Animation.easeInOut(duration: 0.25)
    static let chevron = Animation.easeInOut(duration: 0.2)
    static let collapse = Animation.spring(response: 0.45, dampingFraction: 0.8)

    // MARK: Ikoner (stier fra malen)
    static let search = "M11 18a7 7 0 1 0 0-14a7 7 0 1 0 0 14M20 20l-4-4"
    static let gear = "M12 15a3 3 0 1 0 0-6a3 3 0 1 0 0 6M12 2v3M12 19v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2 12h3M19 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1"
    static let chevDown = "M6 9l6 6 6-6"
    static let chevRight = "M9 6l6 6-6 6"
    static let back = "M15 5l-7 7 7 7"
    static let close = "M6 6l12 12M18 6L6 18"
    static let plus = "M12 5v14M5 12h14"
    static let sort = "M4 7h16M7 12h10M10 17h4"
    static let pin = "M12 17v5M8 3h8l-1 6 3 3H6l3-3z"
    static let vol = "M4 9v6h4l5 4V5L8 9zM16 9a4 4 0 0 1 0 6"
    static let play = "M8 5.2v13.6a1 1 0 0 0 1.52.85l10.6-6.8a1 1 0 0 0 0-1.7L9.52 4.35A1 1 0 0 0 8 5.2z"
    static let pause = SVG.rect(6, 4.5, 4, 15, rx: 1.2) + SVG.rect(14, 4.5, 4, 15, rx: 1.2)
    static let miniPrev = "M7 5h2v14H7zM20 5.5v13a.8.8 0 0 1-1.2.7L9.5 12.7a.8.8 0 0 1 0-1.4l9.3-6.5a.8.8 0 0 1 1.2.7z"
    static let miniNext = "M15 5h2v14h-2zM4 5.5v13a.8.8 0 0 0 1.2.7l9.3-6.5a.8.8 0 0 0 0-1.4L5.2 4.8A.8.8 0 0 0 4 5.5z"
    static let skip = "M5 5.5v13a.8.8 0 0 0 1.25.66L15 13.1V18a1 1 0 0 0 2 0V6a1 1 0 0 0-2 0v4.9L6.25 4.84A.8.8 0 0 0 5 5.5z"
    static let shuffle = "M4 7h3l10 10h3M4 17h3l3-3M14 10l3-3h3M18 5l2 2-2 2M18 15l2 2-2 2"
    static let repeatP = "M4 12V9a3 3 0 0 1 3-3h12M16 3l3 3-3 3M20 12v3a3 3 0 0 1-3 3H5M8 21l-3-3 3-3"
    static let queue = "M4 6h11M4 12h11M4 18h7M18 14v6l4-3z"
    static let speaker = "M7 3h10v18H7zM12 7h.01M12 17a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"
    static let speakerWide = SVG.rect(6, 3, 12, 18, rx: 2) + SVG.circle(12, 14, 3) + SVG.circle(12, 7, 0.8)
    static let dots = SVG.circle(5, 12, 1.8) + SVG.circle(12, 12, 1.8) + SVG.circle(19, 12, 1.8)
    static let dotsSmall = SVG.circle(5, 12, 1.7) + SVG.circle(12, 12, 1.7) + SVG.circle(19, 12, 1.7)
    static let dotsV = SVG.circle(12, 5, 1.9) + SVG.circle(12, 12, 1.9) + SVG.circle(12, 19, 1.9)
    static let check = "M5 12l5 5 9-10"
    static let up = "M6 15l6-6 6 6"
    static let handle = "M5 8h14M5 12h14M5 16h14"
    static let sync = "M4 12a8 8 0 0 1 14-5l2 2M20 12a8 8 0 0 1-14 5l-2-2M20 4v5h-5M4 20v-5h5"
    static let heart = "M12 20s-7-4.5-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.5-7 10-7 10z"

    /// Fanene nederst (TABS i malen).
    static let tabs: [(String, String)] = [
        ("Hjem", "M3 11l9-7 9 7M5 10v10h5v-6h4v6h5V10"),
        ("Lyd", "M5 4v6M5 14v6M12 4v3M12 11v9M19 4v9M19 17v3"),
        ("Rom", "M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z"),
        ("Innstillinger", gear)
    ]
}

// MARK: - Glass (G.btnBg / G.miniBg / G.fieldBg + skygger) – Liquid Glass med HTML-lagene oppå

extension View {
    /// Liquid Glass (Apple: glassEffect(_:in:)) for flytende kontroller i navigasjons-/kontrollaget.
    /// Ingen egne fyll, kanter eller skygger: materialet tegner refleksjon, lys og dybde selv.
    /// Parametrene er beholdt for kompatibilitet med eksisterende kall, men brukes ikke.
    func v4Glass<S: Shape>(_ shape: S, top: Double = 0.13, bottom: Double = 0.05, highlight: Double = 0.45,
                           shadowRadius: CGFloat = 17, shadowY: CGFloat = 12, shadowOpacity: Double = 0.5) -> some View {
        glassEffect(.regular.interactive(), in: shape)
    }

    /// Flytende glassknapp (tilbake, søk, sorter …) – reagerer på berøring som systemknapper.
    func v4GlassButton<S: Shape>(_ shape: S) -> some View {
        glassEffect(.regular.interactive(), in: shape)
    }

    /// Tett mørk kapsel med tynn kant (rgba(40,40,42,.6) + 1px rgba(255,255,255,.1)) – knapper i sidetitler.
    func v4DarkPill<S: InsettableShape>(_ shape: S, border: Double = 0.1, fill: Color = Color(hex: 0x28282a, alpha: 0.6)) -> some View {
        background(shape.fill(fill))
            .overlay(shape.strokeBorder(Color.white.opacity(border), lineWidth: 1))
            .overlay(alignment: .top) {
                shape.strokeBorder(LinearGradient(colors: [Color.white.opacity(0.1), .clear], startPoint: .top, endPoint: .center), lineWidth: 1)
                    .allowsHitTesting(false)
            }
    }

    /// Flytende meny over innholdet: Liquid Glass uten egen bakgrunn (Apple: ikke legg egne bakgrunner bak glass).
    func v4Menu(radius: CGFloat = 22) -> some View {
        glassEffect(.regular, in: RoundedRectangle(cornerRadius: radius, style: .continuous))
    }

    /// 1 px linje øverst (border-top i lister).
    func v4TopLine(_ c: Color) -> some View {
        overlay(alignment: .top) { Rectangle().fill(c).frame(height: 1) }
    }
}

// MARK: - Felles komponenter

/// Ikon fra en SVG-sti, viewBox 24.
struct V4Icon: View {
    let d: String
    var size: CGFloat = 20
    var stroke: CGFloat = 1.8
    var color: Color? = nil
    var fill = false
    var body: some View { SKIcon(d: d, size: size, stroke: stroke, color: color, fill: fill) }
}

/// Spill/pause-ikon (rect-par eller avrundet trekant fra malen).
struct V4PlayIcon: View {
    let playing: Bool
    var size: CGFloat = 18
    var color: Color? = nil
    var body: some View { SKIcon(d: playing ? V4.pause : V4.play, size: size, color: color, fill: true) }
}

/// iOS-bryter 51 × 31 (spor #d9a441 / #3a3a3c, knott 27, venstre 22 / 2).
struct V4Switch: View {
    let on: Bool
    var label: String = ""
    let toggle: () -> Void
    var body: some View {
        Button { Haptics.tick(); withAnimation(V4.toggle) { toggle() } } label: {
            ZStack(alignment: .topLeading) {
                Capsule().fill(on ? V4.goldDark : V4.knobOff).frame(width: 51, height: 31)
                Circle().fill(Color.white).frame(width: 27, height: 27)
                    .shadow(color: .black.opacity(0.35), radius: 3, y: 2)
                    .offset(x: on ? 22 : 2, y: 2)
            }
            .frame(width: 51, height: 31)
        }
        .plain()
        .accessibilityLabel(label)
        .accessibilityValue(on ? "På" : "Av")
    }
}

/// Glidebryter uten knott (input range med opacity 0 over et spor). Høyden er sporets høyde.
/// Mens fingeren er nede følger linja en lokal verdi (statusoppdateringer fra enheten overskriver den ikke),
/// onChange sendes høyst hvert 70. ms og sluttverdien alltid når fingeren slippes. Trykk hopper dit.
struct V4Bar: View {
    let value: Double          // 0…1
    var height: CGFloat = 8
    var trackColor: Color = Color(hex: 0xf2f2ee, alpha: 0.2)
    var fill: Color = V4.ink
    var label: String = "Volum"
    /// Haptiske tikk per hele prosent (av for glidebrytere som gir egen haptikk).
    var haptics: Bool = true
    var onChange: ((Double) -> Void)? = nil
    var onEnd: ((Double) -> Void)? = nil

    @State private var local: Double? = nil      // posisjonen mens fingeren er nede (og like etter)
    @State private var active = false
    @State private var lastSent = Date.distantPast
    @State private var pending: Double? = nil
    @State private var flush: Task<Void, Never>? = nil

    private static let interval: TimeInterval = 0.07
    private var shown: Double { max(0, min(1, local ?? value)) }

    var body: some View {
        GeometryReader { g in
            let w = max(1, g.size.width)
            ZStack(alignment: .leading) {
                Capsule().fill(trackColor)
                Capsule().fill(fill).frame(width: w * CGFloat(shown))
            }
            .frame(height: height)
            .frame(maxHeight: .infinity)
            .contentShape(Rectangle())
            // Høy prioritet: knapper, trykk og rulling rundt linja skal ikke ta draget
            .highPriorityGesture(DragGesture(minimumDistance: 0, coordinateSpace: .local)
                .onChanged { v in moved(Double(v.location.x / w)) }
                .onEnded { v in ended(Double(v.location.x / w)) })
        }
        .frame(height: height + 24)
        .padding(.vertical, -12)
        .accessibilityElement()
        .accessibilityLabel(label)
        .accessibilityValue("\(Int((shown * 100).rounded())) prosent")
        .accessibilityAdjustableAction { dir in
            let n = max(0, min(1, (Double(Int((shown * 100).rounded())) + (dir == .increment ? 5 : -5)) / 100))
            if haptics { Haptics.tick() }
            onChange?(n); onEnd?(n)
        }
    }

    private func moved(_ raw: Double) {
        let f = max(0, min(1, raw))
        if !active {
            active = true
            if haptics { Haptics.prepareSlider() }
        }
        let old = Int(((local ?? value) * 100).rounded())
        local = f
        if haptics { Haptics.sliderStep(from: old, to: Int((f * 100).rounded()), min: 0, max: 100, zero: nil) }
        send(f)
    }

    private func ended(_ raw: Double) {
        let f = max(0, min(1, raw))
        flush?.cancel(); flush = nil; pending = nil
        active = false
        local = f
        lastSent = Date()
        onChange?(f)
        onEnd?(f)
        if haptics { Haptics.sliderRelease() }
        // Behold den lokale verdien litt, til modellen (og enheten) har tatt igjen
        Task { @MainActor in
            try? await Task.sleep(for: .milliseconds(600))
            if !active { local = nil }
        }
    }

    /// Strupet sending: straks om det er gått 70 ms siden sist, ellers den siste verdien når tiden er ute.
    private func send(_ f: Double) {
        let since = Date().timeIntervalSince(lastSent)
        if since >= Self.interval {
            flush?.cancel(); flush = nil; pending = nil
            lastSent = Date()
            onChange?(f)
            return
        }
        pending = f
        guard flush == nil else { return }
        let wait = Self.interval - since
        flush = Task { @MainActor in
            try? await Task.sleep(for: .seconds(wait))
            guard !Task.isCancelled else { return }
            flush = nil
            guard active, let p = pending else { return }
            pending = nil
            lastSent = Date()
            onChange?(p)
        }
    }
}

/// Kildeikon i en sirkel (SRCICON i skjold_settings.js, via SourceLogos).
struct V4SourceIcon: View {
    let label: String
    var size: CGFloat = 68
    var ring: CGFloat = 0
    var body: some View {
        let s = SourceLogos.style(label)
        ZStack {
            s.bg
            if s.size > 0 {
                ZStack {
                    if !s.stroke.isEmpty { SKIcon(d: s.stroke, size: size * s.size, stroke: 1.8, color: s.fg) }
                    if !s.fillPath.isEmpty { SKIcon(d: s.fillPath, size: size * s.size, color: s.fg, fill: true) }
                    if !s.brand.isEmpty { SKIcon(d: s.brand, size: size * s.size, color: s.fg, fill: true) }
                }
            }
        }
        .frame(width: size, height: size)
        .clipShape(Circle())
        .overlay(Circle().strokeBorder(Color.white.opacity(0.08), lineWidth: 1))
        .padding(ring)
        .overlay { if ring > 0 { Circle().strokeBorder(V4.gold, lineWidth: ring) } }   // lineWidth 0 tegner en hårstrek
        .padding(-ring)
    }
}

/// Omslag: ekte bilde / logo når det finnes, ellers gradienten (ArtFill).
struct V4Art: View {
    let key: String
    var radius: CGFloat = 12
    var ring: CGFloat = 0
    var body: some View {
        ArtFill(key)
            .clipShape(RoundedRectangle(cornerRadius: radius, style: .continuous))
            // Bare når ringen er på: strokeBorder med lineWidth 0 tegner en tynn hårstrek (lys kant rundt logoen)
            .overlay { if ring > 0 { RoundedRectangle(cornerRadius: radius, style: .continuous).strokeBorder(V4.gold, lineWidth: ring) } }
    }
}

/// 2 × 2-mosaikk for spillelister.
struct V4Mosaic: View {
    let keys: [String]
    var size: CGFloat = 148
    var radius: CGFloat = 14
    var body: some View {
        let k = keys + Array(repeating: "", count: max(0, 4 - keys.count))
        VStack(spacing: 0) {
            HStack(spacing: 0) { cell(k[0]); cell(k[1]) }
            HStack(spacing: 0) { cell(k[2]); cell(k[3]) }
        }
        .frame(width: size, height: size)
        .clipShape(RoundedRectangle(cornerRadius: radius, style: .continuous))
    }
    @ViewBuilder private func cell(_ key: String) -> some View {
        if key.isEmpty { V4.mosaicEmpty } else { ArtFill(key) }
    }
}

/// Hylle: tittel + vannrett rulling ut til kantene (margin −20, padding 20).
struct V4Shelf<Content: View>: View {
    var spacing: CGFloat = 12
    var inset: CGFloat = 20
    @ViewBuilder var content: Content
    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(alignment: .top, spacing: spacing) { content }
                .padding(.horizontal, inset)
        }
        .padding(.horizontal, -inset)
        .scrollClipDisabled()
    }
}

/// Seksjonstittel med strek under (kicker i mono + store bokstaver) og pil.
struct V4ShelfHeader: View {
    let title: String
    var kicker: String = ""
    var icon: String = ""
    /// Hva et trykk på overskriften gjør. Uten handling vises ingen pil.
    var action: (() -> Void)? = nil
    var body: some View {
        if let action {
            Button(action: action) { row.contentShape(Rectangle()) }
                .buttonStyle(.plain)
                .accessibilityHint("Åpner \(title)")
        } else { row }
    }
    private var row: some View {
        HStack(spacing: 10) {
            HStack(spacing: 9) {
                if !icon.isEmpty { V4SourceIcon(label: icon, size: 20) }
                VStack(alignment: .leading, spacing: 1) {
                    if !kicker.isEmpty { Text(kicker).mono(10, V4.muted, em: 0.12) }
                    Text(title.uppercased()).sora(15, .bold).tracking(0.6).lineLimit(1)
                }
            }
            Spacer(minLength: 0)
            if action != nil { V4Icon(d: V4.chevRight, size: 18, stroke: 2.2, color: V4.ink2) }
        }
        .padding(.bottom, 10)
        .overlay(alignment: .bottom) { Rectangle().fill(Color.white.opacity(0.08)).frame(height: 1) }
    }
}

/// Sidetittel 32/600, −0.02em.
struct V4Title: View {
    let text: String
    var body: some View { Text(text).sora(32, .semibold).tracking(-0.64).lineLimit(1) }
}

/// Liste-kort (#141415, kant #242426, radius 22).
extension View {
    func v4Card(radius: CGFloat = 22, bg: Color = V4.card, border: Color = V4.line) -> some View {
        background(RoundedRectangle(cornerRadius: radius, style: .continuous).fill(bg))
            .overlay(RoundedRectangle(cornerRadius: radius, style: .continuous).strokeBorder(border, lineWidth: 1))
            .clipShape(RoundedRectangle(cornerRadius: radius, style: .continuous))
    }
}

/// Mono-kicker, 10/.12em.
struct V4Kicker: View {
    let text: String
    var color: Color = V4.muted
    var body: some View { Text(text).mono(10, color, em: 0.12) }
}

/// Rund «⋯»-knapp i lister.
struct V4MoreButton: View {
    var size: CGFloat = 18
    let action: () -> Void
    var body: some View {
        Button(action: action) { V4Icon(d: V4.dotsSmall, size: size, color: V4.ink, fill: true).frame(width: 36, height: 36).padding(4).contentShape(Rectangle()).padding(-4) }
            .plain()
            .accessibilityLabel("Mer")
    }
}

/// Spiller-indikator (tre gule stolper) på fliser.
struct V4NowBars: View {
    var body: some View {
        HStack(alignment: .bottom, spacing: 2) {
            RoundedRectangle(cornerRadius: 1).fill(V4.gold).frame(width: 2.5, height: 6)
            RoundedRectangle(cornerRadius: 1).fill(V4.gold).frame(width: 2.5, height: 10)
            RoundedRectangle(cornerRadius: 1).fill(V4.gold).frame(width: 2.5, height: 7)
        }
        .padding(.horizontal, 8).padding(.bottom, 6)
        .frame(height: 22, alignment: .bottom)
        .background(Capsule().fill(Color.black.opacity(0.55)))
    }
}
