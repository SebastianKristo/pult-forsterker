import SwiftUI

/// App state. Mirrors `state` + the logic in `class Component` of "Skjold App v2.dc.html".
@Observable
final class AppModel {
    enum Mode { case onboard, app }

    struct NowPlaying { var st: String; var t: String; var s: String }
    struct HistEntry: Hashable { var track: Track; var when: String }
    struct Job { var done = false; var failed = false; var step = ""; var pct = 0; var upd: UpdateState? = nil }

    // MARK: Flow
    var mode: Mode
    var welcome = true
    var intro = true
    var heroI = 0

    // MARK: Onboarding
    var ob = 0
    var scan = false
    var scanFound = false
    var net = 0
    var netManual = false
    var pw = ""
    var ssid = ""
    var sec = 0
    var room = "Stue"
    var roomCustom = false
    var tested: Set<String> = []
    var obUpd = 0
    var obType = "s1"

    // MARK: Navigation
    var tab = 0
    var sub = ""          // "", "radio", "lib"
    var lib = "ytm"
    var libTab = 0
    var libPl: Int? = nil
    var lq2 = ""
    var libHero = 0
    var libMood: Int? = nil
    var hist: [String: [HistEntry]] = [:]

    // MARK: Player
    var full = false
    var queueOpen = false
    var srcOpen = false
    var shuffle = false
    var repeatOn = false
    var input = 0          // 0 AirPlay, 1 Blåtann, 2 AUX, 3 Radio, 4 USB
    var svc: String? = nil // spotify, upnp, ytm, nd
    var playing = true
    var trk = 0
    var pos: Int? = nil
    var vol = 42
    var lq: [Track]? = nil
    var li = 0

    // MARK: Radio
    var station = 1
    var fav = 2
    var rTmp: Station? = nil
    var radio: [Station] { didSet { Store.save(radio, "skjold-radio") } }
    var rEdit = false
    var rAdd = false
    var q = ""
    var rRes: [RadioResult]? = nil
    var rBusy = false
    var rGenre: Int? = nil
    var rMode = "sok"
    var uName = ""
    var uUrl = ""
    var uGenre = ""
    var uTest: String? = nil
    var uDone = ""

    // MARK: Settings
    var setCat = -1
    var openK = ""
    var confirm = ""
    var setDev = "stue" {
        didSet { if live, oldValue != setDev, let h = settingsHost { Task { [weak self] in await self?.loadSettings(h) } } }
    }
    var sset: [String: Int] { didSet { Store.save(sset, "skjold-set") } }
    var names: [String: String] { didSet { Store.save(names, "skjold-names") } }
    var ytmT: Date? = nil
    var plexT: String? = nil   // nil, "busy", or the result text
    var plexOK = false
    var btPairT: Date? = nil
    var headphones = false
    /// App-level look of the tab bar: "glass" (Liquid Glass, floating) or "classic" (the original design).
    var tabStyle: String = UserDefaults.standard.string(forKey: "skjold-tabstyle") ?? "glass" {
        didSet { UserDefaults.standard.set(tabStyle, forKey: "skjold-tabstyle") }
    }

    // MARK: EQ / system / update
    var eqP: [String: EQProfile] { didSet { Store.save(eqP, "skjold-eq") } }
    var eqSrc: String? = nil
    var sys: SystemState { didSet { Store.save(sys, "skjold-sys") } }
    var upd: UpdateState { didSet { Store.save(upd, "skjold-upd") } }
    var job: Job? = nil
    var checking = false
    var updMsg = ""
    var restoreConf = ""

