import SwiftUI

/// Hjem (tHome): tittel med sted-velger, Nylig spilt, Kilder, Radiofavoritter, Dine spillelister og hyllene.
struct V4HomeTab: View {
    @Environment(AppModel.self) private var m
    @Environment(V4State.self) private var ui

    var body: some View {
        header
        recentShelf
        sourcesShelf
        favShelf
        playlistShelf
        ForEach(shelves, id: \.title) { s in shelfView(s) }
        Color.clear.frame(height: 0).task { await loadLibs() }
    }

    // MARK: Topp

    private var header: some View {
        HStack(spacing: 12) {
            Button { Haptics.tap(); withAnimation(V4.chevron) { ui.homeOpen.toggle() }; ui.hideHint() } label: {
                HStack(spacing: 8) {
                    Text(m.stedNavn).sora(32, .semibold).tracking(-0.64).lineLimit(1)
                    V4Icon(d: V4.chevDown, size: 18, stroke: 2.2, color: V4.body)
                        .rotationEffect(.degrees(ui.homeOpen ? 180 : 0))
                        .padding(.top, 4)
                }
            }
            .plain()
            .accessibilityLabel("Bytt sted, nå \(m.stedNavn)")
            Spacer(minLength: 0)
            HStack(spacing: 2) {
                Button { Haptics.tap(); ui.hideHint(); ui.search = true } label: {
                    V4Icon(d: V4.search, size: 20, color: V4.ink).frame(width: 38, height: 38)
                }
                .plain().accessibilityLabel("Søk")
                Button { Haptics.tap(); m.tab = 3; m.setCat = -1 } label: {
                    V4Icon(d: V4.gear, size: 20, color: V4.ink).frame(width: 38, height: 38)
                }
                .plain().accessibilityLabel("Innstillinger")
            }
            .padding(.horizontal, 4)
            .frame(height: 44)
            .glassEffect(.regular.interactive(), in: Capsule())
        }
    }

    // MARK: Nylig spilt (132 × 132, radius 16)

    private struct Recent: Identifiable { var id: String; var t: String; var key: String; var big: String; var src: String; var cur: Bool; var play: () -> Void }

    private var recent: [Recent] {
        var out: [Recent] = []
        for (lib, h) in m.hist.sorted(by: { $0.key < $1.key }) {
            let list = h.map(\.track)
            for (i, e) in h.prefix(3).enumerated() {
                let cur = m.libTrack?.t == e.track.t
                out.append(Recent(id: "\(lib)-\(i)-\(e.track.t)", t: e.track.t, key: e.track.album, big: e.track.artist,
                                  src: V4Lib.names[lib] ?? lib, cur: cur) { m.lib = lib; m.playLib(list, i, keepOpen: true) })
            }
        }
        if m.demo && out.isEmpty {
            for (i, t) in SK.tr.enumerated() {
                out.append(Recent(id: "d\(i)", t: t.0, key: t.0, big: t.1, src: "AirPlay", cur: m.input == 0 && m.trk == i && m.svc == nil) {
                    m.pickInput(0); m.trk = i; m.pos = 0; m.playing = true
                })
            }
        }
        for (i, st) in m.radio.prefix(max(2, 5 - out.count)).enumerated() {
            out.append(Recent(id: "r\(i)", t: st.name, key: st.name, big: st.name, src: "Radio",
                              cur: m.input == 3 && m.stIdx == i && m.rTmp == nil) { m.playStation(i, open: false) })
        }
        return out
    }

