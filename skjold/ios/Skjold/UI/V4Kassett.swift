import SwiftUI
import UIKit
import WebKit
#if canImport(CoreNFC)
import CoreNFC
#endif

/// «Lag kassett»: velg radio, spilleliste eller podkast → hold telefonen mot NFC-brikken → kassetten registreres på
/// Skjold (POST /api/nfc/cards) → ferdig etikett (PDF fra GET /api/nfc/label) kan deles eller skrives ut.
/// Uten NFC-tillatelse i appen (personlig team kan ikke signere CoreNFC) kobles brikken med Kassett-spilleren i læremodus.
struct V4KassettSheet: View {
    @Environment(AppModel.self) private var m
    @Environment(\.dismiss) private var dismiss

    enum Src: String, CaseIterable { case album = "Album", radio = "Radio", liste = "Spilleliste", podkast = "Podkast" }
    struct Pick: Hashable { var navn: String, under: String, omslag: String, handling: String, verdi: String, verdiKey: String = "" }

    @State private var src: Src = .album
    @State private var query = ""
    @State private var hits: [Pick] = []
    @State private var pick: Pick?
    @State private var navn = ""
    @State private var phase: Phase = .velg
    @State private var status = ""
    @State private var pdf: URL?
    @State private var busy = false
    @State private var showDel = false

