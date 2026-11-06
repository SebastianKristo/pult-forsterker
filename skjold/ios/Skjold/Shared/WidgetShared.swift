import Foundation
import AppIntents
import ActivityKit
import WidgetKit

// Felles for appen og widget-utvidelsen (SkjoldWidgets): siste status i App Group, kall mot Skjold, Live Activity-
// attributter og AppIntents for knappene i widgets, Kontrollsenter og Live Activity. Alt er `nonisolated`, så fila
// kompilerer likt i appen (MainActor som standard) og i utvidelsen.

nonisolated enum SkjoldShared {
    static let group = "group.no.kristo.skjold"
    private static let stateKey = "skjold-widget-state"

    static var defaults: UserDefaults { UserDefaults(suiteName: group) ?? .standard }

    /// Omslag/kanallogo som liten JPEG i den delte containeren (skrives av appen, leses av widgetene).
    static var coverFile: URL? {
        FileManager.default.containerURL(forSecurityApplicationGroupIdentifier: group)?.appendingPathComponent("cover.jpg")
    }

    static func load() -> SharedNowPlaying {
        guard let d = defaults.data(forKey: stateKey), let s = try? JSONDecoder().decode(SharedNowPlaying.self, from: d) else {
            return SharedNowPlaying()
        }
        return s
    }

    static func save(_ s: SharedNowPlaying) {
        if let d = try? JSONEncoder().encode(s) { defaults.set(d, forKey: stateKey) }
    }

    static func mutate(_ change: (inout SharedNowPlaying) -> Void) {
        var s = load()
        change(&s)
        save(s)
    }

    /// "ip:port", "navn.local:port" eller en full URL (relé) → URL.
    static func url(_ base: String, _ path: String) -> URL? {
        var b = base.trimmingCharacters(in: .whitespaces)
        if !b.lowercased().hasPrefix("http") { b = "http://" + b }
        while b.hasSuffix("/") { b.removeLast() }
        return URL(string: b + path)
    }

    /// POST mot sist kjente Skjold. Returnerer true ved 2xx.
    static func post(_ path: String, _ body: [String: Any]) async -> Bool {
        let host = load().host
        guard !host.isEmpty, let u = url(host, path) else { return false }
        var req = URLRequest(url: u, timeoutInterval: 6)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try? JSONSerialization.data(withJSONObject: body)
        guard let (_, r) = try? await URLSession.shared.data(for: req), let http = r as? HTTPURLResponse else { return false }
        return (200..<300).contains(http.statusCode)
    }

    /// Henter /api/status direkte (widgeten oppdaterer seg selv når appen ikke kjører). Lagrer og returnerer ny status.
    static func fetch() async -> SharedNowPlaying {
        var s = load()
        guard !s.host.isEmpty, let u = url(s.host, "/api/status") else { return s }
        let req = URLRequest(url: u, timeoutInterval: 5)
        guard let (d, r) = try? await URLSession.shared.data(for: req), let http = r as? HTTPURLResponse,
              http.statusCode == 200, let j = try? JSONSerialization.jsonObject(with: d) as? [String: Any] else { return s }
        s.apply(j)
        save(s)
        return s
    }

    static func reloadWidgets() {
        WidgetCenter.shared.reloadAllTimelines()
    }
}

