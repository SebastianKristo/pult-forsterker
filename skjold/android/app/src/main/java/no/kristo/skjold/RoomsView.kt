package no.kristo.skjold

import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.compose.ui.window.Popup
import androidx.compose.ui.window.PopupProperties
import kotlin.math.roundToInt

/*
 * Rom (v4), som V4Rooms.swift på iOS: ett kort per rom (gruppen med det aktive rommet først), med omslag, hva som
 * spiller, spill/pause og volum. Sortering og «Fest rom» ligger bak knappene ved tittelen (RoomsHeaderButtons).
 */

private object R4 {
    const val sort = "M4 7h16M7 12h10M10 17h4"
    const val pin = "M12 17v5M8 3h8l-1 6 3 3H6l3-3z"
    const val up = "M6 15l6-6 6 6"
    const val vol = "M4 9v6h4l5 4V5L8 9zM16 9a4 4 0 0 1 0 6"
    val sheet = hex(0x1a1a1c)
    val row = hex(0x202022)
    val goldDark = hex(0xd9a441)
    val sorts = listOf("Spiller nå først", "Mest brukt", "Alfabetisk")
}

private data class RoomCardData(
    val id: String, val name: String, val types: List<String>, val t: String, val s: String, val src: String, val key: String,
    val playing: Boolean, val isMain: Boolean, val pinned: Boolean, val ord: Int?, val room: Room,
)

private fun cards(m: AppModel): List<RoomCardData> {
    val group = m.v4Group
    val gids = group.map { it.id }.toSet()
    val pins = m.roomPins
    val np = m.np
    val main = RoomCardData(
        m.actRoom.id, m.v4GroupName, group.map { it.type }, np.t, np.s, m.v4SrcIcon, m.playerArt.key, m.playing, true,
        group.any { it.id in pins }, group.mapNotNull { r -> pins.indexOf(r.id).takeIf { it >= 0 } }.minOrNull(), m.actRoom,
    )
    val out = mutableListOf(main)
    for (r in m.sys.rooms) {
        if (r.id in gids) continue
        val rnp = r.np
        val t = rnp?.firstOrNull() ?: "Ledig"
        val s = if ((rnp?.size ?: 0) > 1) rnp!![1] else SK.dev(r.type).n
        out += RoomCardData(
            r.id, r.name, listOf(r.type), t, s, "Radio", rnp?.firstOrNull() ?: r.name,
            rnp != null && rnp.firstOrNull() != "Frakoblet", false, r.id in pins, pins.indexOf(r.id).takeIf { it >= 0 }, r,
        )
    }
    val sort = m.roomSort
    return out.sortedWith { a, b ->
        val pa = a.ord ?: 99; val pb = b.ord ?: 99
        when {
            pa != pb -> pa.compareTo(pb)
            sort == 0 && a.playing != b.playing -> if (a.playing) -1 else 1
            sort == 2 -> a.name.compareTo(b.name, ignoreCase = true)
            else -> 0
        }
    }
}

@Composable
fun RoomsView(m: AppModel) {
    val list = cards(m)
    // over 900 dp (nettbrett): to kolonner
    BoxWithConstraints(Modifier.fillMaxWidth().padding(horizontal = 0.dp)) {
        val cols = if (maxWidth >= 900.dp) 2 else 1
        Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
            list.chunked(cols).forEach { rowCards ->
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    rowCards.forEach { c -> Box(Modifier.weight(1f)) { RoomCard(m, c) } }
                    if (rowCards.size < cols) Spacer(Modifier.weight(1f))
                }
            }
        }
    }
    if (m.roomPinOpen) PinSheet(m)
}

/** Sorter- og pluss-knappene ved tittelen «Rom», med «Sorter etter»-menyen under. */
@Composable
fun RoomsHeaderButtons(m: AppModel) {
    Box {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            CircleButton(R4.sort, "Sorter", m.roomSortOpen) { m.roomSortOpen = !m.roomSortOpen }
            CircleButton(Icons.plus, "Legg til", false) { m.v4AddDevice() }
        }
        if (m.roomSortOpen) SortMenu(m)
    }
}

