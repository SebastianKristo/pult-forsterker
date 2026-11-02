import SwiftUI

/// 18 Innstillinger, 19 Innst. → Radio, 20 Innst. → Equalizer and the other categories from catsFor(type).
struct SettingsView: View {
    @Environment(AppModel.self) private var m

    static let catIcon: [String: String] = ["tjenester": "M9 18V5l12-2v13M9 18a3 3 0 1 1-6 0 3 3 0 0 1 6 0zM21 16a3 3 0 1 1-6 0 3 3 0 0 1 6 0z", "eq": "M5 4v6M5 14v6M12 4v3M12 11v9M19 4v9M19 17v3M3 12h4M10 9h4M17 15h4", "lyd": "M4 9h3l5-4v14l-5-4H4zM16 9a4 4 0 0 1 0 6M19 6a8 8 0 0 1 0 12", "tilkobling": "M7 7l10 10-5 5V2l5 5L7 17", "radio": "M4 9h16v11H4zM8 9l9-5M8 14.5h.01M14 13h4M14 16h4", "stemme": "M12 3a3 3 0 0 1 3 3v6a3 3 0 0 1-6 0V6a3 3 0 0 1 3-3zM5 11a7 7 0 0 0 14 0M12 18v3", "skjerm": "M3 5h18v12H3zM8 21h8M12 17v4", "strom": "M12 3v8M6.3 6.6a8 8 0 1 0 11.4 0", "system": "M12 8v4M12 16h.01M12 3l9 4v6c0 5-4 8-9 9-5-1-9-4-9-9V7z", "oppdatering": "M12 4v11M7 10l5 5 5-5M5 20h14", "utgang": "M4 9h3l5-4v14l-5-4H4zM16 8l5 4-5 4"]
    static let catTile: [String: UInt32] = ["tjenester": 0x2a3a2e, "eq": 0x3a2e17, "lyd": 0x2a3340, "tilkobling": 0x22314a, "radio": 0x3d2a2a, "stemme": 0x2f2a40, "skjerm": 0x2a3a33, "strom": 0x40362a, "system": 0x333335, "oppdatering": 0x1f3a3a, "utgang": 0x2a3340]

    var body: some View {
        let cats = m.cats
        if m.setCat < 0 || m.setCat >= cats.count {
            top(cats)
        } else {
            let cat = cats[m.setCat]
            SKBackButton(title: "Innstillinger") { m.setCat = -1; m.openK = "" }
            if cat.id == "radio" {
                Text("Favoritter").sora(17, .semibold)
                if m.rAdd { RadioAddView() } else { RadioFavoritesView() }
                Text("Knapper og oppstart").sora(17, .semibold).padding(.top, 6)
            }
            if cat.id == "oppdatering" {
                UpdateSettingsView()
            } else {
                if cat.id == "skjerm" { ClockPicker() }
                SettingItemsCard(items: cat.items.filter { $0.kind != .update && $0.kind != .clocks })
            }
        }
    }

    @ViewBuilder private func top(_ cats: [SettingCategory]) -> some View {
        let dev = m.devRoom
        EdgeScroll(spacing: 6) {
            ForEach(m.sys.rooms) { r in
                let s = SelStyle.of(r.id == dev.id)
                Button { m.setDev = r.id; m.setCat = -1 } label: {
                    VStack(alignment: .leading, spacing: 1) {
                        SKIcon(d: SK.dev(r.type).icon, size: 30, stroke: 1.2, color: .ink2)
                        Text(r.name).sora(13, .regular, s.fg).lineLimit(1).fixedSize()
                        Text(SK.dev(r.type).n).mono(9.5).lineLimit(1).fixedSize()
                    }
                    .padding(.horizontal, 12).padding(.vertical, 8)
                    .background(RoundedRectangle(cornerRadius: 12, style: .continuous).fill(s.bg))
                    .skBorder(s.bd, radius: 12)
                }
                .plain()
            }
        }
        Text(AppModel.hwText(dev) + (dev.type == "node" ? " · ingen skjerm eller knapper" : "")).sora(11, .regular, .muted)
        VStack(spacing: 0) {
            ForEach(Array(cats.enumerated()), id: \.offset) { i, c in
                Button { m.setCat = i; m.openK = ""; m.confirm = "" } label: {
                    HStack(spacing: 10) {
                        HStack(spacing: 12) {
                            SKIcon(d: Self.catIcon[c.id] ?? "", size: 18, stroke: 1.8, color: .ink)
                                .frame(width: 32, height: 32)
                                .background(RoundedRectangle(cornerRadius: 8, style: .continuous).fill(Color(hex: Self.catTile[c.id] ?? 0x333333)))
                            VStack(alignment: .leading, spacing: 2) {
                                Text(c.n).sora(14)
                                Text(c.sub).sora(11, .regular, .muted).fixedSize(horizontal: false, vertical: true)
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)
                        }
                        SKIcon(d: Icons.chevronRight, size: 16, stroke: 2, color: .muted)
                    }
                    .padding(.vertical, 8).padding(.horizontal, 14)
                    .frame(minHeight: 58)
                    .topLine(i > 0 ? .line : .clear)
                }
                .plain()
            }
        }
        .skBox(.card, .line)
        appSection
    }

