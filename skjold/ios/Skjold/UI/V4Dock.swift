import SwiftUI

/// Dokken nederst: minispiller + fanelinje med linse (telefon), sammenslått dokk ved rulling, spillerlinje (iPad).
struct V4Dock: View {
    @Environment(AppModel.self) private var m
    @Environment(V4State.self) private var ui
    let wide: Bool
    @Namespace private var ns

    var body: some View {
        VStack(spacing: 8) {
            Spacer(minLength: 0)
            if wide {
                V4WideMini()
            } else if ui.col {
                collapsed
            } else {
                if m.tab != 2 { V4MiniPlayer().matchedGeometryEffect(id: "mini", in: ns) }
                V4TabBar().matchedGeometryEffect(id: "bar", in: ns)
            }
        }
        .padding(.horizontal, wide ? 20 : 10)
        .padding(.bottom, wide ? 22 : 28)
        .ignoresSafeArea(edges: .bottom)
        .offset(y: m.full && !wide ? 260 : 0)
        .opacity(m.full && !wide ? 0 : 1)
        .animation(V4.dock, value: m.full)
        .animation(V4.collapse, value: ui.col)
    }

    /// colOn: rund fane-knapp (64) + glasskapsel med omslag, tittel og spill/pause med fremdriftsring.
    private var collapsed: some View {
        let tab = V4.tabs[max(0, min(3, m.tab))]
        return HStack(spacing: 12) {
            Button { withAnimation(V4.collapse) { ui.col = false } } label: {
                V4Icon(d: tab.1, size: 26, stroke: 1.9, color: V4.gold)
                    .frame(width: 64, height: 64)
                    .v4Glass(Circle())
            }
            .plain()
            .accessibilityLabel(tab.0)
            .matchedGeometryEffect(id: "bar", in: ns)
            HStack(spacing: 10) {
                Button { m.full = true } label: {
                    HStack(spacing: 14) {
                        V4Art(key: m.playerArt.key, radius: 12).frame(width: 46, height: 46)
                        Text(m.np.t).sora(17, .semibold).lineLimit(1)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
                .plain()
                V4RingPlay(size: 48)
            }
            .padding(.horizontal, 8)
            .frame(height: 64)
            .v4Glass(Capsule())
            .matchedGeometryEffect(id: "mini", in: ns)
        }
    }
}

/// Spill/pause 48 med fremdriftsring (r 21.5, strek 3, spor .18, fremdrift #f0c46a, 1 s lineær).
struct V4RingPlay: View {
    @Environment(AppModel.self) private var m
    var size: CGFloat = 48
    var body: some View {
        Button { m.togglePlay() } label: {
            ZStack {
                Circle().fill(Color.black.opacity(0.25))
                Circle().stroke(V4.ink.opacity(0.18), lineWidth: 3).padding(1.5 + (size - 46) / 2)
                Circle().trim(from: 0, to: CGFloat(m.v4Progress))
                    .stroke(V4.gold, style: StrokeStyle(lineWidth: 3, lineCap: .round))
                    .rotationEffect(.degrees(-90))
                    .padding(1.5 + (size - 46) / 2)
                    .animation(.linear(duration: 1), value: m.v4Progress)
                V4PlayIcon(playing: m.playing, size: 18, color: V4.ink)
            }
            .frame(width: size, height: size)
        }
        .plain()
        .accessibilityLabel("Spill/pause")
    }
}

/// Minispilleren (telefon): radius 26, glass. Trykk = Nå spilles, hold 450 ms = volumknott.
struct V4MiniPlayer: View {
    @Environment(AppModel.self) private var m
    @Environment(V4State.self) private var ui

    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: 12) {
                HStack(spacing: 12) {
                    V4Art(key: m.playerArt.key, radius: 12).frame(width: 48, height: 48)
                    VStack(alignment: .leading, spacing: 2) {
                        Text(m.v4GroupName + " · " + m.actModel).mono(10, V4.gold).lineLimit(1)
                        Text(m.np.t).sora(14, .semibold).lineLimit(1)
                            .shadow(color: .black.opacity(0.5), radius: 1.5, y: 1)
                        Text(m.np.s).sora(12, .regular, V4.sub).lineLimit(1)
                            .shadow(color: .black.opacity(0.5), radius: 1.5, y: 1)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
                .contentShape(Rectangle())
                .onTapGesture { Haptics.thump(); m.full = true }
                .onLongPressGesture(minimumDuration: 0.45) {
                    Haptics.thump(); ui.hideHint(); withAnimation(V4.fade) { ui.dial = true }
                }
                Button { m.togglePlay() } label: {
                    V4PlayIcon(playing: m.playing, size: 18, color: V4.bg)
                        .frame(width: 44, height: 44)
                        .background(Circle().fill(V4.ink))
                }
                .plain()
                .accessibilityLabel("Spill/pause")
            }
            .padding(.horizontal, 10).padding(.top, 10).padding(.bottom, 8)
            HStack(spacing: 10) {
                V4Icon(d: V4.vol, size: 16, color: V4.body)
                V4Bar(value: Double(m.v4GroupVol) / 100, height: 6, trackColor: V4.ink.opacity(0.18)) { v in
                    m.v4SetGroupVol(Int((v * 100).rounded()))
                }
                Text("\(m.v4GroupVol)").mono(12, V4.ink2).frame(width: 22, alignment: .trailing)
            }
            .padding(.horizontal, 16).padding(.bottom, 12)
        }
        .v4Glass(RoundedRectangle(cornerRadius: 26, style: .continuous), top: 0.12, bottom: 0.05, highlight: 0.4)
    }
}

/// Fanelinjen: 64 høy, radius 32, glass, linse (100 % − 10) / 4 som glir med fjærende overskyting.
struct V4TabBar: View {
    @Environment(AppModel.self) private var m
    @Environment(V4State.self) private var ui