@Composable
private fun CircleButton(d: String, label: String, on: Boolean, act: () -> Unit) {
    Box(
        Modifier.size(44.dp).clip(CircleShape).background(if (on) C.ink.copy(alpha = 0.18f) else hex(0x28282a).copy(alpha = 0.6f))
            .skCapsuleBorder(Color.White.copy(alpha = 0.12f))
            .press(label = label) { Haptics.tap(); act() },
        contentAlignment = Alignment.Center,
    ) { SKIcon(d, 20.dp, 1.8f, C.ink) }
}

// MARK: Kort

/** Romkort: radius 24, farget fra omslaget, kant .1, omslag 52, rund spill-knapp og volum. */
@Composable
private fun RoomCard(m: AppModel, c: RoomCardData) {
    val vol = if (c.isMain) m.v4GroupVol else m.v4RoomVol(c.room)
    val a = art(c.key)
    val open: () -> Unit = {
        if (c.isMain) {
            m.full = true
        } else {
            Haptics.tick(); m.v4Activate(c.room)
        }
    }
    // trykk på omslaget: spilleren med rompanelet, der du legger flere rom i gruppen
    val openGroup: () -> Unit = {
        Haptics.tick()
        if (!c.isMain) m.v4Activate(c.room)
        PlayerUi.fm = "rooms"
        m.full = true
    }
    Box(
        Modifier.fillMaxWidth().alpha(if (c.playing) 1f else 0.78f).clip(RoundedCornerShape(24.dp))
            .cssGradient(150.0, a.stops)
            .background(Color.Black.copy(alpha = if (a.hasLogo) 0.55f else 0.32f))
            .skBorder(Color.White.copy(alpha = 0.1f), 24.dp),
    ) {
        Column(Modifier.padding(start = 16.dp, end = 16.dp, top = 14.dp, bottom = 16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            // navn (med nål når festet) og enhetsikoner
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Row(Modifier.weight(1f), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    if (c.pinned) SKIcon(R4.pin, 13.dp, 1.5f, C.accent2, fill = true)
                    T(c.name, sora(17f, W.Semibold), maxLines = 1)
                }
                Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    for (t in c.types) {
                        Box(Modifier.size(26.dp).clip(RoundedCornerShape(8.dp)).background(Color.Black.copy(alpha = 0.25f)), contentAlignment = Alignment.Center) {
                            SKIcon(SK.dev(t).icon, 16.dp, 1.4f, C.ink)
                        }
                    }
                }
            }
            // omslag, tittel og kilde, spill/pause
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                ArtFill(a, Modifier.size(52.dp).shadow(8.dp, RoundedCornerShape(12.dp)).clip(RoundedCornerShape(12.dp)).press(label = "Velg rom i gruppen med " + c.name) { openGroup() })
                Column(Modifier.weight(1f).press { open() }, verticalArrangement = Arrangement.spacedBy(3.dp)) {
                    T(c.t, sora(14f, W.Semibold), maxLines = 1)
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        SourceGlyph(c.src, 15.dp)
                        T(c.s, sora(12f, W.Regular, C.ink.copy(alpha = 0.72f)), maxLines = 1)
                    }
                }
                Box(
                    Modifier.size(40.dp).clip(CircleShape).skCapsuleBorder(C.ink.copy(alpha = 0.7f), 1.5.dp)
                        .press(label = (if (c.playing) "Pause i " else "Spill i ") + c.name) { m.v4ToggleRoom(c.room) },
                    contentAlignment = Alignment.Center,
                ) { SKIcon(if (c.playing) Icons.pause else Icons.playRound, 15.dp, color = C.ink, fill = true) }
            }
            // volum
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                SKIcon(R4.vol, 16.dp, 1.8f, C.ink.copy(alpha = 0.8f))
                SkBarSlider(vol.toDouble(), { v ->
                    val n = v.roundToInt()
                    if (c.isMain) m.v4SetGroupVol(n) else m.v4SetRoomVol(c.room.id, n)
                }, Modifier.weight(1f))
                T("$vol", mono(13f, C.ink), Modifier.width(24.dp), align = TextAlign.End)
            }
        }
    }
}

