package no.kristo.skjold

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp

/** 16 Radio + 17 Radio, søk (radioDisc() in the design). */
private val genres = listOf("Pop og hits" to "pop|hit|mp3|ung", "Nyheter og prat" to "nyhet|samfunn|kultur|prat|distrikt|sport|debatt",
    "Klassisk" to "klassisk|opera", "Jazz" to "jazz", "Rock" to "rock|metal", "Lokal" to "lokal|distrikt|region")

private val gs: List<Pair<String, List<Station>>> = genres.map { (n, re) ->
    val r = Regex(re, RegexOption.IGNORE_CASE)
    n to SK.catalog.filter { r.containsMatchIn(it.genre + " " + it.name) }
}.filter { it.second.isNotEmpty() }

@Composable
fun RadioView(m: AppModel) {
    val q = m.q.trim().lowercase()
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        SKField("Søk etter kanal, by eller sjanger", m.q, { m.setQ(it) }, height = 44.dp, size = 15f)
        Row(
            Modifier.height(44.dp).clip(RoundedCornerShape(12.dp)).background(C.card2).skBorder(C.line2, 12.dp).press { m.goRadioSettings() }.padding(horizontal = 14.dp),
            verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            SKIcon(Icons.favList, 15.dp, 1.8f, C.ink)
            T("Favoritter", sora(13f))
        }
    }
    if (q.isEmpty()) Discover(m) else Search(m, q)
}

// MARK: Search

@Composable
private fun Search(m: AppModel, q: String) {
    val loc = SK.catalog.filter { (it.name + " " + it.genre).lowercase().contains(q) }
    val onl = (m.rRes ?: emptyList()).filter { s -> loc.none { it.name.lowercase() == s.name.lowercase() } }.map { s ->
        val g = listOf(s.genre, s.country, if (s.br > 0) "${s.br} kbps" else "").filter { it.isNotEmpty() }.joinToString(" · ")
        Station(s.name, g.ifEmpty { "Nettradio" }, s.url)
    }
    if (loc.isNotEmpty()) { SKMonoLabel("NORSKE KANALER"); StationList(m, loc) }
    if (m.rBusy) T("Søker i Radio Browser …", sora(12f, W.Regular, C.muted))
    if (onl.isNotEmpty()) { SKMonoLabel("FRA HELE VERDEN · RADIO BROWSER"); StationList(m, onl) }
    if (!m.rBusy && loc.isEmpty() && onl.isEmpty() && q.length >= 3) {
        T("Ingen kanaler funnet. Du kan legge til en strømadresse under Administrer favoritter.", sora(13f, W.Regular, C.muted))
    }
}

private fun abbr(n: String, len: Int) = (if (n.startsWith("NRK ")) n.drop(4) else n).take(len)

@Composable
private fun StationList(m: AppModel, list: List<Station>) {
    SKCard {
        list.forEachIndexed { i, st ->
            val a = art(st.name); val f = m.favIndex(st.name) != null
            Row(
                Modifier.fillMaxWidth().heightIn(min = 54.dp).topLine(if (i > 0) C.line else Color.Transparent).padding(horizontal = 12.dp),
                verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                Box(Modifier.size(36.dp).clip(RoundedCornerShape(8.dp)).press { m.playRadio(st) }, contentAlignment = Alignment.Center) {
                    ArtFill(a)
                    T(abbr(st.name, 5), sora(9f, W.Semibold, a.ink), align = TextAlign.Center)
                }
                Column(Modifier.weight(1f).press { m.playRadio(st) }.padding(vertical = 6.dp), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    T(st.name, sora(14f), maxLines = 1)
                    T(st.genre, sora(11f, W.Regular, C.muted), maxLines = 1)
                }
                Box(Modifier.size(36.dp).clip(RoundedCornerShape(8.dp)).background(C.card2).skBorder(C.line2, 8.dp).press { m.toggleFav(st) }, contentAlignment = Alignment.Center) {
                    T(if (f) "★" else "☆", sora(16f, W.Regular, if (f) C.accent2 else C.muted))
                }
            }
        }
    }
}

