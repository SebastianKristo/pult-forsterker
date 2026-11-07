import Foundation
import WatchConnectivity

/// Telefonens side av Apple Watch-appen (SkjoldWatch).
/// - Sender kjente Skjold-enheter og aktivt rom til klokka (applicationContext), så klokka kan snakke direkte med Skjold.
/// - Videresender kommandoer fra klokka når den ikke når Skjold selv (utenfor hjemmenettet, eller bare Bluetooth til telefonen):
///   klokka sender {host, path, method, body} som Data, telefonen gjør kallet og svarer med svaret fra Skjold.
final class WatchBridge: NSObject, WCSessionDelegate {
    static let shared = WatchBridge()
    private var timer: Timer?
    private var lastContext = ""

    func start() {
        guard WCSession.isSupported() else { return }
        let s = WCSession.default
        s.delegate = self
        s.activate()
        timer?.invalidate()
        timer = Timer.scheduledTimer(withTimeInterval: 15, repeats: true) { _ in
            Task { @MainActor in WatchBridge.shared.push() }
        }
    }

    /// Kjente enheter og aktiv enhet fra appens lagring → klokka (bare når noe er endret).
    func push() {
        guard WCSession.isSupported() else { return }
        let s = WCSession.default
        guard s.activationState == .activated, s.isPaired, s.isWatchAppInstalled else { return }
        let ud = UserDefaults.standard
        var rooms: [[String: String]] = []
        if let d = ud.data(forKey: "skjold-known"), let arr = try? JSONSerialization.jsonObject(with: d) as? [[String: Any]] {
            for k in arr {
                let host = (k["host"] as? String) ?? ""
                if !host.isEmpty { rooms.append(["host": host, "name": (k["name"] as? String) ?? host, "product": (k["product"] as? String) ?? ""]) }
            }
        }
        let active = ud.string(forKey: "skjold-host") ?? ""
        let ctx: [String: Any] = ["rooms": rooms, "active": active]
        let key = "\(rooms)|\(active)"
        guard key != lastContext else { return }
        lastContext = key
        try? s.updateApplicationContext(ctx)
    }

    // MARK: WCSessionDelegate

    nonisolated func session(_ session: WCSession, activationDidCompleteWith activationState: WCSessionActivationState, error: Error?) {
        Task { @MainActor in WatchBridge.shared.lastContext = ""; WatchBridge.shared.push() }
    }
    nonisolated func sessionDidBecomeInactive(_ session: WCSession) {}
    nonisolated func sessionDidDeactivate(_ session: WCSession) { WCSession.default.activate() }
    nonisolated func sessionWatchStateDidChange(_ session: WCSession) {
        Task { @MainActor in WatchBridge.shared.lastContext = ""; WatchBridge.shared.push() }
    }

    /// Kommando fra klokka: {"host","path","method","body"(base64)} → svar fra Skjold (eller tom Data ved feil).
    nonisolated func session(_ session: WCSession, didReceiveMessageData messageData: Data, replyHandler: @escaping (Data) -> Void) {
        guard let j = (try? JSONSerialization.jsonObject(with: messageData)) as? [String: Any],
              let host = j["host"] as? String, let path = j["path"] as? String,
              let url = Net.url(host, path) else { replyHandler(Data()); return }
        let method = (j["method"] as? String) ?? "GET"
        let body = (j["body"] as? String).flatMap { Data(base64Encoded: $0) }
        Task.detached {
            let r = await Net.data(url, method: method, body: body, timeout: 8)
            replyHandler(r?.0 ?? Data())
        }
    }
}