    // MARK: Live system (see LiveSync.swift)
    var known: [KnownDevice] { didSet { Store.save(known, "skjold-known") } }
    var activeHost: String? {
        didSet { UserDefaults.standard.set(activeHost, forKey: "skjold-host"); DeviceLink.shared.host = activeHost }
    }
    var link: Link = .none
    var dev: DevStatus? = nil
    var devStats: [String: DevStatus] = [:]
    var lyrionServer: String? = nil
    var lyPlayers: [Lyrion.Player] = []
    var lyStats: [String: Lyrion.PStatus] = [:]
    var presetNs: [Int] = []
    var wifiNets: [String] = []
    var wifiBusy = false
    var obErr = ""
    var ndT: String? = nil
    var ndOK = false
    var libs: [String: LibData] = [:]
    var libRes: [Track]? = nil
    let browser = DeviceBrowser()
    @ObservationIgnored var holds: [String: Date] = [:]
    @ObservationIgnored var volWant: Int? = nil
    @ObservationIgnored var volBusy = false
    @ObservationIgnored var libStream: String? = nil
    @ObservationIgnored var libSawPlaying = false
    @ObservationIgnored var presetSig = ""

    @ObservationIgnored var tasks: [String: Task<Void, Never>] = [:]

    init() {
        radio = Store.load("skjold-radio") ?? SK.defaultRadio
        sset = Store.load("skjold-set") ?? SK.def
        names = Store.load("skjold-names") ?? [:]
        sys = Store.load("skjold-sys") ?? SK.sysDefault
        var u: UpdateState = Store.load("skjold-upd") ?? SK.updDefault
        if u.repo != GitHubReleases.repo { u.repo = GitHubReleases.repo; u.latest = nil }
        upd = u
        known = Store.load("skjold-known") ?? []
        activeHost = UserDefaults.standard.string(forKey: "skjold-host")
        var eq: [String: EQProfile] = Store.load("skjold-eq") ?? [:]
        if eq["air"] == nil {
            for (k, _) in SK.eqSources {
                let p = SK.eqDefaults[k] ?? 0
                eq[k] = EQProfile(preset: p, eq: SK.eqPresets[p].1, loud: k != "hp")
            }
        }
        eqP = eq
        mode = UserDefaults.standard.bool(forKey: "skjold-setup-done") ? .app : .onboard
        if mode == .app { welcome = false }
        DeviceLink.shared.host = activeHost
    }

    // MARK: - Lifecycle

    func start() {
        LogoStore.shared.fetch(SK.catalog.map(\.name) + radio.map(\.name))
        run("intro") { [weak self] in
            try? await Task.sleep(for: .seconds(4.7))
            self?.intro = false
        }
        run("hero") { [weak self] in
            while !Task.isCancelled {
                try? await Task.sleep(for: .seconds(2.8))
                guard let self else { return }
                if self.mode == .onboard && self.welcome { self.heroI = (self.heroI + 1) % 4 }
            }
        }
        run("pos") { [weak self] in
            while !Task.isCancelled {
                try? await Task.sleep(for: .seconds(1))
                guard let self, self.playing, self.hasProgress else { continue }
                let p = (self.pos ?? (self.live ? 0 : 45)) + 1
                if self.live { self.pos = min(p, self.duration) }   // the amplifier advances by itself
                else if p >= self.duration { self.next() } else { self.pos = p }
            }
        }
        startLive()
    }

    func restartHero(_ i: Int) {
        heroI = i
        tasks["hero"]?.cancel()
        tasks["hero"] = nil
        run("hero") { [weak self] in
            while !Task.isCancelled {
                try? await Task.sleep(for: .seconds(2.8))
                guard let self, !Task.isCancelled else { return }
                if self.mode == .onboard && self.welcome { self.heroI = (self.heroI + 1) % 4 }
            }
        }
    }

    func run(_ key: String, _ op: @escaping @MainActor () async -> Void) {
        tasks[key]?.cancel()
        tasks[key] = Task { await op() }
    }

    /// The design's BroadcastChannel messages, mapped to the daemon API (pi/ki_amp_daemon.py). Demo mode sends nothing.
    /// Messages without an endpoint (setup steps, previewClock, updSync, forget, reset) stay local; see CLAUDE.md.
    func post(_ msg: [String: Any]) {
        guard live, let type = msg["type"] as? String else { return }
        switch type {
        case "setupTest": devSend("/api/test", ["channel": msg["ch"] as? String ?? "L"])
        case "testSpk", "testOut": speakerTest(on: settingsHost)
        case "testVoice": devSend("/api/voice", ["say": "bt_pairing"], on: settingsHost)
        case "btPair": devSend("/api/bt", ["pairing": true], on: settingsHost)
        case "src": if let v = msg["v"] as? Int { livePlayFavourite(v) }
        case "set": if let k = msg["k"] as? String, let v = msg["v"] { liveSetting(k, v) }
        case "eqSync": if let src = msg["src"] as? String { liveEQ(src) }
        default: break
        }
    }

