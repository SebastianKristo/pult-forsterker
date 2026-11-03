import Foundation

// Swift version of skjold_settings.js. Same ids and keys as the amplifier menu and the web UI.

// MARK: - Settings schema

enum NumFormat: String, Codable, Sendable {
    case dB, bal

    func format(_ v: Int) -> String {
        switch self {
        case .dB: return (v > 0 ? "+" : v < 0 ? "−" : "") + "\(abs(v)) dB"
        case .bal: return v == 0 ? "Midt" : (v < 0 ? "V " : "H ") + "\(abs(v))"
        }
    }
}

enum SettingKind: Codable, Sendable, Equatable {
    case eq
    case num(min: Int, max: Int, format: NumFormat)
    case opt([String])
    case bool
    case str(placeholder: String, long: Bool, max: Int, secret: Bool)
    case info(value: String?, key: String?)
    case act(id: String, label: String, safe: Bool)
    case steps([String])
    case update
    case clocks
}

struct SettingItem: Codable, Sendable, Identifiable {
    var kind: SettingKind
    var k: String            // setting key (or action id)
    var n: String            // label
    var hint: String? = nil
    var dev: [String]? = nil // device types this applies to (nil = all)

    var id: String { k + n }

    static func num(_ k: String, _ n: String, _ mn: Int, _ mx: Int, _ f: NumFormat, _ hint: String? = nil, dev: [String]? = nil) -> SettingItem {
        SettingItem(kind: .num(min: mn, max: mx, format: f), k: k, n: n, hint: hint, dev: dev)
    }
    static func opt(_ k: String, _ n: String, _ list: [String], _ hint: String? = nil, dev: [String]? = nil) -> SettingItem {
        SettingItem(kind: .opt(list), k: k, n: n, hint: hint, dev: dev)
    }
    static func bool(_ k: String, _ n: String, _ hint: String? = nil, dev: [String]? = nil) -> SettingItem {
        SettingItem(kind: .bool, k: k, n: n, hint: hint, dev: dev)
    }
    static func str(_ k: String, _ n: String, _ ph: String, _ hint: String? = nil, long: Bool = false, max: Int = 14, secret: Bool = false, dev: [String]? = nil) -> SettingItem {
        SettingItem(kind: .str(placeholder: ph, long: long, max: max, secret: secret), k: k, n: n, hint: hint, dev: dev)
    }
    static func info(_ n: String, val: String? = nil, key: String? = nil, _ hint: String? = nil) -> SettingItem {
        SettingItem(kind: .info(value: val, key: key), k: key ?? n, n: n, hint: hint)
    }
    static func act(_ n: String, id: String, label: String, safe: Bool = false, _ hint: String? = nil, dev: [String]? = nil) -> SettingItem {
        SettingItem(kind: .act(id: id, label: label, safe: safe), k: id, n: n, hint: hint, dev: dev)
    }
}

struct SettingCategory: Codable, Sendable, Identifiable {
    var id: String
    var n: String
    var sub: String
    var dev: [String]? = nil
    var items: [SettingItem]
}

// MARK: - Catalog

enum SK {
    static let names = ["Skjold S1", "Stue", "Kontor", "Soverom"]
    static let presetsRadio = ["NRK P1", "NRK P2", "NRK P3", "P4 Norge", "Radio Norge", "NRK Klassisk"]
    static let maxRadio = 50

