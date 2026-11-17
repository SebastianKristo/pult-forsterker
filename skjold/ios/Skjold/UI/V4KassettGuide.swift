import SwiftUI

/// Illustrasjonene i «Lag kassett»-veiviseren: tegnet med SwiftUI-figurer og animert med TimelineView, så de er skarpe
/// på alle skjermer og ikke trenger bildefiler. Hver animasjon går i en løkke og viser ett grep: hold telefonen mot
/// kassetten, sett kassetten i spilleren, lim på etiketten, ferdig.

// MARK: - Kassetten

struct KassettFigur: View {
    var etikett: String = ""
    var under: String = ""
    var spinn: Double = 0          // spolene roterer (grader)
    var etikettPaa: Double = 1     // 0 = ingen etikett, 1 = etiketten sitter
    var glod: Double = 0           // lysring rundt kassetten (NFC-kontakt)

    var body: some View {
        GeometryReader { g in
            let w = g.size.width, h = g.size.height
            ZStack {
                // kropp
                RoundedRectangle(cornerRadius: w * 0.06, style: .continuous)
                    .fill(LinearGradient(colors: [Color(hex: 0x2c2c30), Color(hex: 0x19191b)], startPoint: .top, endPoint: .bottom))
                RoundedRectangle(cornerRadius: w * 0.06, style: .continuous)
                    .strokeBorder(Color.white.opacity(0.12), lineWidth: 1)
                // forsenkningen der etiketten limes
                RoundedRectangle(cornerRadius: w * 0.035, style: .continuous)
                    .fill(Color.black.opacity(0.35))
                    .frame(width: w * 0.84, height: h * 0.58)
                    .position(x: w / 2, y: h * 0.38)
                // etiketten
                etikettFlate(w: w, h: h)
                    .frame(width: w * 0.84, height: h * 0.58)
                    .position(x: w / 2, y: h * 0.38 - (1 - etikettPaa) * h * 0.9)
                    .opacity(etikettPaa)
                // vinduet med spolene
                RoundedRectangle(cornerRadius: h * 0.08, style: .continuous)
                    .fill(Color(hex: 0x0d0d0e))
                    .overlay(RoundedRectangle(cornerRadius: h * 0.08, style: .continuous).strokeBorder(Color.white.opacity(0.1), lineWidth: 1))
                    .frame(width: w * 0.5, height: h * 0.2)
                    .position(x: w / 2, y: h * 0.42)
                spole(r: h * 0.075).position(x: w * 0.36, y: h * 0.42)
                spole(r: h * 0.075).position(x: w * 0.64, y: h * 0.42)
                // trapesen nederst med skruehull
                KassettBunn()
                    .fill(Color(hex: 0x242427))
                    .overlay(KassettBunn().stroke(Color.white.opacity(0.08), lineWidth: 1))
                    .frame(width: w * 0.62, height: h * 0.2)
                    .position(x: w / 2, y: h * 0.88)
                ForEach([0.12, 0.88], id: \.self) { x in
                    Circle().fill(Color.black.opacity(0.5)).frame(width: w * 0.035).position(x: w * x, y: h * 0.1)
                }
            }
            .shadow(color: V4.gold.opacity(0.55 * glod), radius: 18 * glod)
        }
        .aspectRatio(1.58, contentMode: .fit)
        .accessibilityHidden(true)
    }

    private func spole(r: CGFloat) -> some View {
        ZStack {
            Circle().fill(Color(hex: 0xe9e4d8)).frame(width: r * 2, height: r * 2)
            ForEach(0..<6) { i in
                Capsule().fill(Color(hex: 0x1a1a1a)).frame(width: r * 0.26, height: r * 0.62)
                    .offset(y: -r * 0.5).rotationEffect(.degrees(Double(i) * 60))
            }
            Circle().fill(Color(hex: 0x1a1a1a)).frame(width: r * 0.55, height: r * 0.55)
        }
        .rotationEffect(.degrees(spinn))
    }

    private func etikettFlate(w: CGFloat, h: CGFloat) -> some View {
        ZStack(alignment: .topLeading) {
            RoundedRectangle(cornerRadius: w * 0.03, style: .continuous)
                .fill(LinearGradient(colors: [Color(hex: 0xf3ead6), Color(hex: 0xe4d6b8)], startPoint: .top, endPoint: .bottom))
            VStack(spacing: 0) {
                Rectangle().fill(V4.goldDark).frame(height: h * 0.05)
                Spacer()
                Rectangle().fill(Color(hex: 0xc94f3d)).frame(height: h * 0.03)
            }
            .clipShape(RoundedRectangle(cornerRadius: w * 0.03, style: .continuous))
            VStack(alignment: .leading, spacing: 1) {
                Text(etikett.isEmpty ? "Skjold" : etikett)
                    .font(.custom("Sora-SemiBold", size: max(8, h * 0.085))).foregroundStyle(Color(hex: 0x1d1a14))
                    .lineLimit(1).minimumScaleFactor(0.5)
                if !under.isEmpty {
                    Text(under).font(.custom("Sora-Regular", size: max(6, h * 0.055))).foregroundStyle(Color(hex: 0x5b5244)).lineLimit(1)
                }
            }
            .padding(.horizontal, w * 0.04).padding(.top, h * 0.08)
        }
    }
}

