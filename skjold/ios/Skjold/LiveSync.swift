import SwiftUI

// Live connection to the real system: Skjold daemons (ki_amp_daemon.py, port 8765), Lyrion, Navidrome, Plex and GitHub.
// AppModel.swift keeps the design's state and actions; the actions call into here when `live` is true.
// With no known device the app runs in demo mode on the design's sample data (SK.sysDefault, SK.lt …).

/// A Skjold device the app has talked to. Saved, so rooms survive restarts and Bonjour hiccups.
struct KnownDevice: Codable, Hashable, Sendable {
    var host: String       // "ip:port"
    var id: String         // daemon "id" (hostname)
    var name: String
    var product: String    // s1 | node | core
}

/// Navidrome / Plex content for LibraryView. `state`: "" not loaded, "busy", "ok", otherwise an error text.
struct LibData {
    var state = ""
    var newest: [LibColl] = []
    var other: [LibColl] = []
    var frequent: [LibColl] = []
    var playlists: [LibColl] = []
    var tracks: [String: [Track]] = [:]

    /// All albums once, newest first (LibraryView indexes into this).
    var albums: [LibColl] {
        var out: [LibColl] = []
        for a in newest + other + frequent where !out.contains(where: { $0.id == a.id }) { out.append(a) }
        return out
    }
}

extension AppModel {
    enum Link: Equatable { case none, connecting, online, offline }

    /// Demo mode: no Skjold device has ever been found or chosen.
    var demo: Bool { known.isEmpty && stedId.isEmpty }
    var live: Bool { !demo }

    /// The active room is a plain Lyrion player (no Skjold daemon): control it over JSON-RPC.
    var actLyrionOnly: Bool { live && actRoom.host == nil && actRoom.pid != nil && lyrionServer != nil }
    var activeLyrion: Lyrion.PStatus? { actLyrionOnly ? actRoom.pid.flatMap { lyStats[$0] } : nil }

    /// Status of the device behind the room selected in Innstillinger.
    var devRoomStatus: DevStatus? { devRoom.host.flatMap { $0 == activeHost ? dev : devStats[$0] } }
    /// Host settings are sent to: the device chosen in Innstillinger, else the active one.
    var settingsHost: String? { devRoom.host ?? activeHost }

    var lyrionURL: URL? { lyrionServer.flatMap { Net.url($0, "/") } }

    // MARK: Hold window (like hold() in skjold/app/src/lib/store.ts)

    /// The user's last change wins for a while: status that arrives meanwhile does not overwrite it.
    func hold(_ k: String, _ seconds: Double = 1.5) { holds[k] = Date().addingTimeInterval(seconds) }
    func held(_ k: String) -> Bool { (holds[k] ?? .distantPast) > Date() }

    // MARK: Connect

    /// Talks to a device ("ip", "ip:port", "name.local" or a URL), remembers it and makes it the active one.
    @discardableResult
    func connect(_ raw: String) async -> Bool {
        let h = DeviceLink.normHost(raw)
        link = .connecting
        guard let st = await DeviceLink.status(at: h) else { link = dev == nil ? .none : link; return false }
        let wasDemo = demo
        remember(h, st)
        if wasDemo {
            upd = UpdateState(version: st.version, repo: GitHubReleases.repo, channel: upd.channel, auto: upd.auto, failNext: false,
                              latest: nil, checkedAt: "", log: [], backups: [])
            hist = [:]
        }
        activeHost = h
        dev = nil
        apply(st, host: h)
        rebuildRooms()
        if let r = sys.rooms.first(where: { $0.host == h }) { sys.active = r.id; setDev = r.id }
        startLive()
        return true
    }

    func remember(_ h: String, _ st: DevStatus) {
        var k = known.filter { $0.host != h && (st.id.isEmpty || $0.id != st.id) }
        k.insert(KnownDevice(host: h, id: st.id.isEmpty ? h : st.id, name: st.name, product: st.product), at: 0)
        known = Array(k.prefix(16))
    }

