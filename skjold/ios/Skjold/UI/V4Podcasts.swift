import SwiftUI

// Podkaster (/api/pod/*): Apple Podcasts-katalogen, NRK, Podme og egne RSS-adresser.
// Samme oppsett som web-appen (skjold/app/src/screens/podcasts.tsx). Favorittene lagres på enheten.
// Episoder fortsetter der du slapp.

// MARK: - Datatyper

/// En podkast. id: «apple:123», «nrk:serie», «rss:https://…» eller «podme:123».
nonisolated struct PodShow: Sendable, Hashable, Identifiable {
    var id = "", title = "", author = "", image = "", genre = "", src = "", kind = ""

    init() {}

    init?(_ d: [String: Any]) {
        id = PodAPI.str(d, "id")
        guard !id.isEmpty else { return nil }
        title = PodAPI.str(d, "title"); author = PodAPI.str(d, "author"); image = PodAPI.str(d, "image")
        genre = PodAPI.str(d, "genre"); kind = PodAPI.str(d, "kind")
        let s = PodAPI.str(d, "src")
        // Mangler kilden, står den først i id-en
        src = s.isEmpty ? (id.split(separator: ":").first.map(String.init) ?? "") : s
    }
}

/// En episode. nrk = true spilles via /api/nrk/play, ellers /api/pod/play.
nonisolated struct PodEpisode: Sendable, Hashable, Identifiable {
    var id = "", url = "", title = "", date = "", image = "", description = "", show = "", pid = ""
    var ts = 0, duration = 0, pos = 0
    var nrk = false, podcast = false, heard = false

    init() {}

    init?(_ d: [String: Any]) {
        id = PodAPI.str(d, "id")
        guard !id.isEmpty else { return nil }
        url = PodAPI.str(d, "url"); title = PodAPI.str(d, "title"); date = PodAPI.str(d, "date")
        image = PodAPI.str(d, "image"); description = PodAPI.str(d, "description"); show = PodAPI.str(d, "show")
        pid = PodAPI.str(d, "pid")
        ts = PodAPI.int(d, "ts"); duration = PodAPI.int(d, "duration"); pos = PodAPI.int(d, "pos")
        nrk = PodAPI.bool(d, "nrk"); podcast = PodAPI.bool(d, "podcast"); heard = PodAPI.bool(d, "heard")
    }
}

/// Fremdrift for en episode du har begynt på (/api/pod/continue).
nonisolated struct PodProg: Sendable, Hashable, Identifiable {
    var id = "", title = "", series = "", image = "", url = "", pid = ""
    var pos = 0, dur = 0, t = 0

    init?(_ d: [String: Any]) {
        id = PodAPI.str(d, "id")
        guard !id.isEmpty else { return nil }
        title = PodAPI.str(d, "title"); series = PodAPI.str(d, "series"); image = PodAPI.str(d, "image")
        url = PodAPI.str(d, "url"); pid = PodAPI.str(d, "pid")
        pos = PodAPI.int(d, "pos"); dur = PodAPI.int(d, "dur"); t = PodAPI.int(d, "t")
    }

    /// Som episode, så den spilles på samme måte.
    var episode: PodEpisode {
        var e = PodEpisode()
        e.id = id; e.url = url; e.title = title; e.show = series; e.image = image
        e.pid = pid; e.pos = pos; e.duration = dur
        return e
    }
}

nonisolated struct PodGenre: Sendable, Hashable, Identifiable {
    var id: Int
    var name: String
}

/// Podkastsiden: podkasten, beskrivelsen, om du følger den og episodene.
nonisolated struct PodDetail: Sendable, Equatable {
    var show: PodShow
    var description: String
    var fav: Bool
    var episodes: [PodEpisode]
}

nonisolated struct PodErr: Error, Sendable {
    var msg: String
}

// MARK: - API

