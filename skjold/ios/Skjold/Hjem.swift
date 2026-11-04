import SwiftUI
import WebKit

// Skjold-hjem (docs/SKJOLD_HJEM.md): steder i skyen (Cloudflare Worker bak Cloudflare Access), stedsvelger,
// relé via skyen når en enhet ikke svarer på LAN, og innlogging.
//
// Innlogging: Access setter informasjonskapselen CF_Authorization på sky-domenet. Appen åpner skyen i en WKWebView
// (HjemLoginView), leser informasjonskapselen derfra og legger den i HTTPCookieStorage.shared – da sender
// URLSession.shared den på alle kall (også SSE via relé). ASWebAuthenticationSession deler ikke informasjonskapsler
// med appen, så den kan bare brukes hvis Workeren får et endepunkt som sender tokenet tilbake til en app-URL.
// Begrensning: Google-innlogging tillates ikke i innebygde nettlesere; bruk engangskode (e-post) eller en annen IdP i Access.

nonisolated struct HjemSted: Sendable, Hashable, Identifiable {
    var id: String
    var navn: String
    var rolle: String
    var enheter: Int
    var online: Int

    init?(_ o: [String: Any]) {
        guard let id = o["id"] as? String else { return nil }
        self.id = id
        navn = (o["navn"] as? String) ?? id
        rolle = (o["rolle"] as? String) ?? "medlem"
        enheter = (o["enheter"] as? NSNumber)?.intValue ?? (o["enheter"] as? [Any])?.count ?? 0
        if let b = o["online"] as? Bool { online = b ? 1 : 0 } else { online = (o["online"] as? NSNumber)?.intValue ?? 0 }
    }
}

nonisolated struct HjemEnhet: Sendable, Hashable, Identifiable {
    var id: String
    var navn: String
    var produkt: String
    var rom: String
    var online: Bool
    var aktivHoved: Bool
    var hoved: Bool
    var reserveNr: Int?
    /// LAN-adresse som skyen kjenner ("ip:port"), om noen.
    var lan: String?

    init?(_ o: [String: Any]) {
        guard let id = o["id"] as? String else { return nil }
        self.id = id
        navn = (o["navn"] as? String) ?? id
        produkt = (o["produkt"] as? String) ?? "s1"
        rom = (o["rom"] as? String) ?? ""
        online = (o["online"] as? Bool) ?? false
        aktivHoved = (o["aktivHoved"] as? Bool) ?? false
        hoved = (o["hoved"] as? Bool) ?? false
        let r = (o["reserveNr"] as? NSNumber)?.intValue ?? 0
        reserveNr = r > 0 ? r : nil
        if let s = o["lan"] as? String, !s.isEmpty {
            lan = s
        } else if let l = o["lan"] as? [String: Any], let ip = l["ip"] as? String {
            lan = "\(ip):\((l["port"] as? NSNumber)?.intValue ?? 8765)"
        } else {
            lan = nil
        }
    }

    var merke: String { hoved ? "Hoved" : reserveNr.map { "Reserve \($0)" } ?? "" }
}

nonisolated enum HjemSvar: Sendable {
    case ok(Data)
    case login
    case feil(String)
}