    /// Bonjour found and resolved a device: add it to the system (and leave demo mode).
    func discovered(_ d: FoundDevice) {
        guard let h = d.host, !known.contains(where: { $0.host == h }) else { return }
        Task { [weak self] in
            guard let self, let st = await DeviceLink.status(at: h) else { return }
            if self.known.contains(where: { $0.id == st.id && $0.host != h }) {
                // same box, new address (DHCP): update it
                self.remember(h, st)
                if self.activeHost == nil || self.dev == nil { self.activeHost = h }
                return
            }
            if self.demo && self.mode == .app { _ = await self.connect(h); return }
            if self.mode == .app { self.remember(h, st); self.devStats[h] = st; self.rebuildRooms() }
        }
    }

    func startLive() {
        browser.onResolved = { [weak self] d in self?.discovered(d) }
        browser.start()
        guard live else { return }
        if activeHost == nil { activeHost = known.first?.host }
        startEvents()
        run("poll") { [weak self] in
            var n = 0
            while !Task.isCancelled {
                guard let self else { return }
                await self.pollSystem()
                if n % 8 == 0, let h = self.settingsHost { await self.loadSettings(h) }
                n += 1
                try? await Task.sleep(for: .seconds(4))
            }
        }
        Task { [weak self] in await self?.loadPresets() }
    }

    /// Subscribes to /api/events of the active device; falls back to polling /api/status every 2 s.
    func startEvents() {
        run("sse") { [weak self] in
            var fails = 0
            while !Task.isCancelled {
                guard let self, let h = self.activeHost, let url = Net.url(h, "/api/events") else {
                    try? await Task.sleep(for: .seconds(2)); continue
                }
                var got = false
                do {
                    for try await d in DeviceEvents.stream(url) {
                        if Task.isCancelled || self.activeHost != h { break }
                        if let st = DevStatus(d) { got = true; fails = 0; self.apply(st, host: h) }
                    }
                } catch {}
                if Task.isCancelled { return }
                if let st = await DeviceLink.status(at: h) {
                    fails = 0; self.apply(st, host: h)
                } else {
                    fails += 1
                    if fails >= 2 { self.link = .offline; self.rebuildRooms() }
                }
                try? await Task.sleep(for: .seconds(got ? 0.5 : 2))
            }
        }
    }

    // MARK: Status → model

    func apply(_ st: DevStatus, host h: String) {
        devStats[h] = st
        guard h == activeHost else { return }
        let first = dev == nil || link != .online
        dev = st
        link = .online
        if !st.lyrionServer.isEmpty { lyrionServer = st.lyrionServer }
        headphones = st.headphones
        if upd.repo == GitHubReleases.repo, !st.version.isEmpty, upd.version != st.version { upd.version = st.version }

        let cover = DeviceLink.shared.coverURL(st.coverURL)
        if !cover.isEmpty { CoverStore.shared.set(st.title, cover) }
        if let rn = st.radioNow, !rn.name.isEmpty { LogoStore.shared.adopt(rn.name, rn.image) }

        let sig = st.presetTitles.joined(separator: "\u{1}")
        if sig != presetSig {
            presetSig = sig
            Task { [weak self] in await self?.loadPresets() }
        }
        if first { Task { [weak self] in await self?.loadSettings(h) } }

        guard !actLyrionOnly else { return }
        if !held("vol") { vol = st.volume }
        if !held("pos") { pos = st.position }

        // a library track we started on the amplifier (via Lyrion as a stream)?
        if let ls = libStream {
            if st.input == "radio", st.radioNow?.url == ls {
                if st.playing { libSawPlaying = true }
                else if libSawPlaying && !st.paused && !held("input") { libSawPlaying = false; libEnded() }
                if !held("play") { playing = st.playing }
                return
            }
            if !held("input") { libStream = nil; lq = nil; svc = nil }
        }
        if !held("play") { playing = st.playing }
        guard !held("input") else { return }
        switch st.input {
        case "airplay": input = 0; if svc != "upnp" { svc = nil }
        case "bt": input = 1; svc = nil
        case "aux", "aux2": input = 2; svc = nil
        case "usb": input = 4; svc = nil
        case "spotify": input = 0; svc = "spotify"
        case "plex": input = 0; svc = "plex"
        case "radio":
            input = 3; svc = nil
            if let rn = st.radioNow {
                if rn.n > 0, let i = presetNs.firstIndex(of: rn.n) { station = i; rTmp = nil }
                else if !rn.name.isEmpty, rn.n == 0 {
                    if let i = radio.firstIndex(where: { $0.url == rn.url && !rn.url.isEmpty }) { station = i; rTmp = nil }
                    else if rTmp?.name != rn.name { rTmp = Station(name: rn.name, genre: rn.genre.isEmpty ? "Nettradio" : rn.genre, url: rn.url, image: rn.image) }
                }
            }
        default: break
        }
    }

