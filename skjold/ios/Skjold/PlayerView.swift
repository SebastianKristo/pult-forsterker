import SwiftUI

/// 10 Fullskjermspiller + 11 Kø. Opened from the mini player, dragged down to close.
struct FullPlayerView: View {
    @Environment(AppModel.self) private var m

    var body: some View {
        let pa = m.playerArt
        SKSheet(onClose: { m.full = false }) {
            VStack(spacing: 0) {
                topBar
                VStack(alignment: .leading, spacing: 14) { content(pa) }
                    .padding(.horizontal, 18).padding(.top, 6).padding(.bottom, 12)
            }
            .background {
                // background runs all the way to the bottom edge (behind the home indicator)
                ZStack {
                    ArtFill(pa.key)
                    LinearGradient(stops: [.init(color: Color.bg.opacity(0.15), location: 0),
                                           .init(color: Color.bg.opacity(0.55), location: 0.55),
                                           .init(color: Color.bg.opacity(0.85), location: 1)],
                                   startPoint: .top, endPoint: .bottom)
                }
                // full screen: background goes behind the status bar and the home indicator
                .ignoresSafeArea()
            }
        }
    }

    /// Top bar (YouTube Music style): close ⌄ · Låt/Kø switch · speakers · more ⋮
    private var topBar: some View {
        ZStack {
            // segmented Låt / Kø in the middle
            HStack(spacing: 2) {
                ForEach([(false, "Låt"), (true, "Kø")], id: \.1) { q, label in
                    let on = m.queueOpen == q
                    Button {
                        if !on { Haptics.tick() }
                        withAnimation(.easeOut(duration: 0.2)) { m.queueOpen = q }
                    } label: {
                        Text(label).sora(14, .semibold, on ? .ink : Color.ink.opacity(0.5))
                            .padding(.horizontal, 18).frame(height: 32)
                            .background(Capsule().fill(on ? Color.ink.opacity(0.16) : .clear))
                    }
                    .plain()
                }
            }
            .padding(3)
            .background(Capsule().fill(Color.black.opacity(0.3)))
            HStack(spacing: 0) {
                topButton(Icons.chevronDown, size: 26, stroke: 2.2, label: "Lukk") { m.full = false }
                Spacer()
                topButton(Icons.speaker, size: 22, stroke: 1.8, label: "Høyttalere") { m.full = false; m.tab = 2 }
                topButton(Icons.moreVertical, size: 22, fill: true, on: m.srcOpen, label: "Mer") {
                    withAnimation(.easeOut(duration: 0.2)) { m.srcOpen.toggle() }
                }
            }
            .padding(.horizontal, 8)
        }
        .padding(.top, 8).padding(.bottom, 4)
    }

