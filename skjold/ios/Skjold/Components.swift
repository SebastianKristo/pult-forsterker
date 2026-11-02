import SwiftUI

// Components drawn by hand to match the design file 1:1 (no List/Form/system controls).

// MARK: - Text helpers

struct SKMonoLabel: View {
    let text: String
    var color: Color = .muted
    var size: CGFloat = 10
    var body: some View { Text(text).mono(size, color, em: 0.12) }
}

struct SKSectionHeader: View {
    let title: String
    var size: CGFloat = 17
    var kicker: String? = nil
    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            if let kicker, !kicker.isEmpty { SKMonoLabel(text: kicker) }
            Text(title).sora(size, .semibold)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

// MARK: - Buttons

enum SKButtonKind { case primary, secondary, disabled }

struct SKButton: View {
    let title: String
    var kind: SKButtonKind = .primary
    var height: CGFloat = 52
    var size: CGFloat = 15
    var radius: CGFloat = 14
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .sora(size, kind == .secondary ? .regular : .semibold, fg)
                .frame(maxWidth: .infinity)
                .frame(height: height)
                .background(RoundedRectangle(cornerRadius: radius, style: .continuous).fill(bg))
                .if(kind == .secondary) { $0.skBorder(.line2, radius: radius) }
        }
        .plain()
    }

    private var bg: Color { kind == .primary ? .accent : kind == .disabled ? .line : .clear }
    private var fg: Color { kind == .primary ? .bg : kind == .disabled ? .muted : .ink }
}

/// Gold text button ("Tilbake", "Administrer", …).
struct SKLinkButton: View {
    let title: String
    var size: CGFloat = 13
    var color: Color = .accent
    let action: () -> Void
    var body: some View {
        Button(action: action) { Text(title).sora(size, .regular, color) }.plain()
    }
}

/// "‹ Hjem" style back link.
struct SKBackButton: View {
    let title: String
    let action: () -> Void
    var body: some View {
        Button(action: action) {
            HStack(spacing: 4) {
                SKIcon(d: Icons.back, size: 16, stroke: 2)
                Text(title).sora(14, .regular, .accent)
            }
            .foregroundStyle(Color.accent)
        }
        .plain()
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

/// Pill with gold primary fill (Spill) or outline.
struct SKPill: View {
    let title: String
    var primary = false
    var icon: String? = nil
    var height: CGFloat = 38
    var hPad: CGFloat = 16
    var border: Color = .line2
    var bg: Color = .clear
    var fg: Color = .ink
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 6) {
                if let icon { SKIcon(d: icon, size: 12, color: .bg, fill: true) }
                Text(title).sora(13, primary ? .semibold : .regular, primary ? .bg : fg).lineLimit(1)
            }
            .padding(.horizontal, hPad)
            .frame(height: height)
            .background(Capsule().fill(primary ? Color.accent : bg))
            .if(!primary) { $0.skCapsuleBorder(border) }
        }
        .plain()
    }
}

// MARK: - Fields

struct SKField: View {
    let placeholder: String
    @Binding var text: String
    var height: CGFloat = 48
    var size: CGFloat = 16
    var radius: CGFloat = 12
    var border: Color = .line2
    var bg: Color = .card
    var secure = false
    var mono = false
    var keyboard: UIKeyboardType = .default
    var plainInput = false   // autocapitalize/autocorrect off
    var maxLength: Int? = nil

    var body: some View {
        Group {
            if secure {
                SecureField("", text: $text, prompt: prompt)
            } else {
                TextField("", text: $text, prompt: prompt)
            }
        }
        .font(mono ? .plexMono(size) : .sora(size))
        .foregroundStyle(Color.ink)
        .tint(.accent)
        .keyboardType(keyboard)
        .textInputAutocapitalization(plainInput ? .never : .sentences)
        .autocorrectionDisabled(plainInput)
        .padding(.horizontal, 14)
        .frame(height: height)
        .background(RoundedRectangle(cornerRadius: radius, style: .continuous).fill(bg))
        .skBorder(border, radius: radius)
        .onChange(of: text) { _, v in
            if let maxLength, v.count > maxLength { text = String(v.prefix(maxLength)) }
        }
    }

