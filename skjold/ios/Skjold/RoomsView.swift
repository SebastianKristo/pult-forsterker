import SwiftUI

/// Rom («Ditt system»): now-playing group card with group volume, room tiles (drag sideways for volume),
/// surround placement and add device.
struct RoomsView: View {
    @Environment(AppModel.self) private var m

    var body: some View {
        let act = m.actRoom
        let members = m.sys.groupOf(act.id)
        let gid = act.group
        let gMode = gid.flatMap { m.sys.modes[$0] } ?? "sync"
        let surround = members.count > 1 && gMode == "surround"

        groupCard(act: act, members: members, gid: gid, gMode: gMode)

        VStack(alignment: .leading, spacing: 10) {
            HStack {
                SKMonoLabel(text: "ROM")
                Spacer()
                Text("Dra sidelengs for volum").sora(11, .regular, .muted)
            }
            LazyVGrid(columns: [GridItem(.flexible(), spacing: 10), GridItem(.flexible(), spacing: 10)], spacing: 10) {
                ForEach(m.sys.rooms) { r in RoomTile(room: r, act: act) }
                addTile
            }
        }

        if surround { surroundCard(members) }

        Text("Rom med hake spiller det samme, synkronisert av Lyrion. Trykk på et rom for å styre det.")
            .sora(11, .regular, .muted).fixedSize(horizontal: false, vertical: true)
    }

    // MARK: Group / now playing