    static let cats: [SettingCategory] = [
        SettingCategory(id: "eq", n: "Equalizer", sub: "Egen profil per inngang", items: [SettingItem(kind: .eq, k: "eq", n: "Equalizer")]),
        SettingCategory(id: "lyd", n: "Lyd", sub: "Tone, volum og nivå", items: [
            .num("bass", "Bass", -6, 6, .dB), .num("treb", "Diskant", -6, 6, .dB), .num("bal", "Balanse", -5, 5, .bal),
            .opt("vstart", "Startvolum", ["Sist brukt", "20", "30", "40"]), .opt("vmax", "Maksvolum", ["100", "90", "80", "70"]),
            .bool("perIn", "Volum per inngang", "Hver inngang husker sitt eget volum", dev: ["s1", "node"]),
            .bool("hpOwn", "Eget volum for hodetelefoner", dev: ["s1"]),
            .num("lvlAux", "Nivå AUX", -6, 6, .dB, "Juster så AUX er like høy som strømming", dev: ["s1"]),
            .num("lvlUsb", "Nivå USB", -6, 6, .dB, dev: ["s1"]),
            .act("Test høyttalerne", id: "testSpk", label: "Spill av", safe: true, "Spiller en kort tone i venstre og så i høyre høyttaler, så du kan sjekke at de er koblet riktig")]),
        SettingCategory(id: "touch", n: "Skjold Touch", sub: "Rolle, skjerm og standby", dev: ["touch"], items: [
            .opt("tRole", "Rolle", ["Spiller og fjernkontroll", "Bare spiller", "Bare fjernkontroll"], "Som spiller har den egen lydutgang (RCA og 3,5 mm). Som fjernkontroll styrer den alle Skjold-enhetene i huset."),
            .opt("tOut", "Lydutgang", ["RCA", "3,5 mm", "Begge"], "PCM5122 HIFI HAT"),
            .opt("tStandby", "Standby etter", ["Aldri", "30 s", "1 min", "5 min"], "Uten trykk på skjermen"),
            .opt("tIdle", "I standby vis", ["Klokke", "Cover og klokke", "Svart"]),
            .bool("tNight", "Nattmodus", "Rødlig, svakt lys mellom 23 og 07")]),
        SettingCategory(id: "utgang", n: "Lydutgang", sub: "DAC, HDMI, optisk eller 3,5 mm", dev: ["node", "core", "touch"], items: [
            .opt("out", "Utgang", ["3,5 mm (innebygd)", "HDMI", "USB-DAC", "I²S-kort (HiFiBerry / IQaudio)", "Optisk (S/PDIF)"], "Pi 3B og Pi 4 har 3,5 mm og HDMI. Et I²S-kort gir best lyd."),
            .opt("hat", "I²S-kort", ["Spotpear HIFI HAT (PCM5122)", "HiFiBerry DAC+", "HiFiBerry DAC2 HD", "IQaudio DAC Pro", "Allo Boss"], "Brukes bare når utgang er I²S-kort"),
            .opt("rate", "Samplingsfrekvens", ["44,1 kHz", "48 kHz", "96 kHz", "Følg kilden"]),
            .opt("mixer", "Volumkontroll", ["Programvare", "Maskinvare (DAC)", "Fast 100 % (styres av forsterker)"], "Velg fast hvis enheten er koblet til en egen forsterker med volumknapp"),
            .act("Test utgang", id: "testOut", label: "Spill testtone", safe: true)]),
        SettingCategory(id: "tilkobling", n: "Tilkobling", sub: "Navn og Blåtann", items: [
            .opt("name", "Enhetsnavn", names, "Navnet som vises i AirPlay og Blåtann"),
            .str("nAux1", "Navn på AUX 1", "AUX 1", "Vises på skjermen og i appen", dev: ["s1"]), .str("nAux2", "Navn på AUX 2", "AUX 2", dev: ["s1"]),
            .str("nUsb1", "Navn på USB-C «PC 1»", "PC", "For eksempel Mac eller Jobb-PC", dev: ["s1"]), .str("nUsb2", "Navn på USB-C «PC 2»", "Switch", dev: ["s1"]),
            .info("Parede enheter", key: "btDev"),
            .act("Blåtann-paring", id: "btPair", label: "Start paring", safe: true, "Enheten har ingen knapp. Gjør den synlig for Blåtann i 2 minutter herfra.", dev: ["node", "core", "touch"]),
            .bool("btAuto", "Blåtann alltid synlig", "Kan pares uten å starte paring først. Mindre sikkert.", dev: ["node", "core", "touch"]),
            .act("Glem alle Blåtann-enheter", id: "forget", label: "Glem alle")]),
        SettingCategory(id: "radio", n: "Radio", sub: "Favoritter, knapper og oppstart", items: [
            .opt("hold", "Hold radioknappen", presetsRadio, "Kanalen som spilles når du holder radioknappen inne", dev: ["s1"]),
            .opt("nodeStart", "Kanal ved oppstart", ["Ingen"] + presetsRadio, "Enheten har ingen knapper. Velg om den skal starte en radiokanal når den slås på.", dev: ["node", "core"])]),
        SettingCategory(id: "tjenester", n: "Musikktjenester", sub: "Spotify, UPnP/DLNA, YouTube Music, Navidrome, Plex", items: [
            .bool("spEn", "Spotify Connect", "Vises som høyttaler i Spotify-appen"),
            .bool("upnpEn", "UPnP/DLNA-mottaker", "Vises som høyttaler i apper som BubbleUPnP, foobar2000, Plex og «Cast til enhet» i Windows"),
            .info("Navn på nettverket", key: "netName", "Samme navn som i AirPlay. Endres under Enhet."),
            .bool("ytmEn", "YouTube Music", "Krever YouTube Music Premium. Gratiskontoer virker ikke."),
            .str("ytmUser", "Google-konto", "navn@gmail.com", "Gmail-adressen, eller den 21-sifrede ID-en for en merkekonto", long: true, max: 64),
            .str("ytmCookie", "Innloggings-cookie", "Lim inn Cookie-verdien", "Google tillater ikke vanlig innlogging for andre apper. Cookien må hentes på nytt når den utløper.", long: true, max: 8000, secret: true),
            SettingItem(kind: .steps(["Åpne music.youtube.com i et privat vindu (inkognito) på en datamaskin og logg inn.", "Åpne utviklerverktøyene og velg fanen Nettverk (Network).", "Skriv /browse i filterfeltet. Åpne en av spillelistene dine.", "Klikk på forespørselen som dukker opp. Under Request Headers kopierer du hele verdien til Cookie, uten mellomrom foran eller bak.", "Lukk det private vinduet med en gang, uten å logge ut. Lim inn verdien over."]), k: "ytmSteps", n: "Slik henter du cookien"),
            .info("PO-token-tjeneste", key: "ytmPo", "Bekrefter overfor Google at avspillingen kommer fra en ekte YouTube-klient"),
            .act("Test innlogging", id: "ytmTest", label: "Test", safe: true),
            .bool("ndEn", "Navidrome", "Eget musikkbibliotek via Subsonic-API"),
            .str("ndUrl", "Navidrome-server", "http://192.168.1.10:4533", "Adressen til Navidrome-serveren på hjemmenettet"),
            .str("ndUser", "Brukernavn", "brukernavn"),
            .str("ndPass", "Passord", "Navidrome-passord", "Lagres bare på telefonen", long: true, max: 128, secret: true),
            .act("Test Navidrome", id: "ndTest", label: "Test tilkobling", safe: true),
            .bool("plexEn", "Plex", "Spill musikk fra Plex Media Server"),
            .str("plexUrl", "Plex-server", "http://192.168.1.20:32400", "Adressen til Plex Media Server på hjemmenettet", long: true, max: 120),
            .str("plexToken", "Plex-token", "X-Plex-Token", "Finnes i Plex Web: åpne et album, velg ⋯ → Vis XML og kopier X-Plex-Token fra adressen", long: true, max: 64, secret: true),
            .act("Test Plex", id: "plexTest", label: "Test tilkobling", safe: true)]),
        SettingCategory(id: "stemme", n: "Stemme", sub: "Talebeskjeder", items: [
            .bool("voice", "Talebeskjed ved bytte"), .opt("lang", "Språk", ["Norsk", "English", "Svenska", "Dansk"]), .opt("vv", "Stemmevolum", ["Lav", "Middels", "Høy"]),
            .act("Test stemme", id: "testVoice", label: "Spill av", safe: true)]),
        SettingCategory(id: "skjerm", n: "Skjerm og lys", sub: "Dimming, klokke, LED", dev: ["s1"], items: [
            .opt("dim", "Dimme skjermen etter", ["Av", "30 s", "1 min"]), .opt("off", "Slukk skjermen etter", ["Av", "2 min", "5 min"], "Beskytter OLED-skjermen mot innbrenning"),
            .bool("clock", "Klokke i standby"), SettingItem(kind: .clocks, k: "clockStyle", n: "Klokke i standby"), .opt("led", "LED-ringer", ["Høy", "Middels", "Lav", "Av"])]),
        SettingCategory(id: "strom", n: "Strøm", sub: "Standby og påslag", items: [
            .opt("auto", "Auto-standby uten lyd", ["Av", "20 min", "60 min"]), .bool("wake", "Slå på ved signal", "AirPlay eller Blåtann vekker forsterkeren")]),
        SettingCategory(id: "oppdatering", n: "Oppdatering", sub: "GitHub, backup og gjenoppretting", items: [SettingItem(kind: .update, k: "update", n: "Oppdatering")]),
        SettingCategory(id: "steder", n: "Steder", sub: "Skjold-hjem: Hjem, Hytta … hovedenhet og reserve", items: [SettingItem(kind: .update, k: "steder", n: "Steder")]),
        SettingCategory(id: "skjoldhjem", n: "Skjold-hjem", sub: "Koble denne enheten til et sted", items: [SettingItem(kind: .update, k: "skjoldhjem", n: "Skjold-hjem")]),
        SettingCategory(id: "system", n: "System", sub: "Om, oppsett og tilbakestilling", items: [
            .info("Programvare", key: "version"), .info("IP-adresse", key: "ip"),
            .info("Lyrion", key: "lyrion"), .info("Serienummer", key: "serial"),
            .act("Kjør oppsett på nytt", id: "setup", label: "Start oppsett"),
            .act("Fabrikkinnstillinger", id: "reset", label: "Tilbakestill")])
    ]