/// REST mot /api/pod/* på Skjold-enheten. Alt tolkes leniently: felt som mangler, får standardverdier.
nonisolated enum PodAPI {
    static func str(_ d: [String: Any], _ k: String) -> String {
        (d[k] as? String) ?? (d[k] as? NSNumber)?.stringValue ?? ""
    }

    static func int(_ d: [String: Any], _ k: String) -> Int {
        if let n = d[k] as? NSNumber { return n.intValue }
        if let s = d[k] as? String { return Int(s) ?? Int(Double(s) ?? 0) }
        return 0
    }

    static func bool(_ d: [String: Any], _ k: String) -> Bool {
        (d[k] as? NSNumber)?.boolValue ?? false
    }

    private static func list(_ j: [String: Any], _ k: String) -> [[String: Any]] {
        (j[k] as? [Any] ?? []).compactMap { $0 as? [String: Any] }
    }

    /// Bare bokstaver, tall og -._~ står urørt. Resten kodes, også : / ? & i RSS-adresser.
    static func enc(_ s: String) -> String {
        let ok = CharacterSet(charactersIn: "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")
        return s.addingPercentEncoding(withAllowedCharacters: ok) ?? s
    }

    private static func call(_ host: String, _ path: String, method: String = "GET", body: [String: Any]? = nil,
                             timeout: TimeInterval = 15) async -> Result<[String: Any], PodErr> {
        guard let url = Net.url(host, path) else { return .failure(PodErr(msg: "Ugyldig adresse til Skjold")) }
        let data = body.flatMap { try? JSONSerialization.data(withJSONObject: $0) }
        guard let (d, code) = await Net.data(url, method: method, body: data, timeout: timeout) else {
            return .failure(PodErr(msg: "Fikk ikke kontakt med Skjold"))
        }
        let j = (try? JSONSerialization.jsonObject(with: d)) as? [String: Any]
        if code == 401 { return .failure(PodErr(msg: "Logg inn på Skjold-hjem")) }
        if code >= 300 {
            let e = (j?["error"] as? String) ?? ""
            return .failure(PodErr(msg: e.isEmpty ? "Skjold svarte med feil \(code)" : e.prefix(1).uppercased() + e.dropFirst()))
        }
        guard let j else { return .failure(PodErr(msg: "Uventet svar fra Skjold")) }
        return .success(j)
    }

    static func genres(_ host: String) async -> Result<[PodGenre], PodErr> {
        await call(host, "/api/pod/genres").map { j in
            list(j, "genres").compactMap { g in
                let n = str(g, "name")
                return n.isEmpty ? nil : PodGenre(id: int(g, "id"), name: n)
            }
        }
    }

    static func top(_ host: String, genre: Int) async -> Result<[PodShow], PodErr> {
        await call(host, "/api/pod/top?genre=\(genre)").map { list($0, "shows").compactMap(PodShow.init) }
    }

    static func search(_ host: String, _ q: String) async -> Result<[PodShow], PodErr> {
        await call(host, "/api/pod/search?q=" + enc(q)).map { list($0, "shows").compactMap(PodShow.init) }
    }

    static func show(_ host: String, _ s: PodShow, fresh: Bool) async -> Result<PodDetail, PodErr> {
        await call(host, "/api/pod/show?id=" + enc(s.id) + (fresh ? "&fresh=1" : ""), timeout: 20).map { j in
            var sh = PodShow(j) ?? s
            if sh.title.isEmpty { sh.title = s.title }
            if sh.image.isEmpty { sh.image = s.image }
            if sh.author.isEmpty { sh.author = s.author }
            return PodDetail(show: sh, description: clean(str(j, "description")), fav: bool(j, "fav"),
                             episodes: list(j, "episodes").compactMap(PodEpisode.init))
        }
    }

    static func favs(_ host: String) async -> Result<[PodShow], PodErr> {
        await call(host, "/api/pod/favs").map { list($0, "items").compactMap(PodShow.init) }
    }

    /// Følg (add) eller slutt å følge (remove). Svarer med hele lista.
    static func setFav(_ host: String, _ s: PodShow, on: Bool) async -> Result<[PodShow], PodErr> {
        let body: [String: Any] = on
            ? ["add": ["id": s.id, "title": s.title, "author": s.author, "image": s.image, "kind": s.kind]]
            : ["remove": s.id]
        return await call(host, "/api/pod/favs", method: "POST", body: body).map { list($0, "items").compactMap(PodShow.init) }
    }

    static func newEpisodes(_ host: String) async -> Result<[PodEpisode], PodErr> {
        await call(host, "/api/pod/new", timeout: 30).map { list($0, "items").compactMap(PodEpisode.init) }
    }

    static func cont(_ host: String) async -> Result<[PodProg], PodErr> {
        await call(host, "/api/pod/continue").map { list($0, "items").compactMap(PodProg.init) }
    }

    /// Spiller episoden på enheten. Gir tilbake hvor den fortsetter (sekunder), 0 = fra start.
    static func play(_ host: String, _ e: PodEpisode, show: PodShow?, restart: Bool) async -> Result<Int, PodErr> {
        let image = e.image.isEmpty ? (show?.image ?? "") : e.image
        let path: String
        var body: [String: Any]
        if e.nrk {
            path = "/api/nrk/play"
            body = ["id": e.id, "title": e.title, "series": e.show.isEmpty ? (show?.title ?? "") : e.show,
                    "image": image, "duration": e.duration, "podcast": e.podcast]
        } else {
            path = "/api/pod/play"
            body = ["id": e.id, "url": e.url, "title": e.title, "show": show?.title ?? e.show,
                    "image": image, "duration": e.duration, "pid": show?.id ?? e.pid]
        }
        if restart { body["restart"] = true }
        return await call(host, path, method: "POST", body: body, timeout: 15).map { int($0, "resume") }
    }

    /// Fjerner HTML-merker fra beskrivelser i RSS-feeder.
    static func clean(_ s: String) -> String {
        s.replacingOccurrences(of: "<[^>]+>", with: " ", options: .regularExpression)
            .replacingOccurrences(of: "&amp;", with: "&").replacingOccurrences(of: "&nbsp;", with: " ")
            .replacingOccurrences(of: "&quot;", with: "\"").replacingOccurrences(of: "&#39;", with: "'")
            .replacingOccurrences(of: "[ \\t]+", with: " ", options: .regularExpression)
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }

    /// «1 t 5 min» / «42 min».
    static func mins(_ s: Int) -> String {
        (s >= 3600 ? "\(s / 3600) t " : "") + "\(Int((Double(s % 3600) / 60).rounded())) min"
    }

    static let srcText: [String: String] = ["apple": "PODKAST", "nrk": "NRK", "rss": "RSS", "podme": "PODME"]
}

