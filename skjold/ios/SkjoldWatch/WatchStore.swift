import Foundation
import SwiftUI
import WatchConnectivity

struct WatchRoom: Identifiable, Hashable { var host: String; var name: String; var product: String; var id: String { host } }
struct WatchFav: Identifiable, Hashable { var n: Int; var title: String; var logo: String; var id: Int { n } }

/// Status fra Skjold (GET /api/status) – bare det klokka viser.
struct WatchStatus: Equatable {
    var name = "", title = "", artist = "", art = "", input = ""
    var power = true, playing = false, mute = false
    var volume = 0, preset = 0
    var favs: [WatchFav] = []

    init() {}
    init?(_ data: Data) {
        guard let j = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any], j["volume"] != nil else { return nil }
        func s(_ k: String, _ o: [String: Any]) -> String { (o[k] as? String) ?? (o[k] as? NSNumber)?.stringValue ?? "" }
        func i(_ k: String, _ o: [String: Any]) -> Int { (o[k] as? NSNumber)?.intValue ?? Int(s(k, o)) ?? 0 }
        func b(_ k: String, _ o: [String: Any]) -> Bool { (o[k] as? NSNumber)?.boolValue ?? false }
        name = s("name", j); input = s("input", j)
        title = s("title", j); artist = s("artist", j)
        power = j["power"] == nil ? true : b("power", j); playing = b("playing", j); mute = b("mute", j)
        volume = i("volume", j); preset = i("preset", j)
        art = s("cover_url", j)
        if art.isEmpty, !s("cover", j).isEmpty { art = "/api/cover?v=" + s("cover", j) }
        if let r = j["radio_now"] as? [String: Any] {
            if title.isEmpty { title = s("name", r) }
            if artist.isEmpty { artist = s("now", r) }
            if art.isEmpty { art = s("logo", r) }
        }
        favs = ((j["presets"] as? [[String: Any]]) ?? []).compactMap { p in
            let t = s("title", p); return t.isEmpty ? nil : WatchFav(n: i("n", p), title: t, logo: s("logo", p))
        }
    }
}

/// Snakker direkte med Skjold over nettet når klokka når den, ellers via telefonen (WatchConnectivity).
@MainActor final class WatchStore: NSObject, ObservableObject, WCSessionDelegate {
    @Published var rooms: [WatchRoom] = []
    @Published var host: String = UserDefaults.standard.string(forKey: "skjold-watch-host") ?? "" {
        didSet { UserDefaults.standard.set(host, forKey: "skjold-watch-host") }
    }
    @Published var status = WatchStatus()
    @Published var reachable = true
    @Published var viaPhone = false
    private var poll: Task<Void, Never>?

    override init() {
        super.init()
        if let d = UserDefaults.standard.data(forKey: "skjold-watch-rooms"),
           let arr = (try? JSONSerialization.jsonObject(with: d)) as? [[String: String]] {
            rooms = arr.compactMap { r in r["host"].map { WatchRoom(host: $0, name: r["name"] ?? $0, product: r["product"] ?? "") } }
        }
    }

    func start() {
        if WCSession.isSupported() {
            WCSession.default.delegate = self
            WCSession.default.activate()
        }
        poll?.cancel()
        poll = Task { [weak self] in
            while !Task.isCancelled {
                await self?.refresh()
                try? await Task.sleep(nanoseconds: 3_000_000_000)
            }
        }
    }

    var roomName: String { rooms.first { $0.host == host }?.name ?? (status.name.isEmpty ? "Skjold" : status.name) }

    /// Absolutt adresse for et bilde fra statusen («/api/cover…», «/api/logo…» eller full https-adresse).
    func imageURL(_ s: String) -> URL? {
        if s.isEmpty { return nil }
        if s.lowercased().hasPrefix("http") { return URL(string: s) }
        return Self.url(host, s)
    }

