import Foundation

/// Én seksjon på hjemskjermen. Samme id-er som web (lib/homelayout.ts), Android og pi/skjold_homelayout.py.
nonisolated struct HomeItem: Sendable, Equatable, Hashable, Identifiable, Codable {
    var id: String
    var visible: Bool
}

/// Rekkefølge og synlighet for seksjonene på hjemskjermen (settings.homeLayout). Lagres per Skjold-enhet (rom)
/// og synkes med web-UI og Android via /api/settings.
nonisolated enum HomeLayout {
    static let sections: [(String, String)] = [
        ("recent", "Nylig spilt"), ("favs", "Radiofavoritter"), ("sources", "Kilder"), ("routines", "Rutiner"),
        ("discover", "Oppdag"), ("ask", "Spill noe til …"), ("nrk", "Fortsett på NRK"), ("playlists", "Dine spillelister"),
        ("library", "Fra bibliotekene"), ("wrapped", "Skjold Wrapped"),
    ]
    /// Seksjonene iOS-appen viser, i standardrekkefølge.
    static let ios = ["recent", "sources", "favs", "playlists", "library"]

    static func label(_ id: String) -> String { sections.first { $0.0 == id }?.1 ?? id }

    /// Lagret rekkefølge først (bare kjente id-er), deretter manglende seksjoner – synlige – på slutten.
    static func resolve(_ layout: [HomeItem], available: [String]) -> [HomeItem] {
        var out: [HomeItem] = []
        for it in layout where available.contains(it.id) && !out.contains(where: { $0.id == it.id }) { out.append(it) }
        for id in available where !out.contains(where: { $0.id == id }) { out.append(HomeItem(id: id, visible: true)) }
        return out
    }

    static func parse(_ v: Any?) -> [HomeItem]? {
        guard let arr = v as? [Any] else { return nil }
        return arr.compactMap { e -> HomeItem? in
            guard let d = e as? [String: Any], let id = d["id"] as? String, !id.isEmpty else { return nil }
            return HomeItem(id: id, visible: (d["visible"] as? NSNumber)?.boolValue ?? true)
        }
    }
}
