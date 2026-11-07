import AppIntents
import Foundation

// Siri og Snarveier: «Hei Siri, spill NRK Jazz med Skjold», «Skru opp volumet i Skjold», «Hva spiller på Skjold».
// Intentene kjører i bakgrunnen uten å åpne appen og snakker direkte med Skjold-daemonen (port 8765) – lokalt eller
// via Skjold-hjem-reléet (samme informasjonskapsel som appen). Rom = enhetene appen kjenner («skjold-known»);
// uten valgt rom brukes enheten appen styrer nå («skjold-host»). Alt er `nonisolated` (målet har MainActor som standard).

// MARK: - Klient

nonisolated enum SiriSkjold {
    struct Dev: Decodable, Sendable { var host: String; var id: String; var name: String; var product: String }

    /// Kjente enheter, lagret av appen (KnownDevice i LiveSync.swift – samme JSON-felter).
    static func devices() -> [Dev] {
        guard let d = UserDefaults.standard.data(forKey: "skjold-known"),
              let l = try? JSONDecoder().decode([Dev].self, from: d) else { return [] }
        return l
    }

    static var activeHost: String? {
        let h = UserDefaults.standard.string(forKey: "skjold-host") ?? ""
        if !h.isEmpty { return h }
        return devices().first?.host
    }

    static func host(_ rom: RomEntity?) -> String? { rom?.id ?? activeHost }

    static func url(_ base: String, _ path: String) -> URL? {
        var b = base.trimmingCharacters(in: .whitespaces)
        if !b.lowercased().hasPrefix("http") { b = "http://" + b }
        while b.hasSuffix("/") { b.removeLast() }
        return URL(string: b + path)
    }

    static func request(_ host: String, _ path: String, body: [String: Any]? = nil, timeout: TimeInterval = 8) async -> Data? {
        HjemAPI.restoreCookie()   // fjerntilgang via Skjold-hjem bruker samme innloggings-informasjonskapsel som appen
        guard let u = url(host, path) else { return nil }
        var req = URLRequest(url: u, timeoutInterval: timeout)
        req.cachePolicy = .reloadIgnoringLocalCacheData
        if let body {
            req.httpMethod = "POST"
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
            req.httpBody = try? JSONSerialization.data(withJSONObject: body)
        }
        guard let (d, r) = try? await URLSession.shared.data(for: req), let http = r as? HTTPURLResponse,
              (200..<300).contains(http.statusCode), !HjemAPI.accessBlocked(http) else { return nil }
        return d
    }

    static func post(_ host: String?, _ path: String, _ body: [String: Any] = [:]) async -> Bool {
        guard let host else { return false }
        return await request(host, path, body: body) != nil
    }

    static func json(_ host: String?, _ path: String) async -> [String: Any]? {
        guard let host, let d = await request(host, path) else { return nil }
        return try? JSONSerialization.jsonObject(with: d) as? [String: Any]
    }

    static func roomName(_ host: String?) -> String {
        guard let host else { return "Skjold" }
        return devices().first { $0.host == host }?.name ?? "Skjold"
    }

    static var offline: IntentDialog { "Fikk ikke kontakt med Skjold. Sjekk at appen har en enhet og at du er på samme nett eller har fjerntilgang." }
}

// MARK: - Entiteter

nonisolated struct RomEntity: AppEntity, Sendable {
    static var typeDisplayRepresentation: TypeDisplayRepresentation { "Rom" }
    static var defaultQuery: RomQuery { RomQuery() }
    var id: String          // vert ("ip:port" eller relé-adresse)
    var name: String
    var displayRepresentation: DisplayRepresentation { DisplayRepresentation(title: "\(name)") }
}

nonisolated struct RomQuery: EntityStringQuery {
    init() {}
    private func all() -> [RomEntity] { SiriSkjold.devices().map { RomEntity(id: $0.host, name: $0.name.isEmpty ? $0.id : $0.name) } }
    func entities(for identifiers: [String]) async throws -> [RomEntity] { all().filter { identifiers.contains($0.id) } }
    func suggestedEntities() async throws -> [RomEntity] { all() }
    func entities(matching string: String) async throws -> [RomEntity] {
        let q = string.lowercased().trimmingCharacters(in: .whitespaces)
        return all().filter { $0.name.lowercased().contains(q) || q.contains($0.name.lowercased()) }
    }
}

