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
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.unit.dp

/** 09 Hjem: logo + room pill, active room card, recently played, sources, radio favourites. */
@Composable
fun HomeView(m: AppModel) {
    val uri = LocalUriHandler.current
    val room = m.actRoom
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        SKLogo()
        Spacer(Modifier.weight(1f))
        Row(
            Modifier.height(32.dp).clip(CircleShape).background(C.card).skCapsuleBorder(C.line2).press { m.tab = 2 }.padding(horizontal = 12.dp),
            verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Dot(if (m.link == Link.OFFLINE) C.danger else if (m.live && m.link != Link.ONLINE) C.muted else C.ok)
            T(m.groupName, sora(12f), maxLines = 1)
        }
    }

    Row(
        Modifier.fillMaxWidth().skBox(C.card, C.line).press { m.tab = 2 }.padding(14.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Box(Modifier.size(44.dp).clip(RoundedCornerShape(12.dp)).background(C.selBg).skBorder(C.selLine, 12.dp), contentAlignment = Alignment.Center) {
            SKIcon(SK.dev(room.type).icon, 24.dp, 1.5f, C.accent2)
        }
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            T(room.name, sora(15f, W.Semibold))
            T(SK.dev(room.type).n, sora(12f, W.Semibold, C.accent2))
            T(AppModel.hwText(room), mono(10f), Modifier.padding(top = 2.dp), maxLines = 1)
        }
        Box(Modifier.height(28.dp).skCapsuleBorder(C.line2).padding(horizontal = 12.dp), contentAlignment = Alignment.Center) {
            T("Bytt", sora(12f, W.Regular, C.ink2))
        }
    }

    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        SKSectionHeader("Nylig spilt")
        EdgeScroll(12.dp) {
            for (r in recent(m)) {
                Column(Modifier.width(118.dp).press(onClick = r.pick), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    val a = art(r.key)
                    Box(Modifier.size(118.dp).clip(RoundedCornerShape(if (r.round) 59.dp else 10.dp)), contentAlignment = Alignment.BottomStart) {
                        ArtFill(a)
                        T(r.big, sora(14f, W.Semibold, a.ink, 1.05f), Modifier.padding(10.dp))
                    }
                    T(r.title, sora(13f), maxLines = 1)
                    T(r.kind, sora(11f, W.Regular, C.muted))
                }
            }
        }
    }

    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        SKSectionHeader("Kilder")
        EdgeScroll(14.dp) {
            for ((label, act) in services(m) { u -> try { uri.openUri(u) } catch (_: Exception) { Haptics.warning() } }) SKSourceLogo(label, act)
        }
    }

    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            T("Radiofavoritter", sora(17f, W.Semibold))
            Spacer(Modifier.weight(1f))
            SKLinkButton("Administrer") { m.sub = "radio" }
        }
        EdgeScroll(12.dp) {
            m.radio.forEachIndexed { i, st ->
                Column(Modifier.width(96.dp).press { m.playStation(i) }, verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    val a = art(st.name)
                    Box(Modifier.size(96.dp).clip(RoundedCornerShape(12.dp))) {
                        ArtFill(a)
                        Column(Modifier.fillMaxSize().padding(9.dp)) {
                            T("${i + 1}", mono(9f, a.ink.copy(alpha = a.ink.alpha * 0.8f)))
                            Spacer(Modifier.weight(1f))
                            T(st.name, sora(13f, W.Semibold, a.ink, 1.05f))
                        }
                    }
                    T(st.genre, sora(11f, W.Regular, C.muted), maxLines = 1)
                }
            }
        }
    }
}

private data class Recent(val title: String, val key: String, val big: String, val kind: String, val round: Boolean, val pick: () -> Unit)

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
        "UPnP/DLNA" to { m.pickService("upnp") },
        "YT Music" to { m.openLib("ytm") },
        "Navidrome" to { m.openLib("nd") },
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
