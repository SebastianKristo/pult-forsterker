import Foundation
import UIKit
import WidgetKit
import ActivityKit
import CryptoKit

/// Appen → widgets og Live Activity. Kalles fra `AppModel.apply(_:host:)` for den aktive enheten.
/// Skriver siste status til App Group, laster widgetene på nytt ved låtbytte/spill-pause (volum maks hvert 5. s),
/// lagrer omslaget som liten JPEG og starter/oppdaterer/avslutter Live Activity.
@MainActor
final class WidgetBridge {
    static let shared = WidgetBridge()

    private var lastSig = ""
    private var lastVolume = -1
    private var lastReload = Date.distantPast
    private var coverSource = ""
    private var activity: Activity<SkjoldNowPlayingAttributes>? = Activity<SkjoldNowPlayingAttributes>.activities.first
    private var activityState: SkjoldNowPlayingAttributes.ContentState?
    private var endTask: Task<Void, Never>?

    func update(_ st: DevStatus, host: String, coverURL: String, presets: [String]) {
        var s = SkjoldShared.load()
        s.host = host
        s.room = st.name.isEmpty ? "Skjold" : st.name
        s.source = SharedNowPlaying.sourceLabel(st.input)
        let station = st.radioNow?.name ?? ""
        if st.input == "radio" && !station.isEmpty {
            if st.title.isEmpty {
                s.title = station
                let now = st.radioNow?.now ?? ""
                s.subtitle = now.isEmpty ? "Radio" : now
            } else {
                s.title = st.title
                s.subtitle = [st.artist, station].filter { !$0.isEmpty }.joined(separator: " · ")
            }
        } else {
            s.title = st.title.isEmpty ? s.source : st.title
            s.subtitle = st.artist
        }
        s.playing = st.playing
        s.volume = st.volume
        s.activePreset = st.preset
        if !presets.isEmpty { s.presets = presets }
        s.updated = Date()
        SkjoldShared.save(s)

        let sig = [s.title, s.subtitle, s.source, s.room, String(s.playing), s.presets.joined(separator: "|")].joined(separator: "\u{1}")
        let volumeChanged = s.volume != lastVolume
        if sig != lastSig {
            lastSig = sig
            reload()
        } else if volumeChanged && Date().timeIntervalSince(lastReload) > 5 {
            reload()
        }
        lastVolume = s.volume

        var img = coverURL
        if img.isEmpty, let rn = st.radioNow {   // kanallogo fra Skjold (/api/logo) før Lyrions bildeadresse
            img = rn.logo.isEmpty ? rn.image : DeviceLink.shared.coverURL(rn.logo, on: host)
        }
        updateCover(img)
        updateActivity(s)
    }

    private func reload() {
        lastReload = Date()
        SkjoldShared.reloadWidgets()
    }

    // MARK: Omslag

    /// Sangomslag, ellers kanallogo (/api/logo, samme opphav som API-et). Bildet lagres som eget lite JPEG per
    /// kilde i App Group; nøkkelen settes i delt status og i Live Activity-tilstanden, så både widgets og
    /// aktiviteten (låseskjerm og Dynamic Island) tegnes på nytt med riktig bilde.
    private func updateCover(_ src: String) {
        guard src != coverSource else { return }
        coverSource = src
        guard src.lowercased().hasPrefix("http"), let url = URL(string: src) else {
            SkjoldShared.mutate { $0.hasCover = false; $0.coverKey = nil }
            reload()
            refreshActivity()
            return
        }
        let key = Self.key(src)
        if let f = SkjoldShared.coverFileFor(key: key), FileManager.default.fileExists(atPath: f.path) {   // allerede hentet
            SkjoldShared.mutate { $0.hasCover = true; $0.coverKey = key }
            reload()
            refreshActivity()
            return
        }
        Task { [weak self] in
            let jpeg = await Self.thumbnail(url)
            guard let self, self.coverSource == src else { return }
            if let jpeg, let f = SkjoldShared.coverFileFor(key: key), (try? jpeg.write(to: f, options: .atomic)) != nil {
                if let old = SkjoldShared.coverFile { try? jpeg.write(to: old, options: .atomic) }   // eldre widgets
                SkjoldShared.mutate { $0.hasCover = true; $0.coverKey = key }
                Self.prune(keep: key)
            } else {
                SkjoldShared.mutate { $0.hasCover = false; $0.coverKey = nil }
            }
            self.reload()
            self.refreshActivity()
        }
    }