nonisolated struct FavorittEntity: AppEntity, Sendable {
    static var typeDisplayRepresentation: TypeDisplayRepresentation { "Radiofavoritt" }
    static var defaultQuery: FavorittQuery { FavorittQuery() }
    var id: String          // kanalnavnet – samme favoritt heter det samme i alle rom
    var n: Int
    var displayRepresentation: DisplayRepresentation { DisplayRepresentation(title: "\(id)", subtitle: "Favoritt \(n)") }
}

nonisolated struct FavorittQuery: EntityStringQuery {
    init() {}
    static func load(_ host: String?) async -> [FavorittEntity] {
        guard let j = await SiriSkjold.json(host, "/api/presets"), let ps = j["presets"] as? [Any] else { return [] }
        var out: [FavorittEntity] = []
        for (i, p) in ps.enumerated() {
            guard let p = p as? [String: Any], let t = p["title"] as? String, !t.isEmpty else { continue }
            let n = (p["n"] as? NSNumber)?.intValue ?? (i + 1)
            if !out.contains(where: { $0.id == t }) { out.append(FavorittEntity(id: t, n: n)) }
        }
        return out
    }
    func entities(for identifiers: [String]) async throws -> [FavorittEntity] {
        let all = await Self.load(SiriSkjold.activeHost)
        return identifiers.map { id in all.first { $0.id == id } ?? FavorittEntity(id: id, n: 0) }
    }
    func suggestedEntities() async throws -> [FavorittEntity] { await Self.load(SiriSkjold.activeHost) }
    func entities(matching string: String) async throws -> [FavorittEntity] {
        let q = string.lowercased()
        return await Self.load(SiriSkjold.activeHost).filter { $0.id.lowercased().contains(q) || q.contains($0.id.lowercased()) }
    }
}

nonisolated struct RutineEntity: AppEntity, Sendable {
    static var typeDisplayRepresentation: TypeDisplayRepresentation { "Rutine" }
    static var defaultQuery: RutineQuery { RutineQuery() }
    var id: String
    var navn: String
    var displayRepresentation: DisplayRepresentation { DisplayRepresentation(title: "\(navn)") }
}

nonisolated struct RutineQuery: EntityStringQuery {
    init() {}
    static func load() async -> [RutineEntity] {
        guard let j = await SiriSkjold.json(SiriSkjold.activeHost, "/api/routines"), let rs = j["routines"] as? [Any] else { return [] }
        return rs.compactMap { r in
            guard let r = r as? [String: Any], let id = r["id"] as? String else { return nil }
            return RutineEntity(id: id, navn: (r["navn"] as? String) ?? id)
        }
    }
    func entities(for identifiers: [String]) async throws -> [RutineEntity] {
        let all = await Self.load()
        return identifiers.map { id in all.first { $0.id == id } ?? RutineEntity(id: id, navn: id) }
    }
    func suggestedEntities() async throws -> [RutineEntity] { await Self.load() }
    func entities(matching string: String) async throws -> [RutineEntity] {
        let q = string.lowercased()
        return await Self.load().filter { $0.navn.lowercased().contains(q) || $0.id.lowercased().contains(q) }
    }
}

// MARK: - Intents

nonisolated struct SpillFavorittIntent: AppIntent {
    static var title: LocalizedStringResource { "Spill radiofavoritt" }
    static var description: IntentDescription { IntentDescription("Spiller en av radiofavorittene i et rom.") }
    static var openAppWhenRun: Bool { false }
    @Parameter(title: "Favoritt") var favoritt: FavorittEntity
    @Parameter(title: "Rom") var rom: RomEntity?
    init() {}
    func perform() async throws -> some IntentResult & ProvidesDialog {
        let host = SiriSkjold.host(rom)
        // nummeret kan være ulikt i hvert rom: slå opp på navnet i det valgte rommet
        let lokal = await FavorittQuery.load(host)
        let n = lokal.first { $0.id == favoritt.id }?.n ?? favoritt.n
        guard n > 0 else { return .result(dialog: "Fant ikke \(favoritt.id) blant favorittene.") }
        _ = await SiriSkjold.post(host, "/api/power", ["on": true])
        let ok = await SiriSkjold.post(host, "/api/preset", ["n": n])
        return .result(dialog: ok ? "Spiller \(favoritt.id) i \(SiriSkjold.roomName(host))." : SiriSkjold.offline)
    }
}