private struct KassettBunn: Shape {
    func path(in r: CGRect) -> Path {
        var p = Path()
        p.move(to: CGPoint(x: r.minX + r.width * 0.1, y: r.minY))
        p.addLine(to: CGPoint(x: r.maxX - r.width * 0.1, y: r.minY))
        p.addLine(to: CGPoint(x: r.maxX, y: r.maxY))
        p.addLine(to: CGPoint(x: r.minX, y: r.maxY))
        p.closeSubpath()
        return p
    }
}

// MARK: - Telefonen

private struct TelefonFigur: View {
    var skjerm: Color = Color(hex: 0x111114)
    var body: some View {
        GeometryReader { g in
            let w = g.size.width
            ZStack(alignment: .top) {
                RoundedRectangle(cornerRadius: w * 0.2, style: .continuous).fill(Color(hex: 0x3a3a3e))
                RoundedRectangle(cornerRadius: w * 0.17, style: .continuous).fill(skjerm).padding(w * 0.045)
                Capsule().fill(Color.black).frame(width: w * 0.32, height: w * 0.09).padding(.top, w * 0.1)
            }
        }
        .aspectRatio(0.49, contentMode: .fit)
    }
}

/// Bølger som sendes ut fra et punkt (NFC).
private struct NFCBolger: View {
    let t: Double   // 0…1 i syklusen
    var body: some View {
        ZStack {
            ForEach(0..<3) { i in
                let f = (t + Double(i) / 3).truncatingRemainder(dividingBy: 1)
                Circle().strokeBorder(V4.gold.opacity((1 - f) * 0.8), lineWidth: 2)
                    .frame(width: 20 + f * 90, height: 20 + f * 90)
            }
        }
    }
}

// MARK: - Animasjonene

/// «Hold toppen av iPhone mot kassetten»: telefonen senkes mot kassetten, bølger, kassetten lyser.
struct KassettNFCAnimasjon: View {
    var etikett = ""
    var body: some View {
        TimelineView(.animation) { ctx in
            let s = ctx.date.timeIntervalSinceReferenceDate
            let t = (s / 3.4).truncatingRemainder(dividingBy: 1)
            let ned = ease(clamp((t - 0.05) / 0.35))              // telefonen kommer ned
            let opp = ease(clamp((t - 0.8) / 0.18))               // og løftes igjen
            let pos = ned - opp
            let kontakt = clamp((t - 0.4) / 0.08) * (1 - clamp((t - 0.78) / 0.06))
            ZStack {
                KassettFigur(etikett: etikett, spinn: 0, etikettPaa: 1, glod: kontakt)
                    .frame(width: 200)
                    .offset(y: 50)
                if kontakt > 0.01 { NFCBolger(t: (s / 1.1).truncatingRemainder(dividingBy: 1)).offset(y: 4).opacity(kontakt) }
                TelefonFigur(skjerm: kontakt > 0.5 ? Color(hex: 0x1d1709) : Color(hex: 0x111114))
                    .frame(width: 78)
                    .rotationEffect(.degrees(180))          // toppen av telefonen ned mot kassetten
                    .offset(y: -150 + pos * 115)
                    .shadow(color: .black.opacity(0.5), radius: 14, y: 8)
            }
            .frame(height: 260)
            .frame(maxWidth: .infinity)
        }
        .accessibilityLabel("Animasjon: hold toppen av telefonen mot kassetten")
    }
}

/// «Sett kassetten inn i spilleren»: kassetten glir ned i luka på Skjold Kassett, lampen blir grønn.
struct KassettSpillerAnimasjon: View {
    var etikett = ""
    var body: some View {
        TimelineView(.animation) { ctx in
            let s = ctx.date.timeIntervalSinceReferenceDate
            let t = (s / 3.6).truncatingRemainder(dividingBy: 1)
            let inn = ease(clamp((t - 0.08) / 0.4)) - ease(clamp((t - 0.86) / 0.12))
            let lest = clamp((t - 0.5) / 0.05) * (1 - clamp((t - 0.84) / 0.04))
            ZStack(alignment: .top) {
                KassettFigur(etikett: etikett, spinn: s * 160 * lest)
                    .frame(width: 170)
                    .offset(y: 0 + inn * 96)
                // spilleren foran kassetten (luka skjuler den nederste delen)
                ZStack(alignment: .top) {
                    RoundedRectangle(cornerRadius: 22, style: .continuous)
                        .fill(LinearGradient(colors: [Color(hex: 0x2a2a2e), Color(hex: 0x161618)], startPoint: .top, endPoint: .bottom))
                        .overlay(RoundedRectangle(cornerRadius: 22, style: .continuous).strokeBorder(Color.white.opacity(0.12), lineWidth: 1))
                    Capsule().fill(Color.black).frame(width: 190, height: 10).padding(.top, 14)
                    HStack(spacing: 8) {
                        Circle().fill(lest > 0.5 ? V4.green : Color(hex: 0x3a3a3c)).frame(width: 8, height: 8)
                            .shadow(color: V4.green.opacity(lest), radius: 6)
                        Text(lest > 0.5 ? "LEST" : "SKJOLD KASSETT").mono(9, V4.muted, em: 0.16)
                    }
                    .padding(.top, 54)
                }
                .frame(width: 230, height: 96)
                .offset(y: 150)
            }
            .frame(height: 260)
            .frame(maxWidth: .infinity)
            .clipped()
        }
        .accessibilityLabel("Animasjon: sett kassetten inn i Skjold Kassett-spilleren")
    }
}

