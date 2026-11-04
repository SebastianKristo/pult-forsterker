import SwiftUI

/// Nå spilles (full): gradient fra omslaget, Låt/Kø-segment, omslag 322, kontroller, rom-panel og bunnrad.
struct V4NowPlaying: View {
    @Environment(AppModel.self) private var m
    @Environment(V4State.self) private var ui
    let wide: Bool
    @State private var drag: CGFloat = 0

    private var info: ArtInfo { art(m.playerArt.key) }
    private var cover: CGFloat {
        let base: CGFloat = wide ? 300 : 322
        return ui.fm == "rooms" ? (base * 0.62).rounded() : base
    }

    var body: some View {
        VStack(spacing: 0) {
            VStack(spacing: 16) {
                header
                if ui.fm == "queue" { queue } else { coverView }
                titleRow
                if ui.fm == "rooms" { roomsPanel } else if ui.fm == "ctrl" { controls }
                if ui.fm == "queue" { Spacer(minLength: 0) }
            }
            .padding(.horizontal, 24).padding(.top, 4)
            .frame(maxHeight: .infinity, alignment: .top)
            bottomRow
        }
        .background { pbg.ignoresSafeArea() }
        .offset(y: wide ? 0 : max(0, drag))
        .animation(V4.cover, value: ui.fm)
    }

    /// linear-gradient(180deg, top 0%, mid 46%, #090d0f 100%)
    private var pbg: some View {
        let stops = info.stops
        let top = stops.first?.color ?? Color(hex: 0x145a67)
        let mid = stops.last?.color ?? Color(hex: 0x0b2f38)
        return LinearGradient(stops: [.init(color: top, location: 0), .init(color: mid, location: 0.46),
                                      .init(color: Color(hex: 0x090d0f), location: 1)], startPoint: .top, endPoint: .bottom)
    }

    // MARK: Topp

    private var header: some View {
        HStack(spacing: 4) {
            Button { close() } label: {
                V4Icon(d: V4.chevDown, size: 24, stroke: 2.4, color: V4.ink).frame(width: 44, height: 44)
            }
            .plain().accessibilityLabel("Lukk spiller")
            Spacer(minLength: 0)
            segment
            Spacer(minLength: 0)
            Button { toggle("rooms") } label: {
                V4Icon(d: V4.speaker, size: 22, color: ui.fm == "rooms" ? V4.gold : V4.ink).frame(width: 44, height: 44)
            }
            .plain().accessibilityLabel("Rom")
            Button { openMore() } label: {
                V4Icon(d: V4.dotsV, size: 22, color: V4.ink, fill: true).frame(width: 36, height: 44)
            }
            .plain().accessibilityLabel("Mer")
        }
        .padding(.horizontal, -8)
        .contentShape(Rectangle())
        .gesture(DragGesture(minimumDistance: 10)
            .onChanged { v in if !wide { drag = v.translation.height } }
            .onEnded { v in
                if v.translation.height > 120 { close() }
                withAnimation(.spring(response: 0.35, dampingFraction: 0.85)) { drag = 0 }
            })
    }

    /// Låt/Kø: valgt del er en Liquid Glass-linse som morpher mellom knappene (GlassEffectContainer).
    private var segment: some View {
        let q = ui.fm == "queue"
        return GlassEffectContainer(spacing: 0) {
            HStack(spacing: 0) {
                segButton("Låt", on: !q) { ui.fm = "ctrl" }
                segButton("Kø", on: q) { ui.fm = "queue" }
            }
        }
        .padding(4)
        .frame(width: 170, height: 42)
        .background(Capsule().fill(Color.black.opacity(0.22)))
    }

    private func segButton(_ title: String, on: Bool, _ act: @escaping () -> Void) -> some View {
        Button {
            Haptics.tick()
            withAnimation(V4.segLens) { act() }
        } label: {
            Text(title).sora(15, .semibold, on ? V4.ink : V4.ink.opacity(0.55))
                .frame(width: 81, height: 34)
                .glassEffect(on ? Glass.regular.interactive() : Glass.identity, in: Capsule())
        }
        .plain()
    }

    // MARK: Omslag