    /// Now playing from the live system. nil = use the design's local text (AUX/USB, demo, library queue).
    var liveNP: NowPlaying? {
        guard live, libTrack == nil else { return nil }
        if actLyrionOnly {
            let s = activeLyrion
            let t = s?.title ?? ""
            return NowPlaying(st: "Lyrion · " + actRoom.name, t: t.isEmpty ? "Ingenting spiller" : t,
                              s: [s?.artist ?? "", s?.album ?? ""].filter { !$0.isEmpty }.joined(separator: " · "))
        }
        guard let d = dev else {
            return NowPlaying(st: actRoom.name, t: link == .offline ? "Frakoblet" : "Kobler til …", s: activeHost ?? "")
        }
        if link == .offline { return NowPlaying(st: d.name, t: "Frakoblet", s: "Får ikke kontakt med \(d.name)") }
        if !d.power { return NowPlaying(st: d.name, t: "Standby", s: srcName) }
        switch input {
        case 2, 4: return nil
        case 3:
            let name = d.radioNow?.name.isEmpty == false ? d.radioNow!.name : curRadio.name
            return NowPlaying(st: "Radio · " + name, t: d.title.isEmpty || d.title == name ? "Direkte" : d.title,
                              s: d.artist.isEmpty ? name : d.artist)
        default:
            let who = input == 1 ? d.btDevice : d.airplayDevice
            return NowPlaying(st: who.isEmpty ? srcName : srcName + " · " + who, t: d.title.isEmpty ? "Ingenting spiller" : d.title,
                              s: [d.artist, d.album].filter { !$0.isEmpty }.joined(separator: " · "))
        }
    }

    // MARK: Commands

    /// Sends to the active device. Result status (if any) is applied straight away.
    func devSend(_ path: String, _ body: [String: Any] = [:], method: String = "POST", on host: String? = nil) {
        guard let h = host ?? activeHost else { return }
        let data = DeviceLink.json(body, method: method)
        Task { [weak self] in
            let d = await DeviceLink.shared.sendRaw(path, data, method: method, on: h)
            if let d, let st = DevStatus(d) { self?.apply(st, host: h) }
        }
    }

    func lyrionCmd(_ pid: String, _ cmd: [String]) {
        guard let srv = lyrionServer else { return }
        Task { await Lyrion.command(srv, pid, cmd) }
    }

    func liveTransport(_ action: String) {
        if actLyrionOnly, let pid = actRoom.pid {
            switch action {
            case "play": lyrionCmd(pid, ["pause", "0"])
            case "pause": lyrionCmd(pid, ["pause", "1"])
            case "next": lyrionCmd(pid, ["playlist", "index", "+1"])
            case "previous": lyrionCmd(pid, ["playlist", "index", "-1"])
            default: break
            }
            return
        }
        devSend("/api/transport", ["action": action])
    }

    /// Volume with at most one request in flight; the newest value is sent when the previous answer arrives.
    func liveVolume(_ v: Int) {
        hold("vol", 1.2)
        if actLyrionOnly, let pid = actRoom.pid { lyrionCmd(pid, ["mixer", "volume", "\(v)"]); return }
        volWant = v
        pumpVolume()
    }

    private func pumpVolume() {
        guard !volBusy, let v = volWant, let h = activeHost else { return }
        volWant = nil
        volBusy = true
        Task { [weak self] in
            _ = await DeviceLink.shared.send("/api/volume", ["volume": v], on: h)
            guard let self else { return }
            self.volBusy = false
            self.hold("vol", 0.8)
            self.pumpVolume()
        }
    }

    func roomVolume(_ r: Room, _ v: Int) {
        if let h = r.host { Task { await DeviceLink.shared.send("/api/volume", ["volume": v], on: h) } }
        else if let pid = r.pid { lyrionCmd(pid, ["mixer", "volume", "\(v)"]) }
    }

