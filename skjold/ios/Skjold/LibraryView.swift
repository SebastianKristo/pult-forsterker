import SwiftUI

/// 14 YouTube Music / 15 Navidrome: search, tabs, featured mix, shelves, playlists and history (libVals() in the design).
struct LibraryView: View {
    @Environment(AppModel.self) private var m

    private var L: SK.Library { SK.lib[m.lib] ?? SK.lib["ytm"]! }
    /// Album-based personal libraries (Navidrome, Plex) vs. the YouTube Music mix layout.
    private var nd: Bool { m.lib == "nd" || m.lib == "plex" }
    private var pls: [(String, [Track])] { L.pls.map { ($0.0, $0.1.map { SK.lt[$0] }) } }

    private var albums: [(String, [Track])] {
        var out: [(String, [Track])] = []
        for k in L.pls.flatMap(\.1) {
            let a = SK.lt[k].album
            if !out.contains(where: { $0.0 == a }) { out.append((a, SK.lt.filter { $0.album == a })) }
        }
        return out
    }

    private var hist: [AppModel.HistEntry] { m.hist[m.lib] ?? m.defaultHist(m.lib) }
    private var cur: Track? { m.svc == m.lib && m.lq != nil && m.li < m.lq!.count ? m.lq![m.li] : nil }
    private var plSrc: [(String, [Track])] { m.libTab == 0 && nd ? albums : pls }
    private var open: (String, [Track])? { m.libPl.flatMap { $0 < plSrc.count ? plSrc[$0] : nil } }

    var body: some View {
        @Bindable var m = m
        SKBackButton(title: m.libPl != nil ? L.tabs[m.libTab] : "Hjem") {
            if m.libPl != nil { m.libPl = nil } else { m.sub = "" }
        }
        .padding(.top, -6)
        SKField(placeholder: "Søk etter sang, artist eller album", text: $m.lq2, height: 44, size: 15)

        let q = m.lq2.trimmingCharacters(in: .whitespaces).lowercased()
        if !q.isEmpty {
            let res = SK.lt.filter { ($0.t + " " + $0.artist + " " + $0.album).lowercased().contains(q) }
            if res.isEmpty { Text("Ingen treff").sora(13, .regular, .muted) }
            trackList(res, meta: nil)
        } else if let open {
            playlistHeader(open)
            trackList(open.1, meta: nil)
        } else {
            SKSegmented(items: L.tabs, selected: m.libTab) { i in m.libTab = i; m.libPl = nil }
            switch m.libTab {
            case 0: discover
            case 1: playlistRows
            default: history
            }
        }
    }

    // MARK: Rows

