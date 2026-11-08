import SwiftUI
import UIKit

/// Søk (searchOn): #050506, «Søk i»-filter (ring 3 / opasitet .45), Spillelister, Låter, Radio. Søkefeltet nederst.
struct V4SearchPage: View {
    @Environment(AppModel.self) private var m
    @Environment(V4State.self) private var ui
    @FocusState private var focus: Bool
    @State private var hits: [String: [Track]] = [:]
    /// Tastaturhøyden måles selv: siden ligger som overlegg i et ZStack over systemets TabView, og der flytter ikke
    /// SwiftUI innholdet opp automatisk – søkefeltet nederst ble liggende bak tastaturet.
    @State private var kb: CGFloat = 0
    /// Treff fra Music Assistant og NRK (via Skjold: /api/ma/search og /api/nrk/search).
    @State private var ext: [ExtHit] = []
    /// Svar fra «Spill noe til …» (POST /api/ask på Skjold).
    @State private var askMsg: String = ""

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
            field.padding(.bottom, kb)
        }
        .ignoresSafeArea(.keyboard, edges: .bottom)
        .onReceive(NotificationCenter.default.publisher(for: UIResponder.keyboardWillChangeFrameNotification)) { n in
            setKeyboard(n)
        }
        .onReceive(NotificationCenter.default.publisher(for: UIResponder.keyboardWillHideNotification)) { _ in
            withAnimation(.easeOut(duration: 0.25)) { kb = 0 }
        }
        .onAppear { focus = true }
        .task(id: q + "|\(ui.sSrc ?? -1)") { await run() }
        .onChange(of: q) { _, v in if ok("Radio") { m.setQ(v) } }
    }

    private func setKeyboard(_ n: Notification) {
        guard let end = n.userInfo?[UIResponder.keyboardFrameEndUserInfoKey] as? CGRect else { return }
        let screen = UIScreen.main.bounds.height
        let h = max(0, screen - end.minY)
        // tastaturet dekker også hjem-indikatoren; trekk fra den nederste trygge sonen så feltet ikke svever for høyt
        let bottomInset = UIApplication.shared.connectedScenes
            .compactMap { ($0 as? UIWindowScene)?.keyWindow?.safeAreaInsets.bottom }.first ?? 0
        let lift = h > 0 ? max(0, h - bottomInset) : 0
        withAnimation(.easeOut(duration: 0.25)) { kb = lift }
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
        if !q.isEmpty && !m.demo {
            VStack(alignment: .leading, spacing: 6) {
                Button { askPlay(q) } label: {
                    HStack(spacing: 10) {
                        V4Icon(d: V4.search, size: 18, stroke: 2.2, color: V4.gold)
                        Text("Spill noe til «\(q)»").sora(15, .semibold).lineLimit(1)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    .padding(.vertical, 6)
                }
                .plain()
                if !askMsg.isEmpty {
                    Text(askMsg).sora(12, .regular, V4.muted)
                }
            }
        }
        if !ext.isEmpty {
            VStack(alignment: .leading, spacing: 8) {
                V4Kicker(text: "MUSIC ASSISTANT OG NRK")
                ForEach(ext) { h in
                    Button { playExt(h) } label: {
                        HStack(spacing: 14) {
                            V4Art(key: h.title, radius: 9).frame(width: 52, height: 52)
                            VStack(alignment: .leading, spacing: 2) {
                                Text(h.title).sora(15, .semibold).lineLimit(1)
                                Text(h.sub).sora(12, .regular, V4.muted).lineLimit(1)
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)
                            Text(h.badge).mono(10, V4.gold, em: 0.1)
                        }
                        .padding(.vertical, 4)
                    }
                    .plain()
                }
            }
        }
        if !q.isEmpty && pls.isEmpty && trs.isEmpty && rs.isEmpty && ext.isEmpty && !m.rBusy {
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

    private func playExt(_ h: ExtHit) {
        let host = m.settingsHost
        let path = h.path
        let data = DeviceLink.json(h.body)
        Task { _ = await DeviceLink.shared.sendRaw(path, data, on: host, timeout: 12) }
    }

    private func askPlay(_ text: String) {
        let host = m.settingsHost
        let data = DeviceLink.json(["text": text])
        askMsg = "Finner noe …"
        Task {
            let d = await DeviceLink.shared.sendRaw("/api/ask", data, on: host, timeout: 60)
            var msg = "Fant ikke noe som passet"
            if let d = d, let o = try? JSONSerialization.jsonObject(with: d) as? [String: Any] {
                let ok = (o["ok"] as? Bool) ?? false
                let sum = (o["summary"] as? String) ?? ""
                if ok {
                    msg = "Spiller " + sum
                } else {
                    msg = ((o["error"] as? String) ?? msg) + " (" + sum + ")"
                }
            }
            askMsg = msg
        }
    }

    private func loadExt(_ query: String) async -> [ExtHit] {
        let host = m.settingsHost
        let enc = query.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? query
        var out: [ExtHit] = []
        if let d = await DeviceLink.shared.get("/api/ma/search?q=" + enc, on: host, timeout: 12) {
            out += ExtHit.fromMA(d)
        }
        if let d = await DeviceLink.shared.get("/api/nrk/search?q=" + enc, on: host, timeout: 12) {
            out += ExtHit.fromNRK(d)
        }
        return out
    }

    private func run() async {
        guard !q.isEmpty else { hits = [:]; ext = []; return }
        try? await Task.sleep(for: .milliseconds(350))
        guard !Task.isCancelled else { return }
        if !m.demo {
            let found = await loadExt(q)
            if !Task.isCancelled { ext = found }
        }
        var out: [String: [Track]] = [:]
        for lib in ["nd", "plex", "ytm"] where ok(V4Lib.names[lib] ?? "") {
            if m.demo {
                out[lib] = SK.lt.filter { ($0.t + " " + $0.artist + " " + $0.album).localizedCaseInsensitiveContains(q) }.prefix(lib == "ytm" ? 6 : 3).map { $0 }
            } else {
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


/// Ett treff fra Music Assistant (låt/album/spilleliste/podkast) eller NRK (episode). Spilles via Skjold.
struct ExtHit: Identifiable {
    let id: String
    let title: String
    let sub: String
    let badge: String
    let path: String
    let body: [String: Any]

    static func fromMA(_ data: Data) -> [ExtHit] {
        guard let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return [] }
        var out: [ExtHit] = []
        for key in ["tracks", "albums", "playlists", "podcasts"] {
            let list = obj[key] as? [[String: Any]] ?? []
            for item in list.prefix(key == "tracks" ? 8 : 4) {
                let uri = item["uri"] as? String ?? ""
                if uri.isEmpty { continue }
                let name = item["name"] as? String ?? ""
                let artist = item["artist"] as? String ?? ""
                let prov = item["provider"] as? String ?? "MA"
                let sub = artist.isEmpty ? prov : artist + " · " + prov
                out.append(ExtHit(id: "ma:" + uri, title: name, sub: sub, badge: prov.uppercased(),
                                  path: "/api/ma/play", body: ["uri": uri, "enqueue": "play"]))
            }
        }
        return out
    }

    static func fromNRK(_ data: Data) -> [ExtHit] {
        guard let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return [] }
        let eps = obj["episodes"] as? [[String: Any]] ?? []
        var out: [ExtHit] = []
        for e in eps.prefix(8) {
            let id = e["id"] as? String ?? ""
            if id.isEmpty { continue }
            let title = e["title"] as? String ?? ""
            let series = e["series"] as? String ?? ""
            let date = e["date"] as? String ?? ""
            var body: [String: Any] = ["id": id, "title": title, "series": series]
            if let img = e["image"] as? String { body["image"] = img }
            if let dur = e["duration"] as? Double { body["duration"] = dur }
            if let pod = e["podcast"] as? Bool { body["podcast"] = pod }
            let sub = series.isEmpty ? date : (date.isEmpty ? series : series + " · " + date)
            out.append(ExtHit(id: "nrk:" + id, title: title, sub: sub, badge: "NRK", path: "/api/nrk/play", body: body))
        }
        return out
    }
}