    // MARK: - Onboarding

    static let obText = [("Legg til forsterker", "Slå på forsterkeren. Den dukker opp her."),
                         ("Koble til Wi-Fi", "Sendes kryptert over Blåtann. Godta på forsterkeren med volumknappen."),
                         ("Hvor står den?", "Navnet vises i AirPlay, Blåtann og Lyrion."),
                         ("Test høyttalerne", "Trykk på en side og hør etter."),
                         ("Programvare", "Installerer siste versjon.")]
    static let roomList = ["Stue", "Kjøkken", "Soverom", "Kontor", "Barnerom", "Bad", "Gang", "Verksted"]
    static let nets = ["Hjemme", "Hjemme-5G", "Telenor-8F2A"]

    var needPw: Bool { !netManual || sec < 2 }

    var okOb: Bool {
        switch ob {
        case 0: return true
        case 1: return (!netManual || !ssid.trimmingCharacters(in: .whitespaces).isEmpty) && (!needPw || pw.count >= 8)
        case 2: return roomCustom ? !room.trimmingCharacters(in: .whitespaces).isEmpty : !room.isEmpty
        case 3: return tested.contains("L") && tested.contains("R")
        default: return obUpd >= 100
        }
    }

    var obStep: Int { ob == 4 ? 3 : ob }

    func goOb(_ n: Int) {
        ob = n
        obErr = ""
        post(["type": "setup", "step": [1, 2, 3, 4, 6][min(n, 4)], "name": room])
        if n == 1 && live { loadWifi() }
        if n == 4 && live { checkUpdate() }
        if n == 4 {
            obUpd = 0
            run("obUpd") { [weak self] in
                while let self, self.obUpd < 100, !Task.isCancelled {
                    try? await Task.sleep(for: .milliseconds(110))
                    self.obUpd = min(100, self.obUpd + 5)
                    self.post(["type": "setup", "step": 6, "upd": self.obUpd])
                }
            }
        }
    }

    func obBack() {
        if scan { tasks["scan"]?.cancel(); scan = false; return }
        goOb(ob == 4 ? 2 : ob - 1)
    }

    func obNext() {
        guard okOb else { return }
        if live && ob == 1 { joinWifi(); return }
        if live && ob == 2 {
            let name = room.trimmingCharacters(in: .whitespaces)
            if let h = activeHost { Task { await DeviceLink.shared.send("/api/settings", ["nameCustom": name], on: h) } }
            names["nameCustom"] = name
        }
        // speaker test lives in Innstillinger → Lyd, not in setup
        if ob < 4 { goOb(ob == 2 ? 4 : ob + 1); return }
        if demo, obType == "node", !sys.rooms.contains(where: { $0.name == room }) {
            sys.rooms.append(Room(id: "r\(Int(Date().timeIntervalSince1970 * 1000))", name: room, type: "node", hw: "Raspberry Pi 4 · HDMI", vol: 30))
        }
        Haptics.success()
        mode = .app
        tab = obType == "node" ? 2 : 0
        UserDefaults.standard.set(true, forKey: "skjold-setup-done")
        post(["type": "setup", "step": 7, "name": room])
        if live, let h = activeHost { Task { await DeviceLink.shared.send("/api/settings", ["setupDone": true], on: h) } }
        startLive()
        run("setupDone") { [weak self] in
            try? await Task.sleep(for: .seconds(3))
            self?.post(["type": "setup", "step": 8])
        }
    }

    func pickDevice(_ type: String) { obType = type; goOb(1) }

    /// A real device in «Finn forsterker» (Bonjour or QR): connect, then continue the setup against it.
    func pickFound(_ host: String, type: String) {
        obType = type
        Task { [weak self] in
            guard let self else { return }
            if await self.connect(host) { Haptics.success(); self.goOb(1) } else { Haptics.error() }
        }
    }

