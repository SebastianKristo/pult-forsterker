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
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/** An album or playlist. Live collections load their tracks when opened or played (`src`). */
private data class Coll(val name: String, val tracks: List<Track>, val count: Int, val artist: String, val src: LibColl? = null)

private class Lib(val m: AppModel) {
    val L: SK.Library = SK.lib[m.lib] ?: SK.lib.getValue("ytm")
    /** Album-based personal libraries (Navidrome, Plex) vs. the YouTube Music mix layout. */
    val nd = m.lib == "nd" || m.lib == "plex"
    val data: LibData = m.libs[m.lib] ?: LibData()

    fun coll(c: LibColl): Coll {
        val t = data.tracks[c.id] ?: emptyList()
        return Coll(c.name, t, if (t.isEmpty()) c.count else t.size, c.artist, c)
    }

    val pls: List<Coll> =
        if (!m.demo) data.playlists.map { coll(it) }
        else L.pls.map { p -> val t = p.second.map { SK.lt[it] }; Coll(p.first, t, t.size, t.firstOrNull()?.artist ?: "") }

    val albums: List<Coll> = if (!m.demo) data.albums.map { coll(it) } else {
        val out = ArrayList<Coll>()
        for (k in L.pls.flatMap { it.second }) {
            val a = SK.lt[k].album
            if (out.none { it.name == a }) { val t = SK.lt.filter { it.album == a }; out.add(Coll(a, t, t.size, t.firstOrNull()?.artist ?: "")) }
        }
        out
    }

    val hist: List<AppModel.HistEntry> = m.hist[m.lib] ?: m.defaultHist(m.lib)
    val cur: Track? = m.lq?.let { if (m.svc == m.lib && m.li < it.size) it[m.li] else null }
    val plSrc: List<Coll> = if (m.libTab == 0 && nd) albums else pls
    val open: Coll? = m.libPl?.let { plSrc.getOrNull(it) }
}

/** 14 YouTube Music / 15 Navidrome / Plex: search, tabs, featured mix, shelves, playlists and history. */
@Composable
fun LibraryView(m: AppModel) {
    val x = Lib(m)
    val scope = rememberCoroutineScope()
    /** Plays a collection, loading its tracks first when needed. */
    val play: (Coll, Boolean, Boolean) -> Unit = { c, shuffle, queue ->
        val go: (List<Track>) -> Unit = { t ->
            if (t.isEmpty()) Haptics.warning()
            else if (queue) m.addQueue(t)
            else { m.playLib(if (shuffle) t.shuffled() else t, 0); if (shuffle) m.shuffle = true }
        }
        val src = c.src
        if (c.tracks.isNotEmpty() || src == null) go(c.tracks)
        else { val lib = m.lib; scope.launch { go(m.collTracks(lib, src)) } }
    }

    SKBackButton(if (m.libPl != null) x.L.tabs[m.libTab] else "Hjem", Modifier.offset(y = (-6).dp)) {
        if (m.libPl != null) m.libPl = null else m.sub = ""
    }
    SKField("Søk etter sang, artist eller album", m.lq2, { m.lq2 = it }, height = 44.dp, size = 15f)

    val q = m.lq2.trim().lowercase()
    val state = x.data.state
    when {
        q.isNotEmpty() -> {
            val res = if (m.demo) SK.lt.filter { (it.t + " " + it.artist + " " + it.album).lowercase().contains(q) } else (m.libRes ?: emptyList())
            if (res.isEmpty()) T(if (m.live && m.libRes == null) "Søker …" else "Ingen treff", sora(13f, W.Regular, C.muted))
            TrackList(m, x, res, null)
            LaunchedEffect(m.lib + "/" + q) {
                if (!m.live) return@LaunchedEffect
                m.libRes = null
                delay(400)
                m.libRes = m.searchLib(m.lib, q)
            }
        }
        m.live && state != "ok" -> {
            // not set up / not reachable / YouTube Music without backend: no sample data
            T(if (state == "busy" || state.isEmpty()) "Henter biblioteket …" else state, sora(13f, W.Regular, C.muted, 1.45f))
            LaunchedEffect(m.lib) { m.loadLib(m.lib) }
            if (state != "busy" && state.isNotEmpty() && m.lib != "ytm") SKLinkButton("Prøv igjen") { scope.launch { m.loadLib(m.lib, true) } }
        }
        x.open != null -> {
            val open = x.open!!
            PlaylistHeader(open, play)
            LaunchedEffect((open.src?.id ?: open.name) + m.lib) {
                val src = open.src
                if (src != null && open.tracks.isEmpty()) m.collTracks(m.lib, src)
            }
            TrackList(m, x, open.tracks, null)
        }
        else -> {
            SKSegmented(x.L.tabs, m.libTab) { i -> m.libTab = i; m.libPl = null }
            when (m.libTab) {
                0 -> Discover(m, x, play)
                1 -> PlaylistRows(m, x)
                else -> History(m, x)
            }
        }
    }
}

