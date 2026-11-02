import SwiftUI

/// 09 Hjem: logo + room pill, active room card, recently played, sources, radio favourites.
struct HomeView: View {
    @Environment(AppModel.self) private var m
    @Environment(\.openURL) private var openURL

    var body: some View {
        let room = m.actRoom
        HStack {
            SKLogo()
            Spacer()
            Button { m.tab = 2 } label: {
                HStack(spacing: 6) {
                    Circle().fill(Color.ok).frame(width: 6, height: 6)
                    Text(m.groupName).sora(12).lineLimit(1)
                }
                .padding(.horizontal, 12).frame(height: 32)
                .background(Capsule().fill(Color.card)).skCapsuleBorder(.line2)
            }
            .plain()
        }

        Button { m.tab = 2 } label: {
            HStack(spacing: 12) {
                SKIcon(d: SK.dev(room.type).icon, size: 24, stroke: 1.5, color: .accent2)
                    .frame(width: 44, height: 44)
                    .background(RoundedRectangle(cornerRadius: 12, style: .continuous).fill(Color.selBg))
                    .skBorder(.selLine, radius: 12)
                VStack(alignment: .leading, spacing: 2) {
                    Text(room.name).sora(15, .semibold)
                    Text(SK.dev(room.type).n).sora(12, .semibold, .accent2)
                    Text(AppModel.hwText(room)).mono(10).lineLimit(1).padding(.top, 2)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                Text("Bytt").sora(12, .regular, .ink2)
                    .padding(.horizontal, 12).frame(height: 28)
                    .skCapsuleBorder(.line2)
            }
            .padding(14)
            .skBox(.card, .line)
        }
        .plain()

        VStack(alignment: .leading, spacing: 10) {
            SKSectionHeader(title: "Nylig spilt")
            EdgeScroll(spacing: 12) {
                ForEach(recent, id: \.title) { r in
                    Button(action: r.pick) {
                        VStack(alignment: .leading, spacing: 6) {
                            let a = art(r.key)
                            ZStack(alignment: .bottomLeading) {
                                ArtFill(a)
                                Text(r.big).sora(14, .semibold, a.ink, lineHeight: 1.05).padding(10)
                            }
                            .frame(width: 118, height: 118)
                            .clipShape(RoundedRectangle(cornerRadius: r.round ? 59 : 10, style: .continuous))
                            Text(r.title).sora(13).lineLimit(1)
                            Text(r.kind).sora(11, .regular, .muted)
                        }
                        .frame(width: 118, alignment: .leading)
                    }
                    .plain()
                }
            }
        }

        VStack(alignment: .leading, spacing: 10) {
            SKSectionHeader(title: "Kilder")
            EdgeScroll(spacing: 14) {
                ForEach(services, id: \.0) { s in
                    SKSourceLogo(label: s.0, action: s.1)
                }
            }
        }

        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .firstTextBaseline) {
                Text("Radiofavoritter").sora(17, .semibold)
                Spacer()
                SKLinkButton(title: "Administrer") { m.sub = "radio" }
            }
            EdgeScroll(spacing: 12) {
                ForEach(Array(m.radio.enumerated()), id: \.offset) { i, st in
                    Button { m.playStation(i) } label: {
                        VStack(alignment: .leading, spacing: 6) {
                            let a = art(st.name)
                            ZStack {
                                ArtFill(a)
                                VStack(alignment: .leading) {
                                    Text("\(i + 1)").mono(9, a.ink).opacity(0.8)
                                    Spacer(minLength: 0)
                                    Text(st.name).sora(13, .semibold, a.ink, lineHeight: 1.05)
                                }
                                .padding(9)
                                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .leading)
                            }
                            .frame(width: 96, height: 96)
                            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                            Text(st.genre).sora(11, .regular, .muted).lineLimit(1)
                        }
                        .frame(width: 96, alignment: .leading)
                    }
                    .plain()
                }
            }
        }
    }

    private struct Recent { var title: String; var key: String; var big: String; var kind: String; var round: Bool; var pick: () -> Void }

    private var recent: [Recent] {
        var out: [Recent] = []
        for i in 0..<2 {
            let t = SK.tr[i]
            out.append(Recent(title: t.0, key: t.0, big: t.1, kind: "AirPlay · låt", round: false) { m.input = 0; m.trk = i; m.full = true })
        }
        for (i, st) in m.radio.prefix(2).enumerated() {
            out.append(Recent(title: st.name, key: st.name, big: st.name, kind: "Radio · kanal", round: true) { m.playStation(i) })
        }
        let t = SK.tr[2]
        out.append(Recent(title: t.0, key: t.0, big: t.1, kind: "Blåtann · låt", round: false) { m.input = 1; m.trk = 2; m.full = true })
        return out
    }

    private var services: [(String, () -> Void)] {
        let node = m.actRoom.type == "node"
        var list: [(String, () -> Void)] = [
            ("Radio", { m.sub = "radio" }),
            ("AirPlay", { m.input = 0; m.svc = nil; m.full = true }),
            ("Blåtann", node ? {
                m.tab = 3; m.setDev = m.actRoom.id
                m.setCat = SK.catsFor("node").firstIndex { $0.id == "tilkobling" } ?? -1
            } : { m.input = 1; m.svc = nil; m.full = true }),
            ("Spotify", { m.svc = "spotify"; m.input = 0; m.full = true }),
            ("UPnP/DLNA", { m.svc = "upnp"; m.input = 0; m.full = true }),
            ("YT Music", { m.openLib("ytm") }),
            ("Navidrome", { m.openLib("nd") }),
            ("Plex", { m.openLib("plex") }),
            ("Lyrion", { if let u = URL(string: "http://192.168.1.42:9000/") { openURL(u) } }),
            ("AUX", { m.input = 2; m.svc = nil; m.full = true })
        ]
        if node { list.removeAll { $0.0 == "AUX" } }
        return list
    }
}
