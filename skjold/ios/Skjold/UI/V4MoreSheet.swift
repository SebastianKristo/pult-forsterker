import SwiftUI

/// «Mer»-arket (iOS): flytende glassark 8 fra kantene, radius 34, farget fra låten.
struct V4MoreSheet: View {
    @Environment(AppModel.self) private var m
    @Environment(V4State.self) private var ui
    let left: CGFloat
    @AppStorage("skjold-v4-favs") private var favsRaw = ""

    private static let sleeps = ["Av", "15 min", "30 min", "60 min", "Etter låten"]

    var body: some View {
        GeometryReader { g in
            ZStack(alignment: .bottomLeading) {
                Color.black.opacity(ui.more ? 0.45 : 0).ignoresSafeArea()
                    .onTapGesture { close() }
                    .animation(V4.scrim, value: ui.more)
                sheet
                    .padding(.leading, left).padding(.trailing, 8).padding(.bottom, 8)
                    .offset(y: ui.more ? 0 : g.size.height * 1.1 + 60)
                    .animation(V4.moreSheet, value: ui.more)
            }
            .ignoresSafeArea(edges: .bottom)
        }
        .allowsHitTesting(ui.more)
    }

    // MARK: Innhold

    private var t: Track? { ui.moreTrack ?? m.libTrack }
    private var title: String { t?.t ?? m.np.t }
    private var artist: String { t?.artist ?? m.np.s }
    private var key: String { t?.album ?? m.playerArt.key }

    private var sheet: some View {
        let a = art(m.playerArt.key)
        let top = a.stops.first?.color ?? Color(hex: 0x145a67)
        let mid = a.stops.last?.color ?? Color(hex: 0x0b2f38)
        let shape = RoundedRectangle(cornerRadius: 34, style: .continuous)
        return VStack(alignment: .leading, spacing: 4) {
            Button { close() } label: {
                Capsule().fill(V4.ink.opacity(0.4)).frame(width: 40, height: 5).frame(width: 60, height: 14)
            }
            .plain().frame(maxWidth: .infinity).accessibilityLabel("Lukk")
            HStack(spacing: 14) {
                V4Art(key: key, radius: 10).frame(width: 56, height: 56).shadow(color: .black.opacity(0.4), radius: 8, y: 6)
                VStack(alignment: .leading, spacing: 3) {
                    Text(title).sora(18, .semibold).lineLimit(1)
                    HStack(spacing: 6) {
                        V4SourceIcon(label: m.v4SrcIcon, size: 16)
                        Text(artist).sora(14, .regular, V4.ink.opacity(0.7)).lineLimit(1)
                    }
                }
            }
            .padding(.horizontal, 4).padding(.top, 4).padding(.bottom, 8)
            ForEach(rows, id: \.n) { r in row(r) }
            Rectangle().fill(Color.white.opacity(0.1)).frame(height: 1).padding(.horizontal, 4).padding(.vertical, 6)
            HStack(spacing: 14) {
                V4SourceIcon(label: m.v4SrcIcon, size: 34).frame(width: 40)
                VStack(alignment: .leading, spacing: 1) {
                    Text(m.v4Src).sora(15, .semibold)
                    Text(m.quality).mono(11, V4.ink.opacity(0.6))
                }
            }
            .padding(.horizontal, 4).frame(minHeight: 48)
        }
        .padding(.horizontal, 16).padding(.top, 10).padding(.bottom, 26)
        .background(shape.fill(LinearGradient(colors: [top.opacity(0.93), mid.opacity(0.95)], startPoint: .top, endPoint: .bottom)))
        .glassEffect(.regular, in: shape)
        .overlay(shape.stroke(LinearGradient(colors: [Color.white.opacity(0.3), .clear], startPoint: .top, endPoint: .center), lineWidth: 1))
        .shadow(color: .black.opacity(0.5), radius: 20, y: -10)
    }

