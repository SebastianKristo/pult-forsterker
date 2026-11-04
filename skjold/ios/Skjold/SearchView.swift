import SwiftUI

/// v4 «Søk»: ett felt som søker i radiokanaler (norske + Radio Browser) og i musikktjenestene som er satt opp.
struct SearchView: View {
    @Environment(AppModel.self) private var m
    @State private var q = ""
    @State private var libRes: [String: [Track]] = [:]
    @State private var busy = false

    private let libNames: [String: String] = ["nd": "Navidrome", "plex": "Plex", "ytm": "YouTube Music"]

    var body: some View {
        SKBackButton(title: "Hjem") { m.sub = "" }
            .padding(.top, -6)
        SKField(placeholder: "Søk etter kanal, sang, artist eller album",
                text: Binding(get: { q }, set: { v in q = v; m.setQ(v) }), height: 44, size: 15)

        let t = q.trimmingCharacters(in: .whitespaces).lowercased()
        if t.isEmpty {
            Text("Søk i radiokanaler og i musikken din.").sora(13, .regular, .muted)
        } else {
            radioSection(t)
            ForEach(libOrder, id: \.self) { lib in
                let list = libRes[lib] ?? []
                if !list.isEmpty { libSection(lib, list) }
            }
            if busy { Text("Søker …").sora(12, .regular, .muted) }
            if !busy && nothingFound(t) { Text("Ingen treff").sora(13, .regular, .muted) }
        }
        Color.clear.frame(height: 0)
            .task(id: t) { await searchLibs(t) }
    }

    private var libOrder: [String] { ["nd", "plex", "ytm"] }

    private func stations(_ t: String) -> [Station] {
        let loc = SK.catalog.filter { ($0.name + " " + $0.genre).lowercased().contains(t) }
        let fav = m.radio.filter { s in s.name.lowercased().contains(t) && !loc.contains { $0.name == s.name } }
        let onl: [Station] = (m.rRes ?? []).compactMap { r in
            if loc.contains(where: { $0.name.lowercased() == r.name.lowercased() }) { return nil }
            let g = [r.genre, r.country].filter { !$0.isEmpty }.joined(separator: " · ")
            return Station(name: r.name, genre: g.isEmpty ? "Nettradio" : g, url: r.url)
        }
        return fav + loc + onl
    }

    private func nothingFound(_ t: String) -> Bool {
        stations(t).isEmpty && libRes.values.allSatisfy { $0.isEmpty } && !m.rBusy
    }

    @ViewBuilder private func radioSection(_ t: String) -> some View {
        let list = Array(stations(t).prefix(12))
        if !list.isEmpty || m.rBusy {
            VStack(alignment: .leading, spacing: 8) {
                SKMonoLabel(text: "RADIO")
                if m.rBusy { Text("Søker i Radio Browser …").sora(12, .regular, .muted) }
                VStack(spacing: 0) {
                    ForEach(Array(list.enumerated()), id: \.offset) { i, st in
                        stationRow(st, first: i == 0)
                    }
                }
                .skBox(.card, .line)
            }
        }
    }

    private func stationRow(_ st: Station, first: Bool) -> some View {
        let fav = m.favIndex(st.name) != nil
        return HStack(spacing: 12) {
            Button { m.playRadio(st) } label: {
                HStack(spacing: 12) {
                    ArtFill(st.name).frame(width: 40, height: 40)
                        .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                    VStack(alignment: .leading, spacing: 2) {
                        Text(st.name).sora(14).lineLimit(1)
                        Text(st.genre).sora(11, .regular, .muted).lineLimit(1)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
            .plain()
            Button { m.toggleFav(st) } label: {
                Text(fav ? "★" : "☆").font(.system(size: 16)).foregroundStyle(fav ? Color.accent2 : .muted)
                    .frame(width: 36, height: 36)
            }
            .plain()
            .accessibilityLabel(fav ? "Fjern fra favoritter" : "Legg til i favoritter")
        }
        .padding(.horizontal, 12).frame(minHeight: 56)
        .topLine(first ? .clear : .line)
    }

    private func libSection(_ lib: String, _ list: [Track]) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            SKMonoLabel(text: (libNames[lib] ?? lib).uppercased())
            VStack(spacing: 0) {
                ForEach(Array(list.prefix(10).enumerated()), id: \.offset) { i, x in
                    Button { m.lib = lib; m.playLib(list, i) } label: {
                        HStack(spacing: 10) {
                            ArtFill(x.album).frame(width: 42, height: 42)
                                .clipShape(RoundedRectangle(cornerRadius: 6, style: .continuous))
                            VStack(alignment: .leading, spacing: 2) {
                                Text(x.t).sora(14).lineLimit(1)
                                Text(x.artist + " · " + x.album).sora(12, .regular, .muted).lineLimit(1)
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)
                        }
                        .padding(.horizontal, 12).frame(minHeight: 58)
                        .topLine(i > 0 ? .line : .clear)
                    }
                    .plain()
                }
            }
            .skBox(.card, .line)
        }
    }

    private func searchLibs(_ t: String) async {
        guard !t.isEmpty else { libRes = [:]; busy = false; return }
        try? await Task.sleep(for: .milliseconds(400))
        guard !Task.isCancelled else { return }
        busy = true
        var out: [String: [Track]] = [:]
        for lib in libOrder {
            if m.demo {
                let pool = SK.lt
                out[lib] = lib == "plex" ? [] : pool.filter { ($0.t + " " + $0.artist + " " + $0.album).lowercased().contains(t) }
            } else {
                let r = await m.searchLib(lib, t)
                out[lib] = r
            }
            if Task.isCancelled { return }
        }
        libRes = out
        busy = false
    }
}