    private var prompt: Text {
        Text(placeholder).font(mono ? .plexMono(size) : .sora(size)).foregroundStyle(Color.dim)
    }
}

// MARK: - Chips

struct SKChip: View {
    let label: String
    var on = false
    var height: CGFloat? = nil
    var hPad: CGFloat = 12
    var vPad: CGFloat = 8
    var size: CGFloat = 12
    var radius: CGFloat = 999
    var style: SelStyle? = nil
    var trailingDot: Color? = nil
    var leadingNumber: String? = nil
    let action: () -> Void

    var body: some View {
        let s = style ?? SelStyle.of(on)
        Button(action: action) {
            HStack(spacing: 6) {
                if let leadingNumber { Text(leadingNumber).mono(10, s.fg).opacity(0.7) }
                Text(label).sora(size, .regular, s.fg).lineLimit(1).fixedSize()
                if let trailingDot { Circle().fill(trailingDot).frame(width: 6, height: 6) }
            }
            .padding(.horizontal, hPad)
            .padding(.vertical, height == nil ? vPad : 0)
            .frame(height: height)
            .background(shape.fill(s.bg))
            .overlay(shape.strokeBorder(s.bd, lineWidth: 1))
        }
        .plain()
    }

    private var shape: RoundedRectangle { RoundedRectangle(cornerRadius: min(radius, 200), style: .continuous) }
}

/// Black/white filter chips (genres, moods): selected = ink background.
struct SKFilterChip: View {
    let label: String
    let on: Bool
    var hPad: CGFloat = 14
    let action: () -> Void
    var body: some View {
        SKChip(label: label, height: 34, hPad: hPad, size: 13, radius: 8,
               style: SelStyle(bd: on ? .ink : .line2, bg: on ? .ink : .card2, fg: on ? .bg : .ink), action: action)
    }
}

// MARK: - Segmented

struct SKSegmented: View {
    let items: [String]
    let selected: Int
    var height: CGFloat = 36
    var bg: Color = .card
    var border: Color? = .line
    var selBg: Color = .seg
    var selFg: Color = .ink
    var fg: Color = .muted
    let pick: (Int) -> Void

    var body: some View {
        HStack(spacing: 4) {
            ForEach(Array(items.enumerated()), id: \.offset) { i, n in
                Button { pick(i) } label: {
                    Text(n).sora(13, .semibold, i == selected ? selFg : fg)
                        .frame(maxWidth: .infinity).frame(height: height)
                        .background(RoundedRectangle(cornerRadius: 8, style: .continuous).fill(i == selected ? selBg : .clear))
                }
                .plain()
            }
        }
        .padding(3)
        .background(RoundedRectangle(cornerRadius: 10, style: .continuous).fill(bg))
        .if(border != nil) { $0.skBorder(border!, radius: 10) }
    }
}

// MARK: - Toggle

struct SKToggle: View {
    let on: Bool
    var onColor: Color = .accent
    let action: () -> Void
    var body: some View {
        Button(action: action) {
            ZStack(alignment: .topLeading) {
                Capsule().fill(on ? onColor : .off).frame(width: 46, height: 28)
                Circle().fill(Color.ink).frame(width: 22, height: 22).offset(x: on ? 21 : 3, y: 3)
            }
            .frame(width: 46, height: 28)
            .animation(.easeOut(duration: 0.15), value: on)
        }
        .plain()
        .accessibilityValue(on ? "På" : "Av")
        .accessibilityAddTraits(.isToggle)
    }
}

// MARK: - Slider (CSS range input with accent-color)

