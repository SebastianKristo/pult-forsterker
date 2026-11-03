import SwiftUI

/// One network from GET /api/wifi.
struct WifiNet: Identifiable, Equatable {
    var id: String { ssid }
    let ssid: String
    let signal: Int
    let secure: Bool
    let active: Bool

    static func parse(_ data: Data) -> [WifiNet] {
        guard let j = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let arr = j["networks"] as? [[String: Any]] else { return [] }
        var out: [WifiNet] = []
        for x in arr {
            guard let s = x["ssid"] as? String, !s.isEmpty, !out.contains(where: { $0.ssid == s }) else { continue }
            let sig = (x["signal"] as? NSNumber)?.intValue ?? 0
            let sec = (x["security"] as? String ?? "wpa2") != "open"
            let act = (x["active"] as? Bool) ?? false
            out.append(WifiNet(ssid: s, signal: sig, secure: sec, active: act))
        }
        return out
    }
}

/// Innstillinger → Tilkobling → Wi-Fi: change the network later (same choices as the Wi-Fi step in setup).
struct WifiSettingsView: View {
    @Environment(AppModel.self) private var m
    @State private var open = false
    @State private var nets: [WifiNet] = []
    @State private var loading = true
    @State private var unavailable = ""
    @State private var pick = -1          // -1 none, -2 «Annet nettverk …», else index
    @State private var ssid = ""
    @State private var sec = 0
    @State private var pw = ""
    @State private var phase = ""         // "", connecting, waiting, done, lost
    @State private var err = ""
    @State private var alt = ""

