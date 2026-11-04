import SwiftUI

/// Kildeside (srcOn): radial gradient i kildens farge, status, søk, spillelister og låter – eller forklaring for innganger.
struct V4SourcePage: View {
    @Environment(AppModel.self) private var m
    @Environment(V4State.self) private var ui
    let wide: Bool
    @State private var libHits: [Track] = []
    @State private var busy = false

    private var n: String { ui.src ?? "" }
    private var lib: String? { V4Lib.id(n) }
    private var isRadio: Bool { n == "Radio" }
    private var isInput: Bool { ["AirPlay", "Blåtann", "UPnP/DLNA", "AUX", "Spotify"].contains(n) }
    private var q: String { ui.srcQ.trimmingCharacters(in: .whitespaces) }

    var body: some View {
        ScrollView(.vertical, showsIndicators: false) {
            VStack(alignment: .leading, spacing: 22) {
                Button { close() } label: {
                    V4Icon(d: V4.back, size: 20, stroke: 2.4, color: V4.ink).frame(width: 46, height: 46).v4GlassButton(Circle())
                }
                .plain().accessibilityLabel("Tilbake")
                head
                if !isInput { searchField }
                if isInput { inputCard }
                content
            }
            .padding(.horizontal, wide ? 40 : 20).padding(.top, 6).padding(.bottom, wide ? 130 : 230)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .scrollDismissesKeyboard(.interactively)
        .onScrollGeometryChange(for: CGFloat.self) { $0.contentOffset.y + $0.contentInsets.top } action: { _, y in
            if !wide { ui.scrolled(y) }
        }
        .background(alignment: .top) { glow }
        .background(V4.bg.ignoresSafeArea())
        .task(id: n) { if let lib { await m.loadLib(lib) } }
        .task(id: q) { await search() }
    }

    /// radial-gradient(90% 70% at 20% 0%, kildefarge55 0%, transparent 70%), 420 høy.
    private var glow: some View {
        RadialGradient(colors: [V4Src.color(n).opacity(0.33), .clear], center: UnitPoint(x: 0.2, y: 0), startRadius: 0, endRadius: 330)
            .frame(height: 420)
            .ignoresSafeArea(edges: .top)
            .allowsHitTesting(false)
    }

    // MARK: Topp

    private var playingHere: Bool { m.v4SrcIcon == n || (n == "YT Music" && m.v4SrcIcon == "YouTube Music") }

    private var head: some View {
        HStack(spacing: 16) {
            V4SourceIcon(label: n, size: 72).shadow(color: .black.opacity(0.4), radius: 15, y: 10)
            VStack(alignment: .leading, spacing: 4) {
                Text(n).sora(30, .bold).tracking(-0.6).lineLimit(1).minimumScaleFactor(0.7)
                HStack(spacing: 7) {
                    Circle().fill(playingHere ? V4.green : isInput ? V4.muted : V4.goldDark).frame(width: 7, height: 7)
                    Text(playingHere ? "Spiller nå i " + m.v4GroupName : isInput ? "Inngang · klar" : "Koblet til")
                        .sora(13, .regular, V4.ink.opacity(0.75)).lineLimit(1)
                }
            }
        }
    }

    private var searchField: some View {
        HStack(spacing: 10) {
            V4Icon(d: "M11 18a7 7 0 1 0 0-14a7 7 0 1 0 0 14M20 20l-4-4", size: 18, stroke: 2, color: V4.body)
            TextField("", text: Binding(get: { ui.srcQ }, set: { ui.srcQ = $0 }),
                      prompt: Text(isRadio ? "Søk etter kanal" : "Søk i " + n).foregroundStyle(V4.muted))
                .font(.sora(16)).foregroundStyle(V4.ink)
                .autocorrectionDisabled().textInputAutocapitalization(.never)
                .submitLabel(.search)
            if !q.isEmpty {
                Button { ui.srcQ = "" } label: {
                    V4Icon(d: V4.close, size: 12, stroke: 2.6, color: V4.ink).frame(width: 28, height: 28)
                        .background(Circle().fill(Color.white.opacity(0.14)))
                }
                .plain().accessibilityLabel("Tøm")
            }
        }
        .padding(.horizontal, 16).frame(height: 48)
        .v4GlassButton(Capsule())
    }

    // MARK: Innganger

    private var inputText: (String, [(String, String, String, Color)], String) {
        let room = "«Skjold " + m.actRoom.name + "»"
        switch n {
        case "AirPlay":
            let d = m.dev?.airplayDevice ?? ""
            return ("Velg \(room) i kontrollsenteret på iPhone, iPad eller Mac. Lyden kommer uten tap i kvalitet.",
                    d.isEmpty ? [] : [(d, "Spiller nå", "TILKOBLET", V4.green)], "Bytt til AirPlay")
        case "Blåtann":
            let d = m.dev?.btDevice ?? ""
            return ("Koble til \(room) fra Blåtann-innstillingene på telefonen. Forsterkeren husker åtte enheter.",
                    d.isEmpty ? [] : [(d, "Tilkoblet", "PARET", V4.green)], "Gjør synlig i 2 minutter")
        case "UPnP/DLNA":
            return ("Skjold vises som høyttaler i apper som BubbleUPnP, foobar2000 og Plex.", [], "Vis navnet på nettverket")
        case "Spotify":
            return ("Åpne Spotify, trykk på høyttalerikonet og velg \(room). Skjold spiller via Spotify Connect.", [], "Bruk Spotify")
        default:
            return ("Analog inngang bak på forsterkeren. Bytter automatisk når det kommer signal.",
                    [("AUX-inngang", m.input == 2 ? "Aktiv" : "Ingen signal", m.input == 2 ? "AKTIV" : "LEDIG", m.input == 2 ? V4.green : V4.muted)],
                    "Bytt til AUX nå")
        }
    }

    private var inputCard: some View {
        let t = inputText
        return VStack(alignment: .leading, spacing: 14) {
            Text(t.0).sora(15, .regular, V4.ink2, lineHeight: 1.5).fixedSize(horizontal: false, vertical: true)
            ForEach(t.1, id: \.0) { d in
                HStack(spacing: 12) {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(d.0).sora(15).lineLimit(1)
                        Text(d.1).sora(12, .regular, V4.muted)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    Text(d.2).mono(10, d.3, em: 0.1)
                }
                .padding(.top, 12)
                .v4TopLine(V4.line)
            }
            Button { use() } label: {
                Text(t.2).sora(15, .semibold, V4.bg).frame(maxWidth: .infinity).frame(height: 48).background(Capsule().fill(V4.ink))
            }
            .plain()
        }
        .padding(18)
        .v4Card()
    }

    private func use() {
        Haptics.thump()
        switch n {
        case "AirPlay": m.pickInput(0)
        case "Blåtann": m.pickInput(1); if m.live { m.devSend("/api/bt", ["pairing": true]) }
        case "UPnP/DLNA": m.pickService("upnp")
        case "Spotify": m.pickService("spotify")
        default: m.pickInput(2)
        }
    }

    // MARK: Spillelister og låter

    @ViewBuilder private var content: some View {
        if isRadio {
            radioList
        } else if let lib {
            let pls = V4Lib.playlists(m, lib).filter { q.isEmpty || $0.name.localizedCaseInsensitiveContains(q) }
            let trs = tracks(lib)
            if !q.isEmpty && pls.isEmpty && trs.isEmpty && !busy {
                Text("Fant ingenting for «\(q)» i \(n)").sora(15, .regular, V4.muted).frame(maxWidth: .infinity).padding(.vertical, 20)
            }
            if pls.isEmpty && trs.isEmpty && q.isEmpty { emptyLib(lib) }
            if !pls.isEmpty {
                VStack(alignment: .leading, spacing: 12) {
                    sectionTitle("Spillelister")
                    V4Shelf(spacing: 12) {
                        ForEach(pls, id: \.id) { p in
                            Button { ui.pl = p } label: {
                                VStack(alignment: .leading, spacing: 6) {
                                    V4Mosaic(keys: p.keys, size: 148, radius: 14)
                                    Text(p.name).sora(14, .semibold).lineLimit(1)
                                    Text("\(p.count) låter").sora(12, .regular, V4.muted)
                                }
                                .frame(width: 148, alignment: .leading)
                            }
                            .plain()
                        }
                    }
                }
            }
            if !trs.isEmpty {
                VStack(alignment: .leading, spacing: 6) {
                    sectionTitle("Låter")
                    ForEach(Array(trs.enumerated()), id: \.offset) { i, t in
                        trackRow(t.t, t.artist, key: t.album, cur: m.libTrack?.t == t.t) {
                            m.lib = lib; m.playLib(trs, i, keepOpen: true)
                        } more: { ui.moreTrack = t; withAnimation(V4.moreSheet) { ui.more = true } }
                    }
                }
            }
        }
    }

    private func tracks(_ lib: String) -> [Track] {
        if !q.isEmpty {
            if m.demo { return SK.lt.filter { ($0.t + " " + $0.artist + " " + $0.album).localizedCaseInsensitiveContains(q) } }
            return libHits
        }
        if m.demo { return (SK.lib[lib]?.hist ?? []).map { SK.lt[$0.0 % SK.lt.count] } }
        return (m.hist[lib] ?? []).map(\.track)
    }

    @ViewBuilder private func emptyLib(_ lib: String) -> some View {
        let s = m.libs[lib]?.state ?? ""
        let text = lib == "ytm" ? "YouTube Music er ikke koblet til ennå. Legg inn innloggingen under Innstillinger → Musikktjenester."
            : s == "busy" ? "Henter biblioteket …"
            : s.isEmpty || s == "ok" ? "Ingen spillelister ennå." : s
        Text(text).sora(14, .regular, V4.muted, lineHeight: 1.45).fixedSize(horizontal: false, vertical: true)
    }

    private func search() async {
        guard let lib, !m.demo, !q.isEmpty else { libHits = []; return }
        try? await Task.sleep(for: .milliseconds(350))
        guard !Task.isCancelled else { return }
        busy = true
        let r = await m.searchLib(lib, q)
        guard !Task.isCancelled else { return }
        libHits = r; busy = false
    }

    // MARK: Radio

    @ViewBuilder private var radioList: some View {
        let hits: [Station] = q.isEmpty ? [] : (m.rRes ?? []).map { Station(name: $0.name, genre: $0.genre, url: $0.url) }
        let favs = m.radio.enumerated().filter { q.isEmpty || $0.element.name.localizedCaseInsensitiveContains(q) }
        VStack(alignment: .leading, spacing: 6) {
            sectionTitle("Kanaler")
            ForEach(Array(favs), id: \.offset) { i, st in
                trackRow(st.name, st.genre, key: st.name, cur: m.input == 3 && m.stIdx == i && m.rTmp == nil) {
                    m.playStation(i, open: false)
                } more: { m.toggleFav(st) }
            }
            if !q.isEmpty {
                if m.rBusy { Text("Søker …").sora(13, .regular, V4.muted).padding(.vertical, 8) }
                ForEach(hits, id: \.self) { st in
                    trackRow(st.name, st.genre, key: st.name, cur: m.curRadioName == st.name) {
                        m.playRadio(st)
                    } more: { m.toggleFav(st) }
                }
                if !m.rBusy && hits.isEmpty && favs.isEmpty {
                    Text("Fant ingenting for «\(q)» i Radio").sora(15, .regular, V4.muted).frame(maxWidth: .infinity).padding(.vertical, 20)
                }
            }
        }
        .onChange(of: q) { _, v in m.setQ(v) }
    }

    // MARK: Felles

    private func sectionTitle(_ t: String) -> some View {
        Text(t.uppercased()).sora(15, .bold).tracking(0.6)
            .padding(.bottom, 10)
            .frame(maxWidth: .infinity, alignment: .leading)
            .overlay(alignment: .bottom) { Rectangle().fill(Color.white.opacity(0.08)).frame(height: 1) }
    }

    private func trackRow(_ t: String, _ s: String, key: String, cur: Bool, play: @escaping () -> Void, more: @escaping () -> Void) -> some View {
        HStack(spacing: 14) {
            Button(action: play) {
                HStack(spacing: 14) {
                    V4Art(key: key, radius: 10, ring: cur ? 2 : 0).frame(width: 56, height: 56)
                    VStack(alignment: .leading, spacing: 2) {
                        Text(t).sora(15, .semibold, cur ? V4.gold : V4.ink).lineLimit(1)
                        Text(s).sora(13, .regular, V4.muted).lineLimit(1)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
            .plain()
            V4MoreButton(action: more)
        }
        .padding(.vertical, 5)
    }

    private func close() { ui.src = nil; ui.srcQ = "" }
}

/// Kildefarger (SRCICON-bakgrunnen) til gradientene.
enum V4Src {
    static func color(_ n: String) -> Color {
        switch n {
        case "Radio": return V4.goldDark
        case "AirPlay": return Color(hex: 0x3a3a3e)
        case "Blåtann": return Color(hex: 0x0082fc)
        case "Spotify": return Color(hex: 0x1ed760)
        case "YouTube Music", "YT Music": return Color(hex: 0xff0000)
        case "Navidrome": return Color(hex: 0x1e5aa8)
        case "Plex": return Color(hex: 0xe5a00d)
        case "UPnP/DLNA": return Color(hex: 0xf2f2ee)
        default: return Color(hex: 0x3a3a37)
        }
    }
}

/// Spilleliste (plOn): gradient 560, mosaikk 240, meta, Spill / tilfeldig / mer, låtliste.
struct V4PlaylistPage: View {
    @Environment(AppModel.self) private var m
    @Environment(V4State.self) private var ui
    let wide: Bool
    @State private var tracks: [Track] = []

    var body: some View {
        if let p = ui.pl { page(p) }
    }

    private func page(_ p: V4Playlist) -> some View {
        ScrollView(.vertical, showsIndicators: false) {
            VStack(alignment: .leading, spacing: 18) {
                Button { ui.pl = nil } label: {
                    V4Icon(d: V4.back, size: 20, stroke: 2.4, color: V4.ink).frame(width: 46, height: 46).v4GlassButton(Circle())
                }
                .plain().accessibilityLabel("Tilbake")
                V4Mosaic(keys: p.keys, size: 240, radius: 18)
                    .shadow(color: .black.opacity(0.5), radius: 30, y: 30)
                    .frame(maxWidth: .infinity)
                VStack(alignment: .leading, spacing: 4) {
                    Text(p.name).sora(34, .bold, lineHeight: 1.05).tracking(-0.68).lineLimit(2)
                    Text(p.owner).sora(17, .semibold).lineLimit(1)
                    HStack(spacing: 7) {
                        V4SourceIcon(label: p.src, size: 18)
                        Text(p.src + " · Spilleliste · " + meta).sora(13, .regular, V4.ink.opacity(0.72)).lineLimit(1)
                    }
                    .padding(.top, 4)
                }
                .padding(.top, 8)
                buttons(p)
                VStack(spacing: 4) {
                    ForEach(Array(tracks.enumerated()), id: \.offset) { i, t in row(p, i, t) }
                }
                .padding(.top, 6)
            }
            .padding(.horizontal, 20).padding(.top, 6).padding(.bottom, 240)
            .frame(maxWidth: wide ? 760 : .infinity, alignment: .leading)
            .frame(maxWidth: .infinity)
        }
        .onScrollGeometryChange(for: CGFloat.self) { $0.contentOffset.y + $0.contentInsets.top } action: { _, y in
            if !wide { ui.scrolled(y) }
        }
        .background(alignment: .top) { bg(p) }
        .background(V4.bg.ignoresSafeArea())
        .task(id: p.id) { tracks = await V4Lib.tracks(m, p) }
    }

    private var meta: String {
        let mins = tracks.reduce(0) { $0 + $1.dur } / 60
        return "\(tracks.count) låter · \(mins) min"
    }

    private var isPlaying: Bool { !tracks.isEmpty && m.playing && m.lq == tracks }

    private func bg(_ p: V4Playlist) -> some View {
        let a = art(p.keys.first ?? p.name), b = art(p.keys.count > 1 ? p.keys[1] : p.name)
        return ZStack(alignment: .top) {
            RadialGradient(colors: [a.base, .clear], center: UnitPoint(x: 0.2, y: 0.1), startRadius: 0, endRadius: 360)
            RadialGradient(colors: [b.base, .clear], center: UnitPoint(x: 0.85, y: 0.25), startRadius: 0, endRadius: 360)
            LinearGradient(colors: [.clear, V4.bg], startPoint: UnitPoint(x: 0.5, y: 300.0 / 560), endPoint: .bottom)
        }
        .frame(height: 560)
        .ignoresSafeArea(edges: .top)
        .allowsHitTesting(false)
    }

    private func buttons(_ p: V4Playlist) -> some View {
        HStack(spacing: 12) {
            Button { play(p, 0, shuffle: false) } label: {
                HStack(spacing: 10) {
                    V4PlayIcon(playing: isPlaying, size: 20, color: V4.bg)
                    Text(m.v4GroupName).sora(16, .semibold, V4.bg).lineLimit(1)
                }
                .padding(.leading, 18).padding(.trailing, 22).frame(height: 52)
                .frame(maxWidth: 200)
                .background(Capsule().fill(V4.ink))
            }
            .plain()
            Button { play(p, 0, shuffle: true) } label: {
                V4Icon(d: V4.shuffle, size: 22, stroke: 2, color: V4.bg).frame(width: 52, height: 52).background(Circle().fill(V4.ink))
            }
            .plain().accessibilityLabel("Spill tilfeldig")
            Button { ui.moreTrack = tracks.first; withAnimation(V4.moreSheet) { ui.more = true } } label: {
                V4Icon(d: V4.dots, size: 20, color: V4.ink, fill: true).frame(width: 52, height: 52).background(Circle().fill(V4.ink.opacity(0.12)))
            }
            .plain().accessibilityLabel("Mer")
        }
    }

    private func play(_ p: V4Playlist, _ i: Int, shuffle: Bool) {
        guard !tracks.isEmpty else { return }
        if isPlaying && !shuffle && i == 0 { m.togglePlay(); return }
        let list = shuffle ? tracks.shuffled() : tracks
        m.lib = p.lib
        m.shuffle = shuffle
        m.playLib(list, i, keepOpen: true)
    }

    private func row(_ p: V4Playlist, _ i: Int, _ t: Track) -> some View {
        let cur = m.libTrack?.t == t.t
        return HStack(spacing: 14) {
            Button { m.lib = p.lib; m.playLib(tracks, i, keepOpen: true) } label: {
                HStack(spacing: 14) {
                    V4Art(key: t.album, radius: 10, ring: cur ? 2 : 0).frame(width: 60, height: 60)
                    VStack(alignment: .leading, spacing: 3) {
                        Text(t.t).sora(16, .semibold, cur ? V4.gold : V4.ink).lineLimit(1)
                        Text(t.artist).sora(14, .regular, V4.ink.opacity(0.6)).lineLimit(1)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
            .plain()
            V4MoreButton(size: 20) { ui.moreTrack = t; withAnimation(V4.moreSheet) { ui.more = true } }
        }
        .padding(.vertical, 6)
    }
}