struct SKSlider: View {
    @Binding var value: Double
    var range: ClosedRange<Double> = 0...100
    var step: Double = 1
    var tint: Color = .accent
    var vertical = false
    var onChange: ((Double) -> Void)? = nil

    private let thumb: CGFloat = 17
    private let track: CGFloat = 5

    var body: some View {
        GeometryReader { g in
            let len = (vertical ? g.size.height : g.size.width) - thumb
            let frac = CGFloat((value - range.lowerBound) / (range.upperBound - range.lowerBound))
            // Thumb centre along the track; everything is positioned from the same centre line.
            let c = thumb / 2 + len * (vertical ? 1 - frac : frac)
            let w = g.size.width, h = g.size.height
            ZStack(alignment: .topLeading) {
                Capsule().fill(Color(hex: 0x4a4a4c))
                    .frame(width: vertical ? track : w, height: vertical ? h : track)
                    .position(x: w / 2, y: h / 2)
                Capsule().fill(tint)
                    .frame(width: vertical ? track : c, height: vertical ? h - c : track)
                    .position(x: vertical ? w / 2 : c / 2, y: vertical ? (c + h) / 2 : h / 2)
                Circle().fill(tint)
                    .frame(width: thumb, height: thumb)
                    .shadow(color: .black.opacity(0.3), radius: 1, y: 0.5)
                    .position(x: vertical ? w / 2 : c, y: vertical ? c : h / 2)
            }
            .frame(width: w, height: h)
            .contentShape(Rectangle())
            .gesture(DragGesture(minimumDistance: 0).onChanged { d in
                let p = vertical ? 1 - (d.location.y - thumb / 2) / len : (d.location.x - thumb / 2) / len
                let raw = range.lowerBound + Double(max(0, min(1, p))) * (range.upperBound - range.lowerBound)
                let v = (raw / step).rounded() * step
                if v != value {
                    detentHaptic(from: value, to: v)
                    value = v; onChange?(v)
                }
            })
        }
        .frame(width: vertical ? 28 : nil, height: vertical ? nil : 16)
    }

    /// Small ranges (EQ, bass, balance) tick on every step; large ranges (volume) every 10.
    /// The ends and the centre (0 dB / Midt) give a firmer bump.
    private func detentHaptic(from old: Double, to new: Double) {
        let span = range.upperBound - range.lowerBound
        if new == range.lowerBound || new == range.upperBound || (range.lowerBound < 0 && new == 0) {
            Haptics.bump(); return
        }
        let every = span > 30 ? 10.0 : step
        if (old / every).rounded(.down) != (new / every).rounded(.down) { Haptics.tick() }
    }
}

// MARK: - Cards and rows

struct SKCard<Content: View>: View {
    var bg: Color = .card
    var border: Color = .line
    var radius: CGFloat = 14
    @ViewBuilder var content: Content
    var body: some View {
        VStack(alignment: .leading, spacing: 0) { content }
            .frame(maxWidth: .infinity, alignment: .leading)
            .skBox(bg, border, radius: radius)
    }
}

struct SKSelectCard<Content: View>: View {
    let selected: Bool
    var radius: CGFloat = 14
    let action: () -> Void
    @ViewBuilder var content: Content
    var body: some View {
        let s = SelStyle.of(selected)
        Button(action: action) {
            content
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(RoundedRectangle(cornerRadius: radius, style: .continuous).fill(s.bg))
                .skBorder(s.bd, radius: radius)
        }
        .plain()
    }
}

extension View {
    /// CSS `border-top: 1px solid …` used for list rows.
    func topLine(_ color: Color) -> some View {
        overlay(alignment: .top) { Rectangle().fill(color).frame(height: 1) }
    }
}

/// Horizontal scroller that bleeds to the screen edges (margin 0 -20px; padding 0 20px).
struct EdgeScroll<Content: View>: View {
    var spacing: CGFloat = 12
    var inset: CGFloat = 20
    var alignment: VerticalAlignment = .top
    @ViewBuilder var content: Content
    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(alignment: alignment, spacing: spacing) { content }
                .padding(.horizontal, inset)
        }
        .padding(.horizontal, -inset)
    }
}

