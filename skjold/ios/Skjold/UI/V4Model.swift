import SwiftUI

/// Avledede verdier og handlinger v4-skjermene trenger, bygget på AppModel sitt eksisterende API.
extension AppModel {
    /// Rommene i gruppen til det aktive rommet.
    var v4Group: [Room] {
        let g = sys.groupOf(actRoom.id)
        return g.isEmpty ? [actRoom] : g
    }

    /// groupName i malen: «Stue», «Stue + Kjøkken», «Stue + 2».
    var v4GroupName: String {
        let g = v4Group
        guard let first = g.first(where: { $0.id == actRoom.id }) ?? g.first else { return actRoom.name }
        if g.count == 1 { return first.name }
        if g.count == 2, let other = g.first(where: { $0.id != first.id }) { return first.name + " + " + other.name }
        return first.name + " + \(g.count - 1)"
    }

    /// Gruppevolum = snittet av rommene i gruppen (aktivt rom leses fra vol).
    var v4GroupVol: Int {
        let g = v4Group
        guard g.count > 1 else { return vol }
        let vals = g.map { $0.id == actRoom.id ? vol : $0.vol }
        return Int((Double(vals.reduce(0, +)) / Double(vals.count)).rounded())
    }

    /// Flytter alle rommene i gruppen like mye (shift() i malen).
    func v4SetGroupVol(_ v: Int) {
        let target = max(0, min(100, v))
        let g = v4Group
        guard g.count > 1 else { setVol(target); return }
        let delta = target - v4GroupVol
        guard delta != 0 else { return }
        var n = sys
        for r in g {
            guard let i = n.rooms.firstIndex(where: { $0.id == r.id }) else { continue }
            let cur = r.id == actRoom.id ? vol : r.vol
            n.rooms[i].vol = max(0, min(100, cur + delta))
            if r.id == actRoom.id { setVol(n.rooms[i].vol) }
        }
        setSys(n)
    }

    /// Volum for ett rom.
    func v4SetRoomVol(_ id: String, _ v: Int) {
        let t = max(0, min(100, v))
        if id == actRoom.id { setVol(t) }
        var n = sys
        if let i = n.rooms.firstIndex(where: { $0.id == id }) { n.rooms[i].vol = t }
        setSys(n)
    }

    func v4RoomVol(_ r: Room) -> Int { r.id == actRoom.id ? vol : r.vol }

    /// Legg til / fjern et rom i gruppen til det aktive rommet.
    func v4ToggleInGroup(_ id: String) {
        setSys(sys.toggledInGroup(active: actRoom.id, id))
    }

    /// Gjør et rom aktivt (det appen styrer).
    func v4Activate(_ r: Room) {
        var n = sys
        n.active = r.id
        setSys(n)
        if live { activate(r) }
    }

    /// Spill/pause i et annet rom enn det aktive.
    func v4ToggleRoom(_ r: Room) {
        if r.id == actRoom.id { togglePlay(); return }
        Haptics.thump()
        if let h = r.host { devSend("/api/transport", ["action": "playpause"], on: h) }
        else if let pid = r.pid { lyrionCmd(pid, ["pause"]) }
    }

    /// Nå spilles: kildenavn som i malen (cur.src).
    var v4Src: String {
        if headphones && input == 4 { return "USB" }
        return srcName
    }

    /// Kildeikon-etikett for det som spiller.
    var v4SrcIcon: String {
        if let s = svc {
            return ["spotify": "Spotify", "upnp": "UPnP/DLNA", "ytm": "YouTube Music", "nd": "Navidrome", "plex": "Plex"][s] ?? "AirPlay"
        }
        return ["AirPlay", "Blåtann", "AUX", "Radio", "USB"][max(0, min(4, input))]
    }

    var v4Live: Bool { input == 3 }

    /// Fremdrift 0…1 (radio = full ring).
    var v4Progress: Double {
        guard hasProgress, duration > 0 else { return v4Live ? 1 : 0 }
        return Double(position) / Double(duration)
    }

    /// Køen: bibliotekskø, ellers demolåtene, ellers bare det som spiller.
    var v4Queue: [(t: String, s: String, key: String, cur: Bool, i: Int)] {
        if let q = lq, libTrack != nil {
            return q.enumerated().map { (t: $0.element.t, s: $0.element.artist, key: $0.element.album, cur: $0.offset == li, i: $0.offset) }
        }
        if !live {
            return SK.tr.enumerated().map { (t: $0.element.0, s: $0.element.1, key: $0.element.0, cur: $0.offset == trk, i: $0.offset) }
        }
        return [(t: np.t, s: np.s, key: playerArt.key, cur: true, i: 0)]
    }

    func v4PlayQueue(_ i: Int) {
        if let q = lq, libTrack != nil { playLib(q, i, keepOpen: true) }
        else if !live { trk = i; pos = 0; playing = true }
    }

    /// Flytt en låt i bibliotekskøen ett hakk opp.
    func v4QueueUp(_ i: Int) {
        guard var q = lq, libTrack != nil, i > 0, i < q.count else { return }
        q.swapAt(i - 1, i)
        if li == i { li = i - 1 } else if li == i - 1 { li = i }
        lq = q
    }

    func v4QueueRemove(_ t: Track) {
        guard var q = lq, libTrack != nil, let i = q.firstIndex(of: t), i != li else { return }
        q.remove(at: i)
        if i < li { li -= 1 }
        lq = q
    }

    func v4PlayNext(_ t: Track) {
        guard var q = lq, libTrack != nil else { return }
        if let i = q.firstIndex(of: t), i != li { q.remove(at: i); if i < li { li -= 1 } }
        q.insert(t, at: min(q.count, li + 1))
        lq = q
    }

    /// EQ-kildene i malen og nøklene i eqP.
    static let v4EqSrcs: [(String, String)] = [("AirPlay", "air"), ("Blåtann", "bt"), ("Radio", "radio"), ("AUX", "aux"), ("USB", "usb"), ("Hodetelefoner", "hp")]
}