    static let inputNames = ["airplay", "bt", "aux", "radio", "usb"]

    func liveInput(_ i: Int) {
        hold("input", 2.5)
        libStream = nil
        devSend("/api/input", ["input": Self.inputNames[max(0, min(4, i))]])
    }

    /// Spotify Connect / UPnP from Kilder. Spotify is a real input on newer daemons; UPnP has no backend yet.
    func pickService(_ s: String) {
        svc = s; input = 0; full = true
        guard live, s == "spotify", dev?.inputs.contains("spotify") == true else { return }
        hold("input", 2.5)
        devSend("/api/input", ["input": "spotify"])
    }

    func livePlayFavourite(_ i: Int) {
        hold("input", 3)
        libStream = nil
        let n = i < presetNs.count ? presetNs[i] : i + 1
        devSend("/api/presets/\(n)/play")
    }

    func livePlayStream(_ st: Station) {
        hold("input", 3)
        libStream = nil
        Task { [weak self] in
            var url = st.url ?? ""
            if url.isEmpty { url = await RadioBrowser.streamURL(for: st.name) ?? "" }
            guard let self, !url.isEmpty else { Haptics.error(); return }
            var body: [String: Any] = ["url": url, "title": st.name, "genre": st.genre]
            if let img = st.image ?? LogoStore.shared.url(for: st.name)?.absoluteString { body["image"] = img }
            self.devSend("/api/radio/play", body)
        }
    }

    /// Library track → the amplifier plays the stream URL through Lyrion (POST /api/radio/play).
    func livePlayTrack(_ tr: Track) {
        guard !tr.stream.isEmpty else { Haptics.warning(); return }
        hold("input", 4); hold("play", 4); hold("pos", 2)
        libStream = tr.stream
        libSawPlaying = false
        if !tr.cover.isEmpty { CoverStore.shared.set(tr.t, tr.cover); CoverStore.shared.set(tr.album, tr.cover) }
        devSend("/api/radio/play", ["url": tr.stream, "title": tr.artist.isEmpty ? tr.t : tr.t + " – " + tr.artist, "image": tr.cover])
    }

    /// The stream of a library track finished: play the next one in the queue.
    func libEnded() {
        guard let lq, svc != nil, !lq.isEmpty else { return }
        if li + 1 < lq.count || repeatOn { playLib(lq, (li + 1) % lq.count, keepOpen: true) } else { libStream = nil }
    }

    // MARK: Radio favourites (GET/POST /api/presets)

    func loadPresets() async {
        guard let h = activeHost, let d = await DeviceLink.shared.get("/api/presets", on: h), let ps = DevPreset.list(d) else { return }
        if ps.isEmpty {
            if !radio.isEmpty { pushPresets(radio) }
            return
        }
        presetNs = ps.map(\.n)
        let l = ps.map { Station(name: $0.title, genre: $0.genre.isEmpty ? "Nettradio" : $0.genre, url: $0.url, image: $0.image.isEmpty ? nil : $0.image) }
        for p in ps { LogoStore.shared.adopt(p.title, p.image) }
        if l != radio { radio = l; station = min(station, max(0, l.count - 1)) }
        LogoStore.shared.fetch(l.map(\.name))
    }

    /// Replaces the favourites on the amplifier. Catalog stations without a URL are looked up on Radio Browser first.
    func pushPresets(_ l: [Station]) {
        guard let h = activeHost else { return }
        Task { [weak self] in
            var out: [Station] = []
            for var s in l {
                if (s.url ?? "").isEmpty { s.url = await RadioBrowser.streamURL(for: s.name) }
                out.append(s)
            }
            let body: [[String: Any]] = out.compactMap { s in
                guard let u = s.url, !u.isEmpty else { return nil }
                return ["title": s.name, "url": u, "genre": s.genre, "icon": s.image ?? LogoStore.shared.url(for: s.name)?.absoluteString ?? ""]
            }
            guard let self else { return }
            if body.count < out.count { Haptics.warning() }
            _ = await DeviceLink.shared.send("/api/presets", ["presets": body], on: h)
            await self.loadPresets()
        }
    }

