import Foundation
import CryptoKit

// Clients for the services around the amplifier: Lyrion (rooms and sync), Navidrome (Subsonic API), Plex and GitHub Releases.
// Everything here runs off the main actor and hands back plain Sendable values; AppModel turns them into Room/Track.

// MARK: - Library values

/// One track from Navidrome or Plex. `stream` is a direct URL the amplifier can play (POST /api/radio/play).
nonisolated struct LibItem: Sendable, Hashable {
    var id: String, title: String, artist: String, album: String, cover: String, stream: String
    var dur: Int
}

/// An album or playlist. Tracks are loaded when it is opened.
nonisolated struct LibColl: Sendable, Hashable {
    var id: String, name: String, artist: String, cover: String
    var count: Int
    var playlist: Bool
}

private nonisolated func jsonObject(_ d: Data) -> [String: Any]? { try? JSONSerialization.jsonObject(with: d) as? [String: Any] }
private nonisolated func str(_ o: [String: Any], _ k: String) -> String { (o[k] as? String) ?? (o[k] as? NSNumber)?.stringValue ?? "" }
private nonisolated func num(_ o: [String: Any], _ k: String) -> Int { (o[k] as? NSNumber)?.intValue ?? Int(str(o, k)) ?? 0 }
private nonisolated func list(_ x: Any?) -> [[String: Any]] {
    if let a = x as? [[String: Any]] { return a }
    if let o = x as? [String: Any] { return [o] }
    return []
}

// MARK: - Lyrion Music Server (JSON-RPC, POST http://server:9000/jsonrpc.js)

nonisolated enum Lyrion {
    struct Player: Sendable, Hashable { var id: String, name: String, model: String, ip: String; var connected: Bool }
    struct PStatus: Sendable, Equatable {
        var mode = "", title = "", artist = "", album = "", cover = ""
        var volume = 0, duration = 0, time = 0
        var syncMaster = ""
        var syncSlaves: [String] = []
        var playing: Bool { mode == "play" }
    }

    /// `server` is "host:port" (status field "lyrion_server" from the daemon).
    static func rpc(_ server: String, _ player: String, _ cmd: [String], timeout: TimeInterval = 4) async -> [String: Any]? {
        guard let url = Net.url(server, "/jsonrpc.js"),
              let body = try? JSONSerialization.data(withJSONObject: ["id": 1, "method": "slim.request", "params": [player, cmd] as [Any]] as [String: Any]),
              let (d, code) = await Net.data(url, method: "POST", body: body, timeout: timeout), code == 200,
              let j = jsonObject(d) else { return nil }
        return (j["result"] as? [String: Any]) ?? [:]
    }

    static func players(_ server: String) async -> [Player]? {
        guard let r = await rpc(server, "", ["players", "0", "100"]) else { return nil }
        return list(r["players_loop"]).map {
            Player(id: str($0, "playerid"), name: str($0, "name"), model: str($0, "modelname").isEmpty ? str($0, "model") : str($0, "modelname"),
                   ip: str($0, "ip"), connected: num($0, "connected") == 1)
        }
    }

    static func status(_ server: String, _ pid: String) async -> PStatus? {
        guard let r = await rpc(server, pid, ["status", "-", "1", "tags:aAlKcdj"]) else { return nil }
        var s = PStatus()
        s.mode = str(r, "mode")
        s.volume = abs(num(r, "mixer volume"))
        s.time = Int((r["time"] as? NSNumber)?.doubleValue ?? 0)
        s.duration = Int((r["duration"] as? NSNumber)?.doubleValue ?? 0)
        s.syncMaster = str(r, "sync_master")
        s.syncSlaves = str(r, "sync_slaves").split(separator: ",").map(String.init)
        if let t = list(r["playlist_loop"]).first {
            s.title = str(t, "title"); s.artist = str(t, "artist"); s.album = str(t, "album")
            let art = str(t, "artwork_url"), cid = str(t, "coverid")
            if art.lowercased().hasPrefix("http") { s.cover = art }
            else if !art.isEmpty { s.cover = Net.url(server, art.hasPrefix("/") ? art : "/" + art)?.absoluteString ?? "" }
            else if !cid.isEmpty { s.cover = Net.url(server, "/music/\(cid)/cover.jpg")?.absoluteString ?? "" }
        }
        if s.title.isEmpty { s.title = str(r, "current_title") }
        return s
    }

    static func command(_ server: String, _ pid: String, _ cmd: [String]) async {
        _ = await rpc(server, pid, cmd)
    }
}