    /// Wi-Fi networks seen by the amplifier (GET /api/wifi, nmcli).
    var nets: [String] { live && !wifiNets.isEmpty ? wifiNets : (live ? [] : Self.nets) }

    func loadWifi() {
        wifiBusy = true
        Task { [weak self] in
            let d = await DeviceLink.shared.get("/api/wifi", timeout: 25)
            guard let self else { return }
            self.wifiBusy = false
            self.wifiNets = d.map(DevWifi.list) ?? []
            if self.wifiNets.isEmpty { self.netManual = true }
        }
    }

    /// POST /api/wifi {ssid, psk, hidden}. The amplifier is already on the network when it was found, so this mostly
    /// moves it to another network; the result shows in obErr.
    func joinWifi() {
        let name = netManual ? ssid.trimmingCharacters(in: .whitespaces) : (net < nets.count ? nets[net] : "")
        guard !name.isEmpty, let h = activeHost else { goOb(2); return }
        var body: [String: Any] = ["ssid": name, "hidden": netManual]
        if needPw && !pw.isEmpty { body["psk"] = pw }
        let data = DeviceLink.json(body)
        obErr = "Kobler til \(name) …"
        Task { [weak self] in
            let ok = await DeviceLink.shared.sendRaw("/api/wifi", data, on: h, timeout: 50) != nil
            guard let self else { return }
            if ok { Haptics.success(); self.goOb(2) } else { Haptics.error(); self.obErr = "Fikk ikke koblet til \(name). Sjekk passordet." }
        }
    }

    /// Starts the QR step. On a device the camera calls `qrFound()`; in the simulator it finishes after 2.2 s like the design.
    func startScan(simulated: Bool) {
        scan = true
        scanFound = false
        guard simulated else { return }
        run("scan") { [weak self] in
            try? await Task.sleep(for: .seconds(1.4))
            guard let self, self.scan else { return }
            Haptics.success()
            self.scanFound = true
            try? await Task.sleep(for: .seconds(0.8))
            guard self.scan else { return }
            self.scan = false
            self.goOb(1)
        }
    }

    func qrFound(_ payload: String = "") {
        guard scan else { return }
        // QR with an address (http://ip:8765, ip or name.local): connect to it
        let p = payload.trimmingCharacters(in: .whitespacesAndNewlines)
        if !p.isEmpty, p.range(of: #"^(https?://)?[A-Za-z0-9.\-\[\]:]+(/.*)?$"#, options: .regularExpression) != nil {
            scan = false
            pickFound(p, type: obType)
            return
        }
        Haptics.success()
        scanFound = true
        run("scan") { [weak self] in
            try? await Task.sleep(for: .seconds(0.6))
            guard let self, self.scan else { return }
            self.scan = false
            self.goOb(1)
        }
    }

    func testSide(_ k: String) {
        tested.insert(k)
        if live { devSend("/api/test", ["channel": k]); return }
        post(["type": "setupTest", "ch": k])
    }

    func restartSetup() {
        mode = .onboard; welcome = false; ob = 0; tested = []; pw = ""; obUpd = 0; scan = false
        post(["type": "setup", "step": 0])
    }

    // MARK: - System / rooms

    var actRoom: Room { sys.rooms.first { $0.id == sys.active } ?? sys.rooms.first ?? Room(id: "stue", name: room, type: "s1", hw: "", vol: vol) }
    var devRoom: Room { sys.rooms.first { $0.id == setDev } ?? sys.rooms.first ?? Room(id: "stue", name: "Stue", type: "s1", hw: "", vol: 0) }
    var groupName: String { sys.rooms.isEmpty ? room : sys.groupLabel(actRoom.id) }
    var actModel: String { SK.dev(actRoom.type).n }

    static func hwText(_ r: Room) -> String {
        let hw = r.type == "s1" && r.hw.contains("Raspberry Pi 4") ? "Pi Zero 2 W · TPA3116 2 × 50 W" : r.hw
        // keep "2 × 50 W" together like the design's non-breaking spaces
        return hw.replacingOccurrences(of: " ×", with: "\u{00a0}×").replacingOccurrences(of: "× ", with: "×\u{00a0}")
            .replacingOccurrences(of: " W", with: "\u{00a0}W").replacingOccurrences(of: " kHz", with: "\u{00a0}kHz")
    }

