import AppIntents

/// Siri-fraser og Snarveier-appen. Bare i app-målet (ett AppShortcutsProvider per bunt, maks 10 snarveier).
/// Hver frase må inneholde \(.applicationName); maks én parameter per frase. Fraser på norsk og engelsk – Siri bruker
/// dem som passer telefonens språk. Alle intentene (også de uten frase her, f.eks. «Hva er dette?», dørklokke og
/// «Neste») finnes i Snarveier-appen.
struct SkjoldShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(intent: SpillFavorittIntent(), phrases: [
            "Spill \(\.$favoritt) med \(.applicationName)",
            "Spill \(\.$favoritt) på \(.applicationName)",
            "Sett på \(\.$favoritt) i \(.applicationName)",
            "Play \(\.$favoritt) on \(.applicationName)",
            "Spill radio med \(.applicationName)",
        ], shortTitle: "Spill favoritt", systemImageName: "radio")
        AppShortcut(intent: SpillKanalIntent(), phrases: [
            "Spill en kanal med \(.applicationName)",
            "Finn radiokanal i \(.applicationName)",
            "Play a radio station on \(.applicationName)",
        ], shortTitle: "Spill kanal", systemImageName: "antenna.radiowaves.left.and.right")
        AppShortcut(intent: KjorRutineIntent(), phrases: [
            "Kjør \(\.$rutine) i \(.applicationName)",
            "Start \(\.$rutine) med \(.applicationName)",
            "Kjør rutine i \(.applicationName)",
            "Run \(\.$rutine) on \(.applicationName)",
        ], shortTitle: "Kjør rutine", systemImageName: "sparkles")
        AppShortcut(intent: VolumOppIntent(), phrases: [
            "Skru opp volumet i \(.applicationName)",
            "Skru opp \(.applicationName)",
            "Turn up \(.applicationName)",
        ], shortTitle: "Volum opp", systemImageName: "speaker.plus")
        AppShortcut(intent: VolumNedIntent(), phrases: [
            "Skru ned volumet i \(.applicationName)",
            "Skru ned \(.applicationName)",
            "Turn down \(.applicationName)",
        ], shortTitle: "Volum ned", systemImageName: "speaker.minus")
        AppShortcut(intent: SettVolumIntent(), phrases: [
            "Sett volumet i \(.applicationName)",
            "Set the volume on \(.applicationName)",
        ], shortTitle: "Sett volum", systemImageName: "speaker.wave.2")
        AppShortcut(intent: PauseIntent(), phrases: [
            "Pause \(.applicationName)",
            "Sett \(.applicationName) på pause",
        ], shortTitle: "Pause", systemImageName: "pause.fill")
        AppShortcut(intent: SpillIntent(), phrases: [
            "Fortsett \(.applicationName)",
            "Spill musikk med \(.applicationName)",
            "Resume \(.applicationName)",
        ], shortTitle: "Spill", systemImageName: "play.fill")
        AppShortcut(intent: SpillerNaIntent(), phrases: [
            "Hva spiller på \(.applicationName)",
            "Hva spiller \(.applicationName)",
            "What's playing on \(.applicationName)",
        ], shortTitle: "Hva spiller nå", systemImageName: "music.note")
        AppShortcut(intent: SlaAvIntent(), phrases: [
            "Slå av \(.applicationName)",
            "Turn off \(.applicationName)",
        ], shortTitle: "Slå av", systemImageName: "power")
    }
}