// MARK: - Navidrome (Subsonic API 1.16.1, token auth: t = md5(password + salt))

nonisolated enum Subsonic {
    struct Conf: Sendable, Equatable {
        var url: String, user: String, pass: String
        var ok: Bool { !url.trimmingCharacters(in: .whitespaces).isEmpty && !user.trimmingCharacters(in: .whitespaces).isEmpty && !pass.isEmpty }
    }

    static func md5(_ s: String) -> String {
        Insecure.MD5.hash(data: Data(s.utf8)).map { String(format: "%02x", $0) }.joined()
    }

    static func url(_ c: Conf, _ view: String, _ params: [String: String] = [:]) -> URL? {
        let salt = String(UUID().uuidString.replacingOccurrences(of: "-", with: "").prefix(10)).lowercased()
        guard let base = Net.url(c.url, "/rest/" + view), var comp = URLComponents(url: base, resolvingAgainstBaseURL: false) else { return nil }
        comp.queryItems = [.init(name: "u", value: c.user.trimmingCharacters(in: .whitespaces)), .init(name: "t", value: md5(c.pass + salt)),
                           .init(name: "s", value: salt), .init(name: "v", value: "1.16.1"), .init(name: "c", value: "skjold-ios"),
                           .init(name: "f", value: "json")] + params.sorted { $0.key < $1.key }.map { .init(name: $0.key, value: $0.value) }
        return comp.url
    }

    /// nil on success, otherwise an error text for the settings row.
    static func ping(_ c: Conf) async -> String? {
        guard c.ok else { return "Fyll inn server, brukernavn og passord" }
        switch await call(c, "ping") {
        case .success: return nil
        case let .failure(e): return e.text
        }
    }

    struct Failure: Error, Sendable { var text: String }

    private static func call(_ c: Conf, _ view: String, _ params: [String: String] = [:]) async -> Result<[String: Any], Failure> {
        guard let u = url(c, view, params) else { return .failure(Failure(text: "Ugyldig adresse")) }
        guard let (d, code) = await Net.data(u, timeout: 10) else { return .failure(Failure(text: "Fant ikke serveren")) }
        guard code == 200, let j = jsonObject(d), let sr = j["subsonic-response"] as? [String: Any] else {
            return .failure(Failure(text: "Navidrome svarte \(code)"))
        }
        guard str(sr, "status") == "ok" else {
            let msg = ((sr["error"] as? [String: Any]).map { str($0, "message") }) ?? ""
            return .failure(Failure(text: msg.isEmpty ? "Innlogging feilet" : "Feil brukernavn eller passord"))
        }
        return .success(sr)
    }

    private static func song(_ c: Conf, _ s: [String: Any]) -> LibItem {
        let id = str(s, "id"), cover = str(s, "coverArt")
        return LibItem(id: id, title: str(s, "title"), artist: str(s, "artist"), album: str(s, "album"),
                       cover: cover.isEmpty ? "" : url(c, "getCoverArt", ["id": cover, "size": "300"])?.absoluteString ?? "",
                       stream: url(c, "stream", ["id": id])?.absoluteString ?? "", dur: num(s, "duration"))
    }

    private static func coll(_ c: Conf, _ a: [String: Any], playlist: Bool) -> LibColl {
        let cover = str(a, "coverArt")
        return LibColl(id: str(a, "id"), name: str(a, "name").isEmpty ? str(a, "title") : str(a, "name"),
                       artist: playlist ? str(a, "owner") : str(a, "artist"),
                       cover: cover.isEmpty ? "" : url(c, "getCoverArt", ["id": cover, "size": "300"])?.absoluteString ?? "",
                       count: num(a, "songCount"), playlist: playlist)
    }

    /// type: newest | frequent | random | recent
    static func albums(_ c: Conf, _ type: String, size: Int = 16) async -> Result<[LibColl], Failure> {
        await call(c, "getAlbumList2", ["type": type, "size": "\(size)"]).map { sr in
            list((sr["albumList2"] as? [String: Any])?["album"]).map { coll(c, $0, playlist: false) }
        }
    }

    static func playlists(_ c: Conf) async -> Result<[LibColl], Failure> {
        await call(c, "getPlaylists").map { sr in
            list((sr["playlists"] as? [String: Any])?["playlist"]).map { coll(c, $0, playlist: true) }
        }
    }

    static func tracks(_ c: Conf, _ col: LibColl) async -> [LibItem] {
        if col.playlist {
            guard case let .success(sr) = await call(c, "getPlaylist", ["id": col.id]) else { return [] }
            return list((sr["playlist"] as? [String: Any])?["entry"]).map { song(c, $0) }
        }
        guard case let .success(sr) = await call(c, "getAlbum", ["id": col.id]) else { return [] }
        return list((sr["album"] as? [String: Any])?["song"]).map { song(c, $0) }
    }

    static func search(_ c: Conf, _ q: String) async -> [LibItem] {
        guard case let .success(sr) = await call(c, "search3", ["query": q, "songCount": "30", "albumCount": "0", "artistCount": "0"]) else { return [] }
        return list((sr["searchResult3"] as? [String: Any])?["song"]).map { song(c, $0) }
    }
}

