import SwiftUI
import UIKit

/// Cover / station art. Mirrors art() in skjold_settings.js: a real logo when one is known,
/// otherwise a 150° oklch gradient derived from a hash of the name.
struct ArtInfo {
    var stops: [Gradient.Stop]
    var ink: Color
    var logoAsset: String? = nil
    var logoURL: URL? = nil
    /// Navnet (nøkkelen) og tekstfargen fra gradienten: brukes som reserveflis når logoen ikke kan lastes.
    var name: String = ""
    var nameInk: Color = .white

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
    let ink = OKLCH.color(0.93, 0.03, h)
    var info = ArtInfo(stops: OKLCH.stops(from: a, to: b), ink: ink, name: key, nameInk: ink)
    if let asset = SK.nrkAsset[key] {
        info.logoAsset = asset
        info.ink = .clear
    } else if let url = CoverStore.shared.url(for: key) ?? LogoStore.shared.url(for: key) {
        info.logoURL = url
        info.ink = .clear
    }
    return info
}

/// Draws the art background: gradient, or logo on #121214 (NRK, 72% wide) / a background that matches the logo (others).
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
            RemoteLogo(url: url, info: info)
        } else {
            CSSLinearGradient(angle: 150, stops: info.stops)
        }
    }
}

/// Logo fra nettet. Bakgrunnen hentes fra selve bildet (hjørnepikslene), så flisen og logoen går i ett uten en
/// lysere ramme rundt. Gjennomsiktige logoer får mørk bakgrunn når de er lyse (hvit-på-hvitt) og lys ellers.
/// Feiler lastingen (http blokkert av ATS, SVG, 404) vises gradienten med kanalnavnet i stedet for en tom flis.
private struct RemoteLogo: View {
    let url: URL
    let info: ArtInfo

    var body: some View {
        GeometryReader { g in
            let w = g.size.width, h = g.size.height
            ZStack {
                switch LogoImages.shared.state(url) {
                case .loaded(let l):
                    l.bg
                    Image(uiImage: l.image).resizable().interpolation(.high).scaledToFit()
                        .padding(l.opaque ? 0 : min(w, h) * 0.12)
                        .frame(width: w, height: h)
                case .failed:
                    ArtNameTile(info: info, size: min(w, h))
                case .loading:
                    CSSLinearGradient(angle: 150, stops: info.stops)
                }
            }
            .frame(width: w, height: h)
            .clipped()
        }
        .task(id: url) { await LogoImages.shared.load(url) }
    }
}

/// Reserveflis: gradienten med kanalnavnet (store fliser) eller forkortelsen (små).
private struct ArtNameTile: View {
    let info: ArtInfo
    let size: CGFloat

    var body: some View {
        ZStack(alignment: size >= 80 ? .bottomLeading : .center) {
            CSSLinearGradient(angle: 150, stops: info.stops)
            if size >= 80 {
                Text(info.name).sora(15, .semibold, info.nameInk, lineHeight: 1.05).lineLimit(3)
                    .padding(11)
                    .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .bottomLeading)
            } else if size >= 24 {
                Text(Self.abbr(info.name)).sora(max(8, size * 0.28), .semibold, info.nameInk)
                    .lineLimit(1).minimumScaleFactor(0.5).padding(3)
            }
        }
    }

    static func abbr(_ n: String) -> String {
        let w = n.split(separator: " ").filter { !$0.isEmpty }
        if w.count >= 2 { return w.prefix(3).compactMap { $0.first.map(String.init) }.joined().uppercased() }
        return String(n.prefix(3)).uppercased()
    }
}

/// Lastede logoer i minnet, med bakgrunnsfargen som passer til hver av dem.
@Observable
final class LogoImages {
    static let shared = LogoImages()

    struct Loaded {
        let image: UIImage
        let bg: Color
        /// Bildet har egen, ugjennomsiktig bakgrunn (fylles kant i kant), ellers tegnes det med luft rundt.
        let opaque: Bool
    }
    enum Phase { case loading, loaded(Loaded), failed }

    private(set) var states: [URL: Phase] = [:]
    private var inFlight: Set<URL> = []

    func state(_ url: URL) -> Phase { states[url] ?? .loading }

    func load(_ url: URL) async {
        if let s = states[url], case .loaded = s { return }
        guard !inFlight.contains(url) else { return }
        inFlight.insert(url)
        defer { inFlight.remove(url) }
        var req = URLRequest(url: url, timeoutInterval: 12)
        req.cachePolicy = .returnCacheDataElseLoad
        guard let res = try? await URLSession.shared.data(for: req),
              (res.1 as? HTTPURLResponse).map({ (200..<300).contains($0.statusCode) }) ?? true else {
            states[url] = .failed
            return
        }
        let data = res.0
        let result = await Task.detached(priority: .utility) { LogoAnalysis.analyze(data) }.value
        if let r = result {
            states[url] = .loaded(Loaded(image: r.image, bg: Color(.sRGB, red: r.r, green: r.g, blue: r.b, opacity: 1), opaque: r.opaque))
        } else {
            states[url] = .failed
        }
    }
}

