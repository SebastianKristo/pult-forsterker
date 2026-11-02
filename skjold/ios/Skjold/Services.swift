import Foundation
import Network
import AVFoundation

// MARK: - Radio Browser (https://de1.api.radio-browser.info)

struct RadioResult: Hashable, Sendable {
    var name: String
    var genre: String
    var url: String
    var country: String
    var br: Int
    var codec: String
}

nonisolated enum RadioBrowser {
    static let base = "https://de1.api.radio-browser.info/json/stations/search"

    private struct Raw: Decodable {
        var name: String?
        var tags: String?
        var url: String?
        var url_resolved: String?
        var countrycode: String?
        var bitrate: Int?
        var codec: String?
        var favicon: String?
    }

    static func search(_ q: String) async -> [RadioResult] {
        var c = URLComponents(string: base)!
        c.queryItems = [.init(name: "limit", value: "20"), .init(name: "hidebroken", value: "true"),
                        .init(name: "order", value: "clickcount"), .init(name: "reverse", value: "true"),
                        .init(name: "name", value: q)]
        guard let url = c.url, let (data, _) = try? await URLSession.shared.data(from: url),
              let list = try? JSONDecoder().decode([Raw].self, from: data) else { return [] }
        return list.compactMap { s in
            let name = (s.name ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
            let u = s.url_resolved ?? s.url ?? ""
            guard !name.isEmpty, !u.isEmpty else { return nil }
            let genre = (s.tags ?? "").split(separator: ",").prefix(2).joined(separator: ", ")
            return RadioResult(name: name, genre: genre, url: u, country: s.countrycode ?? "", br: s.bitrate ?? 0, codec: s.codec ?? "")
        }
    }

    /// Best logo for a station, scored like fetchLogos() in the design. nil = request failed, "" = none found.
    static func logo(query q: String, country cc: String) async -> String? {
        var c = URLComponents(string: base)!
        c.queryItems = [.init(name: "name", value: q), .init(name: "countrycode", value: cc), .init(name: "hidebroken", value: "true"),
                        .init(name: "order", value: "clickcount"), .init(name: "reverse", value: "true"), .init(name: "limit", value: "25")]
        guard let url = c.url, let (data, _) = try? await URLSession.shared.data(from: url),
              let list = try? JSONDecoder().decode([Raw].self, from: data) else { return nil }
        let ql = q.lowercased()
        func score(_ s: Raw) -> Int {
            let n = (s.name ?? "").trimmingCharacters(in: .whitespaces).lowercased(), f = s.favicon ?? ""
            return (n == ql ? 4 : n.hasPrefix(ql) ? 2 : 0) + (f.range(of: #"\.ico(\?|$)"#, options: .regularExpression) != nil ? -3 : 2) + (f.lowercased().contains("logo") ? 1 : 0)
        }
        let hits = list.filter { ($0.favicon ?? "").hasPrefix("https:") }.sorted { score($0) > score($1) }
        guard let f = hits.first?.favicon,
              f.range(of: #"\.ico(\?|$)|16x16|32x32|\.svg"#, options: [.regularExpression, .caseInsensitive]) == nil else { return "" }
        return f
    }

    /// Checks that a stream can be played (testStream() in the design).
    @MainActor
    static func testStream(_ urlString: String) async -> Bool {
        guard let url = URL(string: urlString), urlString.lowercased().hasPrefix("http") else { return false }
        let item = AVPlayerItem(url: url)
        let player = AVPlayer(playerItem: item)
        player.isMuted = true
        defer { player.replaceCurrentItem(with: nil) }
        for _ in 0..<80 {   // 8 s timeout
            switch item.status {
            case .readyToPlay: return true
            case .failed: return false
            default: try? await Task.sleep(for: .milliseconds(100))
            }
        }
        return false
    }
}

// MARK: - Plex Media Server

nonisolated enum PlexAPI {
    enum Result: Sendable { case ok(Int), unauthorized, unreachable, badURL }

    /// Checks the server address and token by listing the library sections. `.ok` carries the number of music libraries.
    static func test(server: String, token: String) async -> Result {
        var base = server.trimmingCharacters(in: .whitespaces)
        if !base.lowercased().hasPrefix("http") { base = "http://" + base }
        while base.hasSuffix("/") { base.removeLast() }
        guard var c = URLComponents(string: base + "/library/sections") else { return .badURL }
        c.queryItems = [.init(name: "X-Plex-Token", value: token.trimmingCharacters(in: .whitespaces))]
        guard let url = c.url else { return .badURL }
        var req = URLRequest(url: url, timeoutInterval: 6)
        req.setValue("application/json", forHTTPHeaderField: "Accept")
        req.setValue("Skjold", forHTTPHeaderField: "X-Plex-Product")
        req.setValue("skjold-ios", forHTTPHeaderField: "X-Plex-Client-Identifier")
        guard let (data, resp) = try? await URLSession.shared.data(for: req), let http = resp as? HTTPURLResponse else { return .unreachable }
        if http.statusCode == 401 { return .unauthorized }
        guard http.statusCode == 200 else { return .unreachable }
        struct Root: Decodable { struct MC: Decodable { struct Dir: Decodable { var type: String? }; var Directory: [Dir]? }; var MediaContainer: MC }
        let music = (try? JSONDecoder().decode(Root.self, from: data))?.MediaContainer.Directory?.filter { $0.type == "artist" }.count ?? 0
        return .ok(music)
    }
}

// MARK: - Device discovery (Bonjour _skjold._tcp)

struct FoundDevice: Hashable, Identifiable {
    var id: String { name }
    var name: String
    var endpoint: NWEndpoint
}

@Observable
final class DeviceBrowser {
    private(set) var devices: [FoundDevice] = []
    private var browser: NWBrowser?

    func start() {
        guard browser == nil else { return }
        let b = NWBrowser(for: .bonjour(type: "_skjold._tcp", domain: nil), using: .tcp)
        b.browseResultsChangedHandler = { [weak self] results, _ in
            let found = results.compactMap { r -> FoundDevice? in
                if case let .service(name, _, _, _) = r.endpoint { return FoundDevice(name: name, endpoint: r.endpoint) }
                return nil
            }
            Task { @MainActor in self?.devices = found.sorted { $0.name < $1.name } }
        }
        b.start(queue: .main)
        browser = b
    }

    func stop() {
        browser?.cancel()
        browser = nil
    }
}

// MARK: - Device API

/// Local REST API on the amplifier: http://<name>.local/api/...
/// The web UI and the app share it. Messages are the same ones the design posts on its BroadcastChannel.
@MainActor
final class DeviceLink {
    static let shared = DeviceLink()
    var host: String? = nil

    func post(_ message: [String: Any]) {
        guard let host, let type = message["type"] as? String,
              let url = URL(string: "http://\(host)/api/\(type)"),
              let body = try? JSONSerialization.data(withJSONObject: message) else { return }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = body
        req.timeoutInterval = 4
        URLSession.shared.dataTask(with: req).resume()
    }
}
