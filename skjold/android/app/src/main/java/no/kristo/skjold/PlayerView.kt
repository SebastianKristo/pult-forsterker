package no.kristo.skjold

import androidx.compose.animation.core.Animatable
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.Orientation
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.gestures.draggable
import androidx.compose.foundation.gestures.rememberDraggableState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.systemBars
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlin.math.abs
import kotlin.math.roundToInt
import kotlin.math.sin

/** 10 Fullskjermspiller + 11 Kø. Opened from the mini player, dragged down to close (SKSheet). */
@Composable
fun FullPlayerView(m: AppModel) {
    val pa = m.playerArt
    val scope = rememberCoroutineScope()
    val drag = remember { Animatable(0f) }
    val closeAt = with(LocalDensity.current) { 90.dp.toPx() }
    Box(
        Modifier.fillMaxSize()
            .offset { IntOffset(0, drag.value.roundToInt()) }
            .draggable(
                rememberDraggableState { d ->
                    val new = maxOf(0f, drag.value + d)
                    if ((drag.value <= closeAt) != (new <= closeAt)) Haptics.bump()
                    scope.launch { drag.snapTo(new) }
                },
                Orientation.Vertical,
                onDragStopped = { v ->
                    if (drag.value > closeAt || (drag.value > 20 && v > 1800f)) { m.full = false; delay(350); drag.snapTo(0f) }
                    else drag.animateTo(0f)
                },
            ),
    ) {
        // background runs all the way behind the status bar and the navigation bar
        ArtFill(pa.key)
        Box(Modifier.fillMaxSize().background(Brush.verticalGradient(0f to C.bg.copy(alpha = 0.15f), 0.55f to C.bg.copy(alpha = 0.55f), 1f to C.bg.copy(alpha = 0.85f))))
        Column(Modifier.fillMaxSize().windowInsetsPadding(WindowInsets.systemBars)) {
            TopBar(m)
            Column(Modifier.weight(1f).padding(start = 18.dp, end = 18.dp, top = 6.dp, bottom = 12.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                PlayerContent(m, pa)
            }
        }
    }
}

/** Top bar (YouTube Music style): close ⌄ · Låt/Kø switch · speakers · more ⋮ */
@Composable
private fun TopBar(m: AppModel) {
    Box(Modifier.fillMaxWidth().padding(top = 8.dp, bottom = 4.dp), contentAlignment = Alignment.Center) {
        Row(Modifier.clip(CircleShape).background(Color.Black.copy(alpha = 0.3f)).padding(3.dp), horizontalArrangement = Arrangement.spacedBy(2.dp)) {
            for ((q, label) in listOf(false to "Låt", true to "Kø")) {
                val on = m.queueOpen == q
                Box(
                    Modifier.height(32.dp).clip(CircleShape).background(if (on) C.ink.copy(alpha = 0.16f) else Color.Transparent)
                        .press { if (!on) Haptics.tick(); m.queueOpen = q }.padding(horizontal = 18.dp),
                    contentAlignment = Alignment.Center,
                ) { T(label, sora(14f, W.Semibold, if (on) C.ink else C.ink.copy(alpha = 0.5f))) }
            }
        }
        Row(Modifier.fillMaxWidth().padding(horizontal = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            TopButton(Icons.chevronDown, 26.dp, 2.2f) { m.full = false }
            Spacer(Modifier.weight(1f))
            TopButton(Icons.speaker, 22.dp, 1.8f) { m.full = false; m.tab = 2 }
            TopButton(Icons.moreVertical, 22.dp, fill = true, on = m.srcOpen) { m.srcOpen = !m.srcOpen }
        }
    }
}

@Composable
private fun TopButton(d: String, size: androidx.compose.ui.unit.Dp, stroke: Float = 2f, fill: Boolean = false, on: Boolean = false, action: () -> Unit) {
    Box(Modifier.size(44.dp).clip(CircleShape).background(if (on) C.ink.copy(alpha = 0.16f) else Color.Transparent).press(onClick = action), contentAlignment = Alignment.Center) {
        SKIcon(d, size, stroke, C.ink, fill)
    }
}

@Composable
private fun androidx.compose.foundation.layout.ColumnScope.PlayerContent(m: AppModel, pa: AppModel.PlayerArt) {
    // Flexible area: the cover (or the queue) shrinks so everything fits without scrolling.
    Box(Modifier.weight(1f).fillMaxWidth(), contentAlignment = Alignment.Center) {
        if (!m.queueOpen) Cover(m, pa) else Queue(m)
    }
    if (m.srcOpen) Flow(6.dp) {
        for ((label, i) in m.inputs) SKChip(label, on = m.input == i && m.svc == null) { m.pickInput(i) }
    }
    if (m.input == 3) EdgeScroll(6.dp, 18.dp) {
        m.radio.forEachIndexed { i, st ->
            SKChip(st.name, on = m.stIdx == i, hPad = 11.dp, vPad = 7.dp, leadingNumber = "${i + 1}") {
                m.station = i; m.rTmp = null
                m.post(mapOf("type" to "src", "v" to i))
            }
        }
    }
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        T(m.np.t, sora(24f, W.Semibold), maxLines = 1)
        T(m.np.s, sora(15f, W.Regular, C.ink.copy(alpha = 0.65f)), maxLines = 1)
    }
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(Modifier.press { m.srcOpen = !m.srcOpen }, verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            T(m.srcName, sora(15f, W.Semibold))
            SKIcon(Icons.chevronDown, 12.dp, 2.4f, C.ink.copy(alpha = 0.6f))
        }
        Spacer(Modifier.weight(1f))
        T(m.quality, mono(10f, C.ink.copy(alpha = 0.7f), 0.06f))
    }
    if (m.hasProgress) Progress(m)
    Controls(m)
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        SKIcon(Icons.volume, 18.dp, 2f, C.ink)
        SKSlider(m.vol.toDouble(), { m.setVol(it.toInt()) }, tint = C.ink, modifier = Modifier.weight(1f))
        T("${m.vol}", mono(12f, C.ink.copy(alpha = 0.7f)), Modifier.width(22.dp), align = androidx.compose.ui.text.style.TextAlign.End)
    }
    Row(Modifier.fillMaxWidth().padding(top = 2.dp), verticalAlignment = Alignment.CenterVertically) {
        CircleButton(Icons.queue, m.queueOpen) { m.queueOpen = !m.queueOpen }
        Spacer(Modifier.weight(1f))
        Row(
            Modifier.height(48.dp).clip(CircleShape).background(Color.Black.copy(alpha = 0.18f)).skCapsuleBorder(C.ink.copy(alpha = 0.18f))
                .press { m.full = false; m.tab = 2 }.padding(horizontal = 18.dp),
            verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            SKIcon(Icons.speaker, 18.dp, 1.8f, C.ink)
            T(m.groupName, sora(14f, W.Semibold), maxLines = 1)
        }
        Spacer(Modifier.weight(1f))
        CircleButton(Icons.more, m.srcOpen, fill = true) { m.srcOpen = !m.srcOpen }
    }
}