// MARK: Rows

@Composable
private fun TrackList(m: AppModel, x: Lib, list: List<Track>, meta: List<String>?, artistOnly: Boolean = false) {
    if (list.isEmpty()) return
    SKCard {
        list.forEachIndexed { i, t ->
            Row(
                Modifier.fillMaxWidth().heightIn(min = 58.dp).topLine(if (i > 0) C.line else Color.Transparent).press { m.playLib(list, i) }.padding(horizontal = 12.dp),
                verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                ArtFill(t.album, Modifier.size(42.dp).clip(RoundedCornerShape(6.dp)))
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    T(t.t, sora(14f, W.Regular, if (x.cur?.t == t.t) C.accent2 else C.ink), maxLines = 1)
                    T(if (artistOnly) t.artist else t.artist + " · " + t.album, sora(12f, W.Regular, C.muted), maxLines = 1)
                }
                T(meta?.getOrNull(i) ?: fmt(t.dur), mono(10f), maxLines = 1)
            }
        }
    }
}

@Composable
private fun PlaylistHeader(p: Coll, play: (Coll, Boolean, Boolean) -> Unit) {
    val a = art(p.name)
    val total = p.tracks.sumOf { it.dur }
    Row(verticalAlignment = Alignment.Bottom, horizontalArrangement = Arrangement.spacedBy(14.dp)) {
        Box(Modifier.size(120.dp).clip(RoundedCornerShape(12.dp)), contentAlignment = Alignment.BottomStart) {
            ArtFill(a)
            T(p.name, sora(15f, W.Semibold, a.ink, 1.05f), Modifier.padding(10.dp))
        }
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Column(verticalArrangement = Arrangement.spacedBy(3.dp)) {
                T(p.name, sora(19f, W.Semibold, lineHeight = 1.15f))
                T("${p.count} låter · ${total / 60} min", mono(10f))
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                SKPill("Spill", primary = true) { play(p, false, false) }
                SKPill("Tilfeldig", hPad = 14.dp) { play(p, true, false) }
            }
        }
    }
}

@Composable
private fun PlaylistRows(m: AppModel, x: Lib) {
    SKCard {
        x.pls.forEachIndexed { i, p ->
            Row(
                Modifier.fillMaxWidth().heightIn(min = 68.dp).topLine(if (i > 0) C.line else Color.Transparent).press { m.libPl = i }.padding(horizontal = 12.dp),
                verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                ArtFill(p.name, Modifier.size(52.dp).clip(RoundedCornerShape(8.dp)))
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    T(p.name, sora(15f))
                    T("${p.count} låter", sora(12f, W.Regular, C.muted))
                }
                SKIcon(Icons.chevronRight, 16.dp, 2f, C.muted)
            }
        }
    }
}

