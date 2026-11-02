import SwiftUI

/// Root: dark background edge to edge, intro on top, then welcome → setup → app.
struct ContentView: View {
    @Environment(AppModel.self) private var m

    var body: some View {
        ZStack {
            Color.bg.ignoresSafeArea()
            switch m.mode {
            case .onboard:
                if m.welcome { WelcomeView() } else { OnboardingView() }
            case .app:
                AppShell()
            }
            if m.intro {
                IntroView()
                    .transition(.asymmetric(insertion: .identity, removal: .opacity.combined(with: .scale(scale: 1.04))))
                    .zIndex(10)
            }
        }
        .foregroundStyle(Color.ink)
        .font(.sora(14))
        .tint(.accent)
        .preferredColorScheme(.dark)
        .task { m.start() }
    }
}

/// Main app: tab content with either the system Liquid Glass tab bar or the classic bar – plus the full-screen player.
struct AppShell: View {
    @Environment(AppModel.self) private var m

    var body: some View {
        ZStack {
            // The tabs stay mounted under the player so scroll positions survive opening/closing it.
            Group {
                if glass { glassTabs } else { classic }
            }
            .opacity(m.full ? 0 : 1)
            .allowsHitTesting(!m.full)   // no taps fall through to the tabs while the player is open
            .accessibilityHidden(m.full)
            if m.full {
                FullPlayerView()
                    .transition(.move(edge: .bottom))
                    .zIndex(1)
            }
        }
        .animation(.easeOut(duration: 0.28), value: m.full)
    }

    private var glass: Bool { m.tabStyle == "glass" }

    // MARK: Liquid Glass (system TabView, as Apple recommends)

    /// System tab bar: Liquid Glass, drag between tabs, minimizes on scroll; the mini player is the bottom accessory.
    private var glassTabs: some View {
        TabView(selection: Binding(get: { m.tab }, set: { i in
            if i != m.tab { Haptics.tick() }
            pickTab(i)
        })) {
            Tab("Hjem", systemImage: "house", value: 0) { page(0) }
            Tab("Lyd", systemImage: "slider.vertical.3", value: 1) { page(1) }
            Tab("Rom", systemImage: "square.grid.2x2", value: 2) { page(2) }
            Tab("Innstillinger", systemImage: "gearshape", value: 3) { page(3) }
        }
        .tint(.accent2)
        .tabBarMinimizeBehavior(.onScrollDown)
        .tabViewBottomAccessory { NowPlayingAccessory() }
    }

    // MARK: Classic (original design)

    private var classic: some View {
        VStack(spacing: 0) {
            page(m.tab)
            SKMiniPlayer()
            SKTabBar(selected: m.tab, pick: pickTab)
        }
    }

    // MARK: Pages

    private func pickTab(_ i: Int) {
        m.tab = i; m.sub = ""
        if i == 3 { m.setCat = -1 }
    }

    /// Title + scrolling content for a tab.
    private func page(_ tab: Int) -> some View {
        VStack(spacing: 0) {
            if let title = title(tab) {
                Text(title).sora(28, .semibold).lineLimit(1)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.horizontal, 20).padding(.top, 6).padding(.bottom, 8)
            }
            ScrollView(.vertical, showsIndicators: false) {
                VStack(alignment: .leading, spacing: 16) { content(tab) }
                    .padding(.horizontal, 20).padding(.top, 10)
                    // glass: the bottom accessory floats over the content, leave room for it
                    .padding(.bottom, glass ? 84 : 16)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
            .scrollDismissesKeyboard(.interactively)
            // short soft fade at the top so content melts away under the title instead of a hard cut
            .mask {
                VStack(spacing: 0) {
                    LinearGradient(colors: [.black.opacity(0), .black], startPoint: .top, endPoint: .bottom).frame(height: 18)
                    Color.black
                }
                .ignoresSafeArea(edges: .bottom)
            }
            .id(scrollKey(tab))
        }
        .background(Color.bg.ignoresSafeArea())
    }

    /// New scroll position when the visible page changes.
    private func scrollKey(_ tab: Int) -> String { "\(tab)-\(m.sub)-\(m.lib)-\(m.setCat)-\(m.libPl ?? -1)" }

    private func title(_ tab: Int) -> String? {
        switch tab {
        case 0: return m.sub == "radio" ? "Radio" : m.sub == "lib" ? SK.lib[m.lib]?.name : nil
        case 1: return "Lyd"
        case 2: return "Ditt system"
        default: return m.setCat >= 0 && m.setCat < m.cats.count ? m.cats[m.setCat].n : "Innstillinger"
        }
    }

    @ViewBuilder private func content(_ tab: Int) -> some View {
        switch tab {
        case 0:
            if m.sub == "radio" { RadioView() } else if m.sub == "lib" { LibraryView() } else { HomeView() }
        case 1: SoundView()
        case 2: RoomsView()
        default: SettingsView()
        }
    }
}

