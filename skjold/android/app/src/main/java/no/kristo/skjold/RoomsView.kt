package no.kristo.skjold

import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.unit.dp
import kotlin.math.roundToInt

/** Rom («Ditt system»): now-playing group card with group volume, room tiles (drag sideways for volume), surround and add device. */
@Composable
fun RoomsView(m: AppModel) {
    val act = m.actRoom
    val members = m.sys.groupOf(act.id)
    val gid = act.group
    val gMode = gid?.let { m.sys.modes[it] } ?: "sync"
    val surround = members.size > 1 && gMode == "surround"

    GroupCard(m, act, members, gid, gMode)

    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            SKMonoLabel("ROM")
            Spacer(Modifier.weight(1f))
            T("Dra sidelengs for volum", sora(11f, W.Regular, C.muted))
        }
        val cells: List<Room?> = m.sys.rooms + listOf(null)
        cells.chunked(2).forEach { pair ->
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                pair.forEach { r ->
                    Box(Modifier.weight(1f)) { if (r != null) RoomTile(m, r, act) else AddTile(m) }
                }
                if (pair.size == 1) Spacer(Modifier.weight(1f))
            }
        }
    }

    if (surround) SurroundCard(m, members)

    T("Samme musikk i alle rommene, synkronisert ned til millisekunder. Trykk på et rom for å styre det.", sora(11f, W.Regular, C.muted))
}

// MARK: Group / now playing

@Composable
private fun GroupCard(m: AppModel, act: Room, members: List<Room>, gid: String?, gMode: String) {
    val np = m.np
    val groupVol = if (members.isEmpty()) m.vol else (members.sumOf { if (it.id == act.id) m.vol else it.vol }.toDouble() / members.size).roundToInt()
    // v4: romkort r24 tonet i omslagsfargen (romfarger), navn 17/600 og enhetsikoner, cover 52, rund omrisset spill-knapp
    val tone = art(m.playerArt.key).base
    Box(
        Modifier.fillMaxWidth().clip(RoundedCornerShape(24.dp))
            .cssGradient(150.0, listOf(0f to mix(tone, C.bg, 0.25f), 1f to mix(tone, C.bg, 0.6f)))
            .skBorder(Color.White.copy(alpha = 0.1f), 24.dp),
    ) {
        Column(Modifier.padding(start = 16.dp, end = 16.dp, top = 14.dp, bottom = 16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                T(if (members.size > 1) m.groupName else act.name, sora(17f, W.Semibold), Modifier.weight(1f), maxLines = 1)
                Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    for (r in (if (members.isEmpty()) listOf(act) else members)) {
                        Box(Modifier.size(26.dp).clip(RoundedCornerShape(8.dp)).background(Color.Black.copy(alpha = 0.25f)), contentAlignment = Alignment.Center) {
                            SKIcon(SK.dev(r.type).icon, 16.dp, 1.4f, C.ink)
                        }
                    }
                }
            }
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                ArtFill(m.playerArt.key, Modifier.size(52.dp).shadow(8.dp, RoundedCornerShape(12.dp)).clip(RoundedCornerShape(12.dp)).press { Haptics.thump(); m.full = true })
                Column(Modifier.weight(1f).press { m.full = true }, verticalArrangement = Arrangement.spacedBy(3.dp)) {
                    T(np.t, sora(14f, W.Semibold), maxLines = 1)
                    T(np.s, sora(12f, W.Regular, C.ink.copy(alpha = 0.72f)), maxLines = 1)
                }
                Box(
                    Modifier.size(40.dp).clip(CircleShape).skBorder(C.ink.copy(alpha = 0.7f), 20.dp, 1.5.dp).press { m.togglePlay() },
                    contentAlignment = Alignment.Center,
                ) { SKIcon(if (m.playing) Icons.pause else Icons.playRound, 15.dp, color = C.ink, fill = true) }
            }
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                SKIcon("M4 9v6h4l5 4V5L8 9zM16 9a4 4 0 0 1 0 6", 16.dp, 1.8f, C.ink.copy(alpha = 0.8f))
                SkBarSlider(groupVol.toDouble(), { setGroupVolume(m, it.roundToInt()) }, Modifier.weight(1f))
                T("$groupVol", mono(13f, C.ink), Modifier.width(24.dp), align = androidx.compose.ui.text.style.TextAlign.End)
            }
            // members
            Flow(6.dp) {
                for (r in members) {
                    Row(
                        Modifier.height(28.dp).clip(CircleShape).background(Color.White.copy(alpha = 0.08f)).padding(horizontal = 10.dp),
                        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp),
                    ) {
                        SKIcon(SK.dev(r.type).icon, 14.dp, 1.6f, C.ink2)
                        T(r.name, sora(12f))
                    }
                }
            }
            if (members.size > 1 && gid != null) {
                SKSegmented(listOf("Samme musikk", "Surround"), if (gMode == "surround") 1 else 0, 34.dp, Color.Black.copy(alpha = 0.3f), null, C.selBg2, C.accent2, C.ink2) { i ->
                    Haptics.tick()
                    m.setSys(m.sys.withGroupMode(gid, if (i == 1) "surround" else "sync"))
                }
            }
            val rooms = m.sys.rooms
            val allGrouped = rooms.size > 1 && rooms.all { it.group != null && it.group == rooms[0].group }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                QuickButton("Alle rom", Icons.tabRooms, allGrouped, Modifier.weight(1f)) { m.setSys(m.sys.groupedAll()) }
                QuickButton("Bare ${act.name}", Icons.speaker, members.size == 1, Modifier.weight(1f)) {
                    m.setSys(m.sys.copy(rooms = m.sys.rooms.map { it.copy(group = null) }))
                }
            }
        }
    }
}