nonisolated struct SharedNowPlaying: Codable, Sendable, Hashable {
    var host = ""
    var room = "Skjold"
    var title = "Ingenting spilles"
    var subtitle = ""
    var source = ""
    var playing = false
    var volume = 0
    var presets: [String] = []
    var activePreset = 0
    var hasCover = false
    var updated = Date.distantPast

    static let placeholder = SharedNowPlaying(host: "", room: "Stue", title: "Midnight City", subtitle: "M83 · NRK P3",
                                              source: "Radio", playing: true, volume: 34,
                                              presets: ["NRK P1", "NRK P3", "NRK Jazz", "NRK Klassisk", "P4", "Radio Norge"],
                                              activePreset: 2, hasCover: false, updated: Date())

    static func sourceLabel(_ input: String) -> String {
        switch input {
        case "airplay": return "AirPlay"
        case "bt": return "Blåtann"
        case "radio": return "Radio"
        case "aux", "aux2": return "AUX"
        case "usb": return "USB"
        case "spotify": return "Spotify"
        case "plex": return "Plex"
        case "upnp": return "UPnP/DLNA"
        default: return input.isEmpty ? "Skjold" : input.capitalized
        }
    }

    /// Fyller inn fra JSON-en til /api/status (samme regler som appen bruker).
    mutating func apply(_ j: [String: Any]) {
        func str(_ k: String, _ o: [String: Any]) -> String { (o[k] as? String) ?? "" }
        let input = str("input", j)
        let t = str("title", j), a = str("artist", j)
        let rn = (j["radio_now"] as? [String: Any]) ?? [:]
        let station = str("name", rn)
        if !str("name", j).isEmpty { room = str("name", j) }
        source = Self.sourceLabel(input)
        if input == "radio" && !station.isEmpty {
            if t.isEmpty {
                title = station
                let now = str("now", rn)
                subtitle = now.isEmpty ? "Radio" : now
            } else {
                title = t
                subtitle = [a, station].filter { !$0.isEmpty }.joined(separator: " · ")
            }
        } else {
            title = t.isEmpty ? source : t
            subtitle = a
        }
        playing = (j["playing"] as? Bool) ?? ((j["playing"] as? NSNumber)?.boolValue ?? false)
        volume = (j["volume"] as? Int) ?? ((j["volume"] as? NSNumber)?.intValue ?? volume)
        activePreset = (j["preset"] as? Int) ?? 0
        if let ps = j["presets"] as? [[String: Any]] {
            let names = ps.map { str("title", $0) }.filter { !$0.isEmpty }
            if !names.isEmpty { presets = names }
        }
        updated = Date()
    }
}

// MARK: - Live Activity

nonisolated struct SkjoldNowPlayingAttributes: ActivityAttributes {
    nonisolated struct ContentState: Codable, Hashable, Sendable {
        var title: String
        var subtitle: String
        var source: String
        var playing: Bool
        var volume: Int
    }
    var room: String
}

// MARK: - AppIntents (knapper i widgets, Kontrollsenter og Live Activity)

nonisolated struct SkjoldPlayPauseIntent: LiveActivityIntent {
    static var title: LocalizedStringResource { "Spill eller pause" }
    init() {}
    func perform() async throws -> some IntentResult {
        let wasPlaying = SkjoldShared.load().playing
        let ok = await SkjoldShared.post("/api/transport", ["action": wasPlaying ? "pause" : "play"])
        if ok { SkjoldShared.mutate { $0.playing = !wasPlaying } }
        SkjoldShared.reloadWidgets()
        return .result()
    }
}

nonisolated struct SkjoldNextIntent: LiveActivityIntent {
    static var title: LocalizedStringResource { "Neste" }
    init() {}
    func perform() async throws -> some IntentResult {
        _ = await SkjoldShared.post("/api/transport", ["action": "next"])
        _ = await SkjoldShared.fetch()
        SkjoldShared.reloadWidgets()
        return .result()
    }
}

nonisolated struct SkjoldVolumeIntent: LiveActivityIntent {
    static var title: LocalizedStringResource { "Endre volum" }
    @Parameter(title: "Endring") var delta: Int
    init() {}
    init(delta: Int) { self.delta = delta }
    func perform() async throws -> some IntentResult {
        let v = max(0, min(100, SkjoldShared.load().volume + delta))
        let ok = await SkjoldShared.post("/api/volume", ["volume": v])
        if ok { SkjoldShared.mutate { $0.volume = v } }
        SkjoldShared.reloadWidgets()
        return .result()
    }
}

nonisolated struct SkjoldPresetIntent: AppIntent {
    static var title: LocalizedStringResource { "Spill radiofavoritt" }
    @Parameter(title: "Nummer") var n: Int
    init() {}
    init(n: Int) { self.n = n }
    func perform() async throws -> some IntentResult {
        let num = n
        let ok = await SkjoldShared.post("/api/preset", ["n": num])
        if ok { SkjoldShared.mutate { $0.activePreset = num; $0.playing = true } }
        _ = await SkjoldShared.fetch()
        SkjoldShared.reloadWidgets()
        return .result()
    }
}