@Composable
private fun History(m: AppModel, x: Lib) {
    val h = x.hist
    if (h.isEmpty()) T("Ingen historikk ennå", sora(13f, W.Regular, C.muted))
    else TrackList(m, x, h.map { it.track }, h.map { it.time }, artistOnly = true)
    Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
        T("Tøm historikk", sora(13f, W.Regular, C.muted), Modifier.press { m.hist = m.hist + (m.lib to emptyList()) }.padding(6.dp))
    }
}

// MARK: Discover (discVals)

private data class Tile(val name: String, val meta: String, val key: String, val label: String, val pick: () -> Unit)
private data class Shelf(val kicker: String, val title: String, val tiles: List<Tile>)

@Composable
private fun Discover(m: AppModel, x: Lib, play: (Coll, Boolean, Boolean) -> Unit) {
    val feat: List<Coll> = if (x.nd) x.albums.take(5) else x.pls.drop(1) + x.pls.take(1)
    val fi = m.libHero % maxOf(1, feat.size)
    if (fi < feat.size) HeroCard(m, x, feat[fi], fi, feat.size, play) else T("Biblioteket er tomt", sora(13f, W.Regular, C.muted))
    if (!x.nd) EdgeScroll(8.dp) {
        SK.moods.forEachIndexed { j, n -> SKFilterChip(n, m.libMood == j) { m.libMood = if (m.libMood == j) null else j } }
    }
    for (sh in shelves(m, x)) {
        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            SKSectionHeader(sh.title, 19f, sh.kicker)
            EdgeScroll(12.dp) { for (t in sh.tiles) TileView(t) }
        }
    }
}

private fun artists(l: List<Track>): String {
    val seen = ArrayList<String>()
    for (x in l) if (!seen.contains(x.artist)) seen.add(x.artist)
    return seen.take(3).joinToString(", ")
}

@Composable
private fun HeroCard(m: AppModel, x: Lib, f: Coll, fi: Int, count: Int, play: (Coll, Boolean, Boolean) -> Unit) {
    val a = art(f.name)
    val chips = if (x.nd) listOf("${f.count} låter", "FLAC", "44,1 kHz") else listOf("Miks", "${f.count} låter", "AAC 256")
    Box(Modifier.fillMaxWidth().clip(RoundedCornerShape(16.dp)).background(C.card).skBorder(C.line, 16.dp)) {
        Box(Modifier.matchParentSize().background(a.base.copy(alpha = 0.5f)))
        Box(Modifier.matchParentSize().background(Brush.verticalGradient(listOf(C.bg.copy(alpha = 0.35f), C.bg.copy(alpha = 0.9f)))))
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Row(verticalAlignment = Alignment.Bottom, horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                Box(
                    Modifier.size(112.dp).shadow(15.dp, RoundedCornerShape(10.dp)).clip(RoundedCornerShape(10.dp))
                        .press { m.libPl = if (x.nd) fi else (fi + 1) % x.pls.size },
                    contentAlignment = Alignment.BottomStart,
                ) {
                    ArtFill(a)
                    T(f.name, sora(13f, W.Semibold, a.ink, 1.05f), Modifier.padding(10.dp))
                }
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    T(if (x.nd) "NYLIG LAGT TIL" else "UTVALGT MIKS", mono(10f, C.accent2, 0.12f))
                    T(f.name, sora(21f, W.Semibold, lineHeight = 1.1f))
                    T(if (x.nd) f.artist else artists(f.tracks), sora(12f, W.Regular, C.ink2), maxLines = 1)
                    Flow(5.dp) {
                        for (c in chips) Box(Modifier.height(20.dp).clip(RoundedCornerShape(5.dp)).background(Color.White.copy(alpha = 0.09f)).padding(horizontal = 7.dp), contentAlignment = Alignment.Center) {
                            T(c, mono(9f, C.ink))
                        }
                    }
                }
            }
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                SKPill("Spill", primary = true, icon = Icons.play) { play(f, false, false) }
                SKPill("Legg i kø", hPad = 14.dp, border = C.off, bg = C.bg.copy(alpha = 0.4f)) { play(f, false, true) }
                Spacer(Modifier.weight(1f))
                Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    for (j in 0 until count) Box(Modifier.size(if (j == fi) 18.dp else 6.dp, 6.dp).clip(CircleShape).background(if (j == fi) C.accent else C.off).press { m.libHero = j })
                }
            }
        }
    }
}

