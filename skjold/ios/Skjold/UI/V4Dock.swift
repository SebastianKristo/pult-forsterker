import SwiftUI

/// Minispilleren som tilbehør i systemets fanelinje (tabViewBottomAccessory). Systemet tegner Liquid Glass-
/// kapselen rundt; her ligger bare innholdet. Utvidet: omslag, tittel, «gruppe · kilde», spill/pause med
/// fremdriftsring. Innfelt (fanelinjen minimert ved rulling): omslag, tittel og spill/pause.
/// Trykk = Nå spilles, hold 450 ms = volumknotten.
struct V4MiniAccessory: View {
    @Environment(AppModel.self) private var m
    @Environment(V4State.self) private var ui
    @Environment(\.tabViewBottomAccessoryPlacement) private var placement

    var body: some View {
        let inline = placement == .inline
        HStack(spacing: 10) {
            V4Art(key: m.playerArt.key, radius: inline ? 7 : 9)
                .frame(width: inline ? 28 : 34, height: inline ? 28 : 34)
            VStack(alignment: .leading, spacing: 1) {
                Text(m.np.t).sora(inline ? 13 : 14, .semibold).lineLimit(1)
                if !inline {
                    Text(m.v4GroupName + " · " + m.np.s).sora(11, .regular, V4.sub).lineLimit(1)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            V4RingPlay(size: inline ? 32 : 38)
        }
        .padding(.leading, inline ? 6 : 8).padding(.trailing, 4)
        .contentShape(Rectangle())
        .onTapGesture { Haptics.thump(); m.full = true }
        .onLongPressGesture(minimumDuration: 0.45) {
            Haptics.thump(); ui.hideHint(); withAnimation(V4.fade) { ui.dial = true }
        }
        .accessibilityElement(children: .contain)
        .accessibilityLabel("Spiller nå: \(m.np.t)")
    }
}

/// Spill/pause 48 med fremdriftsring (r 21.5, strek 3, spor .18, fremdrift #f0c46a, 1 s lineær).
struct V4RingPlay: View {
    @Environment(AppModel.self) private var m
    var size: CGFloat = 48
    var body: some View {
        Button { m.togglePlay() } label: {
            ZStack {
                Circle().fill(Color.black.opacity(0.25))
                Circle().stroke(V4.ink.opacity(0.18), lineWidth: 3).padding(max(1.5, 1.5 + (size - 46) / 2))
                Circle().trim(from: 0, to: CGFloat(m.v4Progress))
                    .stroke(V4.gold, style: StrokeStyle(lineWidth: 3, lineCap: .round))
                    .rotationEffect(.degrees(-90))
                    .padding(max(1.5, 1.5 + (size - 46) / 2))
                    .animation(.linear(duration: 1), value: m.v4Progress)
                V4PlayIcon(playing: m.playing, size: 18, color: V4.ink)
            }
            .frame(width: size, height: size)
        }
        .plain()
        .accessibilityLabel("Spill/pause")
    }
}