// MARK: - Avspilling

extension AppModel {
    /// Spiller en episode på den aktive enheten og sier hvor den fortsetter.
    func playPod(_ e: PodEpisode, show: PodShow? = nil, restart: Bool = false) {
        guard live, let h = activeHost else {
            Haptics.warning()
            showNotice("Koble til en Skjold-enhet for å spille podkaster")
            return
        }
        Haptics.thump()
        Task { [weak self] in
            let r = await PodAPI.play(h, e, show: show, restart: restart)
            guard let self else { return }
            switch r {
            case .success(let resume):
                self.showNotice(resume > 0 ? "Fortsetter fra " + PodAPI.mins(resume) : "Spiller " + e.title)
            case .failure(let x):
                Haptics.warning()
                self.showNotice(x.msg)
            }
        }
    }
}

// MARK: - Kildesiden

/// Kildesiden «Podkaster»: søk, Fortsett, Nye episoder, Mine podkaster, Podme og topplisten per sjanger.
struct V4PodcastPage: View {
    @Environment(AppModel.self) private var m
    @Environment(V4State.self) private var ui
    let wide: Bool

    @State private var genres: [PodGenre] = []
    @State private var genre = 0
    @State private var top: [PodShow]? = nil
    @State private var nye: [PodEpisode]? = nil
    @State private var cont: [PodProg] = []
    @State private var favs: [PodShow]? = nil
    @State private var res: [PodShow]? = nil
    @State private var err = ""
    @State private var shown: PodShow? = nil

    private var q: String { ui.srcQ.trimmingCharacters(in: .whitespaces) }
    private var host: String? { m.live ? m.activeHost : nil }
    private var favKey: String? { favs.map { $0.map(\.id).joined(separator: ",") } }
    private var podme: [PodShow] { (favs ?? []).filter { $0.src == "podme" }.reversed() }
    private var mine: [PodShow] { (favs ?? []).filter { $0.src != "podme" }.reversed() }

    var body: some View {
        ZStack {
            main
            if let s = shown {
                V4PodShowPage(show: s, wide: wide, favs: $favs) { shown = nil }
                    .transition(.move(edge: .trailing))
                    .zIndex(1)
            }
        }
        .animation(V4.dock, value: shown)
    }

