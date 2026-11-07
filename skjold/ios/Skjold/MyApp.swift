import SwiftUI
import AppIntents

@main struct MyApp: App {
    @State private var model = AppModel()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(model)
                .task { WatchBridge.shared.start() }   // Apple Watch-appen: rom til klokka, kommandoer fra klokka
                .task { CallDuck.shared.start() }   // «Senk musikken når telefonen ringer» (hvis slått på)
                // Siri lærer navnene på favoritter og rutiner (for «Spill NRK Jazz med Skjold»)
                .task { SkjoldShortcuts.updateAppShortcutParameters() }
                // Delte kassetter: skjold://kassett/del?d=<kode> (QR/lenke fra en venn)
                .onOpenURL { url in
                    if let k = V4KassettMottaSheet.kode(fra: url) { model.kassettDel = k }
                }
        }
    }
}