/// Finner bakgrunnen til en logo: snittet av hjørnepikslene når de er dekkende, ellers mørk eller lys
/// etter hvor lys selve logoen er.
nonisolated enum LogoAnalysis {
    nonisolated struct Analysed: @unchecked Sendable { let image: UIImage; let r: Double; let g: Double; let b: Double; let opaque: Bool }

    static func analyze(_ data: Data) -> Analysed? {
        guard let img = UIImage(data: data), let cg = img.cgImage, cg.width > 0, cg.height > 0 else { return nil }
        let n = 32
        var px = [UInt8](repeating: 0, count: n * n * 4)
        let ok: Bool = px.withUnsafeMutableBytes { buf in
            guard let ctx = CGContext(data: buf.baseAddress, width: n, height: n, bitsPerComponent: 8, bytesPerRow: n * 4,
                                      space: CGColorSpaceCreateDeviceRGB(),
                                      bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else { return false }
            ctx.interpolationQuality = .medium
            ctx.draw(cg, in: CGRect(x: 0, y: 0, width: n, height: n))
            return true
        }
        guard ok else { return nil }
        func pixel(_ x: Int, _ y: Int) -> (Double, Double, Double, Double) {
            let i = (y * n + x) * 4
            return (Double(px[i]) / 255, Double(px[i + 1]) / 255, Double(px[i + 2]) / 255, Double(px[i + 3]) / 255)
        }
        // Hjørnene (1 px inn, så kantutjevning i selve bildet ikke teller)
        let corners = [pixel(1, 1), pixel(n - 2, 1), pixel(1, n - 2), pixel(n - 2, n - 2)]
        let alpha = corners.map { $0.3 }.reduce(0, +) / 4
        if alpha > 0.92 {
            let r = corners.map { $0.0 }.reduce(0, +) / 4, g = corners.map { $0.1 }.reduce(0, +) / 4, b = corners.map { $0.2 }.reduce(0, +) / 4
            return Analysed(image: img, r: r, g: g, b: b, opaque: true)
        }
        // Gjennomsiktig bakgrunn: hvor lys er selve logoen?
        var lum = 0.0, weight = 0.0
        for y in 0..<n { for x in 0..<n {
            let (r, g, b, a) = pixel(x, y)
            guard a > 0.4 else { continue }
            lum += 0.2126 * r + 0.7152 * g + 0.0722 * b   // premultiplisert = lysheten vektet med alfa
            weight += a
        } }
        guard weight > 0.5 else { return nil }   // helt tomt bilde: vis reserveflisen
        let light = lum / weight > 0.62
        return light ? Analysed(image: img, r: 18 / 255, g: 18 / 255, b: 20 / 255, opaque: false)
                     : Analysed(image: img, r: 0xf4 / 255, g: 0xf2 / 255, b: 0xee / 255, opaque: false)
    }
}

/// Real cover art by key (track title, album or playlist name, station). Filled from the amplifier status (cover_url),
/// Lyrion, Navidrome and Plex. In memory only: the URLs carry tokens and change with the cover hash.
@Observable
final class CoverStore {
    static let shared = CoverStore()
    private(set) var urls: [String: URL] = [:]

    func url(for key: String) -> URL? { key.isEmpty ? nil : urls[key] }

    func set(_ key: String, _ url: String) {
        guard !key.isEmpty, !url.isEmpty, let u = URL(string: url), urls[key] != u else { return }
        urls[key] = u
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

    /// Station image from the amplifier's favourites (only when no logo is known yet).
    func adopt(_ name: String, _ url: String) {
        guard !url.isEmpty, url.lowercased().hasPrefix("https"), SK.nrkAsset[name] == nil, (urls[name] ?? "").isEmpty else { return }
        store(name, url)
    }

    /// Logo servert av Skjold selv (/api/logo): går foran Radio Browser-gjetninger (men de innebygde NRK-logoene beholdes).
    func device(_ name: String, _ url: String) {
        guard !url.isEmpty, SK.nrkAsset[name] == nil, urls[name] != url else { return }
        store(name, url)
    }

    private func store(_ name: String, _ url: String) {
        urls[name] = url
        UserDefaults.standard.set(urls, forKey: key)
    }
}