    private var main: some View {
        ScrollView(.vertical, showsIndicators: false) {
            VStack(alignment: .leading, spacing: 22) {
                Button { close() } label: {
                    V4Icon(d: V4.back, size: 20, stroke: 2.4, color: V4.ink).frame(width: 46, height: 46).v4GlassButton(Circle())
                }
                .plain().accessibilityLabel("Tilbake")
                head
                if host == nil {
                    emptyText(m.demo ? "Podkaster spilles fra Skjold-enheten. Koble til en enhet for å bla i og spille podkaster."
                                     : "Ingen Skjold-enhet er valgt. Velg et rom for å bla i podkaster.")
                } else {
                    searchField
                    if !err.isEmpty { Text(err).sora(13, .regular, V4.red) }
                    if q.isEmpty { browse } else { results }
                }
            }
            .padding(.horizontal, wide ? 40 : 20).padding(.top, 6).padding(.bottom, wide ? 130 : 230)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .scrollDismissesKeyboard(.interactively)
        .onScrollGeometryChange(for: CGFloat.self) { $0.contentOffset.y + $0.contentInsets.top } action: { _, y in
            if !wide { ui.scrolled(y) }
        }
        .refreshable { await loadAll(); await loadTop() }
        .background(alignment: .top) { V4PodGlow() }
        .background(V4.bg.ignoresSafeArea())
        .task(id: host) { await loadAll() }
        .task(id: (host ?? "") + "|\(genre)") { await loadTop() }
        .task(id: favKey) { await loadNew() }
        .task(id: q) { await search() }
    }

    // MARK: Topp

    private var head: some View {
        HStack(spacing: 16) {
            V4SourceIcon(label: V4Pod.name, size: 72).shadow(color: .black.opacity(0.4), radius: 15, y: 10)
            VStack(alignment: .leading, spacing: 4) {
                Text(V4Pod.name).sora(30, .bold).tracking(-0.6).lineLimit(1).minimumScaleFactor(0.7)
                HStack(spacing: 7) {
                    Circle().fill(host == nil ? V4.muted : V4.goldDark).frame(width: 7, height: 7)
                    Text(host == nil ? "Ikke koblet til" : "Spilles i " + m.v4GroupName)
                        .sora(13, .regular, V4.ink.opacity(0.75)).lineLimit(1)
                }
            }
        }
    }

    private var searchField: some View {
        HStack(spacing: 10) {
            V4Icon(d: V4.search, size: 18, stroke: 2, color: V4.body)
            TextField("", text: Binding(get: { ui.srcQ }, set: { ui.srcQ = $0 }),
                      prompt: Text("Søk i alle podkaster, eller lim inn en RSS-adresse").foregroundStyle(V4.muted))
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
        .frame(maxWidth: wide ? 560 : .infinity)
        .v4GlassButton(Capsule())
    }

    // MARK: Søk

    @ViewBuilder private var results: some View {
        if let res {
            if res.isEmpty {
                emptyText("Fant ingen podkaster for «\(q)».")
            } else {
                VStack(alignment: .leading, spacing: 12) {
                    V4ShelfHeader(title: "Treff", kicker: "\(res.count) PODKASTER")
                    grid(res, ranked: false)
                }
            }
        } else {
            emptyText("Søker …")
        }
    }

    private func search() async {
        guard let h = host, !q.isEmpty else { res = nil; return }
        res = nil
        try? await Task.sleep(for: .milliseconds(400))
        guard !Task.isCancelled else { return }
        let r = await PodAPI.search(h, q)
        guard !Task.isCancelled else { return }
        switch r {
        case .success(let v): res = v; err = ""
        case .failure(let x): res = []; err = x.msg
        }
    }

    // MARK: Bla

    @ViewBuilder private var browse: some View {
        if !cont.isEmpty { contShelf }
        if let nye, !nye.isEmpty {
            VStack(alignment: .leading, spacing: 6) {
                V4ShelfHeader(title: "Nye episoder", kicker: "FRA PODKASTENE DU FØLGER")
                ForEach(Array(nye.prefix(8).enumerated()), id: \.offset) { _, e in
                    V4PodEpisodeRow(e: e, show: nil)
                }
            }
        }
        VStack(alignment: .leading, spacing: 12) {
            V4ShelfHeader(title: "Mine podkaster", kicker: "VISES OGSÅ PÅ SKJOLD TOUCH")
            if favs == nil {
                Text("Henter …").sora(13, .regular, V4.muted)
            } else if mine.isEmpty {
                emptyText("Ingen podkaster ennå. Åpne en podkast og trykk Følg.")
            } else {
                shelf(mine)
            }
        }
        if !podme.isEmpty {
            VStack(alignment: .leading, spacing: 12) {
                V4ShelfHeader(title: "Podme", kicker: "FRA PODME-KONTOEN")
                shelf(podme)
            }
        }
        topList
    }

    private var contShelf: some View {
        VStack(alignment: .leading, spacing: 12) {
            V4ShelfHeader(title: "Fortsett", kicker: "DER DU SLAPP")
            V4Shelf(spacing: 12) {
                ForEach(cont) { p in
                    Button { m.playPod(p.episode) } label: {
                        VStack(alignment: .leading, spacing: 6) {
                            V4PodArt(image: p.image, name: p.series.isEmpty ? p.title : p.series, radius: 14).frame(width: 132, height: 132)
                            Text(p.title.isEmpty ? "Episode" : p.title).sora(13, .semibold).lineLimit(1)
                            Text(p.series).sora(12, .regular, V4.muted).lineLimit(1)
                            V4PodBar(pos: p.pos, dur: p.dur)
                        }
                        .frame(width: 132, alignment: .leading)
                    }
                    .plain()
                }
            }
        }
    }

    private var allGenres: [PodGenre] {
        genres.contains { $0.id == 0 } ? genres : [PodGenre(id: 0, name: "Alle")] + genres
    }

    private var topList: some View {
        VStack(alignment: .leading, spacing: 12) {
            V4ShelfHeader(title: "Topplisten", kicker: "MEST LYTTET I NORGE NÅ")
            if !genres.isEmpty {
                V4Shelf(spacing: 8) {
                    ForEach(allGenres) { g in
                        let on = genre == g.id
                        Button { Haptics.tick(); genre = g.id } label: {
                            Text(g.name).sora(13, .regular, on ? V4.gold : V4.ink).lineLimit(1).fixedSize()
                                .padding(.horizontal, 14).frame(height: 36)
                                .background(Capsule().fill(on ? V4.selBg : V4.card))
                                .overlay(Capsule().strokeBorder(on ? V4.goldDark : V4.line2, lineWidth: 1))
                        }
                        .plain()
                    }
                }
            }
            if let top {
                if top.isEmpty { emptyText("Topplisten er tom akkurat nå.") } else { grid(Array(top.prefix(60)), ranked: true) }
            } else {
                Text("Henter topplisten …").sora(13, .regular, V4.muted)
            }
        }
    }

    // MARK: Fliser

    private func shelf(_ shows: [PodShow]) -> some View {
        V4Shelf(spacing: 12) {
            ForEach(shows) { s in V4PodTile(s: s, w: 132) { shown = $0 } }
        }
    }

    private func grid(_ shows: [PodShow], ranked: Bool) -> some View {
        LazyVGrid(columns: [GridItem(.adaptive(minimum: wide ? 150 : 100, maximum: 220), spacing: 14, alignment: .top)],
                  alignment: .leading, spacing: 18) {
            ForEach(Array(shows.enumerated()), id: \.offset) { i, s in
                V4PodTile(s: s, rank: ranked ? i + 1 : nil) { shown = $0 }
            }
        }
    }

    private func emptyText(_ t: String) -> some View {
        Text(t).sora(14, .regular, V4.muted, lineHeight: 1.45).fixedSize(horizontal: false, vertical: true)
    }

    // MARK: Lasting

    private func loadAll() async {
        guard let h = host else { return }
        async let g = PodAPI.genres(h)
        async let f = PodAPI.favs(h)
        async let c = PodAPI.cont(h)
        let (gr, fr, cr) = await (g, f, c)
        if let v = try? gr.get() { genres = v }
        favs = (try? fr.get()) ?? favs ?? []
        if let v = try? cr.get() { cont = v }
    }

    private func loadTop() async {
        guard let h = host else { return }
        top = nil
        let r = await PodAPI.top(h, genre: genre)
        guard !Task.isCancelled else { return }
        switch r {
        case .success(let v): top = v; err = ""
        case .failure(let x): top = []; err = x.msg
        }
    }

    private func loadNew() async {
        guard let h = host, favs != nil else { return }
        let r = await PodAPI.newEpisodes(h)
        guard !Task.isCancelled else { return }
        nye = (try? r.get()) ?? []
    }

    private func close() { ui.src = nil; ui.srcQ = "" }
}

// MARK: - Podkastsiden

/// Én podkast: omslag, beskrivelse, Følg/Følger, Spill nyeste og episodene (dato, lengde, fremdrift, hørt).
struct V4PodShowPage: View {
    @Environment(AppModel.self) private var m
    @Environment(V4State.self) private var ui
    let show: PodShow
    let wide: Bool
    @Binding var favs: [PodShow]?
    let close: () -> Void

    @State private var detail: PodDetail? = nil
    @State private var err = ""
    @State private var n = 40
    @State private var more = false
    @State private var busy = false

    private var h: PodShow { detail?.show ?? show }
    private var fav: Bool { favs?.contains { $0.id == show.id } ?? detail?.fav ?? false }
    private var host: String? { m.live ? m.activeHost : nil }

    var body: some View {
        ScrollView(.vertical, showsIndicators: false) {
            VStack(alignment: .leading, spacing: 18) {
                Button(action: close) {
                    V4Icon(d: V4.back, size: 20, stroke: 2.4, color: V4.ink).frame(width: 46, height: 46).v4GlassButton(Circle())
                }
                .plain().accessibilityLabel("Tilbake")
                header
                buttons
                if let d = detail?.description, !d.isEmpty { descText(d) }
                if !err.isEmpty { Text(err).sora(13, .regular, V4.red) }
                episodes
            }
            .padding(.horizontal, 20).padding(.top, 6).padding(.bottom, wide ? 130 : 240)
            .frame(maxWidth: wide ? 760 : .infinity, alignment: .leading)
            .frame(maxWidth: .infinity)
        }
        .onScrollGeometryChange(for: CGFloat.self) { $0.contentOffset.y + $0.contentInsets.top } action: { _, y in
            if !wide { ui.scrolled(y) }
        }
        .refreshable { await load(fresh: true) }
        .background(alignment: .top) { V4PodGlow() }
        .background(V4.bg.ignoresSafeArea())
        .task(id: show.id) { await load(fresh: false) }
    }

    private var header: some View {
        let layout = wide ? AnyLayout(HStackLayout(alignment: .bottom, spacing: 22)) : AnyLayout(VStackLayout(alignment: .leading, spacing: 16))
        return layout {
            V4PodArt(image: h.image, name: h.title, radius: 18)
                .frame(width: wide ? 200 : 220, height: wide ? 200 : 220)
                .shadow(color: .black.opacity(0.5), radius: 30, y: 24)
                .frame(maxWidth: wide ? nil : .infinity)
            VStack(alignment: .leading, spacing: 6) {
                Text(kicker).mono(10, V4.muted, em: 0.12).lineLimit(1)
                Text(h.title).sora(30, .bold, lineHeight: 1.1).tracking(-0.6).lineLimit(3)
                if let d = detail { Text("\(d.episodes.count) episoder").sora(13, .regular, V4.ink.opacity(0.72)) }
            }
        }
    }

    private var kicker: String {
        let s = PodAPI.srcText[show.src] ?? "PODKAST"
        return h.author.isEmpty || show.src == "nrk" ? s : s + " · " + h.author.uppercased()
    }

    private var buttons: some View {
        HStack(spacing: 12) {
            if let first = detail?.episodes.first {
                Button { m.playPod(first, show: h) } label: {
                    HStack(spacing: 10) {
                        V4PlayIcon(playing: false, size: 18, color: V4.bg)
                        Text("Spill nyeste").sora(15, .semibold, V4.bg).lineLimit(1)
                    }
                    .padding(.leading, 16).padding(.trailing, 20).frame(height: 48)
                    .background(Capsule().fill(V4.ink))
                }
                .plain()
            }
            Button { Task { await toggleFav() } } label: {
                HStack(spacing: 8) {
                    V4Icon(d: fav ? V4.check : V4.plus, size: 16, stroke: 2.4, color: fav ? V4.gold : V4.ink)
                    Text(fav ? "Følger" : "Følg").sora(15, .semibold, fav ? V4.gold : V4.ink)
                }
                .padding(.horizontal, 18).frame(height: 48)
                .background(Capsule().fill(fav ? V4.selBg : Color.clear))
                .overlay(Capsule().strokeBorder(fav ? V4.goldDark : V4.line2, lineWidth: 1))
                .opacity(busy ? 0.5 : 1)
            }
            .plain().disabled(busy || host == nil)
            .accessibilityLabel(fav ? "Følger, trykk for å slutte å følge" : "Følg")
        }
    }

    private func descText(_ d: String) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(d).sora(14, .regular, V4.body, lineHeight: 1.5)
                .lineLimit(more ? nil : 4)
                .fixedSize(horizontal: false, vertical: true)
            if d.count > 220 {
                Button { Haptics.tap(); withAnimation(V4.fade) { more.toggle() } } label: {
                    Text(more ? "Vis mindre" : "Vis mer").sora(13, .semibold, V4.gold)
                }
                .plain()
            }
        }
    }