    // MARK: Settings (GET/POST /api/settings)

    static let boolKeys: Set<String> = Set(SK.cats.flatMap(\.items).filter { $0.kind == .bool }.map(\.k)).union(["updAuto", "setupDone"])
    /// Innloggingene til musikktjenestene lagres nå på forsterkeren (/api/settings), så appen og web-UI-et deler dem.
    static let localKeys: Set<String> = []
    static let serviceKeys = ["ytmUser", "ytmCookie", "ndUrl", "ndUser", "ndPass", "plexUrl", "plexToken"]
    static let stringKeys = ["nAux1", "nAux2", "nUsb1", "nUsb2", "nameCustom"] + serviceKeys

    func loadSettings(_ h: String) async {
        guard let d = await DeviceLink.shared.get("/api/settings", on: h), let s = DevSettings(d), h == settingsHost else { return }
        var n = sset
        for (k, v) in s.ints where !held("set-" + k) { n[k] = v }
        if n != sset { sset = n }
        if let f = s.ints["hold"] { fav = f }
        var nm = names
        var push: [String: Any] = [:]
        for k in Self.stringKeys {
            guard !held("set-" + k) else { continue }
            if let v = s.strings[k], !(v.isEmpty && Self.serviceKeys.contains(k) && !(nm[k] ?? "").isEmpty) { nm[k] = v }
            else if Self.serviceKeys.contains(k), let mine = nm[k], !mine.isEmpty { push[k] = mine }   // forsterkeren er tom: send det appen har
        }
        if nm != names { names = nm }
        if !push.isEmpty { let data = DeviceLink.json(push); Task { await DeviceLink.shared.sendRaw("/api/settings", data, on: h) } }
        var e = eqP
        for (src, p) in s.eq where !held("eq-" + src) { e[src] = EQProfile(preset: p.preset, eq: p.eq, loud: p.loud) }
        if e != eqP { eqP = e }
    }

    func liveSetting(_ k: String, _ v: Any) {
        guard !Self.localKeys.contains(k), let h = settingsHost else { return }
        hold("set-" + k, 3)
        var val = v
        if let i = v as? Int, Self.boolKeys.contains(k) { val = i != 0 }
        var patch: [String: Any] = [k: val]
        if k == "name" { patch["nameCustom"] = ""; names["nameCustom"] = "" }
        let data = DeviceLink.json(patch)
        Task { await DeviceLink.shared.sendRaw("/api/settings", data, on: h) }
    }

    func liveEQ(_ src: String) {
        guard let h = settingsHost, let p = eqP[src] else { return }
        hold("eq-" + src, 3)
        let data = DeviceLink.json(["eq": [src: ["preset": p.preset, "eq": p.eq, "loud": p.loud] as [String: Any]]])
        Task { await DeviceLink.shared.sendRaw("/api/settings", data, on: h) }
    }

    /// 440 Hz tone left, then right (POST /api/test).
    func speakerTest(on h: String?) {
        guard let h = h ?? activeHost else { return }
        Task {
            _ = await DeviceLink.shared.send("/api/test", ["channel": "L"], on: h, timeout: 12)
            try? await Task.sleep(for: .milliseconds(300))
            _ = await DeviceLink.shared.send("/api/test", ["channel": "R"], on: h, timeout: 12)
        }
    }

    /// Info rows in Innstillinger (Parede enheter, Lyrion, IP …).
    func infoText(_ key: String?) -> String {
        let st = devRoomStatus
        let offline = live && st == nil && devRoom.host != nil
        switch key {
        case "btDev":
            if demo { return "Sebastians iPhone, MacBook Pro" }
            if offline { return "Frakoblet" }
            return st.map { $0.btDevice.isEmpty ? "Ingen tilkoblet" : $0.btDevice } ?? "–"
        case "lyrion":
            if demo { return "Demo" }
            if offline { return "Frakoblet" }
            if let st, st.lyrion { return "Tilkoblet · " + (st.lyrionServer.isEmpty ? "ukjent adresse" : st.lyrionServer) }
            if devRoom.host == nil, lyrionServer != nil { return "Tilkoblet · " + (lyrionServer ?? "") }
            return "Ikke funnet"
        case "version": return demo ? upd.version : offline ? "Frakoblet" : st.map { $0.version } ?? "–"
        case "ip":
            if demo { return "192.168.1.42" }
            return devRoom.host.map { h in String(h.split(separator: ":").first ?? Substring(h)) } ?? "–"
        case "serial": return demo ? "SKJ-S1-0001" : st.map { $0.id } ?? "–"
        case "netName": return demo ? "Skjold · romnavn" : st.map { $0.name } ?? devRoom.name
        case "ytmPo": return "Ikke tilgjengelig"
        default: return ""
        }
    }