    func setSys(_ n: SystemState) {
        let old = sys
        sys = n
        if live { liveSys(old: old, new: n) }
    }

    // MARK: - Player

    var curRadio: Station {
        if let rTmp { return rTmp }
        return radio[max(0, min(station, radio.count - 1))]
    }
    var stIdx: Int { max(0, min(station, radio.count - 1)) }

    var libTrack: Track? {
        guard let lq, svc != nil, input == 0, li < lq.count else { return nil }
        return lq[li]
    }

    static let svcInfo: [String: (String, String)] = ["upnp": ("UPnP/DLNA", ""), "spotify": ("Spotify Connect", ""), "ytm": ("YouTube Music", ""), "nd": ("Navidrome", " · FLAC"), "plex": ("Plex", " · FLAC")]

    var np: NowPlaying {
        if let lt = libTrack, let svc { return NowPlaying(st: Self.svcInfo[svc]?.0 ?? "", t: lt.t, s: lt.artist + " · " + lt.album) }
        if let l = liveNP { return l }
        if let svc, let info = Self.svcInfo[svc], input == 0 { return NowPlaying(st: info.0, t: SK.tr[trk].0, s: SK.tr[trk].1 + info.1) }
        switch input {
        case 3:
            let n = SK.nowPlaying(curRadio.name)
            return NowPlaying(st: "Radio · " + curRadio.name, t: n.0, s: n.1)
        case 2: return NowPlaying(st: "AUX", t: names["nAux1"].flatMap { $0.isEmpty ? nil : $0 } ?? "AUX 1", s: "3,5 mm · analog")
        case 4: return NowPlaying(st: "USB-lyd", t: names["nUsb1"].flatMap { $0.isEmpty ? nil : $0 } ?? "PC", s: "USB-C «PC 1» · 48 kHz · 24 bit")
        default: return NowPlaying(st: input == 1 ? "Blåtann · iPhone" : "AirPlay · iPhone", t: SK.tr[trk].0, s: SK.tr[trk].1)
        }
    }

    struct PlayerArt { var key: String; var kicker: String; var big: String; var size: CGFloat; var live: Bool }

    var playerArt: PlayerArt {
        let n = np
        let big = input == 3 ? curRadio.name : n.t
        let kicker = input == 3 ? "RADIO · " + curRadio.genre.uppercased() : input == 2 ? "AUX" : input == 4 ? "USB-LYD" : n.s.uppercased()
        return PlayerArt(key: big, kicker: kicker, big: big, size: big.count > 14 ? 30 : 40, live: input == 3)
    }

    var duration: Int {
        if let d = libTrack?.dur, d > 0 { return d }
        if live { return actLyrionOnly ? activeLyrion?.duration ?? 0 : dev?.duration ?? 0 }
        return libTrack?.dur ?? (trk < SK.dur.count ? SK.dur[trk] : 240)
    }
    var position: Int { min(pos ?? (live ? 0 : 45), duration) }
    var hasProgress: Bool { input != 3 && input != 2 && input != 4 && (!live || duration > 0) }

    var srcName: String {
        let sn = ["upnp": "UPnP/DLNA", "spotify": "Spotify", "ytm": "YouTube Music", "nd": "Navidrome", "plex": "Plex"]
        if let svc, let n = sn[svc], input == 0 { return n }
        return ["AirPlay", "Blåtann", "AUX", "Radio", "USB-lyd"][input]
    }

    var quality: String {
        if input == 3 { return "DIREKTE" }
        if svc == "nd" { return "FLAC · 44,1 kHz" }
        if svc == "plex" { return "FLAC · Direkte avspilling" }
        if input == 1 { return "AAC" }
        if input == 2 { return "ANALOG" }
        if input == 4 { return "48 kHz · 24 bit" }
        if svc == "ytm" { return "AAC · 256 kbps" }
        if svc == "spotify" { return "OGG · 320 kbps" }
        return "ALAC · 44,1 kHz"
    }