nonisolated struct SpillKanalIntent: AppIntent {
    static var title: LocalizedStringResource { "Spill radiokanal" }
    static var description: IntentDescription { IntentDescription("Søker etter en radiokanal (NRK eller nettradio) og spiller den.") }
    static var openAppWhenRun: Bool { false }
    @Parameter(title: "Kanal", requestValueDialog: "Hvilken kanal?") var kanal: String
    @Parameter(title: "Rom") var rom: RomEntity?
    init() {}
    func perform() async throws -> some IntentResult & ProvidesDialog {
        let host = SiriSkjold.host(rom)
        let q = kanal.trimmingCharacters(in: .whitespaces)
        guard !q.isEmpty else { return .result(dialog: "Hvilken kanal vil du høre?") }
        _ = await SiriSkjold.post(host, "/api/power", ["on": true])
        // Favoritt med samme navn først (har riktig logo og strøm), så NRK, så Radio Browser.
        if let f = await FavorittQuery.load(host).first(where: { $0.id.lowercased().contains(q.lowercased()) }),
           await SiriSkjold.post(host, "/api/preset", ["n": f.n]) {
            return .result(dialog: "Spiller \(f.id) i \(SiriSkjold.roomName(host)).")
        }
        if q.lowercased().hasPrefix("nrk"), await SiriSkjold.post(host, "/api/nrk/play", ["query": q]) {
            return .result(dialog: "Spiller \(q) i \(SiriSkjold.roomName(host)).")
        }
        let enc = q.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? q
        guard let j = await SiriSkjold.json(host, "/api/radio/search?q=" + enc) else { return .result(dialog: SiriSkjold.offline) }
        let treff = ((j["norway"] as? [[String: Any]]) ?? []) + ((j["world"] as? [[String: Any]]) ?? [])
        guard let st = treff.first, let url = st["url"] as? String, !url.isEmpty else {
            return .result(dialog: "Fant ingen kanal som heter \(q).")
        }
        let navn = (st["name"] as? String) ?? q
        let ok = await SiriSkjold.post(host, "/api/radio/play", ["url": url, "title": navn, "image": (st["image"] as? String) ?? "",
                                                                 "genre": (st["genre"] as? String) ?? ""])
        return .result(dialog: ok ? "Spiller \(navn) i \(SiriSkjold.roomName(host))." : SiriSkjold.offline)
    }
}

nonisolated struct SettVolumIntent: AppIntent {
    static var title: LocalizedStringResource { "Sett volum" }
    static var openAppWhenRun: Bool { false }
    @Parameter(title: "Volum (%)", inclusiveRange: (0, 100)) var prosent: Int
    @Parameter(title: "Rom") var rom: RomEntity?
    init() {}
    func perform() async throws -> some IntentResult & ProvidesDialog {
        let host = SiriSkjold.host(rom)
        let v = max(0, min(100, prosent))
        let ok = await SiriSkjold.post(host, "/api/volume", ["volume": v])
        return .result(dialog: ok ? "Volumet i \(SiriSkjold.roomName(host)) er \(v) prosent." : SiriSkjold.offline)
    }
}

nonisolated struct VolumOppIntent: AppIntent {
    static var title: LocalizedStringResource { "Skru opp volumet" }
    static var openAppWhenRun: Bool { false }
    @Parameter(title: "Rom") var rom: RomEntity?
    init() {}
    func perform() async throws -> some IntentResult & ProvidesDialog {
        let host = SiriSkjold.host(rom)
        let ok = await SiriSkjold.post(host, "/api/volume", ["delta": 8])
        return .result(dialog: ok ? "Skrudde opp i \(SiriSkjold.roomName(host))." : SiriSkjold.offline)
    }
}

nonisolated struct VolumNedIntent: AppIntent {
    static var title: LocalizedStringResource { "Skru ned volumet" }
    static var openAppWhenRun: Bool { false }
    @Parameter(title: "Rom") var rom: RomEntity?
    init() {}
    func perform() async throws -> some IntentResult & ProvidesDialog {
        let host = SiriSkjold.host(rom)
        let ok = await SiriSkjold.post(host, "/api/volume", ["delta": -8])
        return .result(dialog: ok ? "Skrudde ned i \(SiriSkjold.roomName(host))." : SiriSkjold.offline)
    }
}