/// flex-wrap row.
struct FlowLayout: Layout {
    var spacing: CGFloat = 6
    var lineSpacing: CGFloat? = nil

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let w = proposal.width ?? .infinity
        var x: CGFloat = 0, y: CGFloat = 0, lineH: CGFloat = 0, maxW: CGFloat = 0
        for s in subviews {
            let sz = s.sizeThatFits(.unspecified)
            if x > 0 && x + sz.width > w { x = 0; y += lineH + (lineSpacing ?? spacing); lineH = 0 }
            x += sz.width + spacing; lineH = max(lineH, sz.height); maxW = max(maxW, x - spacing)
        }
        return CGSize(width: proposal.width ?? maxW, height: y + lineH)
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        var x = bounds.minX, y = bounds.minY, lineH: CGFloat = 0
        for s in subviews {
            let sz = s.sizeThatFits(.unspecified)
            if x > bounds.minX && x + sz.width > bounds.maxX { x = bounds.minX; y += lineH + (lineSpacing ?? spacing); lineH = 0 }
            s.place(at: CGPoint(x: x, y: y), proposal: ProposedViewSize(sz))
            x += sz.width + spacing; lineH = max(lineH, sz.height)
        }
    }
}

// MARK: - Progress steps (OPPSETT · 1 AV 4)

struct SKProgressSteps: View {
    let step: Int
    var count = 4
    var body: some View {
        // 5-column grid with 4 bars, as in the design
        GeometryReader { g in
            let w = (g.size.width - 4 * 4) / 5
            HStack(spacing: 4) {
                ForEach(0..<count, id: \.self) { i in
                    RoundedRectangle(cornerRadius: 2).fill(i <= step ? Color.accent : Color.dots).frame(width: w, height: 3)
                }
            }
        }
        .frame(height: 3)
    }
}

// MARK: - Source logo (Kilder)

struct SourceStyle {
    var bg: AnyView
    var fg: Color
    var stroke: String = ""
    var fillPath: String = ""
    var brand: String = ""
    var size: CGFloat   // icon size as fraction of 64
}