/// Mini player inside the system tab bar accessory (Apple Music style).
/// Expanded: cover, title, artist + rooms, play/pause with a progress ring, next.
/// Inline (tab bar minimized): cover, title, play/pause. Swipe sideways to change track.
struct NowPlayingAccessory: View {
    @Environment(AppModel.self) private var m
    @Environment(\.tabViewBottomAccessoryPlacement) private var placement
    @State private var swipe: CGFloat = 0

    var body: some View {
        let np = m.np
        let inline = placement == .inline
        HStack(spacing: 10) {
            cover(inline ? 28 : 34)
            VStack(alignment: .leading, spacing: 1) {
                Text(np.t).sora(inline ? 13 : 14, .semibold).lineLimit(1)
                    .id(np.t)
                    .transition(.push(from: swipe < 0 ? .trailing : .leading))
                if !inline {
                    HStack(spacing: 4) {
                        Text(np.s).lineLimit(1)
                        Text("·")
                        SKIcon(d: Icons.speaker, size: 10, stroke: 2)
                        Text(m.groupName).lineLimit(1).layoutPriority(1)
                    }
                    .sora(11, .regular, .muted)
                    .foregroundStyle(Color.muted)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .offset(x: swipe * 0.35)
            .opacity(1 - min(0.5, abs(swipe) / 240))
            playButton(size: inline ? 30 : 36)
            if !inline {
                Button { Haptics.tap(); withAnimation(.snappy) { m.next() } } label: {
                    SKIcon(d: Icons.next, size: 17, color: .ink, fill: true).frame(width: 34, height: 36)
                }
                .plain()
                .accessibilityLabel("Neste")
            }
        }
        .padding(.leading, inline ? 6 : 8).padding(.trailing, 6)
        .contentShape(Rectangle())
        .onTapGesture { Haptics.thump(); m.full = true }
        .gesture(
            DragGesture(minimumDistance: 14)
                .onChanged { v in if abs(v.translation.width) > abs(v.translation.height) { swipe = v.translation.width } }
                .onEnded { v in
                    let dx = v.translation.width
                    if dx < -60 { Haptics.bump(); withAnimation(.snappy) { m.next() } }
                    else if dx > 60 { Haptics.bump(); withAnimation(.snappy) { m.prev() } }
                    else if v.translation.height < -30 { Haptics.thump(); m.full = true }
                    withAnimation(.spring(response: 0.3, dampingFraction: 0.8)) { swipe = 0 }
                }
        )
        .accessibilityElement(children: .contain)
        .accessibilityAction(named: "Neste låt") { m.next() }
        .accessibilityAction(named: "Forrige låt") { m.prev() }
    }

    private func cover(_ size: CGFloat) -> some View {
        ZStack(alignment: .bottomTrailing) {
            ArtFill(m.playerArt.key)
                .frame(width: size, height: size)
                .clipShape(RoundedRectangle(cornerRadius: size * 0.22, style: .continuous))
                .shadow(color: .black.opacity(0.35), radius: 4, y: 2)
            if m.input == 3 {
                // live radio marker
                Circle().fill(Color.live).frame(width: 8, height: 8)
                    .overlay(Circle().strokeBorder(Color.bg, lineWidth: 1.5))
                    .offset(x: 2, y: 2)
            }
        }
        .id(m.playerArt.key)
        .transition(.opacity.combined(with: .scale(scale: 0.9)))
    }

    /// Play/pause inside a thin progress ring (full red ring = live radio).
    private func playButton(size: CGFloat) -> some View {
        let frac = m.hasProgress ? CGFloat(m.position) / CGFloat(max(1, m.duration)) : 1
        return Button { m.togglePlay() } label: {
            ZStack {
                Circle().stroke(Color.ink.opacity(0.14), lineWidth: 2)
                Circle().trim(from: 0, to: frac)
                    .stroke(m.input == 3 ? Color.live : Color.accent2, style: StrokeStyle(lineWidth: 2, lineCap: .round))
                    .rotationEffect(.degrees(-90))
                    .animation(.linear(duration: 1), value: frac)
                SKIcon(d: m.playing ? Icons.pause : Icons.playRound, size: size * 0.46, color: .ink, fill: true)
            }
            .frame(width: size, height: size)
            .frame(width: size + 6, height: 40)
        }
        .plain()
        .accessibilityLabel(m.playing ? "Pause" : "Spill")
    }
}

#Preview("App") {
    let m = AppModel()
    m.intro = false; m.mode = .app; m.welcome = false
    return ContentView().environment(m)
}

#Preview("Velkomst") {
    let m = AppModel()
    m.intro = false; m.mode = .onboard; m.welcome = true
    return ContentView().environment(m)
}
