package no.kristo.skjold

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
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
import androidx.compose.foundation.layout.wrapContentWidth
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp

/*
 * Hjem (v4), som V4Home.swift på iOS: tittel med stedsvelger («Hjemme ⌄») og en kapsel med søk og innstillinger,
 * deretter seksjonene i brukerens rekkefølge (Nylig spilt, Kilder, Radiofavoritter, Dine spillelister, hyllene fra
 * bibliotekene) og «Rediger hjemskjerm». Stedsmenyen og hjelperne ligger i HomeV4.kt, redigeringen i HomeLayout.kt.
 */

@Composable
fun HomeView(m: AppModel) {
    var editHome by remember { mutableStateOf(false) }
    var placeOpen by remember { mutableStateOf(false) }
    // Fanesiden gir 6 topp og 40 bunn (V4TabPage); 22 mellom seksjonene.
    Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(22.dp)) {
        HomeHeader(m, placeOpen) { placeOpen = !placeOpen }
        // Seksjonene i rekkefølgen brukeren har valgt (settings.homeLayout, delt med web og iOS).
        for (sec in HomeLayout.resolve(m.homeLayout, HomeLayout.android).filter { it.visible }) {
            when (sec.id) {
                "recent" -> RecentShelf(m)
                "sources" -> SourcesShelf(m) { editHome = true }
                "favs" -> FavShelf(m)
                "playlists" -> PlaylistShelf(m)
                "library" -> { for (s in shelves(m)) key(s.title) { ShelfView(s) } }
            }
        }
        T(
            "Rediger hjemskjerm", sora(13f, W.Regular, HomeV4.muted),
            Modifier.fillMaxWidth().press { editHome = true }.padding(vertical = 8.dp), align = TextAlign.Center,
        )
    }
    HomePlaceMenu(m, placeOpen) { placeOpen = false }
    if (editHome) HomeEditorSheet(m) { editHome = false }
    // loadLibs(): hent bibliotekene som ikke er lastet ennå (bare koblet til en Skjold-enhet)
    LaunchedEffect(m.live) {
        if (!m.live) return@LaunchedEffect
        for (lib in listOf("ytm", "nd", "plex")) if ((m.libs[lib]?.state ?: "").isEmpty()) m.loadLib(lib)
    }
}

// MARK: Topp

/** «Hjemme ⌄» (32/600, −0.02em, pil 18 som snur seg når menyen er åpen) og kapselen med søk og innstillinger. */
@Composable
private fun HomeHeader(m: AppModel, open: Boolean, toggle: () -> Unit) {
    val rot by animateFloatAsState(if (open) 180f else 0f, tween(200, easing = HomeV4.easeInOut), label = "homeChevron")
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Box(Modifier.weight(1f)) {
            Row(
                Modifier.press(label = "Bytt sted, nå ${m.stedNavn}") { toggle(); DockUi.hideHint() },
                verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                T(m.stedNavn, sora(32f, W.Semibold).copy(letterSpacing = (-0.02f).em), Modifier.weight(1f, fill = false), maxLines = 1)
                SKIcon(HomeV4.chevDown, 18.dp, 2.2f, HomeV4.body, modifier = Modifier.padding(top = 4.dp).rotate(rot))
            }
        }
        Row(
            Modifier.height(44.dp).homeDarkPill().padding(horizontal = 4.dp),
            verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(2.dp),
        ) {
            Box(Modifier.size(38.dp).press(label = "Søk") { DockUi.hideHint(); m.openSearch() }, contentAlignment = Alignment.Center) {
                SKIcon(HomeV4.search, 20.dp, 1.8f, HomeV4.ink)
            }
            Box(Modifier.size(38.dp).press(label = "Innstillinger") { m.tab = 3; m.setCat = -1 }, contentAlignment = Alignment.Center) {
                SKIcon(HomeV4.gear, 20.dp, 1.8f, HomeV4.ink)
            }
        }
    }
}

// MARK: Nylig spilt (132 × 132, radius 16)

private data class HomeRecent(val id: String, val t: String, val key: String, val big: String, val src: String, val cur: Boolean, val play: () -> Unit)

private fun recent(m: AppModel): List<HomeRecent> {
    val out = ArrayList<HomeRecent>()
    for ((lib, h) in m.hist.toSortedMap()) {
        val list = h.map { it.track }
        h.take(3).forEachIndexed { i, e ->
            val cur = m.libTrack?.t == e.track.t
            out.add(HomeRecent("$lib-$i-${e.track.t}", e.track.t, e.track.album, e.track.artist, HomeLibNames[lib] ?: lib, cur) {
                m.lib = lib; m.playLib(list, i, keepOpen = true)
            })
        }
    }
    if (m.demo && out.isEmpty()) {
        SK.tr.forEachIndexed { i, t ->
            out.add(HomeRecent("d$i", t.first, t.first, t.second, "AirPlay", m.input == 0 && m.trk == i && m.svc == null) {
                m.pickInput(0); m.trk = i; m.pos = 0; m.playing = true
            })
        }
    }
    m.radio.take(maxOf(2, 5 - out.size)).forEachIndexed { i, st ->
        out.add(HomeRecent("r$i", st.name, st.name, st.name, "Radio", m.input == 3 && m.stIdx == i && m.rTmp == null) {
            m.playStation(i, open = false)
        })
    }
    return out
}