    var body: some View {
        GeometryReader { g in
            let w = (g.size.width - 10) / 4
            ZStack(alignment: .topLeading) {
                // linsen
                Capsule()
                    .fill(LinearGradient(colors: [Color.white.opacity(0.2), Color.white.opacity(0.07)], startPoint: .top, endPoint: .bottom))
                    .overlay(Capsule().stroke(LinearGradient(colors: [Color.white.opacity(0.55), Color.white.opacity(0.14)], startPoint: .top, endPoint: .bottom), lineWidth: 1))
                    .shadow(color: .black.opacity(0.3), radius: 7, y: 4)
                    .frame(width: w, height: 54)
                    .offset(x: 5 + w * CGFloat(m.tab), y: 5)
                    .animation(V4.lens, value: m.tab)
                HStack(spacing: 0) {
                    ForEach(Array(V4.tabs.enumerated()), id: \.offset) { i, t in
                        tabButton(i, t.0, t.1)
                    }
                }
                .padding(5)
            }
        }
        .frame(height: 64)
        .background(alignment: .top) {
            // toppglans (6 %–94 %, 22 høy)
            LinearGradient(colors: [Color.white.opacity(0.16), .clear], startPoint: .top, endPoint: .bottom)
                .frame(height: 22)
                .clipShape(UnevenRoundedRectangle(topLeadingRadius: 32, bottomLeadingRadius: 30, bottomTrailingRadius: 30, topTrailingRadius: 32))
                .padding(.horizontal, 23).padding(.top, 1)
        }
        .v4Glass(Capsule(), top: 0.13, bottom: 0.05)
    }

    private func tabButton(_ i: Int, _ name: String, _ path: String) -> some View {
        let on = m.tab == i
        return Button {
            if !on { Haptics.tick() }
            ui.resetOverlays(); m.full = false
            m.tab = i
            if i == 3 { m.setCat = -1 }
        } label: {
            VStack(spacing: 3) {
                V4Icon(d: path, size: 22, color: on ? V4.gold : V4.tabIdle)
                    .shadow(color: .black.opacity(0.35), radius: 1, y: 1)
                Text(name).sora(10, .semibold, on ? V4.gold : V4.tabIdle)
                    .shadow(color: .black.opacity(0.4), radius: 1, y: 1)
                    .lineLimit(1).minimumScaleFactor(0.8)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .scaleEffect(on ? 1.04 : 1)
            .animation(V4.tabColor, value: on)
        }
        .plain()
        .accessibilityLabel(name)
        .accessibilityAddTraits(on ? .isSelected : [])
    }
}

/// iPad: spillerlinjen nederst (maks 1000, 22 fra bunnen).
struct V4WideMini: View {
    @Environment(AppModel.self) private var m

    var body: some View {
        HStack(spacing: 22) {
            Button { m.full = true } label: {
                HStack(spacing: 12) {
                    V4Art(key: m.playerArt.key, radius: 12).frame(width: 50, height: 50)
                    VStack(alignment: .leading, spacing: 2) {
                        Text(m.np.t).sora(15, .semibold).lineLimit(1)
                        Text(m.np.s).sora(12, .regular, V4.sub).lineLimit(1)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
            .plain()
            .layoutPriority(1.3)
            HStack(spacing: 6) {
                Button { m.prev() } label: { V4Icon(d: V4.miniPrev, size: 22, color: V4.ink, fill: true).frame(width: 44, height: 44) }.plain()
                    .accessibilityLabel("Forrige")
                Button { m.togglePlay() } label: {
                    V4PlayIcon(playing: m.playing, size: 18, color: V4.bg).frame(width: 48, height: 48).background(Circle().fill(V4.ink))
                }
                .plain().accessibilityLabel("Spill/pause")
                Button { m.next() } label: { V4Icon(d: V4.miniNext, size: 22, color: V4.ink, fill: true).frame(width: 44, height: 44) }.plain()
                    .accessibilityLabel("Neste")
            }
            HStack(spacing: 10) {
                V4Icon(d: V4.vol, size: 16, color: V4.body)
                V4Bar(value: Double(m.v4GroupVol) / 100, height: 6, trackColor: V4.ink.opacity(0.18)) { v in
                    m.v4SetGroupVol(Int((v * 100).rounded()))
                }
                Text("\(m.v4GroupVol)").mono(12, V4.ink2).frame(width: 22, alignment: .trailing)
            }
            Button { m.full = true } label: {
                HStack(spacing: 8) {
                    V4Icon(d: V4.speakerWide, size: 16)
                    Text(m.v4GroupName).sora(13, .semibold).lineLimit(1)
                }
                .padding(.horizontal, 16).frame(height: 44)
                .background(Capsule().fill(Color.white.opacity(0.06)))
                .overlay(Capsule().strokeBorder(Color.white.opacity(0.14), lineWidth: 1))
            }
            .plain()
        }
        .padding(.vertical, 9).padding(.leading, 9).padding(.trailing, 12)
        .v4Glass(RoundedRectangle(cornerRadius: 26, style: .continuous), top: 0.12, bottom: 0.05, highlight: 0.4)
        .frame(maxWidth: 1000)
        .frame(maxWidth: .infinity)
    }
}
