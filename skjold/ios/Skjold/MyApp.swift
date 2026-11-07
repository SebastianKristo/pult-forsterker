import SwiftUI
import UIKit
import AppIntents

@main struct MyApp: App {
    @State private var model = AppModel()
    @UIApplicationDelegateAdaptor(QuickActionAppDelegate.self) private var quickDelegate
    @Environment(\.scenePhase) private var phase

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(model)
                .task { WatchBridge.shared.start() }   // Apple Watch-appen: rom til klokka, kommandoer fra klokka
                .task { CallDuck.shared.start() }   // «Senk musikken når telefonen ringer» (hvis slått på)
                // Siri lærer navnene på favoritter og rutiner (for «Spill NRK Jazz med Skjold»)
                .task { SkjoldShortcuts.updateAppShortcutParameters() }
                // Delte kassetter: skjold://kassett/del?d=<kode> (QR/lenke fra en venn)
                // Hurtigvalg fra app-ikonet (langt trykk): spill/pause, neste, radiofavoritter
                .onReceive(NotificationCenter.default.publisher(for: QuickAction.note)) { _ in
                    if let it = QuickAction.pending { QuickAction.pending = nil; QuickAction.perform(it, model: model) }
                }
                .task {
                    if let it = QuickAction.pending { QuickAction.pending = nil; QuickAction.perform(it, model: model) }
                }
                .onChange(of: phase) { _, p in
                    if p == .background { QuickAction.update(favourites: model.radio.map(\.name)) }
                }
                .onOpenURL { url in
                    if let k = V4KassettMottaSheet.kode(fra: url) { model.kassettDel = k }
                }
        }
    }
}