    // MARK: Rooms (Skjold devices + Lyrion players)

    func pollSystem() async {
        for k in devices where k.host != activeHost {
            if !stedId.isEmpty, stedEnheter.first(where: { $0.id == k.id })?.online == false { devStats[k.host] = nil; continue }
            devStats[k.host] = await DeviceLink.status(at: k.host, timeout: HjemAPI.isRelay(k.host) ? 5 : 2.5)
        }
        if let srv = lyrionServer, let ps = await Lyrion.players(srv) {
            lyPlayers = ps
            var st: [String: Lyrion.PStatus] = [:]
            for p in ps where p.connected { st[p.id] = await Lyrion.status(srv, p.id) }
            lyStats = st
            if actLyrionOnly, let pid = actRoom.pid, let s = st[pid] {
                if !held("vol") { vol = s.volume }
                if !held("play") { playing = s.playing }
                if !held("pos") { pos = s.time }
                if !s.cover.isEmpty { CoverStore.shared.set(s.title, s.cover) }
            }
        }
        rebuildRooms()
    }

    static func hw(_ type: String, _ st: DevStatus?) -> String {
        let base = ["s1": "Pi Zero 2 W · TPA3116 2 × 50 W", "node": "Raspberry Pi · Skjold Node", "core": "Raspberry Pi · Lyrion-server"][type] ?? "Raspberry Pi"
        guard let v = st?.version, !v.isEmpty else { return base }
        return base + " · v" + v
    }

    func rebuildRooms() {
        guard live else { return }
        let prev = sys
        var rooms: [Room] = []
        var used = Set<String>()
        for k in devices {
            let st = k.host == activeHost ? (link == .offline ? nil : dev) : devStats[k.host]
            let id = (st?.id).flatMap { $0.isEmpty ? nil : $0 } ?? k.id
            let p = st?.product ?? k.product
            let type = ["s1", "node", "core", "touch"].contains(p) ? p : "s1"
            var r = Room(id: id, name: st?.name ?? k.name, type: type, hw: Self.hw(type, st), vol: st?.volume ?? 0, host: k.host)
            var pid = (st?.lyrionPlayer ?? "").lowercased()
            if pid.isEmpty || pid == "00:00:00:00:00:01" {
                pid = lyPlayers.first { $0.name.caseInsensitiveCompare(r.name) == .orderedSame }?.id.lowercased() ?? ""
            }
            if !pid.isEmpty, lyPlayers.isEmpty || lyPlayers.contains(where: { $0.id.lowercased() == pid }) { r.pid = pid; used.insert(pid) }
            if st == nil { r.np = ["Frakoblet", HjemAPI.isRelay(k.host) ? "Skjold-hjem" : k.host] }
            else if k.host != activeHost, let st, st.playing, !st.title.isEmpty { r.np = [st.title, st.artist.isEmpty ? st.name : st.artist] }
            if !rooms.contains(where: { $0.id == r.id }) { rooms.append(r) }
        }
        // Andre Lyrion-spillere (max2play, TV-bokser …) er ikke Skjold-enheter – bare med når brukeren ber om det.
        let others = UserDefaults.standard.bool(forKey: "skjold-show-lyrion-players")
        for p in lyPlayers where others && !used.contains(p.id.lowercased()) {
            var r = Room(id: p.id, name: p.name, type: "node", hw: (p.model.isEmpty ? "Lyrion-spiller" : p.model) + " · Lyrion",
                         vol: lyStats[p.id]?.volume ?? 0, pid: p.id)
            if !p.connected { r.np = ["Frakoblet", "Lyrion"] }
            else if let s = lyStats[p.id], s.playing, !s.title.isEmpty { r.np = [s.title, s.artist.isEmpty ? "Lyrion" : s.artist] }
            rooms.append(r)
        }
        let lyGroups = !lyStats.isEmpty && !held("groups")
        for i in rooms.indices {
            let old = prev.rooms.first { $0.id == rooms[i].id }
            rooms[i].role = old?.role
            if held("rvol-" + rooms[i].id), let old { rooms[i].vol = old.vol }
            if lyGroups, let pid = rooms[i].pid, let s = lyStats[pid] ?? lyStats.first(where: { $0.key.lowercased() == pid })?.value {
                let master = !s.syncMaster.isEmpty ? s.syncMaster : (s.syncSlaves.isEmpty ? "" : pid)
                rooms[i].group = master.isEmpty ? nil : "ly-" + master.lowercased()
                if rooms[i].group != nil { rooms[i].np = nil }
            } else {
                rooms[i].group = old?.group
            }
        }
        var n = SystemState(active: prev.active, rooms: rooms, modes: prev.modes)
        if !rooms.contains(where: { $0.id == n.active }) {
            n.active = rooms.first { $0.host == activeHost }?.id ?? rooms.first?.id ?? ""
        }
        if n.rooms != prev.rooms || n.active != prev.active { sys = n }
    }