    /// Default setting values. Booleans are stored as 0/1.
    static let def: [String: Int] = ["nodeStart": 0, "btAuto": 0, "out": 3, "hat": 0, "rate": 3, "mixer": 0, "clockStyle": 0, "name": 0, "lvlAux": 0, "lvlUsb": 0, "led": 0, "voice": 0, "lang": 0, "vv": 1, "hold": 2, "bass": 0, "treb": 0, "bal": 0, "vstart": 0, "vmax": 0, "perIn": 1, "hpOwn": 1, "dim": 1, "off": 1, "clock": 1, "auto": 1, "wake": 1, "tRole": 0, "tOut": 2, "tStandby": 1, "tIdle": 0, "tNight": 0]

    static func forDev(_ dev: [String]?, _ type: String) -> Bool { dev == nil || dev!.contains(type) }

    static func catsFor(_ type: String) -> [SettingCategory] {
        cats.filter { forDev($0.dev, type) }
            .map { var c = $0; c.items = c.items.filter { forDev($0.dev, type) }; return c }
            .filter { !$0.items.isEmpty }
    }

    // MARK: EQ

    static let eqBands = ["60", "250", "1k", "4k", "12k"]
    static let eqNames = ["Dypbass", "Bass", "Mellomtone", "Presens", "Luft"]
    static let eqHz = ["60 Hz", "250 Hz", "1 kHz", "4 kHz", "12 kHz"]
    static let eqDesc = ["Trommer, bassgitar og dunk. Mye her kan gi rumling.", "Fylde og varme. For mye gjør lyden grøtete.", "Stemmer og de fleste instrumenter.", "Klarhet i tale og vokal. For mye blir skarpt.", "Cymbaler, glans og romfølelse."]
    static let eqPresets: [(String, [Int])] = [("Flat", [0, 0, 0, 0, 0]), ("Bass+", [5, 2, 0, 0, 1]), ("Vokal", [-2, -1, 2, 3, 1]), ("Kveld", [2, 1, 0, -2, -3]), ("Podkast", [-5, -1, 3, 3, -2]), ("Klassisk", [1, 0, 0, 1, 2]), ("Rock", [4, 1, -2, 2, 3]), ("Pop", [2, 0, 1, 2, 2]), ("Elektronisk", [6, 1, -1, 1, 3]), ("Hip-hop", [6, 3, -1, 1, 1]), ("Jazz", [2, 1, -1, 1, 2]), ("Akustisk", [1, 2, 0, 2, 2]), ("Små høyttalere", [-4, 2, 1, 1, 0]), ("Lavt volum", [4, 1, -1, 1, 3])]
    static let eqSources: [(String, String)] = [("air", "AirPlay"), ("bt", "Blåtann"), ("radio", "Radio"), ("aux", "AUX"), ("usb", "USB"), ("hp", "Hodetelefoner")]
    static let eqDefaults: [String: Int] = ["air": 0, "bt": 1, "radio": 2, "aux": 0, "usb": 0, "hp": 3]