@Composable
private fun QuickButton(title: String, icon: String, on: Boolean, modifier: Modifier, action: () -> Unit) {
    Row(
        modifier.height(36.dp).clip(CircleShape).background(if (on) C.selBg else Color.Black.copy(alpha = 0.25f)).skCapsuleBorder(if (on) C.accent else C.line2)
            .press { if (!on) { Haptics.tick(); action() } },
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp, Alignment.CenterHorizontally),
    ) {
        SKIcon(icon, 14.dp, 1.8f, if (on) C.accent2 else C.ink)
        T(title, sora(12f, if (on) W.Semibold else W.Regular, if (on) C.accent2 else C.ink), maxLines = 1)
    }
}

/** Moves every member by the same amount, like a group volume on Sonos. Reads fresh values from the model each step. */
private fun setGroupVolume(m: AppModel, v: Int) {
    val act = m.actRoom
    var rooms = m.sys.rooms.map { if (it.id == act.id) it.copy(vol = m.vol) else it }
    val n0 = m.sys.copy(rooms = rooms)
    val members = n0.groupOf(act.id)
    if (members.isEmpty()) return
    val current = (members.sumOf { it.vol }.toDouble() / members.size).roundToInt()
    val delta = v - current
    if (delta == 0) return
    rooms = rooms.map { r ->
        if (members.any { it.id == r.id }) {
            val nv = (r.vol + delta).coerceIn(0, 100)
            if (r.id == act.id) m.setVol(nv)
            r.copy(vol = nv)
        } else r
    }
    m.setSys(n0.copy(rooms = rooms))
}

// MARK: Add device

@Composable
private fun AddTile(m: AppModel) {
    Column(
        Modifier.fillMaxWidth().height(150.dp).skBorder(hex(0x3a2e17), 18.dp, dash = listOf(5f, 4f))
            .press {
                Haptics.tap()
                if (m.stedId.isNotEmpty()) { m.openStederSettings(); return@press }
                m.mode = Mode.ONBOARD; m.welcome = false; m.ob = 0; m.tested = emptySet(); m.pw = ""; m.obUpd = 0; m.scan = false
            },
        horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(10.dp, Alignment.CenterVertically),
    ) {
        Box(Modifier.size(44.dp).clip(CircleShape).background(C.selBg2).skCapsuleBorder(C.selLine), contentAlignment = Alignment.Center) {
            SKIcon(Icons.plus, 22.dp, 2f, C.accent2)
        }
        Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(2.dp)) {
            T("Legg til enhet", sora(13f, W.Semibold))
            T("S1, Node eller Core", sora(11f, W.Regular, C.muted))
        }
    }
}

// MARK: Surround

@Composable
private fun SurroundCard(m: AppModel, members: List<Room>) {
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        SKMonoLabel("PLASSERING I SURROUND")
        SKCard(radius = 18.dp) {
            members.forEachIndexed { idx, r ->
                Column(Modifier.fillMaxWidth().topLine(if (idx > 0) C.line else Color.Transparent).padding(vertical = 12.dp, horizontal = 14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        SKIcon(SK.dev(r.type).icon, 18.dp, 1.4f, C.ink2)
                        T(r.name, sora(14f), Modifier.weight(1f))
                        T(SK.roles[r.role ?: 0], mono(10f, C.accent2))
                    }
                    Flow(5.dp) {
                        SK.roles.forEachIndexed { j, label ->
                            val on = (r.role ?: 0) == j
                            SKChip(label, height = 30.dp, hPad = 10.dp, radius = 8.dp, style = SelStyle(if (on) C.accent else C.line2, if (on) C.selBg2 else C.card, if (on) C.accent2 else C.ink2)) {
                                Haptics.tick()
                                m.setSys(m.sys.copy(rooms = m.sys.rooms.map { if (it.id == r.id) it.copy(role = j) else it }))
                            }
                        }
                    }
                }
            }
        }
        T("Tidsforsinkelse justeres automatisk ut fra plasseringen.", sora(11f, W.Regular, C.muted))
    }
}