    /// App-level settings (not stored on the amplifier): choice of tab bar design.
    private var appSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            SKMonoLabel(text: "APPEN").padding(.top, 6)
            VStack(alignment: .leading, spacing: 12) {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Fanelinje").sora(14)
                    Text("Liquid Glass svever over innholdet. Klassisk er det opprinnelige designet.").sora(11, .regular, .muted)
                        .fixedSize(horizontal: false, vertical: true)
                }
                HStack(spacing: 10) {
                    styleOption("glass", "Liquid Glass")
                    styleOption("classic", "Klassisk")
                }
            }
            .padding(14)
            .skBox(.card, .line)
        }
    }

    private func styleOption(_ key: String, _ label: String) -> some View {
        let on = m.tabStyle == key
        let s = SelStyle.of(on)
        return Button {
            guard !on else { return }
            Haptics.tick()
            withAnimation(.spring(response: 0.4, dampingFraction: 0.85)) { m.tabStyle = key }
        } label: {
            VStack(spacing: 10) {
                TabStylePreview(glass: key == "glass").frame(height: 54)
                HStack {
                    Text(label).sora(12, .regular, s.fg)
                    Spacer()
                    Text(on ? "✓" : "").sora(12, .regular, .accent2)
                }
            }
            .padding(10)
            .background(RoundedRectangle(cornerRadius: 12, style: .continuous).fill(s.bg))
            .skBorder(s.bd, radius: 12)
        }
        .plain()
    }
}

/// Small sketch of each tab bar style for the picker.
private struct TabStylePreview: View {
    let glass: Bool
    var body: some View {
        ZStack(alignment: .bottom) {
            LinearGradient(colors: [Color(hex: 0x1f3a40), Color(hex: 0x14161c)], startPoint: .topLeading, endPoint: .bottomTrailing)
            if glass {
                HStack(spacing: 0) {
                    ForEach(0..<4, id: \.self) { i in
                        Circle().fill(i == 0 ? Color.accent2 : Color.ink.opacity(0.6)).frame(width: 5, height: 5)
                            .frame(maxWidth: .infinity, maxHeight: .infinity)
                            .background { if i == 0 { Capsule().fill(Color.ink.opacity(0.14)).padding(2) } }
                    }
                }
                .frame(height: 18)
                .padding(2)
                .glassEffect(.regular, in: .capsule)
                .padding(.horizontal, 8).padding(.bottom, 6)
            } else {
                HStack(spacing: 0) {
                    ForEach(0..<4, id: \.self) { i in
                        Circle().fill(i == 0 ? Color.accent2 : Color.muted).frame(width: 5, height: 5).frame(maxWidth: .infinity)
                    }
                }
                .frame(height: 18)
                .background(Color(hex: 0x121213))
                .topLine(Color(hex: 0x232325))
            }
        }
        .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
    }
}

// MARK: - Item rows

struct SettingItemsCard: View {
    @Environment(AppModel.self) private var m
    let items: [SettingItem]

    var body: some View {
        VStack(spacing: 0) {
            ForEach(Array(items.enumerated()), id: \.offset) { i, d in
                row(d).padding(.vertical, 12).padding(.horizontal, 14).topLine(i > 0 ? .line : .clear)
            }
        }
        .skBox(.card, .line)
    }