    @ViewBuilder private var episodes: some View {
        if let d = detail {
            if d.episodes.isEmpty {
                Text("Ingen episoder tilgjengelig akkurat nå.").sora(14, .regular, V4.muted)
            } else {
                VStack(alignment: .leading, spacing: 4) {
                    V4ShelfHeader(title: "Episoder")
                    ForEach(Array(d.episodes.prefix(n).enumerated()), id: \.offset) { _, e in
                        V4PodEpisodeRow(e: e, show: h)
                    }
                    if d.episodes.count > n {
                        Button { Haptics.tap(); n += 60 } label: {
                            Text("Vis flere episoder (\(d.episodes.count - n))").sora(14, .regular, V4.ink)
                                .padding(.horizontal, 16).frame(height: 40)
                                .overlay(Capsule().strokeBorder(V4.line2, lineWidth: 1))
                        }
                        .plain().padding(.top, 10)
                    }
                }
            }
        } else if err.isEmpty {
            Text("Henter episoder …").sora(14, .regular, V4.muted)
        }
    }

    private func load(fresh: Bool) async {
        guard let host else { err = "Koble til en Skjold-enhet for å se episodene."; return }
        if !fresh { detail = nil; n = 40 }
        let r = await PodAPI.show(host, show, fresh: fresh)
        guard !Task.isCancelled else { return }
        switch r {
        case .success(let d): detail = d; err = ""
        case .failure(let x): err = x.msg
        }
    }

