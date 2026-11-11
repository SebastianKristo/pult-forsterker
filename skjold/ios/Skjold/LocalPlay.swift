import AVFoundation
import Observation

/// «Denne iPhonen»: spill det Skjold spiller på telefonen i stedet for i rommet.
/// Skjold fortsetter å spille, men dempet (POST /api/mute), så kø, neste/forrige, pause og spoling virker som før.
/// Telefonen speiler strømmen fra status `listen` (Skjolds /api/stream-proxy) og holder seg i takt med posisjonen.
/// Tilbake til rommet: lyden slås på igjen i Skjold, fra samme sted i låten.
@Observable @MainActor
final class LocalPlay {
    static let shared = LocalPlay()

    private(set) var on = false
    private(set) var vol: Double = {
        let v = UserDefaults.standard.double(forKey: "skjold-local-vol")
        return v > 0 ? v : 0.8
    }()

    @ObservationIgnored private var player: AVPlayer?
    @ObservationIgnored private var cur = ""
    @ObservationIgnored private var wasMuted = false
    @ObservationIgnored private var host = ""
    @ObservationIgnored private weak var m: AppModel?

    /// Kan det som spilles nå spilles på telefonen? (Radio og bibliotekene – ikke AirPlay, Blåtann, Spotify eller AUX.)
    private static let mutedKey = "skjold-local-muted-host"

    func can(_ m: AppModel) -> Bool { m.live && !(m.dev?.listen.isEmpty ?? true) }

    func start(_ m: AppModel) {
        guard let d = m.dev, !d.listen.isEmpty, let h = m.activeHost else { Haptics.warning(); return }
        self.m = m
        let session = AVAudioSession.sharedInstance()
        try? session.setCategory(.playback, mode: .default)
        try? session.setActive(true)
        on = true
        host = h
        wasMuted = d.mute
        cur = ""
        sync(d, host: h)
        if !wasMuted {
            m.devSend("/api/mute", ["mute": true])
            UserDefaults.standard.set(h, forKey: Self.mutedKey)   // huskes til lyden er slått på igjen (se sync)
        }
        Haptics.success()
    }

    func stop() {
        guard on else { return }
        on = false
        let pos = player?.currentTime().seconds
        player?.pause()
        player?.replaceCurrentItem(with: nil)
        cur = ""
        if let m, let d = m.dev {
            if d.duration > 0, let pos, pos.isFinite, abs(Double(d.position) - pos) > 3 { m.devSend("/api/seek", ["pos": Int(pos)], on: host) }
            if !wasMuted { m.devSend("/api/mute", ["mute": false], on: host) }
        }
        UserDefaults.standard.removeObject(forKey: Self.mutedKey)
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
    }

    func setVol(_ v: Double) {
        vol = max(0, min(1, v))
        player?.volume = Float(vol)
        UserDefaults.standard.set(vol, forKey: "skjold-local-vol")
    }

    /// Kalles for hver ny status fra det aktive rommet: ny strøm, pause/spill og posisjon.
    func sync(_ d: DevStatus, host: String) {
        // Appen ble lukket mens rommet var dempet av «Denne iPhonen»: slå lyden på igjen første gang vi ser rommet
        if !on, d.mute, UserDefaults.standard.string(forKey: Self.mutedKey) == host {
            UserDefaults.standard.removeObject(forKey: Self.mutedKey)
            Task { _ = await DeviceLink.shared.sendRaw("/api/mute", DeviceLink.json(["mute": false]), on: host, timeout: 6) }
        }
        guard on else { return }
        guard host == self.host else { stop(); return }   // byttet rom: lyden tilbake til rommet den kom fra
        guard !d.listen.isEmpty, let url = Net.url(host, d.listen) else { stop(); return }
        let track = d.duration > 0
        if d.listen != cur {
            cur = d.listen
            let item = AVPlayerItem(url: url)
            if let p = player { p.replaceCurrentItem(with: item) } else { player = AVPlayer(playerItem: item) }
            if track && d.position > 1 { player?.seek(to: CMTime(seconds: Double(d.position), preferredTimescale: 600)) }
        } else if track, let p = player {
            let t = p.currentTime().seconds
            if t.isFinite && abs(t - Double(d.position)) > 4 {
                p.seek(to: CMTime(seconds: Double(d.position), preferredTimescale: 600))
            }
        }
        player?.volume = Float(vol)
        if d.playing { player?.play() } else { player?.pause() }
    }
}
