import SwiftUI
import UIKit

// Mac-versjonen (Mac Catalyst): menylinje med avspilling og faner, tastatursnarveier som i Musikk-appen, og et vindu
// som kan gjøres stort (fanene blir sidemeny og Nå spilles et panel til høyre, som på iPad). På iPhone og iPad gjør
// dette ingenting utenom snarveiene (som også virker med tastatur på iPad).

/// Menyene «Avspilling» og «Vis». Snarveiene: mellomrom = spill/pause, ⌘→/⌘← = neste/forrige, ⌘↑/⌘↓ = volum,
/// ⌘1–⌘4 = fanene, ⌘F = søk, ⌘L = Nå spilles.
struct SkjoldCommands: Commands {
    let model: AppModel

    var body: some Commands {
        CommandMenu("Avspilling") {
            Button(model.playing ? "Pause" : "Spill av") { model.togglePlay() }
                .keyboardShortcut(.space, modifiers: [])
            Button("Neste") { model.next() }
                .keyboardShortcut(.rightArrow, modifiers: .command)
            Button("Forrige") { model.prev() }
                .keyboardShortcut(.leftArrow, modifiers: .command)
            Divider()
            Button("Volum opp") { model.setVol(min(100, model.vol + 5)) }
                .keyboardShortcut(.upArrow, modifiers: .command)
            Button("Volum ned") { model.setVol(max(0, model.vol - 5)) }
                .keyboardShortcut(.downArrow, modifiers: .command)
            Divider()
            Button(model.full ? "Lukk Nå spilles" : "Vis Nå spilles") { model.full.toggle() }
                .keyboardShortcut("l", modifiers: .command)
        }
        CommandGroup(after: .sidebar) {
            Button("Hjem") { model.tab = 0; model.full = false }.keyboardShortcut("1", modifiers: .command)
            Button("Lyd") { model.tab = 1; model.full = false }.keyboardShortcut("2", modifiers: .command)
            Button("Rom") { model.tab = 2; model.full = false }.keyboardShortcut("3", modifiers: .command)
            Button("Innstillinger") { model.tab = 3; model.setCat = -1; model.full = false }.keyboardShortcut(",", modifiers: .command)
            Divider()
        }
    }
}

/// Vinduet på Mac: minste størrelse som gir plass til sidemenyen og Nå spilles-panelet, og en tittellinje uten
/// tekst (innholdet går helt opp, som i Musikk-appen).
enum MacWindow {
    static func configure() {
        #if targetEnvironment(macCatalyst)
        for case let scene as UIWindowScene in UIApplication.shared.connectedScenes {
            scene.sizeRestrictions?.minimumSize = CGSize(width: 980, height: 640)
            scene.sizeRestrictions?.maximumSize = CGSize(width: 10_000, height: 10_000)
            if let bar = scene.titlebar {
                bar.titleVisibility = .hidden
                bar.toolbar = nil
            }
        }
        #endif
    }

    /// Kjører på Mac (Mac Catalyst) – brukes til å skjule ting som bare gir mening på telefonen.
    static var isMac: Bool {
        #if targetEnvironment(macCatalyst)
        return true
        #else
        return ProcessInfo.processInfo.isiOSAppOnMac
        #endif
    }
}
