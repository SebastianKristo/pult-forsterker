package no.kristo.skjold

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em

/** 09 Hjem: logo + room pill, active room card, recently played, sources, radio favourites. */
@Composable
fun HomeView(m: AppModel) {
    // v4: hjemmets navn (32/600, −0.02em) med pil som bytter hjem, og en kapsel med søk og innstillinger
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.weight(1f)) { StedPicker(m, 32f) }
        Row(
            Modifier.height(44.dp).clip(CircleShape).background(SkG.pillBg).skCapsuleBorder(SkG.pillLine).padding(horizontal = 4.dp),
            verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(2.dp),
        ) {
            Box(Modifier.size(38.dp).clip(CircleShape).press { m.sub = "radio" }, contentAlignment = Alignment.Center) {
                SKIcon("M11 18a7 7 0 1 0 0-14a7 7 0 1 0 0 14M20 20l-4-4", 20.dp, 1.8f, C.ink)
            }
            Box(Modifier.size(38.dp).clip(CircleShape).press { m.tab = 3; m.setCat = -1 }, contentAlignment = Alignment.Center) {
                SKIcon(Icons.tabSettings, 20.dp, 1.8f, C.ink)
            }
        }
    }

    var editHome by remember { mutableStateOf(false) }
    // Seksjonene i rekkefølgen brukeren har valgt (settings.homeLayout, delt med web og iOS).
    for (sec in HomeLayout.resolve(m.homeLayout, HomeLayout.android).filter { s -> s.visible }) {
        when (sec.id) {
            "recent" -> RecentShelf(m)
            "sources" -> SourcesShelf(m)
            "favs" -> FavShelf(m)
            "playlists" -> PlaylistShelf(m)
        }
    }
    T("Rediger hjemskjerm", sora(13f, W.Regular, C.muted), Modifier.fillMaxWidth().press { editHome = true }.padding(vertical = 8.dp), align = TextAlign.Center)
    if (editHome) HomeEditorDialog(m) { editHome = false }
}


@Composable
private fun RecentShelf(m: AppModel) {
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        T("Nylig spilt ›", sora(SkG.shelfTitle, W.Semibold))
        EdgeScroll(12.dp) {
            for (r in recent(m)) {
                Column(Modifier.width(SkG.recentSize).press(onClick = r.pick), verticalArrangement = Arrangement.spacedBy(7.dp)) {
                    val a = art(r.key)
                    Box(Modifier.size(SkG.recentSize).clip(RoundedCornerShape(SkG.recentR)), contentAlignment = Alignment.BottomStart) {
                        ArtFill(a)
                        T(r.big, sora(15f, W.Semibold, a.ink, 1.05f), Modifier.padding(11.dp))
                    }
                    T(r.title, sora(13f, W.Semibold), maxLines = 1)
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        SourceGlyph(r.src, 16.dp)
                        T(r.src, sora(11f, W.Regular, SkG.subText), maxLines = 1)
                    }
                }
            }
        }
    }

}

@Composable
private fun SourcesShelf(m: AppModel) {
    val uri = LocalUriHandler.current
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        T("Kilder", sora(SkG.shelfTitle, W.Semibold))
        EdgeScroll(14.dp) {
            for ((label, act) in services(m) { u -> try { uri.openUri(u) } catch (_: Exception) { Haptics.warning() } }) SKSourceLogo(label, act)
        }
    }

}

@Composable
private fun FavShelf(m: AppModel) {
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        T("Radiofavoritter ›", sora(SkG.shelfTitle, W.Semibold), Modifier.press { m.sub = "radio" })
        EdgeScroll(12.dp) {
            m.radio.forEachIndexed { i, st ->
                val on = m.input == 3 && m.station == i
                Column(
                    Modifier.size(SkG.favSize).clip(RoundedCornerShape(16.dp)).background(SkG.favBg).skBorder(if (on) C.accent else C.line, 16.dp)
                        .press { m.playStation(i) }.padding(10.dp),
                ) {
                    T("${i + 1}", mono(9f))
                    Spacer(Modifier.weight(1f))
                    FavName(st.name)
                }
            }
        }
    }
}

@Composable
private fun PlaylistShelf(m: AppModel) {
    // v4: «Dine spillelister» – spillelister fra Navidrome/Plex/YouTube Music som er lastet inn
    val pls = playlists(m)
    if (pls.isNotEmpty()) {
        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            T("Dine spillelister", sora(SkG.shelfTitle, W.Semibold))
            EdgeScroll(12.dp) {
                for ((lib, p) in pls) {
                    Column(Modifier.width(SkG.recentSize).press { m.openLib(lib) }, verticalArrangement = Arrangement.spacedBy(7.dp)) {
                        val a = art(p.name)
                        Box(Modifier.size(SkG.recentSize).clip(RoundedCornerShape(SkG.recentR)), contentAlignment = Alignment.BottomStart) {
                            ArtFill(a)
                            T(p.name, sora(15f, W.Semibold, a.ink, 1.05f), Modifier.padding(11.dp), maxLines = 2)
                        }
                        T(p.name, sora(13f, W.Semibold), maxLines = 1)
                        T(if (p.count > 0) "${p.count} låter" else "Spilleliste", sora(11f, W.Regular, SkG.subText), maxLines = 1)
                    }
                }
            }
        }
    }}

