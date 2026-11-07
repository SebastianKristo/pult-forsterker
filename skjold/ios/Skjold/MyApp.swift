import SwiftUI

@main struct MyApp: App {
    @State private var model = AppModel()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(model)
                .task { WatchBridge.shared.start() }   // Apple Watch-appen: rom til klokka, kommandoer fra klokka
        }
    }
}
