import SwiftUI

/// Skjold for Apple Watch: Spiller nå (volum med Digital Crown), Favoritter og Rom.
@main struct SkjoldWatchApp: App {
    @StateObject private var store = WatchStore()

    var body: some Scene {
        WindowGroup {
            TabView {
                NowPlayingView().tag(0)
                FavoritesView().tag(1)
                RoomsView().tag(2)
            }
            .tabViewStyle(.verticalPage)
            .environmentObject(store)
            .task { store.start() }
        }
    }
}