// MARK: - Room tile

/**
 * Square-ish tile: icon, name, status; the background fills with the volume. Drag sideways to change volume,
 * tap to control the room, check mark to add/remove it from the group. A vertical drag stays a scroll: only a
 * horizontal drag past the touch slop is taken by the tile (detectHorizontalDragGestures), the rest goes to the page.
 */
@Composable
private fun RoomTile(m: AppModel, room: Room, act: Room) {
    val isA = room.id == act.id
    val inG = isA || (act.group != null && room.group == act.group)
    val vol = if (isA) m.vol else room.vol
    val np = m.np
    val status = room.np?.let { it[0] + " · " + it.getOrElse(1) { "" } } ?: if (inG) np.t else "Ledig"
    val curVol by rememberUpdatedState(vol)
    val drag = remember { floatArrayOf(0f, 0f) } // start volume, accumulated dx
    BoxWithConstraints(
        Modifier.fillMaxWidth().height(150.dp).clip(RoundedCornerShape(18.dp)).background(if (isA) C.selBg else C.card)
            .skBorder(if (isA) C.accent else C.line, 18.dp)
            .pointerInput(room.id, isA) {
                detectTapGestures {
                    if (!isA) {
                        Haptics.tick()
                        // keep each room's own volume: store the old active room's volume, load the new one
                        val old = m.actRoom
                        val rooms = m.sys.rooms.map { if (it.id == old.id) it.copy(vol = m.vol) else it }
                        m.vol = room.vol
                        m.setSys(m.sys.copy(rooms = rooms, active = room.id))
                    }
                }
            }
            .pointerInput(room.id, isA) {
                detectHorizontalDragGestures(
                    onDragStart = { drag[0] = curVol.toFloat(); drag[1] = 0f },
                    onDragEnd = {}, onDragCancel = {},
                ) { change, dx ->
                    change.consume()
                    drag[1] += dx
                    val v = (drag[0] + drag[1] / size.width * 100).roundToInt().coerceIn(0, 100)
                    val cur = curVol
                    if (v != cur) {
                        if (v == 0 || v == 100) Haptics.bump() else if (v / 5 != cur / 5) Haptics.tick()
                        setRoomVolume(m, room, v, isA)
                    }
                }
            },
    ) {
        // volume fill from the left
        Box(
            Modifier.width(maxWidth * (vol / 100f)).fillMaxHeight()
                .background(Brush.horizontalGradient(listOf(C.accent.copy(alpha = if (inG) 0.22f else 0.08f), C.accent.copy(alpha = if (inG) 0.12f else 0.04f)))),
        )
        Column(Modifier.fillMaxSize().padding(12.dp)) {
            Row(verticalAlignment = Alignment.Top) {
                Box(Modifier.size(40.dp).clip(RoundedCornerShape(11.dp)).background(Color.Black.copy(alpha = 0.25f)), contentAlignment = Alignment.Center) {
                    SKIcon(SK.dev(room.type).icon, 26.dp, 1.3f, if (isA) C.accent2 else C.ink2)
                }
                Spacer(Modifier.weight(1f))
                Box(
                    Modifier.size(40.dp).press(enabled = !isA) {
                        Haptics.tick()
                        m.setSys(m.sys.toggledInGroup(act.id, room.id))
                    },
                    contentAlignment = Alignment.TopEnd,
                ) {
                    Box(
                        Modifier.size(26.dp).clip(CircleShape).background(if (inG) C.accent else Color.Transparent).skCapsuleBorder(if (inG) C.accent else C.dim, 1.5.dp),
                        contentAlignment = Alignment.Center,
                    ) { if (inG) SKIcon(Icons.check, 14.dp, 3f, C.bg) }
                }
            }
            Spacer(Modifier.weight(1f))
            T(room.name, sora(16f, W.Semibold), maxLines = 1)
            m.hjemEnhet(room.id)?.let { HjemBadges(it, Modifier.padding(vertical = 2.dp)) }
            T(status, sora(11f, W.Regular, if (inG) C.ink2 else C.muted), maxLines = 1)
            Row(Modifier.padding(top = 6.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                SKIcon(Icons.volume, 12.dp, 2f, C.muted)
                T("$vol", mono(11f, if (vol > 0) C.ink else C.muted))
                Spacer(Modifier.weight(1f))
                T(SK.dev(room.type).n.replace("Skjold ", ""), mono(9f, C.muted, 0.08f))
            }
        }
    }
}

private fun setRoomVolume(m: AppModel, room: Room, v: Int, isA: Boolean) {
    if (isA) m.setVol(v)
    m.setSys(m.sys.copy(rooms = m.sys.rooms.map { if (it.id == room.id) it.copy(vol = v) else it }))
}