    private struct Row { var n: String; var p: String; var fill: Bool; var ic: Color; var sw: Bool? = nil; var val: String? = nil; var act: () -> Void }

    private var favs: Set<String> { Set(favsRaw.split(separator: "\n").map(String.init)) }

    private var rows: [Row] {
        var r: [Row] = []
        let isFav: Bool
        if m.input == 3 && t == nil { isFav = m.favIndex(m.curRadio.name) != nil } else { isFav = favs.contains(title) }
        r.append(Row(n: isFav ? "Lagret i Skjold-favoritter" : "Lagre i Skjold-favoritter", p: V4.heart, fill: isFav,
                     ic: isFav ? V4.gold : V4.ink) { toggleFav() })
        r.append(Row(n: "Spill neste", p: V4.queue, fill: false, ic: V4.ink) {
            if let t { m.v4PlayNext(t); Haptics.success() } else { Haptics.warning() }
            close()
        })
        r.append(Row(n: "Legg til i spilleliste", p: "M4 6h12M4 12h12M4 18h8M18 15v6M15 18h6", fill: false, ic: V4.ink) { Haptics.warning() })
        let who = artist.components(separatedBy: " · ").first ?? artist
        r.append(Row(n: "Søk etter " + who, p: V4.search, fill: false, ic: V4.ink) {
            close(); m.full = false; ui.sq = who; ui.search = true
        })
        r.append(Row(n: "Fjern fra køen", p: V4.close, fill: false, ic: V4.ink) {
            if let t { m.v4QueueRemove(t) }
            close()
        })
        r.append(Row(n: "Krysstoning", p: "M3 6l9 6-9 6zM21 6l-9 6 9 6z", fill: false, ic: V4.ink, sw: ui.xfade) {
            withAnimation(V4.toggle) { ui.xfade.toggle() }
        })
        r.append(Row(n: "Sovetimer", p: "M12 21a8 8 0 1 0 0-16a8 8 0 1 0 0 16M12 9v4l2 2M5 3L2 6M19 3l3 3", fill: false,
                     ic: ui.sleep > 0 ? V4.gold : V4.ink, val: Self.sleeps[ui.sleep]) {
            ui.sleep = (ui.sleep + 1) % Self.sleeps.count
        })
        return r
    }

    private func row(_ r: Row) -> some View {
        Button { Haptics.tap(); r.act() } label: {
            HStack(spacing: 14) {
                ZStack {
                    Circle().fill(V4.ink.opacity(0.12))
                    if r.fill { V4Icon(d: r.p, size: 21, color: r.ic, fill: true) }
                    V4Icon(d: r.p, size: 21, color: r.ic)
                }
                .frame(width: 40, height: 40)
                Text(r.n).sora(16, .semibold, lineHeight: 1.3).frame(maxWidth: .infinity, alignment: .leading)
                if let on = r.sw { pillSwitch(on) }
                if let v = r.val {
                    HStack(spacing: 8) {
                        Text(v).sora(14, .regular, V4.ink.opacity(0.65))
                        V4Icon(d: V4.chevRight, size: 16, stroke: 2.2, color: V4.ink)
                    }
                }
            }
            .padding(.horizontal, 4).frame(minHeight: 50)
            .contentShape(Rectangle())
        }
        .plain()
    }

    /// Bryteren i arket: kant 1.5 rgba(242,242,238,.8), fylt .9 når på, knott 23.
    private func pillSwitch(_ on: Bool) -> some View {
        ZStack(alignment: .topLeading) {
            Capsule().fill(on ? V4.ink.opacity(0.9) : .clear)
            Capsule().strokeBorder(V4.ink.opacity(0.8), lineWidth: 1.5)
            Circle().fill(on ? V4.bg : V4.ink).frame(width: 23, height: 23).offset(x: on ? 22 : 2.5, y: 2.5)
        }
        .frame(width: 51, height: 31)
        .animation(V4.toggle, value: on)
    }