    // MARK: Radio

    static let catalog: [Station] = [("NRK P1", "Distriktsprogram"), ("NRK P1+", "Musikk for voksne"), ("NRK P2", "Kultur og samfunn"), ("NRK P3", "Pop og humor"), ("NRK mP3", "Hits"), ("NRK Klassisk", "Klassisk musikk"), ("NRK Jazz", "Jazz"), ("NRK Folkemusikk", "Folkemusikk"), ("NRK Alltid Nyheter", "Nyheter"), ("NRK Sport", "Sport"), ("P4 Norge", "Hits"), ("P5 Hits", "Hits"), ("P6 Rock", "Rock"), ("P7 Klem", "Ballader"), ("P9 Retro", "80- og 90-tallet"), ("Radio Norge", "Pop og rock"), ("NRJ", "Dance og pop"), ("Radio Rock", "Rock"), ("Kiss", "Pop"), ("BBC Radio 6 Music", "Alternativ")].map { Station(name: $0.0, genre: $0.1) }

    static let defaultRadio: [Station] = [("NRK P1", "Distriktsprogram"), ("NRK P2", "Kultur og samfunn"), ("NRK P3", "Pop og humor"), ("P4 Norge", "Hits"), ("Radio Norge", "Pop og rock"), ("NRK Klassisk", "Klassisk musikk")].map { Station(name: $0.0, genre: $0.1) }

