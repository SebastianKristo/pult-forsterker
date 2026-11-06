import SwiftUI
import AVFoundation

/// «Høyttalerprofil» (Skjold Sertifisert): søk i delte profiler i Skjold Cloud og ta én i bruk, eller mål høyttalerne
/// med telefonens mikrofon (gated, ≈ 1 m foran). Analysen og EQ-tilpasningen gjøres på Skjold (/api/speakers/*).
@MainActor @Observable
final class SpeakerModel {
    struct Hit: Identifiable { let id: String; let name: String; let count: Int; let certified: Bool }
    var current = ""
    var certified = false
    var enabled = false
    var filters = 0
    var hits: [Hit] = []
    var status = ""
    var busy = false
    var measured = 0
    var curve: [RoomEQPoint] = []
    var after: [RoomEQPoint] = []
    private let session = UUID().uuidString
    private let recorder = RoomEQRecorder()

    private func obj(_ d: Data?) -> [String: Any] { (d.flatMap { try? JSONSerialization.jsonObject(with: $0) } as? [String: Any]) ?? [:] }

    private func apply(_ o: [String: Any]) {
        let p = o["profile"] as? [String: Any] ?? [:]
        current = [p["brand"] as? String, p["model"] as? String].compactMap { $0 }.joined(separator: " ")
        certified = p["certified"] as? Bool ?? false
        enabled = o["enabled"] as? Bool ?? false
        filters = (o["active_filters"] as? [Any])?.count ?? 0
    }

    func load(host: String?) async {
        guard let host else { return }
        apply(obj(await DeviceLink.shared.get("/api/speakers", on: host)))
    }

    func search(_ q: String, host: String?) async {
        guard let host else { return }
        let enc = q.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? ""
        let o = obj(await DeviceLink.shared.get("/api/speakers/search?q=\(enc)", on: host, timeout: 10))
        hits = (o["results"] as? [[String: Any]] ?? []).map {
            Hit(id: $0["id"] as? String ?? "", name: "\($0["merke"] as? String ?? "") \($0["modell"] as? String ?? "")",
                count: ($0["antall"] as? NSNumber)?.intValue ?? 1, certified: $0["sertifisert"] as? Bool ?? false)
        }
        status = hits.isEmpty ? "Ingen treff – mål høyttalerne selv og del profilen." : ((o["offline"] as? Bool ?? false) ? "Uten nett: viser bare profiler brukt før." : "")
    }

    func use(_ id: String, host: String?) async {
        guard let host else { return }
        let d = await DeviceLink.shared.send("/api/speakers", ["use": id], on: host, timeout: 12)
        if d == nil { status = "Fikk ikke hentet profilen." } else { apply(obj(d)); Haptics.success() }
    }

    func toggle(host: String?) async {
        guard let host else { return }
        apply(obj(await DeviceLink.shared.send("/api/speakers", ["enabled": !enabled], on: host)))
    }

    func measure(host: String?) async {
        guard let host else { return }
        guard await AVAudioApplication.requestRecordPermission() else { status = "Skjold trenger mikrofontilgang."; return }
        busy = true; status = "Måler … vær stille"
        defer { busy = false }
        do { try recorder.start() } catch { status = "Fikk ikke startet mikrofonen."; return }
        _ = await DeviceLink.shared.send("/api/roomeq/sweep", ["level": 0.4, "delay": 1.0], on: host)
        try? await Task.sleep(for: .seconds(8.5))
        let wav = recorder.stop()
        let path = "/api/speakers/measure?session=\(session)&mode=gated&reset=\(measured == 0 ? 1 : 0)"
        guard let url = Net.url(host, path), let (d, code) = await Net.data(url, method: "POST", body: wav, timeout: 60, headers: ["Content-Type": "audio/wav"]) else {
            status = "Fikk ikke kontakt med Skjold."; return
        }
        let o = obj(d)
        if code >= 300 { status = o["error"] as? String ?? "Målingen feilet."; return }
        let p = o["profile"] as? [String: Any] ?? [:]
        curve = Self.pts(p["curve"]); after = Self.pts(p["after"])
        measured = (o["gated"] as? NSNumber)?.intValue ?? measured + 1
        let pt = o["point"] as? [String: Any] ?? [:]
        status = (pt["clipped"] as? Bool ?? false) ? "Overstyrt – skru ned og mål igjen." : "Score \((p["score"] as? NSNumber)?.intValue ?? 0). Mål gjerne 3–5 ganger fra litt ulike vinkler."
    }