private fun playlists(m: AppModel): List<Pair<String, LibColl>> {
    val out = ArrayList<Pair<String, LibColl>>()
    // YouTube Music: også «Til deg» (mikser og anbefalte album fra forsiden)
    for ((lib, d) in m.libs) for (p in (if (lib == "ytm") (d.playlists + d.frequent.take(8) + d.other.take(8)).distinctBy { it.id } else d.playlists)) out.add(lib to p)
    return out.take(12)
}

/** «NRK P1»: første ord hvitt og fett, resten i kanalfargen (20/700, −0.02em). */
@Composable
private fun FavName(name: String) {
    val parts = name.split(" ", limit = 2)
    val colors = mapOf("P1" to hex(0x7fa8ff), "P2" to hex(0xe86fa8), "P3" to hex(0xf5d53a))
    Row(horizontalArrangement = Arrangement.spacedBy(4.dp), verticalAlignment = Alignment.Bottom) {
        T(parts[0], sora(20f, W.Semibold).copy(letterSpacing = (-0.02f).em), maxLines = 1)
        if (parts.size > 1) T(parts[1], sora(20f, W.Regular, colors[parts[1]] ?: C.accent2).copy(letterSpacing = (-0.02f).em), maxLines = 1)
    }
}

private data class Recent(val title: String, val key: String, val big: String, val kind: String, val round: Boolean, val pick: () -> Unit) {
    /** kilden (før « · ») – vises med kildeikonet under omslaget */
    val src: String get() = kind.substringBefore(" · ")
}

private fun recent(m: AppModel): List<Recent> {
    if (!m.demo) return liveRecent(m)
    val out = ArrayList<Recent>()
    for (i in 0 until 2) {
        val t = SK.tr[i]
        out.add(Recent(t.first, t.first, t.second, "AirPlay · låt", false) { m.input = 0; m.trk = i; m.full = true })
    }
    m.radio.take(2).forEachIndexed { i, st -> out.add(Recent(st.name, st.name, st.name, "Radio · kanal", true) { m.playStation(i) }) }
    val t = SK.tr[2]
    out.add(Recent(t.first, t.first, t.second, "Blåtann · låt", false) { m.input = 1; m.trk = 2; m.full = true })
    return out
}

/** Live: the latest library tracks played from the app, then the first radio favourites. */
private fun liveRecent(m: AppModel): List<Recent> {
    val out = ArrayList<Recent>()
    val names = mapOf("nd" to "Navidrome", "plex" to "Plex", "ytm" to "YouTube Music")
    for ((lib, h) in m.hist.toSortedMap()) {
        val list = h.map { it.track }
        h.take(2).forEachIndexed { i, e ->
            out.add(Recent(e.track.t, e.track.album, e.track.artist, (names[lib] ?: lib) + " · låt", false) { m.lib = lib; m.playLib(list, i) })
        }
    }
    m.radio.take(maxOf(2, 5 - out.size)).forEachIndexed { i, st -> out.add(Recent(st.name, st.name, st.name, "Radio · kanal", true) { m.playStation(i) }) }
    return out
}

private fun services(m: AppModel, open: (String) -> Unit): List<Pair<String, () -> Unit>> {
    val node = m.actRoom.type == "node"
    val list = mutableListOf<Pair<String, () -> Unit>>(
        "Radio" to { m.sub = "radio" },
        "AirPlay" to { m.pickInput(0); m.full = true },
        "Blåtann" to (if (node) ({
            m.tab = 3; m.setDev = m.actRoom.id
            m.setCat = SK.catsFor("node").indexOfFirst { it.id == "tilkobling" }
        }) else ({ m.pickInput(1); m.full = true })),
        "Spotify" to { m.pickService("spotify") },
        "YT Music" to { m.openLib("ytm") },
        "Navidrome" to { m.openLib("nd") },
        "UPnP/DLNA" to { m.pickService("upnp") },
        "Plex" to { m.openLib("plex") },
        "Lyrion" to {
            val u = m.lyrionURL ?: if (m.demo) "http://192.168.1.42:9000/" else null
            if (u != null) open(u) else Haptics.warning()
        },
        "AUX" to { m.pickInput(2); m.full = true },
    )
    if (node) list.removeAll { it.first == "AUX" }
    return list
}