    static let nowPlayingMap: [String: (String, String)] = ["NRK P1": ("Nyheter", "NRK Dagsnytt"), "NRK P2": ("Ekko", "Et aktuelt samfunnsprogram"), "NRK P3": ("Dance The Way I Feel", "Ofenbach"), "P4 Norge": ("Flowers", "Miley Cyrus"), "Radio Norge": ("Mr. Brightside", "The Killers"), "NRK Klassisk": ("Clair de lune", "Claude Debussy")]

    static func nowPlaying(_ name: String) -> (String, String) { nowPlayingMap[name] ?? ("Direkte", name) }

    /// Search query + country code used to find station logos on Radio Browser.
    static let logoQuery: [String: (String, String)] = ["P4 Norge": ("P4", "NO"), "P5 Hits": ("P5", "NO"), "P6 Rock": ("P6 Rock", "NO"), "P7 Klem": ("P7 Klem", "NO"), "P9 Retro": ("P9 Retro", "NO"), "Radio Norge": ("Radio Norge", "NO"), "NRJ": ("NRJ Norge", "NO"), "Radio Rock": ("Radio Rock", "NO"), "Kiss": ("Kiss", "NO"), "BBC Radio 6 Music": ("BBC Radio 6 Music", "GB"), "NRK Alltid Nyheter": ("NRK Alltid Nyheter", "NO")]