    /// Room tile tapped / active room changed.
    func activate(_ r: Room) {
        if let h = r.host, h != activeHost {
            activeHost = h
            dev = nil
            link = .connecting
            libStream = nil
            if let st = devStats[h] { apply(st, host: h) }
            startEvents()
            Task { [weak self] in await self?.loadPresets() }
        }
        setDev = r.id
    }

    /// setSys() from RoomsView in live mode: volumes per room and Lyrion sync for group changes.
    func liveSys(old: SystemState, new n: SystemState) {
        if n.active != old.active, let r = n.rooms.first(where: { $0.id == n.active }) { activate(r) }
        var groupsChanged = false
        for r in n.rooms {
            guard let o = old.rooms.first(where: { $0.id == r.id }) else { continue }
            if o.vol != r.vol && r.id != n.active { hold("rvol-" + r.id, 2.5); roomVolume(r, r.vol) }
            if o.group != r.group { groupsChanged = true }
        }
        guard groupsChanged, let srv = lyrionServer else { return }
        hold("groups", 5)
        var cmds: [(String, [String])] = []
        for r in n.rooms {
            guard let pid = r.pid, let o = old.rooms.first(where: { $0.id == r.id }), o.group != r.group else { continue }
            guard let g = r.group else { cmds.append((pid, ["sync", "-"])); continue }
            let members = n.rooms.filter { $0.group == g && $0.pid != nil }
            let leader = members.first { $0.id == n.active } ?? members.first
            if let lp = leader?.pid, lp != pid { cmds.append((lp, ["sync", pid])) }
        }
        Task {
            for (p, c) in cmds { await Lyrion.command(srv, p, c) }
        }
    }

    // MARK: Libraries (Navidrome, Plex; YouTube Music has no backend)

    var ndConf: Subsonic.Conf { Subsonic.Conf(url: names["ndUrl"] ?? "", user: names["ndUser"] ?? "", pass: names["ndPass"] ?? "") }
    var plexConf: PlexLib.Conf { PlexLib.Conf(server: names["plexUrl"] ?? "", token: names["plexToken"] ?? "") }