    enum Phase { case velg, skriv, ferdig }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                HStack {
                    Text("Lag kassett").sora(24, .semibold)
                    Spacer()
                    Button { dismiss() } label: { Text("Lukk").sora(15, .regular, V4.gold) }.plain()
                }
                switch phase {
                case .velg: chooser
                case .skriv: writing
                case .ferdig: done
                }
            }
            .padding(20)
        }
        .background(V4.bg.ignoresSafeArea())
        .presentationDragIndicator(.visible)
        .task(id: src) { await load() }
        .sheet(isPresented: $showDel) { V4KassettDelSheet().environment(m) }
    }

    // MARK: 1 – velg hva kassetten skal spille

    private var chooser: some View {
        VStack(alignment: .leading, spacing: 14) {
            V4KassettWrappedCard()
            Button { showDel = true } label: {
                Text("Del kassettene med en venn").sora(14, .regular, V4.gold)
            }.plain()
            HStack(spacing: 8) {
                ForEach(Src.allCases, id: \.self) { s in
                    Button { src = s; pick = nil } label: {
                        Text(s.rawValue).sora(13, .regular, src == s ? V4.gold : V4.ink)
                            .padding(.horizontal, 14).frame(height: 34)
                            .background(Capsule().fill(src == s ? V4.selBg : V4.card))
                            .overlay(Capsule().strokeBorder(src == s ? V4.goldDark : V4.line2, lineWidth: 1))
                    }.plain()
                }
            }
            if src == .album {
                TextField("Artist - Album", text: $query)
                    .autocorrectionDisabled()
                    .padding(12).v4Card(radius: 12)
                    .onSubmit { Task { await load() } }
                Text("Spilles fra Navidrome hvis du har albumet, ellers fra YouTube Music. Skriv f.eks. «Linkin Park - Meteora».")
                    .sora(12, .regular, V4.muted)
            }
            if src == .podkast {
                TextField("Søk i NRK-podkaster", text: $query)
                    .textInputAutocapitalization(.never).autocorrectionDisabled()
                    .padding(12).v4Card(radius: 12)
                    .onSubmit { Task { await load() } }
            }
            if busy { ProgressView().tint(V4.gold) }
            if hits.isEmpty && !busy {
                Text(emptyText).sora(13, .regular, V4.muted)
            }
            VStack(spacing: 0) {
                ForEach(hits, id: \.self) { h in
                    Button { pick = h; navn = h.navn } label: {
                        HStack(spacing: 12) {
                            AsyncImage(url: URL(string: DeviceLink.shared.coverURL(h.omslag, on: m.settingsHost))) { img in
                                img.resizable().scaledToFill()
                            } placeholder: { V4.row }
                            .frame(width: 40, height: 40).clipShape(RoundedRectangle(cornerRadius: 8))
                            VStack(alignment: .leading, spacing: 2) {
                                Text(h.navn).sora(15).lineLimit(1)
                                Text(h.under).sora(12, .regular, V4.muted).lineLimit(1)
                            }
                            Spacer()
                            if pick == h { Text("Valgt").sora(13, .regular, V4.gold) }
                        }
                        .padding(.horizontal, 14).padding(.vertical, 10).contentShape(Rectangle())
                    }.plain()
                }
            }.v4Card()
            if pick != nil {
                TextField("Navn på etiketten", text: $navn).padding(12).v4Card(radius: 12)
                primary(NFCWriter.available ? "Hold telefonen mot brikken" : "Koble med Kassett-spilleren") { start() }
                if !NFCWriter.available {
                    Text("Denne versjonen av appen har ikke NFC-tillatelse. Sett kassetten i Skjold Kassett-spilleren når du blir bedt om det.")
                        .sora(12, .regular, V4.muted)
                }
            }
            if !status.isEmpty { Text(status).sora(13, .regular, V4.red) }
        }
    }

    private var emptyText: String {
        switch src {
        case .radio: return "Ingen radiofavoritter på denne Skjold ennå."
        case .liste: return m.ndConf.ok ? "Fant ingen spillelister i Navidrome." : "Navidrome er ikke satt opp i Innstillinger."
        case .podkast: return "Søk etter en podkast eller et program."
        case .album: return "Skriv artist og album, og trykk Enter."
        }
    }

    private func load() async {
        hits = []; busy = true
        defer { busy = false }
        switch src {
        case .album:
            let q = query.trimmingCharacters(in: .whitespaces)
            guard q.count >= 2 else { return }
            hits = [Self.albumPick(q)]
            if let enc = q.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed),
               let d = await DeviceLink.shared.get("/api/nfc/sok?q=" + enc, on: m.settingsHost, timeout: 12),
               let o = try? JSONSerialization.jsonObject(with: d) as? [String: Any] {
                for t in ((o["treff"] as? [[String: Any]]) ?? []).prefix(10) {
                    let a = (t["artist"] as? String) ?? "", al = (t["album"] as? String) ?? ""
                    if !al.isEmpty { hits.append(Self.albumPick("\(a) - \(al)", kilde: (t["kilde"] as? String) ?? "")) }
                }
            }
        case .radio:
            hits = m.radio.enumerated().map { i, s in
                Pick(navn: s.name, under: s.genre.isEmpty ? "Radio" : s.genre, omslag: s.image ?? "", handling: "preset", verdi: "\(i + 1)")
            }
        case .liste:
            guard m.ndConf.ok, case let .success(ls) = await Subsonic.playlists(m.ndConf) else { return }
            hits = ls.map { Pick(navn: $0.name, under: "Spilleliste · \($0.count) låter", omslag: $0.cover, handling: "navidrome_playlist", verdi: $0.id) }
        case .podkast:
            let q = query.trimmingCharacters(in: .whitespaces)
            guard q.count >= 2, let enc = q.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed),
                  let d = await DeviceLink.shared.get("/api/nrk/search?q=" + enc, on: m.settingsHost, timeout: 12),
                  let o = try? JSONSerialization.jsonObject(with: d) as? [String: Any] else { return }
            hits = ((o["series"] as? [[String: Any]]) ?? []).map {
                Pick(navn: ($0["title"] as? String) ?? "", under: ($0["subtitle"] as? String) ?? "NRK",
                     omslag: ($0["image"] as? String) ?? "", handling: "nrk", verdi: ($0["id"] as? String) ?? "", verdiKey: "series")
            }
        }
    }

    /// «Artist - Album» → album-kassett. Skjold slår opp om den spilles fra Navidrome eller YouTube Music.
    static func albumPick(_ text: String, kilde: String = "") -> Pick {
        let parts = text.components(separatedBy: " - ")
        let artist = parts.count > 1 ? parts[0].trimmingCharacters(in: .whitespaces) : ""
        let album = (parts.count > 1 ? parts.dropFirst().joined(separator: " - ") : text).trimmingCharacters(in: .whitespaces)
        var cs = CharacterSet.urlQueryAllowed; cs.remove(charactersIn: "&=+")
        let ea = artist.addingPercentEncoding(withAllowedCharacters: cs) ?? "", eb = album.addingPercentEncoding(withAllowedCharacters: cs) ?? ""
        return Pick(navn: album, under: kilde.isEmpty ? artist : "\(artist) · \(kilde)", omslag: "/api/nfc/cover?artist=\(ea)&album=\(eb)",
                    handling: "album", verdi: "\(artist) - \(album)")
    }

    private func card(uid: String?) -> [String: Any]? {
        guard let p = pick else { return nil }
        let verdi: Any
        if !p.verdiKey.isEmpty { verdi = [p.verdiKey: p.verdi] } else if p.handling == "preset" { verdi = Int(p.verdi) ?? 1 } else { verdi = p.verdi }
        var c: [String: Any] = ["navn": navn.isEmpty ? p.navn : navn, "handling": p.handling, "verdi": verdi,
                                "omslag": p.omslag, "undertittel": p.handling == "album" ? (p.under.components(separatedBy: " · ").first ?? "") : p.under,
                                "ved_uttak": "pause", "rom": [String]()]
        if let uid { c["uid"] = uid }
        return c
    }

    // MARK: 2 – skriv brikken

    private var writing: some View {
        VStack(alignment: .leading, spacing: 12) {
            V4Kicker(text: NFCWriter.available ? "NFC" : "LÆREMODUS")
            Text(NFCWriter.available ? "Hold toppen av telefonen mot kassetten." : "Sett kassetten inn i Skjold Kassett-spilleren nå.")
                .sora(15, .regular, V4.ink)
            HStack(spacing: 10) { ProgressView().tint(V4.gold); Text(status).sora(13, .regular, V4.muted) }
        }
        .padding(16).v4Card()
    }

    private func start() {
        guard let draft = card(uid: nil) else { return }
        status = ""; phase = .skriv
        let host = m.settingsHost
        Task {
            if NFCWriter.available {
                status = "Venter på brikken …"
                do {
                    let uid = try await NFCWriter.writeCassette()
                    var c = draft; c["uid"] = uid
                    guard await DeviceLink.shared.send("/api/nfc/cards", c, on: host, timeout: 8) != nil else {
                        throw NSError(domain: "skjold", code: 1, userInfo: [NSLocalizedDescriptionKey: "Skjold tok ikke imot kassetten"])
                    }
                    await finish(uid: uid, host: host)
                } catch {
                    status = error.localizedDescription; phase = .velg
                }
            } else {
                status = "Venter på kassetten (60 s) …"
                let before = await lastScan(host)
                _ = await DeviceLink.shared.send("/api/nfc/learn", ["timeout": 60, "kort": draft], on: host)
                let until = Date().addingTimeInterval(60)
                while Date() < until {
                    try? await Task.sleep(for: .seconds(1))
                    if let s = await lastScanFull(host), s.1 > before, s.2 { await finish(uid: s.0, host: host); return }
                }
                _ = await DeviceLink.shared.send("/api/nfc/learn", ["stop": true], on: host)
                status = "Fant ingen kassett. Prøv igjen."; phase = .velg
            }
        }
    }

    private func lastScan(_ host: String?) async -> Double { await lastScanFull(host)?.1 ?? 0 }

    private func lastScanFull(_ host: String?) async -> (String, Double, Bool)? {
        guard let d = await DeviceLink.shared.get("/api/nfc", on: host),
              let o = try? JSONSerialization.jsonObject(with: d) as? [String: Any],
              let last = o["last"] as? [String: Any] else { return nil }
        return ((last["uid"] as? String) ?? "", (last["t"] as? Double) ?? 0, (last["known"] as? Bool) ?? false)
    }

    private func finish(uid: String, host: String?) async {
        Haptics.success()
        status = "Lager etiketten …"
        pdf = await LabelPDF.make(host: host, uid: uid, name: navn.isEmpty ? (pick?.navn ?? "Kassett") : navn)
        phase = .ferdig
    }

    // MARK: 3 – ferdig: etikett

    private var done: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("✓ Kassetten er klar").sora(18, .semibold, V4.green)
            Text("Skriv ut etiketten på A4 (100 %), klipp langs den røde linja og lim den i forsenkningen.").sora(13, .regular, V4.ink)
            if let pdf {
                ShareLink(item: pdf) {
                    Text("Del eller skriv ut etikett").sora(15, .semibold, V4.bg).frame(maxWidth: .infinity).frame(height: 48)
                        .background(Capsule().fill(V4.goldDark))
                }
            } else {
                Text("Fikk ikke laget PDF – skriv ut fra Kassetter i web-appen.").sora(13, .regular, V4.muted)
            }
            secondary("Lag en kassett til") { pick = nil; navn = ""; pdf = nil; status = ""; phase = .velg }
        }
        .padding(16).v4Card()
    }

    private func primary(_ t: String, _ action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(t).sora(15, .semibold, V4.bg).frame(maxWidth: .infinity).frame(height: 48).background(Capsule().fill(V4.goldDark))
        }.plain()
    }

    private func secondary(_ t: String, _ action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(t).sora(14, .regular, V4.ink).frame(maxWidth: .infinity).frame(height: 44)
                .overlay(Capsule().strokeBorder(V4.line2, lineWidth: 1))
        }.plain()
    }
}