    @ViewBuilder private func row(_ d: SettingItem) -> some View {
        let v = m.sset[d.k] ?? SK.def[d.k] ?? 0
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 10) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(d.n).sora(14)
                    if let h = d.hint { Text(h).sora(11, .regular, .muted).fixedSize(horizontal: false, vertical: true) }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                control(d, v)
            }
            .frame(minHeight: 30)
            extra(d, v)
        }
    }

    @ViewBuilder private func control(_ d: SettingItem, _ v: Int) -> some View {
        switch d.kind {
        case .bool:
            SKToggle(on: v != 0) { m.setS(d.k, v != 0 ? 0 : 1) }
        case let .num(mn, mx, f):
            HStack(spacing: 6) {
                stepButton("−") { m.setS(d.k, max(mn, v - 1)) }
                Text(f.format(v)).mono(12, .ink).frame(minWidth: 52)
                stepButton("+") { m.setS(d.k, min(mx, v + 1)) }
            }
        case let .opt(list):
            let open = m.openK == d.k
            Button { m.openK = open ? "" : d.k } label: {
                Text("\(list[min(max(0, v), list.count - 1)]) \(open ? "⌃" : "›")").sora(13, .regular, .muted).lineLimit(1)
            }
            .plain()
        case let .info(val, key):
            Text(val ?? info(key)).mono(12, .ink2).multilineTextAlignment(.trailing)
        case let .act(id, label, safe):
            TimelineView(.periodic(from: .now, by: 1)) { tl in
                let c = m.confirm == id
                let text = actLabel(id, label, c, tl.date)
                Button { m.runAction(id, safe: safe) } label: {
                    Text(text.0).sora(12, .regular, text.1).lineLimit(1)
                        .padding(.horizontal, 12).frame(height: 32)
                        .background(RoundedRectangle(cornerRadius: 8, style: .continuous).fill(Color.card2))
                        .skBorder(c ? .live : .line2, radius: 8)
                }
                .plain()
            }
            .fixedSize()
        case let .str(ph, long, max, _):
            if !long {
                SKField(placeholder: ph, text: nameBinding(d.k, max), height: 34, size: 13, radius: 8, bg: .card2, maxLength: max)
                    .frame(width: 130)
            }
        case .eq:
            SKLinkButton(title: "Åpne ›") { m.tab = 1 }
        default:
            EmptyView()
        }
    }

    @ViewBuilder private func extra(_ d: SettingItem, _ v: Int) -> some View {
        switch d.kind {
        case let .str(ph, true, max, secret):
            SKField(placeholder: ph, text: nameBinding(d.k, max), height: 40, size: 13, radius: 8, bg: .card2, secure: secret, plainInput: true, maxLength: max)
        case let .steps(steps):
            VStack(alignment: .leading, spacing: 8) {
                ForEach(Array(steps.enumerated()), id: \.offset) { j, t in
                    HStack(alignment: .firstTextBaseline, spacing: 8) {
                        Text("\(j + 1)").mono(12, .accent).frame(width: 18, alignment: .leading)
                        Text(t).sora(12, .regular, .ink2, lineHeight: 1.45).fixedSize(horizontal: false, vertical: true)
                    }
                }
            }
        case let .opt(list) where m.openK == d.k:
            FlowLayout(spacing: 6) {
                ForEach(Array(list.enumerated()), id: \.offset) { j, label in
                    SKChip(label: label, on: v == j, height: 34) { m.setS(d.k, j); m.openK = "" }
                }
            }
        default:
            EmptyView()
        }
    }

    private func stepButton(_ s: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(s).sora(14).frame(width: 32, height: 32)
                .background(RoundedRectangle(cornerRadius: 8, style: .continuous).fill(Color.card2))
                .skBorder(.line2, radius: 8)
        }
        .plain()
    }

    private func nameBinding(_ k: String, _ max: Int) -> Binding<String> {
        Binding(get: {
            let defaults = ["nAux1": "AUX 1", "nAux2": "AUX 2", "nUsb1": "PC", "nUsb2": "Switch"]
            return m.names[k] ?? defaults[k] ?? ""
        }, set: { v in
            if k == "ytmCookie" { m.ytmT = nil }
            if k == "plexUrl" || k == "plexToken" { m.plexT = nil }
            m.saveName(k, String(v.prefix(max)))
        })
    }

    private func info(_ key: String?) -> String {
        switch key {
        case "btDev": return "Sebastians iPhone, MacBook Pro"
        case "lyrion": return "Tilkoblet"
        default: return ""
        }
    }

    private func actLabel(_ id: String, _ label: String, _ confirm: Bool, _ now: Date) -> (String, Color) {
        if id == "ytmTest", m.ytmT != nil {
            let c = (m.names["ytmCookie"] ?? "").trimmingCharacters(in: .whitespaces)
            if c.isEmpty { return ("Lim inn cookien først", .danger) }
            if !c.contains("__Secure-3PAPISID") { return ("Mangler __Secure-3PAPISID · hent på nytt", .danger) }
            return ("Innlogget · Premium", .ok)
        }
        if id == "plexTest", let t = m.plexT {
            return t == "busy" ? ("Tester …", .ink2) : (t, m.plexOK ? .ok : .danger)
        }
        if id == "btPair", let t = m.btPairT, now.timeIntervalSince(t) < 120 {
            return ("Synlig · \(Int(ceil(120 - now.timeIntervalSince(t)))) s", .ink)
        }
        return confirm ? ("Trykk igjen", .danger) : (label, .ink)
    }
}

// MARK: - 19 Radio favourites

private func stationAbbr(_ n: String) -> String {
    let s = (n.hasPrefix("NRK ") ? String(n.dropFirst(4)) : n).replacingOccurrences(of: "Radio ", with: "")
    return String(s.split(separator: " ").map { String($0.prefix(4)) }.joined(separator: " ").prefix(7))
}

struct RadioFavoritesView: View {
    @Environment(AppModel.self) private var m