nonisolated enum HjemAPI {
    static let standard = "https://skjold-styring.smarthjemexperten.no"
    static let cookieName = "CF_Authorization"
    private static let urlKey = "skjold-sky-url", tokenKey = "skjold-sky-token"

    static var base: String {
        let s = UserDefaults.standard.string(forKey: urlKey) ?? ""
        return s.isEmpty ? standard : s
    }
    static func setBase(_ raw: String) {
        var s = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        while s.hasSuffix("/") { s.removeLast() }
        if !s.isEmpty && !s.lowercased().hasPrefix("http") { s = "https://" + s }
        UserDefaults.standard.set(s == standard ? "" : s, forKey: urlKey)
    }
    static var host: String { URL(string: base)?.host ?? "" }

    static func enc(_ s: String) -> String {
        s.addingPercentEncoding(withAllowedCharacters: CharacterSet.urlPathAllowed.subtracting(CharacterSet(charactersIn: "/"))) ?? s
    }
    /// Relé-base: base + "/api/status" osv. går til enhetens eget API via skyen.
    static func relay(_ sted: String, _ id: String) -> String { base + "/api/hjem/steder/\(enc(sted))/enheter/\(enc(id))" }
    static func isRelay(_ h: String) -> Bool { h.contains("/api/hjem/steder/") }

    /// Access sendte oss til innloggingen (omdirigering til *.cloudflareaccess.com eller /cdn-cgi/access).
    static func accessBlocked(_ r: HTTPURLResponse) -> Bool {
        let h = r.url?.host ?? "", p = r.url?.path ?? ""
        return h.hasSuffix("cloudflareaccess.com") || p.hasPrefix("/cdn-cgi/access")
    }

    // MARK: Informasjonskapsel

    static var loggedIn: Bool { !(UserDefaults.standard.string(forKey: tokenKey) ?? "").isEmpty }

    static func store(_ c: HTTPCookie) {
        HTTPCookieStorage.shared.setCookie(c)
        UserDefaults.standard.set(c.value, forKey: tokenKey)
    }

    /// Legg lagret token inn igjen (HTTPCookieStorage kan ha mistet det ved oppstart/utløp av økten).
    static func restoreCookie() {
        guard let v = UserDefaults.standard.string(forKey: tokenKey), !v.isEmpty, !host.isEmpty else { return }
        let has = HTTPCookieStorage.shared.cookies?.contains { $0.name == cookieName && matches($0.domain) } ?? false
        guard !has else { return }
        let props: [HTTPCookiePropertyKey: Any] = [.domain: host, .path: "/", .name: cookieName, .value: v, .secure: "TRUE",
                                                   .expires: Date().addingTimeInterval(24 * 3600)]
        if let c = HTTPCookie(properties: props) { HTTPCookieStorage.shared.setCookie(c) }
    }

    static func logout() {
        UserDefaults.standard.removeObject(forKey: tokenKey)
        for c in HTTPCookieStorage.shared.cookies ?? [] where c.name == cookieName { HTTPCookieStorage.shared.deleteCookie(c) }
    }

    static func matches(_ domain: String) -> Bool {
        var d = domain
        while d.hasPrefix(".") { d.removeFirst() }
        let h = host
        return !d.isEmpty && (h == d || h.hasSuffix("." + d))
    }

    // MARK: Kall

    static func call(_ method: String, _ path: String, _ body: [String: Any]? = nil) async -> HjemSvar {
        guard let url = URL(string: base + path) else { return .feil("Ugyldig sky-adresse") }
        var req = URLRequest(url: url, timeoutInterval: 10)
        req.httpMethod = method
        req.cachePolicy = .reloadIgnoringLocalCacheData
        req.setValue("application/json", forHTTPHeaderField: "Accept")
        if let body, let d = try? JSONSerialization.data(withJSONObject: body) {
            req.httpBody = d
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        guard let (d, r) = try? await URLSession.shared.data(for: req), let http = r as? HTTPURLResponse else {
            return .feil("Får ikke kontakt med Skjold-hjem")
        }
        if http.statusCode == 401 || accessBlocked(http) { return .login }
        let json = (http.value(forHTTPHeaderField: "Content-Type") ?? "").contains("json")
        if !(200..<300).contains(http.statusCode) {
            if http.statusCode == 403 && !json { return .login }
            let o = (try? JSONSerialization.jsonObject(with: d)) as? [String: Any]
            let msg = (o?["error"] as? String) ?? (o?["feil"] as? String) ?? "HTTP \(http.statusCode)"
            return .feil(http.statusCode == 403 ? "Bare eieren kan gjøre det" : msg)
        }
        return json ? .ok(d) : .login   // HTML = Access-innloggingssiden
    }

    static func list(_ d: Data) -> [[String: Any]] { ((try? JSONSerialization.jsonObject(with: d)) as? [[String: Any]]) ?? [] }
    static func object(_ d: Data) -> [String: Any] { ((try? JSONSerialization.jsonObject(with: d)) as? [String: Any]) ?? [:] }
}

// MARK: - Modell

extension AppModel {
    /// Enhetene appen viser som rom: valgt steds enheter, ellers de kjente på LAN.
    var devices: [KnownDevice] {
        guard !stedId.isEmpty else { return known }
        return stedEnheter.map { e in
            KnownDevice(host: stedHosts[e.id] ?? HjemAPI.relay(stedId, e.id), id: e.id, name: e.navn, product: e.produkt)
        }
    }
    var stedNavn: String { steder.first { $0.id == stedId }?.navn ?? (stedId.isEmpty ? "Hjemme" : "Sted") }
    /// Stedsvelgeren vises som tittel når Skjold-hjem er i bruk.
    var visSted: Bool { !stedId.isEmpty || !steder.isEmpty }
    func hjemEnhet(_ id: String) -> HjemEnhet? { stedId.isEmpty ? nil : stedEnheter.first { $0.id == id } }

    func openStederSettings() {
        tab = 3
        if let i = cats.firstIndex(where: { $0.id == "steder" }) { setCat = i; openK = "" }
    }

    private func hjemFail(_ s: HjemSvar) {
        switch s {
        case .login: hjemState = "login"
        case .feil(let e): hjemState = e
        case .ok: break
        }
    }

    func startHjem() async {
        await loadSteder()
        guard !stedId.isEmpty else { return }
        await loadStedEnheter(probe: true)
        // Adressene er nettopp sjekket: bytt hvis den lagrede (relé/gammel LAN) ikke lenger er den beste
        if activeHost == nil || !devices.contains(where: { $0.host == activeHost }) {
            if let e = pickDefault() { await velgEnhet(e) }
        }
        run("hjem") { [weak self] in
            while !Task.isCancelled {
                try? await Task.sleep(for: .seconds(15))
                guard let self, !self.stedId.isEmpty, self.hjemState == "ok" else { continue }
                await self.loadStedEnheter(probe: false)
            }
        }
    }

    func loadSteder() async {
        if hjemState != "ok" { hjemState = "laster" }
        let s = await HjemAPI.call("GET", "/api/hjem/steder")
        guard case .ok(let d) = s else { hjemFail(s); return }
        steder = HjemAPI.list(d).compactMap(HjemSted.init)
        hjemState = "ok"
    }

    /// Hent enhetene i valgt sted. `probe`: finn LAN-adresser som svarer innen 1,5 s (ellers relé).
    func loadStedEnheter(probe: Bool) async {
        let id = stedId
        guard !id.isEmpty else { stedEnheter = []; return }
        let s = await HjemAPI.call("GET", "/api/hjem/steder/\(HjemAPI.enc(id))/enheter")
        guard case .ok(let d) = s else { hjemFail(s); return }
        let list = HjemAPI.list(d).compactMap(HjemEnhet.init)
        guard stedId == id else { return }
        if probe {
            var hosts: [String: String] = [:]
            await withTaskGroup(of: (String, String?).self) { g in
                for e in list {
                    guard let lan = e.lan else { continue }
                    let h = DeviceLink.normHost(lan)
                    g.addTask {
                        let st = await DeviceLink.status(at: h, timeout: 1.5)
                        return (e.id, st != nil && (st?.id.isEmpty ?? true || st?.id == e.id) ? h : nil)
                    }
                }
                for await (eid, h) in g { if let h { hosts[eid] = h } }
            }
            if stedId == id { stedHosts = hosts }
        }
        stedEnheter = list
        rebuildRooms()
    }

    private func pickDefault() -> HjemEnhet? {
        let last = UserDefaults.standard.string(forKey: "skjold-sted-enhet:" + stedId)
        return stedEnheter.first { $0.id == last } ?? stedEnheter.first { $0.aktivHoved } ?? stedEnheter.first { $0.online } ?? stedEnheter.first
    }

    /// Bytt sted ("" = Dette nettverket). Valget huskes.
    func selectSted(_ id: String) async {
        guard id != stedId else { return }
        if stedId.isEmpty, let h = activeHost, !HjemAPI.isRelay(h) { UserDefaults.standard.set(h, forKey: "skjold-lan-host") }
        stedId = id
        stedEnheter = []; stedHosts = [:]
        if id.isEmpty {
            let h = UserDefaults.standard.string(forKey: "skjold-lan-host") ?? known.first?.host
            switchHost(h)
            return
        }
        await loadStedEnheter(probe: true)
        if let e = pickDefault() { await velgEnhet(e) } else { switchHost(nil) }
    }

    /// Styr en enhet i valgt sted: LAN hvis den svarte, ellers relé.
    func velgEnhet(_ e: HjemEnhet) async {
        UserDefaults.standard.set(e.id, forKey: "skjold-sted-enhet:" + stedId)
        if stedHosts[e.id] == nil, let lan = e.lan {
            let h = DeviceLink.normHost(lan)
            if await DeviceLink.status(at: h, timeout: 1.5) != nil { stedHosts[e.id] = h }
        }
        switchHost(stedHosts[e.id] ?? HjemAPI.relay(stedId, e.id))
        if let r = sys.rooms.first(where: { $0.host == activeHost }) { sys.active = r.id; setDev = r.id }
    }

    private func switchHost(_ h: String?) {
        activeHost = h
        dev = nil
        devStats = [:]
        link = h == nil ? .none : .connecting
        libStream = nil
        rebuildRooms()
        if h != nil {
            startEvents()
            if let h { Task { [weak self] in await self?.loadSettings(h) } }
            Task { [weak self] in await self?.loadPresets() }
        }
    }

    func hjemLoggedIn(_ c: HTTPCookie) {
        HjemAPI.store(c)
        hjemLogin = false
        Task { [weak self] in await self?.startHjem() }
    }
}

// MARK: - Visninger

/// «Hoved» / «Reserve n» / «aktiv» og online-prikk.
struct HjemBadges: View {
    let e: HjemEnhet
    var body: some View {
        HStack(spacing: 4) {
            Circle().fill(e.online ? Color.ok : Color.danger).frame(width: 6, height: 6)
            if !e.merke.isEmpty { pill(e.merke, e.hoved) }
            if e.aktivHoved { pill("aktiv", true) }
            if !e.online { Text("offline").sora(10.5, .regular, .muted) }
        }
    }
    private func pill(_ t: String, _ on: Bool) -> some View {
        Text(t).mono(9.5, on ? .accent2 : .ink2, em: 0.04)
            .padding(.horizontal, 6).frame(height: 18)
            .background(Capsule().fill(on ? Color.selBg : .clear))
            .skCapsuleBorder(on ? .selLine : .line2)
    }
}

/// Tittelrad «Hytta ▾» som åpner stedsmenyen.
struct StedPicker: View {
    @Environment(AppModel.self) private var m
    var size: CGFloat = 28

    var body: some View {
        Menu {
            Button { Task { await m.selectSted("") } } label: {
                Label("Dette nettverket", systemImage: m.stedId.isEmpty ? "checkmark" : "wifi")
            }
            ForEach(m.steder) { s in
                Button { Task { await m.selectSted(s.id) } } label: {
                    Label("\(s.navn) · \(s.online)/\(s.enheter) online", systemImage: s.id == m.stedId ? "checkmark" : "house")
                }
            }
            Divider()
            if m.hjemState == "login" {
                Button { m.hjemLogin = true } label: { Label("Logg inn på Skjold-hjem", systemImage: "person.crop.circle") }
            }
            Button { m.openStederSettings() } label: { Label("Administrer steder …", systemImage: "gearshape") }
        } label: {
            HStack(spacing: 6) {
                Text(m.stedNavn).sora(size, .semibold).lineLimit(1)
                SKIcon(d: "M6 9l6 6 6-6", size: size * 0.55, stroke: 2.2, color: .ink2)
            }
            .contentShape(Rectangle())
        }
        .simultaneousGesture(TapGesture().onEnded { Haptics.tap(); Task { await m.loadSteder() } })
        .task { if m.steder.isEmpty { await m.loadSteder() } }
        .accessibilityLabel("Velg sted, nå \(m.stedNavn)")
    }
}

/// Innstillinger → Steder.
struct StederSettingsView: View {
    @Environment(AppModel.self) private var m
    @State private var url = HjemAPI.base
    @State private var nytt = ""
    @State private var open = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Steder samler Skjold-enheter på flere adresser (Hjem, Hytta …). Når en enhet ikke svarer på nettet du er på, går trafikken via skyen.")
                .sora(12, .regular, .ink2).fixedSize(horizontal: false, vertical: true)
            SKMonoLabel(text: "SKY-ADRESSE")
            SKField(placeholder: HjemAPI.standard, text: $url, height: 44, size: 14, plainInput: true)
            HStack(spacing: 8) {
                SKPill(title: "Lagre og hent", height: 34) { HjemAPI.setBase(url); Task { await m.loadSteder() } }
                if m.hjemState == "login" || !HjemAPI.loggedIn {
                    SKPill(title: "Logg inn på Skjold-hjem", primary: true, height: 34) { m.hjemLogin = true }
                } else {
                    SKPill(title: "Logg ut", height: 34) { HjemAPI.logout(); m.hjemState = "login"; m.steder = [] }
                }
            }
            if m.hjemState == "laster" { Text("Henter steder …").sora(12, .regular, .muted) }
            else if !["", "ok", "login", "laster"].contains(m.hjemState) { Text(m.hjemState).sora(12, .regular, .danger) }
        }
        .padding(14)
        .skBox(.card, .line)
        .task { await m.loadSteder(); if open.isEmpty { open = m.stedId } }

        ForEach(m.steder) { s in StedCard(s: s, open: open == s.id) { open = open == s.id ? "" : s.id } }

        if m.hjemState == "ok" {
            VStack(alignment: .leading, spacing: 10) {
                Text("Nytt sted").sora(14, .semibold)
                HStack(spacing: 8) {
                    SKField(placeholder: "For eksempel Hytta", text: $nytt, height: 44, size: 14)
                    SKPill(title: "Lag", primary: true, height: 44) {
                        let n = nytt.trimmingCharacters(in: .whitespaces)
                        guard !n.isEmpty else { return }
                        Task {
                            let r = await HjemAPI.call("POST", "/api/hjem/steder", ["navn": n])
                            if case .ok(let d) = r { nytt = ""; open = (HjemAPI.object(d)["id"] as? String) ?? ""; Haptics.success() } else { Haptics.error() }
                            await m.loadSteder()
                        }
                    }
                }
            }
            .padding(14)
            .skBox(.card, .line)
        }
    }
}

