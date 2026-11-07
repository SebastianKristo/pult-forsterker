import SwiftUI
import UIKit
import CoreImage.CIFilterBuiltins

/// Kassett-Wrapped (GET /api/nfc/stats) og deling av kassetter (POST /api/nfc/share, /api/nfc/share/import).

/// Topp 3 og glemte kassetter – vises øverst i «Lag kassett».
struct V4KassettWrappedCard: View {
    @Environment(AppModel.self) private var m
    @State private var topp: [[String: Any]] = []
    @State private var glemte: [[String: Any]] = []
    @State private var totalt = 0
    @State private var lastet = false

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("KASSETT-WRAPPED").mono(10, V4.gold, em: 0.12)
            if !lastet {
                ProgressView().tint(V4.gold)
            } else if totalt == 0 {
                Text("Ingen kassetter spilt i år ennå.").sora(13, .regular, V4.muted)
            } else {
                Text("\(totalt) avspillinger i år").sora(20, .semibold)
                ForEach(Array(topp.prefix(3).enumerated()), id: \.offset) { i, r in
                    rad(r, venstre: "\(i + 1)", hoyre: "\((r["spilt"] as? Int) ?? 0)×")
                }
                if !glemte.isEmpty {
                    Text("Glemte kassetter").sora(13, .semibold).padding(.top, 4)
                    ForEach(Array(glemte.prefix(3).enumerated()), id: \.offset) { _, r in
                        let aldri = (r["aldri"] as? Bool) ?? false
                        rad(r, venstre: "·", hoyre: aldri ? "aldri" : "\((r["uker_siden"] as? Int) ?? 0) uker")
                    }
                }
            }
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .v4Card(radius: 16)
        .task { await load() }
    }

    private func rad(_ r: [String: Any], venstre: String, hoyre: String) -> some View {
        HStack(spacing: 10) {
            Text(venstre).sora(13, .regular, V4.gold).frame(width: 16)
            AsyncImage(url: URL(string: DeviceLink.shared.coverURL((r["omslag"] as? String) ?? "", on: m.settingsHost))) { img in
                img.resizable().scaledToFill()
            } placeholder: { V4.row }
            .frame(width: 34, height: 34).clipShape(RoundedRectangle(cornerRadius: 7))
            VStack(alignment: .leading, spacing: 1) {
                Text((r["navn"] as? String) ?? "").sora(14).lineLimit(1)
                Text((r["undertittel"] as? String) ?? "").sora(12, .regular, V4.muted).lineLimit(1)
            }
            Spacer(minLength: 0)
            Text(hoyre).sora(12, .regular, V4.muted)
        }
    }

    private func load() async {
        defer { lastet = true }
        guard let d = await DeviceLink.shared.get("/api/nfc/stats?periode=%C3%A5r&glemt=8", on: m.settingsHost, timeout: 8),
              let o = try? JSONSerialization.jsonObject(with: d) as? [String: Any] else { return }
        topp = (o["topp"] as? [[String: Any]]) ?? []
        glemte = (o["glemte"] as? [[String: Any]]) ?? []
        totalt = ((o["totalt"] as? [String: Any])?["spilt"] as? Int) ?? 0
    }
}

