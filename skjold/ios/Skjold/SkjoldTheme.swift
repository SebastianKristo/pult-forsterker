import SwiftUI

/// Design-tokens fra «Skjold App v4» (platform=ios): objektene G, L og P i renderVals().
/// 1 CSS-px i designet = 1 pt. iOS bruker glass (Liquid Glass) der designet har blur/gradient-flater.
enum SkG {
    // Typografi
    static let titleSize: CGFloat = 32          // sidetitler og hjemmets navn: 32/600
    static let titleTracking: CGFloat = -0.64   // letter-spacing −0.02em ved 32 px
    static let shelfTitle: CGFloat = 17         // «Nylig spilt ›», «Radiofavoritter ›»: 17/600

    // Dokk og minispiller (G.dock*, G.mini*)
    static let dockSide: CGFloat = 10
    static let dockBottom: CGFloat = 28
    static let miniRadius: CGFloat = 26

    // Ark og menyer (G.menuR, G.moreR, G.moreS)
    static let menuRadius: CGFloat = 22
    static let moreRadius: CGFloat = 34
    static let moreInset: CGFloat = 8
    static let menuBg = Color(.sRGB, red: 44 / 255, green: 44 / 255, blue: 48 / 255, opacity: 0.78)
    static let dim = Color(.sRGB, red: 5 / 255, green: 5 / 255, blue: 6 / 255, opacity: 0.6)

    // Hyller (Hjem)
    static let sourceIcon: CGFloat = 68         // runde kildeikoner
    static let radioTile: CGFloat = 112         // radiofavoritter 112 × 112, radius 16
    static let tileRadius: CGFloat = 16

    // Sidemarg og iPad-oppsett (L.px, L.railW)
    static let padPhone: CGFloat = 20
    static let padPad: CGFloat = 40
    static let padMaxWidth: CGFloat = 860        // innhold på iPad holdes lesbart

    // Valgt fane (tabs.bg / fg)
    static let tabOnBg = Color(.sRGB, red: 240 / 255, green: 196 / 255, blue: 106 / 255, opacity: 0.16)
}

extension View {
    /// Glassflate (Liquid Glass) med designets radius.
    func skGlass(_ radius: CGFloat, interactive: Bool = false) -> some View {
        glassEffect(interactive ? Glass.regular.interactive() : Glass.regular,
                    in: RoundedRectangle(cornerRadius: radius, style: .continuous))
    }
}
