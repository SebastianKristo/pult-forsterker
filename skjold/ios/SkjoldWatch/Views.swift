import SwiftUI
import WatchKit

private let gold = Color(red: 0.85, green: 0.65, blue: 0.29)

/// Cover eller kanallogo; fargefelt med forbokstav når det ikke finnes noe bilde.
struct ArtView: View {
    @EnvironmentObject var store: WatchStore
    var path: String
    var title: String
    var size: CGFloat

    var body: some View {
        Group {
            if let u = store.imageURL(path) {
                AsyncImage(url: u) { img in img.resizable().scaledToFill() } placeholder: { fallback }
            } else { fallback }
        }
        .frame(width: size, height: size)
        .clipShape(RoundedRectangle(cornerRadius: size * 0.18))
    }

    private var fallback: some View {
        ZStack {
            LinearGradient(colors: [gold.opacity(0.55), Color(white: 0.12)], startPoint: .topLeading, endPoint: .bottomTrailing)
            Text(String(title.prefix(1))).font(.system(size: size * 0.4, weight: .semibold)).foregroundStyle(.white)
        }
    }
}

/// Spiller nå. Digital Crown styrer volumet (haptikk per steg, og et tydelig klikk ved 0 og 100).
struct NowPlayingView: View {
    @EnvironmentObject var store: WatchStore
    @State private var crown: Double = 0
    @State private var sent = 0
    @State private var touching = false

    var body: some View {
        let st = store.status
        VStack(spacing: 6) {
            if store.host.isEmpty {
                Text("Åpne Skjold på iPhone for å koble til klokka.").font(.footnote).multilineTextAlignment(.center)
            } else {
                HStack {
                    Text(store.roomName).font(.footnote.weight(.semibold)).foregroundStyle(gold).lineLimit(1)
                    Spacer()
                    if !store.reachable { Image(systemName: "wifi.slash").font(.caption2).foregroundStyle(.secondary) }
                    else if store.viaPhone { Image(systemName: "iphone").font(.caption2).foregroundStyle(.secondary) }
                }
                HStack(spacing: 8) {
                    ArtView(path: st.art, title: st.title.isEmpty ? store.roomName : st.title, size: 48)
                    VStack(alignment: .leading, spacing: 1) {
                        Text(st.title.isEmpty ? (st.power ? "Ingenting spilles" : "Av") : st.title)
                            .font(.headline).lineLimit(2)
                        if !st.artist.isEmpty { Text(st.artist).font(.caption2).foregroundStyle(.secondary).lineLimit(1) }
                    }
                    Spacer(minLength: 0)
                }
                HStack(spacing: 10) {
                    Button { store.power(!st.power) } label: { Image(systemName: "power") }
                        .tint(st.power ? gold : .gray)
                    Button { store.transport("playpause") } label: { Image(systemName: st.playing ? "pause.fill" : "play.fill") }
                    Button { store.transport("next") } label: { Image(systemName: "forward.fill") }
                }
                .buttonStyle(.bordered)
                Gauge(value: Double(st.volume), in: 0...100) { Text("Volum") } currentValueLabel: { Text("\(st.volume)") }
                    .gaugeStyle(.accessoryLinearCapacity).tint(gold)
            }
        }
        .padding(.horizontal, 4)
        .focusable(true)
        .digitalCrownRotation($crown, from: 0, through: 100, by: 1, sensitivity: .medium,
                              isContinuous: false, isHapticFeedbackEnabled: true)
        .onAppear { crown = Double(store.status.volume); sent = store.status.volume }
        .onChange(of: store.status.volume) { _, v in if abs(Double(v) - crown) > 1.5 && v != sent { crown = Double(v) } }
        .onChange(of: crown) { _, v in
            let n = Int(v.rounded())
            guard n != sent else { return }
            if n == 0 || n == 100 { WKInterfaceDevice.current().play(.click) }
            sent = n
            store.setVolume(n)
        }
        .navigationTitle("Skjold")
    }
}

struct FavoritesView: View {
    @EnvironmentObject var store: WatchStore

    var body: some View {
        List {
            if store.status.favs.isEmpty {
                Text("Ingen favoritter").foregroundStyle(.secondary)
            }
            ForEach(store.status.favs) { f in
                Button { WKInterfaceDevice.current().play(.click); store.playFav(f.n) } label: {
                    HStack(spacing: 8) {
                        ArtView(path: f.logo, title: f.title, size: 30)
                        Text(f.title).lineLimit(2)
                        Spacer(minLength: 0)
                        if store.status.preset == f.n && store.status.power { Image(systemName: "speaker.wave.2.fill").foregroundStyle(gold) }
                    }
                }
            }
        }
        .navigationTitle("Favoritter")
    }
}

struct RoomsView: View {
    @EnvironmentObject var store: WatchStore

    var body: some View {
        List {
            if store.rooms.isEmpty {
                Text("Åpne Skjold på iPhone for å hente rommene.").font(.footnote).foregroundStyle(.secondary)
            }
            ForEach(store.rooms) { r in
                Button { WKInterfaceDevice.current().play(.click); store.select(r) } label: {
                    HStack {
                        Image(systemName: "hifispeaker.fill").foregroundStyle(r.host == store.host ? gold : .secondary)
                        Text(r.name).lineLimit(1)
                        Spacer(minLength: 0)
                        if r.host == store.host { Image(systemName: "checkmark").foregroundStyle(gold) }
                    }
                }
            }
        }
        .navigationTitle("Rom")
    }
}