    private func topButton(_ d: String, size: CGFloat, stroke: CGFloat = 2, fill: Bool = false, on: Bool = false,
                           label: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            SKIcon(d: d, size: size, stroke: stroke, color: .ink, fill: fill)
                .frame(width: 44, height: 44)
                .background(Circle().fill(on ? Color.ink.opacity(0.16) : .clear))
        }
        .plain()
        .accessibilityLabel(label)
    }

    @ViewBuilder private func content(_ pa: AppModel.PlayerArt) -> some View {
        // Flexible area: the cover (or the queue) shrinks so everything fits without scrolling.
        Group {
            if !m.queueOpen { cover(pa) } else { queue }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        if m.srcOpen {
            FlowLayout(spacing: 6) {
                ForEach(m.inputs, id: \.i) { inp in
                    SKChip(label: inp.label, on: m.input == inp.i && m.svc == nil) { m.pickInput(inp.i) }
                }
            }
        }
        if m.input == 3 {
            EdgeScroll(spacing: 6, inset: 18) {
                ForEach(Array(m.radio.enumerated()), id: \.offset) { i, st in
                    SKChip(label: st.name, on: m.stIdx == i, hPad: 11, vPad: 7, leadingNumber: "\(i + 1)") {
                        m.station = i; m.rTmp = nil
                        m.post(["type": "src", "v": i])
                    }
                }
            }
        }
        VStack(alignment: .leading, spacing: 4) {
            Text(m.np.t).sora(24, .semibold).lineLimit(1)
            Text(m.np.s).sora(15, .regular, Color.ink.opacity(0.65)).lineLimit(1)
        }
        HStack(spacing: 10) {
            Button { m.srcOpen.toggle() } label: {
                HStack(spacing: 6) {
                    Text(m.srcName).sora(15, .semibold)
                    SKIcon(d: Icons.chevronDown, size: 12, stroke: 2.4).opacity(0.6)
                }
                .foregroundStyle(Color.ink)
            }
            .plain()
            Spacer()
            Text(m.quality).mono(10, Color.ink.opacity(0.7), em: 0.06)
        }
        if m.hasProgress { progress }
        controls
        HStack(spacing: 12) {
            SKIcon(d: Icons.volume, size: 18, stroke: 2, color: .ink)
            SKSlider(value: Binding(get: { Double(m.vol) }, set: { m.setVol(Int($0)) }), tint: .ink)
            Text("\(m.vol)").mono(12, Color.ink.opacity(0.7)).frame(width: 22, alignment: .trailing)
        }
        HStack(spacing: 12) {
            circleButton(Icons.queue, on: m.queueOpen, label: "Kø") {
                withAnimation(.easeOut(duration: 0.2)) { m.queueOpen.toggle() }
            }
            Spacer(minLength: 0)
            Button { m.full = false; m.tab = 2 } label: {
                HStack(spacing: 8) {
                    SKIcon(d: Icons.speaker, size: 18, stroke: 1.8)
                    Text(m.groupName).sora(14, .semibold).lineLimit(1)
                }
                .foregroundStyle(Color.ink)
                .padding(.horizontal, 18).frame(height: 48)
                .background(Capsule().fill(Color.black.opacity(0.18)))
                .skCapsuleBorder(Color.ink.opacity(0.18))
            }
            .plain()
            Spacer(minLength: 0)
            circleButton(Icons.more, on: m.srcOpen, label: "Kilde", fill: true) {
                withAnimation(.easeOut(duration: 0.2)) { m.srcOpen.toggle() }
            }
        }
        .padding(.top, 2)
    }

    // MARK: Cover

    private func cover(_ pa: AppModel.PlayerArt) -> some View {
        let a = art(pa.key)
        return ZStack {
            ArtFill(a)
            VStack(alignment: .leading, spacing: 0) {
                HStack(alignment: .top, spacing: 10) {
                    Text(pa.kicker).mono(10, a.ink, em: 0.12).opacity(0.8).lineLimit(1)
                    Spacer(minLength: 0)
                    if pa.live {
                        Text("DIREKTE").mono(9, .white, em: 0.1)
                            .padding(.horizontal, 6).padding(.vertical, 3)
                            .background(RoundedRectangle(cornerRadius: 4).fill(Color.live))
                    }
                }
                Spacer(minLength: 0)
                Text(pa.big).font(.sora(pa.size, .semibold)).foregroundStyle(a.ink)
                    .lineSpacing(0).minimumScaleFactor(0.6)
                Spacer(minLength: 0)
                viz(a.ink)
            }
            .padding(20)
        }
        .aspectRatio(1, contentMode: .fit)
        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
        .shadow(color: .black.opacity(0.35), radius: 20, y: 18)
    }

    private func viz(_ ink: Color) -> some View {
        TimelineView(.periodic(from: .now, by: 0.14)) { tl in
            let t = tl.date.timeIntervalSinceReferenceDate / 0.14
            HStack(alignment: .bottom, spacing: 3) {
                ForEach(0..<12, id: \.self) { i in
                    let e = Double(m.prof.eq[min(4, Int(Double(i) / 2.4))])
                    let a = m.playing ? 0.35 + 0.55 * abs(sin(t * 0.45 + Double(i) * 0.9) * sin(t * 0.21 + Double(i))) : 0.06
                    let h = max(4, min(100, a * 100 + e * 2.5))
                    RoundedRectangle(cornerRadius: 2).fill(ink)
                        .frame(width: 4, height: 22 * h / 100)
                        .opacity(m.playing ? 1 : 0.35)
                }
            }
            .frame(height: 22, alignment: .bottom)
        }
    }

    // MARK: Queue

    private struct QRow: Hashable { var t: String; var s: String; var cur: Bool; var i: Int }

    private var queue: some View {
        let rows: [QRow]
        if let lq = m.lq, m.libTrack != nil {
            rows = lq.enumerated().map { QRow(t: $0.element.t, s: $0.element.artist, cur: $0.offset == m.li, i: $0.offset) }
        } else {
            rows = SK.tr.enumerated().map { QRow(t: $0.element.0, s: $0.element.1, cur: $0.offset == m.trk, i: $0.offset) }
        }
        return VStack(alignment: .leading, spacing: 6) {
            Text("Neste i køen").sora(15, .semibold)
            ScrollView(.vertical, showsIndicators: false) {
                VStack(spacing: 0) {
                    ForEach(rows, id: \.self) { r in
                        Button {
                            if let lq = m.lq, m.libTrack != nil { m.playLib(lq, r.i, keepOpen: true) } else { m.trk = r.i; m.pos = 0 }
                            m.queueOpen = false
                        } label: {
                            HStack(spacing: 10) {
                                ArtFill(r.t).frame(width: 40, height: 40).clipShape(RoundedRectangle(cornerRadius: 6, style: .continuous))
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(r.t).sora(14, .regular, r.cur ? .accent2 : .ink).lineLimit(1)
                                    Text(r.s).sora(12, .regular, Color.ink.opacity(0.6)).lineLimit(1)
                                }
                                .frame(maxWidth: .infinity, alignment: .leading)
                                Text(r.cur ? "SPILLER" : "").mono(10, .accent2)
                            }
                            .padding(.horizontal, 12).frame(minHeight: 56)
                            .topLine(r.i > 0 ? Color.ink.opacity(0.1) : .clear)
                        }
                        .plain()
                    }
                }
            }
            .background(RoundedRectangle(cornerRadius: 14, style: .continuous).fill(Color.black.opacity(0.22)))
            .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
    }

    // MARK: Progress + controls

    private var progress: some View {
        VStack(spacing: 6) {
            GeometryReader { g in
                ZStack(alignment: .leading) {
                    Capsule().fill(Color.ink.opacity(0.22))
                    Capsule().fill(Color.ink.opacity(0.9)).frame(width: g.size.width * CGFloat(m.position) / CGFloat(max(1, m.duration)))
                }
                .frame(height: 5)
                .frame(maxHeight: .infinity)
                .contentShape(Rectangle())
                .onTapGesture { p in m.pos = Int(Double(p.x / g.size.width) * Double(m.duration)) }
            }
            .frame(height: 16)
            HStack {
                Text(fmt(m.position))
                Spacer()
                Text("−" + fmt(m.duration - m.position))
            }
            .mono(10, Color.ink.opacity(0.6))
        }
    }

    private var controls: some View {
        HStack {
            Button { m.shuffle.toggle() } label: {
                SKIcon(d: Icons.shuffle, size: 20, stroke: 2, color: m.shuffle ? .accent2 : Color.ink.opacity(0.75)).frame(width: 40, height: 40)
            }.plain().accessibilityLabel("Tilfeldig")
            Spacer()
            Button { m.prev() } label: { SKIcon(d: Icons.prev, size: 30, color: .ink, fill: true).frame(width: 52, height: 52) }
                .plain().accessibilityLabel("Forrige")
            Spacer()
            Button { m.togglePlay() } label: {
                SKIcon(d: m.playing ? Icons.pause : Icons.playRound, size: 32, color: .bg, fill: true)
                    .frame(width: 72, height: 72)
                    .background(Circle().fill(Color.ink))
                    .shadow(color: .black.opacity(0.25), radius: 10, y: 4)
            }.plain().accessibilityLabel(m.playing ? "Pause" : "Spill")
            Spacer()
            Button { m.next() } label: { SKIcon(d: Icons.next, size: 30, color: .ink, fill: true).frame(width: 52, height: 52) }
                .plain().accessibilityLabel("Neste")
            Spacer()
            Button { m.repeatOn.toggle() } label: {
                SKIcon(d: Icons.repeatIcon, size: 20, stroke: 2, color: m.repeatOn ? .accent2 : Color.ink.opacity(0.75)).frame(width: 40, height: 40)
            }.plain().accessibilityLabel("Gjenta")
        }
        .padding(.horizontal, 2)
    }

    private func circleButton(_ d: String, on: Bool, label: String, fill: Bool = false, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            SKIcon(d: d, size: 20, stroke: 2, color: .ink, fill: fill)
                .frame(width: 48, height: 48)
                .background(Circle().fill(on ? Color.ink.opacity(0.22) : Color.black.opacity(0.18)))
                .overlay(Circle().strokeBorder(Color.ink.opacity(0.18), lineWidth: 1))
        }
        .plain()
        .accessibilityLabel(label)
    }

    private func fmt(_ s: Int) -> String { "\(s / 60):" + String(format: "%02d", s % 60) }
}