    private func groupCard(act: Room, members: [Room], gid: String?, gMode: String) -> some View {
        let np = m.np
        let groupVol = members.isEmpty ? m.vol : Int((Double(members.map { $0.id == act.id ? m.vol : $0.vol }.reduce(0, +)) / Double(members.count)).rounded())
        return VStack(alignment: .leading, spacing: 14) {
            HStack(spacing: 12) {
                Button { Haptics.thump(); m.full = true } label: {
                    ArtFill(m.playerArt.key).frame(width: 56, height: 56)
                        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                        .shadow(color: .black.opacity(0.45), radius: 10, y: 6)
                }
                .plain()
                VStack(alignment: .leading, spacing: 2) {
                    Text(members.count > 1 ? "SPILLER I \(members.count) ROM" : "SPILLER I \(act.name.uppercased())").mono(10, .accent2, em: 0.12)
                    Text(np.t).sora(17, .semibold).lineLimit(1)
                    Text(np.s).sora(12, .regular, .ink2).lineLimit(1)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                Button { m.togglePlay() } label: {
                    SKIcon(d: m.playing ? Icons.pause : Icons.playRound, size: 18, color: .bg, fill: true)
                        .frame(width: 42, height: 42)
                        .background(Circle().fill(Color.ink))
                }
                .plain()
                .accessibilityLabel(m.playing ? "Pause" : "Spill")
            }
            // members
            FlowLayout(spacing: 6) {
                ForEach(members) { r in
                    HStack(spacing: 6) {
                        SKIcon(d: SK.dev(r.type).icon, size: 14, stroke: 1.6, color: .ink2)
                        Text(r.name).sora(12)
                    }
                    .padding(.horizontal, 10).frame(height: 28)
                    .background(Capsule().fill(Color.white.opacity(0.08)))
                }
            }
            // group volume
            HStack(spacing: 12) {
                SKIcon(d: Icons.volume, size: 18, stroke: 2, color: .ink2)
                SKSlider(value: Binding(get: { Double(groupVol) }, set: { setGroupVolume(Int($0)) }), tint: .accent)
                Text("\(groupVol)").mono(12, .ink).frame(width: 26, alignment: .trailing)
            }
            if members.count > 1, let gid {
                SKSegmented(items: ["Samme musikk", "Surround"], selected: gMode == "surround" ? 1 : 0, height: 34,
                            bg: Color.black.opacity(0.3), border: nil, selBg: .selBg2, selFg: .accent2, fg: .ink2) { i in
                    Haptics.tick()
                    withAnimation(.snappy) { m.setSys(m.sys.withGroupMode(gid, i == 1 ? "surround" : "sync")) }
                }
            }
            HStack(spacing: 8) {
                quickButton("Alle rom", icon: Icons.tabRooms, on: allGrouped) {
                    withAnimation(.snappy) { m.setSys(m.sys.groupedAll()) }
                }
                quickButton("Bare \(act.name)", icon: Icons.speaker, on: members.count == 1) {
                    var n = m.sys
                    for i in n.rooms.indices { n.rooms[i].group = nil }
                    withAnimation(.snappy) { m.setSys(n) }
                }
            }
        }
        .padding(16)
        .background {
            ZStack {
                Color.card
                ArtFill(m.playerArt.key).padding(-60).blur(radius: 50).opacity(0.45)
                LinearGradient(colors: [Color.bg.opacity(0.3), Color.bg.opacity(0.85)], startPoint: .top, endPoint: .bottom)
            }
        }
        .clipShape(RoundedRectangle(cornerRadius: 20, style: .continuous))
        .skBorder(.line, radius: 20)
    }

    private var allGrouped: Bool {
        let rooms = m.sys.rooms
        return rooms.count > 1 && rooms.allSatisfy { $0.group != nil && $0.group == rooms[0].group }
    }

    private func quickButton(_ title: String, icon: String, on: Bool, action: @escaping () -> Void) -> some View {
        Button { if !on { Haptics.tick(); action() } } label: {
            HStack(spacing: 6) {
                SKIcon(d: icon, size: 14, stroke: 1.8)
                Text(title).sora(12, on ? .semibold : .regular).lineLimit(1)
            }
            .foregroundStyle(on ? Color.accent2 : Color.ink)
            .frame(maxWidth: .infinity).frame(height: 36)
            .background(Capsule().fill(on ? Color.selBg : Color.black.opacity(0.25)))
            .skCapsuleBorder(on ? .accent : .line2)
        }
        .plain()
    }

    /// Moves every member by the same amount, like a group volume on Sonos. Reads fresh values from the model each step.
    private func setGroupVolume(_ v: Int) {
        let act = m.actRoom
        var n = m.sys
        n.rooms = n.rooms.map { r in var r = r; if r.id == act.id { r.vol = m.vol }; return r }
        let members = n.groupOf(act.id)
        guard !members.isEmpty else { return }
        let current = Int((Double(members.map(\.vol).reduce(0, +)) / Double(members.count)).rounded())
        let delta = v - current
        guard delta != 0 else { return }
        for r in members {
            guard let i = n.rooms.firstIndex(where: { $0.id == r.id }) else { continue }
            n.rooms[i].vol = max(0, min(100, r.vol + delta))
            if r.id == act.id { m.setVol(n.rooms[i].vol) }
        }
        m.setSys(n)
    }

    // MARK: Add device

    private var addTile: some View {
        Button {
            Haptics.tap()
            m.mode = .onboard; m.welcome = false; m.ob = 0; m.tested = []; m.pw = ""; m.obUpd = 0; m.scan = false
        } label: {
            VStack(spacing: 10) {
                SKIcon(d: Icons.plus, size: 22, stroke: 2, color: .accent2)
                    .frame(width: 44, height: 44)
                    .background(Circle().fill(Color.selBg2))
                    .overlay(Circle().strokeBorder(Color.selLine, lineWidth: 1))
                VStack(spacing: 2) {
                    Text("Legg til enhet").sora(13, .semibold)
                    Text("S1, Node eller Core").sora(11, .regular, .muted)
                }
            }
            .frame(maxWidth: .infinity).frame(height: 150)
            .skBorder(Color(hex: 0x3a2e17), radius: 18, dash: [5, 4])
        }
        .plain()
    }

    // MARK: Surround

    private func surroundCard(_ members: [Room]) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            SKMonoLabel(text: "PLASSERING I SURROUND")
            VStack(spacing: 0) {
                ForEach(Array(members.enumerated()), id: \.element.id) { idx, r in
                    VStack(alignment: .leading, spacing: 8) {
                        HStack(spacing: 8) {
                            SKIcon(d: SK.dev(r.type).icon, size: 18, stroke: 1.4, color: .ink2)
                            Text(r.name).sora(14)
                            Spacer()
                            Text(SK.roles[r.role ?? 0]).mono(10, .accent2)
                        }
                        FlowLayout(spacing: 5) {
                            ForEach(Array(SK.roles.enumerated()), id: \.offset) { j, label in
                                let on = (r.role ?? 0) == j
                                SKChip(label: label, height: 30, hPad: 10, radius: 8,
                                       style: SelStyle(bd: on ? .accent : .line2, bg: on ? .selBg2 : .card, fg: on ? .accent2 : .ink2)) {
                                    Haptics.tick()
                                    var n = m.sys
                                    if let i = n.rooms.firstIndex(where: { $0.id == r.id }) { n.rooms[i].role = j }
                                    m.setSys(n)
                                }
                            }
                        }
                    }
                    .padding(.vertical, 12).padding(.horizontal, 14)
                    .topLine(idx > 0 ? .line : .clear)
                }
            }
            .skBox(.card, .line, radius: 18)
            Text("Tidsforsinkelse justeres automatisk ut fra plasseringen.").sora(11, .regular, .muted)
        }
    }
}

// MARK: - Room tile

