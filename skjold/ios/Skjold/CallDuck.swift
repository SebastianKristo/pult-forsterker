import CallKit
import Foundation

/// «Senk musikken når telefonen ringer» (iOS): CXCallObserver merker innkommende/pågående samtaler og ber Skjold
/// senke volumet (POST /api/duck {kilde: telefon}) og løfte det igjen når samtalen er over ({slutt: true}).
/// iOS lar bare appen få samtalehendelser mens den kjører (forgrunn eller kort i bakgrunnen), så dette virker
/// når appen er åpen eller nylig brukt – ikke når den er lukket helt.
nonisolated final class CallDuck: NSObject, CXCallObserverDelegate, @unchecked Sendable {
    static let shared = CallDuck()
    private let observer = CXCallObserver()
    private var ducked = false
    private var started = false

    static var enabled: Bool {
        get { UserDefaults.standard.bool(forKey: "callDuck") }
        set { UserDefaults.standard.set(newValue, forKey: "callDuck"); if newValue { shared.start() } }
    }

    func start() {
        guard !started, Self.enabled else { return }
        started = true
        observer.setDelegate(self, queue: nil)
    }

    func callObserver(_ callObserver: CXCallObserver, callChanged call: CXCall) {
        guard Self.enabled else { return }
        let busy = callObserver.calls.contains { !$0.hasEnded }
        if busy == ducked { return }
        ducked = busy
        Task.detached {
            let body: [String: Any] = busy ? ["kilde": "telefon"] : ["kilde": "telefon", "slutt": true]
            _ = await SiriSkjold.post(SiriSkjold.activeHost, "/api/duck", body)
        }
    }
}