// MARK: Cover

@Composable
private fun Cover(m: AppModel, pa: AppModel.PlayerArt) {
    val a = art(pa.key)
    Box(Modifier.fillMaxHeight().aspectRatio(1f, matchHeightConstraintsFirst = true).shadow(20.dp, RoundedCornerShape(14.dp)).clip(RoundedCornerShape(14.dp))) {
        ArtFill(a)
        Column(Modifier.fillMaxSize().padding(20.dp)) {
            Row(verticalAlignment = Alignment.Top, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                T(pa.kicker, mono(10f, a.ink.copy(alpha = a.ink.alpha * 0.8f), 0.12f), Modifier.weight(1f), maxLines = 1)
                if (pa.live) Box(Modifier.clip(RoundedCornerShape(4.dp)).background(C.live).padding(horizontal = 6.dp, vertical = 3.dp)) {
                    T("DIREKTE", mono(9f, Color.White, 0.1f))
                }
            }
            Spacer(Modifier.weight(1f))
            T(pa.big, sora(pa.size, W.Semibold, a.ink, 1.05f))
            Spacer(Modifier.weight(1f))
            Viz(m, a.ink)
        }
    }
}

@Composable
private fun Viz(m: AppModel, ink: Color) {
    var tick by remember { mutableLongStateOf(0L) }
    LaunchedEffect(Unit) { while (true) { delay(140); tick++ } }
    val t = tick.toDouble()
    Row(Modifier.height(22.dp), verticalAlignment = Alignment.Bottom, horizontalArrangement = Arrangement.spacedBy(3.dp)) {
        for (i in 0 until 12) {
            val e = m.prof.eq[minOf(4, (i / 2.4).toInt())].toDouble()
            val a = if (m.playing) 0.35 + 0.55 * abs(sin(t * 0.45 + i * 0.9) * sin(t * 0.21 + i)) else 0.06
            val h = (a * 100 + e * 2.5).coerceIn(4.0, 100.0)
            Box(Modifier.width(4.dp).height((22 * h / 100).dp).clip(RoundedCornerShape(2.dp)).background(ink).alpha(if (m.playing) 1f else 0.35f))
        }
    }
}

// MARK: Queue

private data class QRow(val t: String, val s: String, val cur: Boolean, val i: Int)

