import SwiftUI
import WidgetKit
import ActivityKit
import AppIntents

/// Live Activity: låseskjerm og Dynamic Island mens noe spiller på Skjold.
struct SkjoldLiveActivity: Widget {
    var body: some WidgetConfiguration {
        ActivityConfiguration(for: SkjoldNowPlayingAttributes.self) { context in
            LockScreenActivityView(room: context.attributes.room, state: context.state)
                .activityBackgroundTint(W.bg)
                .activitySystemActionForegroundColor(W.accent2)
        } dynamicIsland: { context in
            DynamicIsland {
                DynamicIslandExpandedRegion(.leading) {
                    ActivityCover(title: context.state.title, size: 52)
                }
                DynamicIslandExpandedRegion(.trailing) {
                    VStack(alignment: .trailing, spacing: 2) {
                        Text("\(context.state.volume)").font(W.mono(18)).foregroundStyle(W.accent2)
                        Text("VOLUM").font(W.mono(8)).foregroundStyle(W.muted)
                    }
                }
                DynamicIslandExpandedRegion(.center) {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(context.state.title).font(W.sora(15, true)).foregroundStyle(W.ink).lineLimit(1)
                        Text(subtitle(context.state, room: context.attributes.room))
                            .font(W.sora(12)).foregroundStyle(W.muted).lineLimit(1)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
                DynamicIslandExpandedRegion(.bottom) {
                    ActivityControls(playing: context.state.playing)
                }
            } compactLeading: {
                ActivityCover(title: context.state.title, size: 22, radius: 6)
            } compactTrailing: {
                Image(systemName: context.state.playing ? "waveform" : "pause.fill")
                    .foregroundStyle(W.accent2)
            } minimal: {
                Image(systemName: context.state.playing ? "waveform" : "pause.fill")
                    .foregroundStyle(W.accent2)
            }
            .keylineTint(W.accent)
        }
    }

    private func subtitle(_ s: SkjoldNowPlayingAttributes.ContentState, room: String) -> String {
        let parts = [s.subtitle, room].filter { !$0.isEmpty }
        return parts.joined(separator: " · ")
    }
}

struct LockScreenActivityView: View {
    let room: String
    let state: SkjoldNowPlayingAttributes.ContentState

    var body: some View {
        HStack(spacing: 14) {
            ActivityCover(title: state.title, size: 60, radius: 12)
            VStack(alignment: .leading, spacing: 3) {
                Text((room + " · " + state.source).uppercased())
                    .font(W.mono(9)).tracking(1.2).foregroundStyle(W.accent2).lineLimit(1)
                Text(state.title).font(W.sora(16, true)).foregroundStyle(W.ink).lineLimit(1)
                Text(state.subtitle).font(W.sora(12)).foregroundStyle(W.muted).lineLimit(1)
            }
            Spacer(minLength: 4)
            ActivityControls(playing: state.playing, compact: true)
        }
        .padding(16)
    }
}

struct ActivityCover: View {
    let title: String
    var size: CGFloat
    var radius: CGFloat = 10

    var body: some View {
        let s = SkjoldShared.load()
        return Group {
            if s.title == title, let img = WCover.image(s) {
                Image(uiImage: img).resizable().scaledToFill()
            } else {
                ZStack {
                    Rectangle().fill(W.gradient(for: title))
                    Text(String(title.prefix(1))).font(W.sora(size * 0.4, true)).foregroundStyle(W.ink.opacity(0.85))
                }
            }
        }
        .frame(width: size, height: size)
        .clipShape(RoundedRectangle(cornerRadius: radius, style: .continuous))
    }
}

struct ActivityControls: View {
    let playing: Bool
    var compact = false

    var body: some View {
        HStack(spacing: compact ? 8 : 18) {
            if !compact {
                Button(intent: SkjoldVolumeIntent(delta: -5)) { WRoundIcon(symbol: "speaker.minus.fill", size: 34) }
                    .buttonStyle(.plain)
            }
            Button(intent: SkjoldPlayPauseIntent()) {
                WRoundIcon(symbol: playing ? "pause.fill" : "play.fill", size: compact ? 38 : 42, filled: true)
            }
            .buttonStyle(.plain)
            Button(intent: SkjoldNextIntent()) { WRoundIcon(symbol: "forward.fill", size: compact ? 32 : 34) }
                .buttonStyle(.plain)
            if !compact {
                Button(intent: SkjoldVolumeIntent(delta: 5)) { WRoundIcon(symbol: "speaker.plus.fill", size: 34) }
                    .buttonStyle(.plain)
            }
        }
    }
}