    /// NRK logos ship as vector assets (static.nrk.no SVGs).
    static let nrkAsset: [String: String] = ["NRK P1": "nrk-p1", "NRK P1+": "nrk-p1plus", "NRK P2": "nrk-p2", "NRK P3": "nrk-p3", "NRK mP3": "nrk-mp3", "NRK Klassisk": "nrk-klassisk", "NRK Jazz": "nrk-jazz", "NRK Folkemusikk": "nrk-folkemusikk", "NRK Sport": "nrk-sport"]

    // MARK: Devices and rooms

    struct DevType { let n: String; let d: String; let icon: String; let inputs: [String] }

    static let devTypes: [String: DevType] = [
        "s1": DevType(n: "Skjold S1", d: "Forsterker med skjerm, knapper og AUX/USB-innganger", icon: "M3 7.5h18a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1v-7a1 1 0 0 1 1-1zM4.5 9.8h5v3.4h-5zM11.6 10.3a.6.6 0 1 0 1.2 0a.6.6 0 1 0-1.2 0M13.8 10.3a.6.6 0 1 0 1.2 0a.6.6 0 1 0-1.2 0M11.6 13.7a.6.6 0 1 0 1.2 0a.6.6 0 1 0-1.2 0M13.8 13.7a.6.6 0 1 0 1.2 0a.6.6 0 1 0-1.2 0M16.4 12a2.3 2.3 0 1 0 4.6 0a2.3 2.3 0 1 0-4.6 0M18.7 10.2v1.2M3.5 16.5v1M20.5 16.5v1", inputs: ["AirPlay", "Blåtann", "AUX", "Radio", "USB"]),
        "node": DevType(n: "Skjold Node", d: "Raspberry Pi 3B eller 4 med bare lydutgang. Kobles til egen forsterker, aktive høyttalere eller DAC.", icon: "M4 6h14a1.5 1.5 0 0 1 1.5 1.5v9A1.5 1.5 0 0 1 18 18H4a1.5 1.5 0 0 1-1.5-1.5v-9A1.5 1.5 0 0 1 4 6zM19.5 8h2v2.6h-2zM19.5 11.4h2v2.6h-2zM19.5 14.6h2v2h-2zM5 7.8h9M8 18v1.2M11.5 18v1.2M6.2 11.2h4.6v4.6H6.2zM15.2 15.3a.5.5 0 1 0 1 0a.5.5 0 1 0-1 0", inputs: ["AirPlay", "Blåtann", "Radio"]),
        "core": DevType(n: "Skjold Core", d: "Sentral enhet uten skjerm. Kjører Lyrion-serveren for hele systemet og kan spille via linjeutgang eller digital utgang.", icon: "M5 4h14a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1zM8 8h8v8H8zM12 4V2M12 22v-2M4 12H2M22 12h-2M10 11h4M10 13h4", inputs: ["AirPlay", "Blåtann", "Radio"])
    ]

    static func dev(_ type: String) -> DevType { devTypes[type] ?? devTypes["s1"]! }

    static let roles = ["Stereo", "Venstre", "Høyre", "Bak V", "Bak H", "Sub"]

    static let sysDefault = SystemState(active: "stue", rooms: [
        Room(id: "stue", name: "Stue", type: "s1", hw: "Pi Zero 2 W · TPA3116 2 × 50 W", vol: 42, group: "g1"),
        Room(id: "kjokken", name: "Kjøkken", type: "node", hw: "Raspberry Pi 4 · HiFiBerry DAC+", vol: 30, group: "g1"),
        Room(id: "kontor", name: "Kontor", type: "node", hw: "Raspberry Pi 3B · 3,5 mm", vol: 25, np: ["Teardrop", "Massive Attack", "AirPlay"]),
        Room(id: "core", name: "Hjemmekino", type: "core", hw: "Raspberry Pi 5 · Lyrion-server · optisk ut", vol: 35)
    ])

    // MARK: Updates