@Composable
private fun Queue(m: AppModel) {
    val l = m.lq
    val rows: List<QRow> = when {
        l != null && m.libTrack != null -> l.mapIndexed { i, x -> QRow(x.t, x.artist, i == m.li, i) }
        // the amplifier has no queue API: show what is playing now
        m.live -> listOf(QRow(m.np.t, m.np.s, true, 0))
        else -> SK.tr.mapIndexed { i, x -> QRow(x.first, x.second, i == m.trk, i) }
    }
    Column(Modifier.fillMaxSize(), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        T("Neste i køen", sora(15f, W.Semibold))
        Column(Modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp)).background(Color.Black.copy(alpha = 0.22f)).verticalScroll(rememberScrollState())) {
            for (r in rows) {
                Row(
                    Modifier.fillMaxWidth().heightIn(min = 56.dp).topLine(if (r.i > 0) C.ink.copy(alpha = 0.1f) else Color.Transparent)
                        .press {
                            val q = m.lq
                            if (q != null && m.libTrack != null) m.playLib(q, r.i, keepOpen = true) else if (!m.live) { m.trk = r.i; m.pos = 0 }
                            m.queueOpen = false
                        }.padding(horizontal = 12.dp),
                    verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    ArtFill(r.t, Modifier.size(40.dp).clip(RoundedCornerShape(6.dp)))
                    Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                        T(r.t, sora(14f, W.Regular, if (r.cur) C.accent2 else C.ink), maxLines = 1)
                        T(r.s, sora(12f, W.Regular, C.ink.copy(alpha = 0.6f)), maxLines = 1)
                    }
                    T(if (r.cur) "SPILLER" else "", mono(10f, C.accent2))
                }
            }
        }
    }
}

// MARK: Progress + controls

@Composable
private fun Progress(m: AppModel) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        BoxWithConstraints(
            Modifier.fillMaxWidth().height(16.dp).pointerInput(m.duration) {
                detectTapGestures { p -> m.pos = (p.x / size.width * m.duration).toInt() }
            },
            contentAlignment = Alignment.CenterStart,
        ) {
            Box(Modifier.fillMaxWidth().height(5.dp).clip(CircleShape).background(C.ink.copy(alpha = 0.22f)))
            Box(Modifier.width(maxWidth * (m.position.toFloat() / maxOf(1, m.duration))).height(5.dp).clip(CircleShape).background(C.ink.copy(alpha = 0.9f)))
        }
        Row(Modifier.fillMaxWidth()) {
            T(fmt(m.position), mono(10f, C.ink.copy(alpha = 0.6f)))
            Spacer(Modifier.weight(1f))
            T("−" + fmt(m.duration - m.position), mono(10f, C.ink.copy(alpha = 0.6f)))
        }
    }
}

@Composable
private fun Controls(m: AppModel) {
    Row(Modifier.fillMaxWidth().padding(horizontal = 2.dp), verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.size(40.dp).press { m.shuffle = !m.shuffle }, contentAlignment = Alignment.Center) {
            SKIcon(Icons.shuffle, 20.dp, 2f, if (m.shuffle) C.accent2 else C.ink.copy(alpha = 0.75f))
        }
        Spacer(Modifier.weight(1f))
        Box(Modifier.size(52.dp).press { m.prev() }, contentAlignment = Alignment.Center) { SKIcon(Icons.prev, 30.dp, color = C.ink, fill = true) }
        Spacer(Modifier.weight(1f))
        Box(Modifier.size(72.dp).shadow(10.dp, CircleShape).clip(CircleShape).background(C.ink).press { m.togglePlay() }, contentAlignment = Alignment.Center) {
            SKIcon(if (m.playing) Icons.pause else Icons.playRound, 32.dp, color = C.bg, fill = true)
        }
        Spacer(Modifier.weight(1f))
        Box(Modifier.size(52.dp).press { m.next() }, contentAlignment = Alignment.Center) { SKIcon(Icons.next, 30.dp, color = C.ink, fill = true) }
        Spacer(Modifier.weight(1f))
        Box(Modifier.size(40.dp).press { m.repeatOn = !m.repeatOn }, contentAlignment = Alignment.Center) {
            SKIcon(Icons.repeatIcon, 20.dp, 2f, if (m.repeatOn) C.accent2 else C.ink.copy(alpha = 0.75f))
        }
    }
}

@Composable
private fun CircleButton(d: String, on: Boolean, fill: Boolean = false, action: () -> Unit) {
    Box(
        Modifier.size(48.dp).clip(CircleShape).background(if (on) C.ink.copy(alpha = 0.22f) else Color.Black.copy(alpha = 0.18f))
            .skCapsuleBorder(C.ink.copy(alpha = 0.18f)).press(onClick = action),
        contentAlignment = Alignment.Center,
    ) { SKIcon(d, 20.dp, 2f, C.ink, fill) }
}

fun fmt(s: Int): String = "${s / 60}:" + "%02d".format(s % 60)
