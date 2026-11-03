import SwiftUI

/// GET/POST /api/update: installed and newest skjold-v* release, and update from the app (git pull + update.sh on the device).
struct DeviceUpdateInfo {
    var current: String? = nil
    var latest: String? = nil
    var available = false
    var running = false
    var result: String? = nil
    var log: [String] = []
    var canUpdate = false
    var error: String? = nil

    static func parse(_ d: Data) -> DeviceUpdateInfo? {
        guard let j = try? JSONSerialization.jsonObject(with: d) as? [String: Any] else { return nil }
        var u = DeviceUpdateInfo()
        u.current = j["current"] as? String
        u.latest = j["latest"] as? String
        u.available = (j["available"] as? Bool) ?? false
        u.running = (j["running"] as? Bool) ?? false
        u.result = j["result"] as? String
        u.log = (j["log"] as? [String]) ?? []
        u.canUpdate = (j["can_update"] as? Bool) ?? false
        u.error = j["error"] as? String
        return u
    }
}

/// Innstillinger → Oppdatering: update Skjold on the device to the newest release.
struct DeviceUpdateView: View {
    @Environment(AppModel.self) private var m
    @State private var info: DeviceUpdateInfo? = nil
    @State private var loading = true
    @State private var err = ""
    @State private var phase = ""   // "", running, gone, done, failed
    @State private var log: [String] = []

    private var working: Bool { phase == "running" || phase == "gone" }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            VStack(alignment: .leading, spacing: 4) {
                Text("Installert på enheten").sora(12, .regular, .muted)
                Text(currentText).sora(22, .semibold)
                if let l = info?.latest { Text("NYESTE: " + l).mono(11) }
            }
            content
            if !err.isEmpty { msg(err, bad: true) }
            if !log.isEmpty && (working || phase == "failed" || phase == "done") {
                ScrollView {
                    Text(log.suffix(30).joined(separator: "\n"))
                        .mono(11, .ink2)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
                .frame(maxHeight: 220)
                .padding(10)
                .skBox(Color(hex: 0x0f0f10), .line, radius: 10)
            }
        }
        .padding(18)
        .skBox(.card, .line)
        .task { await load(check: true) }
    }

    private var currentText: String {
        if loading && info == nil { return "…" }
        guard let c = info?.current else { return "Ukjent versjon" }
        return c == "lokal" ? "Lokal utviklerversjon" : c
    }

    @ViewBuilder private var content: some View {
        if working {
            HStack(spacing: 8) {
                ProgressView().tint(.accent)
                Text(phase == "gone" ? "Starter Skjold på nytt … venter på enheten" : "Oppdaterer … ikke slå av enheten").sora(13)
            }
        } else {
            if phase == "done" { msg("Oppdatert" + (info?.current.map { " til " + $0 } ?? "") + ".", bad: false) }
            if phase == "failed" { msg("Oppdateringen feilet. Se loggen under.", bad: true) }
            if let i = info, phase != "done" {
                if i.available, let l = i.latest {
                    Text("En ny versjon er klar: " + l).sora(13, .regular, .ink2)
                    if i.canUpdate {
                        Button { Task { await start() } } label: {
                            Text("Oppdater til " + l).sora(14, .semibold, .bg)
                                .frame(maxWidth: .infinity).frame(height: 44)
                                .background(RoundedRectangle(cornerRadius: 14).fill(Color.accent))
                        }.plain()
                    } else {
                        Text("Denne enheten må oppdateres fra terminalen én gang før den kan oppdateres herfra:\ngit pull && sudo bash pi/update.sh")
                            .sora(12, .regular, .accent2)
                    }
                } else if i.error == nil {
                    HStack(spacing: 8) {
                        Circle().fill(Color.ok).frame(width: 8, height: 8)
                        Text("Skjold er oppdatert").sora(13)
                    }
                }
                if let e = i.error { msg(e, bad: true) }
            }
            Button { phase = ""; Task { await load(check: true) } } label: {
                Text(loading ? "Sjekker …" : "Se etter oppdateringer").sora(13)
                    .frame(maxWidth: .infinity).frame(height: 42)
                    .skBox(.card2, .line2)
            }.plain().disabled(loading)
        }
    }

    private func msg(_ t: String, bad: Bool) -> some View {
        Text(t).sora(13, .regular, bad ? .danger : .ok)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(10)
            .skBox(Color(hex: bad ? 0x2a1412 : 0x16201a), Color(hex: bad ? 0x5a2620 : 0x2a4a33), radius: 8)
    }

    private func fetch(check: Bool) async -> DeviceUpdateInfo? {
        guard let h = m.activeHost, let url = Net.url(h, check ? "/api/update" : "/api/update?check=0") else { return nil }
        guard let (d, code) = await Net.data(url, timeout: 15), code < 300 else { return nil }
        return DeviceUpdateInfo.parse(d)
    }

    private func load(check: Bool) async {
        loading = true
        defer { loading = false }
        err = ""
        guard let i = await fetch(check: check) else { err = "Fikk ikke kontakt med enheten."; return }
        info = i; log = i.log
        if i.running && !working { await follow() }
    }

    private func start() async {
        guard let h = m.activeHost, let url = Net.url(h, "/api/update") else { return }
        err = ""; log = []
        guard let (d, code) = await Net.data(url, method: "POST", body: DeviceLink.json([:]), timeout: 15) else {
            err = "Fikk ikke kontakt med enheten."; return
        }
        if code >= 300 {
            let j = try? JSONSerialization.jsonObject(with: d) as? [String: Any]
            err = (j?["error"] as? String) ?? "HTTP \(code)"; return
        }
        await follow()
    }

    /// Poll every 2 s until done. The service restarts during the update – tolerate up to 3 min without answer.
    private func follow() async {
        phase = "running"
        var lastOk = Date()
        while true {
            try? await Task.sleep(nanoseconds: 2_000_000_000)
            if let r = await fetch(check: false) {
                lastOk = Date(); log = r.log
                if !r.running {
                    let ok = (r.result ?? "").hasPrefix("ok")
                    phase = ok ? "done" : "failed"
                    if ok { Haptics.success() } else { Haptics.error() }
                    info = await fetch(check: true) ?? r
                    return
                }
                phase = "running"
            } else {
                phase = "gone"
                if Date().timeIntervalSince(lastOk) > 180 {
                    phase = "failed"
                    err = "Enheten har ikke svart på 3 minutter. Den kan fortsatt holde på – prøv igjen litt senere."
                    return
                }
            }
        }
    }
}