    private var coverView: some View {
        let a = info
        return ZStack(alignment: .topLeading) {
            ArtFill(a)
            if !a.hasLogo {
                VStack(alignment: .leading, spacing: 0) {
                    Text(m.playerArt.kicker).mono(11, a.ink.opacity(0.8), em: 0.14).lineLimit(1)
                    Spacer(minLength: 0)
                    Text(m.playerArt.big).sora(ui.fm == "rooms" ? 30 : 48, .semibold, a.ink, lineHeight: 1)
                        .tracking(-0.96).lineLimit(3).minimumScaleFactor(0.5)
                }
                .padding(22)
            }
        }
        .frame(width: cover, height: cover)
        .clipShape(RoundedRectangle(cornerRadius: 22, style: .continuous))
        .shadow(color: .black.opacity(0.45), radius: 30, y: 30)
        .frame(maxWidth: .infinity)
    }

    private var titleRow: some View {
        HStack(spacing: 12) {
            VStack(alignment: .leading, spacing: 3) {
                Text(m.np.t).sora(22, .semibold).lineLimit(1)
                Text(m.np.s).sora(14, .regular, V4.ink.opacity(0.7)).lineLimit(1)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            Text(m.quality).mono(10, V4.ink.opacity(0.65), em: 0.06).lineLimit(1).fixedSize()
        }
    }

    // MARK: Kontroller

    private var controls: some View {
        VStack(spacing: 16) {
            if m.hasProgress { progress } else { liveTag }
            HStack {
                iconButton(V4.shuffle, 22, m.shuffle ? V4.gold : V4.ink.opacity(0.7), "Tilfeldig") { m.shuffle.toggle() }
                Spacer()
                Button { m.prev() } label: {
                    V4Icon(d: V4.skip, size: 30, color: V4.ink, fill: true).scaleEffect(x: -1, y: 1).padding(6)
                }
                .plain().accessibilityLabel("Forrige")
                Spacer()
                Button { m.togglePlay() } label: {
                    V4PlayIcon(playing: m.playing, size: 28, color: V4.ink)
                        .frame(width: 72, height: 72)
                        .background(Circle().fill(V4.ink.opacity(0.14)))
                        .overlay(Circle().strokeBorder(Color.white.opacity(0.16), lineWidth: 1))
                }
                .plain().accessibilityLabel("Spill/pause")
                Spacer()
                Button { m.next() } label: { V4Icon(d: V4.skip, size: 30, color: V4.ink, fill: true).padding(6) }
                    .plain().accessibilityLabel("Neste")
                Spacer()
                iconButton(V4.repeatP, 22, m.repeatOn ? V4.gold : V4.ink.opacity(0.7), "Gjenta") { m.repeatOn.toggle() }
            }
            .padding(.horizontal, 4)
            HStack(spacing: 12) {
                V4Icon(d: V4.vol, size: 18, color: V4.ink.opacity(0.8))
                V4Bar(value: Double(m.v4GroupVol) / 100, height: 8, trackColor: V4.ink.opacity(0.2)) { v in
                    m.v4SetGroupVol(Int((v * 100).rounded()))
                }
                Text("\(m.v4GroupVol)").mono(13, V4.ink).frame(width: 24, alignment: .trailing)
            }
        }
    }

    private func iconButton(_ d: String, _ size: CGFloat, _ c: Color, _ label: String, _ act: @escaping () -> Void) -> some View {
        Button { Haptics.tick(); act() } label: { V4Icon(d: d, size: size, color: c).padding(6) }
            .plain().accessibilityLabel(label)
    }

    private var progress: some View {
        VStack(spacing: 7) {
            GeometryReader { g in
                ZStack(alignment: .leading) {
                    Capsule().fill(V4.ink.opacity(0.2))
                    Capsule().fill(V4.ink).frame(width: g.size.width * CGFloat(m.v4Progress))
                        .animation(.linear(duration: 1), value: m.position)
                }
            }
            .frame(height: 5)
            HStack {
                Text(fmt(m.position))
                Spacer()
                Text("−" + fmt(max(0, m.duration - m.position)))
            }
            .mono(11, V4.ink.opacity(0.6))
        }
    }

    private var liveTag: some View {
        HStack(spacing: 8) {
            Circle().fill(V4.red).frame(width: 7, height: 7)
            Text("DIREKTE").mono(11, V4.gold, em: 0.12)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func fmt(_ s: Int) -> String { "\(s / 60):" + String(format: "%02d", s % 60) }

    // MARK: Kø

    private var queue: some View {
        let rows = m.v4Queue
        return VStack(spacing: 10) {
            HStack(alignment: .firstTextBaseline) {
                Text("Neste fra " + (m.libTrack != nil ? (V4Lib.names[m.lib] ?? "køen") : "køen")).sora(13, .semibold, V4.ink.opacity(0.75))
                Spacer()
                Text("\(rows.count) låter").sora(13, .regular, V4.ink.opacity(0.6))
            }
            ScrollView(.vertical, showsIndicators: false) {
                VStack(spacing: 0) {
                    ForEach(rows, id: \.i) { r in queueRow(r, curIdx: rows.firstIndex { $0.cur } ?? 0) }
                }
            }
            .padding(.horizontal, -10)
            .mask(LinearGradient(stops: [.init(color: .black, location: 0.82), .init(color: .clear, location: 1)], startPoint: .top, endPoint: .bottom))
        }
        .frame(height: wide ? 360 : 400)
    }

    private func queueRow(_ r: (t: String, s: String, key: String, cur: Bool, i: Int), curIdx: Int) -> some View {
        HStack(spacing: 12) {
            Button { m.v4PlayQueue(r.i) } label: {
                HStack(spacing: 12) {
                    V4Art(key: r.key, radius: 9).frame(width: 48, height: 48)
                    VStack(alignment: .leading, spacing: 2) {
                        HStack(spacing: 6) {
                            if r.cur { eqBars }
                            Text(r.t).sora(15, .semibold).lineLimit(1)
                        }
                        Text(r.s).sora(13, .regular, V4.ink.opacity(0.6)).lineLimit(1)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
            .plain()
            V4MoreButton { openMore(track(r.i)) }
            Button { Haptics.tick(); m.v4QueueUp(r.i) } label: {
                V4Icon(d: V4.handle, size: 20, color: V4.ink.opacity(0.45)).frame(width: 30, height: 36)
            }
            .plain().accessibilityLabel("Flytt opp")
        }
        .padding(.horizontal, 10).padding(.vertical, 7)
        .background(RoundedRectangle(cornerRadius: 14, style: .continuous).fill(r.cur ? V4.ink.opacity(0.1) : .clear))
        .opacity(r.i < curIdx ? 0.45 : 1)
    }

    private var eqBars: some View {
        HStack(alignment: .bottom, spacing: 1.5) {
            ForEach([4.0, 8.0, 11.0, 6.0], id: \.self) { h in
                RoundedRectangle(cornerRadius: 1).fill(V4.ink).frame(width: 2, height: h)
            }
        }
        .frame(height: 11)
    }

    private func track(_ i: Int) -> Track? {
        guard let q = m.lq, m.libTrack != nil, i < q.count else { return nil }
        return q[i]
    }

    // MARK: Rom-panel («Spill på»)

    private var roomsPanel: some View {
        let group = m.v4Group
        let off = m.sys.rooms.filter { r in !group.contains { $0.id == r.id } }
        return VStack(alignment: .leading, spacing: 12) {
            ForEach(group) { r in groupRow(r, canRemove: group.count > 1) }
            if group.count > 1 {
                Rectangle().fill(Color.white.opacity(0.12)).frame(height: 1)
                HStack {
                    HStack(spacing: 8) {
                        V4Icon(d: V4.sync, size: 16, stroke: 2, color: V4.gold)
                        Text("Gruppe").sora(16, .semibold)
                    }
                    Spacer()
                    Text("SYNKRON").mono(10, V4.gold, em: 0.08)
                }
                HStack(spacing: 10) {
                    stepCircle("−", "Senk alle") { m.v4SetGroupVol(m.v4GroupVol - 5) }
                    GeometryReader { g in
                        ZStack(alignment: .leading) {
                            Capsule().fill(V4.ink.opacity(0.18))
                            Capsule().fill(V4.ink).frame(width: g.size.width * CGFloat(m.v4GroupVol) / 100)
                        }
                    }
                    .frame(height: 12)
                    stepCircle("+", "Øk alle") { m.v4SetGroupVol(m.v4GroupVol + 5) }
                    Text("\(m.v4GroupVol)").mono(13, V4.ink).frame(width: 24, alignment: .trailing)
                }
            }
            if !off.isEmpty {
                Text("Spill også i").sora(12, .regular, V4.ink.opacity(0.6))
                FlowLayout(spacing: 8) {
                    ForEach(off) { r in
                        Button { Haptics.tick(); withAnimation(.snappy) { m.v4ToggleInGroup(r.id) } } label: {
                            Text("+ " + r.name).sora(13).padding(.horizontal, 13).frame(height: 34)
                                .background(Capsule().fill(V4.ink.opacity(0.06)))
                                .overlay(Capsule().strokeBorder(V4.ink.opacity(0.25), lineWidth: 1))
                        }
                        .plain()
                    }
                }
            }
        }
        .padding(.horizontal, 16).padding(.vertical, 14)
        .background(RoundedRectangle(cornerRadius: 24, style: .continuous).fill(V4.ink.opacity(0.1)))
        .overlay(RoundedRectangle(cornerRadius: 24, style: .continuous).strokeBorder(Color.white.opacity(0.14), lineWidth: 1))
    }

    private func groupRow(_ r: Room, canRemove: Bool) -> some View {
        let v = m.v4RoomVol(r)
        return VStack(alignment: .leading, spacing: 8) {
            HStack {
                HStack(alignment: .firstTextBaseline, spacing: 8) {
                    Text(r.name).sora(16, .semibold)
                    Text(SK.dev(r.type).n).mono(10, V4.ink.opacity(0.6))
                }
                Spacer()
                if canRemove {
                    stepCircle("−", "Fjern fra gruppen", size: 30) { withAnimation(.snappy) { m.v4ToggleInGroup(r.id) } }
                }
            }
            HStack(spacing: 10) {
                V4Bar(value: Double(v) / 100, height: 8, trackColor: V4.ink.opacity(0.18)) { x in
                    m.v4SetRoomVol(r.id, Int((x * 100).rounded()))
                }
                Text("\(v)").mono(13, V4.ink).frame(width: 24, alignment: .trailing)
            }
        }
    }

    private func stepCircle(_ s: String, _ label: String, size: CGFloat = 34, _ act: @escaping () -> Void) -> some View {
        Button { Haptics.tick(); act() } label: {
            Text(s).sora(size > 30 ? 18 : 16).frame(width: size, height: size).background(Circle().fill(V4.ink.opacity(0.12)))
        }
        .plain().accessibilityLabel(label)
    }

    // MARK: Bunnrad

    private var bottomRow: some View {
        HStack(spacing: 14) {
            roundButton(V4.queue, ui.fm == "queue" ? V4.ink.opacity(0.28) : V4.ink.opacity(0.1), "Kø", fill: false) { toggle("queue") }
            Button { toggle("rooms") } label: {
                HStack(spacing: 8) {
                    V4Icon(d: V4.speaker, size: 18, color: ui.fm == "rooms" ? V4.gold : V4.ink)
                    Text(m.v4GroupName).sora(14, .semibold, ui.fm == "rooms" ? V4.gold : V4.ink).lineLimit(1)
                }
                .padding(.horizontal, 16)
                .frame(maxWidth: .infinity).frame(height: 52)
                .background(Capsule().fill(ui.fm == "rooms" ? V4.gold.opacity(0.16) : V4.ink.opacity(0.1)))
                .overlay(Capsule().strokeBorder(ui.fm == "rooms" ? V4.goldDark : Color.white.opacity(0.14), lineWidth: 1))
            }
            .plain()
            roundButton(V4.dots, ui.more ? V4.ink.opacity(0.28) : V4.ink.opacity(0.1), "Mer", fill: true) { openMore() }
        }
        .padding(.horizontal, 24).padding(.top, 16).padding(.bottom, wide ? 30 : 24)
    }

    private func roundButton(_ d: String, _ bg: Color, _ label: String, fill: Bool, _ act: @escaping () -> Void) -> some View {
        Button { Haptics.tap(); act() } label: {
            V4Icon(d: d, size: 20, color: V4.ink, fill: fill)
                .frame(width: 52, height: 52)
                .background(Circle().fill(bg))
                .overlay(Circle().strokeBorder(Color.white.opacity(0.14), lineWidth: 1))
        }
        .plain().accessibilityLabel(label)
    }

    private func toggle(_ f: String) { Haptics.tick(); ui.fm = ui.fm == f ? "ctrl" : f }
    private func openMore(_ t: Track? = nil) { ui.moreTrack = t; withAnimation(V4.moreSheet) { ui.more = true } }
    private func close() { m.full = false; ui.more = false; ui.fm = "ctrl" }
}
