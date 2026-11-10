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

    /// Stream URL for a catalog station that only has a name (the amplifier needs a URL to save or play it).
    static func streamURL(for name: String) async -> String? {
        let q = searchName(name)
        let hits = await search(q)
        let n = name.lowercased(), ql = q.lowercased()
        return (hits.first { $0.name.lowercased() == n } ?? hits.first { $0.name.lowercased() == ql }
                ?? hits.first { $0.name.lowercased().hasPrefix(ql) } ?? hits.first)?.url
    }

    /// Same search names as `SK.logoQuery`, without touching the main-actor catalog.
    private static func searchName(_ name: String) -> String {
        ["P4 Norge": "P4", "P5 Hits": "P5", "NRJ": "NRJ Norge"][name] ?? name
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

// MARK: - Device discovery (Bonjour _kipultamp._tcp + _skjold._tcp)

/// A Skjold device seen on Bonjour. `host` ("ip:port") is filled in once the service has been resolved.
struct FoundDevice: Hashable, Identifiable {
    var id: String { type + "/" + name }
    var name: String
    var type: String
    /// "s1" | "node" | "core" from the TXT record (ki_amp_daemon.py: product=…), "" if unknown.
    var product: String
    var host: String? = nil
    var endpoint: NWEndpoint
}

/// Browses for the daemon's `_kipultamp._tcp` (TXT: id, version, name, type, product, path) and the older `_skjold._tcp`,
/// and resolves each service to an IPv4 `ip:port` with a short NWConnection.
@Observable
final class DeviceBrowser {
    static let types = ["_kipultamp._tcp", "_skjold._tcp"]

    private(set) var devices: [FoundDevice] = []
    @ObservationIgnored private var browsers: [NWBrowser] = []
    @ObservationIgnored private var seen: [String: [FoundDevice]] = [:]
    @ObservationIgnored private var hosts: [String: String] = [:]
    @ObservationIgnored private var resolving: Set<String> = []
    /// Called when a device has been resolved to a host.
    @ObservationIgnored var onResolved: ((FoundDevice) -> Void)? = nil

    func start() {
        guard browsers.isEmpty else { return }
        for type in Self.types {
            let b = NWBrowser(for: .bonjourWithTXTRecord(type: type, domain: nil), using: .tcp)
            b.browseResultsChangedHandler = { [weak self] results, _ in
                let found = results.compactMap { r -> FoundDevice? in
                    guard case let .service(name, _, _, _) = r.endpoint else { return nil }
                    var product = ""
                    if case let .bonjour(txt) = r.metadata { product = txt.dictionary["product"] ?? "" }
                    return FoundDevice(name: name, type: type, product: product, endpoint: r.endpoint)
                }
                Task { @MainActor in self?.update(type, found) }
            }
            b.start(queue: .main)
            browsers.append(b)
        }
    }

    func stop() {
        browsers.forEach { $0.cancel() }
        browsers = []
    }

    private func update(_ type: String, _ found: [FoundDevice]) {
        seen[type] = found
        publish()
        for d in found where hosts[d.id] == nil { resolve(d) }
    }

    private func publish() {
        var all: [FoundDevice] = []
        for t in Self.types {
            for var d in seen[t] ?? [] {
                d.host = hosts[d.id]
                // the same box can advertise both types: keep the _kipultamp one
                if !all.contains(where: { $0.name == d.name }) { all.append(d) }
            }
        }
        devices = all.sorted { $0.name < $1.name }
    }

    private func resolve(_ d: FoundDevice) {
        guard !resolving.contains(d.id) else { return }
        resolving.insert(d.id)
        let params = NWParameters.tcp
        if let ip = params.defaultProtocolStack.internetProtocol as? NWProtocolIP.Options { ip.version = .v4 }
        let c = NWConnection(to: d.endpoint, using: params)
        let key = d.id
        c.stateUpdateHandler = { [weak self] st in
            switch st {
            case .ready:
                var host: String? = nil
                if case let .hostPort(h, p)? = c.currentPath?.remoteEndpoint {
                    var hs = "\(h)"
                    if let pct = hs.firstIndex(of: "%") { hs = String(hs[..<pct]) }
                    if hs.contains(":") { hs = "[\(hs)]" }
                    host = "\(hs):\(p.rawValue)"
                }
                c.cancel()
                Task { @MainActor in self?.resolved(key, host) }
            case .failed, .waiting:
                c.cancel()
                Task { @MainActor in self?.resolved(key, nil) }
            default: break
            }
        }
        c.start(queue: .main)
    }

    private func resolved(_ key: String, _ host: String?) {
        guard resolving.contains(key) else { return }
        resolving.remove(key)
        guard let host else { return }
        hosts[key] = host
        publish()
        if let d = devices.first(where: { $0.id == key }) { onResolved?(d) }
    }
}

// MARK: - HTTP helper

nonisolated enum Net {
    /// Plain request. Returns body and status code, or nil when the host could not be reached.
    static func data(_ url: URL, method: String = "GET", body: Data? = nil, timeout: TimeInterval = 6,
                     headers: [String: String] = [:]) async -> (Data, Int)? {
        var req = URLRequest(url: url, timeoutInterval: timeout)
        req.httpMethod = method
        req.cachePolicy = .reloadIgnoringLocalCacheData
        if let body {
            req.httpBody = body
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        for (k, v) in headers { req.setValue(v, forHTTPHeaderField: k) }
        guard let (d, r) = try? await URLSession.shared.data(for: req), let http = r as? HTTPURLResponse else { return nil }
        // Relé via Skjold-hjem: Cloudflare Access sender til innloggingssiden når informasjonskapselen mangler/er utløpt
        if HjemAPI.accessBlocked(http) { return (d, 401) }
        return (d, http.statusCode)
    }

    /// "http://" + host + path for a bare "ip:port" / "name.local:port", or a full URL.
    static func url(_ base: String, _ path: String) -> URL? {
        var b = base.trimmingCharacters(in: .whitespaces)
        if !b.lowercased().hasPrefix("http") { b = "http://" + b }
        while b.hasSuffix("/") { b.removeLast() }
        return URL(string: b + path)
    }
}

// MARK: - Device status (GET /api/status, SSE /api/events)

/// The parts of ki_amp_daemon.py's status the app uses. Parsed off the main actor, so it only holds plain values.
nonisolated struct DevStatus: Sendable, Equatable {
    struct RadioNow: Sendable, Equatable { var name = "", genre = "", now = "", image = "", url = "", logo = ""; var n = 0; var playing = false }

    var name = "", id = "", product = "", board = "", version = "", input = "", source = ""
    var title = "", artist = "", album = "", coverURL = "", btDevice = "", airplayDevice = ""
    var lyrionServer = "", lyrionPlayer = ""
    /// Biblioteket en låt spilles fra («Navidrome», «YouTube Music» …), tom for radio. Fra /api/status `source_label`.
    var sourceLabel = ""
    var power = true, playing = false, paused = false, mute = false, headphones = false, lyrion = false, btPairing = false
    var volume = 0, duration = 0, position = 0, preset = 0, presetsCount = 0, btPairingLeft = 0
    var inputs: [String] = []
    var presetTitles: [String] = []
    var radioNow: RadioNow? = nil

    init?(_ data: Data) {
        guard let j = try? JSONSerialization.jsonObject(with: data) as? [String: Any], j["volume"] != nil else { return nil }
        func s(_ k: String, _ o: [String: Any] = j) -> String { (o[k] as? String) ?? (o[k] as? NSNumber)?.stringValue ?? "" }
        func i(_ k: String, _ o: [String: Any] = j) -> Int { (o[k] as? NSNumber)?.intValue ?? Int(s(k, o)) ?? 0 }
        func b(_ k: String, _ o: [String: Any] = j) -> Bool { (o[k] as? NSNumber)?.boolValue ?? false }
        name = s("name"); id = s("id"); board = s("board"); version = s("version"); input = s("input"); source = s("source")
        title = s("title"); artist = s("artist"); album = s("album"); btDevice = s("bt_device"); airplayDevice = s("airplay_device")
        lyrionServer = s("lyrion_server"); lyrionPlayer = s("lyrion_player"); sourceLabel = s("source_label")
        product = s("product")
        if product.isEmpty { product = board == "node" ? "node" : "s1" }
        coverURL = s("cover_url")
        if coverURL.isEmpty, !s("cover").isEmpty { coverURL = "/api/cover?v=" + s("cover") }
        power = j["power"] == nil ? true : b("power"); playing = b("playing"); paused = b("paused"); mute = b("mute")
        headphones = b("headphones"); lyrion = b("lyrion"); btPairing = b("bt_pairing")
        volume = i("volume"); duration = i("duration"); position = i("position"); preset = i("preset")
        presetsCount = i("presets_count"); btPairingLeft = i("bt_pairing_left")
        inputs = (j["inputs"] as? [String]) ?? []
        presetTitles = ((j["presets"] as? [[String: Any]]) ?? []).map { s("title", $0) }
        if let r = j["radio_now"] as? [String: Any] {
            radioNow = RadioNow(name: s("name", r), genre: s("genre", r), now: s("now", r), image: s("image", r),
                                url: s("url", r), logo: s("logo", r), n: i("n", r), playing: b("playing", r))
        }
    }
}

/// Settings from GET /api/settings (same keys as skjold_settings.js). Booleans become 0/1 like `AppModel.sset`.
nonisolated struct DevSettings: Sendable {
    struct EQ: Sendable { var preset: Int; var eq: [Int]; var loud: Bool }
    var ints: [String: Int] = [:]
    var strings: [String: String] = [:]
    var eq: [String: EQ] = [:]
    /// settings.homeLayout (nil = feltet finnes ikke, eldre daemon).
    var homeLayout: [HomeItem]? = nil

    init?(_ data: Data) {
        guard let j = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let set = j["settings"] as? [String: Any] else { return nil }
        homeLayout = HomeLayout.parse(set["homeLayout"])
        for (k, v) in set {
            if k == "homeLayout" { continue }
            if k == "eq", let e = v as? [String: Any] {
                for (src, p) in e {
                    guard let p = p as? [String: Any] else { continue }
                    let bands = ((p["eq"] as? [NSNumber]) ?? []).map(\.intValue)
                    eq[src] = EQ(preset: (p["preset"] as? NSNumber)?.intValue ?? 0,
                                 eq: bands.count == 5 ? bands : [0, 0, 0, 0, 0], loud: (p["loud"] as? NSNumber)?.boolValue ?? true)
                }
            } else if let str = v as? String {
                strings[k] = str
            } else if let n = v as? NSNumber {
                ints[k] = CFGetTypeID(n) == CFBooleanGetTypeID() ? (n.boolValue ? 1 : 0) : n.intValue
            }
        }
    }
}

/// One favourite from GET /api/presets.
nonisolated struct DevPreset: Sendable, Equatable {
    var n: Int, title: String, url: String, genre: String, image: String
    /// «/api/logo?k=…»: kanallogoen servert av Skjold selv (relativ – gjøres absolutt med DeviceLink.coverURL).
    var logo: String = ""

    static func list(_ data: Data) -> [DevPreset]? {
        guard let j = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let ps = j["presets"] as? [Any] else { return nil }
        return ps.compactMap { p -> DevPreset? in
            guard let p = p as? [String: Any], let url = p["url"] as? String, !url.isEmpty else { return nil }
            return DevPreset(n: (p["n"] as? NSNumber)?.intValue ?? 0, title: p["title"] as? String ?? "", url: url,
                             genre: p["genre"] as? String ?? "", image: (p["image"] as? String) ?? (p["icon"] as? String) ?? "",
                             logo: p["logo"] as? String ?? "")
        }
    }
}

/// Wi-Fi networks from GET /api/wifi.
nonisolated enum DevWifi {
    static func list(_ data: Data) -> [String] {
        guard let j = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let n = j["networks"] as? [[String: Any]] else { return [] }
        var out: [String] = []
        for x in n { if let s = x["ssid"] as? String, !s.isEmpty, !out.contains(s) { out.append(s) } }
        return out
    }
}

/// Server-Sent Events from GET /api/events: one «data: <status JSON>» line per change, «: ping» every 15 s.
nonisolated enum DeviceEvents {
    static func stream(_ url: URL) -> AsyncThrowingStream<Data, Error> {
        AsyncThrowingStream { cont in
            let task = Task {
                do {
                    var req = URLRequest(url: url, timeoutInterval: 40)
                    req.setValue("text/event-stream", forHTTPHeaderField: "Accept")
                    let (bytes, resp) = try await URLSession.shared.bytes(for: req)
                    guard (resp as? HTTPURLResponse)?.statusCode == 200 else { throw URLError(.badServerResponse) }
                    for try await line in bytes.lines where line.hasPrefix("data:") {
                        cont.yield(Data(line.dropFirst(5).trimmingCharacters(in: .whitespaces).utf8))
                    }
                    cont.finish()
                } catch {
                    cont.finish(throwing: error)
                }
            }
            cont.onTermination = { _ in task.cancel() }
        }
    }
}

// MARK: - Device API

/// REST API of ki_amp_daemon.py on port 8765 (see the docstring at the top of pi/ki_amp_daemon.py).
/// `host` is "ip:port" of the device being controlled. All calls answer with the new status where the daemon gives one.
@MainActor
final class DeviceLink {
    static let shared = DeviceLink()
    static let port = 8765
    var host: String? = nil

    /// Normalises "192.168.1.5", "skjold.local" or "http://x:8765/" to "host:port".
    static func normHost(_ s: String) -> String {
        var h = s.trimmingCharacters(in: .whitespacesAndNewlines)
        if let r = h.range(of: "://") { h = String(h[r.upperBound...]) }
        if let slash = h.firstIndex(of: "/") { h = String(h[..<slash]) }
        if !h.contains(":") { h += ":\(port)" }
        return h
    }

    /// Status of any device ("ip:port"), short timeout. nil = unreachable or not a Skjold daemon.
    nonisolated static func status(at host: String, timeout: TimeInterval = 3) async -> DevStatus? {
        guard let url = Net.url(host, "/api/status"), let (d, code) = await Net.data(url, timeout: timeout), code == 200 else { return nil }
        return DevStatus(d)
    }

    func get(_ path: String, on h: String? = nil, timeout: TimeInterval = 6) async -> Data? {
        guard let base = h ?? host, let url = Net.url(base, path),
              let (d, code) = await Net.data(url, timeout: timeout), code < 300 else { return nil }
        return d
    }

    /// POST (or PUT/DELETE) with a JSON body. Returns the body on 2xx, nil otherwise.
    @discardableResult
    func send(_ path: String, _ body: [String: Any] = [:], method: String = "POST", on h: String? = nil, timeout: TimeInterval = 6) async -> Data? {
        await sendRaw(path, Self.json(body, method: method), method: method, on: h, timeout: timeout)
    }

    static func json(_ body: [String: Any], method: String = "POST") -> Data? {
        method == "DELETE" ? nil : (try? JSONSerialization.data(withJSONObject: body))
    }

    @discardableResult
    func sendRaw(_ path: String, _ data: Data?, method: String = "POST", on h: String? = nil, timeout: TimeInterval = 6) async -> Data? {
        guard let base = h ?? host, let url = Net.url(base, path) else { return nil }
        guard let (d, code) = await Net.data(url, method: method, body: data, timeout: timeout), code < 300 else { return nil }
        return d
    }

    /// Absolute URL for a cover_url from the status ("/api/cover?v=…" or a full https URL).
    func coverURL(_ s: String, on h: String? = nil) -> String {
        if s.isEmpty || s.lowercased().hasPrefix("http") { return s }
        guard let base = h ?? host else { return "" }
        return Net.url(base, s)?.absoluteString ?? ""
    }
}