    static func url(_ base: String, _ path: String) -> URL? {
        var b = base.trimmingCharacters(in: .whitespaces)
        if b.isEmpty { return nil }
        if !b.lowercased().hasPrefix("http") { b = "http://" + b }
        while b.hasSuffix("/") { b.removeLast() }
        return URL(string: b + path)
    }

    // MARK: API

    func refresh() async {
        guard !host.isEmpty else { return }
        if let d = await call("/api/status", method: "GET", body: nil), let st = WatchStatus(d) {
            status = st; reachable = true
        } else {
            reachable = false
        }
    }

    func setVolume(_ v: Int) {
        let v = max(0, min(100, v))
        status.volume = v
        Task { _ = await call("/api/volume", body: ["volume": v]) }
    }
    func transport(_ a: String) {
        if a == "playpause" { status.playing.toggle() }
        Task { _ = await call("/api/transport", body: ["action": a]); await refresh() }
    }
    func power(_ on: Bool) {
        status.power = on
        Task { _ = await call("/api/power", body: ["on": on]); await refresh() }
    }
    func playFav(_ n: Int) {
        status.preset = n
        Task { _ = await call("/api/preset", body: ["n": n]); await refresh() }
    }
    func select(_ r: WatchRoom) {
        host = r.host
        status = WatchStatus()
        Task { await refresh() }
    }

    /// Direkte HTTP mot Skjold; feiler det, går kallet via telefonen.
    func call(_ path: String, method: String = "POST", body: [String: Any]?) async -> Data? {
        guard let url = Self.url(host, path) else { return nil }
        let data = body.flatMap { try? JSONSerialization.data(withJSONObject: $0) }
        var req = URLRequest(url: url, timeoutInterval: 4)
        req.httpMethod = method
        req.cachePolicy = .reloadIgnoringLocalCacheData
        if let data { req.httpBody = data; req.setValue("application/json", forHTTPHeaderField: "Content-Type") }
        if let (d, r) = try? await URLSession.shared.data(for: req), let http = r as? HTTPURLResponse, http.statusCode < 300 {
            viaPhone = false
            return d
        }
        let viaP = await viaPhoneCall(path: path, method: method, body: data)
        if viaP != nil { viaPhone = true }
        return viaP
    }

    private func viaPhoneCall(path: String, method: String, body: Data?) async -> Data? {
        guard WCSession.isSupported(), WCSession.default.activationState == .activated, WCSession.default.isReachable else { return nil }
        var msg: [String: Any] = ["host": host, "path": path, "method": method]
        if let body { msg["body"] = body.base64EncodedString() }
        guard let payload = try? JSONSerialization.data(withJSONObject: msg) else { return nil }
        return await withCheckedContinuation { (c: CheckedContinuation<Data?, Never>) in
            WCSession.default.sendMessageData(payload, replyHandler: { d in c.resume(returning: d.isEmpty ? nil : d) },
                                              errorHandler: { _ in c.resume(returning: nil) })
        }
    }

    // MARK: WCSessionDelegate – rom og aktiv enhet fra telefonen

    nonisolated func session(_ session: WCSession, activationDidCompleteWith activationState: WCSessionActivationState, error: Error?) {
        let ctx = session.receivedApplicationContext
        Task { @MainActor in self.apply(ctx) }
    }

    nonisolated func session(_ session: WCSession, didReceiveApplicationContext applicationContext: [String: Any]) {
        Task { @MainActor in self.apply(applicationContext) }
    }

    private func apply(_ ctx: [String: Any]) {
        guard let arr = ctx["rooms"] as? [[String: String]] else { return }
        rooms = arr.compactMap { r in r["host"].map { WatchRoom(host: $0, name: r["name"] ?? $0, product: r["product"] ?? "") } }
        if let d = try? JSONSerialization.data(withJSONObject: arr) { UserDefaults.standard.set(d, forKey: "skjold-watch-rooms") }
        let active = (ctx["active"] as? String) ?? ""
        if host.isEmpty || !rooms.contains(where: { $0.host == host }) {
            host = active.isEmpty ? (rooms.first?.host ?? "") : active
            Task { await refresh() }
        }
    }
}