/// Etikett-SVG fra Skjold → PDF (A4) via WKWebView, lagret i tmp for ShareLink.
@MainActor
enum LabelPDF {
    private static var keep: WKWebView?

    static func make(host: String?, uid: String, name: String) async -> URL? {
        guard let d = await DeviceLink.shared.get("/api/nfc/label?uids=" + uid, on: host, timeout: 20),
              let svg = String(data: d, encoding: .utf8) else { return nil }
        let html = "<!doctype html><meta charset=utf-8><style>@page{size:A4;margin:0}body{margin:0}svg{width:595px;height:842px}</style>" + svg
        let w = WKWebView(frame: CGRect(x: 0, y: 0, width: 595, height: 842))
        keep = w
        defer { keep = nil }
        w.loadHTMLString(html, baseURL: nil)
        for _ in 0..<50 where w.isLoading { try? await Task.sleep(for: .milliseconds(100)) }
        try? await Task.sleep(for: .milliseconds(300))
        let cfg = WKPDFConfiguration(); cfg.rect = CGRect(x: 0, y: 0, width: 595, height: 842)
        guard let pdf = try? await w.pdf(configuration: cfg) else { return nil }
        let safe = name.replacingOccurrences(of: "/", with: "-").prefix(40)
        let url = FileManager.default.temporaryDirectory.appendingPathComponent("Kassett – \(safe).pdf")
        do { try pdf.write(to: url); return url } catch { return nil }
    }
}

