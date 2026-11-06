import SwiftUI
import AVFoundation

/// Romkorreksjon med telefonens mikrofon: Skjold spiller en sweep (POST /api/roomeq/sweep), telefonen tar opp i
/// .measurement-modus (ingen AGC/støyreduksjon), opptaket analyseres på Skjold (POST /api/roomeq/analyze) og flere
/// målepunkter snittes. Forslaget (bare kutt 40–300 Hz) lagres med POST /api/plugins/roomeq.

struct RoomEQPoint: Identifiable { let id = UUID(); let f: Double; let db: Double }

struct RoomEQFilter: Identifiable {
    let id = UUID()
    let f: Double
    let q: Double
    let g: Double
    var json: [String: Any] { ["f": f, "q": q, "g": g] }
}

/// Tar opp mono fra mikrofonen med AVAudioEngine. Tap-blokken kjører på en lydtråd, derfor lås rundt bufferen.
nonisolated final class RoomEQRecorder: @unchecked Sendable {   // lydtråd + hovedtråd; samples er beskyttet av lock
    private let engine = AVAudioEngine()
    private let lock = NSLock()
    private var samples: [Float] = []
    private(set) var sampleRate: Double = 48000

    func start() throws {
        let session = AVAudioSession.sharedInstance()
        try session.setCategory(.playAndRecord, mode: .measurement, options: [.defaultToSpeaker, .mixWithOthers])
        try session.setPreferredSampleRate(48000)
        try session.setActive(true)
        let input = engine.inputNode
        let format = input.outputFormat(forBus: 0)
        sampleRate = format.sampleRate
        lock.lock(); samples.removeAll(keepingCapacity: true); lock.unlock()
        input.removeTap(onBus: 0)
        input.installTap(onBus: 0, bufferSize: 4096, format: format) { @Sendable [weak self] buffer, _ in
            self?.append(buffer)
        }
        engine.prepare()
        try engine.start()
    }

    private func append(_ buffer: AVAudioPCMBuffer) {
        guard let ch = buffer.floatChannelData else { return }
        let n = Int(buffer.frameLength)
        let first = UnsafeBufferPointer(start: ch[0], count: n)
        lock.lock()
        samples.append(contentsOf: first)
        lock.unlock()
    }

    /// Stopper og returnerer opptaket som 16-bit mono WAV.
    func stop() -> Data {
        engine.inputNode.removeTap(onBus: 0)
        engine.stop()
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
        lock.lock()
        let copy = samples
        lock.unlock()
        return Self.wav(copy, sampleRate: Int(sampleRate.rounded()))
    }

    static func wav(_ x: [Float], sampleRate: Int) -> Data {
        var pcm = Data(capacity: x.count * 2)
        for v in x {
            let c = max(-1, min(1, v))
            var s = Int16(c * 32767).littleEndian
            withUnsafeBytes(of: &s) { pcm.append(contentsOf: $0) }
        }
        var d = Data()
        func u32(_ v: UInt32) { var le = v.littleEndian; withUnsafeBytes(of: &le) { d.append(contentsOf: $0) } }
        func u16(_ v: UInt16) { var le = v.littleEndian; withUnsafeBytes(of: &le) { d.append(contentsOf: $0) } }
        d.append(contentsOf: Array("RIFF".utf8)); u32(UInt32(36 + pcm.count)); d.append(contentsOf: Array("WAVE".utf8))
        d.append(contentsOf: Array("fmt ".utf8)); u32(16); u16(1); u16(1); u32(UInt32(sampleRate)); u32(UInt32(sampleRate * 2)); u16(2); u16(16)
        d.append(contentsOf: Array("data".utf8)); u32(UInt32(pcm.count)); d.append(pcm)
        return d
    }
}

@MainActor @Observable
final class RoomEQModel {
    enum Phase: Equatable { case intro, measuring, result, error(String) }
    var phase: Phase = .intro
    var points = 0
    var before: [RoomEQPoint] = []
    var after: [RoomEQPoint] = []
    var filters: [RoomEQFilter] = []
    var status = ""
    var saved = false
    private let session = UUID().uuidString
    private let recorder = RoomEQRecorder()
    static let tips = ["Sitt der du pleier å lytte, og hold telefonen i ørehøyde med mikrofonen opp.",
                       "Flytt telefonen 50 cm til venstre.",
                       "Flytt telefonen 50 cm til høyre.",
                       "Flytt telefonen 30 cm fram.",
                       "Flytt telefonen 30 cm bak."]

    var tip: String { Self.tips[min(points, Self.tips.count - 1)] }

