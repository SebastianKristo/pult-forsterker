import AppIntents

/// Siri-fraser og Snarveier-appen. Bare i app-målet (ett AppShortcutsProvider per bunt).
struct SkjoldShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(intent: SkjoldRoutineIntent(), phrases: ["Kjør rutine i \(.applicationName)", "Start rutine med \(.applicationName)"],
                    shortTitle: "Kjør rutine", systemImageName: "sparkles")
        AppShortcut(intent: SkjoldRecognizeIntent(), phrases: ["Hva spiller \(.applicationName)", "Hva er dette i \(.applicationName)"],
                    shortTitle: "Hva er dette?", systemImageName: "waveform.badge.magnifyingglass")
        AppShortcut(intent: SkjoldDoorbellIntent(), phrases: ["Ring på med \(.applicationName)"],
                    shortTitle: "Dørklokke", systemImageName: "bell")
    }
}