    static let releases: [Release] = [
        Release(tag: "v1.5.0", name: "Skjold 1.5.0", date: "2026-10-29", notes: ["Spotify Connect som egen inngang", "EQ-profiler per inngang", "Raskere oppstart (2,1 s)", "Retter: Blåtann kobler ikke til etter standby"], size: "18,4 MB", pre: false),
        Release(tag: "v1.6.0-beta.1", name: "Skjold 1.6.0 beta 1", date: "2026-10-30", notes: ["Multirom med Lyrion-synk", "Ny radiomeny på skjermen"], size: "19,1 MB", pre: true)
    ]

    static let updDefault = UpdateState(version: "1.4.2", repo: GitHubReleases.repo, channel: 0, auto: true, failNext: false, latest: nil, checkedAt: "", log: [], backups: [
        Backup(id: "b3", ver: "1.4.2", date: "2026-10-28 03:12", kind: "Automatisk før oppdatering"),
        Backup(id: "b2", ver: "1.4.1", date: "2026-10-02 03:08", kind: "Automatisk før oppdatering"),
        Backup(id: "b1", ver: "1.4.0", date: "2026-09-14 19:40", kind: "Manuell")
    ])

    static func findRelease(_ u: UpdateState) -> Release? {
        let r = releases.filter { u.channel == 1 || !$0.pre }.sorted { $0.date > $1.date }.first
        guard let r, r.tag.replacingOccurrences(of: "v", with: "", options: .anchored) != u.version else { return nil }
        return r
    }

    static func now() -> String {
        let f = DateFormatter(); f.dateFormat = "yyyy-MM-dd HH:mm"; return f.string(from: Date())
    }

    // MARK: Clocks

    static let clocks = ["Tynn", "Stor", "Analog", "Ord", "Linje", "Dato"]

    // MARK: Demo music library (same as the design file)

    static let tr: [(String, String)] = [("Midnight City", "M83"), ("Intro", "The xx"), ("Breathe", "Télépopmusik")]
    static let dur = [243, 128, 279]
    static let lt: [Track] = [("Eple", "Röyksopp", "Melody A.M.", 219), ("Take On Me", "a-ha", "Hunting High and Low", 225), ("Runaway", "AURORA", "All My Demons Greeting Me as a Friend", 249), ("Strangers", "Sigrid", "Sucker Punch", 214), ("Firestone", "Kygo", "Cloud Nine", 272), ("Midnight City", "M83", "Hurry Up, We're Dreaming", 243), ("Teardrop", "Massive Attack", "Mezzanine", 330), ("Intro", "The xx", "xx", 128), ("Breathe", "Télépopmusik", "Genetic World", 279), ("Poor Leno", "Röyksopp", "Melody A.M.", 237), ("Hunting High and Low", "a-ha", "Hunting High and Low", 225), ("Murder Song (5, 4, 3, 2, 1)", "AURORA", "All My Demons Greeting Me as a Friend", 199)].map { Track(t: $0.0, artist: $0.1, album: $0.2, dur: $0.3) }

    struct Library { let name: String; let tabs: [String]; let pls: [(String, [Int])]; let hist: [(Int, String)] }

    static let lib: [String: Library] = [
        "ytm": Library(name: "YouTube Music", tabs: ["Hjem", "Spillelister", "Historikk"], pls: [("Likte låter", Array(0...11)), ("Supermix", [5, 0, 2, 6, 1, 4]), ("Fredagskveld", [4, 3, 1, 10]), ("Nordisk ro", [2, 11, 0, 9])], hist: [(3, "I dag 21:40"), (0, "I dag 20:12"), (5, "I går 22:05"), (1, "I går 18:30")]),
        "nd": Library(name: "Navidrome", tabs: ["Album", "Spillelister", "Historikk"], pls: [("Favoritter", [6, 7, 8, 5]), ("Vinyl-rips", [0, 9, 1, 10]), ("Sent på kvelden", [7, 6, 8, 2])], hist: [(6, "I dag 19:02"), (9, "Mandag"), (7, "Søndag")]),
        "plex": Library(name: "Plex", tabs: ["Album", "Spillelister", "Historikk"], pls: [("Mest spilt", [1, 4, 3, 5, 0]), ("Søndagsmorgen", [8, 2, 7, 11]), ("Nordisk", [0, 1, 2, 3, 9, 10])], hist: [(4, "I dag 17:45"), (1, "I går 21:10"), (8, "Lørdag")])
    ]

