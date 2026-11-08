import SwiftUI

/// UI-tilstand som bare finnes i v4-skallet (state i class Component: src, pl, search, more, dial, col …).
/// Avspilling, rom, EQ og innstillinger ligger fortsatt i AppModel.
@Observable
final class V4State {
    /// fm: "ctrl" | "queue" | "rooms"
    var fm = "ctrl"
    var src: String? = nil
    var srcQ = ""
    var pl: V4Playlist? = nil
    var search = false
    var sq = ""
    var sSrc: Int? = nil
    var more = false
    var moreTrack: Track? = nil
    var dial = false
    var col = false
    var homeOpen = false
    var sortOpen = false
    var pin = false
    var sort: Int = UserDefaults.standard.integer(forKey: "skjold-v4-sort") {
        didSet { UserDefaults.standard.set(sort, forKey: "skjold-v4-sort") }
    }
    var pins: [String] = UserDefaults.standard.stringArray(forKey: "skjold-v4-pins") ?? [] {
        didSet { UserDefaults.standard.set(pins, forKey: "skjold-v4-pins") }
    }
    var hint = !UserDefaults.standard.bool(forKey: "skjold-v4-hint-seen")
    var xfade = UserDefaults.standard.bool(forKey: "skjold-v4-xfade") {
        didSet { UserDefaults.standard.set(xfade, forKey: "skjold-v4-xfade") }
    }
    var sleep = 0
    var lastY: CGFloat = 0

    func hideHint() {
        guard hint else { return }
        hint = false
        UserDefaults.standard.set(true, forKey: "skjold-v4-hint-seen")
    }

    /// Lukker alt som ligger over fanene (som pick() i TABS).
    func resetOverlays() {
        sortOpen = false; pl = nil; src = nil; search = false; homeOpen = false
    }

    /// onScr: slå sammen dokken når man ruller ned forbi 60, fold ut når man ruller opp > 4 eller er nær toppen.
    func scrolled(_ y: CGFloat) {
        let d = y - lastY
        lastY = y
        var c = col
        if y > 60 && d > 0 { c = true } else if d < -4 || y < 20 { c = false }
        if c != col { withAnimation(V4.collapse) { col = c } }
    }
}

/// Spilleliste/album fra et bibliotek (eller demobiblioteket).
struct V4Playlist: Hashable {
    var id: String
    var name: String
    var owner: String
    var src: String        // visningsnavn: «Navidrome», «Plex», «YouTube Music»
    var lib: String        // «nd», «plex», «ytm»
    var keys: [String]     // omslag til mosaikken
    var demoIdx: [Int] = []
    var coll: LibColl? = nil
    var count: Int = 0
}

/// Kildeside-navn → bibliotek-id.
enum V4Lib {
    static let names: [String: String] = ["nd": "Navidrome", "plex": "Plex", "ytm": "YouTube Music"]
    static func id(_ label: String) -> String? {
        switch label {
        case "Navidrome": return "nd"
        case "Plex": return "plex"
        case "YouTube Music", "YT Music": return "ytm"
        default: return nil
        }
    }

    /// Spillelister for ett bibliotek: demodata eller det som er lastet fra tjenesten.
    @MainActor static func playlists(_ m: AppModel, _ lib: String) -> [V4Playlist] {
        let src = names[lib] ?? lib
        if m.demo {
            let pls = SK.lib[lib]?.pls ?? []
            return pls.enumerated().map { i, p in
                let keys = p.1.prefix(4).map { SK.lt[$0 % SK.lt.count].album }
                return V4Playlist(id: lib + "/\(i)", name: p.0, owner: i == 0 ? "Deg" : "Laget for deg", src: src, lib: lib,
                                  keys: Array(keys), demoIdx: p.1, count: p.1.count)
            }
        }
        let d = m.libs[lib]
        // YouTube Music: også «Til deg» (mikser og anbefalte album fra forsiden), så det er noe å spille uten innlogging
        let colls = (d?.playlists ?? []) + (d?.newest ?? []).prefix(8) + (lib == "ytm" ? Array((d?.frequent ?? []).prefix(8)) + Array((d?.other ?? []).prefix(8)) : [])
        return colls.map { c in
            V4Playlist(id: lib + "/" + c.id, name: c.name, owner: c.playlist ? "Spilleliste" : c.artist, src: src, lib: lib,
                       keys: [c.name, c.name + " 2", c.name + " 3", c.name + " 4"], coll: c, count: c.count)
        }
    }

    @MainActor static func tracks(_ m: AppModel, _ p: V4Playlist) async -> [Track] {
        if let c = p.coll { return await m.collTracks(p.lib, c) }
        return p.demoIdx.map { SK.lt[$0 % SK.lt.count] }
    }
}
