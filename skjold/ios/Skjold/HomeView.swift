import SwiftUI

/// 09 Hjem: logo + room pill, active room card, recently played, sources, radio favourites.
struct HomeView: View {
    @Environment(AppModel.self) private var m
    @Environment(\.openURL) private var openURL

    var body: some View {
        let room = m.actRoom
        // v4: hjemmets navn (32/600) med pil – trykk for å bytte sted – og glasskapsel med søk og innstillinger
        HStack(alignment: .center, spacing: 12) {
            StedPicker(size: 32)
                .frame(maxWidth: .infinity, alignment: .leading)
            HStack(spacing: 2) {
                Button { Haptics.tap(); m.tab = 0; m.sub = "search" } label: {
                    SKIcon(d: "M11 18a7 7 0 1 0 0-14a7 7 0 1 0 0 14M20 20l-4-4", size: 20, stroke: 1.8, color: .ink)
                        .frame(width: 38, height: 38)
                }
                .plain()
                .accessibilityLabel("Søk")
                Button { Haptics.tap(); m.tab = 3; m.setCat = -1 } label: {
                    SKIcon(d: Icons.tabSettings, size: 20, stroke: 1.8, color: .ink)
                        .frame(width: 38, height: 38)
                }
                .plain()
                .accessibilityLabel("Innstillinger")
            }
            .padding(.horizontal, 4)
            .frame(height: 44)
            .glassEffect(.regular.interactive(), in: Capsule())
        }

        Button { m.tab = 2 } label: {
            HStack(spacing: 12) {
                SKIcon(d: SK.dev(room.type).icon, size: 24, stroke: 1.5, color: .accent2)
                    .frame(width: 44, height: 44)
                    .background(RoundedRectangle(cornerRadius: 12, style: .continuous).fill(Color.selBg))
                    .skBorder(.selLine, radius: 12)
                VStack(alignment: .leading, spacing: 2) {
                    Text(room.name).sora(15, .semibold)
                    Text(SK.dev(room.type).n).sora(12, .semibold, .accent2)
                    Text(AppModel.hwText(room)).mono(10).lineLimit(1).padding(.top, 2)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                Text("Bytt").sora(12, .regular, .ink2)
                    .padding(.horizontal, 12).frame(height: 28)
                    .skCapsuleBorder(.line2)
            }
            .padding(14)
            .skBox(.card, .line)
        }
        .plain()

        // v4: hyller med 12 pt mellomrom, tittel 17/600 med «›» der hylla kan åpnes
        VStack(alignment: .leading, spacing: 12) {
            Text("Nylig spilt ›").sora(SkG.shelfTitle, .semibold)
            EdgeScroll(spacing: 12) {
                ForEach(recent, id: \.title) { r in
                    Button(action: r.pick) { recentTile(r) }.plain()
                }
            }
        }

        VStack(alignment: .leading, spacing: 12) {
            Text("Kilder").sora(SkG.shelfTitle, .semibold)
            EdgeScroll(spacing: 14) {
                ForEach(services, id: \.0) { s in
                    SKSourceLogo(label: s.0, action: s.1)
                }
            }
        }

        VStack(alignment: .leading, spacing: 12) {
            Button { m.sub = "radio" } label: {
                Text("Radiofavoritter ›").sora(SkG.shelfTitle, .semibold)
            }
            .plain()
            EdgeScroll(spacing: 12) {
                ForEach(Array(m.radio.enumerated()), id: \.offset) { i, st in
                    Button { m.playStation(i) } label: { favTile(i, st) }.plain()
                }
            }
        }

        let pl = playlistTiles
        if !pl.isEmpty {
            VStack(alignment: .leading, spacing: 12) {
                HStack(alignment: .center, spacing: 10) {
                    VStack(alignment: .leading, spacing: 1) {
                        Text("FRA MUSIKKTJENESTENE").mono(10, .muted, em: 0.12)
                        Text("DINE SPILLELISTER").sora(15, .bold).tracking(0.6)
                    }
                    Spacer(minLength: 0)
                    SKIcon(d: "M9 6l6 6-6 6", size: 18, stroke: 2.2, color: .ink2)
                }
                .padding(.bottom, 10)
                .overlay(alignment: .bottom) { Rectangle().fill(Color.white.opacity(0.08)).frame(height: 1) }
                EdgeScroll(spacing: 12) {
                    ForEach(pl, id: \.id) { t in
                        Button(action: t.open) { playlistTile(t) }.plain()
                    }
                }
            }
            .task { await loadPlaylists() }
        } else {
            Color.clear.frame(height: 0).task { await loadPlaylists() }
        }
    }

    // MARK: Fliser (v4-mål)

    private func recentTile(_ r: Recent) -> some View {
        let a = art(r.key)
        return VStack(alignment: .leading, spacing: 7) {
            ZStack(alignment: .bottomLeading) {
                ArtFill(a)
                Text(r.big).sora(15, .semibold, a.ink, lineHeight: 1.05).padding(11)
            }
            .frame(width: 132, height: 132)
            .clipShape(RoundedRectangle(cornerRadius: SkG.tileRadius, style: .continuous))
            Text(r.title).sora(13, .semibold).lineLimit(1)
            Text(r.kind).sora(11, .regular, Color(hex: 0xa9a9a3)).lineLimit(1)
        }
        .frame(width: 132, alignment: .leading)
    }

    private func favTile(_ i: Int, _ st: Station) -> some View {
        let on = m.input == 3 && m.stIdx == i && m.rTmp == nil
        let parts = st.name.split(separator: " ", maxSplits: 1).map(String.init)
        let first = parts.first ?? st.name
        let rest = parts.count > 1 ? parts[1] : ""
        return VStack(alignment: .leading, spacing: 0) {
            Text("\(i + 1)").mono(9)
            Spacer(minLength: 0)
            HStack(alignment: .firstTextBaseline, spacing: 4) {
                Text(first).sora(20, .bold).tracking(-0.4).lineLimit(1)
                if !rest.isEmpty {
                    Text(rest).sora(20, .regular, .accent2).lineLimit(1)
                }
            }
            .minimumScaleFactor(0.6)
        }
        .padding(10)
        .frame(width: SkG.radioTile, height: SkG.radioTile, alignment: .topLeading)
        .background(RoundedRectangle(cornerRadius: SkG.tileRadius, style: .continuous).fill(Color(hex: 0x151517)))
        .skBorder(on ? .accent2 : .line, radius: SkG.tileRadius)
    }

    private struct PlTile { var id: String; var name: String; var lib: String; var keys: [String]; var open: () -> Void }

    private func playlistTile(_ t: PlTile) -> some View {
        let names = ["nd": "Navidrome", "plex": "Plex", "ytm": "YouTube Music"]
        return VStack(alignment: .leading, spacing: 6) {
            VStack(spacing: 0) {
                HStack(spacing: 0) { ArtFill(t.keys[0]); ArtFill(t.keys[1]) }
                HStack(spacing: 0) { ArtFill(t.keys[2]); ArtFill(t.keys[3]) }
            }
            .frame(width: 148, height: 148)
            .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
            Text(t.name).sora(14, .semibold).lineLimit(1)
            Text(names[t.lib] ?? t.lib).sora(12, .regular, .muted).lineLimit(1)
        }
        .frame(width: 148, alignment: .leading)
    }

    /// Spillelister fra Navidrome, Plex og YouTube Music (det som er satt opp).
    private var playlistTiles: [PlTile] {
        var out: [PlTile] = []
        for lib in ["nd", "plex", "ytm"] {
            let names: [String]
            if m.demo {
                names = (SK.lib[lib]?.pls ?? []).map { $0.0 }
            } else {
                names = (m.libs[lib]?.playlists ?? []).map { $0.name }
            }
            for (i, n) in names.prefix(8).enumerated() {
                let keys = [n, n + " 2", n + " 3", n + " 4"]
                out.append(PlTile(id: lib + "/" + n + "/\(i)", name: n, lib: lib, keys: keys) {
                    m.openLib(lib); m.libTab = 1; m.libPl = i
                })
            }
        }
        return out
    }

    private func loadPlaylists() async {
        guard m.live else { return }
        for lib in ["nd", "plex"] where (m.libs[lib]?.state ?? "").isEmpty {
            await m.loadLib(lib)
        }
    }

    private struct Recent { var title: String; var key: String; var big: String; var kind: String; var round: Bool; var pick: () -> Void }

    private var recent: [Recent] {
        guard m.demo else { return liveRecent }
        var out: [Recent] = []
        for i in 0..<2 {
            let t = SK.tr[i]
            out.append(Recent(title: t.0, key: t.0, big: t.1, kind: "AirPlay · låt", round: false) { m.input = 0; m.trk = i; m.full = true })
        }
        for (i, st) in m.radio.prefix(2).enumerated() {
            out.append(Recent(title: st.name, key: st.name, big: st.name, kind: "Radio · kanal", round: true) { m.playStation(i) })
        }
        let t = SK.tr[2]
        out.append(Recent(title: t.0, key: t.0, big: t.1, kind: "Blåtann · låt", round: false) { m.input = 1; m.trk = 2; m.full = true })
        return out
    }

    /// Live: the latest library tracks played from the app, then the first radio favourites.
    private var liveRecent: [Recent] {
        var out: [Recent] = []
        let names = ["nd": "Navidrome", "plex": "Plex", "ytm": "YouTube Music"]
        for (lib, h) in m.hist.sorted(by: { $0.key < $1.key }) {
            for (i, e) in h.prefix(2).enumerated() {
                let list = h.map(\.track)
                out.append(Recent(title: e.track.t, key: e.track.album, big: e.track.artist, kind: (names[lib] ?? lib) + " · låt", round: false) {
                    m.lib = lib; m.playLib(list, i)
                })
            }
        }
        for (i, st) in m.radio.prefix(max(2, 5 - out.count)).enumerated() {
            out.append(Recent(title: st.name, key: st.name, big: st.name, kind: "Radio · kanal", round: true) { m.playStation(i) })
        }
        return out
    }

    private var services: [(String, () -> Void)] {
        let node = m.actRoom.type == "node"
        var list: [(String, () -> Void)] = [
            ("Radio", { m.sub = "radio" }),
            ("AirPlay", { m.pickInput(0); m.full = true }),
            ("Blåtann", node ? {
                m.tab = 3; m.setDev = m.actRoom.id
                m.setCat = SK.catsFor("node").firstIndex { $0.id == "tilkobling" } ?? -1
            } : { m.pickInput(1); m.full = true }),
            ("Spotify", { m.pickService("spotify") }),
            ("UPnP/DLNA", { m.pickService("upnp") }),
            ("YT Music", { m.openLib("ytm") }),
            ("Navidrome", { m.openLib("nd") }),
            ("Plex", { m.openLib("plex") }),
            ("Lyrion", {
                if let u = m.lyrionURL ?? (m.demo ? URL(string: "http://192.168.1.42:9000/") : nil) { openURL(u) } else { Haptics.warning() }
            }),
            ("AUX", { m.pickInput(2); m.full = true })
        ]
        if node { list.removeAll { $0.0 == "AUX" } }
        return list
    }
}