/// Square-ish tile: icon, name, status; the background fills with the volume. Drag sideways to change volume,
/// tap to control the room, check mark to add/remove it from the group.
private struct RoomTile: View {
    @Environment(AppModel.self) private var m
    let room: Room
    let act: Room
    @State private var dragStart: Int? = nil

    var body: some View {
        let isA = room.id == act.id
        let inG = isA || (act.group != nil && room.group == act.group)
        let vol = isA ? m.vol : room.vol
        let np = m.np
        let status = room.np.map { $0[0] + " · " + $0[1] } ?? (inG ? np.t : "Ledig")
        GeometryReader { g in
            ZStack(alignment: .leading) {
                RoundedRectangle(cornerRadius: 18, style: .continuous).fill(isA ? Color.selBg : .card)
                // volume fill from the left
                Rectangle()
                    .fill(LinearGradient(colors: [Color.accent.opacity(inG ? 0.22 : 0.08), Color.accent.opacity(inG ? 0.12 : 0.04)],
                                         startPoint: .leading, endPoint: .trailing))
                    .frame(width: g.size.width * CGFloat(vol) / 100)
                VStack(alignment: .leading, spacing: 0) {
                    HStack(alignment: .top) {
                        SKIcon(d: SK.dev(room.type).icon, size: 26, stroke: 1.3, color: isA ? .accent2 : .ink2)
                            .frame(width: 40, height: 40)
                            .background(RoundedRectangle(cornerRadius: 11, style: .continuous).fill(Color.black.opacity(0.25)))
                        Spacer()
                        Button {
                            Haptics.tick()
                            withAnimation(.snappy) { m.setSys(m.sys.toggledInGroup(active: act.id, room.id)) }
                        } label: {
                            Image(systemName: "checkmark").font(.system(size: 12, weight: .bold))
                                .foregroundStyle(inG ? Color.bg : .clear)
                                .frame(width: 26, height: 26)
                                .background(Circle().fill(inG ? Color.accent : .clear))
                                .overlay(Circle().strokeBorder(inG ? Color.accent : .dim, lineWidth: 1.5))
                                .frame(width: 40, height: 40, alignment: .topTrailing)
                        }
                        .plain()
                        .disabled(isA)
                        .accessibilityLabel(inG ? "Fjern fra gruppen" : "Legg til i gruppen")
                    }
                    Spacer(minLength: 0)
                    Text(room.name).sora(16, .semibold).lineLimit(1)
                    Text(status).sora(11, .regular, inG ? .ink2 : .muted).lineLimit(1)
                    HStack(spacing: 6) {
                        SKIcon(d: Icons.volume, size: 12, stroke: 2, color: .muted)
                        Text("\(vol)").mono(11, vol > 0 ? .ink : .muted)
                            .contentTransition(.numericText(value: Double(vol)))
                        Spacer()
                        Text(SK.dev(room.type).n.replacingOccurrences(of: "Skjold ", with: "")).mono(9, .muted, em: 0.08)
                    }
                    .padding(.top, 6)
                }
                .padding(12)
            }
            .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
            .skBorder(isA ? .accent : .line, radius: 18)
            .contentShape(Rectangle())
            .onTapGesture {
                guard !isA else { return }
                Haptics.tick()
                // keep each room's own volume: store the old active room's volume, load the new one
                var n = m.sys
                if let old = n.rooms.firstIndex(where: { $0.id == act.id }) { n.rooms[old].vol = m.vol }
                n.active = room.id
                m.vol = room.vol
                withAnimation(.snappy) { m.setSys(n) }
            }
            .simultaneousGesture(
                DragGesture(minimumDistance: 12)
                    .onChanged { d in
                        guard abs(d.translation.width) > abs(d.translation.height) || dragStart != nil else { return }
                        let start = dragStart ?? vol
                        if dragStart == nil { dragStart = vol }
                        let v = max(0, min(100, start + Int(d.translation.width / g.size.width * 100)))
                        if v != vol {
                            if v == 0 || v == 100 { Haptics.bump() } else if v / 5 != vol / 5 { Haptics.tick() }
                            setVolume(v, isA: isA)
                        }
                    }
                    .onEnded { _ in dragStart = nil }
            )
        }
        .frame(height: 150)
        .accessibilityElement(children: .combine)
        .accessibilityValue("Volum \(vol)")
        .accessibilityAdjustableAction { dir in
            setVolume(max(0, min(100, vol + (dir == .increment ? 5 : -5))), isA: isA)
        }
    }

    private func setVolume(_ v: Int, isA: Bool) {
        if isA { m.setVol(v) }
        var n = m.sys
        if let i = n.rooms.firstIndex(where: { $0.id == room.id }) { n.rooms[i].vol = v }
        m.setSys(n)
    }
}
