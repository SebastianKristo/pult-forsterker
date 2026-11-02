import SwiftUI

/// 16 Radio + 17 Radio, søk (radioDisc() in the design).
struct RadioView: View {
    @Environment(AppModel.self) private var m

    static let genres: [(String, String)] = [("Pop og hits", "pop|hit|mp3|ung"), ("Nyheter og prat", "nyhet|samfunn|kultur|prat|distrikt|sport|debatt"),
                                             ("Klassisk", "klassisk|opera"), ("Jazz", "jazz"), ("Rock", "rock|metal"), ("Lokal", "lokal|distrikt|region")]

    private var gs: [(String, [Station])] {
        Self.genres.map { n, re in
            (n, SK.catalog.filter { ($0.genre + " " + $0.name).range(of: re, options: [.regularExpression, .caseInsensitive]) != nil })
        }.filter { !$0.1.isEmpty }
    }

    var body: some View {
        let q = m.q.trimmingCharacters(in: .whitespaces).lowercased()
        VStack(alignment: .leading, spacing: 10) {
            SKField(placeholder: "Søk etter kanal, by eller sjanger",
                    text: Binding(get: { m.q }, set: { m.setQ($0) }), height: 44, size: 15)
            Button { m.goRadioSettings() } label: {
                HStack(spacing: 8) {
                    SKIcon(d: Icons.favList, size: 15, stroke: 1.8)
                    Text("Favoritter").sora(13)
                }
                .foregroundStyle(Color.ink)
                .padding(.horizontal, 14).frame(height: 44)
                .background(RoundedRectangle(cornerRadius: 12, style: .continuous).fill(Color.card2))
                .skBorder(.line2, radius: 12)
            }
            .plain()
        }
        if q.isEmpty { discover } else { search(q) }
    }

    // MARK: Search