    private var recentShelf: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Nylig spilt ›").sora(17, .semibold)
            V4Shelf(spacing: 12) {
                ForEach(recent) { r in
                    Button(action: r.play) { recentTile(r) }.plain()
                }
            }
        }
    }

    private func recentTile(_ r: Recent) -> some View {
        let a = art(r.key)
        return VStack(alignment: .leading, spacing: 7) {
            ZStack(alignment: .bottomLeading) {
                ArtFill(a)
                Text(r.big).sora(15, .semibold, a.ink, lineHeight: 1.05).lineLimit(3).padding(11)
            }
            .frame(width: 132, height: 132)
            .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: 16, style: .continuous).strokeBorder(V4.gold, lineWidth: r.cur ? 2 : 0))
            Text(r.t).sora(13, .semibold).lineLimit(1)
            HStack(spacing: 6) {
                V4SourceIcon(label: r.src, size: 16)
                Text(r.src).sora(11, .regular, V4.body).lineLimit(1)
            }
        }
        .frame(width: 132, alignment: .leading)
    }

    // MARK: Kilder (68 runde ikoner)

    private var sources: [(String, String)] {
        var l: [(String, String)] = [("Radio", "Radio"), ("AirPlay", "AirPlay"), ("Blåtann", "Blåtann"), ("Spotify", "Spotify"),
                                     ("YouTube Music", "YT Music"), ("Navidrome", "Navidrome"), ("Plex", "Plex"), ("UPnP/DLNA", "UPnP/DLNA"), ("AUX", "AUX")]
        if m.actRoom.type != "s1" { l.removeAll { $0.0 == "AUX" } }
        return l
    }

    private var sourcesShelf: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Kilder").sora(17, .semibold)
            V4Shelf(spacing: 14) {
                ForEach(sources, id: \.0) { s in
                    Button { Haptics.tap(); ui.srcQ = ""; ui.pl = nil; ui.src = s.0 } label: {
                        VStack(spacing: 7) {
                            V4SourceIcon(label: s.0, size: 68)
                            Text(s.1).sora(11, .regular, V4.ink2).lineLimit(1).fixedSize()
                        }
                        .frame(width: 68)
                    }
                    .plain()
                }
            }
        }
    }

    // MARK: Radiofavoritter (112 × 112)

    private var favShelf: some View {
        VStack(alignment: .leading, spacing: 12) {
            Button { ui.srcQ = ""; ui.src = "Radio" } label: { Text("Radiofavoritter ›").sora(17, .semibold) }.plain()
            V4Shelf(spacing: 12) {
                ForEach(Array(m.radio.enumerated()), id: \.offset) { i, st in
                    Button { m.playStation(i, open: false) } label: { favTile(i, st) }.plain()
                }
            }
        }
    }

    private func favTile(_ i: Int, _ st: Station) -> some View {
        let on = m.input == 3 && m.stIdx == i && m.rTmp == nil
        let parts = st.name.split(separator: " ", maxSplits: 1).map(String.init)
        let a = parts.first ?? st.name
        let b = parts.count > 1 ? parts[1] : ""
        return VStack(alignment: .leading, spacing: 0) {
            Text("\(i + 1)").mono(9, V4.muted)
            Spacer(minLength: 0)
            HStack(alignment: .firstTextBaseline, spacing: 4) {
                Text(a).sora(20, .bold).tracking(-0.4).lineLimit(1)
                if !b.isEmpty { Text(b).sora(20, .regular, V4Fav.color(st.name)).lineLimit(1) }
            }
            .minimumScaleFactor(0.55)
        }
        .padding(10)
        .frame(width: 112, height: 112, alignment: .topLeading)
        .background(RoundedRectangle(cornerRadius: 16, style: .continuous).fill(V4.card2))
        .overlay(RoundedRectangle(cornerRadius: 16, style: .continuous).strokeBorder(on ? V4.goldDark : V4.line, lineWidth: 1))
    }

    // MARK: Dine spillelister

    private var playlists: [V4Playlist] {
        ["ytm", "nd", "plex"].flatMap { V4Lib.playlists(m, $0).filter { $0.coll?.playlist ?? true }.prefix(6) }
    }

    @ViewBuilder private var playlistShelf: some View {
        let pls = playlists
        if !pls.isEmpty {
            VStack(alignment: .leading, spacing: 12) {
                V4ShelfHeader(title: "Dine spillelister", kicker: "FRA MUSIKKTJENESTENE")
                V4Shelf(spacing: 12) {
                    ForEach(pls, id: \.id) { p in
                        Button { ui.pl = p } label: {
                            VStack(alignment: .leading, spacing: 6) {
                                V4Mosaic(keys: p.keys, size: 148, radius: 14)
                                Text(p.name).sora(14, .semibold).lineLimit(1)
                                HStack(spacing: 6) {
                                    V4SourceIcon(label: p.src, size: 15)
                                    Text(p.src).sora(12, .regular, V4.muted).lineLimit(1)
                                }
                            }
                            .frame(width: 148, alignment: .leading)
                        }
                        .plain()
                    }
                }
            }
        }
    }

    // MARK: Hyller fra bibliotekene

    private struct ShelfTile: Identifiable { var id: String; var t: String; var s: String; var key: String; var now: Bool; var play: () -> Void }
    private struct ShelfData { var title: String; var kicker: String; var icon: String; var w: CGFloat; var tiles: [ShelfTile] }

    private var shelves: [ShelfData] {
        var out: [ShelfData] = []
        for lib in ["ytm", "nd", "plex"] {
            let tracks: [Track]
            if m.demo {
                tracks = (SK.lib[lib]?.pls.first?.1 ?? []).prefix(6).map { SK.lt[$0 % SK.lt.count] }
            } else {
                let h = (m.hist[lib] ?? []).map(\.track)
                tracks = Array(h.prefix(8))
            }
            guard !tracks.isEmpty else { continue }
            let tiles = tracks.enumerated().map { i, t in
                ShelfTile(id: "\(lib)-\(i)-\(t.t)", t: t.t, s: t.artist, key: t.album, now: m.libTrack?.t == t.t && m.playing) {
                    m.lib = lib; m.playLib(tracks, i, keepOpen: true)
                }
            }
            let title = lib == "ytm" ? "Til deg" : lib == "nd" ? "Nytt i biblioteket" : "Fra Plex"
            let name = V4Lib.names[lib] ?? lib
            out.append(ShelfData(title: title, kicker: name.uppercased(), icon: name, w: 148, tiles: tiles))
        }
        if !m.radio.isEmpty {
            let tiles = m.radio.prefix(6).enumerated().map { i, st in
                ShelfTile(id: "r\(i)", t: st.name, s: st.genre, key: st.name, now: m.input == 3 && m.stIdx == i && m.playing) {
                    m.playStation(i, open: false)
                }
            }
            out.append(ShelfData(title: "Radio akkurat nå", kicker: "RADIO", icon: "Radio", w: 120, tiles: Array(tiles)))
        }
        return out
    }

    private func shelfView(_ s: ShelfData) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            V4ShelfHeader(title: s.title, kicker: s.kicker, icon: s.icon)
            V4Shelf(spacing: 12) {
                ForEach(s.tiles) { t in
                    Button(action: t.play) {
                        VStack(alignment: .leading, spacing: 6) {
                            V4Art(key: t.key, radius: 14, ring: t.now ? 2 : 0)
                                .frame(width: s.w, height: s.w)
                                .overlay(alignment: .topTrailing) { if t.now { V4NowBars().padding(9) } }
                            Text(t.t).sora(14, .semibold).lineLimit(1)
                            Text(t.s).sora(12, .regular, V4.muted).lineLimit(1)
                        }
                        .frame(width: s.w, alignment: .leading)
                    }
                    .plain()
                }
            }
        }
    }

    private func loadLibs() async {
        guard m.live else { return }
        for lib in ["nd", "plex"] where (m.libs[lib]?.state ?? "").isEmpty { await m.loadLib(lib) }
    }
}

