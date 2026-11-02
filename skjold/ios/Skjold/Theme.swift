import SwiftUI
import UIKit

// MARK: - Design tokens (XCODE_BYGG.md)

extension Color {
    init(hex: UInt32, alpha: Double = 1) {
        self.init(.sRGB,
                  red: Double((hex >> 16) & 0xff) / 255,
                  green: Double((hex >> 8) & 0xff) / 255,
                  blue: Double(hex & 0xff) / 255,
                  opacity: alpha)
    }

    static let bg      = Color(hex: 0x0b0b0c)
    static let card    = Color(hex: 0x141415)
    static let card2   = Color(hex: 0x1b1b1c)
    static let line    = Color(hex: 0x242426)
    static let line2   = Color(hex: 0x2e2e30)
    static let ink     = Color(hex: 0xf2f2ee)
    static let ink2    = Color(hex: 0xc9c9c4)
    static let muted   = Color(hex: 0x8b8b86)
    static let accent  = Color(hex: 0xd9a441)
    static let accent2 = Color(hex: 0xf0c46a)
    static let selBg   = Color(hex: 0x1c170d)
    static let selLine = Color(hex: 0x5a4420)
    static let ok      = Color(hex: 0x6fcf7f)
    static let live    = Color(hex: 0xe05a4a)
    static let off     = Color(hex: 0x3a3a37)

    // Further colours that appear in the design file
    static let body    = Color(hex: 0xa9a9a3)   // paragraph text
    static let dim     = Color(hex: 0x55554f)   // placeholders / disabled
    static let seg     = Color(hex: 0x2a2a2c)   // selected segment
    static let selBg2  = Color(hex: 0x2a2112)   // selected chip (darker gold)
    static let danger  = Color(hex: 0xff8a7a)
    static let dots    = Color(hex: 0x2a2a28)   // inactive progress step
}

/// Colours for the shared "selected" state (sel() in the design file).
struct SelStyle {
    let bd: Color, bg: Color, fg: Color
    static func of(_ on: Bool) -> SelStyle {
        on ? SelStyle(bd: .accent, bg: .selBg, fg: .accent2) : SelStyle(bd: .line2, bg: .card, fg: .ink)
    }
}

// MARK: - Fonts

extension Font {
    /// Sora in the three weights the design ships (300/400/600). 700 in the design maps to 600.
    static func sora(_ size: CGFloat, _ weight: Font.Weight = .regular) -> Font {
        .custom(soraName(weight), fixedSize: size)
    }

    static func plexMono(_ size: CGFloat, _ weight: Font.Weight = .regular) -> Font {
        .custom(weight == .medium || weight == .semibold || weight == .bold ? "IBMPlexMono-Medium" : "IBMPlexMono-Regular", fixedSize: size)
    }

    static func soraName(_ weight: Font.Weight) -> String {
        switch weight {
        case .light, .thin, .ultraLight: return "Sora-Light"
        case .semibold, .bold, .heavy, .black: return "Sora-SemiBold"
        default: return "Sora-Regular"
        }
    }
}

extension View {
    /// Sora text with an optional CSS line-height multiplier (adds the missing line spacing).
    func sora(_ size: CGFloat, _ weight: Font.Weight = .regular, _ color: Color? = nil, lineHeight: CGFloat? = nil) -> some View {
        let natural = UIFont(name: Font.soraName(weight), size: size)?.lineHeight ?? size * 1.26
        let spacing = lineHeight.map { max(0, size * $0 - natural) } ?? 0
        return self.font(.sora(size, weight)).foregroundStyle(color ?? .ink).lineSpacing(spacing)
    }

    /// IBM Plex Mono label, letter-spacing given in em like the CSS.
    func mono(_ size: CGFloat, _ color: Color = .muted, em: CGFloat = 0, weight: Font.Weight = .regular) -> some View {
        self.font(.plexMono(size, weight)).tracking(size * em).foregroundStyle(color)
    }