    nonisolated private static func key(_ src: String) -> String {
        Insecure.SHA1.hash(data: Data(src.utf8)).prefix(8).map { String(format: "%02x", $0) }.joined()
    }

    /// Behold bare de siste omslagene i den delte containeren.
    nonisolated private static func prune(keep: String, max: Int = 8) {
        guard let dir = SkjoldShared.coverFile?.deletingLastPathComponent(),
              let files = try? FileManager.default.contentsOfDirectory(at: dir, includingPropertiesForKeys: [.contentModificationDateKey])
        else { return }
        let covers = files.filter { $0.lastPathComponent.hasPrefix("cover-") && $0.pathExtension == "jpg" }
        guard covers.count > max else { return }
        let sorted = covers.sorted {
            let a = (try? $0.resourceValues(forKeys: [.contentModificationDateKey]).contentModificationDate) ?? .distantPast
            let b = (try? $1.resourceValues(forKeys: [.contentModificationDateKey]).contentModificationDate) ?? .distantPast
            return a > b
        }
        for f in sorted.dropFirst(max) where !f.lastPathComponent.contains(keep) { try? FileManager.default.removeItem(at: f) }
    }

    private func refreshActivity() {
        updateActivity(SkjoldShared.load())
    }

    nonisolated private static func thumbnail(_ url: URL) async -> Data? {
        guard let (d, _) = try? await URLSession.shared.data(from: url), let img = UIImage(data: d) else { return nil }
        let side: CGFloat = 240   // lite nok for Live Activity (bilder der må være små), skarpt nok for widgets
        let fmt = UIGraphicsImageRendererFormat()
        fmt.scale = 1   // ellers 3× (720 px) – for stort for Live Activity
        let r = UIGraphicsImageRenderer(size: CGSize(width: side, height: side), format: fmt)
        let out = r.image { _ in
            let w = img.size.width, h = img.size.height
            let scale = max(side / max(w, 1), side / max(h, 1))
            let size = CGSize(width: w * scale, height: h * scale)
            img.draw(in: CGRect(x: (side - size.width) / 2, y: (side - size.height) / 2, width: size.width, height: size.height))
        }
        return out.jpegData(compressionQuality: 0.8)
    }

    // MARK: Live Activity

    private func updateActivity(_ s: SharedNowPlaying) {
        guard ActivityAuthorizationInfo().areActivitiesEnabled else { return }
        let state = SkjoldNowPlayingAttributes.ContentState(title: s.title, subtitle: s.subtitle, source: s.source,
                                                            playing: s.playing, volume: s.volume,
                                                            cover: s.hasCover ? s.coverKey : nil)
        if s.playing {
            endTask?.cancel()
            endTask = nil
            if let a = activity {
                guard state != activityState else { return }
                activityState = state
                Task { await a.update(ActivityContent(state: state, staleDate: nil)) }
            } else if UIApplication.shared.applicationState == .active {
                let attrs = SkjoldNowPlayingAttributes(room: s.room)
                activity = try? Activity.request(attributes: attrs, content: ActivityContent(state: state, staleDate: nil), pushType: nil)
                activityState = state
            }
        } else if let a = activity {
            if state != activityState {
                activityState = state
                Task { await a.update(ActivityContent(state: state, staleDate: nil)) }
            }
            guard endTask == nil else { return }
            // Pause: la aktiviteten stå et par minutter (rask gjenopptak), så avslutt.
            endTask = Task { [weak self] in
                try? await Task.sleep(for: .seconds(120))
                guard !Task.isCancelled else { return }
                await a.end(ActivityContent(state: state, staleDate: nil), dismissalPolicy: .immediate)
                self?.activity = nil
                self?.activityState = nil
                self?.endTask = nil
            }
        }
    }
}