/// Farge på kanalnavnet i radiofavorittene (NRK P1 #7fa8ff, P2 #e86fa8, P3 #f5d53a, ellers gull).
enum V4Fav {
    static func color(_ name: String) -> Color {
        switch name {
        case "NRK P1", "NRK P1+": return Color(hex: 0x7fa8ff)
        case "NRK P2": return Color(hex: 0xe86fa8)
        case "NRK P3": return Color(hex: 0xf5d53a)
        default: return V4.gold
        }
    }
}

/// Stedsmenyen (STEDER) under tittelen på Hjem.
struct V4HomeMenu: View {
    @Environment(AppModel.self) private var m
    @Environment(V4State.self) private var ui
    let wide: Bool

    var body: some View {
        ZStack(alignment: .topLeading) {
            Color.black.opacity(0.35).ignoresSafeArea().onTapGesture { close() }
            VStack(alignment: .leading, spacing: 0) {
                Text("STEDER").mono(10, V4.body, em: 0.12).padding(.horizontal, 12).padding(.top, 8).padding(.bottom, 6)
                row(name: "Hjemme", sub: "\(m.sys.rooms.count) rom · samme nett", dot: V4.green, tile: Color(hex: 0x3a2e14),
                    icon: V4.tabs[0].1, on: m.stedId.isEmpty) { Task { await m.selectSted("") } }
                ForEach(m.steder) { s in
                    row(name: s.navn, sub: "\(s.enheter) rom · via Skjold-hjem", dot: s.online > 0 ? V4.goldDark : V4.muted,
                        tile: Color(hex: 0x1e3426), icon: "M3 20h18M5 20V11l7-6 7 6v9M10 20v-5h4v5", on: s.id == m.stedId) {
                        Task { await m.selectSted(s.id) }
                    }
                }
                Rectangle().fill(Color.white.opacity(0.1)).frame(height: 1).padding(.horizontal, 8).padding(.vertical, 6)
                Button { close(); m.openStederSettings() } label: {
                    HStack(spacing: 10) { V4Icon(d: V4.plus, size: 16, stroke: 2); Text("Legg til sted").sora(14) }
                        .padding(.horizontal, 12).frame(height: 44)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
                .plain()
            }
            .padding(8)
            .frame(width: 270)
            .v4Menu()
            .padding(.leading, 16).padding(.top, wide ? 108 : 54)
        }
        .transition(.opacity)
        .task { await m.loadSteder() }
    }

    private func row(name: String, sub: String, dot: Color, tile: Color, icon: String, on: Bool, pick: @escaping () -> Void) -> some View {
        Button { Haptics.tick(); close(); pick() } label: {
            HStack(spacing: 12) {
                V4Icon(d: icon, size: 18, color: V4.ink)
                    .frame(width: 36, height: 36)
                    .background(RoundedRectangle(cornerRadius: 10, style: .continuous).fill(tile))
                VStack(alignment: .leading, spacing: 2) {
                    Text(name).sora(15, .semibold).lineLimit(1)
                    HStack(spacing: 6) {
                        Circle().fill(dot).frame(width: 6, height: 6)
                        Text(sub).sora(11, .regular, V4.body).lineLimit(1)
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                Text(on ? "✓" : "").sora(14, .regular, V4.gold).frame(width: 16)
            }
            .padding(.horizontal, 12)
            .frame(minHeight: 56)
            .background(RoundedRectangle(cornerRadius: 14, style: .continuous).fill(on ? V4.ink.opacity(0.08) : .clear))
        }
        .plain()
    }

    private func close() { withAnimation(V4.chevron) { ui.homeOpen = false } }
}