/// Del alle kassettene: kort kode via Skjold Cloud (kryptert, 14 dager) som QR, lenke og systemets delingsark.
struct V4KassettDelSheet: View {
    @Environment(AppModel.self) private var m
    @Environment(\.dismiss) private var dismiss
    @State private var lenke = ""
    @State private var info = ""
    @State private var feil = ""
    @State private var sky = true

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                HStack {
                    Text("Del kassetter").sora(24, .semibold)
                    Spacer()
                    Button { dismiss() } label: { Text("Lukk").sora(15, .regular, V4.gold) }.plain()
                }
                Text("Vennen skanner QR-koden med kameraet eller Skjold-appen. Kassettene blir ventende hos dem, klare til å kobles til en NFC-brikke. Albumene slås opp i deres eget Navidrome eller YouTube Music – ingen passord eller private ID-er deles.")
                    .sora(13, .regular, V4.muted)
                if lenke.isEmpty && feil.isEmpty { ProgressView().tint(V4.gold) }
                if !feil.isEmpty { Text(feil).sora(13, .regular, V4.red) }
                if !lenke.isEmpty {
                    if let qr = Self.qr(lenke) {
                        Image(uiImage: qr).interpolation(.none).resizable().scaledToFit()
                            .frame(maxWidth: 240).padding(12)
                            .background(RoundedRectangle(cornerRadius: 14).fill(Color.white))
                            .frame(maxWidth: .infinity)
                    }
                    if !info.isEmpty { Text(info).sora(12, .regular, V4.muted) }
                    Text(lenke).font(.system(size: 12, design: .monospaced)).foregroundStyle(V4.muted).textSelection(.enabled)
                    HStack(spacing: 10) {
                        ShareLink(item: lenke) {
                            Text("Del lenke").sora(15, .semibold, V4.bg).frame(maxWidth: .infinity).frame(height: 46)
                                .background(Capsule().fill(V4.gold))
                        }
                        Button { UIPasteboard.general.string = lenke; info = "Lenken er kopiert" } label: {
                            Text("Kopier").sora(15).frame(maxWidth: .infinity).frame(height: 46).v4Card(radius: 23)
                        }.plain()
                    }
                    Button { sky.toggle(); Task { await lag() } } label: {
                        Text(sky ? "Lag kode uten Skjold Cloud" : "Lag kort kode via Skjold Cloud").sora(13, .regular, V4.gold)
                    }.plain()
                }
            }
            .padding(20)
        }
        .background(V4.bg.ignoresSafeArea())
        .presentationDragIndicator(.visible)
        .task { await lag() }
    }

    private func lag() async {
        lenke = ""; feil = ""; info = ""
        let body = (try? JSONSerialization.data(withJSONObject: ["uids": [String](), "sky": sky])) ?? Data()
        var d = await DeviceLink.shared.sendRaw("/api/nfc/share", body, on: m.settingsHost, timeout: 15)
        if d == nil && sky {   // Skjold Cloud svarer ikke: lag en kode uten sky
            sky = false
            let b2 = (try? JSONSerialization.data(withJSONObject: ["uids": [String](), "sky": false])) ?? Data()
            d = await DeviceLink.shared.sendRaw("/api/nfc/share", b2, on: m.settingsHost, timeout: 15)
        }
        guard let d, let o = try? JSONSerialization.jsonObject(with: d) as? [String: Any], let l = o["lenke"] as? String else {
            feil = "Fikk ikke laget delingskode. Har du kassetter som kan deles (album, radiostrømmer, NRK)?"
            return
        }
        lenke = l
        let n = (o["delt"] as? Int) ?? 0, hopp = (o["hoppet_over"] as? Int) ?? 0
        info = "\(n) kassett\(n == 1 ? "" : "er") delt" + (hopp > 0 ? " · \(hopp) kunne ikke deles" : "") + ((o["sky"] as? Bool) == true ? " · gyldig i 14 dager" : "")
    }

    static func qr(_ text: String) -> UIImage? {
        let f = CIFilter.qrCodeGenerator()
        f.message = Data(text.utf8)
        f.correctionLevel = "M"
        guard let out = f.outputImage?.transformed(by: CGAffineTransform(scaleX: 8, y: 8)),
              let cg = CIContext().createCGImage(out, from: out.extent) else { return nil }
        return UIImage(cgImage: cg)
    }
}

/// Mottatt delingslenke (skjold://kassett/del?d=…): bekreft og legg kassettene som ventende på valgt Skjold.
struct V4KassettMottaSheet: View {
    @Environment(AppModel.self) private var m
    @Environment(\.dismiss) private var dismiss
    let kode: String
    @State private var status = ""
    @State private var ferdig = false
    @State private var busy = false

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Du har fått kassetter").sora(24, .semibold)
            Text("De legges som ventende kassetter på \(m.settingsHost ?? "Skjold"). Sett inn en ny NFC-brikke i kassettspilleren for å koble den første.")
                .sora(13, .regular, V4.muted)
            if !status.isEmpty { Text(status).sora(14, .regular, ferdig ? V4.gold : V4.red) }
            if busy { ProgressView().tint(V4.gold) }
            Button {
                if ferdig { dismiss(); return }
                Task { await importer() }
            } label: {
                Text(ferdig ? "Ferdig" : "Legg til").sora(15, .semibold, V4.bg).frame(maxWidth: .infinity).frame(height: 48)
                    .background(Capsule().fill(V4.gold))
            }.plain().disabled(busy)
            if !ferdig { Button { dismiss() } label: { Text("Avbryt").sora(14, .regular, V4.muted).frame(maxWidth: .infinity) }.plain() }
            Spacer(minLength: 0)
        }
        .padding(20)
        .background(V4.bg.ignoresSafeArea())
        .presentationDetents([.medium])
    }

    private func importer() async {
        busy = true; defer { busy = false }
        let body = (try? JSONSerialization.data(withJSONObject: ["kode": kode])) ?? Data()
        guard let d = await DeviceLink.shared.sendRaw("/api/nfc/share/import", body, on: m.settingsHost, timeout: 15),
              let o = try? JSONSerialization.jsonObject(with: d) as? [String: Any] else {
            status = "Fikk ikke lagt til kassettene. Sjekk at du er koblet til Skjold, og at lenken ikke er utløpt."
            return
        }
        let n = (o["lagt_til"] as? Int) ?? 0, fra = (o["fra"] as? String) ?? ""
        status = n > 0 ? "\(n) kassett\(n == 1 ? "" : "er")\(fra.isEmpty ? "" : " fra \(fra)") venter på en NFC-brikke" : "Du har disse kassettene fra før"
        ferdig = true
    }

    /// skjold://kassett/del?d=<kode> eller https://…/kassett/del#<kode> → koden.
    static func kode(fra url: URL) -> String? {
        if url.scheme == "skjold", url.host == "kassett", url.path.hasPrefix("/del") {
            return URLComponents(url: url, resolvingAgainstBaseURL: false)?.queryItems?.first { $0.name == "d" }?.value
        }
        if url.path.hasPrefix("/kassett/del"), let f = url.fragment, !f.isEmpty { return f }
        return nil
    }
}
