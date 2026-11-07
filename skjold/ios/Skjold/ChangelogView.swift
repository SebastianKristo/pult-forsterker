import SwiftUI
import UIKit

/// GET /api/changelog: release-notater fra GitHub Releases (cachet på enheten, virker uten nett).
struct ReleaseNote: Identifiable, Equatable {
    var id: String { tag }
    var tag: String
    var body: String
    var date: String
    var prerelease: Bool

    init?(_ j: [String: Any]) {
        guard let t = j["tag"] as? String else { return nil }
        tag = t; body = (j["body"] as? String) ?? ""; date = (j["date"] as? String) ?? ""; prerelease = (j["prerelease"] as? Bool) ?? false
    }
}

struct ChangelogData {
    var current: String?
    var notes: ReleaseNote?
    var history: [ReleaseNote] = []
    var offline = false

    static func fetch(host: String) async -> ChangelogData? {
        guard let url = Net.url(host, "/api/changelog"), let (d, code) = await Net.data(url, timeout: 12), code < 300,
              let j = try? JSONSerialization.jsonObject(with: d) as? [String: Any] else { return nil }
        var c = ChangelogData()
        c.current = j["current"] as? String
        c.notes = (j["notes"] as? [String: Any]).flatMap(ReleaseNote.init)
        c.history = ((j["history"] as? [[String: Any]]) ?? []).compactMap(ReleaseNote.init)
        c.offline = (j["offline"] as? Bool) ?? false
        return c
    }

    /// «Hva er nytt» én gang etter versjonsbytte. Første gang appen ser enheten vises ingenting.
    /// Sist «Hva er nytt» ble sjekket per enhet. Visningen kan bli laget på nytt ofte (statusoppdateringer, rombytte),
    /// og et tomt/feilende svar ga da en ny forespørsel hver gang. Sjekk høyst hver 6. time per enhet.
    @MainActor private static var lastCheck: [String: Date] = [:]

    @MainActor static func whatsNew(host: String) async -> ReleaseNote? {
        if let t = lastCheck[host], Date().timeIntervalSince(t) < 6 * 3600 { return nil }
        lastCheck[host] = Date()
        guard let c = await fetch(host: host), let cur = c.current, let n = c.notes else { return nil }
        let key = "skjold-seenRelease-" + host
        guard let seen = UserDefaults.standard.string(forKey: key) else { UserDefaults.standard.set(cur, forKey: key); return nil }
        return seen == cur ? nil : n
    }

    static func markSeen(_ tag: String, host: String) { UserDefaults.standard.set(tag, forKey: "skjold-seenRelease-" + host) }
}

/// Enkel markdown: ## overskrift, * / - punkt, ellers avsnitt.
struct ReleaseNotesText: View {
    let text: String
    var bodyView: some View {
        let lines = text.split(separator: "\n").map(String.init).filter { !$0.trimmingCharacters(in: .whitespaces).isEmpty }
        return VStack(alignment: .leading, spacing: 5) {
            if lines.isEmpty { Text("Ingen notater for denne versjonen.").sora(13, .regular, .muted) }
            ForEach(Array(lines.enumerated()), id: \.offset) { _, raw in
                let l = raw.replacingOccurrences(of: "**", with: "").replacingOccurrences(of: "`", with: "")
                if l.hasPrefix("#") {
                    Text(l.drop(while: { $0 == "#" || $0 == " " })).sora(14, .semibold).padding(.top, 6)
                } else if let r = l.range(of: #"^\s*[*-]\s+"#, options: .regularExpression) {
                    HStack(alignment: .firstTextBaseline, spacing: 6) { Text("•").sora(13); Text(String(l[r.upperBound...])).sora(13) }
                } else {
                    Text(l).sora(13, .regular, .ink2)
                }
            }
        }
    }
    var body: some View { bodyView }
}