enum SourceLogos {
    static let spotify = "M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.160 5.16 9.301c-.6.179-1.2-.181-1.380-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.020.599-1.559.3z"
    static let ytm = "M12 0C5.376 0 0 5.376 0 12s5.376 12 12 12 12-5.376 12-12S18.624 0 12 0zm0 19.104c-3.924 0-7.104-3.18-7.104-7.104S8.076 4.896 12 4.896s7.104 3.18 7.104 7.104-3.18 7.104-7.104 7.104zm0-13.332c-3.432 0-6.228 2.796-6.228 6.228S8.568 18.228 12 18.228s6.228-2.796 6.228-6.228S15.432 5.772 12 5.772zM9.684 15.54V8.46L15.816 12l-6.132 3.54z"
    static let bluetooth = "M12 0C6.76 0 3.1484 2.4895 3.1484 12S6.76 24 12 24c5.24 0 8.8516-2.4895 8.8516-12S17.24 0 12 0zm-.7773 1.6816l6.2148 6.2149L13.334 12l4.1035 4.1035-6.2148 6.2149V14.125l-3.418 3.42-1.2422-1.2442L10.8515 12l-4.289-4.3008 1.2422-1.2441 3.418 3.4199V1.6816zm1.748 4.2442v3.9687l1.9844-1.9843-1.9844-1.9844zm0 8.1816v3.9668l1.9844-1.9844-1.9844-1.9824Z"
    static let airplay = "M11.908.183a12.012 12.012 0 00-8.044 3.172c-4.882 4.475-5.166 12.08-.692 16.962.204.244.448.447.692.692a.315.315 0 00.408-.04l.53-.61a.32.32 0 000-.448C.53 15.965.243 9.253 4.23 4.982 8.217.711 14.889.427 19.16 4.414c4.271 3.986 4.555 10.655.568 14.927-.203.203-.365.407-.568.57a.32.32 0 000 .447l.53.611a.37.37 0 00.446.04c4.882-4.516 5.166-12.081.692-16.962a11.98 11.98 0 00-8.92-3.864zm.387 3.518A8.607 8.607 0 006.143 6c-3.458 3.213-3.66 8.623-.447 12.080.122.123.243.285.406.407a.319.319 0 00.447 0l.53-.61a.32.32 0 000-.446A7.263 7.263 0 014.8 12.183c0-3.946 3.212-7.160 7.158-7.160s7.160 3.253 7.160 7.199a7.207 7.207 0 01-2.238 5.209.319.319 0 000 .447l.529.61c.122.121.325.162.447.04a8.599 8.599 0 00.408-12.122 8.494 8.494 0 00-5.970-2.705zm-.266 3.316A5.198 5.198 0 008.34 8.48c-2.075 1.993-2.115 5.247-.122 7.322l.121.123a.319.319 0 00.447 0l.53-.611a.32.32 0 000-.448 3.814 3.814 0 01-1.098-2.683 3.732 3.732 0 013.742-3.742 3.732 3.732 0 013.742 3.742c0 1.017-.406 1.951-1.139 2.683a.32.32 0 000 .448l.53.61a.32.32 0 00.447 0c2.034-1.992 2.116-5.246.123-7.321a5.128 5.128 0 00-3.633-1.586zm.006 7.744a.599.599 0 00-.402.146l-.04.041-7.159 8.055a.506.506 0 00.041.69.437.437 0 00.283.124h14.36a.495.495 0 00.489-.488.463.463 0 00-.121-.326l-7.080-8.055a.5.5 0 00-.37-.187z"
    static let upnp = "M23.255 12.667H13.02c-1.052 0-2.1.489-2.693 1.266v-.017a3.24 3.24 0 01-2.629 1.353 3.25 3.25 0 010-6.502c1.085 0 2.04.536 2.630 1.353v-.013c.591.776 1.640 1.273 2.692 1.273h10.129c.186-.005.873-.095.848-.981-.884-5.086-5.880-8.987-11.923-8.987-3.722 0-7.048 1.480-9.263 3.803-.356.527.014.689.350.734H9.77c1.050 0 2.100-.498 2.692-1.277v.018a3.242 3.242 0 012.630-1.355 3.252 3.252 0 010 6.503 3.240 3.240 0 01-2.630-1.355v.019c-.592-.780-1.642-1.266-2.692-1.266H2.55l.028.003s-1.068-.06-1.719.859C.361 8.9 0 10.620 0 12.002c0 1.388.198 2.650.867 3.923.564.908 1.710.850 1.710.850l-.042.005h7.233c1.050 0 2.100-.490 2.692-1.268v.020a3.242 3.242 0 012.630-1.356 3.251 3.251 0 010 6.502 3.242 3.242 0 01-2.630-1.354v.018c-.592-.779-1.642-1.277-2.692-1.277H3.164c-.328.042-.698.198-.379.700 2.216 2.336 5.555 3.823 9.289 3.823 6.054 0 11.056-3.910 11.926-9.009-.004-.713-.489-.877-.745-.912z"

    /// Plex chevron (simple-icons)
    static let plex = "M11.643 0H4.68l7.679 12L4.68 24h6.963l7.677-12-7.677-12"