// MARK: - Plex Media Server (music libraries)

nonisolated enum PlexLib {
    struct Conf: Sendable, Equatable {
        var server: String, token: String
        var ok: Bool { !server.trimmingCharacters(in: .whitespaces).isEmpty && !token.trimmingCharacters(in: .whitespaces).isEmpty }
    }

    private static func url(_ c: Conf, _ path: String, _ q: [String: String] = [:]) -> URL? {
        guard let u = Net.url(c.server, path), var comp = URLComponents(url: u, resolvingAgainstBaseURL: false) else { return nil }
        comp.queryItems = (comp.queryItems ?? []) + q.sorted { $0.key < $1.key }.map { .init(name: $0.key, value: $0.value) }
            + [.init(name: "X-Plex-Token", value: c.token.trimmingCharacters(in: .whitespaces))]
        return comp.url
    }

    private static func get(_ c: Conf, _ path: String, _ q: [String: String] = [:]) async -> [String: Any]? {
        guard let u = url(c, path, q),
              let (d, code) = await Net.data(u, timeout: 10, headers: ["Accept": "application/json", "X-Plex-Product": "Skjold",
                                                                       "X-Plex-Client-Identifier": "skjold-ios"]),
              code == 200, let j = jsonObject(d) else { return nil }
        return j["MediaContainer"] as? [String: Any]
    }

    static func thumb(_ c: Conf, _ path: String) -> String {
        guard !path.isEmpty else { return "" }
        return url(c, "/photo/:/transcode", ["width": "300", "height": "300", "minSize": "1", "url": path])?.absoluteString ?? ""
    }

    /// Key of the first music library ("artist" section).
    static func musicSection(_ c: Conf) async -> String? {
        guard let mc = await get(c, "/library/sections") else { return nil }
        return list(mc["Directory"]).first { str($0, "type") == "artist" }.map { str($0, "key") }
    }

    private static func track(_ c: Conf, _ t: [String: Any]) -> LibItem {
        let part = list(list(t["Media"]).first?["Part"]).first.map { str($0, "key") } ?? ""
        let artist = str(t, "originalTitle").isEmpty ? str(t, "grandparentTitle") : str(t, "originalTitle")
        let th = str(t, "parentThumb").isEmpty ? str(t, "thumb") : str(t, "parentThumb")
        return LibItem(id: str(t, "ratingKey"), title: str(t, "title"), artist: artist, album: str(t, "parentTitle"),
                       cover: thumb(c, th), stream: part.isEmpty ? "" : url(c, part)?.absoluteString ?? "", dur: num(t, "duration") / 1000)
    }

    /// sort: "addedAt:desc", "viewCount:desc", "random"
    static func albums(_ c: Conf, section: String, sort: String, size: Int = 16) async -> [LibColl]? {
        guard let mc = await get(c, "/library/sections/\(section)/all",
                                 ["type": "9", "sort": sort, "X-Plex-Container-Start": "0", "X-Plex-Container-Size": "\(size)"]) else { return nil }
        return list(mc["Metadata"]).map {
            LibColl(id: str($0, "ratingKey"), name: str($0, "title"), artist: str($0, "parentTitle"), cover: thumb(c, str($0, "thumb")),
                    count: num($0, "leafCount"), playlist: false)
        }
    }

    static func playlists(_ c: Conf) async -> [LibColl]? {
        guard let mc = await get(c, "/playlists", ["playlistType": "audio"]) else { return nil }
        return list(mc["Metadata"]).map {
            LibColl(id: str($0, "ratingKey"), name: str($0, "title"), artist: "",
                    cover: thumb(c, str($0, "composite").isEmpty ? str($0, "thumb") : str($0, "composite")),
                    count: num($0, "leafCount"), playlist: true)
        }
    }

    static func tracks(_ c: Conf, _ col: LibColl) async -> [LibItem] {
        let path = col.playlist ? "/playlists/\(col.id)/items" : "/library/metadata/\(col.id)/children"
        guard let mc = await get(c, path) else { return [] }
        return list(mc["Metadata"]).map { track(c, $0) }
    }

    static func search(_ c: Conf, section: String, _ q: String) async -> [LibItem] {
        guard let mc = await get(c, "/library/sections/\(section)/search", ["type": "10", "query": q]) else { return [] }
        return list(mc["Metadata"]).prefix(30).map { track(c, $0) }
    }
}