private struct StedCard: View {
    @Environment(AppModel.self) private var m
    let s: HjemSted
    let open: Bool
    let toggle: () -> Void
    @State private var navn = ""
    @State private var list: [HjemEnhet] = []
    @State private var kode: String? = nil
    @State private var msg = ""
    @State private var confirm = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Button(action: toggle) {
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(s.navn + (s.id == m.stedId ? " · valgt" : "")).sora(15, .semibold)
                        Text("\(s.enheter) enheter · \(s.rolle)").mono(10.5)
                    }
                    Spacer()
                    SKIcon(d: open ? "M6 15l6-6 6 6" : "M6 9l6 6 6-6", size: 14, stroke: 2.2, color: .muted)
                }
                .contentShape(Rectangle())
            }
            .plain()
            if open { detail }
        }
        .padding(14)
        .skBox(.card, .line)
        .task(id: open) { if open { navn = s.navn; await load() } }
    }

    private var reserve: [String] {
        list.filter { $0.reserveNr != nil }.sorted { ($0.reserveNr ?? 0) < ($1.reserveNr ?? 0) }.map(\.id)
    }

    @ViewBuilder private var detail: some View {
        HStack(spacing: 8) {
            SKField(placeholder: "Navn", text: $navn, height: 40, size: 14)
            SKPill(title: "Gi nytt navn", height: 40) { run("PATCH", "", ["navn": navn.trimmingCharacters(in: .whitespaces)]) }
        }
        SKMonoLabel(text: "ENHETER")
        if list.isEmpty { Text("Ingen enheter ennå. Trykk «Legg til enhet».").sora(12, .regular, .muted) }
        VStack(spacing: 0) {
            ForEach(Array(list.enumerated()), id: \.element.id) { i, e in
                let r = reserve
                VStack(alignment: .leading, spacing: 8) {
                    VStack(alignment: .leading, spacing: 3) {
                        Text(e.navn + (e.rom.isEmpty ? "" : " · " + e.rom)).sora(14)
                        HjemBadges(e: e)
                    }
                    FlowLayout(spacing: 6) {
                        if !e.hoved {
                            SKPill(title: "Gjør til hoved", height: 30, hPad: 10, border: .selLine, fg: .accent2) {
                                run("PATCH", "", ["hoved": e.id, "reserve": r.filter { $0 != e.id }])
                            }
                            if !r.contains(e.id) { SKPill(title: "Legg i reserve", height: 30, hPad: 10) { run("PATCH", "", ["reserve": r + [e.id]]) } }
                        }
                        if let k = r.firstIndex(of: e.id) {
                            SKPill(title: "↑", height: 30, hPad: 12) { if k > 0 { var n = r; n.swapAt(k, k - 1); run("PATCH", "", ["reserve": n]) } }
                            SKPill(title: "↓", height: 30, hPad: 12) { if k < r.count - 1 { var n = r; n.swapAt(k, k + 1); run("PATCH", "", ["reserve": n]) } }
                            SKPill(title: "Ut av reserve", height: 30, hPad: 10) { run("PATCH", "", ["reserve": r.filter { $0 != e.id }]) }
                        }
                        SKPill(title: confirm == e.id ? "Sikker? Fjern" : "Fjern", height: 30, hPad: 10, border: .danger.opacity(0.5), fg: .danger) {
                            if confirm == e.id { confirm = ""; run("DELETE", "/enheter/\(HjemAPI.enc(e.id))", nil) } else { confirm = e.id }
                        }
                    }
                }
                .padding(.vertical, 10).padding(.horizontal, 12)
                .frame(maxWidth: .infinity, alignment: .leading)
                .topLine(i > 0 ? .line : .clear)
            }
        }
        .skBox(.bg, .line, radius: 12)

        if let kode {
            VStack(spacing: 8) {
                Text(kode).font(.plexMono(40, .medium)).tracking(40 * 0.18).foregroundStyle(Color.accent2)
                    .textSelection(.enabled)
                Text("Tast inn koden på enheten under Innstillinger → Skjold-hjem").sora(13).multilineTextAlignment(.center)
                    .fixedSize(horizontal: false, vertical: true)
                Text("Gyldig i 10 minutter").sora(11, .regular, .muted)
                HStack(spacing: 8) {
                    SKPill(title: "Oppdater liste", height: 32) { Task { await load() } }
                    SKPill(title: "Ferdig", height: 32) { self.kode = nil }
                }
            }
            .frame(maxWidth: .infinity)
            .padding(16)
            .skBox(.selBg, .selLine, radius: 12)
        } else {
            FlowLayout(spacing: 8) {
                SKPill(title: "Legg til enhet", primary: true, height: 40) {
                    Task {
                        let r = await HjemAPI.call("POST", "/api/hjem/steder/\(HjemAPI.enc(s.id))/kobling", [:])
                        switch r {
                        case .ok(let d): kode = HjemAPI.object(d)["kode"] as? String; Haptics.success()
                        case .login: m.hjemLogin = true
                        case .feil(let e): msg = e; Haptics.error()
                        }
                    }
                }
                if s.id != m.stedId { SKPill(title: "Bruk dette stedet", height: 40) { Task { await m.selectSted(s.id) } } }
                if s.rolle == "eier" {
                    SKPill(title: confirm == "sted" ? "Sikker? Slett" : "Slett sted", height: 40, border: .danger.opacity(0.5), fg: .danger) {
                        guard confirm == "sted" else { confirm = "sted"; return }
                        confirm = ""
                        Task {
                            let r = await HjemAPI.call("DELETE", "/api/hjem/steder/\(HjemAPI.enc(s.id))")
                            if case .feil(let e) = r { msg = e; Haptics.error(); return }
                            if s.id == m.stedId { await m.selectSted("") }
                            await m.loadSteder()
                        }
                    }
                }
            }
        }
        if !msg.isEmpty { Text(msg).sora(12, .regular, .danger) }
    }

    private func load() async {
        let r = await HjemAPI.call("GET", "/api/hjem/steder/\(HjemAPI.enc(s.id))/enheter")
        if case .ok(let d) = r { list = HjemAPI.list(d).compactMap(HjemEnhet.init); msg = "" }
        else if case .feil(let e) = r { msg = e }
    }

    private func run(_ method: String, _ sub: String, _ body: [String: Any]?) {
        Haptics.tap()
        Task {
            let r = await HjemAPI.call(method, "/api/hjem/steder/\(HjemAPI.enc(s.id))" + sub, body)
            switch r {
            case .ok: msg = ""
            case .login: m.hjemLogin = true
            case .feil(let e): msg = e; Haptics.error()
            }
            await load()
            await m.loadSteder()
            if s.id == m.stedId { await m.loadStedEnheter(probe: false) }
        }
    }
}