    static func style(_ label: String) -> SourceStyle {
        switch label {
        case "Radio": return SourceStyle(bg: AnyView(Color.accent), fg: .bg, stroke: "M4 9h16v11H4zM8 9l9-5M14 13h3M14 16h3", fillPath: "M9.5 12.5a2 2 0 1 0 0 4 2 2 0 0 0 0-4z", size: 0.47)
        case "AirPlay": return SourceStyle(bg: AnyView(CSSLinearGradient(angle: 160, stops: [.init(color: Color(hex: 0x3a3a3e), location: 0), .init(color: .bg, location: 1)])), fg: .white, brand: airplay, size: 0.48)
        case "Blåtann": return SourceStyle(bg: AnyView(Color(hex: 0x0082fc)), fg: .white, brand: bluetooth, size: 0.46)
        case "Spotify": return SourceStyle(bg: AnyView(Color.black), fg: Color(hex: 0x1ed760), brand: spotify, size: 1)
        case "YT Music", "YouTube Music": return SourceStyle(bg: AnyView(Color.white), fg: Color(hex: 0xff0000), brand: ytm, size: 1)
        case "UPnP/DLNA": return SourceStyle(bg: AnyView(Color.white), fg: .card2, brand: upnp, size: 0.6)
        case "AUX": return SourceStyle(bg: AnyView(Color.off), fg: .ink, stroke: "M12 2.5v3M9.5 5.5h5v4h-5zM10.8 9.5h2.4v8.2a1.2 1.2 0 0 1-2.4 0zM10.8 13h2.4", size: 0.47)
        case "Navidrome": return SourceStyle(bg: AnyView(NavidromeMark()), fg: .white, size: 0)
        case "USB": return SourceStyle(bg: AnyView(Color.seg), fg: .ink, stroke: "M12 3v15M8 9v2.5l4 3M16 8v3l-4 3", fillPath: "M12 2l-2 3h4zM12 18a1.6 1.6 0 1 0 0 3.2 1.6 1.6 0 0 0 0-3.2zM7 7.5h2v2H7zM16 6.5a1.1 1.1 0 1 0 0 2.2 1.1 1.1 0 0 0 0-2.2z", size: 0.5)
        case "Hodetelefoner": return SourceStyle(bg: AnyView(Color(hex: 0x2f2a40)), fg: .ink, stroke: "M4 15v-3a8 8 0 0 1 16 0v3M4 15a2 2 0 0 1 2-2h1v7H6a2 2 0 0 1-2-2zM20 15a2 2 0 0 0-2-2h-1v7h1a2 2 0 0 0 2-2z", size: 0.5)
        case "Plex": return SourceStyle(bg: AnyView(Color(hex: 0x1f1f1f)), fg: Color(hex: 0xe5a00d), brand: plex, size: 0.5)
        case "Lyrion": return SourceStyle(bg: AnyView(LyrionMark()), fg: .white, size: 0)
        default: return SourceStyle(bg: AnyView(Color.seg), fg: .ink, size: 0.47)
        }
    }
}

/// Fallback marks for the two brand PNGs that are not included in the hand-off (logo/brands/*.png).
private struct NavidromeMark: View {
    var body: some View {
        ZStack {
            Color.bg
            if UIImage(named: "brand-navidrome") != nil {
                Image("brand-navidrome").resizable().scaledToFill().scaleEffect(1.04)
            } else {
                Circle().fill(Color(hex: 0x0f62fe)).padding(12)
                Text("N").sora(22, .semibold, .white)
            }
        }
    }
}

private struct LyrionMark: View {
    var body: some View {
        ZStack {
            Color.bg
            if UIImage(named: "brand-lyrion") != nil {
                Image("brand-lyrion").resizable().scaledToFill()
            } else {
                Text("L").sora(24, .semibold, .ink)
            }
        }
    }
}

/// Small round source logo (same artwork as Kilder), for chips and rows.
struct SourceGlyph: View {
    let label: String
    var size: CGFloat = 24
    var body: some View {
        let s = SourceLogos.style(label)
        ZStack {
            s.bg
            if s.size > 0 {
                if !s.stroke.isEmpty { SKIcon(d: s.stroke, size: size * s.size, stroke: 2, color: s.fg) }
                if !s.fillPath.isEmpty { SKIcon(d: s.fillPath, size: size * s.size, color: s.fg, fill: true) }
                if !s.brand.isEmpty { SKIcon(d: s.brand, size: size * s.size, color: s.fg, fill: true) }
            }
        }
        .frame(width: size, height: size)
        .clipShape(Circle())
    }
}