    private func toggleFav() async {
        guard let host, !busy else { return }
        let on = !fav
        busy = true
        Haptics.tick()
        var s = show
        s.title = h.title; s.image = h.image; s.author = h.author
        let r = await PodAPI.setFav(host, s, on: on)
        busy = false
        switch r {
        case .success(let items):
            favs = items
            Haptics.success()
            m.showNotice(on ? "Følger «\(h.title)». Vises også på Skjold Touch." : "Følger ikke lenger «\(h.title)»")
        case .failure(let x):
            Haptics.warning()
            m.showNotice(x.msg)
        }
    }
}

// MARK: - Byggeklosser

enum V4Pod {
    /// Navnet på kilden i Kilder og på kildesiden.
    static let name = "Podkaster"
}

/// Ikonet i Kilder: lilla flate med antenne (SF Symbol).
struct V4PodMark: View {
    var body: some View {
        GeometryReader { g in
            ZStack {
                LinearGradient(colors: [V4.pod, V4.podDark], startPoint: .top, endPoint: .bottom)
                Image(systemName: "antenna.radiowaves.left.and.right")
                    .resizable().scaledToFit()
                    .fontWeight(.semibold)
                    .foregroundStyle(V4.ink)
                    .frame(width: g.size.width * 0.52, height: g.size.height * 0.52)
            }
            .frame(width: g.size.width, height: g.size.height)
        }
    }
}