    func measure(host: String?) async {
        guard let host else { phase = .error("Ingen Skjold valgt."); return }
        let ok = await AVAudioApplication.requestRecordPermission()
        if !ok { phase = .error("Skjold trenger mikrofontilgang. Slå det på i Innstillinger → Skjold → Mikrofon."); return }
        phase = .measuring
        status = "Tar opp … vær stille"
        do { try recorder.start() } catch { phase = .error("Fikk ikke startet mikrofonen: \(error.localizedDescription)"); return }
        _ = await DeviceLink.shared.send("/api/roomeq/sweep", ["level": 0.5, "delay": 1.0], on: host)
        try? await Task.sleep(for: .seconds(8.5))
        let wav = recorder.stop()
        status = "Regner ut …"
        await upload(wav, host: host)
    }

    private func upload(_ wav: Data, host: String) async {
        let reset = points == 0 ? "1" : "0"
        let path = "/api/roomeq/analyze?session=\(session)&reset=\(reset)"
        guard let url = Net.url(host, path) else { phase = .error("Ugyldig adresse."); return }
        guard let (d, code) = await Net.data(url, method: "POST", body: wav, timeout: 60, headers: ["Content-Type": "audio/wav"]) else {
            phase = .error("Fikk ikke kontakt med Skjold."); return
        }
        let obj = (try? JSONSerialization.jsonObject(with: d)) as? [String: Any] ?? [:]
        if code >= 300 { phase = .error(obj["error"] as? String ?? "Analysen feilet (\(code))."); return }
        before = Self.curve(obj["curve"])
        after = Self.curve(obj["after"])
        filters = Self.filterList(obj["filters"])
        points = obj["points"] as? Int ?? points + 1
        saved = false
        status = (obj["clipped"] as? Bool ?? false) ? "Opptaket ble overstyrt – skru ned volumet litt og mål på nytt." : ""
        phase = .result
    }

    static func curve(_ any: Any?) -> [RoomEQPoint] {
        guard let arr = any as? [[String: Any]] else { return [] }
        var out: [RoomEQPoint] = []
        for p in arr {
            let f = (p["f"] as? NSNumber)?.doubleValue ?? 0
            let db = (p["db"] as? NSNumber)?.doubleValue ?? 0
            if f >= 20 && f <= 1000 { out.append(RoomEQPoint(f: f, db: db)) }
        }
        return out
    }

    static func filterList(_ any: Any?) -> [RoomEQFilter] {
        guard let arr = any as? [[String: Any]] else { return [] }
        return arr.map { p in
            RoomEQFilter(f: (p["f"] as? NSNumber)?.doubleValue ?? 0, q: (p["q"] as? NSNumber)?.doubleValue ?? 1,
                         g: (p["g"] as? NSNumber)?.doubleValue ?? 0)
        }
    }

    func save(host: String?) async {
        guard let host else { return }
        let body: [String: Any] = ["enabled": true, "filters": filters.map { $0.json }]
        let r = await DeviceLink.shared.send("/api/plugins/roomeq", body, on: host)
        saved = r != nil
        status = saved ? "Lagret. Romkorreksjonen er på." : "Fikk ikke lagret – prøv igjen."
        if saved { Haptics.success() }
    }

    func turnOff(host: String?) async {
        guard let host else { return }
        let r = await DeviceLink.shared.send("/api/plugins/roomeq", ["enabled": false], on: host)
        status = r != nil ? "Romkorreksjon er slått av." : "Fikk ikke kontakt med Skjold."
    }

    /// Høyttalerplassering (POST /api/placement/start → opptak → /api/placement/analyze → /api/placement/apply):
    /// hver høyttaler spiller en kort sweep etter tur, Skjold regner ut forsinkelse og nivå så alt treffer lytteplassen likt.
    var placementStatus = ""
    var placementBusy = false

