import SwiftUI
import WidgetKit
import AppIntents

@main
struct SkjoldWidgetsBundle: WidgetBundle {
    var body: some Widget {
        SkjoldNowPlayingWidget()
        SkjoldFavoritesWidget()
        SkjoldPlayControl()
        SkjoldLiveActivity()
    }
}

// MARK: - Tidslinje (felles for begge widgetene)

struct SkjoldEntry: TimelineEntry {
    let date: Date
    let state: SharedNowPlaying
}

struct SkjoldProvider: TimelineProvider {
    func placeholder(in context: Context) -> SkjoldEntry {
        SkjoldEntry(date: Date(), state: .placeholder)
    }

    func getSnapshot(in context: Context, completion: @escaping (SkjoldEntry) -> Void) {
        let s = SkjoldShared.load()
        let show = context.isPreview && s.host.isEmpty ? SharedNowPlaying.placeholder : s
        completion(SkjoldEntry(date: Date(), state: show))
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<SkjoldEntry>) -> Void) {
        Task {
            let s = await SkjoldShared.fetch()
            let next = Date().addingTimeInterval(15 * 60)
            completion(Timeline(entries: [SkjoldEntry(date: Date(), state: s)], policy: .after(next)))
        }
    }
}

// MARK: - Spiller nå

struct SkjoldNowPlayingWidget: Widget {
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: "no.kristo.skjold.nowplaying", provider: SkjoldProvider()) { entry in
            NowPlayingView(state: entry.state)
                .containerBackground(for: .widget) { W.bg }
        }
        .configurationDisplayName("Spiller nå")
        .description("Det som spiller på Skjold, med spill/pause, neste og volum.")
        .supportedFamilies([.systemSmall, .systemMedium, .accessoryRectangular, .accessoryCircular, .accessoryInline])
    }
}

struct NowPlayingView: View {
    let state: SharedNowPlaying
    @Environment(\.widgetFamily) private var family

    var body: some View {
        switch family {
        case .systemSmall: small
        case .accessoryRectangular: rect
        case .accessoryCircular: circular
        case .accessoryInline: inline
        default: medium
        }
    }

    private var playSymbol: String { state.playing ? "pause.fill" : "play.fill" }

    private var small: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .top) {
                WCover(state: state, size: 54, radius: 10)
                Spacer(minLength: 4)
                Button(intent: SkjoldPlayPauseIntent()) { WRoundIcon(symbol: playSymbol, size: 36, filled: true) }
                    .buttonStyle(.plain)
            }
            Spacer(minLength: 0)
            Text(state.room.uppercased())
                .font(W.mono(9)).tracking(1.2).foregroundStyle(W.muted).lineLimit(1)
            Text(state.title)
                .font(W.sora(14, true)).foregroundStyle(W.ink).lineLimit(2)
            Text(state.subtitle.isEmpty ? state.source : state.subtitle)
                .font(W.sora(11)).foregroundStyle(W.muted).lineLimit(1)
        }
    }

    private var medium: some View {
        HStack(spacing: 14) {
            WCover(state: state, size: 112, radius: 14)
            VStack(alignment: .leading, spacing: 4) {
                Text((state.room + " · " + state.source).uppercased())
                    .font(W.mono(9)).tracking(1.2).foregroundStyle(W.accent2).lineLimit(1)
                Text(state.title)
                    .font(W.sora(16, true)).foregroundStyle(W.ink).lineLimit(2)
                Text(state.subtitle)
                    .font(W.sora(12)).foregroundStyle(W.muted).lineLimit(1)
                Spacer(minLength: 0)
                controls
            }
        }
    }

    private var controls: some View {
        HStack(spacing: 8) {
            Button(intent: SkjoldVolumeIntent(delta: -5)) { WRoundIcon(symbol: "minus", size: 30) }
                .buttonStyle(.plain)
            Text("\(state.volume)")
                .font(W.mono(12)).foregroundStyle(W.accent2).frame(minWidth: 24)
            Button(intent: SkjoldVolumeIntent(delta: 5)) { WRoundIcon(symbol: "plus", size: 30) }
                .buttonStyle(.plain)
            Spacer(minLength: 0)
            Button(intent: SkjoldPlayPauseIntent()) { WRoundIcon(symbol: playSymbol, size: 36, filled: true) }
                .buttonStyle(.plain)
            Button(intent: SkjoldNextIntent()) { WRoundIcon(symbol: "forward.fill", size: 30) }
                .buttonStyle(.plain)
        }
    }

    private var rect: some View {
        HStack(spacing: 8) {
            VStack(alignment: .leading, spacing: 1) {
                Text(state.title).font(.headline).lineLimit(1)
                Text(state.subtitle.isEmpty ? state.room : state.subtitle).font(.caption).lineLimit(1)
            }
            Spacer(minLength: 0)
            Button(intent: SkjoldPlayPauseIntent()) { Image(systemName: playSymbol).font(.title3) }
                .buttonStyle(.plain)
        }
        .widgetAccentable()
    }

    private var circular: some View {
        ZStack {
            AccessoryWidgetBackground()
            Button(intent: SkjoldPlayPauseIntent()) { Image(systemName: playSymbol).font(.title2) }
                .buttonStyle(.plain)
        }
    }

    private var inline: some View {
        Text(state.playing ? "▶︎ " + state.title : state.room + " · pause")
    }
}