@Composable
private fun TileView(t: Tile) {
    val a = art(t.key)
    Column(Modifier.width(136.dp).press(onClick = t.pick), verticalArrangement = Arrangement.spacedBy(5.dp)) {
        Box(Modifier.size(136.dp).clip(RoundedCornerShape(10.dp))) {
            ArtFill(a)
            T(t.label, sora(14f, W.Semibold, a.ink, 1.05f), Modifier.align(Alignment.BottomStart).padding(start = 10.dp, bottom = 10.dp, end = 44.dp))
            Box(Modifier.align(Alignment.BottomEnd).padding(8.dp).size(30.dp).clip(CircleShape).background(C.bg.copy(alpha = 0.72f)), contentAlignment = Alignment.Center) {
                SKIcon(Icons.play, 14.dp, color = C.ink, fill = true)
            }
        }
        T(t.name, sora(13f), maxLines = 1)
        T(t.meta, sora(11f, W.Regular, C.muted), maxLines = 1)
    }
}

private fun shelves(m: AppModel, x: Lib): List<Shelf> {
    val lt = SK.lt; val pls = x.pls; val albums = x.albums
    val mi = m.libMood; val mm = mi?.let { it + 1 } ?: 0
    fun <T> rot(a: List<T>): List<T> = if (a.isEmpty()) a else a.drop(mm % a.size) + a.take(mm % a.size)
    fun tr(list: List<Track>) = list.mapIndexed { i, t -> Tile(t.t, t.artist, t.album, "") { m.playLib(list, i) } }
    val plT: (Coll) -> Tile = { p ->
        val idx = pls.indexOfFirst { it.name == p.name }.coerceAtLeast(0)
        Tile(p.name, "${p.count} låter · " + artists(p.tracks), p.name, p.name) { m.libPl = idx }
    }
    val alT: (Coll) -> Tile = { al ->
        val idx = albums.indexOfFirst { it.name == al.name && it.src?.id == al.src?.id }.coerceAtLeast(0)
        Tile(al.name, al.artist, al.name, "") { m.libTab = 0; m.libPl = idx }
    }
    if (x.nd && m.live) {
        val d = x.data
        return listOf(
            Shelf("", "Nylig lagt til", d.newest.map { x.coll(it) }.map(alT)),
            Shelf("", "Oppdag", d.other.map { x.coll(it) }.map(alT)),
            Shelf("FRA BIBLIOTEKET", "Mest spilt", d.frequent.map { x.coll(it) }.map(alT)),
        ).filter { it.tiles.isNotEmpty() }
    }
    if (x.nd) return listOf(
        Shelf("", "Nylig lagt til", albums.map(alT)),
        Shelf("", "Oppdag", albums.reversed().map(alT)),
        Shelf("FRA BIBLIOTEKET", "Mest spilt", tr(lt.subList(4, 12))),
    )
    val again = ArrayList<Track>()
    for (t in x.hist.map { it.track } + lt) if (again.none { it.t == t.t }) again.add(t)
    val forgotten = rot(lt.reversed()).take(8)
    return listOf(
        Shelf("SEBASTIAN", "Hør på nytt", tr(again.take(8))),
        Shelf("", if (mi == null) "Mikser for deg" else "Mikser · " + SK.moods[mi], rot(pls).map(plT)),
        Shelf("", "Glemte favoritter", tr(forgotten)),
    )
}