/// Innstillinger → Skjold-hjem på enheten selv (GET/POST /api/sky via LAN eller relé).
struct SkyDeviceView: View {
    @Environment(AppModel.self) private var m
    @State private var st: [String: Any] = [:]
    @State private var loaded = false
    @State private var kode = ""
    @State private var err = ""
    @State private var confirm = false

    var body: some View {
        let koblet = (st["koblet"] as? Bool) ?? false
        let tilkoblet = (st["tilkoblet"] as? Bool) ?? false
        let navn = (st["stedNavn"] as? String) ?? (st["sted"] as? String) ?? "Skjold-hjem"
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text(koblet ? "Koblet til \(navn)" : "Ikke koblet til Skjold-hjem").sora(15, .semibold)
                Spacer()
                if loaded { Text(tilkoblet ? "● Tilkoblet skyen" : koblet ? "○ Ikke tilkoblet nå" : "").sora(12, .regular, tilkoblet ? .ok : .muted) }
            }
            if koblet {
                let erHoved = (st["erHoved"] as? Bool) ?? false
                let aktiv = (st["aktivHoved"] as? String) ?? ""
                Text((erHoved ? "Denne enheten er stedets hovedenhet" : "Denne enheten er med i stedet") + (aktiv.isEmpty ? "." : " · kontaktpunkt nå: \(aktiv)."))
                    .sora(12, .regular, .ink2).fixedSize(horizontal: false, vertical: true)
                SKPill(title: confirm ? "Sikker? Koble fra" : "Koble fra", height: 36, border: .danger.opacity(0.5), fg: .danger) {
                    guard confirm else { confirm = true; return }
                    confirm = false
                    send(["koble_fra": true])
                }
            } else {
                Text("Lag en kode under Innstillinger → Steder → «Legg til enhet», og tast den inn her.")
                    .sora(12, .regular, .ink2).fixedSize(horizontal: false, vertical: true)
                HStack(spacing: 8) {
                    SKField(placeholder: "K7Q2XM", text: $kode, height: 44, size: 18, mono: true, plainInput: true, maxLength: 6)
                        .textInputAutocapitalization(.characters)
                    SKPill(title: "Koble til", primary: true, height: 44) {
                        let k = kode.uppercased().filter { $0.isLetter || $0.isNumber }
                        guard k.count == 6 else { err = "Koden har seks tegn"; return }
                        send(["kode": k])
                    }
                }
            }
            if !err.isEmpty { Text(err).sora(12, .regular, .danger) }
        }
        .padding(14)
        .skBox(.card, .line)
        .task {
            while !Task.isCancelled {
                await load()
                try? await Task.sleep(for: .seconds(5))
            }
        }
    }

    private func load() async {
        guard let h = m.settingsHost else { err = "Ingen enhet valgt"; return }
        guard let d = await DeviceLink.shared.get("/api/sky", on: h) else {
            err = "Enheten svarer ikke på /api/sky – oppdater programvaren på enheten."
            return
        }
        st = HjemAPI.object(d); loaded = true; err = ""
    }

    private func send(_ body: [String: Any]) {
        guard let h = m.settingsHost else { return }
        Haptics.tap()
        Task {
            if let d = await DeviceLink.shared.send("/api/sky", body, on: h, timeout: 15) {
                st = HjemAPI.object(d); kode = ""; err = ""; Haptics.success()
            } else {
                err = "Enheten godtok ikke forespørselen. Sjekk koden (gyldig i 10 minutter)."; Haptics.error()
            }
        }
    }
}