    /// 1 pt border on a rounded rectangle, drawn inside like CSS box-sizing.
    func skBorder(_ color: Color, radius: CGFloat, width: CGFloat = 1, dash: [CGFloat] = []) -> some View {
        overlay(RoundedRectangle(cornerRadius: radius, style: .continuous)
            .strokeBorder(color, style: StrokeStyle(lineWidth: width, dash: dash)))
    }

    func skCapsuleBorder(_ color: Color, width: CGFloat = 1) -> some View {
        overlay(Capsule().strokeBorder(color, lineWidth: width))
    }

    /// Card: background + border + radius.
    func skBox(_ bg: Color, _ bd: Color, radius: CGFloat = 14) -> some View {
        background(RoundedRectangle(cornerRadius: radius, style: .continuous).fill(bg))
            .skBorder(bd, radius: radius)
            .clipShape(RoundedRectangle(cornerRadius: radius, style: .continuous))
    }

    @ViewBuilder func `if`<V: View>(_ cond: Bool, _ transform: (Self) -> V) -> some View {
        if cond { transform(self) } else { self }
    }
}

/// Plain button style without the default highlight, so buttons look exactly like the design.
struct PlainPress: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .contentShape(Rectangle())
            .opacity(configuration.isPressed ? 0.75 : 1)
            // light tap on touch-down for every button in the app
            .onChange(of: configuration.isPressed) { _, pressed in if pressed { Haptics.tap() } }
    }
}

extension Button {
    func plain() -> some View { buttonStyle(PlainPress()) }
}

// MARK: - OKLCH (used by the generated cover art)

nonisolated enum OKLCH {
    struct Lab { var L: Double, a: Double, b: Double }

    static func lab(_ L: Double, _ C: Double, _ h: Double) -> Lab {
        let r = h * .pi / 180
        return Lab(L: L, a: C * cos(r), b: C * sin(r))
    }

    static func color(_ lab: Lab) -> Color {
        let l_ = lab.L + 0.3963377774 * lab.a + 0.2158037573 * lab.b
        let m_ = lab.L - 0.1055613458 * lab.a - 0.0638541728 * lab.b
        let s_ = lab.L - 0.0894841775 * lab.a - 1.2914855480 * lab.b
        let l = l_ * l_ * l_, m = m_ * m_ * m_, s = s_ * s_ * s_
        let r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
        let g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
        let b = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
        func enc(_ x: Double) -> Double {
            let v = max(0, min(1, x))
            return v <= 0.0031308 ? 12.92 * v : 1.055 * pow(v, 1 / 2.4) - 0.055
        }
        return Color(.sRGB, red: enc(r), green: enc(g), blue: enc(b), opacity: 1)
    }

    static func color(_ L: Double, _ C: Double, _ h: Double) -> Color { color(lab(L, C, h)) }

    /// CSS interpolates oklch gradients in Oklab; approximate with extra stops.
    static func stops(from a: Lab, to b: Lab, count: Int = 6) -> [Gradient.Stop] {
        (0...count).map { i in
            let t = Double(i) / Double(count)
            let c = Lab(L: a.L + (b.L - a.L) * t, a: a.a + (b.a - a.a) * t, b: a.b + (b.b - a.b) * t)
            return Gradient.Stop(color: color(c), location: t)
        }
    }
}

/// CSS `linear-gradient(<angle>deg, …)` that keeps the correct angle for any frame size.
struct CSSLinearGradient: View {
    let angle: Double
    let stops: [Gradient.Stop]

    var body: some View {
        GeometryReader { g in
            let w = max(g.size.width, 1), h = max(g.size.height, 1)
            let a = angle * .pi / 180
            let dx = sin(a), dy = -cos(a)
            let len = abs(w * sin(a)) + abs(h * cos(a))
            let start = UnitPoint(x: 0.5 - dx * len / 2 / w, y: 0.5 - dy * len / 2 / h)
            let end = UnitPoint(x: 0.5 + dx * len / 2 / w, y: 0.5 + dy * len / 2 / h)
            LinearGradient(stops: stops, startPoint: start, endPoint: end)
        }
    }
}