    func measurePlacement(host: String?) async {
        guard let host else { placementStatus = "Ingen Skjold valgt."; return }
        guard await AVAudioApplication.requestRecordPermission() else { placementStatus = "Skjold trenger mikrofontilgang."; return }
        placementBusy = true; defer { placementBusy = false }
        placementStatus = "Hold telefonen der du sitter …"
        do { try recorder.start() } catch { placementStatus = "Fikk ikke startet mikrofonen."; return }
        let tRec = Date().timeIntervalSince1970
        let t1 = Date().timeIntervalSince1970
        guard let d = await DeviceLink.shared.send("/api/placement/start", [:], on: host),
              let o = (try? JSONSerialization.jsonObject(with: d)) as? [String: Any],
              let startAt = (o["start_at"] as? NSNumber)?.doubleValue, let now = (o["now"] as? NSNumber)?.doubleValue else {
            _ = recorder.stop(); placementStatus = "Fikk ikke kontakt med Skjold."; return
        }
        let t2 = Date().timeIntervalSince1970
        let n = (o["n"] as? NSNumber)?.intValue ?? 2
        let recS = (o["record_s"] as? NSNumber)?.doubleValue ?? 6
        let skip = max(0, startAt - (now - (t1 + t2) / 2) - tRec)
        try? await Task.sleep(for: .seconds(max(0, startAt - now) + recS))
        let wav = recorder.stop()
        placementStatus = "Regner ut …"
        guard let url = Net.url(host, "/api/placement/analyze?n=\(n)&skip=\(String(format: "%.3f", skip))"),
              let (rd, code) = await Net.data(url, method: "POST", body: wav, timeout: 60, headers: ["Content-Type": "audio/wav"]) else {
            placementStatus = "Analysen feilet."; return
        }
        let r = (try? JSONSerialization.jsonObject(with: rd)) as? [String: Any] ?? [:]
        if code >= 300 { placementStatus = r["error"] as? String ?? "Analysen feilet (\(code))."; return }
        let al = r["align"] as? [[String: Any]] ?? []
        let parts = al.enumerated().map { i, a in
            String(format: "#%d +%.2f ms %.1f dB", i + 1, (a["delay_ms"] as? NSNumber)?.doubleValue ?? 0, (a["gain_db"] as? NSNumber)?.doubleValue ?? 0)
        }
        _ = await DeviceLink.shared.send("/api/placement/apply", [:], on: host)
        placementStatus = ((r["warning"] as? String).map { $0 + ". " } ?? "") + "Justert: " + parts.joined(separator: " · ")
        Haptics.success()
    }

    func restart() { points = 0; before = []; after = []; filters = []; saved = false; status = ""; phase = .intro }
}

/// Skjermen «Romkorreksjon» (ark), åpnet fra Lyd-fanen og fra Innstillinger → Lyd.
struct V4RoomEQSheet: View {
    @Environment(AppModel.self) private var m
    @Environment(\.dismiss) private var dismiss
    @State private var model = RoomEQModel()

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                header
                switch model.phase {
                case .intro: intro
                case .measuring: measuring
                case .result: result
                case .error(let msg): errorView(msg)
                }
                limits
            }
            .padding(20)
        }
        .background(V4.bg.ignoresSafeArea())
        .presentationDragIndicator(.visible)
    }

    private var header: some View {
        HStack {
            Text("Romkorreksjon").sora(24, .semibold)
            Spacer()
            Button { dismiss() } label: { Text("Lukk").sora(15, .regular, V4.gold) }.plain()
        }
    }

    private var intro: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("Rommet former bassen mer enn høyttalerne gjør. Skjold spiller en glidetone, telefonen lytter, og Skjold demper topper der rommet buldrer.")
                .sora(14, .regular, V4.ink)
            stepRow(1, "Gjør rommet stille, og skru volumet på Skjold til vanlig lyttenivå.")
            stepRow(2, "Sitt der du lytter, med telefonen i ørehøyde.")
            stepRow(3, "Mål 3–5 punkter rundt lytteplassen. Snittet blir mest riktig.")
            primary("Start måling") { Task { await model.measure(host: m.settingsHost) } }
            secondary(model.placementBusy ? "Måler plassering …" : "Mål høyttalerplassering") { Task { await model.measurePlacement(host: m.settingsHost) } }
                .disabled(model.placementBusy)
            if !model.placementStatus.isEmpty { Text(model.placementStatus).sora(13, .regular, V4.muted) }
        }
        .padding(16).v4Card()
    }

    private var measuring: some View {
        VStack(alignment: .leading, spacing: 12) {
            V4Kicker(text: "PUNKT \(model.points + 1)")
            Text(model.tip).sora(15, .regular, V4.ink)
            HStack(spacing: 10) {
                ProgressView().tint(V4.gold)
                Text(model.status).sora(13, .regular, V4.muted)
            }
        }
        .padding(16).v4Card()
    }

    private var result: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                V4Kicker(text: "\(model.points) PUNKT\(model.points == 1 ? "" : "ER")")
                Spacer()
                legend(V4.muted, "Før"); legend(V4.gold, "Etter")
            }
            RoomEQChart(before: model.before, after: model.after).frame(height: 190)
            Text(filterSummary).sora(13, .regular, V4.muted)
            if !model.status.isEmpty { Text(model.status).sora(13, .regular, model.saved ? V4.green : V4.gold) }
            if model.points < 5 {
                Text("Neste: " + model.tip).sora(13, .regular, V4.ink)
                secondary("Mål et punkt til") { Task { await model.measure(host: m.settingsHost) } }
            }
            primary(model.saved ? "Lagret" : "Lagre korreksjon") { Task { await model.save(host: m.settingsHost) } }
                .disabled(model.filters.isEmpty || model.saved)
            HStack(spacing: 10) {
                secondary("Start på nytt") { model.restart() }
                secondary("Slå av romkorreksjon") { Task { await model.turnOff(host: m.settingsHost) } }
            }
        }
        .padding(16).v4Card()
    }

    private var filterSummary: String {
        if model.filters.isEmpty { return "Rommet er jevnt i bassen – ingen kutt trengs." }
        let parts: [String] = model.filters.map { f in
            let hz = Int(f.f.rounded())
            let db = String(format: "%.1f", f.g)
            return "\(hz) Hz \(db) dB"
        }
        return "\(model.filters.count) kutt: " + parts.joined(separator: " · ")
    }

    private func errorView(_ msg: String) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(msg).sora(14, .regular, V4.ink)
            primary("Prøv igjen") { model.phase = model.points > 0 ? .result : .intro }
        }
        .padding(16).v4Card()
    }

    private var limits: some View {
        Text("Telefonmikrofoner er unøyaktige under 40 Hz og over ca. 10 kHz. Derfor retter Skjold bare 40–300 Hz, og bare med kutt – aldri mer enn 10 dB.")
            .sora(12, .regular, V4.muted)
    }

    private func stepRow(_ n: Int, _ t: String) -> some View {
        HStack(alignment: .top, spacing: 10) {
            Text("\(n)").mono(11, V4.gold).frame(width: 22, height: 22)
                .overlay(Circle().strokeBorder(V4.goldDark, lineWidth: 1))
            Text(t).sora(13, .regular, V4.ink)
        }
    }

    private func legend(_ c: Color, _ t: String) -> some View {
        HStack(spacing: 5) { Capsule().fill(c).frame(width: 12, height: 3); Text(t).mono(10, V4.muted) }
    }

    private func primary(_ t: String, _ action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(t).sora(15, .semibold, V4.bg).frame(maxWidth: .infinity).frame(height: 48)
                .background(Capsule().fill(V4.goldDark))
        }
        .plain()
    }

    private func secondary(_ t: String, _ action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(t).sora(14, .regular, V4.ink).frame(maxWidth: .infinity).frame(height: 44)
                .overlay(Capsule().strokeBorder(V4.line2, lineWidth: 1))
        }
        .plain()
    }
}