/// «Lim etiketten i forsenkningen»: etiketten senkes ned på kassetten og trykkes fast.
struct KassettEtikettAnimasjon: View {
    var etikett = ""
    var under = ""
    var body: some View {
        TimelineView(.animation) { ctx in
            let s = ctx.date.timeIntervalSinceReferenceDate
            let t = (s / 3.2).truncatingRemainder(dividingBy: 1)
            let paa = ease(clamp((t - 0.1) / 0.45))
            let ut = clamp((t - 0.9) / 0.1)
            KassettFigur(etikett: etikett, under: under, spinn: 0, etikettPaa: paa * (1 - ut))
                .frame(width: 210)
                .scaleEffect(1 + 0.03 * sin(clamp((t - 0.55) / 0.12) * .pi))
                .frame(height: 170)
                .frame(maxWidth: .infinity)
        }
        .accessibilityLabel("Animasjon: lim etiketten i forsenkningen på kassetten")
    }
}

/// Kassetten med etiketten som spiller (spolene går): forsiden av veiviseren.
struct KassettHelt: View {
    var etikett = "Skjold"
    var under = ""
    var body: some View {
        TimelineView(.animation) { ctx in
            let s = ctx.date.timeIntervalSinceReferenceDate
            KassettFigur(etikett: etikett, under: under, spinn: s * 90)
                .frame(width: 230)
                .rotation3DEffect(.degrees(sin(s / 2.2) * 7), axis: (x: 0.2, y: 1, z: 0), perspective: 0.6)
                .offset(y: sin(s / 1.7) * 4)
                .frame(maxWidth: .infinity)
        }
    }
}

/// Grønn hake som tegnes opp (ferdig).
struct KassettFerdigHake: View {
    @State private var vis = false
    var body: some View {
        ZStack {
            Circle().fill(V4.green.opacity(0.14)).frame(width: 96, height: 96)
                .scaleEffect(vis ? 1 : 0.6)
            Circle().trim(from: 0, to: vis ? 1 : 0).stroke(V4.green, style: StrokeStyle(lineWidth: 4, lineCap: .round))
                .rotationEffect(.degrees(-90)).frame(width: 84, height: 84)
            HakePath().trim(from: 0, to: vis ? 1 : 0).stroke(V4.green, style: StrokeStyle(lineWidth: 6, lineCap: .round, lineJoin: .round))
                .frame(width: 40, height: 30)
        }
        .onAppear {
            Haptics.success()
            withAnimation(.spring(response: 0.7, dampingFraction: 0.75).delay(0.1)) { vis = true }
        }
        .accessibilityLabel("Ferdig")
    }
}

private struct HakePath: Shape {
    func path(in r: CGRect) -> Path {
        var p = Path()
        p.move(to: CGPoint(x: r.minX, y: r.midY))
        p.addLine(to: CGPoint(x: r.minX + r.width * 0.36, y: r.maxY))
        p.addLine(to: CGPoint(x: r.maxX, y: r.minY))
        return p
    }
}

/// Prikker øverst som viser hvor langt du er kommet.
struct KassettStegPrikker: View {
    let steg: Int
    let antall: Int
    var body: some View {
        HStack(spacing: 6) {
            ForEach(0..<antall, id: \.self) { i in
                Capsule().fill(i == steg ? V4.gold : V4.ink.opacity(i < steg ? 0.5 : 0.18))
                    .frame(width: i == steg ? 18 : 6, height: 6)
            }
        }
        .animation(.snappy, value: steg)
        .accessibilityLabel("Steg \(steg + 1) av \(antall)")
    }
}

/// Én forklaringsrad med ikon (som i Apples oppsettsskjermer).
struct KassettForklaring: View {
    let ikon: String
    let tittel: String
    let tekst: String
    var body: some View {
        HStack(alignment: .top, spacing: 14) {
            Image(systemName: ikon).font(.system(size: 22, weight: .regular)).foregroundStyle(V4.gold)
                .frame(width: 34)
            VStack(alignment: .leading, spacing: 3) {
                Text(tittel).sora(15, .semibold)
                Text(tekst).sora(13, .regular, V4.body, lineHeight: 1.4).fixedSize(horizontal: false, vertical: true)
            }
            Spacer(minLength: 0)
        }
    }
}

private func clamp(_ x: Double) -> Double { min(1, max(0, x)) }
private func ease(_ x: Double) -> Double { x < 0.5 ? 4 * x * x * x : 1 - pow(-2 * x + 2, 3) / 2 }
