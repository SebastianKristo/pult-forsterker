import SwiftUI
import UIKit

/// Farger og fonter fra appens Theme.swift (utvidelsen kompilerer ikke appens filer, bare Skjold/Shared).
enum W {
    static let bg      = Color(red: 0x0b / 255.0, green: 0x0b / 255.0, blue: 0x0c / 255.0)
    static let card    = Color(red: 0x14 / 255.0, green: 0x14 / 255.0, blue: 0x15 / 255.0)
    static let card2   = Color(red: 0x1b / 255.0, green: 0x1b / 255.0, blue: 0x1c / 255.0)
    static let line    = Color(red: 0x2e / 255.0, green: 0x2e / 255.0, blue: 0x30 / 255.0)
    static let ink     = Color(red: 0xf2 / 255.0, green: 0xf2 / 255.0, blue: 0xee / 255.0)
    static let ink2    = Color(red: 0xc9 / 255.0, green: 0xc9 / 255.0, blue: 0xc4 / 255.0)
    static let muted   = Color(red: 0x8b / 255.0, green: 0x8b / 255.0, blue: 0x86 / 255.0)
    static let accent  = Color(red: 0xd9 / 255.0, green: 0xa4 / 255.0, blue: 0x41 / 255.0)
    static let accent2 = Color(red: 0xf0 / 255.0, green: 0xc4 / 255.0, blue: 0x6a / 255.0)
    static let selBg   = Color(red: 0x1c / 255.0, green: 0x17 / 255.0, blue: 0x0d / 255.0)

    static func sora(_ size: CGFloat, _ semibold: Bool = false) -> Font {
        .custom(semibold ? "Sora-SemiBold" : "Sora-Regular", size: size)
    }
    static func mono(_ size: CGFloat) -> Font { .custom("IBMPlexMono-Medium", size: size) }

    /// Fargeforløp når det ikke finnes omslag (samme idé som appens art()).
    static func gradient(for key: String) -> LinearGradient {
        var h = 0
        for u in key.unicodeScalars { h = (h * 31 + Int(u.value)) % 360 }
        let hue = Double(h) / 360
        let a = Color(hue: hue, saturation: 0.55, brightness: 0.45)
        let b = Color(hue: hue, saturation: 0.45, brightness: 0.16)
        return LinearGradient(colors: [a, b], startPoint: .topLeading, endPoint: .bottomTrailing)
    }
}

/// Omslag fra den delte containeren, ellers fargeforløp med første bokstav.
struct WCover: View {
    let state: SharedNowPlaying
    var size: CGFloat
    var radius: CGFloat = 12

    var body: some View {
        ZStack {
            if let img = Self.image(state) {
                Image(uiImage: img).resizable().scaledToFill()
            } else {
                Rectangle().fill(W.gradient(for: state.title))
                Text(String(state.title.prefix(1)))
                    .font(W.sora(size * 0.4, true))
                    .foregroundStyle(W.ink.opacity(0.85))
            }
        }
        .frame(width: size, height: size)
        .clipShape(RoundedRectangle(cornerRadius: radius, style: .continuous))
    }

    static func image(_ s: SharedNowPlaying) -> UIImage? {
        guard s.hasCover else { return nil }
        if let img = SkjoldShared.coverImage(key: s.coverKey) { return img }
        guard let f = SkjoldShared.coverFile else { return nil }
        return UIImage(contentsOfFile: f.path)
    }
}

/// Rund knapp for widgets og Live Activity.
struct WRoundIcon: View {
    let symbol: String
    var size: CGFloat = 34
    var filled = false

    var body: some View {
        Image(systemName: symbol)
            .font(.system(size: size * 0.42, weight: .semibold))
            .foregroundStyle(filled ? W.bg : W.ink)
            .frame(width: size, height: size)
            .background(Circle().fill(filled ? W.ink : W.card2))
    }
}