    func loadLib(_ id: String, force: Bool = false) async {
        guard live else { return }
        if !force, let s = libs[id]?.state, s == "ok" || s == "busy" { return }
        var d = LibData()
        d.state = "busy"
        libs[id] = d
        switch id {
        case "nd":
            let c = ndConf
            guard c.ok else { d.state = "Navidrome er ikke satt opp. Legg inn server, brukernavn og passord under Innstillinger → Musikktjenester."; break }
            async let a = Subsonic.albums(c, "newest")
            async let r = Subsonic.albums(c, "random")
            async let f = Subsonic.albums(c, "frequent")
            async let p = Subsonic.playlists(c)
            let (ra, rr, rf, rp) = await (a, r, f, p)
            switch ra {
            case let .success(x): d.newest = x; d.state = "ok"
            case let .failure(e): d.state = "Navidrome: " + e.text
            }
            d.other = (try? rr.get()) ?? []
            d.frequent = (try? rf.get()) ?? []
            d.playlists = (try? rp.get()) ?? []
        case "plex":
            let c = plexConf
            guard c.ok else { d.state = "Plex er ikke satt opp. Legg inn server og token under Innstillinger → Musikktjenester."; break }
            guard let sec = await PlexLib.musicSection(c) else { d.state = "Fant ikke Plex-serveren eller et musikkbibliotek."; break }
            async let a = PlexLib.albums(c, section: sec, sort: "addedAt:desc")
            async let r = PlexLib.albums(c, section: sec, sort: "random")
            async let f = PlexLib.albums(c, section: sec, sort: "viewCount:desc")
            async let p = PlexLib.playlists(c)
            let (ra, rr, rf, rp) = await (a, r, f, p)
            d.newest = ra ?? []; d.other = rr ?? []; d.frequent = rf ?? []; d.playlists = rp ?? []
            d.state = ra == nil ? "Plex svarte ikke." : "ok"
        default:
            d.state = "YouTube Music er ikke koblet til. Forsterkeren har ingen YouTube Music-tjeneste ennå."
        }
        for c in d.albums + d.playlists { CoverStore.shared.set(c.name, c.cover) }
        libs[id] = d
    }

    static func track(_ x: LibItem) -> Track {
        Track(t: x.title, artist: x.artist, album: x.album, dur: x.dur, id: x.id, cover: x.cover, stream: x.stream)
    }

    func collTracks(_ lib: String, _ c: LibColl) async -> [Track] {
        if let t = libs[lib]?.tracks[c.id], !t.isEmpty { return t }
        let items: [LibItem]
        if lib == "plex" { items = await PlexLib.tracks(plexConf, c) } else { items = await Subsonic.tracks(ndConf, c) }
        let t = items.map(Self.track)
        for x in t where !x.cover.isEmpty { CoverStore.shared.set(x.album, x.cover) }
        libs[lib, default: LibData()].tracks[c.id] = t
        return t
    }

    func searchLib(_ lib: String, _ q: String) async -> [Track] {
        let items: [LibItem]
        switch lib {
        case "nd":
            guard ndConf.ok else { return [] }
            items = await Subsonic.search(ndConf, q)
        case "plex":
            guard plexConf.ok, let sec = await PlexLib.musicSection(plexConf) else { return [] }
            items = await PlexLib.search(plexConf, section: sec, q)
        default: items = []
        }
        let t = items.map(Self.track)
        for x in t where !x.cover.isEmpty { CoverStore.shared.set(x.album, x.cover) }
        return t
    }

    func testNavidrome() {
        ndT = "busy"
        Task { [weak self] in
            guard let self else { return }
            let err = await Subsonic.ping(self.ndConf)
            self.ndOK = err == nil
            self.ndT = err ?? "Tilkoblet"
            if err == nil { Haptics.success(); self.libs["nd"] = nil } else { Haptics.error() }
        }
    }

    // MARK: Updates (GitHub Releases, skjold-v*)

    func liveCheckUpdate() {
        checking = true; job = nil; updMsg = ""
        if upd.repo != GitHubReleases.repo { upd.repo = GitHubReleases.repo }
        run("check") { [weak self] in
            let r = await GitHubReleases.latest(includePre: (self?.upd.channel ?? 0) == 1)
            guard let self else { return }
            self.checking = false
            self.upd.checkedAt = SK.now()
            switch r {
            case let .failure(e):
                Haptics.error()
                self.updMsg = e.text + "."
            case let .success(rel):
                Haptics.tick()
                if let rel, GitHubReleases.cmp(rel.tag, self.upd.version) > 0 {
                    self.upd.latest = Release(tag: rel.tag, name: rel.name, date: rel.date, notes: rel.notes, size: rel.size, pre: rel.pre)
                } else {
                    self.upd.latest = nil
                    let newest = rel.map { " Nyeste utgivelse er \(GitHubReleases.version($0.tag))." } ?? ""
                    self.updMsg = "Du har siste versjon (\(self.upd.version)). Sjekket \(SK.now()).\(newest)"
                }
            }
        }
    }
}