// MARK: Sorter etter

@Composable
private fun SortMenu(m: AppModel) {
    val close = { m.roomSortOpen = false }
    Popup(
        alignment = Alignment.TopEnd,
        offset = IntOffset(0, with(androidx.compose.ui.platform.LocalDensity.current) { 52.dp.roundToPx() }),
        onDismissRequest = close,
        properties = PopupProperties(focusable = true),
    ) {
        Column(
            Modifier.width(250.dp).shadow(24.dp, RoundedCornerShape(18.dp)).clip(RoundedCornerShape(18.dp)).background(SkG.menuBg)
                .skBorder(Color.White.copy(alpha = 0.1f), 18.dp).padding(8.dp),
        ) {
            T("SORTER ETTER", mono(10f, C.body, 0.12f), Modifier.padding(start = 12.dp, end = 12.dp, top = 8.dp, bottom = 6.dp))
            R4.sorts.forEachIndexed { i, n ->
                val on = m.roomSort == i
                Row(
                    Modifier.fillMaxWidth().height(44.dp).clip(RoundedCornerShape(12.dp)).background(if (on) C.ink.copy(alpha = 0.08f) else Color.Transparent)
                        .press { Haptics.tick(); m.roomSort = i; close() }.padding(horizontal = 12.dp),
                    verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    T(if (on) "✓" else "", sora(14f, W.Regular, C.accent2), Modifier.width(16.dp))
                    T(n, sora(14f))
                }
            }
            Box(Modifier.padding(horizontal = 8.dp, vertical = 6.dp).fillMaxWidth().height(1.dp).background(Color.White.copy(alpha = 0.1f)))
            Row(
                Modifier.fillMaxWidth().height(44.dp).press { close(); m.roomPinOpen = true }.padding(horizontal = 12.dp),
                verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                SKIcon(R4.pin, 16.dp, 1.8f, C.ink)
                T("Fest rom …", sora(14f))
            }
        }
    }
}

// MARK: Fest rom