    var body: some View {
        let rl = m.radio
        HStack {
            Text("\(rl.count) " + (rl.count == 1 ? "favoritt" : "favoritter")).sora(12, .regular, .muted)
            Spacer()
            SKLinkButton(title: m.rEdit ? "Ferdig" : "Endre rekkefølge") { m.rEdit.toggle() }.padding(.vertical, 4)
        }
        VStack(spacing: 0) {
            ForEach(Array(rl.enumerated()), id: \.offset) { i, st in
                let playing = m.input == 3 && m.stIdx == i && m.rTmp == nil
                let a = art(st.name)
                HStack(spacing: 10) {
                    ZStack {
                        ArtFill(a)
                        Text(stationAbbr(st.name)).sora(10, .semibold, a.ink).multilineTextAlignment(.center)
                    }
                    .frame(width: 38, height: 38)
                    .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                    Button { m.playStation(i, open: false) } label: {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(st.name).sora(14)
                            Text(st.genre).sora(11, .regular, .muted)
                        }
                        .padding(.vertical, 8)
                        .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    .plain()
                    if m.rEdit {
                        HStack(spacing: 4) {
                            editButton(Icons.chevronUp, fg: i > 0 ? .ink : .off, bd: .line2, label: "Flytt opp") {
                                guard i > 0 else { return }
                                var l = m.radio; l.swapAt(i - 1, i); m.setRL(l)
                            }
                            editButton(Icons.chevronDown, fg: i < rl.count - 1 ? .ink : .off, bd: .line2, label: "Flytt ned") {
                                guard i < m.radio.count - 1 else { return }
                                var l = m.radio; l.swapAt(i + 1, i); m.setRL(l)
                            }
                            editButton(Icons.close, fg: .danger, bd: Color(hex: 0x4a2522), label: "Fjern") {
                                guard m.radio.count > 1 else { return }
                                var l = m.radio; l.remove(at: i); m.setRL(l)
                            }
                        }
                    } else {
                        HStack(spacing: 8) {
                            Text(playing ? "Spiller" : "").sora(11, .regular, .accent2)
                            Button { m.fav = i; m.post(["type": "set", "k": "hold", "v": i]) } label: {
                                Text("★").font(.system(size: 15)).foregroundStyle(m.fav == i ? Color.accent2 : .off)
                                    .frame(width: 32, height: 32)
                            }
                            .plain()
                            .accessibilityLabel("Favoritt på radioknappen")
                        }
                    }
                }
                .padding(.horizontal, 12).frame(minHeight: 58)
                .background(playing ? Color.selBg : .clear)
                .topLine(i > 0 ? .line : .clear)
            }
        }
        .skBox(.card, .line)
        let full = m.radioFull
        Button { if !full { m.rAdd = true; m.q = "" } } label: {
            Text(full ? "Maks \(SK.maxRadio) favoritter · fjern én for å legge til" : "+ Legg til kanal")
                .sora(13, .regular, full ? .muted : .accent2)
                .frame(maxWidth: .infinity).frame(height: 46)
                .skBorder(full ? .line2 : .selLine, radius: 14, dash: [4, 3])
        }
        .plain()
        Text("Rekkefølgen er den samme som på radioknappen. ★ spilles når du holder radioknappen inne.")
            .sora(11, .regular, .muted).fixedSize(horizontal: false, vertical: true)
    }

    private func editButton(_ d: String, fg: Color, bd: Color, label: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            SKIcon(d: d, size: 14, stroke: 2.2, color: fg)
                .frame(width: 30, height: 30)
                .background(RoundedRectangle(cornerRadius: 8, style: .continuous).fill(Color.card2))
                .skBorder(bd, radius: 8)
        }
        .plain()
        .accessibilityLabel(label)
    }
}

/// Add favourites: search (catalogue + Radio Browser) or a custom stream URL.
struct RadioAddView: View {
    @Environment(AppModel.self) private var m

    var body: some View {
        @Bindable var m = m
        SKBackButton(title: "Favoritter") { m.rAdd = false }
        SKSegmented(items: ["Søk", "Fra URL"], selected: m.rMode == "url" ? 1 : 0) { i in m.rMode = i == 1 ? "url" : "sok" }
        if m.rMode == "sok" {
            let ql = m.q.trimmingCharacters(in: .whitespaces).lowercased()
            SKField(placeholder: "Søk etter kanal, by eller sjanger", text: Binding(get: { m.q }, set: { m.setQ($0) }), height: 44, size: 15)
            SKMonoLabel(text: "NORSKE KANALER")
            let cat = SK.catalog.filter { ql.isEmpty || ($0.name + " " + $0.genre).lowercased().contains(ql) }
            addList(cat)
            if m.rBusy { Text("Søker i Radio Browser …").sora(12, .regular, .muted) }
            let onl = (m.rRes ?? []).filter { s in !SK.catalog.contains { $0.name.lowercased() == s.name.lowercased() } }.map { s in
                Station(name: s.name, genre: [s.genre, s.country, s.br > 0 ? "\(s.br) kbps" : s.codec].filter { !$0.isEmpty }.joined(separator: " · "), url: s.url)
            }
            if !onl.isEmpty {
                SKMonoLabel(text: "FRA RADIO BROWSER")
                addList(onl, newGenre: { st in m.rRes?.first { $0.name == st.name }?.genre.nilIfEmpty ?? "Nettradio" })
            }
            if ql.count < 3 {
                Text("Skriv minst tre bokstaver for å søke blant over 50 000 kanaler fra hele verden.")
                    .sora(12, .regular, .muted, lineHeight: 1.45).fixedSize(horizontal: false, vertical: true)
            }
        } else {
            urlForm
        }
    }

