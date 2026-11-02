import SwiftUI

/// Cover / station art. Mirrors art() in skjold_settings.js: a real logo when one is known,
/// otherwise a 150° oklch gradient derived from a hash of the name.
struct ArtInfo {
    var stops: [Gradient.Stop]
    var ink: Color
    var logoAsset: String? = nil
    var logoURL: URL? = nil

    var hasLogo: Bool { logoAsset != nil || logoURL != nil }
    /// First stop, used where a flat colour is needed.
    var base: Color { stops.first?.color ?? .card }
}

nonisolated enum ArtHash {
    static func hue(_ s: String) -> Int {
        var h = 0
        for u in s.utf16 { h = (h * 31 + Int(u)) % 360 }
        return h
    }
}

@MainActor
func art(_ key: String) -> ArtInfo {
    let h = Double(ArtHash.hue(key))
    let a = OKLCH.lab(0.42, 0.09, h), b = OKLCH.lab(0.2, 0.04, Double((Int(h) + 40) % 360))
    var info = ArtInfo(stops: OKLCH.stops(from: a, to: b), ink: OKLCH.color(0.93, 0.03, h))
    if let asset = SK.nrkAsset[key] {
        info.logoAsset = asset
        info.ink = .clear
    } else if let url = LogoStore.shared.url(for: key) {
        info.logoURL = url
        info.ink = .clear
    }
    return info
}

/// Draws the art background: gradient, or logo on #121214 (NRK, 72% wide) / #f4f2ee (others, cover).
struct ArtFill: View {
    let info: ArtInfo

    init(_ info: ArtInfo) { self.info = info }
    init(_ key: String) { self.info = art(key) }

    var body: some View {
        if let asset = info.logoAsset {
            GeometryReader { g in
                ZStack {
                    Color(hex: 0x121214)
                    Image(asset).resizable().scaledToFit().frame(width: g.size.width * 0.72)
                }
                .frame(width: g.size.width, height: g.size.height)
            }
        } else if let url = info.logoURL {
            ZStack {
                Color(hex: 0xf4f2ee)
                AsyncImage(url: url) { img in
                    img.resizable().scaledToFill()
                } placeholder: { Color.clear }
            }
            .clipped()
        } else {
            CSSLinearGradient(angle: 150, stops: info.stops)
        }
    }
}

/// Fetches station logos from Radio Browser (same source as the design) and caches the URLs.
@Observable
final class LogoStore {
    static let shared = LogoStore()

    private(set) var urls: [String: String]
    private var pending: Set<String> = []
    private let key = "skjold-logos-v2"

    private init() {
        urls = (UserDefaults.standard.dictionary(forKey: key) as? [String: String]) ?? [:]
    }

    func url(for name: String) -> URL? {
        guard let s = urls[name], !s.isEmpty else { return nil }
        return URL(string: s)
    }

    func fetch(_ names: [String]) {
        for name in names where urls[name] == nil && !pending.contains(name) && SK.nrkAsset[name] == nil {
            guard let (q, cc) = SK.logoQuery[name] else { continue }
            pending.insert(name)
            Task {
                let found = await RadioBrowser.logo(query: q, country: cc)
                pending.remove(name)
                // nil = network error (try again next launch), "" = no usable logo
                if let found { store(name, found) }
            }
        }
    }

    private func store(_ name: String, _ url: String) {
        urls[name] = url
        UserDefaults.standard.set(urls, forKey: key)
    }
}
