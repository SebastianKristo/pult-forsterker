import SwiftUI
import UIKit

/// Hurtigvalg ved langt trykk på app-ikonet (Home Screen Quick Actions).
/// Faste: Spill/pause og Neste. Dynamiske: de to første radiofavorittene. Oppdateres når appen går i bakgrunnen.
enum QuickAction {
    static let playPause = "no.kristo.skjold.playpause"
    static let next = "no.kristo.skjold.next"
    static let favourite = "no.kristo.skjold.favourite"
    static let kassett = "no.kristo.skjold.kassett"
    static let note = Notification.Name("SkjoldQuickAction")

    /// Siste hurtigvalg som kom før appen var klar (kaldstart).
    @MainActor static var pending: UIApplicationShortcutItem?

    @MainActor static func update(favourites: [String]) {
        var items: [UIApplicationShortcutItem] = [
            UIApplicationShortcutItem(type: playPause, localizedTitle: String(localized: "Spill / pause"), localizedSubtitle: nil,
                                      icon: UIApplicationShortcutIcon(systemImageName: "playpause.fill"), userInfo: nil),
            UIApplicationShortcutItem(type: next, localizedTitle: String(localized: "Neste"), localizedSubtitle: nil,
                                      icon: UIApplicationShortcutIcon(systemImageName: "forward.fill"), userInfo: nil),
        ]
        for (i, name) in favourites.prefix(2).enumerated() {
            items.append(UIApplicationShortcutItem(type: favourite, localizedTitle: name, localizedSubtitle: String(localized: "Radiofavoritt"),
                                                   icon: UIApplicationShortcutIcon(systemImageName: "radio"),
                                                   userInfo: ["i": NSNumber(value: i)]))
        }
        UIApplication.shared.shortcutItems = items
    }

    /// Utfør et hurtigvalg på modellen.
    @MainActor static func perform(_ item: UIApplicationShortcutItem, model: AppModel) {
        switch item.type {
        case playPause: model.togglePlay()
        case next: model.next()
        case favourite:
            if let i = (item.userInfo?["i"] as? NSNumber)?.intValue, i < model.radio.count { model.playStation(i) }
        case kassett: model.showKassett = true
        default: break
        }
    }

    @MainActor static func deliver(_ item: UIApplicationShortcutItem) {
        pending = item
        NotificationCenter.default.post(name: note, object: nil)
    }
}

/// App-delegat som setter scene-delegaten (SwiftUI har ingen egen hook for hurtigvalg).
final class QuickActionAppDelegate: NSObject, UIApplicationDelegate {
    func application(_ application: UIApplication, configurationForConnecting connectingSceneSession: UISceneSession,
                     options: UIScene.ConnectionOptions) -> UISceneConfiguration {
        if let item = options.shortcutItem {   // kaldstart fra et hurtigvalg
            MainActor.assumeIsolated { QuickAction.pending = item }
        }
        let cfg = UISceneConfiguration(name: nil, sessionRole: connectingSceneSession.role)
        cfg.delegateClass = QuickActionSceneDelegate.self
        return cfg
    }
}

final class QuickActionSceneDelegate: NSObject, UIWindowSceneDelegate {
    func windowScene(_ windowScene: UIWindowScene, performActionFor shortcutItem: UIApplicationShortcutItem,
                     completionHandler: @escaping (Bool) -> Void) {
        MainActor.assumeIsolated { QuickAction.deliver(shortcutItem) }
        completionHandler(true)
    }
}
