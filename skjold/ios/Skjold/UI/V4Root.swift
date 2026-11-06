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
                tabs
                if ui.src != nil {
                    V4SourcePage(wide: wide).transition(.move(edge: .trailing)).zIndex(14)
                }
                if ui.pl != nil {
                    V4PlaylistPage(wide: wide).transition(.move(edge: .trailing)).zIndex(15)
                }
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
        .sheet(isPresented: Binding(get: { m.showRoomEQ }, set: { m.showRoomEQ = $0 })) { V4RoomEQSheet().environment(m) }
        .sheet(item: Binding(get: { m.whatsNew }, set: { m.whatsNew = $0 })) { n in
            WhatsNewSheet(note: n) { if let h = m.activeHost { ChangelogData.markSeen(n.tag, host: h) }; m.whatsNew = nil }
        }
        .task(id: m.activeHost) {
            if let h = m.activeHost, let n = await ChangelogData.whatsNew(host: h) { m.whatsNew = n }
        }
        .task {
            try? await Task.sleep(for: .seconds(4.5))
            withAnimation(V4.fade) { ui.hideHint() }
        }
    }

    private var showHint: Bool { ui.hint && m.tab == 0 && !m.full && !ui.homeOpen && !wide && !ui.search && ui.src == nil }

    /// Fanene: systemets TabView (Liquid Glass). Fanelinjen minimeres ved rulling, minispilleren er
    /// tilbehøret nederst, og på iPad blir fanene en sidemeny (sidebarAdaptable) – som Apple anbefaler.
    private var tabs: some View {
        TabView(selection: Binding(get: { m.tab }, set: { i in pickTab(i) })) {
            Tab("Hjem", systemImage: "house", value: 0) { V4TabPage(tab: 0, wide: wide) }
            Tab("Lyd", systemImage: "slider.vertical.3", value: 1) { V4TabPage(tab: 1, wide: wide) }
            Tab("Rom", systemImage: "square.grid.2x2", value: 2) { V4TabPage(tab: 2, wide: wide) }
            Tab("Innstillinger", systemImage: "gearshape", value: 3) { V4TabPage(tab: 3, wide: wide) }
        }
        .tint(V4.gold)
        .tabViewStyle(.sidebarAdaptable)
        .tabBarMinimizeBehavior(.onScrollDown)
        .tabViewBottomAccessory { V4MiniAccessory() }
    }

    private func pickTab(_ i: Int) {
        if i != m.tab { Haptics.tick() }
        ui.resetOverlays(); m.full = false
        m.tab = i
        if i == 3 { m.setCat = -1 }
    }

    private var hintBubble: some View {
        VStack {
            Spacer()
            Text("Hold på minispilleren for volumknotten").sora(12)
                .padding(.horizontal, 14).frame(height: 32)
                .background(Capsule().fill(Color(hex: 0x2c2c30, alpha: 0.85)))
                .overlay(Capsule().strokeBorder(Color.white.opacity(0.12), lineWidth: 1))
                .padding(.bottom, 150)
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

/// Én fane: rullbar side (padding 20 / 6). Systemets fanelinje og tilbehør legger seg over innholdet.
struct V4TabPage: View {
    @Environment(AppModel.self) private var m
    let tab: Int
    let wide: Bool

    var body: some View {
        ScrollView(.vertical, showsIndicators: false) {
            VStack(alignment: .leading, spacing: 22) {
                switch tab {
                case 0: V4HomeTab()
                case 1: V4SoundTab()
                case 2: V4RoomsTab(wide: wide)
                default: V4SettingsTab()
                }
            }
            .frame(maxWidth: wide ? 860 : .infinity, alignment: .leading)
            .frame(maxWidth: .infinity)
            .padding(.horizontal, wide ? 40 : 20)
            .padding(.top, wide ? 24 : 6)
            .padding(.bottom, 40)
        }
        .scrollDismissesKeyboard(.interactively)
        .background(V4.bg.ignoresSafeArea())
        .id("tab-\(tab)-\(m.setCat)")
    }
}