    /// Inputs available on the active device type.
    var inputs: [(label: String, i: Int)] {
        let allowed = SK.dev(actRoom.type).inputs
        return ["AirPlay", "Blåtann", "AUX", "Radio", "USB"].enumerated().map { ($0.element, $0.offset) }.filter { allowed.contains($0.0) }
    }

    func pickInput(_ i: Int) {
        input = i; svc = nil
        if live { liveInput(i); return }
        if i < 2 { post(["type": "wl", "v": i == 1 ? "bt" : "air"]) } else { post(["type": "input", "i": i - 1]) }
    }

    func togglePlay() {
        Haptics.thump()
        playing.toggle()
        if live { hold("play", 3); liveTransport(playing ? "play" : "pause") } else { post(["type": "pause"]) }
    }

    func next() {
        if let lq, svc != nil { playLib(lq, (li + 1) % lq.count, keepOpen: true); return }
        if live { pos = 0; hold("pos", 1); liveTransport("next"); return }
        trk = (trk + 1) % 3; pos = 0
        post(["type": "next"])
    }

    func prev() {
        if let lq, svc != nil { playLib(lq, (li + lq.count - 1) % lq.count, keepOpen: true); return }
        if live { pos = 0; hold("pos", 1); liveTransport("previous"); return }
        trk = (trk + 2) % 3; pos = 0
    }

    func setVol(_ v: Int) {
        vol = v
        if live { liveVolume(v) } else { post(["type": "vol", "v": v]) }
    }

    func playLib(_ list: [Track], _ i: Int, keepOpen: Bool = false) {
        let tr = list[i]
        let cur = (hist[lib] ?? defaultHist(lib)).filter { $0.track.t != tr.t }
        hist[lib] = Array(([HistEntry(track: tr, when: "Nå")] + cur).prefix(20))
        svc = lib; input = 0; lq = list; li = i; pos = 0; playing = true
        if !keepOpen { full = true }
        if live { livePlayTrack(tr) } else { post(["type": "play", "svc": lib, "t": tr.t]) }
    }

    func addQueue(_ list: [Track]) {
        guard let cur = lq, !cur.isEmpty else { playLib(list, 0); return }
        lq = cur + list
    }

    func defaultHist(_ lib: String) -> [HistEntry] {
        guard demo else { return [] }
        return (SK.lib[lib]?.hist ?? []).map { HistEntry(track: SK.lt[$0.0], when: $0.1) }
    }

    func openLib(_ id: String) {
        sub = "lib"; lib = id; libTab = 0; libPl = nil; lq2 = ""; tab = 0
    }

    // MARK: - Radio

    var radioFull: Bool { radio.count >= SK.maxRadio }

    func setRL(_ l: [Station]) {
        radio = l
        station = min(station, l.count - 1)
        if live { pushPresets(l) }
        LogoStore.shared.fetch(l.map(\.name))
    }

    func playStation(_ i: Int, open: Bool = true) {
        rTmp = nil; station = i; input = 3
        if open { full = true }
        if live { livePlayFavourite(i) }
    }

    func playAny(_ st: Station) {
        rTmp = st; input = 3; full = true
        if live { livePlayStream(st) }
    }

    func favIndex(_ name: String) -> Int? { radio.firstIndex { $0.name == name } }

    func playRadio(_ st: Station) {
        if let f = favIndex(st.name) { playStation(f) } else { playAny(st) }
    }

    func toggleFav(_ st: Station) {
        if let f = favIndex(st.name) {
            if radio.count > 1 { Haptics.tick(); setRL(radio.enumerated().filter { $0.offset != f }.map(\.element)) } else { Haptics.warning() }
        } else if !radioFull {
            Haptics.success()
            setRL(radio + [st])
        } else {
            Haptics.warning()
        }
    }

    /// Name of the station currently playing ("" if radio is not the input).
    var curRadioName: String { input == 3 ? curRadio.name : "" }