struct SKSourceLogo: View {
    let label: String
    let action: () -> Void
    var body: some View {
        let s = SourceLogos.style(label)
        Button(action: action) {
            VStack(spacing: 6) {
                ZStack {
                    s.bg
                    if s.size > 0 {
                        ZStack {
                            if !s.stroke.isEmpty { SKIcon(d: s.stroke, size: 64 * s.size, stroke: 1.8, color: s.fg) }
                            if !s.fillPath.isEmpty { SKIcon(d: s.fillPath, size: 64 * s.size, color: s.fg, fill: true) }
                            if !s.brand.isEmpty { SKIcon(d: s.brand, size: 64 * s.size, color: s.fg, fill: true) }
                        }
                    }
                }
                .frame(width: 64, height: 64)
                .clipShape(Circle())
                Text(label).sora(11, .regular, .ink2).lineLimit(1).fixedSize()
            }
        }
        .plain()
    }
}

// MARK: - Logo text (5 bars + SKJOLD)

struct SKLogo: View {
    var barW: CGFloat = 2.5
    var gap: CGFloat = 2
    var size: CGFloat = 15
    var tracking: CGFloat = 1.8
    var bottomAligned = true
    var spacing: CGFloat = 9
    var body: some View {
        HStack(spacing: spacing) {
            HStack(alignment: bottomAligned ? .bottom : .top, spacing: gap) {
                ForEach(Array([8, 12, 16, 12, 8].enumerated()), id: \.offset) { _, h in
                    RoundedRectangle(cornerRadius: 2).fill(Color.ink).frame(width: barW, height: CGFloat(h))
                }
            }
            .frame(height: 16, alignment: bottomAligned ? .bottom : .top)
            Text("SKJOLD").sora(size, .semibold).tracking(tracking)
        }
    }
}

// MARK: - Tab bar

struct SKTabBar: View {
    let selected: Int
    let pick: (Int) -> Void

    private let items: [(String, String)] = [(Icons.tabHome, "Hjem"), (Icons.tabSound, "Lyd"), (Icons.tabRooms, "Rom"), (Icons.tabSettings, "Innstillinger")]

    var body: some View {
        HStack(spacing: 0) {
            ForEach(Array(items.enumerated()), id: \.offset) { i, it in
                let on = i == selected
                Button { if i != selected { Haptics.tick() }; pick(i) } label: {
                    VStack(spacing: 4) {
                        SKIcon(d: it.0, size: 22, stroke: 1.8)
                            .frame(width: 30, height: 30)
                        Text(it.1).sora(10.5, on ? .semibold : .regular, on ? .accent2 : .muted).lineLimit(1).fixedSize()
                    }
                    .foregroundStyle(on ? Color.accent2 : Color.muted)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                }
                .plain()
            }
        }
        .padding(.horizontal, 6)
        .padding(.top, 4)
        .frame(height: 70)
        .frame(maxWidth: .infinity)
        .background(alignment: .top) {
            ZStack {
                Rectangle().fill(.ultraThinMaterial)
                Color(.sRGB, red: 18 / 255, green: 18 / 255, blue: 19 / 255, opacity: 0.94)
            }
            .ignoresSafeArea(edges: .bottom)
        }
        .overlay(alignment: .top) { Rectangle().fill(Color(hex: 0x232325)).frame(height: 1) }
    }
}

// MARK: - Mini player

struct SKMiniPlayer: View {
    @Environment(AppModel.self) private var m
    /// Liquid Glass variant: floating, no border, rounder corners.
    var glass = false

