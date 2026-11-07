import SwiftUI

/// Innstillinger (tSet): tittel, enhetsvalg, kategoriliste i v4-stil. Undersidene vises med SettingsView.
struct V4SettingsTab: View {
    @Environment(AppModel.self) private var m
    @AppStorage("skjold-show-lyrion-players") private var showLyrion = false
    @AppStorage("hapticSliders") private var hapticSliders = true

    var body: some View {
        if m.setCat >= 0 && m.setCat < m.cats.count {
            SettingsView()
        } else {
            VStack(alignment: .leading, spacing: 6) {
                V4Title(text: "Innstillinger")
                Text(subtitle).mono(11, V4.muted).lineLimit(1)
            }
            if m.sys.rooms.count > 1 { devicePicker }
            list
            appCard
        }
    }

    private var subtitle: String {
        let r = m.devRoom
        let v = m.devRoomStatus?.version ?? ""
        return [r.name, SK.dev(r.type).n, v.isEmpty ? m.upd.version : v].filter { !$0.isEmpty }.joined(separator: " · ")
    }

    private var devicePicker: some View {
        V4Shelf(spacing: 8) {
            ForEach(m.sys.rooms) { r in
                let on = r.id == m.devRoom.id
                Button { Haptics.tick(); m.setDev = r.id; m.setCat = -1 } label: {
                    HStack(spacing: 8) {
                        V4Icon(d: SK.dev(r.type).icon, size: 18, stroke: 1.4, color: on ? V4.gold : V4.ink2)
                        Text(r.name).sora(13, .regular, on ? V4.gold : V4.ink).lineLimit(1).fixedSize()
                    }
                    .padding(.horizontal, 14).frame(height: 36)
                    .background(Capsule().fill(on ? V4.selBg : V4.card))
                    .overlay(Capsule().strokeBorder(on ? V4.goldDark : V4.line2, lineWidth: 1))
                }
                .plain()
            }
        }
    }

    private var list: some View {
        let cats = m.cats
        return VStack(spacing: 0) {
            ForEach(Array(cats.enumerated()), id: \.offset) { i, c in
                Button { Haptics.tap(); open(i, c) } label: {
                    HStack(spacing: 14) {
                        V4Icon(d: SettingsView.catIcon[c.id] ?? "", size: 19, stroke: 1.7, color: V4.ink)
                            .frame(width: 38, height: 38)
                            .background(RoundedRectangle(cornerRadius: 11, style: .continuous).fill(Color(hex: SettingsView.catTile[c.id] ?? 0x2a2a2c)))
                        VStack(alignment: .leading, spacing: 2) {
                            Text(c.n).sora(15)
                            Text(c.sub).sora(12, .regular, V4.muted).lineLimit(1)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        V4Icon(d: V4.chevRight, size: 16, stroke: 2, color: V4.chev)
                    }
                    .padding(.horizontal, 16).padding(.vertical, 10)
                    .frame(minHeight: 62)
                    .v4TopLine(i > 0 ? V4.line : .clear)
                    .contentShape(Rectangle())
                }
                .plain()
            }
        }
        .v4Card()
    }

    /// Equalizer i listen går rett til Lyd-fanen (som i malen).
    private func open(_ i: Int, _ c: SettingCategory) {
        if c.id == "eq" { m.tab = 1; return }
        m.setCat = i; m.openK = ""; m.confirm = ""
    }

    private var appCard: some View {
        VStack(alignment: .leading, spacing: 10) {
            V4Kicker(text: "APPEN")
            HStack(spacing: 12) {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Vis andre Lyrion-spillere").sora(15)
                    Text("Ta med spillere som ikke er Skjold (for eksempel max2play eller TV-bokser) under Rom.")
                        .sora(12, .regular, V4.muted, lineHeight: 1.4).fixedSize(horizontal: false, vertical: true)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                V4Switch(on: showLyrion, label: "Vis andre Lyrion-spillere") {
                    showLyrion.toggle()
                    m.rebuildRooms()
                }
            }
            .padding(.horizontal, 16).padding(.vertical, 13)
            .v4Card()
            HStack(spacing: 12) {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Haptikk på glidebrytere").sora(15)
                    Text("Tikk for hvert steg på equalizer og balanse, tydelig klikk ved 0 dB og et støt ved grensen.")
                        .sora(12, .regular, V4.muted, lineHeight: 1.4).fixedSize(horizontal: false, vertical: true)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                V4Switch(on: hapticSliders, label: "Haptikk på glidebrytere") {
                    hapticSliders.toggle()
                    if hapticSliders { Haptics.tick() }
                }
            }
            .padding(.horizontal, 16).padding(.vertical, 13)
            .v4Card()
        }
    }
}