@Composable
private fun RecentShelf(m: AppModel) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        T("Nylig spilt ›", sora(17f, W.Semibold))
        EdgeScroll(12.dp) {
            for (r in recent(m)) key(r.id) { RecentTile(r) }
        }
    }
}

@Composable
private fun RecentTile(r: HomeRecent) {
    val a = art(r.key)
    Column(Modifier.width(132.dp).press(onClick = r.play), verticalArrangement = Arrangement.spacedBy(7.dp)) {
        Box(Modifier.size(132.dp).clip(RoundedCornerShape(16.dp)), contentAlignment = Alignment.BottomStart) {
            ArtFill(a)
            T(r.big, sora(15f, W.Semibold, a.ink, 1.05f), Modifier.padding(11.dp), maxLines = 3)
            // gull ring 2 bare når flisen spiller
            if (r.cur) Box(Modifier.fillMaxSize().skBorder(HomeV4.gold, 16.dp, 2.dp))
        }
        T(r.t, sora(13f, W.Semibold), maxLines = 1)
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            HomeSourceIcon(r.src, 16.dp)
            T(r.src, sora(11f, W.Regular, HomeV4.body), maxLines = 1)
        }
    }
}

// MARK: Kilder (68 runde ikoner)

/** Alle kildene (navn, kort etikett), som V4HomeTab.alleKilder. AUX bare på S1. */
fun homeAlleKilder(rom: String): List<Pair<String, String>> {
    val l = mutableListOf(
        "Radio" to "Radio", "AirPlay" to "AirPlay", "Blåtann" to "Blåtann", "Spotify" to "Spotify",
        "YouTube Music" to "YT Music", "Navidrome" to "Navidrome", "Plex" to "Plex", "UPnP/DLNA" to "UPnP/DLNA", "AUX" to "AUX", "USB" to "USB",
    )
    if (rom != "s1") l.removeAll { it.first == "AUX" || it.first == "USB" }
    return l
}

/** Kildene i brukerens rekkefølge, bare de som er slått på (Rediger hjemskjerm → Kilder). */
private fun sources(m: AppModel): List<Pair<String, String>> {
    val alle = homeAlleKilder(m.actRoom.type)
    return HomeLayout.resolve(m.homeSources, alle.map { it.first }).filter { it.visible }
        .mapNotNull { k -> alle.firstOrNull { a -> a.first == k.id } }
}

@Composable
private fun SourcesShelf(m: AppModel, onEdit: () -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Row(Modifier.fillMaxWidth()) {
            T("Kilder", sora(17f, W.Semibold), Modifier.alignByBaseline())
            Spacer(Modifier.weight(1f))
            T("Rediger", sora(13f, W.Regular, HomeV4.muted), Modifier.alignByBaseline().press(label = "Rediger kilder", onClick = onEdit))
        }
        EdgeScroll(14.dp) {
            for ((name, short) in sources(m)) key(name) {
                Column(
                    Modifier.width(68.dp).press { m.openSource(name) },
                    horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(7.dp),
                ) {
                    HomeSourceIcon(name, 68.dp)
                    T(short, sora(11f, W.Regular, HomeV4.ink2), Modifier.wrapContentWidth(unbounded = true), maxLines = 1)
                }
            }
        }
    }
}

// MARK: Radiofavoritter (112 × 112)

/** Farge på kanalnavnet (V4Fav): NRK P1 #7fa8ff, P2 #e86fa8, P3 #f5d53a, ellers gull. */
private fun favColor(name: String): Color = when (name) {
    "NRK P1", "NRK P1+" -> hex(0x7fa8ff)
    "NRK P2" -> hex(0xe86fa8)
    "NRK P3" -> hex(0xf5d53a)
    else -> HomeV4.gold
}

@Composable
private fun FavShelf(m: AppModel) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        T("Radiofavoritter ›", sora(17f, W.Semibold), Modifier.press { m.openSource("Radio") })
        EdgeScroll(12.dp) {
            m.radio.forEachIndexed { i, st ->
                val on = m.input == 3 && m.stIdx == i && m.rTmp == null
                Column(
                    Modifier.size(112.dp).clip(RoundedCornerShape(16.dp)).background(HomeV4.card2)
                        .skBorder(if (on) HomeV4.goldDark else HomeV4.line, 16.dp)
                        .press { m.playStation(i, open = false) }.padding(10.dp),
                ) {
                    T("${i + 1}", mono(9f, HomeV4.muted))
                    Spacer(Modifier.weight(1f))
                    FavName(st.name, 92.dp)
                }
            }
        }
    }
}