    var body: some View {
        let np = m.np
        HStack(spacing: 10) {
            Button { m.full = true } label: {
                ArtFill(m.playerArt.key).frame(width: 44, height: 44).clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
            }
            .plain()
            Button { m.full = true } label: {
                VStack(alignment: .leading, spacing: 1) {
                    Text("\(m.groupName) · \(m.actModel)").mono(9.5).lineLimit(1)
                    Text(np.t).sora(13, .semibold).lineLimit(1)
                    Text(np.s).sora(11, .regular, .muted).lineLimit(1)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .plain()
            HStack(spacing: 2) {
                Button { m.prev() } label: {
                    SKIcon(d: Icons.prev, size: 18, color: .ink, fill: true).frame(width: 34, height: 40)
                }
                .plain()
                .accessibilityLabel("Forrige")
                Button { m.togglePlay() } label: {
                    SKIcon(d: m.playing ? Icons.pause : Icons.playRound, size: 18, color: .ink, fill: true)
                        .frame(width: 38, height: 38)
                        .background(Circle().fill(Color.ink.opacity(0.1)))
                }
                .plain()
                .accessibilityLabel(m.playing ? "Pause" : "Spill")
                Button { m.next() } label: {
                    SKIcon(d: Icons.next, size: 18, color: .ink, fill: true).frame(width: 34, height: 40)
                }
                .plain()
                .accessibilityLabel("Neste")
            }
        }
        .padding(8)
        .background {
            if !glass { RoundedRectangle(cornerRadius: 14, style: .continuous).fill(Color(hex: 0x1b1b1d)) }
        }
        .overlay(alignment: .bottom) {
            // thin progress line along the bottom edge (radio shows a live marker instead)
            GeometryReader { g in
                let frac = m.hasProgress ? CGFloat(m.position) / CGFloat(max(1, m.duration)) : 1
                ZStack(alignment: .leading) {
                    Capsule().fill(Color.ink.opacity(0.1))
                    Capsule().fill(m.input == 3 ? Color.live.opacity(0.8) : Color.accent).frame(width: g.size.width * frac)
                }
            }
            .frame(height: 2)
            .padding(.horizontal, glass ? 22 : 14)
            .padding(.bottom, glass ? 2 : 1)
        }
        .if(!glass) { $0.skBorder(Color(hex: 0x2a2a2c), radius: 14) }
        .if(glass) { $0.padding(.horizontal, 4).glassEffect(.regular.tint(Color.bg.opacity(0.55)).interactive(), in: .rect(cornerRadius: 24, style: .continuous)) }
        .contentShape(Rectangle())
        .gesture(DragGesture(minimumDistance: 15).onEnded { v in
            if v.translation.height < -30 { Haptics.thump(); m.full = true }   // swipe up opens the player
        })
        .padding(.horizontal, glass ? 0 : 10)
        .padding(.bottom, glass ? 0 : 8)
    }
}

// MARK: - Sheet (drag down to close)

struct SKSheet<Content: View>: View {
    let onClose: () -> Void
    @ViewBuilder var content: Content
    @State private var drag: CGFloat = 0

    var body: some View {
        // the content draws its own rounded background, so it can extend under the home indicator
        content
            .offset(y: drag)
            .simultaneousGesture(
                // Global coordinates: local ones move with the offset and cancel the drag out.
                DragGesture(minimumDistance: 10, coordinateSpace: .global)
                    .onChanged { v in
                        if v.translation.height > abs(v.translation.width) || drag > 0 {
                            let new = max(0, v.translation.height)
                            // bump when crossing the close threshold (both ways)
                            if (drag <= 90) != (new <= 90) { Haptics.bump() }
                            drag = new
                        }
                    }
                    .onEnded { v in
                        if drag > 90 || (drag > 20 && v.predictedEndTranslation.height > 260) {
                            onClose()
                            // let the slide-out transition take over from the current position
                            DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) { drag = 0 }
                        } else {
                            withAnimation(.spring(response: 0.3, dampingFraction: 0.85)) { drag = 0 }
                        }
                    }
            )
    }
}