// MARK: Discover

@Composable
private fun Discover(m: AppModel) {
    val gi = m.rGenre?.takeIf { it < gs.size }
    Hero(m)
    EdgeScroll(8.dp) {
        SKFilterChip("Alle", gi == null, 15.dp) { m.rGenre = null }
        gs.forEachIndexed { i, g -> SKFilterChip(g.first, gi == i, 15.dp) { m.rGenre = i } }
    }
    val shelves: List<Triple<String, String, List<Station>>> = if (gi == null)
        listOf(Triple("${m.radio.size}" + if (m.radio.size == 1) " KANAL" else " KANALER", "Dine favoritter", m.radio),
            Triple("", "Populære i Norge", SK.catalog.take(14))) + gs.take(2).map { Triple("SJANGER", it.first, it.second) }
    else listOf(Triple("SJANGER", gs[gi].first, gs[gi].second))
    for (sh in shelves.filter { it.third.isNotEmpty() }) {
        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            SKSectionHeader(sh.second, 19f, sh.first)
            EdgeScroll(12.dp) { for (st in sh.third) StationTile(m, st) }
        }
    }
}

@Composable
private fun StationTile(m: AppModel, st: Station) {
    val on = m.curRadioName == st.name
    Column(Modifier.width(112.dp).press { m.playRadio(st) }, verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Box(Modifier.size(112.dp).clip(RoundedCornerShape(12.dp)).skBorder(C.line, 12.dp)) {
            ArtFill(st.name)
            if (on) Box(Modifier.padding(8.dp).height(18.dp).clip(RoundedCornerShape(4.dp)).background(C.live).padding(horizontal = 6.dp), contentAlignment = Alignment.Center) {
                T("DIREKTE", mono(9f, Color.White, 0.08f))
            }
        }
        T(st.name, sora(13f), maxLines = 1)
        T(st.genre, sora(11f, W.Regular, C.muted), maxLines = 1)
    }
}

@Composable
private fun Hero(m: AppModel) {
    val cur = m.curRadioName
    val st: Station = (if (cur.isEmpty()) null else (m.radio.firstOrNull { it.name == cur } ?: SK.catalog.firstOrNull { it.name == cur } ?: m.rTmp?.takeIf { it.name == cur }))
        ?: m.radio.firstOrNull() ?: SK.catalog[0]
    val fav = m.favIndex(st.name) != null; val live = cur == st.name
    val npH = SK.nowPlaying(st.name)
    val now = npH.first + if (npH.second.isNotEmpty() && npH.second != st.name) " · " + npH.second else ""
    Box(Modifier.fillMaxWidth().clip(RoundedCornerShape(16.dp)).background(C.card).skBorder(C.line, 16.dp)) {
        Box(Modifier.matchParentSize().background(art(st.name).base.copy(alpha = 0.5f)))
        Box(Modifier.matchParentSize().background(Brush.verticalGradient(listOf(C.bg.copy(alpha = 0.35f), C.bg.copy(alpha = 0.92f)))))
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                ArtFill(st.name, Modifier.size(96.dp).shadow(22.dp, RoundedCornerShape(12.dp)).clip(RoundedCornerShape(12.dp)).press { m.playRadio(st) })
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Dot(if (live) C.live else C.off, 7.dp)
                        T(if (live) "SPILLER NÅ" else "FRA FAVORITTENE", mono(10f, C.accent2, 0.14f))
                    }
                    T(st.name, sora(22f, W.Semibold, lineHeight = 1.05f))
                    T(st.genre, sora(12f, W.Regular, C.ink2))
                    T(now, sora(12f, W.Regular, C.muted), maxLines = 1)
                }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                SKPill(if (live) "Spiller" else "Spill", primary = true, icon = Icons.play, hPad = 18.dp) { m.playRadio(st) }
                SKPill(if (fav) "★ I favorittene" else "☆ Legg til favoritter", border = C.off, bg = C.bg.copy(alpha = 0.4f), fg = if (fav) C.accent2 else C.ink) { m.toggleFav(st) }
            }
        }
    }
}