    private func trackList(_ list: [Track], meta: [String]?, artistOnly: Bool = false) -> some View {
        VStack(spacing: 0) {
            ForEach(Array(list.enumerated()), id: \.offset) { i, x in
                Button { m.playLib(list, i) } label: {
                    HStack(spacing: 10) {
                        ArtFill(x.album).frame(width: 42, height: 42).clipShape(RoundedRectangle(cornerRadius: 6, style: .continuous))
                        VStack(alignment: .leading, spacing: 2) {
                            Text(x.t).sora(14, .regular, cur?.t == x.t ? .accent2 : .ink).lineLimit(1)
                            Text(artistOnly ? x.artist : x.artist + " · " + x.album).sora(12, .regular, .muted).lineLimit(1)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        Text(meta?[i] ?? fmt(x.dur)).mono(10).lineLimit(1).fixedSize()
                    }
                    .padding(.horizontal, 12).frame(minHeight: 58)
                    .topLine(i > 0 ? .line : .clear)
                }
                .plain()
            }
        }
        .skBox(.card, .line)
    }

    private func playlistHeader(_ p: (String, [Track])) -> some View {
        let a = art(p.0)
        let total = p.1.reduce(0) { $0 + $1.dur }
        return HStack(alignment: .bottom, spacing: 14) {
            ZStack(alignment: .bottomLeading) {
                ArtFill(a)
                Text(p.0).sora(15, .semibold, a.ink, lineHeight: 1.05).padding(10)
            }
            .frame(width: 120, height: 120)
            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
            VStack(alignment: .leading, spacing: 10) {
                VStack(alignment: .leading, spacing: 3) {
                    Text(p.0).sora(19, .semibold, lineHeight: 1.15)
                    Text("\(p.1.count) låter · \(total / 60) min").mono(10)
                }
                HStack(spacing: 8) {
                    SKPill(title: "Spill", primary: true) { m.playLib(p.1, 0) }
                    SKPill(title: "Tilfeldig", hPad: 14) { m.playLib(p.1.shuffled(), 0); m.shuffle = true }
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private var playlistRows: some View {
        VStack(spacing: 0) {
            ForEach(Array(pls.enumerated()), id: \.offset) { i, p in
                Button { m.libPl = i } label: {
                    HStack(spacing: 12) {
                        ArtFill(p.0).frame(width: 52, height: 52).clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                        VStack(alignment: .leading, spacing: 2) {
                            Text(p.0).sora(15)
                            Text("\(p.1.count) låter").sora(12, .regular, .muted)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        SKIcon(d: Icons.chevronRight, size: 16, stroke: 2, color: .muted)
                    }
                    .padding(.horizontal, 12).frame(minHeight: 68)
                    .topLine(i > 0 ? .line : .clear)
                }
                .plain()
            }
        }
        .skBox(.card, .line)
    }

    @ViewBuilder private var history: some View {
        let h = hist
        if h.isEmpty { Text("Ingen historikk ennå").sora(13, .regular, .muted) }
        if !h.isEmpty { trackList(h.map(\.track), meta: h.map(\.when), artistOnly: true) }
        Button { m.hist[m.lib] = [] } label: { Text("Tøm historikk").sora(13, .regular, .muted).padding(6) }
            .plain()
            .frame(maxWidth: .infinity)
    }

    // MARK: Discover (discVals)

    private struct Tile: Identifiable { var id: String { name + meta }; var name: String; var meta: String; var key: String; var label: String; var pick: () -> Void }
    private struct Shelf { var kicker: String; var title: String; var tiles: [Tile] }

    @ViewBuilder private var discover: some View {
        let feat: [(String, [Track])] = nd ? Array(albums.prefix(5)) : Array(pls.dropFirst()) + Array(pls.prefix(1))
        let fi = m.libHero % max(1, feat.count)
        let f = feat[fi]
        heroCard(f, fi: fi, count: feat.count)
        if !nd {
            EdgeScroll(spacing: 8) {
                ForEach(Array(SK.moods.enumerated()), id: \.offset) { j, n in
                    SKFilterChip(label: n, on: m.libMood == j) { m.libMood = m.libMood == j ? nil : j }
                }
            }
        }
        ForEach(Array(shelves.enumerated()), id: \.offset) { _, sh in
            VStack(alignment: .leading, spacing: 10) {
                SKSectionHeader(title: sh.title, size: 19, kicker: sh.kicker)
                EdgeScroll(spacing: 12) {
                    ForEach(Array(sh.tiles.enumerated()), id: \.offset) { _, t in tileView(t) }
                }
            }
        }
    }

    private func artists(_ l: [Track]) -> String {
        var seen: [String] = []
        for x in l where !seen.contains(x.artist) { seen.append(x.artist) }
        return seen.prefix(3).joined(separator: ", ")
    }

    private func heroCard(_ f: (String, [Track]), fi: Int, count: Int) -> some View {
        let a = art(f.0)
        let chips = nd ? ["\(f.1.count) låter", "FLAC", "44,1 kHz"] : ["Miks", "\(f.1.count) låter", "AAC 256"]
        let openF = { m.libPl = nd ? fi : (fi + 1) % pls.count }
        return VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .bottom, spacing: 14) {
                Button(action: openF) {
                    ZStack(alignment: .bottomLeading) {
                        ArtFill(a)
                        Text(f.0).sora(13, .semibold, a.ink, lineHeight: 1.05).multilineTextAlignment(.leading).padding(10)
                    }
                    .frame(width: 112, height: 112)
                    .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                    .shadow(color: .black.opacity(0.5), radius: 15, y: 14)
                }
                .plain()
                VStack(alignment: .leading, spacing: 6) {
                    Text(nd ? "NYLIG LAGT TIL" : "UTVALGT MIKS").mono(10, .accent2, em: 0.12)
                    Text(f.0).sora(21, .semibold, lineHeight: 1.1)
                    Text(nd ? (f.1.first?.artist ?? "") : artists(f.1)).sora(12, .regular, .ink2).lineLimit(1)
                    FlowLayout(spacing: 5) {
                        ForEach(chips, id: \.self) { c in
                            Text(c).mono(9, .ink).padding(.horizontal, 7).frame(height: 20)
                                .background(RoundedRectangle(cornerRadius: 5).fill(Color.white.opacity(0.09)))
                        }
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            HStack(spacing: 8) {
                SKPill(title: "Spill", primary: true, icon: Icons.play) { m.playLib(f.1, 0) }
                SKPill(title: "Legg i kø", hPad: 14, border: .off, bg: Color.bg.opacity(0.4)) { m.addQueue(f.1) }
                Spacer(minLength: 0)
                HStack(spacing: 4) {
                    ForEach(0..<count, id: \.self) { j in
                        Button { m.libHero = j } label: {
                            Capsule().fill(j == fi ? Color.accent : .off).frame(width: j == fi ? 18 : 6, height: 6)
                        }
                        .plain()
                    }
                }
            }
        }
        .padding(16)
        .background {
            ZStack {
                Color.card
                ArtFill(a).padding(-40).blur(radius: 40).opacity(0.5)
                LinearGradient(colors: [Color.bg.opacity(0.35), Color.bg.opacity(0.9)], startPoint: .top, endPoint: .bottom)
            }
        }
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
        .skBorder(.line, radius: 16)
    }

    private func tileView(_ t: Tile) -> some View {
        let a = art(t.key)
        return Button(action: t.pick) {
            VStack(alignment: .leading, spacing: 5) {
                ZStack(alignment: .bottomLeading) {
                    ArtFill(a)
                    Text(t.label).sora(14, .semibold, a.ink, lineHeight: 1.05)
                        .padding(.leading, 10).padding(.bottom, 10).padding(.trailing, 44)
                    SKIcon(d: Icons.play, size: 14, color: .ink, fill: true)
                        .frame(width: 30, height: 30)
                        .background(Circle().fill(Color.bg.opacity(0.72)))
                        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .bottomTrailing)
                        .padding(8)
                }
                .frame(width: 136, height: 136)
                .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                Text(t.name).sora(13).lineLimit(1)
                Text(t.meta).sora(11, .regular, .muted).lineLimit(1)
            }
            .frame(width: 136, alignment: .leading)
        }
        .plain()
    }

    private var shelves: [Shelf] {
        let lt = SK.lt, pls = self.pls, albums = self.albums
        let mi = m.libMood, mm = mi.map { $0 + 1 } ?? 0
        func rot<T>(_ a: [T]) -> [T] { a.isEmpty ? a : Array(a[(mm % a.count)...] + a[..<(mm % a.count)]) }
        func tr(_ list: [Track]) -> [Tile] {
            list.enumerated().map { i, x in Tile(name: x.t, meta: x.artist, key: x.album, label: "") { m.playLib(list, i) } }
        }
        let plT: ((String, [Track])) -> Tile = { p in
            let idx = pls.firstIndex { $0.0 == p.0 } ?? 0
            return Tile(name: p.0, meta: "\(p.1.count) låter · " + artists(p.1), key: p.0, label: p.0) { m.libPl = idx }
        }
        let alT: ((String, [Track])) -> Tile = { al in
            let idx = albums.firstIndex { $0.0 == al.0 } ?? 0
            return Tile(name: al.0, meta: al.1.first?.artist ?? "", key: al.0, label: "") { m.libPl = idx }
        }
        if nd {
            return [Shelf(kicker: "", title: "Nylig lagt til", tiles: albums.map(alT)),
                    Shelf(kicker: "", title: "Oppdag", tiles: albums.reversed().map(alT)),
                    Shelf(kicker: "FRA BIBLIOTEKET", title: "Mest spilt", tiles: tr(Array(lt[4..<12])))]
        }
        var again: [Track] = []
        for x in hist.map(\.track) + lt where !again.contains(where: { $0.t == x.t }) { again.append(x) }
        let forgotten = Array(rot(Array(lt.reversed())).prefix(8))
        return [Shelf(kicker: "SEBASTIAN", title: "Hør på nytt", tiles: tr(Array(again.prefix(8)))),
                Shelf(kicker: "", title: mi == nil ? "Mikser for deg" : "Mikser · " + SK.moods[mi!], tiles: rot(pls).map(plT)),
                Shelf(kicker: "", title: "Glemte favoritter", tiles: tr(forgotten))]
    }

    private func fmt(_ s: Int) -> String { "\(s / 60):" + String(format: "%02d", s % 60) }
}