// MARK: - GitHub Releases (skjold-v* in SebastianKristo/pult-forsterker)

nonisolated enum GitHubReleases {
    static let repo = "SebastianKristo/pult-forsterker"
    static let prefix = "skjold-v"

    struct Rel: Sendable { var tag: String, name: String, date: String, notes: [String], size: String, pre: Bool }

    /// Newest skjold-v* release (betas only when `includePre`). `.failure` when GitHub could not be reached.
    static func latest(includePre: Bool) async -> Result<Rel?, Subsonic.Failure> {
        guard let u = URL(string: "https://api.github.com/repos/\(repo)/releases?per_page=30"),
              let (d, code) = await Net.data(u, timeout: 10, headers: ["Accept": "application/vnd.github+json"]) else {
            return .failure(.init(text: "Fikk ikke kontakt med GitHub"))
        }
        guard code == 200, let arr = try? JSONSerialization.jsonObject(with: d) as? [[String: Any]] else {
            return .failure(.init(text: "GitHub svarte \(code)"))
        }
        for r in arr {
            let tag = str(r, "tag_name")
            let pre = (r["prerelease"] as? NSNumber)?.boolValue ?? false
            if (r["draft"] as? NSNumber)?.boolValue == true || !tag.hasPrefix(prefix) || (pre && !includePre) { continue }
            let bytes = list(r["assets"]).reduce(0) { $0 + num($1, "size") }
            let notes = str(r, "body").split(whereSeparator: \.isNewline).map {
                $0.trimmingCharacters(in: .whitespaces).replacingOccurrences(of: #"^[-*•]\s*"#, with: "", options: .regularExpression)
            }.filter { !$0.isEmpty && !$0.hasPrefix("#") }
            let size = bytes > 0 ? String(format: "%.1f MB", Double(bytes) / 1_048_576).replacingOccurrences(of: ".", with: ",") : ""
            let name = str(r, "name")
            return .success(Rel(tag: tag, name: name.isEmpty ? tag : name, date: String(str(r, "published_at").prefix(10)),
                                notes: Array(notes.prefix(6)), size: size, pre: pre))
        }
        return .success(nil)
    }

    static func version(_ tag: String) -> String {
        var v = tag
        if v.hasPrefix(prefix) { v.removeFirst(prefix.count) }
        if v.hasPrefix("v") { v.removeFirst() }
        return v
    }

    /// > 0 when a is newer than b ("1.2.3", "2.0", "1.6.0-beta.1").
    static func cmp(_ a: String, _ b: String) -> Int {
        let pa = version(a).split(whereSeparator: { $0 == "." || $0 == "-" }).map { Int($0) }
        let pb = version(b).split(whereSeparator: { $0 == "." || $0 == "-" }).map { Int($0) }
        for i in 0..<max(pa.count, pb.count) {
            let xo: Int? = i < pa.count ? pa[i] : 0, yo: Int? = i < pb.count ? pb[i] : 0
            guard let x = xo, let y = yo else { continue }
            if x != y { return x - y }
        }
        return 0
    }
}