/** «Fest rom»-arket: festede rom i rekkefølge (flytt opp, fjern) og de andre rommene (trykk for å feste). */
@Composable
private fun PinSheet(m: AppModel) {
    val close = { m.roomPinOpen = false }
    Dialog(onDismissRequest = close, properties = DialogProperties(usePlatformDefaultWidth = false, decorFitsSystemWindows = false)) {
        Box(Modifier.fillMaxSize().background(Color.Black.copy(alpha = 0.55f)).press(label = "Lukk") { close() }) {
            val pins = m.roomPins
            val pinned = pins.mapNotNull { id -> m.sys.rooms.firstOrNull { it.id == id } }
            val others = m.sys.rooms.filter { it.id !in pins }
            Column(
                Modifier.fillMaxSize().statusBarsPadding().padding(top = 56.dp, start = 8.dp, end = 8.dp)
                    .clip(RoundedCornerShape(topStart = 34.dp, topEnd = 34.dp)).background(R4.sheet)
                    .skBorder(Color.White.copy(alpha = 0.08f), 34.dp)
                    .pointerInput(Unit) { detectTapGestures { } }  // trykk på arket lukker det ikke
                    .verticalScroll(rememberScrollState())
                    .padding(start = 18.dp, end = 18.dp, top = 16.dp, bottom = 32.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        Modifier.size(44.dp).clip(CircleShape).background(C.ink.copy(alpha = 0.1f)).skCapsuleBorder(Color.White.copy(alpha = 0.12f))
                            .press(label = "Lukk") { close() },
                        contentAlignment = Alignment.Center,
                    ) { SKIcon(Icons.close, 18.dp, 2f, C.ink) }
                    Spacer(Modifier.weight(1f))
                    Box(
                        Modifier.height(44.dp).clip(CircleShape).background(R4.goldDark).press { close() }.padding(horizontal = 18.dp),
                        contentAlignment = Alignment.Center,
                    ) { T("Ferdig", sora(14f, W.Semibold, C.bg)) }
                }
                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    T("Fest rom", sora(28f, W.Semibold).copy(letterSpacing = (-0.02f).em))
                    T("Festede rom ligger alltid øverst i Rom-fanen, i den rekkefølgen du velger her.", sora(13f, W.Regular, C.body, lineHeight = 1.5f))
                }
                Row(verticalAlignment = Alignment.CenterVertically) {
                    SKMonoLabel("FESTET · ${pinned.size}")
                    Spacer(Modifier.weight(1f))
                    T("Velg alle", sora(13f, W.Regular, R4.goldDark), Modifier.press { Haptics.tick(); m.roomPins = m.sys.rooms.map { it.id } })
                }
                Column(Modifier.fillMaxWidth().clip(RoundedCornerShape(18.dp)).background(R4.row).skBorder(Color.White.copy(alpha = 0.08f), 18.dp)) {
                    if (pinned.isEmpty()) T("Velg rom under for å feste dem.", sora(13f, W.Regular, C.muted), Modifier.padding(16.dp))
                    pinned.forEachIndexed { i, r ->
                        Row(
                            Modifier.fillMaxWidth().heightIn(min = 56.dp).topLine(if (i > 0) Color.White.copy(alpha = 0.07f) else Color.Transparent).padding(horizontal = 14.dp),
                            verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp),
                        ) {
                            T("${i + 1}", mono(11f, C.accent2), Modifier.width(22.dp))
                            RoomIcon(r)
                            T(r.name, sora(15f), Modifier.weight(1f), maxLines = 1)
                            Box(
                                Modifier.size(28.dp).alpha(if (i > 0) 1f else 0.3f).clip(RoundedCornerShape(8.dp)).background(C.ink.copy(alpha = 0.08f))
                                    .press(enabled = i > 0, label = "Flytt opp") {
                                        Haptics.tick()
                                        val p = m.roomPins.toMutableList(); val t = p[i - 1]; p[i - 1] = p[i]; p[i] = t; m.roomPins = p
                                    },
                                contentAlignment = Alignment.Center,
                            ) { SKIcon(R4.up, 14.dp, 2f, C.ink) }
                            Box(
                                Modifier.size(26.dp).clip(CircleShape).background(R4.goldDark)
                                    .press(label = "Fjern") { Haptics.tick(); m.roomPins = m.roomPins.filter { it != r.id } },
                                contentAlignment = Alignment.Center,
                            ) { SKIcon(Icons.check, 14.dp, 3f, C.bg) }
                        }
                    }
                }
                SKMonoLabel("ANDRE ROM")
                Column(Modifier.fillMaxWidth().clip(RoundedCornerShape(18.dp)).background(R4.row).skBorder(Color.White.copy(alpha = 0.08f), 18.dp)) {
                    others.forEachIndexed { i, r ->
                        Row(
                            Modifier.fillMaxWidth().heightIn(min = 56.dp).topLine(if (i > 0) Color.White.copy(alpha = 0.07f) else Color.Transparent)
                                .press { Haptics.tick(); m.roomPins = m.roomPins + r.id }.padding(horizontal = 14.dp),
                            verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp),
                        ) {
                            RoomIcon(r)
                            T(r.name, sora(15f), Modifier.weight(1f), maxLines = 1)
                            Box(Modifier.size(26.dp).clip(CircleShape).skCapsuleBorder(C.dim, 1.5.dp))
                        }
                    }
                    if (others.isEmpty()) T("Alle rom er festet.", sora(13f, W.Regular, C.muted), Modifier.padding(16.dp))
                }
            }
        }
    }
}

@Composable
private fun RoomIcon(r: Room) {
    Box(Modifier.size(36.dp).clip(RoundedCornerShape(10.dp)).background(C.bg), contentAlignment = Alignment.Center) {
        SKIcon(SK.dev(r.type).icon, 20.dp, 1.3f, C.ink2)
    }
}