/// Innlogging i Cloudflare Access: skyen åpnes i en WKWebView; når CF_Authorization finnes for sky-domenet,
/// kopieres den til appens HTTPCookieStorage.
struct HjemLoginView: View {
    @Environment(AppModel.self) private var m

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Text("Logg inn på Skjold-hjem").sora(15, .semibold)
                Spacer()
                SKLinkButton(title: "Avbryt") { m.hjemLogin = false }
            }
            .padding(16)
            HjemWeb { c in m.hjemLoggedIn(c) }
        }
        .background(Color.bg.ignoresSafeArea())
        .preferredColorScheme(.dark)
    }
}

private struct HjemWeb: UIViewRepresentable {
    let done: (HTTPCookie) -> Void

    func makeCoordinator() -> Coord { Coord(done: done) }

    func makeUIView(context: Context) -> WKWebView {
        let w = WKWebView(frame: .zero, configuration: WKWebViewConfiguration())
        w.navigationDelegate = context.coordinator
        w.isOpaque = false
        if let u = URL(string: HjemAPI.base + "/api/hjem/steder") { w.load(URLRequest(url: u)) }
        return w
    }

    func updateUIView(_ uiView: WKWebView, context: Context) {}

    final class Coord: NSObject, WKNavigationDelegate {
        let done: (HTTPCookie) -> Void
        var fired = false
        init(done: @escaping (HTTPCookie) -> Void) { self.done = done }

        func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
            let store = webView.configuration.websiteDataStore.httpCookieStore
            Task { @MainActor in
                let cookies = await store.allCookies()
                guard !self.fired, let c = cookies.first(where: { $0.name == HjemAPI.cookieName && HjemAPI.matches($0.domain) }) else { return }
                self.fired = true
                self.done(c)
            }
        }
    }
}
