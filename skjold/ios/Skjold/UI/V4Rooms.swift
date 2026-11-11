import SwiftUI

/// Rom (tRom): gruppekortet og de andre rommene, med volum per rom, sortering og festing.
struct V4RoomsTab: View {
    @Environment(AppModel.self) private var m
    @Environment(V4State.self) private var ui
    let wide: Bool

    var body: some View {
        HStack(spacing: 12) {
            V4Title(text: "Rom")
            Spacer(minLength: 0)
            HStack(spacing: 8) {
                circleButton(V4.sort, "Sorter", on: ui.sortOpen) { withAnimation(V4.fade) { ui.sortOpen.toggle() } }
                circleButton(V4.plus, "Legg til", on: false) { m.restartSetup() }
            }
        }
        grid
    }

    @State private var width: CGFloat = 390

    private var grid: some View {
        let cols = wide && width > 900 ? 2 : 1
        let cards = sortedCards
        return LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 12), count: cols), spacing: 12) {
            ForEach(cards, id: \.id) { c in V4RoomCard(card: c) }
        }
        .padding(.horizontal, -4)
        .onGeometryChange(for: CGFloat.self) { $0.size.width } action: { width = $0 }
        .animation(.snappy, value: cards.map(\.id))
    }

    private func circleButton(_ d: String, _ label: String, on: Bool, _ act: @escaping () -> Void) -> some View {
        Button { Haptics.tap(); act() } label: {
            V4Icon(d: d, size: 20, color: V4.ink).frame(width: 44, height: 44)
                .v4DarkPill(Circle(), border: 0.12, fill: on ? V4.ink.opacity(0.18) : Color(hex: 0x28282a, alpha: 0.6))
        }
        .plain()
        .accessibilityLabel(label)
    }

    // MARK: Kort

    private var sortedCards: [V4RoomCardData] {
        let group = m.v4Group
        let gids = Set(group.map(\.id))
        let main = V4RoomCardData(id: m.actRoom.id, name: m.v4GroupName, types: group.map(\.type), t: m.np.t, s: m.np.s,
                                  src: m.v4SrcIcon, key: m.playerArt.key, playing: m.playing, isMain: true,
                                  pinned: group.contains { ui.pins.contains($0.id) },
                                  ord: group.compactMap { ui.pins.firstIndex(of: $0.id) }.min(), room: m.actRoom)
        var out = [main]
        for r in m.sys.rooms where !gids.contains(r.id) {
            let t = r.np?.first ?? "Ledig"
            let s = (r.np?.count ?? 0) > 1 ? r.np![1] : SK.dev(r.type).n
            out.append(V4RoomCardData(id: r.id, name: r.name, types: [r.type], t: t, s: s, src: "Radio", key: r.np?.first ?? r.name,
                                      playing: r.np != nil && r.np?.first != "Frakoblet", isMain: false, pinned: ui.pins.contains(r.id),
                                      ord: ui.pins.firstIndex(of: r.id), room: r))
        }
        let sort = ui.sort
        return out.sorted { a, b in
            let pa = a.ord ?? 99, pb = b.ord ?? 99
            if pa != pb { return pa < pb }
            if sort == 0, a.playing != b.playing { return a.playing }
            if sort == 2 { return a.name.localizedCompare(b.name) == .orderedAscending }
            return false
        }
    }
}

struct V4RoomCardData {
    var id: String, name: String, types: [String], t: String, s: String, src: String, key: String
    var playing: Bool, isMain: Bool, pinned: Bool, ord: Int?
    var room: Room
}

/// Romkort: radius 24, farget fra omslaget (romfarger), kant .1, innerlys.
struct V4RoomCard: View {
    @Environment(AppModel.self) private var m
    let card: V4RoomCardData

    private var vol: Int { card.isMain ? m.v4GroupVol : m.v4RoomVol(card.room) }