/// Lilla glød øverst, som kildefargen på de andre kildesidene.
private struct V4PodGlow: View {
    var body: some View {
        RadialGradient(colors: [V4.pod.opacity(0.33), .clear], center: UnitPoint(x: 0.2, y: 0), startRadius: 0, endRadius: 330)
            .frame(height: 420)
            .ignoresSafeArea(edges: .top)
            .allowsHitTesting(false)
    }
}

/// Omslag fra enheten eller nettet. Uten bilde, eller mens det lastes, vises fargeforløpet (ArtFill).
struct V4PodArt: View {
    @Environment(AppModel.self) private var m
    let image: String
    let name: String
    var radius: CGFloat = 12

    private var url: URL? {
        guard !image.isEmpty else { return nil }
        return URL(string: DeviceLink.shared.coverURL(image, on: m.activeHost))
    }

    var body: some View {
        Color.clear
            .overlay {
                if let url {
                    AsyncImage(url: url) { phase in
                        if case .success(let img) = phase { img.resizable().scaledToFill() } else { ArtFill(name) }
                    }
                } else {
                    ArtFill(name)
                }
            }
            .clipShape(RoundedRectangle(cornerRadius: radius, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: radius, style: .continuous).strokeBorder(Color.white.opacity(0.06), lineWidth: 1))
    }
}