/// Leser UID-en til en NTAG-brikke og skriver NDEF-lenken skjold://kassett/<UID> (leseren i spilleren bruker bare UID-en).
/// Krever tillatelsen com.apple.developer.nfc.readersession.formats (TAG) – se Entitlements/Skjold-NFC.entitlements.
nonisolated final class NFCWriter: NSObject, @unchecked Sendable {
    static var available: Bool {
        #if canImport(CoreNFC)
        return NFCTagReaderSession.readingAvailable
        #else
        return false
        #endif
    }

    @MainActor static func writeCassette() async throws -> String {
        #if canImport(CoreNFC)
        let w = NFCWriter()
        return try await withCheckedThrowingContinuation { cont in
            w.cont = cont
            w.session = NFCTagReaderSession(pollingOption: [.iso14443], delegate: w, queue: nil)
            w.session?.alertMessage = "Hold telefonen mot kassetten."
            w.retain = w
            w.session?.begin()
        }
        #else
        throw NSError(domain: "skjold", code: 2, userInfo: [NSLocalizedDescriptionKey: "NFC finnes ikke på denne enheten"])
        #endif
    }

    #if canImport(CoreNFC)
    private var session: NFCTagReaderSession?
    private var cont: CheckedContinuation<String, Error>?
    private var retain: NFCWriter?

    private func end(_ r: Result<String, Error>, _ msg: String? = nil) {
        if let c = cont { cont = nil; c.resume(with: r) }
        if case .success = r { session?.alertMessage = msg ?? "Ferdig"; session?.invalidate() }
        else { session?.invalidate(errorMessage: msg ?? "Noe gikk galt") }
        retain = nil
    }
    #endif
}

#if canImport(CoreNFC)
extension NFCWriter: NFCTagReaderSessionDelegate {
    nonisolated func tagReaderSessionDidBecomeActive(_ session: NFCTagReaderSession) {}

    nonisolated func tagReaderSession(_ session: NFCTagReaderSession, didInvalidateWithError error: Error) {
        if let c = cont {
            cont = nil
            let e = error as? NFCReaderError
            c.resume(throwing: NSError(domain: "skjold", code: 3, userInfo: [NSLocalizedDescriptionKey:
                e?.code == .readerSessionInvalidationErrorUserCanceled ? "Avbrutt" : error.localizedDescription]))
        }
        retain = nil
    }

    nonisolated func tagReaderSession(_ session: NFCTagReaderSession, didDetect tags: [NFCTag]) {
        guard let tag = tags.first, case let .miFare(mf) = tag else {
            session.restartPolling(); return
        }
        session.connect(to: tag) { [self] err in
            if let err { end(.failure(err), "Fikk ikke kontakt med brikken"); return }
            let uid = mf.identifier.map { String(format: "%02X", $0) }.joined(separator: "-")
            guard let rec = NFCNDEFPayload.wellKnownTypeURIPayload(string: "skjold://kassett/" + uid) else {
                end(.success(uid), "Kassetten er koblet"); return
            }
            mf.queryNDEFStatus { st, _, _ in
                guard st == .readWrite else { self.end(.success(uid), "Kassetten er koblet"); return }   // låst brikke: UID holder
                mf.writeNDEF(NFCNDEFMessage(records: [rec])) { _ in self.end(.success(uid), "Kassetten er koblet") }
            }
        }
    }
}
#endif