nonisolated struct SpillIntent: AppIntent {
    static var title: LocalizedStringResource { "Fortsett avspilling" }
    static var openAppWhenRun: Bool { false }
    @Parameter(title: "Rom") var rom: RomEntity?
    init() {}
    func perform() async throws -> some IntentResult & ProvidesDialog {
        let host = SiriSkjold.host(rom)
        _ = await SiriSkjold.post(host, "/api/power", ["on": true])
        let ok = await SiriSkjold.post(host, "/api/transport", ["action": "play"])
        return .result(dialog: ok ? "Spiller i \(SiriSkjold.roomName(host))." : SiriSkjold.offline)
    }
}

nonisolated struct PauseIntent: AppIntent {
    static var title: LocalizedStringResource { "Pause" }
    static var openAppWhenRun: Bool { false }
    @Parameter(title: "Rom") var rom: RomEntity?
    init() {}
    func perform() async throws -> some IntentResult & ProvidesDialog {
        let host = SiriSkjold.host(rom)
        let ok = await SiriSkjold.post(host, "/api/transport", ["action": "pause"])
        return .result(dialog: ok ? "Pause i \(SiriSkjold.roomName(host))." : SiriSkjold.offline)
    }
}

nonisolated struct NesteIntent: AppIntent {
    static var title: LocalizedStringResource { "Neste låt" }
    static var openAppWhenRun: Bool { false }
    @Parameter(title: "Rom") var rom: RomEntity?
    init() {}
    func perform() async throws -> some IntentResult & ProvidesDialog {
        let host = SiriSkjold.host(rom)
        let ok = await SiriSkjold.post(host, "/api/transport", ["action": "next"])
        return .result(dialog: ok ? "Neste." : SiriSkjold.offline)
    }
}

nonisolated struct SlaAvIntent: AppIntent {
    static var title: LocalizedStringResource { "Slå av Skjold" }
    static var openAppWhenRun: Bool { false }
    @Parameter(title: "Rom") var rom: RomEntity?
    init() {}
    func perform() async throws -> some IntentResult & ProvidesDialog {
        let host = SiriSkjold.host(rom)
        let ok = await SiriSkjold.post(host, "/api/power", ["on": false])
        return .result(dialog: ok ? "Slo av \(SiriSkjold.roomName(host))." : SiriSkjold.offline)
    }
}

nonisolated struct KjorRutineIntent: AppIntent {
    static var title: LocalizedStringResource { "Kjør rutine" }
    static var description: IntentDescription { IntentDescription("Kjører en Skjold-rutine, f.eks. «Morgen» eller «Leggetid».") }
    static var openAppWhenRun: Bool { false }
    @Parameter(title: "Rutine") var rutine: RutineEntity
    init() {}
    func perform() async throws -> some IntentResult & ProvidesDialog {
        let id = rutine.id.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? rutine.id
        let ok = await SiriSkjold.post(SiriSkjold.activeHost, "/api/routines/" + id + "/run")
        return .result(dialog: ok ? "Kjører \(rutine.navn)." : SiriSkjold.offline)
    }
}

nonisolated struct SpillerNaIntent: AppIntent {
    static var title: LocalizedStringResource { "Hva spiller nå" }
    static var openAppWhenRun: Bool { false }
    @Parameter(title: "Rom") var rom: RomEntity?
    init() {}
    func perform() async throws -> some IntentResult & ProvidesDialog & ReturnsValue<String> {
        let host = SiriSkjold.host(rom)
        let romNavn = SiriSkjold.roomName(host)
        guard let s = await SiriSkjold.json(host, "/api/status") else {
            return .result(value: "", dialog: SiriSkjold.offline)
        }
        let pa = (s["power"] as? NSNumber)?.boolValue ?? true
        if !pa { return .result(value: "", dialog: "\(romNavn) er slått av.") }
        var tekst = ""
        if let r = s["radio_now"] as? [String: Any], let navn = r["name"] as? String, !navn.isEmpty {
            let naa = (r["now"] as? String) ?? ""
            tekst = naa.isEmpty ? "\(navn) spiller i \(romNavn)." : "\(navn) spiller i \(romNavn): \(naa)."
        } else {
            let t = (s["title"] as? String) ?? "", a = (s["artist"] as? String) ?? ""
            if t.isEmpty { tekst = "Ingenting spiller i \(romNavn) nå." }
            else { tekst = a.isEmpty ? "\(t) spiller i \(romNavn)." : "\(t) med \(a) spiller i \(romNavn)." }
        }
        return .result(value: tekst, dialog: "\(tekst)")
    }
}