    static let moods = ["Ny energi", "Godfølelse", "Avslapping", "Trening", "Fest", "Fokus", "Søvn"]
}

// MARK: - Value types

struct Station: Codable, Hashable, Sendable {
    var name: String
    var genre: String
    var url: String? = nil
    var image: String? = nil
}

struct Track: Hashable, Sendable {
    var t: String
    var artist: String
    var album: String
    var dur: Int
    /// Live libraries: service id, cover URL and a stream URL the amplifier can play. Empty for demo tracks.
    var id: String = ""
    var cover: String = ""
    var stream: String = ""
}

struct Room: Codable, Hashable, Sendable, Identifiable {
    var id: String
    var name: String
    var type: String
    var hw: String
    var vol: Int
    var group: String? = nil
    var np: [String]? = nil
    var role: Int? = nil
    /// Skjold daemon ("ip:port") when the room is a Skjold device, nil for a plain Lyrion player.
    var host: String? = nil
    /// Lyrion playerid (Squeezelite MAC) used for sync and per-room volume.
    var pid: String? = nil
}

struct SystemState: Codable, Sendable {
    var active: String
    var rooms: [Room]
    var modes: [String: String] = [:]

    func groupOf(_ id: String) -> [Room] {
        guard let r = rooms.first(where: { $0.id == id }) else { return [] }
        guard let g = r.group else { return [r] }
        return rooms.filter { $0.group == g }
    }

    func groupLabel(_ id: String) -> String {
        let g = groupOf(id)
        guard let first = g.first else { return "" }
        return (g.first(where: { $0.id == id }) ?? first).name + (g.count > 1 ? " + \(g.count - 1)" : "")
    }

    func toggledInGroup(active activeId: String, _ id: String) -> SystemState {
        var n = self
        guard let ai = n.rooms.firstIndex(where: { $0.id == activeId }),
              let ri = n.rooms.firstIndex(where: { $0.id == id }), ai != ri else { return n }
        if n.rooms[ai].group == nil { n.rooms[ai].group = "g\(Int(Date().timeIntervalSince1970 * 1000))" }
        let g = n.rooms[ai].group
        if n.rooms[ri].group == g { n.rooms[ri].group = nil } else { n.rooms[ri].group = g; n.rooms[ri].np = nil }
        if n.rooms.filter({ $0.group == g }).count == 1 { n.rooms[ai].group = nil }
        return n
    }

    func groupedAll() -> SystemState {
        var n = self
        for i in n.rooms.indices { n.rooms[i].group = "gall"; n.rooms[i].np = nil }
        return n
    }

    func withGroupMode(_ gid: String, _ mode: String) -> SystemState {
        var n = self
        n.modes[gid] = mode
        if mode == "surround" {
            var i = 0
            for j in n.rooms.indices where n.rooms[j].group == gid && n.rooms[j].role == nil {
                n.rooms[j].role = [0, 3, 4, 5][min(3, i)]; i += 1
            }
        }
        return n
    }
}

struct EQProfile: Codable, Hashable, Sendable {
    var preset: Int
    var eq: [Int]
    var loud: Bool
}

struct Release: Codable, Hashable, Sendable {
    var tag: String, name: String, date: String, notes: [String], size: String, pre: Bool
}

struct Backup: Codable, Hashable, Sendable {
    var id: String, ver: String, date: String, kind: String
}

struct UpdateLog: Codable, Hashable, Sendable {
    var date: String, text: String, bad: Bool = false
}

struct UpdateState: Codable, Sendable {
    var version: String
    var repo: String
    var channel: Int
    var auto: Bool
    var failNext: Bool
    var latest: Release?
    var checkedAt: String
    var log: [UpdateLog]
    var backups: [Backup]
}
