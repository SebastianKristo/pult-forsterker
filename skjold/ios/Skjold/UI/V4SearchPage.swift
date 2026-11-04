import SwiftUI

/// Søk (searchOn): #050506, «Søk i»-filter (ring 3 / opasitet .45), Spillelister, Låter, Radio. Søkefeltet nederst.
struct V4SearchPage: View {
    @Environment(AppModel.self) private var m
    @Environment(V4State.self) private var ui
    @FocusState private var focus: Bool
    @State private var hits: [String: [Track]] = [:]

    private static let srcs = ["YouTube Music", "Navidrome", "Plex", "Radio", "AirPlay"]
    private var q: String { ui.sq.trimmingCharacters(in: .whitespaces) }
    private func ok(_ s: String) -> Bool { ui.sSrc == nil || Self.srcs[ui.sSrc!] == s }

    var body: some View {
        ZStack(alignment: .bottom) {
            V4.searchBg.ignoresSafeArea()
            ScrollView(.vertical, showsIndicators: false) {
                VStack(alignment: .leading, spacing: 22) {
                    V4Title(text: "Søk")
                    if q.isEmpty { intro }
                    filter
                    results
                }
                .padding(.horizontal, 20).padding(.top, 6).padding(.bottom, 120)
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .scrollDismissesKeyboard(.interactively)
            field
        }
        .onAppear { focus = true }
        .task(id: q + "|\(ui.sSrc ?? -1)") { await run() }
        .onChange(of: q) { _, v in if ok("Radio") { m.setQ(v) } }
    }

    private var intro: some View {
        Text("Søk etter **låter, artister, album, spillelister** eller **radiokanaler** i alle tjenestene dine.")
            .sora(17, .regular, V4.ink2, lineHeight: 1.45)
            .fixedSize(horizontal: false, vertical: true)
    }

    private var filter: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .firstTextBaseline) {
                Text("Søk i").sora(17, .semibold)
                Spacer()
                Text(ui.sSrc.map { Self.srcs[$0] } ?? "Alle tjenester").sora(13, .regular, V4.muted)
            }
            V4Shelf(spacing: 12) {
                ForEach(Array(Self.srcs.enumerated()), id: \.offset) { i, s in
                    Button { Haptics.tick(); ui.sSrc = ui.sSrc == i ? nil : i } label: {
                        VStack(spacing: 7) {
                            V4SourceIcon(label: s, size: 62, ring: ui.sSrc == i ? 3 : 0)
                            Text(s == "YouTube Music" ? "YT Music" : s).sora(11, .regular, V4.ink2).lineLimit(1).fixedSize()
                        }
                        .frame(width: 66)
                        .opacity(ui.sSrc == nil || ui.sSrc == i ? 1 : 0.45)
                    }
                    .plain()
                }
            }
            .padding(.vertical, 2)
        }
    }

    // MARK: Resultater

    private var playlists: [V4Playlist] {
        let libs = ["ytm", "nd", "plex"].filter { ok(V4Lib.names[$0] ?? "") }
        let all = libs.flatMap { V4Lib.playlists(m, $0) }
        if q.isEmpty { return ui.sSrc == nil ? [] : all }
        return all.filter { $0.name.localizedCaseInsensitiveContains(q) || $0.owner.localizedCaseInsensitiveContains(q) }
    }

    private var tracks: [(lib: String, t: Track)] {
        guard !q.isEmpty else { return [] }
        var out: [(lib: String, t: Track)] = []
        for lib in ["ytm", "nd", "plex"] where ok(V4Lib.names[lib] ?? "") {
            for t in hits[lib] ?? [] { out.append((lib: lib, t: t)) }
        }
        return out
    }

    private var radio: [Station] {
        guard ok("Radio") else { return [] }
        if q.isEmpty { return ui.sSrc == 3 ? m.radio : [] }
        let favs = m.radio.filter { $0.name.localizedCaseInsensitiveContains(q) || $0.genre.localizedCaseInsensitiveContains(q) }
        let more = (m.rRes ?? []).map { Station(name: $0.name, genre: $0.genre, url: $0.url) }.filter { r in !favs.contains { $0.name == r.name } }
        return favs + more
    }

    @ViewBuilder private var results: some View {
        let pls = playlists, trs = tracks, rs = radio
        if !pls.isEmpty {
            VStack(alignment: .leading, spacing: 8) {
                V4Kicker(text: "SPILLELISTER")
                ForEach(pls, id: \.id) { p in
                    Button { ui.search = false; ui.pl = p } label: {
                        HStack(spacing: 14) {
                            V4Mosaic(keys: p.keys, size: 52, radius: 9)
                            VStack(alignment: .leading, spacing: 2) {
                                Text(p.name).sora(15, .semibold).lineLimit(1)
                                Text(p.src + " · \(p.count) låter").sora(12, .regular, V4.muted).lineLimit(1)
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)
                            V4Icon(d: V4.chevRight, size: 16, stroke: 2, color: V4.chev)
                        }
                        .padding(.vertical, 4)
                    }
                    .plain()
                }
            }
        }
        if !trs.isEmpty {
            VStack(alignment: .leading, spacing: 8) {
                V4Kicker(text: "LÅTER")
                ForEach(Array(trs.enumerated()), id: \.offset) { i, x in
                    HStack(spacing: 14) {
                        Button { play(trs, i) } label: {
                            HStack(spacing: 14) {
                                V4Art(key: x.t.album, radius: 9).frame(width: 52, height: 52)
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(x.t.t).sora(15, .semibold).lineLimit(1)
                                    HStack(spacing: 6) {
                                        V4SourceIcon(label: V4Lib.names[x.lib] ?? "", size: 14)
                                        Text(x.t.artist + " · " + (V4Lib.names[x.lib] ?? "")).sora(12, .regular, V4.muted).lineLimit(1)
                                    }
                                }
                                .frame(maxWidth: .infinity, alignment: .leading)
                            }
                        }
                        .plain()
                        V4MoreButton { ui.moreTrack = x.t; withAnimation(V4.moreSheet) { ui.more = true } }
                    }
                    .padding(.vertical, 4)
                }
            }
        }
        if !rs.isEmpty {
            VStack(alignment: .leading, spacing: 8) {
                V4Kicker(text: "RADIO")
                ForEach(rs, id: \.self) { st in
                    Button { m.playRadio(st) } label: {
                        HStack(spacing: 14) {
                            V4Art(key: st.name, radius: 9).frame(width: 52, height: 52)
                            VStack(alignment: .leading, spacing: 2) {
                                Text(st.name).sora(15, .semibold).lineLimit(1)
                                Text(st.genre).sora(12, .regular, V4.muted).lineLimit(1)
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)
                            Text("DIREKTE").mono(10, V4.gold, em: 0.1)
                        }
                        .padding(.vertical, 4)
                    }
                    .plain()
                }
            }
        }
        if !q.isEmpty && pls.isEmpty && trs.isEmpty && rs.isEmpty && !m.rBusy {
            Text("Fant ingenting for «\(q)».").sora(14, .regular, V4.muted)
        }
    }

    private func play(_ trs: [(lib: String, t: Track)], _ i: Int) {
        let lib = trs[i].lib
        let list = trs.filter { $0.lib == lib }.map(\.t)
        let idx = list.firstIndex(of: trs[i].t) ?? 0
        m.lib = lib
        m.playLib(list, idx, keepOpen: true)
    }

    private func run() async {
        guard !q.isEmpty else { hits = [:]; return }
        try? await Task.sleep(for: .milliseconds(350))
        guard !Task.isCancelled else { return }
        var out: [String: [Track]] = [:]
        for lib in ["nd", "plex", "ytm"] where ok(V4Lib.names[lib] ?? "") {
            if m.demo {
                out[lib] = SK.lt.filter { ($0.t + " " + $0.artist + " " + $0.album).localizedCaseInsensitiveContains(q) }.prefix(lib == "ytm" ? 6 : 3).map { $0 }
            } else if lib != "ytm" {
                out[lib] = await m.searchLib(lib, q)
            }
            guard !Task.isCancelled else { return }
        }
        hits = out
    }

    // MARK: Søkefelt nederst (54, glass) + lukk

    private var field: some View {
        HStack(spacing: 10) {
            HStack(spacing: 10) {
                V4Icon(d: V4.search, size: 20, stroke: 2.2, color: V4.ink)
                TextField("", text: Binding(get: { ui.sq }, set: { ui.sq = $0 }), prompt: Text("Søk").foregroundStyle(V4.muted))
                    .font(.sora(17)).foregroundStyle(V4.ink)
                    .focused($focus)
                    .autocorrectionDisabled().textInputAutocapitalization(.never)
                    .submitLabel(.search)
            }
            .padding(.horizontal, 18).frame(height: 54)
            .v4Glass(Capsule(), top: 0.12, bottom: 0.05, highlight: 0.35, shadowRadius: 15, shadowY: 10)
            Button { focus = false; ui.search = false; ui.sq = "" } label: {
                V4Icon(d: V4.close, size: 20, stroke: 2.4, color: V4.ink).frame(width: 54, height: 54)
                    .v4Glass(Circle(), top: 0.12, bottom: 0.05, highlight: 0.35, shadowRadius: 15, shadowY: 10)
            }
            .plain().accessibilityLabel("Lukk søk")
        }
        .padding(.horizontal, 12).padding(.bottom, 12)
    }
}