/// Kurve 20–1000 Hz, log-skala, ±15 dB, med 40–300 Hz-området markert.
struct RoomEQChart: View {
    let before: [RoomEQPoint]
    let after: [RoomEQPoint]

    var body: some View {
        GeometryReader { g in
            let w = g.size.width, h = g.size.height
            ZStack {
                band(w: w, h: h)
                grid(w: w, h: h)
                path(before, w: w, h: h).stroke(V4.muted, style: StrokeStyle(lineWidth: 1.5, lineJoin: .round))
                path(after, w: w, h: h).stroke(V4.gold, style: StrokeStyle(lineWidth: 2, lineJoin: .round))
            }
        }
    }

    private func x(_ f: Double, _ w: CGFloat) -> CGFloat { CGFloat(log(f / 20) / log(1000.0 / 20)) * w }
    private func y(_ db: Double, _ h: CGFloat) -> CGFloat { h / 2 - CGFloat(max(-15, min(15, db)) / 15) * (h / 2) }

    private func band(w: CGFloat, h: CGFloat) -> some View {
        let x0 = x(40, w), x1 = x(300, w)
        return Rectangle().fill(V4.gold.opacity(0.07)).frame(width: x1 - x0, height: h).position(x: (x0 + x1) / 2, y: h / 2)
    }

    private func grid(w: CGFloat, h: CGFloat) -> some View {
        Path { p in
            for db in [-10.0, 0, 10] { let yy = y(db, h); p.move(to: CGPoint(x: 0, y: yy)); p.addLine(to: CGPoint(x: w, y: yy)) }
            for f in [50.0, 100, 200, 500] { let xx = x(f, w); p.move(to: CGPoint(x: xx, y: 0)); p.addLine(to: CGPoint(x: xx, y: h)) }
        }
        .stroke(V4.line2, lineWidth: 1)
    }

    private func path(_ pts: [RoomEQPoint], w: CGFloat, h: CGFloat) -> Path {
        Path { p in
            for (i, pt) in pts.enumerated() {
                let c = CGPoint(x: x(pt.f, w), y: y(pt.db, h))
                if i == 0 { p.move(to: c) } else { p.addLine(to: c) }
            }
        }
    }
}