    func save(brand: String, model: String, share: Bool, host: String?) async {
        guard let host else { return }
        let d = await DeviceLink.shared.send("/api/speakers/save", ["session": session, "brand": brand, "model": model, "share": share, "apply": true], on: host, timeout: 20)
        if d == nil { status = "Fikk ikke lagret – oppgi merke og modell og mål minst én gang."; return }
        measured = 0; curve = []; after = []
        status = "Lagret og i bruk."
        Haptics.success()
        await load(host: host)
    }

    static func pts(_ any: Any?) -> [RoomEQPoint] {
        (any as? [[String: Any]] ?? []).compactMap { p in
            guard let f = (p["f"] as? NSNumber)?.doubleValue, let db = (p["db"] as? NSNumber)?.doubleValue, f >= 20, f <= 20000 else { return nil }
            return RoomEQPoint(f: f, db: db)
        }
    }
}

struct V4SpeakerSheet: View {
    @Environment(AppModel.self) private var m
    @Environment(\.dismiss) private var dismiss
    @State private var model = SpeakerModel()
    @State private var q = ""
    @State private var brand = ""
    @State private var name = ""
    @State private var share = true

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                HStack {
                    Text("Høyttalerprofil").sora(24, .semibold)
                    Spacer()
                    Button { dismiss() } label: { Text("Lukk").sora(15, .regular, V4.gold) }.plain()
                }
                Text("Retter høyttalernes egen frekvensgang. Romkorreksjonen tar seg fortsatt av bassen i rommet.").sora(13, .regular, V4.muted)
                if !model.current.isEmpty {
                    HStack {
                        VStack(alignment: .leading, spacing: 3) {
                            Text(model.current).sora(15)
                            Text(model.certified ? "✓ Skjold Sertifisert · \(model.filters) filtre" : "\(model.filters) filtre").sora(12, .regular, model.certified ? V4.gold : V4.muted)
                        }
                        Spacer()
                        Toggle("", isOn: Binding(get: { model.enabled }, set: { _ in Task { await model.toggle(host: m.settingsHost) } })).labelsHidden().tint(V4.gold)
                    }
                    .padding(14).v4Card()
                }
                V4Kicker(text: "FINN PROFIL")
                HStack {
                    TextField("Merke eller modell", text: $q).textInputAutocapitalization(.never).autocorrectionDisabled()
                        .onSubmit { Task { await model.search(q, host: m.settingsHost) } }
                    Button { Task { await model.search(q, host: m.settingsHost) } } label: { Text("Søk").sora(14, .regular, V4.gold) }.plain()
                }
                .padding(12).v4Card()
                ForEach(model.hits) { h in
                    HStack {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(h.name).sora(14)
                            Text(h.certified ? "✓ Skjold Sertifisert" : "\(h.count) måling\(h.count == 1 ? "" : "er")").sora(11, .regular, h.certified ? V4.gold : V4.muted)
                        }
                        Spacer()
                        Button { Task { await model.use(h.id, host: m.settingsHost) } } label: { Text("Bruk").sora(14, .regular, V4.gold) }.plain()
                    }
                    .padding(.horizontal, 14).padding(.vertical, 10).v4Card()
                }
                V4Kicker(text: "MÅL SELV")
                Text("Spill én høyttaler. Hold telefonen 1 m foran, i høyde med diskanten og minst 1 m fra vegger og gulv. Mål 3–5 ganger fra litt ulike vinkler.").sora(12, .regular, V4.muted)
                HStack {
                    TextField("Merke", text: $brand)
                    TextField("Modell", text: $name)
                }
                .padding(12).v4Card()
                HStack(spacing: 10) {
                    Button { Task { await model.measure(host: m.settingsHost) } } label: {
                        Text(model.busy ? "Måler …" : model.measured == 0 ? "Start måling" : "Mål igjen (\(model.measured))").sora(14, .regular, V4.gold)
                            .frame(maxWidth: .infinity).padding(.vertical, 12).v4Card()
                    }
                    .plain().disabled(model.busy)
                    if model.measured > 0 {
                        Button { Task { await model.save(brand: brand, model: name, share: share, host: m.settingsHost) } } label: {
                            Text("Lagre og bruk").sora(14, .regular, V4.bg).frame(maxWidth: .infinity).padding(.vertical, 12).background(Capsule().fill(V4.gold))
                        }
                        .plain().disabled(brand.isEmpty || name.isEmpty)
                    }
                }
                Toggle(isOn: $share) { Text("Del anonymt i Skjold Cloud").sora(13) }.tint(V4.gold)
                if !model.status.isEmpty { Text(model.status).sora(12, .regular, V4.muted) }
            }
            .padding(20)
        }
        .background(V4.bg.ignoresSafeArea())
        .presentationDragIndicator(.visible)
        .task { await model.load(host: m.settingsHost) }
    }
}