// MARK: - Radiofavoritter

struct SkjoldFavoritesWidget: Widget {
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: "no.kristo.skjold.favorites", provider: SkjoldProvider()) { entry in
            FavoritesView(state: entry.state)
                .containerBackground(for: .widget) { W.bg }
        }
        .configurationDisplayName("Radiofavoritter")
        .description("Spill en radiofavoritt på Skjold med ett trykk.")
        .supportedFamilies([.systemMedium, .systemLarge])
    }
}

struct FavoritesView: View {
    let state: SharedNowPlaying
    @Environment(\.widgetFamily) private var family

    private var items: [String] {
        let list = state.presets.isEmpty ? SharedNowPlaying.placeholder.presets : state.presets
        return Array(list.prefix(family == .systemLarge ? 8 : 4))
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("RADIOFAVORITTER").font(W.mono(9)).tracking(1.4).foregroundStyle(W.muted)
                Spacer()
                Text(state.room).font(W.sora(11)).foregroundStyle(W.muted).lineLimit(1)
            }
            LazyVGrid(columns: [GridItem(.flexible(), spacing: 8), GridItem(.flexible(), spacing: 8)], spacing: 8) {
                ForEach(Array(items.enumerated()), id: \.offset) { pair in
                    tile(pair.offset + 1, pair.element)
                }
            }
            Spacer(minLength: 0)
        }
    }

    private func tile(_ n: Int, _ name: String) -> some View {
        let on = n == state.activePreset && state.playing
        return Button(intent: SkjoldPresetIntent(n: n)) {
            HStack(spacing: 8) {
                Text("\(n)")
                    .font(W.mono(10))
                    .foregroundStyle(on ? W.accent2 : W.muted)
                    .frame(width: 18, height: 18)
                    .background(Circle().stroke(on ? W.accent : W.line, lineWidth: 1))
                Text(name)
                    .font(W.sora(12, true))
                    .foregroundStyle(on ? W.accent2 : W.ink)
                    .lineLimit(1)
                Spacer(minLength: 0)
            }
            .padding(.horizontal, 10)
            .frame(height: family == .systemLarge ? 46 : 40)
            .background(RoundedRectangle(cornerRadius: 12, style: .continuous).fill(on ? W.selBg : W.card))
            .overlay(RoundedRectangle(cornerRadius: 12, style: .continuous).stroke(on ? W.accent.opacity(0.6) : W.line, lineWidth: 1))
        }
        .buttonStyle(.plain)
    }
}

// MARK: - Kontrollsenter

struct SkjoldPlayControl: ControlWidget {
    var body: some ControlWidgetConfiguration {
        StaticControlConfiguration(kind: "no.kristo.skjold.control.playpause") {
            ControlWidgetButton(action: SkjoldPlayPauseIntent()) {
                Label("Skjold", systemImage: "playpause.fill")
            }
        }
        .displayName("Spill/pause Skjold")
        .description("Spill eller pause det som spiller på Skjold.")
    }
}