    func setQ(_ v: String) {
        q = v; rRes = nil
        let t = v.trimmingCharacters(in: .whitespaces)
        guard t.count >= 3 else { rBusy = false; tasks["rq"]?.cancel(); return }
        rBusy = true
        run("rq") { [weak self] in
            try? await Task.sleep(for: .milliseconds(400))
            guard !Task.isCancelled else { return }
            let r = await RadioBrowser.search(t)
            guard let self, self.q.trimmingCharacters(in: .whitespaces) == t else { return }
            self.rRes = r; self.rBusy = false
        }
    }

    func goRadioSettings() {
        tab = 3; sub = ""; openK = ""
        setCat = cats.firstIndex { $0.id == "radio" } ?? -1
    }

    func testCustomStream() {
        let u = uUrl.trimmingCharacters(in: .whitespaces)
        uTest = "busy"
        Task { [weak self] in
            let ok = await RadioBrowser.testStream(u)
            if ok { Haptics.success() } else { Haptics.error() }
            self?.uTest = ok ? "ok" : "bad"
        }
    }

    // MARK: - Settings

    var cats: [SettingCategory] { SK.catsFor(devRoom.type) }

    func setS(_ k: String, _ v: Int) {
        sset[k] = v
        post(["type": "set", "k": k, "v": v])
    }

    func saveName(_ k: String, _ v: String) {
        names[k] = v
        post(["type": "set", "k": k, "v": v])
    }

    func runAction(_ id: String, safe: Bool) {
        if confirm != id && !safe { Haptics.warning(); confirm = id; return }
        confirm = ""
        switch id {
        case "ytmTest": ytmT = Date()
        case "ndTest": testNavidrome()
        case "plexTest": testPlex()
        case "btPair": btPairT = Date(); post(["type": "btPair", "room": devRoom.id])
        case "openRadio": tab = 0; sub = "radio"
        case "setup": restartSetup()
        default: post(["type": id])
        }
    }

    func testPlex() {
        let url = names["plexUrl"] ?? "", token = names["plexToken"] ?? ""
        guard !url.trimmingCharacters(in: .whitespaces).isEmpty else { plexT = "Skriv inn serveradressen"; plexOK = false; Haptics.warning(); return }
        guard !token.trimmingCharacters(in: .whitespaces).isEmpty else { plexT = "Lim inn Plex-token"; plexOK = false; Haptics.warning(); return }
        plexT = "busy"
        Task { [weak self] in
            let r = await PlexAPI.test(server: url, token: token)
            guard let self else { return }
            switch r {
            case let .ok(n): self.plexT = n == 1 ? "Tilkoblet · 1 musikkbibliotek" : "Tilkoblet · \(n) musikkbiblioteker"; self.plexOK = true; Haptics.success()
            case .unauthorized: self.plexT = "Feil token"; self.plexOK = false; Haptics.error()
            case .unreachable: self.plexT = "Fant ikke serveren"; self.plexOK = false; Haptics.error()
            case .badURL: self.plexT = "Ugyldig adresse"; self.plexOK = false; Haptics.error()
            }
        }
    }

    // MARK: - EQ

    var actSrc: String { headphones ? "hp" : ["air", "bt", "aux", "radio", "usb"][input] }
    var eqEditing: String { eqSrc ?? actSrc }
    var prof: EQProfile { eqP[eqEditing] ?? EQProfile(preset: 0, eq: [0, 0, 0, 0, 0], loud: true) }

    func setProf(_ change: (inout EQProfile) -> Void) {
        var p = prof
        change(&p)
        eqP[eqEditing] = p
        post(["type": "eqSync", "src": eqEditing])
    }

    // MARK: - Update (simulated GitHub release flow from the design)

    func checkUpdate() {
        liveCheckUpdate()
    }

    /// The design's simulated check (kept for reference; not used).
    private func checkUpdateDemo() {
        checking = true; job = nil; updMsg = ""
        run("check") { [weak self] in
            try? await Task.sleep(for: .seconds(1.1))
            guard let self else { return }
            let r = SK.findRelease(self.upd)
            self.upd.latest = r; self.upd.checkedAt = SK.now()
            self.checking = false
            Haptics.tick()
            self.updMsg = r == nil ? "Du har siste versjon (\(self.upd.version)). Sjekket \(SK.now())." : ""
        }
    }