    var body: some View {
        let a = art(card.key)
        VStack(alignment: .leading, spacing: 12) {
            head
            HStack(spacing: 12) {
                Button { open() } label: {
                    ArtFill(a).frame(width: 52, height: 52)
                        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                        .shadow(color: .black.opacity(0.35), radius: 8, y: 6)
                }
                .plain()
                Button { open() } label: {
                    VStack(alignment: .leading, spacing: 3) {
                        Text(card.t).sora(14, .semibold).lineLimit(1)
                        HStack(spacing: 6) {
                            V4SourceIcon(label: card.src, size: 15)
                            Text(card.s).sora(12, .regular, V4.ink.opacity(0.72)).lineLimit(1)
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
                .plain()
                Button { m.v4ToggleRoom(card.room) } label: {
                    V4PlayIcon(playing: card.playing, size: 15, color: V4.ink)
                        .frame(width: 40, height: 40)
                        .overlay(Circle().strokeBorder(V4.ink.opacity(0.7), lineWidth: 1.5))
                }
                .plain()
                .accessibilityLabel("Spill/pause")
            }
            HStack(spacing: 10) {
                V4Icon(d: V4.vol, size: 16, color: V4.ink.opacity(0.8))
                V4Bar(value: Double(vol) / 100, height: 8, trackColor: V4.ink.opacity(0.2)) { v in
                    let n = Int((v * 100).rounded())
                    if card.isMain { m.v4SetGroupVol(n) } else { m.v4SetRoomVol(card.room.id, n) }
                }
                Text("\(vol)").mono(13, V4.ink).frame(width: 24, alignment: .trailing)
            }
        }
        .padding(.horizontal, 16).padding(.top, 14).padding(.bottom, 16)
        .background { cardBg(a) }
        .overlay(RoundedRectangle(cornerRadius: 24, style: .continuous).strokeBorder(Color.white.opacity(0.1), lineWidth: 1))
        .overlay(alignment: .top) {
            RoundedRectangle(cornerRadius: 24, style: .continuous)
                .strokeBorder(LinearGradient(colors: [Color.white.opacity(0.1), .clear], startPoint: .top, endPoint: .center), lineWidth: 1)
                .allowsHitTesting(false)
        }
        .clipShape(RoundedRectangle(cornerRadius: 24, style: .continuous))
        .opacity(card.playing ? 1 : 0.78)
    }

    private var head: some View {
        HStack(spacing: 10) {
            HStack(spacing: 8) {
                if card.pinned { V4Icon(d: V4.pin, size: 13, stroke: 1.5, color: V4.gold, fill: true) }
                Text(card.name).sora(17, .semibold).lineLimit(1)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            HStack(spacing: 4) {
                ForEach(Array(card.types.enumerated()), id: \.offset) { _, t in
                    V4Icon(d: SK.dev(t).icon, size: 16, stroke: 1.4, color: V4.ink)
                        .frame(width: 26, height: 26)
                        .background(RoundedRectangle(cornerRadius: 8, style: .continuous).fill(Color.black.opacity(0.25)))
                }
            }
        }
    }

    /// linear-gradient(150deg, top, mid) – farger fra omslaget, mørknet som i malen.
    private func cardBg(_ a: ArtInfo) -> some View {
        ZStack {
            CSSLinearGradient(angle: 150, stops: a.stops)
            Color.black.opacity(a.hasLogo ? 0.55 : 0.32)
        }
    }

    private func open() {
        if card.isMain { m.full = true; return }
        Haptics.tick()
        withAnimation(.snappy) { m.v4Activate(card.room) }
    }
}

/// «Sorter etter»-menyen.
struct V4SortMenu: View {
    @Environment(V4State.self) private var ui
    private static let sorts = ["Spiller nå først", "Mest brukt", "Alfabetisk"]

    var body: some View {
        ZStack(alignment: .topTrailing) {
            Color.black.opacity(0.35).ignoresSafeArea().onTapGesture { close() }
            VStack(alignment: .leading, spacing: 0) {
                Text("SORTER ETTER").mono(10, V4.body, em: 0.12).padding(.horizontal, 12).padding(.top, 8).padding(.bottom, 6)
                ForEach(Array(Self.sorts.enumerated()), id: \.offset) { i, n in
                    Button { Haptics.tick(); ui.sort = i; close() } label: {
                        HStack(spacing: 10) {
                            Text(ui.sort == i ? "✓" : "").sora(14, .regular, V4.gold).frame(width: 16)
                            Text(n).sora(14)
                        }
                        .padding(.horizontal, 12).frame(height: 44)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(RoundedRectangle(cornerRadius: 12, style: .continuous).fill(ui.sort == i ? V4.ink.opacity(0.08) : .clear))
                    }
                    .plain()
                }
                Rectangle().fill(Color.white.opacity(0.1)).frame(height: 1).padding(.horizontal, 8).padding(.vertical, 6)
                Button { close(); withAnimation(V4.pinSheet) { ui.pin = true } } label: {
                    HStack(spacing: 10) { V4Icon(d: V4.pin, size: 16); Text("Fest rom …").sora(14) }
                        .padding(.horizontal, 12).frame(height: 44)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
                .plain()
            }
            .padding(8)
            .frame(width: 250)
            .v4Menu()
            .padding(.trailing, 20).padding(.top, 58)
        }
        .transition(.opacity)
    }

    private func close() { withAnimation(V4.fade) { ui.sortOpen = false } }
}

/// «Fest rom»-arket: radius 34/34/0/0, 56 fra toppen, #1a1a1c.
struct V4PinSheet: View {
    @Environment(AppModel.self) private var m
    @Environment(V4State.self) private var ui
    let wide: Bool

    var body: some View {
        GeometryReader { g in
            ZStack(alignment: .top) {
                Color.black.opacity(ui.pin ? 0.55 : 0).ignoresSafeArea()
                    .onTapGesture { close() }
                    .animation(V4.scrim, value: ui.pin)
                sheet
                    .padding(.top, 56 - g.safeAreaInsets.top)
                    .padding(.horizontal, 8)
                    .offset(y: ui.pin ? 0 : g.size.height * 1.05 + 80)
                    .animation(V4.pinSheet, value: ui.pin)
                    .ignoresSafeArea(edges: .bottom)
            }
        }
        .allowsHitTesting(ui.pin)
    }

    private var pinned: [Room] { ui.pins.compactMap { id in m.sys.rooms.first { $0.id == id } } }
    private var others: [Room] { m.sys.rooms.filter { !ui.pins.contains($0.id) } }

    private var sheet: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Button { close() } label: {
                    V4Icon(d: V4.close, size: 18, stroke: 2).frame(width: 44, height: 44)
                        .background(Circle().fill(V4.ink.opacity(0.1)))
                        .overlay(Circle().strokeBorder(Color.white.opacity(0.12), lineWidth: 1))
                }
                .plain().accessibilityLabel("Lukk")
                Spacer()
                Button { close() } label: {
                    Text("Ferdig").sora(14, .semibold, V4.bg).padding(.horizontal, 18).frame(height: 44)
                        .background(Capsule().fill(V4.goldDark))
                }
                .plain()
            }
            VStack(alignment: .leading, spacing: 6) {
                Text("Fest rom").sora(28, .semibold).tracking(-0.56)
                Text("Festede rom ligger alltid øverst i Rom-fanen, i den rekkefølgen du velger her.")
                    .sora(13, .regular, V4.body, lineHeight: 1.5).fixedSize(horizontal: false, vertical: true)
            }
            HStack(alignment: .firstTextBaseline) {
                V4Kicker(text: "FESTET · \(pinned.count)")
                Spacer()
                Button { Haptics.tick(); ui.pins = m.sys.rooms.map(\.id) } label: { Text("Velg alle").sora(13, .regular, V4.goldDark) }.plain()
            }
            VStack(spacing: 0) {
                if pinned.isEmpty { Text("Velg rom under for å feste dem.").sora(13, .regular, V4.muted).padding(16).frame(maxWidth: .infinity, alignment: .leading) }
                ForEach(Array(pinned.enumerated()), id: \.element.id) { i, r in pinnedRow(i, r) }
            }
            .v4Card(radius: 18, bg: V4.row, border: Color.white.opacity(0.08))
            V4Kicker(text: "ANDRE ROM")
            VStack(spacing: 0) {
                ForEach(Array(others.enumerated()), id: \.element.id) { i, r in otherRow(i, r) }
                if others.isEmpty { Text("Alle rom er festet.").sora(13, .regular, V4.muted).padding(16).frame(maxWidth: .infinity, alignment: .leading) }
            }
            .v4Card(radius: 18, bg: V4.row, border: Color.white.opacity(0.08))
            Spacer(minLength: 0)
        }
        .padding(.horizontal, 18).padding(.top, 16)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        .background(UnevenRoundedRectangle(topLeadingRadius: 34, topTrailingRadius: 34, style: .continuous).fill(V4.sheet))
        .overlay(UnevenRoundedRectangle(topLeadingRadius: 34, topTrailingRadius: 34, style: .continuous).stroke(Color.white.opacity(0.08), lineWidth: 1))
    }

    private func roomIcon(_ r: Room) -> some View {
        V4Icon(d: SK.dev(r.type).icon, size: 20, stroke: 1.3, color: V4.ink2)
            .frame(width: 36, height: 36)
            .background(RoundedRectangle(cornerRadius: 10, style: .continuous).fill(V4.bg))
    }

    private func pinnedRow(_ i: Int, _ r: Room) -> some View {
        HStack(spacing: 12) {
            Text("\(i + 1)").mono(11, V4.gold).frame(width: 22, alignment: .leading)
            roomIcon(r)
            Text(r.name).sora(15).frame(maxWidth: .infinity, alignment: .leading)
            HStack(spacing: 6) {
                Button {
                    guard i > 0 else { return }
                    Haptics.tick(); var p = ui.pins; p.swapAt(i - 1, i); ui.pins = p
                } label: {
                    V4Icon(d: V4.up, size: 14, stroke: 2).frame(width: 28, height: 28)
                        .background(RoundedRectangle(cornerRadius: 8, style: .continuous).fill(V4.ink.opacity(0.08)))
                }
                .plain().opacity(i > 0 ? 1 : 0.3).accessibilityLabel("Flytt opp")
                Button { Haptics.tick(); ui.pins.removeAll { $0 == r.id } } label: {
                    V4Icon(d: V4.check, size: 14, stroke: 3, color: V4.bg).frame(width: 26, height: 26).background(Circle().fill(V4.goldDark))
                }
                .plain().accessibilityLabel("Fjern")
            }
        }
        .padding(.horizontal, 14).frame(minHeight: 56)
        .v4TopLine(i > 0 ? Color.white.opacity(0.07) : .clear)
    }

    private func otherRow(_ i: Int, _ r: Room) -> some View {
        Button { Haptics.tick(); ui.pins.append(r.id) } label: {
            HStack(spacing: 12) {
                roomIcon(r)
                Text(r.name).sora(15).frame(maxWidth: .infinity, alignment: .leading)
                Circle().strokeBorder(V4.dim, lineWidth: 1.5).frame(width: 26, height: 26)
            }
            .padding(.horizontal, 14).frame(minHeight: 56)
            .v4TopLine(i > 0 ? Color.white.opacity(0.07) : .clear)
        }
        .plain()
    }

    private func close() { withAnimation(V4.pinSheet) { ui.pin = false } }
}