/// Tynn fremdriftslinje. Vises bare når episoden er påbegynt.
struct V4PodBar: View {
    let pos: Int
    let dur: Int
    var body: some View {
        if pos > 0 && dur > 0 {
            Capsule().fill(V4.line2).frame(height: 3)
                .overlay(alignment: .leading) {
                    GeometryReader { g in
                        Capsule().fill(V4.goldDark).frame(width: g.size.width * min(1, CGFloat(pos) / CGFloat(dur)))
                    }
                }
        }
    }
}

/// Flis for en podkast: omslag, tittel og forfatter. Med rank vises plassen på topplisten.
struct V4PodTile: View {
    let s: PodShow
    var w: CGFloat? = nil
    var rank: Int? = nil
    let onOpen: (PodShow) -> Void

    var body: some View {
        Button { Haptics.tap(); onOpen(s) } label: {
            VStack(alignment: .leading, spacing: 6) {
                Color.clear.aspectRatio(1, contentMode: .fit)
                    .overlay { V4PodArt(image: s.image, name: s.title, radius: 14) }
                    .overlay(alignment: .topLeading) {
                        if let rank {
                            Text("\(rank)").mono(10, V4.ink)
                                .padding(.horizontal, 5).frame(minWidth: 22, minHeight: 20)
                                .background(RoundedRectangle(cornerRadius: 6, style: .continuous).fill(V4.bg.opacity(0.78)))
                                .padding(6)
                        }
                    }
                Text(s.title).sora(13, .semibold).lineLimit(1)
                Text(s.author.isEmpty ? (PodAPI.srcText[s.src] ?? "") : s.author).sora(12, .regular, V4.muted).lineLimit(1)
            }
            .frame(width: w, alignment: .leading)
            .frame(maxWidth: w == nil ? .infinity : nil, alignment: .leading)
            .contentShape(Rectangle())
        }
        .plain()
    }
}

/// Episoderad: omslag, tittel, dato · lengde · Hørt/Fortsett, fremdrift og «Fra start».
struct V4PodEpisodeRow: View {
    @Environment(AppModel.self) private var m
    let e: PodEpisode
    let show: PodShow?

    private var cur: Bool { !e.title.isEmpty && m.dev?.title == e.title }

    private var meta: String {
        [show == nil ? e.show : "", e.date, e.duration > 0 ? PodAPI.mins(e.duration) : "",
         e.heard ? "Hørt" : e.pos > 0 ? "Fortsett" : ""].filter { !$0.isEmpty }.joined(separator: " · ")
    }

    var body: some View {
        HStack(spacing: 12) {
            Button { m.playPod(e, show: show) } label: {
                HStack(spacing: 14) {
                    V4PodArt(image: e.image.isEmpty ? (show?.image ?? "") : e.image,
                             name: e.show.isEmpty ? (show?.title ?? e.title) : e.show, radius: 10)
                        .frame(width: 56, height: 56)
                    VStack(alignment: .leading, spacing: 4) {
                        Text(e.title).sora(15, .semibold, cur ? V4.gold : e.heard ? V4.muted : V4.ink).lineLimit(2)
                        Text(meta).sora(12, .regular, V4.muted).lineLimit(1)
                        if !e.heard { V4PodBar(pos: e.pos, dur: e.duration) }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
                .contentShape(Rectangle())
            }
            .plain()
            .accessibilityLabel("Spill " + e.title)
            if e.pos > 0 {
                Button { m.playPod(e, show: show, restart: true) } label: {
                    Text("Fra start").sora(12, .regular, V4.ink2)
                        .padding(.horizontal, 10).frame(height: 32)
                        .overlay(Capsule().strokeBorder(V4.line2, lineWidth: 1))
                }
                .plain()
                .accessibilityLabel("Spill fra start")
            }
        }
        .padding(.vertical, 6)
    }
}
