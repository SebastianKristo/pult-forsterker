import SwiftUI

/// 01 Velkomst: logo, slowly rotating product renders, intro text and «Kom i gang».
struct WelcomeView: View {
    @Environment(AppModel.self) private var m

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            SKLogo(barW: 3, gap: 3, size: 14, tracking: 3, bottomAligned: false, spacing: 10)
                .padding(.top, 4)
            HeroCarousel().frame(height: 250)
            VStack(alignment: .leading, spacing: 10) {
                SKMonoLabel(text: "VELKOMMEN")
                Text("Musikk i hvert rom").sora(28, .semibold, lineHeight: 1.15)
                Text("Appen styrer Skjold S1 og Skjold Node. Velg kilde, juster lyden og samle rommene til ett system.")
                    .sora(13, .regular, .body, lineHeight: 1.5)
                    .fixedSize(horizontal: false, vertical: true)
            }
            Spacer(minLength: 0)
            SKButton(title: "Legg til Skjold-enhet") { m.welcome = false }
            SKLinkButton(title: "Hopp over og gå til appen") { m.skipSetup() }
                .frame(maxWidth: .infinity)
                .padding(.top, 2)
        }
        .padding(.top, 8).padding(.horizontal, 20).padding(.bottom, 18)
    }
}

/// heroView(): four renders that cross-fade and drift, with label and page dots.
struct HeroCarousel: View {
    @Environment(AppModel.self) private var m

    static let slides: [(img: String, name: String, sub: String)] = [
        ("hero-01-s1", "Skjold S1", "Forsterker med skjerm og knapper"),
        ("hero-03-s1", "Skjold S1", "Forsterker med skjerm og knapper"),
        ("hero-02-node", "Skjold Node", "Liten spiller for flere rom"),
        ("hero-04-node", "Skjold Node", "Liten spiller for flere rom")
    ]

    var body: some View {
        let i = m.heroI % Self.slides.count, cur = Self.slides[i]
        GeometryReader { g in
            let w = g.size.width, h = g.size.height
            ZStack(alignment: .topLeading) {
                // warm glow behind the product
                EllipticalGradient(stops: [.init(color: Color.accent.opacity(0.16), location: 0),
                                           .init(color: Color.accent.opacity(0.04), location: 0.6),
                                           .init(color: .clear, location: 1)],
                                   center: .center, startRadiusFraction: 0, endRadiusFraction: 0.5)
                    .frame(width: w * 1.2, height: h * 0.78)
                    .offset(x: -w * 0.1, y: h * 0.08)
                // floor shadow
                EllipticalGradient(colors: [Color.black.opacity(0.9), .clear], center: .center, startRadiusFraction: 0, endRadiusFraction: 0.5)
                    .frame(width: w * 0.64, height: 18)
                    .offset(x: w * 0.18, y: h * 0.83 - 18)
                ForEach(Array(Self.slides.enumerated()), id: \.offset) { j, s in
                    slide(s.img, j: j, w: w)
                        .opacity(j == i ? 1 : 0)
                        .offset(x: j == i ? 0 : (j < i ? -14 : 14))
                        .scaleEffect(j == i ? 1 : 0.97)
                        .animation(.easeInOut(duration: 0.9), value: i)
                }
                HStack(alignment: .center, spacing: 12) {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(cur.name).sora(14, .semibold)
                        Text(cur.sub).sora(12, .regular, .muted)
                    }
                    Spacer(minLength: 0)
                    HStack(spacing: 5) {
                        ForEach(0..<Self.slides.count, id: \.self) { j in
                            Button { m.restartHero(j) } label: {
                                Capsule().fill(j == i ? Color.accent : .off).frame(width: j == i ? 18 : 6, height: 6)
                            }
                            .plain()
                            .accessibilityLabel("Bilde \(j + 1)")
                        }
                    }
                    .animation(.easeInOut(duration: 0.3), value: i)
                }
                .frame(width: w, height: h, alignment: .bottom)
            }
        }
    }

    /// Uses the render from renders/cut when it is in the asset catalog; otherwise the S1 render cut from the
    /// design screenshot, or the Node outline.
    @ViewBuilder private func slide(_ name: String, j: Int, w: CGFloat) -> some View {
        if UIImage(named: name) != nil {
            Image(name).resizable().scaledToFit()
                .frame(width: w * 1.12).offset(x: -w * 0.06, y: -250 * 0.08)
                .shadow(color: .white.opacity(0.18), radius: 0.5)
        } else if name.contains("s1") {
            Image("hero-s1").resizable().scaledToFit()
                .frame(width: w * 230 / 330)
                .offset(x: w * 103.3 / 330, y: -6)
                .blendMode(.lighten)
        } else {
            SKIcon(d: SK.dev("node").icon, size: 150, stroke: 0.5, color: .ink2)
                .frame(width: w, height: 200)
        }
    }
}

#Preview {
    let m = AppModel()
    m.intro = false
    return WelcomeView().environment(m).background(Color.bg)
}