    private func toggleFav() {
        if m.input == 3 && t == nil { m.toggleFav(m.curRadio); return }
        var f = favs
        if f.contains(title) { f.remove(title) } else { f.insert(title); Haptics.success() }
        favsRaw = f.sorted().joined(separator: "\n")
    }

    private func close() { withAnimation(V4.moreSheet) { ui.more = false } }
}

/// Volumknotten: hold på minispilleren i 450 ms. −150° … +150°, 31 streker.
struct V4VolumeDial: View {
    @Environment(AppModel.self) private var m
    @Environment(V4State.self) private var ui

    var body: some View {
        ZStack {
            Rectangle().fill(.ultraThinMaterial).ignoresSafeArea()
                .overlay(Color(hex: 0x050506, alpha: 0.6).ignoresSafeArea())
                .onTapGesture { withAnimation(V4.fade) { ui.dial = false } }
            VStack(spacing: 26) {
                HStack(spacing: 8) {
                    Circle().fill(V4.green).frame(width: 6, height: 6)
                    Text(m.v4GroupName).sora(13, .semibold)
                }
                .padding(.horizontal, 14).frame(height: 34)
                .background(Capsule().fill(Color(hex: 0x28282a, alpha: 0.7)))
                .overlay(Capsule().strokeBorder(Color.white.opacity(0.12), lineWidth: 1))
                knob
                Text("Dra rundt knotten · trykk utenfor for å lukke").sora(13, .regular, V4.body)
            }
        }
    }

    private var vol: Int { m.v4GroupVol }

    private var knob: some View {
        let lit = Int((Double(vol) / 100 * 30).rounded())
        return ZStack {
            ForEach(0..<31, id: \.self) { i in
                let on = i <= lit && vol > 0
                let tip = i == lit
                RoundedRectangle(cornerRadius: 3)
                    .fill(on ? (tip ? Color(hex: 0xfff3d6) : V4.gold) : V4.ink.opacity(0.16))
                    .frame(width: 5, height: tip ? 24 : 15)
                    .shadow(color: on ? V4.gold.opacity(0.55) : .clear, radius: 5)
                    .offset(y: -140)
                    .rotationEffect(.degrees(-150 + Double(i) * 10))
            }
            Circle()
                .fill(RadialGradient(colors: [Color(hex: 0x3c3c3f), Color(hex: 0x1a1a1c), Color(hex: 0x0d0d0e)],
                                     center: UnitPoint(x: 0.36, y: 0.28), startRadius: 0, endRadius: 140))
                .frame(width: 200, height: 200)
                .overlay(Circle().stroke(Color.white.opacity(0.14), lineWidth: 1).blur(radius: 0.5).mask(LinearGradient(colors: [.black, .clear], startPoint: .top, endPoint: .center)))
                .shadow(color: .black.opacity(0.7), radius: 25, y: 24)
            RoundedRectangle(cornerRadius: 3).fill(V4.ink).frame(width: 5, height: 30)
                .offset(y: -100 + 14 + 15)
                .rotationEffect(.degrees(-150 + Double(vol) * 3))
            VStack(spacing: 2) {
                Text("\(vol)").sora(56, .light).tracking(-1.68)
                Text("VOLUM").mono(10, V4.muted, em: 0.14)
            }
            .allowsHitTesting(false)
        }
        .frame(width: 310, height: 310)
        .contentShape(Circle())
        .gesture(DragGesture(minimumDistance: 0).onChanged { v in
            let dx = v.location.x - 155, dy = v.location.y - 155
            let a = max(-150, min(150, atan2(dx, -dy) * 180 / .pi))
            let n = Int(((a + 150) / 3).rounded())
            if n != vol { Haptics.tick(); m.v4SetGroupVol(n) }
        })
        .accessibilityElement()
        .accessibilityLabel("Volum")
        .accessibilityValue("\(vol)")
        .accessibilityAdjustableAction { d in m.v4SetGroupVol(vol + (d == .increment ? 5 : -5)) }
    }
}