    private func addList(_ list: [Station], newGenre: ((Station) -> String)? = nil) -> some View {
        VStack(spacing: 0) {
            ForEach(Array(list.enumerated()), id: \.offset) { i, st in
                let has = m.favIndex(st.name) != nil || m.radio.contains { $0.name.lowercased() == st.name.lowercased() }
                let full = m.radioFull
                let a = art(st.name)
                HStack(spacing: 10) {
                    ZStack {
                        ArtFill(a)
                        Text(stationAbbr(st.name)).sora(9, .semibold, a.ink).multilineTextAlignment(.center)
                    }
                    .frame(width: 34, height: 34)
                    .clipShape(RoundedRectangle(cornerRadius: 7, style: .continuous))
                    VStack(alignment: .leading, spacing: 2) {
                        Text(st.name).sora(14).lineLimit(1)
                        Text(st.genre).sora(11, .regular, .muted).lineLimit(1)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    Button {
                        guard !has && !full else { return }
                        m.setRL(m.radio + [Station(name: st.name, genre: newGenre?(st) ?? st.genre, url: st.url)])
                    } label: {
                        Text(has ? "Lagt til" : full ? "Fullt" : "Legg til").sora(12, .regular, has || full ? .muted : .accent2)
                            .padding(.horizontal, 12).frame(height: 30)
                            .skCapsuleBorder(has || full ? .line2 : .accent)
                    }
                    .plain()
                }
                .padding(.horizontal, 12).frame(minHeight: 52)
                .topLine(i > 0 ? .line : .clear)
            }
        }
        .skBox(.card, .line)
    }

    @ViewBuilder private var urlForm: some View {
        @Bindable var m = m
        let u = m.uUrl.trimmingCharacters(in: .whitespaces)
        let okUrl = u.range(of: #"^https?://\S+\.\S+"#, options: [.regularExpression, .caseInsensitive]) != nil
        let nm = m.uName.trimmingCharacters(in: .whitespaces)
        let isPl = u.range(of: #"\.(m3u8?|pls)(\?|$)"#, options: [.regularExpression, .caseInsensitive]) != nil
        let has = m.radio.contains { $0.name.lowercased() == nm.lowercased() }
        let full = m.radioFull
        let canAdd = okUrl && !nm.isEmpty && !full && !has
        let msg: (String, Color) = u.isEmpty ? ("Støtter MP3, AAC, OGG, FLAC og spillelister (.m3u, .pls).", .muted)
            : !okUrl ? ("Adressen må starte med http:// eller https://", .danger)
            : m.uTest == "busy" ? ("Tester strømmen …", .ink2)
            : m.uTest == "ok" ? ("Strømmen virker.", .ok)
            : m.uTest == "bad" ? (isPl ? ("Spilleliste. Lyrion henter strømmen fra den ved avspilling.", .ink2) : ("Fikk ikke kontakt med strømmen. Sjekk adressen.", .danger))
            : ("Trykk Test for å sjekke at strømmen virker.", .muted)
        VStack(alignment: .leading, spacing: 10) {
            SKField(placeholder: "Navn, for eksempel Jazzradio", text: Binding(get: { m.uName }, set: { m.uName = String($0.prefix(40)); m.uDone = "" }), height: 44, size: 15)
            SKField(placeholder: "https://… strømadresse", text: Binding(get: { m.uUrl }, set: { m.uUrl = $0; m.uTest = nil; m.uDone = "" }),
                    height: 44, size: 13, mono: true, keyboard: .URL, plainInput: true)
            SKField(placeholder: "Sjanger (valgfritt)", text: Binding(get: { m.uGenre }, set: { m.uGenre = String($0.prefix(30)) }), height: 44, size: 15)
            Text(msg.0).sora(12, .regular, msg.1, lineHeight: 1.45).fixedSize(horizontal: false, vertical: true)
            HStack(spacing: 8) {
                Button { if okUrl { m.testCustomStream() } } label: {
                    Text("Test").sora(14).padding(.horizontal, 18).frame(height: 44)
                        .background(RoundedRectangle(cornerRadius: 12, style: .continuous).fill(Color.card2))
                        .skBorder(.line2, radius: 12)
                }
                .plain()
                Button {
                    guard canAdd else { return }
                    let g = m.uGenre.trimmingCharacters(in: .whitespaces)
                    m.setRL(m.radio + [Station(name: nm, genre: g.isEmpty ? "Egen strøm" : g, url: u)])
                    m.uName = ""; m.uUrl = ""; m.uGenre = ""; m.uTest = nil; m.uDone = nm
                } label: {
                    Text(full ? "Fullt · fjern en favoritt først" : !nm.isEmpty && has ? "Finnes allerede" : "Legg til i favoritter")
                        .sora(14, .semibold, canAdd ? .bg : .dim).lineLimit(1)
                        .frame(maxWidth: .infinity).frame(height: 44)
                        .background(RoundedRectangle(cornerRadius: 12, style: .continuous).fill(canAdd ? Color.accent : .line))
                }
                .plain()
            }
            if !m.uDone.isEmpty { Text("«\(m.uDone)» er lagt til i favorittene.").sora(12, .regular, .ok) }
        }
    }
}

private extension String {
    var nilIfEmpty: String? { isEmpty ? nil : self }
}

// MARK: - Oppdatering

struct UpdateSettingsView: View {
    @Environment(AppModel.self) private var m
    @Environment(\.openURL) private var openURL

    var body: some View {
        let u = m.upd
        let busy = m.job.map { !$0.done } ?? false
        let idle = !busy && !m.checking
        let msg: (String, Bool)? = {
            if let j = m.job, j.done, let ju = j.upd {
                return j.failed ? ("Oppdateringen feilet ved oppstart. Forrige versjon (\(ju.version)) er gjenopprettet automatisk, og alt virker som før.", true)
                                : ("Ferdig. Skjold \(ju.version) kjører nå.", false)
            }
            return m.updMsg.isEmpty ? nil : (m.updMsg, false)
        }()

        VStack(alignment: .leading, spacing: 14) {
            VStack(alignment: .leading, spacing: 12) {
                HStack(alignment: .top, spacing: 12) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Installert").sora(12, .regular, .muted)
                        Text("Skjold \(u.version)").sora(22, .semibold)
                    }
                    Spacer()
                    link("github.com/\(u.repo) ↗", "https://github.com/\(u.repo)/releases")
                }
                HStack(spacing: 6) {
                    ForEach(Array(["Stabil", "Beta"].enumerated()), id: \.offset) { i, label in
                        let on = u.channel == i
                        SKChip(label: label, height: 32, radius: 14,
                               style: SelStyle(bd: on ? .accent : .line2, bg: on ? .selBg2 : .card2, fg: on ? .accent2 : .ink)) {
                            m.upd.channel = i; m.upd.latest = nil
                        }
                    }
                }
                HStack(spacing: 12) {
                    Text("Installer automatisk om natten").sora(13)
                    Spacer()
                    SKToggle(on: u.auto) { m.upd.auto.toggle() }
                }
                HStack(spacing: 12) {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Demo: la neste oppdatering feile").sora(13)
                        Text("Viser automatisk gjenoppretting").sora(11, .regular, .muted)
                    }
                    Spacer()
                    SKToggle(on: u.failNext, onColor: .live) { m.upd.failNext.toggle() }
                }
                if idle || m.checking {
                    Button { if idle { m.checkUpdate() } } label: {
                        Text(m.checking ? "Sjekker GitHub …" : "Se etter oppdatering").sora(13)
                            .frame(maxWidth: .infinity).frame(height: 42)
                            .background(RoundedRectangle(cornerRadius: 14, style: .continuous).fill(Color.card2))
                            .skBorder(.line2, radius: 14)
                    }
                    .plain()
                }
                if let msg, !busy {
                    Text(msg.0).sora(13, .regular, msg.1 ? Color(hex: 0xff9a8a) : Color(hex: 0x9be0a8), lineHeight: 1.45)
                        .fixedSize(horizontal: false, vertical: true)
                        .padding(.vertical, 10).padding(.horizontal, 12)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .skBox(msg.1 ? Color(hex: 0x2a1412) : Color(hex: 0x16201a), msg.1 ? Color(hex: 0x5a2620) : Color(hex: 0x2a4a33), radius: 8)
                }
            }
            .padding(18)
            .skBox(.card, .line)

            if let rel = u.latest, !busy {
                VStack(alignment: .leading, spacing: 10) {
                    HStack(alignment: .firstTextBaseline) {
                        Text(rel.name).sora(16, .semibold)
                        Spacer()
                        Text("\(rel.tag) · \(rel.date) · \(rel.size)").mono(11, Color(hex: 0xc9b48a))
                    }
                    VStack(alignment: .leading, spacing: 4) {
                        ForEach(rel.notes, id: \.self) { Text("· " + $0).sora(13, .regular, Color(hex: 0xe8dcc4), lineHeight: 1.45) }
                    }
                    HStack(spacing: 10) {
                        if idle {
                            Button { m.installUpdate() } label: {
                                Text("Installer \(rel.tag)").sora(13, .semibold, .bg).padding(.horizontal, 16).frame(height: 40)
                                    .background(RoundedRectangle(cornerRadius: 14, style: .continuous).fill(Color.accent))
                            }
                            .plain()
                        }
                        link("Se på GitHub ↗", "https://github.com/\(u.repo)/releases/tag/\(rel.tag)")
                    }
                    Text("Det tas automatisk backup før installering. Hvis forsterkeren ikke starter etterpå, gjenopprettes forrige versjon.")
                        .sora(11, .regular, Color(hex: 0xc9b48a)).fixedSize(horizontal: false, vertical: true)
                }
                .padding(18)
                .skBox(.selBg, .selLine)
            }

            if busy, let j = m.job {
                VStack(alignment: .leading, spacing: 10) {
                    HStack {
                        Text(j.step).sora(13)
                        Spacer()
                        Text("\(j.pct) %").mono(12)
                    }
                    GeometryReader { g in
                        ZStack(alignment: .leading) {
                            Color.line
                            Color.accent.frame(width: g.size.width * CGFloat(j.pct) / 100)
                        }
                    }
                    .frame(height: 6).clipShape(RoundedRectangle(cornerRadius: 3))
                    Text("Ikke slå av forsterkeren.").sora(11, .regular, .muted)
                }
                .padding(18)
                .skBox(.card, .line)
            }

            HStack {
                Text("Backup").sora(14, .semibold)
                Spacer()
                if idle { SKLinkButton(title: "Ta backup nå") { m.backupNow() }.padding(.vertical, 4) }
            }
            VStack(spacing: 0) {
                ForEach(Array(u.backups.enumerated()), id: \.offset) { i, b in
                    let cur = b.ver == u.version, c = m.restoreConf == b.id
                    HStack(spacing: 10) {
                        VStack(alignment: .leading, spacing: 2) {
                            Text("\(b.ver) \(cur ? "· installert" : "")").sora(14)
                            Text("\(b.date) · \(b.kind)").sora(11, .regular, .muted)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        if !busy && !cur {
                            Button { m.restore(b) } label: {
                                Text(c ? "Trykk igjen" : "Gjenopprett").sora(12, .regular, c ? .danger : .ink)
                                    .padding(.horizontal, 12).frame(height: 32)
                                    .background(RoundedRectangle(cornerRadius: 8, style: .continuous).fill(Color.card2))
                                    .skBorder(c ? .live : .line2, radius: 8)
                            }
                            .plain()
                        }
                    }
                    .padding(.vertical, 12).padding(.horizontal, 14)
                    .topLine(i > 0 ? .line : .clear)
                }
            }
            .skBox(.card, .line)

            if !u.log.isEmpty {
                Text("Historikk").sora(14, .semibold)
                VStack(alignment: .leading, spacing: 6) {
                    ForEach(Array(u.log.enumerated()), id: \.offset) { _, l in
                        HStack(alignment: .firstTextBaseline, spacing: 10) {
                            Text(l.date).mono(12)
                            Text(l.text).sora(12, .regular, l.bad ? Color(hex: 0xff9a8a) : .ink2, lineHeight: 1.4)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                }
            }
        }
    }

    private func link(_ title: String, _ url: String) -> some View {
        Button { if let u = URL(string: url) { openURL(u) } } label: { Text(title).sora(12, .regular, .accent).lineLimit(1) }.plain()
    }
}

// MARK: - Standby clocks (Skjerm og lys)

struct ClockPicker: View {
    @Environment(AppModel.self) private var m

    var body: some View {
        let sel = m.sset["clockStyle"] ?? 0
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .firstTextBaseline) {
                Text("Klokke i standby").sora(14, .semibold)
                Spacer()
                SKLinkButton(title: "Vis på forsterkeren", size: 12) { m.post(["type": "previewClock"]) }
            }
            LazyVGrid(columns: [GridItem(.adaptive(minimum: 130), spacing: 10)], spacing: 10) {
                ForEach(Array(SK.clocks.enumerated()), id: \.offset) { i, label in
                    let on = sel == i
                    Button { m.setS("clockStyle", i) } label: {
                        VStack(alignment: .leading, spacing: 8) {
                            TimelineView(.everyMinute) { tl in
                                ClockFace(style: i, date: tl.date, color: on ? Color(hex: 0xe8e8e2) : .muted)
                            }
                            .aspectRatio(2, contentMode: .fit)
                            .background(Color.black)
                            .clipShape(RoundedRectangle(cornerRadius: 6))
                            HStack {
                                Text(label)
                                Spacer()
                                Text(on ? "✓" : "")
                            }
                            .sora(12, .regular, on ? .accent2 : .ink2)
                            .padding(.horizontal, 2)
                        }
                        .padding(8)
                        .skBox(on ? .selBg : .card, on ? .accent : .line)
                    }
                    .plain()
                }
            }
            Text("Vises dempet på skjermen og flytter seg litt hvert minutt for å unngå innbrenning.").sora(11, .regular, .muted)
                .fixedSize(horizontal: false, vertical: true)
        }
    }
}

/// drawClock(): 128×64 logical OLED pixels, scaled to fit.
struct ClockFace: View {
    let style: Int
    let date: Date
    let color: Color