/// Innstillinger → Endringslogg.
struct ChangelogView: View {
    @Environment(AppModel.self) private var m
    @State private var data: ChangelogData? = nil
    @State private var loading = true

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            if loading { Text("Henter …").sora(13, .regular, .muted) }
            else if let d = data {
                if d.offline { Text("Uten nett – viser lagrede notater.").sora(12, .regular, Color(hex: 0xc9b48a)) }
                if d.history.isEmpty { Text("Ingen release-notater ennå.").sora(13, .regular, .muted) }
                ForEach(d.history) { r in
                    VStack(alignment: .leading, spacing: 6) {
                        HStack {
                            Text(r.tag.replacingOccurrences(of: "skjold-", with: "") + (r.tag == d.current ? " · installert" : "") + (r.prerelease ? " · beta" : "")).sora(15, .semibold)
                            Spacer()
                            Text(String(r.date.prefix(10))).mono(11)
                        }
                        ReleaseNotesText(text: r.body)
                    }
                    .padding(14)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .skBox(Color(hex: 0x141415), Color(hex: 0x232325), radius: 14)
                }
            } else { Text("Endringsloggen krever nyere Skjold-programvare.").sora(13, .regular, .muted) }
        }
        .task {
            if let h = m.activeHost { data = await ChangelogData.fetch(host: h) }
            loading = false
        }
    }
}

/// Arket «Hva er nytt» (vises fra ContentView).
struct WhatsNewSheet: View {
    let note: ReleaseNote
    let done: () -> Void
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                Text(note.tag.replacingOccurrences(of: "skjold-", with: "")).mono(12, V4.goldDark)
                Text("Hva er nytt").sora(22, .semibold)
                ReleaseNotesText(text: note.body)
                Button { done() } label: {
                    Text("OK").sora(15, .semibold, .black).frame(maxWidth: .infinity).frame(height: 46)
                        .background(Capsule().fill(V4.goldDark))
                }.buttonStyle(.plain).padding(.top, 8)
            }.padding(22)
        }
        .presentationDetents([.medium, .large])
        .background(Color(hex: 0x141415))
    }
}

/// Innstillinger → Radioprogrammer: planlagte programopptak (episoder) fra /api/recordings. Planlegging gjøres i web-appen.
struct RecordedProgramsView: View {
    @Environment(AppModel.self) private var m
    @State private var progs: [[String: Any]] = []
    @State private var feed = ""
    @State private var loaded = false

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Planlegg opptak (f.eks. «Nitimen hver lørdag») under Plugins → Radioopptak i web-appen. Episodene vises her og som podkast.")
                .sora(12.5, .regular, .muted)
            if !feed.isEmpty {
                HStack { Text(feed).mono(11, V4.gold).lineLimit(2); Spacer(); Button { UIPasteboard.general.string = feed } label: { Text("Kopier").sora(13, .regular, V4.gold) }.buttonStyle(.plain) }
            }
            if loaded && progs.isEmpty { Text("Ingen programmer tatt opp ennå.").sora(13, .regular, .muted) }
            ForEach(Array(progs.enumerated()), id: \.offset) { _, p in
                let id = p["id"] as? String ?? ""
                VStack(alignment: .leading, spacing: 6) {
                    Text((p["name"] as? String ?? "") + " · " + (p["channel"] as? String ?? "")).sora(14, .semibold)
                    ForEach(Array(((p["episodes"] as? [[String: Any]]) ?? []).enumerated()), id: \.offset) { _, e in
                        HStack {
                            Text(Self.day(e["t"] as? Double ?? 0) + " · \(Int((e["dur"] as? Double ?? 0) / 60)) min").sora(13, .regular, .ink2)
                            Spacer()
                            Button { Task { await play(id, e) } } label: { Text("Spill").sora(13, .regular, V4.gold) }.buttonStyle(.plain)
                        }
                    }
                }
                .padding(14).frame(maxWidth: .infinity, alignment: .leading)
                .skBox(Color(hex: 0x141415), Color(hex: 0x232325), radius: 14)
            }
        }
        .task { await load() }
    }

    static func day(_ t: Double) -> String {
        let f = DateFormatter(); f.locale = Locale(identifier: "nb_NO"); f.dateFormat = "EEE d. MMM"
        return f.string(from: Date(timeIntervalSince1970: t))
    }

    private func load() async {
        defer { loaded = true }
        guard let h = m.activeHost, let url = Net.url(h, "/api/recordings"), let (d, code) = await Net.data(url, timeout: 8), code < 300,
              let j = try? JSONSerialization.jsonObject(with: d) as? [String: Any] else { return }
        progs = (j["programs"] as? [[String: Any]]) ?? []
        feed = (j["feed"] as? String) ?? ""
    }

    private func play(_ prog: String, _ e: [String: Any]) async {
        guard let h = m.activeHost, let url = Net.url(h, "/api/recordings"),
              let body = try? JSONSerialization.data(withJSONObject: ["play_episode": ["prog": prog, "file": e["file"] ?? "", "title": e["title"] ?? ""]]) else { return }
        _ = await Net.data(url, method: "POST", body: body, timeout: 8)
    }
}