    private var manual: Bool { pick == -2 }
    private var picked: WifiNet? { pick >= 0 && pick < nets.count ? nets[pick] : nil }
    private var needPw: Bool { manual ? sec < 2 : (picked?.secure ?? false) }
    private var busy: Bool { phase == "connecting" || phase == "waiting" }
    private var canJoin: Bool {
        let hasNet = manual ? !ssid.trimmingCharacters(in: .whitespaces).isEmpty : picked != nil
        return !busy && hasNet && (!needPw || pw.count >= 8)
    }
    private var activeName: String? { nets.first(where: { $0.active })?.ssid }

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Button { open.toggle() } label: {
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Wi-Fi").sora(14)
                        Text(summary).sora(11, .regular, .muted).lineLimit(1)
                    }
                    Spacer()
                    Text(open ? "Lukk" : "Endre").sora(13, .regular, .accent)
                }
                .padding(.horizontal, 14).frame(minHeight: 54)
            }
            .plain()
            .skBox(.card, .line)
            if open { panel }
        }
        .task { await scan() }
    }

    private var summary: String {
        if loading { return "Henter …" }
        if !unavailable.isEmpty { return "Ikke tilgjengelig" }
        if let a = activeName { return "Tilkoblet " + a }
        return "Ikke tilkoblet Wi-Fi (kabel eller ukjent)"
    }

    @ViewBuilder private var panel: some View {
        if !unavailable.isEmpty {
            Text("Enheten kan ikke styre Wi-Fi herfra (\(unavailable)). Den trenger NetworkManager (Skjold OS / Raspberry Pi OS Bookworm). Wi-Fi kan også settes i Skjold Flasher.")
                .sora(12, .regular, .danger, lineHeight: 1.5).fixedSize(horizontal: false, vertical: true)
        } else {
            HStack {
                Text("Velg nettverk").sora(14, .semibold)
                Spacer()
                Button { Task { await scan() } } label: { Text("Oppdater").sora(13, .regular, .accent) }.plain()
            }
            VStack(spacing: 0) {
                if loading { netRow("Leter etter nettverk …", net: nil, on: false, first: true) {} }
                ForEach(Array(nets.enumerated()), id: \.offset) { i, n in
                    netRow(n.ssid, net: n, on: pick == i, first: i == 0 && !loading) { pick = i }
                }
                netRow("Annet nettverk …", net: nil, on: manual, first: false) { pick = -2 }
            }
            .skBox(.card, .line)
            if manual {
                SKField(placeholder: "Nettverksnavn (SSID)", text: $ssid, height: 44, size: 15, plainInput: true)
                HStack(spacing: 6) {
                    ForEach(Array(["WPA2", "WPA3", "Ingen"].enumerated()), id: \.offset) { i, label in
                        let s = SelStyle.of(sec == i)
                        Button { sec = i } label: {
                            Text(label).sora(13, .regular, s.fg).lineLimit(1)
                                .frame(maxWidth: .infinity).frame(height: 36)
                                .background(Capsule().fill(s.bg)).skCapsuleBorder(s.bd)
                        }
                        .plain()
                    }
                }
            }
            if needPw { SKField(placeholder: "Passord (minst 8 tegn)", text: $pw, height: 44, size: 15, secure: true) }
            Text("Når enheten bytter nettverk, mister den forbindelsen noen sekunder. Appen kobler til igjen av seg selv. Havner telefonen på et annet nett enn enheten, finner du den ikke før de er på samme nett.")
                .sora(12, .regular, .muted, lineHeight: 1.5).fixedSize(horizontal: false, vertical: true)
            if !err.isEmpty { Text(err).sora(12, .regular, .danger, lineHeight: 1.45).fixedSize(horizontal: false, vertical: true) }
            if phase == "waiting" { Text("Bytter nettverk – venter på at enheten svarer igjen …").sora(12, .regular, .accent2) }
            if phase == "done" { Text("Enheten er tilkoblet og svarer.").sora(12, .regular, .ok) }
            if phase == "lost" {
                Text(alt.isEmpty ? "Enheten svarer ikke. Koble telefonen til samme nett som enheten og prøv igjen." : "Enheten svarer ikke. Koble telefonen til samme nett som enheten – den finnes da på \(alt).")
                    .sora(12, .regular, .danger, lineHeight: 1.45).fixedSize(horizontal: false, vertical: true)
            }
            Button { Task { await join() } } label: {
                Text(phase == "connecting" ? "Kobler til …" : (phase == "waiting" ? "Venter …" : "Koble til"))
                    .sora(14, .semibold, canJoin ? Color.bg : .muted)
                    .frame(maxWidth: .infinity).frame(height: 44)
                    .background(RoundedRectangle(cornerRadius: 12).fill(canJoin ? Color.accent : Color.seg))
            }
            .plain()
            .disabled(!canJoin)
        }
    }

    private func netRow(_ title: String, net: WifiNet?, on: Bool, first: Bool, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack(spacing: 8) {
                Text(title).sora(14, .regular, net == nil && !on ? .ink2 : .ink).lineLimit(1)
                if net?.active == true { Text("· tilkoblet").sora(11, .regular, .ok) }
                Spacer(minLength: 0)
                if let n = net {
                    if n.secure { Image(systemName: "lock").font(.system(size: 11)).foregroundStyle(Color.muted) }
                    Image(systemName: "wifi", variableValue: Double(n.signal) / 100.0).font(.system(size: 13)).foregroundStyle(Color.ink2)
                }
                Text(on ? "✓" : "").sora(12, .regular, .accent2).frame(minWidth: 9)
            }
            .padding(.horizontal, 14).frame(minHeight: 50)
            .background(on ? Color.selBg : Color.clear)
            .topLine(first ? .clear : .line)
        }
        .plain()
    }

    private func scan() async {
        loading = true
        defer { loading = false }
        guard let h = m.activeHost, let url = Net.url(h, "/api/wifi") else { unavailable = "ingen enhet valgt"; return }
        guard let (d, code) = await Net.data(url, timeout: 25) else { unavailable = "svarer ikke"; return }
        if code >= 300 { unavailable = Self.errText(d, code); return }
        unavailable = ""
        nets = WifiNet.parse(d)
        if pick >= nets.count { pick = -1 }
    }

    private func join() async {
        guard let h = m.activeHost, let url = Net.url(h, "/api/wifi") else { return }
        let name = manual ? ssid.trimmingCharacters(in: .whitespaces) : (picked?.ssid ?? "")
        var body: [String: Any] = ["ssid": name, "hidden": manual]
        if needPw { body["psk"] = pw }
        if manual { body["security"] = ["wpa2", "wpa3", "open"][sec] }
        err = ""; alt = ""; phase = "connecting"
        let res = await Net.data(url, method: "POST", body: DeviceLink.json(body), timeout: 50)
        if let (d, code) = res, code >= 300 {
            phase = ""; err = "Fikk ikke koblet til «\(name)»: " + Self.errText(d, code)
            Haptics.error(); return
        }
        // nil = the connection dropped while the device switched network – wait for it either way
        pw = ""
        await waitBack(host: h)
    }

    /// After switching: wait up to 60 s for the device to answer again (same address, else <id>.local).
    private func waitBack(host: String) async {
        phase = "waiting"
        let id = m.dev?.id ?? ""
        let local = id.isEmpty ? "" : "http://\(id).local:8765"
        let start = Date()
        while Date().timeIntervalSince(start) < 60 {
            try? await Task.sleep(nanoseconds: 3_000_000_000)
            if await DeviceLink.shared.get("/api/status", on: host, timeout: 4) != nil {
                phase = "done"; Haptics.success(); await scan(); return
            }
            if !local.isEmpty && local != host, await DeviceLink.shared.get("/api/status", on: local, timeout: 4) != nil {
                m.activeHost = local
                phase = "done"; Haptics.success(); await scan(); return
            }
        }
        alt = local.replacingOccurrences(of: "http://", with: "")
        phase = "lost"; Haptics.error()
    }

    private static func errText(_ d: Data, _ code: Int) -> String {
        if let j = try? JSONSerialization.jsonObject(with: d) as? [String: Any], let e = j["error"] as? String, !e.isEmpty { return e }
        return "HTTP \(code)"
    }
}