    private static let hw = ["tolv", "ett", "to", "tre", "fire", "fem", "seks", "sju", "åtte", "ni", "ti", "elleve", "tolv"]
    private static let days = ["søndag", "mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag"]
    private static let months = ["januar", "februar", "mars", "april", "mai", "juni", "juli", "august", "september", "oktober", "november", "desember"]

    var body: some View {
        Canvas { g, size in
            let k = size.width / 128, oy = (size.height - 64 * k) / 2
            let cal = Calendar.current
            let h = cal.component(.hour, from: date), mi = cal.component(.minute, from: date)
            let hh = String(format: "%02d", h), mm = String(format: "%02d", mi)
            let wd = cal.component(.weekday, from: date) - 1, day = cal.component(.day, from: date), mon = cal.component(.month, from: date) - 1
            func text(_ s: String, _ weight: String, _ px: CGFloat, _ x: CGFloat, _ y: CGFloat, _ align: CGFloat = 0.5) {
                let name = weight == "300" ? "HelveticaNeue-Light" : weight == "600" ? "HelveticaNeue-Medium" : weight == "700" ? "HelveticaNeue-Bold" : "HelveticaNeue"
                let t = g.resolve(Text(s).font(.custom(name, fixedSize: px * k)).foregroundStyle(color))
                // canvas baseline: anchor at the bottom of the glyph box minus the descender
                g.draw(t, at: CGPoint(x: x * k, y: oy + y * k + px * k * 0.22), anchor: UnitPoint(x: align, y: 1))
            }
            func fill(_ r: CGRect) { g.fill(Path(CGRect(x: r.minX * k, y: oy + r.minY * k, width: r.width * k, height: r.height * k)), with: .color(color)) }
            switch style {
            case 0: text(hh + ":" + mm, "300", 22, 64, 40)
            case 1: text(hh + ":" + mm, "700", 40, 64, 47)
            case 2:
                let cx: CGFloat = 40, cy: CGFloat = 32, r: CGFloat = 24
                var p = Path()
                p.addEllipse(in: CGRect(x: (cx - r) * k, y: oy + (cy - r) * k, width: 2 * r * k, height: 2 * r * k))
                for i in 0..<12 {
                    let a = CGFloat(i) / 12 * .pi * 2, l: CGFloat = i % 3 == 0 ? 4 : 2
                    p.move(to: CGPoint(x: (cx + sin(a) * (r - 1.5)) * k, y: oy + (cy - cos(a) * (r - 1.5)) * k))
                    p.addLine(to: CGPoint(x: (cx + sin(a) * (r - 1.5 - l)) * k, y: oy + (cy - cos(a) * (r - 1.5 - l)) * k))
                }
                g.stroke(p, with: .color(color), lineWidth: k)
                let ha = (CGFloat(h % 12) + CGFloat(mi) / 60) / 12 * .pi * 2, ma = CGFloat(mi) / 60 * .pi * 2
                func hand(_ a: CGFloat, _ len: CGFloat, _ w: CGFloat) {
                    var q = Path()
                    q.move(to: CGPoint(x: cx * k, y: oy + cy * k))
                    q.addLine(to: CGPoint(x: (cx + sin(a) * len) * k, y: oy + (cy - cos(a) * len) * k))
                    g.stroke(q, with: .color(color), style: StrokeStyle(lineWidth: w * k, lineCap: .round))
                }
                hand(ha, 12, 2.4); hand(ma, 19, 1.4)
                g.fill(Path(ellipseIn: CGRect(x: (cx - 1.6) * k, y: oy + (cy - 1.6) * k, width: 3.2 * k, height: 3.2 * k)), with: .color(color))
                text(String(Self.days[wd].prefix(3)).capitalized, "600", 9, 74, 30, 0)
                text("\(day). " + String(Self.months[mon].prefix(3)), "400", 8, 74, 41, 0)
            case 3:
                let (a, b) = wordTime(h, mi)
                text(a, "300", 11, 64, 28); text(b, "600", 15, 64, 45)
            case 4:
                let p = CGFloat(h * 60 + mi) / 1440
                fill(CGRect(x: 8, y: 40, width: 112, height: 0.8))
                for i in stride(from: 0, through: 24, by: 6) { fill(CGRect(x: 8 + 112 * CGFloat(i) / 24 - 0.4, y: 37.5, width: 0.8, height: 5)) }
                g.fill(Path(ellipseIn: CGRect(x: (8 + 112 * p - 2.4) * k, y: oy + (40.4 - 2.4) * k, width: 4.8 * k, height: 4.8 * k)), with: .color(color))
                text(hh + ":" + mm, "400", 10, 8 + 112 * p, 31, p > 0.75 ? 1 : p < 0.25 ? 0 : 0.5)
            default:
                text(hh + ":" + mm, "300", 26, 64, 34)
                text(Self.days[wd].capitalized + " \(day). " + Self.months[mon], "400", 8, 64, 48)
            }
        }
    }

    private func wordTime(_ hour: Int, _ minute: Int) -> (String, String) {
        let m = Int((Double(minute) / 5).rounded()) * 5 % 60
        let h0 = hour + (minute >= 58 ? 1 : 0), h = h0 % 12
        let n = Self.hw[h == 0 ? 12 : h], n1 = Self.hw[(h + 1) % 12 == 0 ? 12 : (h + 1) % 12]
        let table = [("klokka er", n), ("fem over", n), ("ti over", n), ("kvart over", n), ("ti på halv", n1), ("fem på halv", n1),
                     ("halv", n1), ("fem over halv", n1), ("ti over halv", n1), ("kvart på", n1), ("ti på", n1), ("fem på", n1)]
        return table[m / 5]
    }
}
