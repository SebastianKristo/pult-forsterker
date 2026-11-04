import SwiftUI

/// Rot: bakgrunn, intro, velkomst/oppsett og appen (v4-skallet).
struct ContentView: View {
    @Environment(AppModel.self) private var m
    @State private var ui = V4State()

    var body: some View {
        ZStack {
            V4.bg.ignoresSafeArea()
            switch m.mode {
            case .onboard:
                if m.welcome { WelcomeView() } else { OnboardingView() }
            case .app:
                V4App()
            }
            if m.intro {
                IntroView()
                    .transition(.asymmetric(insertion: .identity, removal: .opacity.combined(with: .scale(scale: 1.04))))
                    .zIndex(10)
            }
        }
        .environment(ui)
        .foregroundStyle(V4.ink)
        .font(.sora(14))
        .tint(V4.gold)
        .preferredColorScheme(.dark)
        .task { m.start() }
    }
}

/// Hovedskallet: faneinnhold, kildeside/spilleliste, dokk, søk, menyer, ark, Nå spilles, «Mer» og volumknott.
struct V4App: View {
    @Environment(AppModel.self) private var m
    @Environment(V4State.self) private var ui
    @Environment(\.horizontalSizeClass) private var hsc

    private var wide: Bool { hsc == .regular }

    var body: some View {
        GeometryReader { geo in
            let panelW: CGFloat = wide ? 400 : 0
            ZStack(alignment: .topLeading) {
                V4.bg.ignoresSafeArea()
                V4TabPages(wide: wide)
                topFade
                if ui.src != nil {
                    V4SourcePage(wide: wide).transition(.move(edge: .trailing)).zIndex(14)
                }
                if ui.pl != nil {
                    V4PlaylistPage(wide: wide).transition(.move(edge: .trailing)).zIndex(15)
                }
                V4Dock(wide: wide)
                    .zIndex(20)
                if wide { V4TopNav().zIndex(21) }
                if ui.homeOpen { V4HomeMenu(wide: wide).zIndex(30) }
                if ui.sortOpen { V4SortMenu().zIndex(30) }
                V4PinSheet(wide: wide).zIndex(35)
                if ui.search { V4SearchPage().transition(.opacity).zIndex(36) }
                if showHint { hintBubble.zIndex(42) }
                if wide && m.full {
                    Color.black.opacity(0.45).ignoresSafeArea()
                        .onTapGesture { closeFull() }
                        .transition(.opacity).zIndex(44)
                }
                nowPlaying(geo: geo, panelW: panelW).zIndex(45)
                V4MoreSheet(left: wide ? geo.size.width - panelW + 8 : 8).zIndex(47)
                if ui.dial { V4VolumeDial().transition(.opacity).zIndex(50) }
            }
            .animation(V4.panel, value: m.full)
            .animation(V4.dock, value: ui.src)
            .animation(V4.dock, value: ui.pl)
            .animation(V4.fade, value: ui.search)
            .animation(V4.fade, value: ui.dial)
        }
        .sheet(isPresented: Binding(get: { m.hjemLogin }, set: { m.hjemLogin = $0 })) { HjemLoginView() }
        .task {
            try? await Task.sleep(for: .seconds(4.5))
            withAnimation(V4.fade) { ui.hideHint() }
        }
    }

    private var showHint: Bool { ui.hint && m.tab == 0 && !m.full && !ui.homeOpen && !wide && !ui.search && ui.src == nil }

    /// Toppfade bak statuslinjen (64 høy, #0b0b0c .92 → 0).
    private var topFade: some View {
        LinearGradient(stops: [.init(color: V4.bg.opacity(0.92), location: 0), .init(color: V4.bg.opacity(0.6), location: 0.55),
                               .init(color: V4.bg.opacity(0), location: 1)], startPoint: .top, endPoint: .bottom)
            .frame(height: 64)
            .ignoresSafeArea(edges: .top)
            .allowsHitTesting(false)
    }

    private var hintBubble: some View {
        VStack {
            Spacer()
            Text("Hold på minispilleren for volumknotten").sora(12)
                .padding(.horizontal, 14).frame(height: 32)
                .background(Capsule().fill(Color(hex: 0x2c2c30, alpha: 0.85)))
                .overlay(Capsule().strokeBorder(Color.white.opacity(0.12), lineWidth: 1))
                .padding(.bottom, 212 - 34)
        }
        .frame(maxWidth: .infinity)
        .allowsHitTesting(false)
        .transition(.opacity)
    }

    @ViewBuilder private func nowPlaying(geo: GeometryProxy, panelW: CGFloat) -> some View {
        if wide {
            HStack(spacing: 0) {
                Spacer(minLength: 0)
                V4NowPlaying(wide: true)
                    .frame(width: panelW)
                    .overlay(alignment: .leading) { Rectangle().fill(Color.white.opacity(0.08)).frame(width: 1) }
                    .offset(x: m.full ? 0 : panelW * 1.05)
            }
            .allowsHitTesting(m.full)
        } else {
            V4NowPlaying(wide: false)
                .offset(y: m.full ? 0 : geo.size.height * 1.04 + geo.safeAreaInsets.bottom + 40)
                .allowsHitTesting(m.full)
        }
    }

    private func closeFull() { m.full = false; ui.more = false }
}

/// De fire fanene som én rullbar side (padding 58 / 20 / 230, gap 22).
struct V4TabPages: View {
    @Environment(AppModel.self) private var m
    @Environment(V4State.self) private var ui
    let wide: Bool

    var body: some View {
        ScrollView(.vertical, showsIndicators: false) {
            VStack(alignment: .leading, spacing: 22) {
                switch m.tab {
                case 0: V4HomeTab()
                case 1: V4SoundTab()
                case 2: V4RoomsTab(wide: wide)
                default: V4SettingsTab()
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.horizontal, wide ? 40 : 20)
            .padding(.top, wide ? 58 : 6)
            .padding(.bottom, wide ? 130 : 230)
        }
        .scrollDismissesKeyboard(.interactively)
        .onScrollGeometryChange(for: CGFloat.self) { $0.contentOffset.y + $0.contentInsets.top } action: { _, y in
            if !wide { ui.scrolled(y) }
        }
        .id("tab-\(m.tab)-\(m.setCat)")
    }
}

/// iPad: fanene som sentrert glasskapsel øverst (topNav).
struct V4TopNav: View {
    @Environment(AppModel.self) private var m
    @Environment(V4State.self) private var ui
    var body: some View {
        HStack(spacing: 2) {
            ForEach(Array(V4.tabs.enumerated()), id: \.offset) { i, t in
                Button { pick(i) } label: {
                    Text(t.0).sora(14, .semibold, i == m.tab ? V4.gold : V4.tabIdle)
                        .padding(.horizontal, 18).frame(height: 38)
                        .background(Capsule().fill(i == m.tab ? Color.white.opacity(0.16) : .clear))
                }
                .plain()
            }
        }
        .padding(4)
        .frame(height: 46)
        .v4GlassButton(Capsule())
        .frame(maxWidth: .infinity)
        .padding(.top, 4)
        .animation(V4.toggle, value: m.tab)
    }
    private func pick(_ i: Int) {
        Haptics.tick(); ui.resetOverlays(); m.full = false; m.tab = i; m.setCat = -1
    }
}