/** «NRK P1»: første ord 20/700 (−0.02em), resten 20/400 i kanalfargen. Krymper ned til 55 % (minimumScaleFactor). */
@Composable
private fun FavName(name: String, avail: Dp) {
    val parts = name.split(" ", limit = 2)
    val a = parts[0]
    val b = if (parts.size > 1) parts[1] else ""
    val tm = rememberTextMeasurer()
    val d = LocalDensity.current
    val sa = sora(20f, W.Semibold).copy(letterSpacing = (-0.02f).em)
    val sb = sora(20f, W.Regular, favColor(name))
    val k = remember(name) {
        val gap = with(d) { 4.dp.toPx() }
        val w = tm.measure(a, sa, maxLines = 1).size.width.toFloat() +
            (if (b.isEmpty()) 0f else gap + tm.measure(b, sb, maxLines = 1).size.width.toFloat())
        val room = with(d) { avail.toPx() }
        (room / w.coerceAtLeast(1f)).coerceIn(0.55f, 1f)
    }
    Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
        T(a, sa.copy(fontSize = (20f * k).sp), Modifier.alignByBaseline(), maxLines = 1)
        if (b.isNotEmpty()) T(b, sb.copy(fontSize = (20f * k).sp), Modifier.alignByBaseline(), maxLines = 1)
    }
}

// MARK: Dine spillelister

private fun playlists(m: AppModel): List<SourcePlaylist> =
    listOf("ytm", "nd", "plex").flatMap { lib -> SourceLib.playlists(m, lib).filter { it.coll?.playlist ?: true }.take(6) }

@Composable
private fun PlaylistShelf(m: AppModel) {
    val pls = playlists(m)
    if (pls.isEmpty()) return
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        HomeShelfHeader("Dine spillelister", kicker = "FRA MUSIKKTJENESTENE") { m.openLib(pls[0].lib) }
        EdgeScroll(12.dp) {
            for (p in pls) key(p.id) {
                Column(Modifier.width(148.dp).press { m.openSourcePlaylist(p) }, verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    HomeMosaic(p.keys, 148.dp, 14.dp)
                    T(p.name, sora(14f, W.Semibold), maxLines = 1)
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        HomeSourceIcon(p.src, 15.dp)
                        T(p.src, sora(12f, W.Regular, HomeV4.muted), maxLines = 1)
                    }
                }
            }
        }
    }
}

// MARK: Hyller fra bibliotekene

private data class HomeShelfTile(val id: String, val t: String, val s: String, val key: String, val now: Boolean, val play: () -> Unit)
private data class HomeShelfData(val title: String, val kicker: String, val icon: String, val w: Dp, val tiles: List<HomeShelfTile>, val open: () -> Unit)

private fun shelves(m: AppModel): List<HomeShelfData> {
    val out = ArrayList<HomeShelfData>()
    for (lib in listOf("ytm", "nd", "plex")) {
        val tracks: List<Track> =
            if (m.demo) (SK.lib[lib]?.pls?.firstOrNull()?.second ?: emptyList()).take(6).map { SK.lt[it % SK.lt.size] }
            else (m.hist[lib] ?: emptyList()).map { it.track }.take(8)
        if (tracks.isEmpty()) continue
        val tiles = tracks.mapIndexed { i, t ->
            HomeShelfTile("$lib-$i-${t.t}", t.t, t.artist, t.album, m.libTrack?.t == t.t && m.playing) {
                m.lib = lib; m.playLib(tracks, i, keepOpen = true)
            }
        }
        val title = when (lib) { "ytm" -> "Til deg"; "nd" -> "Nytt i biblioteket"; else -> "Fra Plex" }
        val name = HomeLibNames[lib] ?: lib
        out.add(HomeShelfData(title, name.uppercase(), name, 148.dp, tiles) { m.openLib(lib) })
    }
    if (m.radio.isNotEmpty()) {
        val tiles = m.radio.take(6).mapIndexed { i, st ->
            HomeShelfTile("r$i", st.name, st.genre, st.name, m.input == 3 && m.stIdx == i && m.playing) { m.playStation(i, open = false) }
        }
        out.add(HomeShelfData("Radio akkurat nå", "RADIO", "Radio", 120.dp, tiles) { m.sub = "radio" })
    }
    return out
}

@Composable
private fun ShelfView(s: HomeShelfData) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        HomeShelfHeader(s.title, s.kicker, s.icon, s.open)
        EdgeScroll(12.dp) {
            for (t in s.tiles) key(t.id) {
                Column(Modifier.width(s.w).press(onClick = t.play), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Box {
                        HomeArt(t.key, s.w, 14.dp, if (t.now) 2.dp else 0.dp)
                        if (t.now) HomeNowBars(Modifier.align(Alignment.TopEnd).padding(9.dp))
                    }
                    T(t.t, sora(14f, W.Semibold), maxLines = 1)
                    T(t.s, sora(12f, W.Regular, HomeV4.muted), maxLines = 1)
                }
            }
        }
    }
}