    func backupNow() {
        if live { updMsg = "Backup fra appen er ikke støttet av forsterkeren ennå."; Haptics.warning(); return }
        upd.backups = Array(([Backup(id: "b\(Int(Date().timeIntervalSince1970 * 1000))", ver: upd.version, date: SK.now(), kind: "Manuell")] + upd.backups).prefix(6))
        Haptics.success()
        updMsg = "Backup av \(upd.version) er lagret."
        job = nil
    }

    func installUpdate() {
        guard let rel = upd.latest else { return }
        updMsg = ""
        if live {
            Haptics.warning()
            updMsg = "Installering fra appen er ikke koblet til forsterkeren ennå. Oppdater med Skjold Flasher eller fra forsterkerens meny (\(rel.tag))."
            return
        }
        let u = upd, fail = u.failNext, ver = rel.tag.replacingOccurrences(of: "v", with: "", options: .anchored)
        let steps = ["Tar backup av " + u.version, "Laster ned " + rel.tag + " fra github.com/" + u.repo, "Verifiserer SHA-256", "Installerer", fail ? "Starter tjenester …" : "Starter på nytt"]
        runJob(steps: steps, inc: 4, failAt: fail ? 4 : nil) { [weak self] failed in
            guard let self else { return }
            var n = u
            if failed {
                n.failNext = false
                n.log = Array(([UpdateLog(date: SK.now(), text: "Oppdatering til \(ver) feilet ved oppstart. Gjenopprettet \(u.version) automatisk.", bad: true)] + u.log).prefix(8))
            } else {
                n.version = ver; n.latest = nil
                n.backups = Array(([Backup(id: "b\(Int(Date().timeIntervalSince1970 * 1000))", ver: u.version, date: SK.now(), kind: "Automatisk før oppdatering")] + u.backups).prefix(6))
                n.log = Array(([UpdateLog(date: SK.now(), text: "Oppdatert \(u.version) → \(ver)")] + u.log).prefix(8))
            }
            if failed { Haptics.error() } else { Haptics.success() }
            self.upd = n
            self.job = Job(done: true, failed: failed, upd: n)
            self.post(["type": "updSync", "version": n.version])
        }
    }

    func restore(_ b: Backup) {
        if restoreConf != b.id { Haptics.warning(); restoreConf = b.id; return }
        if live { restoreConf = ""; updMsg = "Gjenoppretting fra appen er ikke støttet av forsterkeren ennå."; return }
        restoreConf = ""; updMsg = ""
        let u = upd
        runJob(steps: ["Stopper tjenester", "Gjenoppretter " + b.ver, "Starter på nytt"], inc: 6, failAt: nil) { [weak self] _ in
            guard let self else { return }
            var n = u
            n.version = b.ver; n.latest = nil
            n.log = Array(([UpdateLog(date: SK.now(), text: "Gjenopprettet backup \(b.ver) (\(b.date))")] + u.log).prefix(8))
            Haptics.success()
            self.upd = n
            self.job = nil
            self.updMsg = "Backup \(b.ver) er gjenopprettet."
            self.post(["type": "updSync", "version": n.version])
        }
    }

    private func runJob(steps: [String], inc: Int, failAt: Int?, done: @escaping (Bool) -> Void) {
        run("job") { [weak self] in
            var i = 0, p = 0
            while !Task.isCancelled {
                try? await Task.sleep(for: .milliseconds(70))
                guard let self else { return }
                p += inc
                if p >= 100 { p = 0; i += 1 }
                if let f = failAt, i == f, p > 40 { done(true); return }
                if i >= steps.count { done(false); return }
                self.job = Job(step: steps[i], pct: Int((Double(i) + Double(p) / 100) / Double(steps.count) * 100 + 0.5))
            }
        }
    }
}

// MARK: - Persistence

nonisolated enum Store {
    static func save<T: Encodable>(_ v: T, _ key: String) {
        if let d = try? JSONEncoder().encode(v) { UserDefaults.standard.set(d, forKey: key) }
    }

    static func load<T: Decodable>(_ key: String) -> T? {
        guard let d = UserDefaults.standard.data(forKey: key) else { return nil }
        return try? JSONDecoder().decode(T.self, from: d)
    }
}