    @ViewBuilder private func search(_ q: String) -> some View {
        let loc = SK.catalog.filter { ($0.name + " " + $0.genre).lowercased().contains(q) }
        let onl: [Station] = (m.rRes ?? []).filter { s in !loc.contains { $0.name.lowercased() == s.name.lowercased() } }.map { s in
            let g = [s.genre, s.country, s.br > 0 ? "\(s.br) kbps" : ""].filter { !$0.isEmpty }.joined(separator: " · ")
            return Station(name: s.name, genre: g.isEmpty ? "Nettradio" : g, url: s.url)
        }
        if !loc.isEmpty {
            SKMonoLabel(text: "NORSKE KANALER")
            stationList(loc)
        }
        if m.rBusy { Text("Søker i Radio Browser …").sora(12, .regular, .muted) }
        if !onl.isEmpty {
            SKMonoLabel(text: "FRA HELE VERDEN · RADIO BROWSER")
            stationList(onl)
        }
        if !m.rBusy && loc.isEmpty && onl.isEmpty && q.count >= 3 {
            Text("Ingen kanaler funnet. Du kan legge til en strømadresse under Administrer favoritter.").sora(13, .regular, .muted)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private func stationList(_ list: [Station]) -> some View {
        VStack(spacing: 0) {
            ForEach(Array(list.enumerated()), id: \.offset) { i, st in
                let a = art(st.name), f = m.favIndex(st.name) != nil
                HStack(spacing: 12) {
                    Button { m.playRadio(st) } label: {
                        ZStack {
                            ArtFill(a)
                            Text(abbr(st.name, 5)).sora(9, .semibold, a.ink).multilineTextAlignment(.center)
                        }
                        .frame(width: 36, height: 36)
                        .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                    }
                    .plain().accessibilityLabel("Spill")
                    Button { m.playRadio(st) } label: {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(st.name).sora(14).lineLimit(1)
                            Text(st.genre).sora(11, .regular, .muted).lineLimit(1)
                        }
                        .padding(.vertical, 6)
                        .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    .plain()
                    Button { m.toggleFav(st) } label: {
                        Text(f ? "★" : "☆").font(.system(size: 16)).foregroundStyle(f ? Color.accent2 : .muted)
                            .frame(width: 36, height: 36)
                            .background(RoundedRectangle(cornerRadius: 8, style: .continuous).fill(Color.card2))
                            .skBorder(.line2, radius: 8)
                    }
                    .plain().accessibilityLabel("Favoritt")
                }
                .padding(.horizontal, 12).frame(minHeight: 54)
                .topLine(i > 0 ? .line : .clear)
            }
        }
        .skBox(.card, .line)
    }

    private func abbr(_ n: String, _ len: Int) -> String {
        String((n.hasPrefix("NRK ") ? String(n.dropFirst(4)) : n).prefix(len))
    }

    // MARK: Discover

    @ViewBuilder private var discover: some View {
        let gs = self.gs
        let gi = m.rGenre.flatMap { $0 < gs.count ? $0 : nil }
        hero
        EdgeScroll(spacing: 8) {
            SKFilterChip(label: "Alle", on: gi == nil, hPad: 15) { m.rGenre = nil }
            ForEach(Array(gs.enumerated()), id: \.offset) { i, g in
                SKFilterChip(label: g.0, on: gi == i, hPad: 15) { m.rGenre = i }
            }
        }
        let shelves: [(String, String, [Station])] = gi == nil
            ? [("\(m.radio.count)" + (m.radio.count == 1 ? " KANAL" : " KANALER"), "Dine favoritter", m.radio),
               ("", "Populære i Norge", Array(SK.catalog.prefix(14)))] + gs.prefix(2).map { ("SJANGER", $0.0, $0.1) }
            : [("SJANGER", gs[gi!].0, gs[gi!].1)]
        ForEach(Array(shelves.filter { !$0.2.isEmpty }.enumerated()), id: \.offset) { _, sh in
            VStack(alignment: .leading, spacing: 10) {
                SKSectionHeader(title: sh.1, size: 19, kicker: sh.0)
                EdgeScroll(spacing: 12) {
                    ForEach(Array(sh.2.enumerated()), id: \.offset) { _, st in tile(st) }
                }
            }
        }
    }

    private func tile(_ st: Station) -> some View {
        let on = m.curRadioName == st.name
        return Button { m.playRadio(st) } label: {
            VStack(alignment: .leading, spacing: 6) {
                ZStack(alignment: .topLeading) {
                    ArtFill(st.name)
                    if on {
                        Text("DIREKTE").mono(9, .white, em: 0.08)
                            .padding(.horizontal, 6).frame(height: 18)
                            .background(RoundedRectangle(cornerRadius: 4).fill(Color.live))
                            .padding(8)
                    }
                }
                .frame(width: 112, height: 112)
                .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                .skBorder(.line, radius: 12)
                Text(st.name).sora(13).lineLimit(1)
                Text(st.genre).sora(11, .regular, .muted).lineLimit(1)
            }
            .frame(width: 112, alignment: .leading)
        }
        .plain()
    }

    private var hero: some View {
        let cur = m.curRadioName
        let st: Station = (cur.isEmpty ? nil : (m.radio.first { $0.name == cur } ?? SK.catalog.first { $0.name == cur } ?? (m.rTmp?.name == cur ? m.rTmp : nil)))
            ?? m.radio.first ?? SK.catalog[0]
        let fav = m.favIndex(st.name) != nil, live = cur == st.name
        let npH = SK.nowPlaying(st.name)
        let now = npH.0 + (!npH.1.isEmpty && npH.1 != st.name ? " · " + npH.1 : "")
        return VStack(alignment: .leading, spacing: 14) {
            HStack(spacing: 14) {
                Button { m.playRadio(st) } label: {
                    ArtFill(st.name).frame(width: 96, height: 96)
                        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                        .shadow(color: .black.opacity(0.55), radius: 22, y: 18)
                }
                .plain()
                VStack(alignment: .leading, spacing: 6) {
                    HStack(spacing: 8) {
                        Circle().fill(live ? Color.live : .off).frame(width: 7, height: 7)
                        Text(live ? "SPILLER NÅ" : "FRA FAVORITTENE").mono(10, .accent2, em: 0.14)
                    }
                    Text(st.name).sora(22, .semibold, lineHeight: 1.05)
                    Text(st.genre).sora(12, .regular, .ink2)
                    Text(now).sora(12, .regular, .muted).lineLimit(1)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            HStack(spacing: 8) {
                SKPill(title: live ? "Spiller" : "Spill", primary: true, icon: Icons.play, hPad: 18) { m.playRadio(st) }
                SKPill(title: fav ? "★ I favorittene" : "☆ Legg til favoritter", border: .off, bg: Color.bg.opacity(0.4),
                       fg: fav ? .accent2 : .ink) { m.toggleFav(st) }
            }
        }
        .padding(16)
        .background {
            ZStack {
                Color.card
                ArtFill(st.name).padding(-60).blur(radius: 50).opacity(0.5)
                LinearGradient(colors: [Color.bg.opacity(0.35), Color.bg.opacity(0.92)], startPoint: .top, endPoint: .bottom)
            }
        }
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
        .skBorder(.line, radius: 16)
    }
}
