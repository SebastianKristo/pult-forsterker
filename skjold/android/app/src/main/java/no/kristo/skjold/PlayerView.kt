package no.kristo.skjold

import androidx.compose.animation.core.Animatable
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.tween
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
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
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
    var more by remember { mutableStateOf(false) }
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
            TopBar(m) { more = true }
            Column(Modifier.weight(1f).padding(start = 18.dp, end = 18.dp, top = 6.dp, bottom = 12.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                PlayerContent(m, pa) { more = true }
            }
        }
        if (more) MoreSheet(m) { more = false }
    }
}

// v4: segmentkontroll Låt/Kø (Android) – kantlinje rgba(242,242,238,.4), linse rgba(240,196,106,.24) som glir 0.4 s
private val LensEase = CubicBezierEasing(0.3f, 1.3f, 0.45f, 1f)

/**
 * Låt/Kø: én linse som kan dras mellom knappene (som Liquid Glass-bryteren på iOS). Mens du holder strekker linsen seg
 * (bredere og lavere), den følger fingeren med gummistrikk forbi kantene, gir et tikk når den passerer midten og
 * fjærer på plass når du slipper. Et trykk flytter den dit du trykket.
 */
@Composable
private fun SongQueueSwitch(m: AppModel) {
    val segW = 76.dp
    val segPx = with(LocalDensity.current) { segW.toPx() }
    val scope = rememberCoroutineScope()
    val lens = remember { Animatable(if (m.queueOpen) segPx else 0f) }
    var hold by remember { mutableStateOf(false) }
    val sx by animateFloatAsState(if (hold) 1.14f else 1f, spring(dampingRatio = 0.55f, stiffness = 600f), label = "lensX")
    val sy by animateFloatAsState(if (hold) 0.9f else 1f, spring(dampingRatio = 0.55f, stiffness = 600f), label = "lensY")
    LaunchedEffect(m.queueOpen) { if (!hold) lens.animateTo(if (m.queueOpen) segPx else 0f, tween(400, easing = LensEase)) }
    val gummi = { r: Float -> if (r < 0f) -Math.pow((-r).toDouble(), 0.7).toFloat() else if (r > segPx) segPx + Math.pow((r - segPx).toDouble(), 0.7).toFloat() else r }
    val onQ = lens.value >= segPx / 2
    Box(
        Modifier.width(segW * 2 + 8.dp).height(40.dp).clip(CircleShape).skCapsuleBorder(SkG.segLine).padding(4.dp)
            .pointerInput(Unit) {
                detectTapGestures(
                    onPress = { hold = true; tryAwaitRelease(); hold = false },
                    onTap = { o -> val q = o.x > segPx; if (q != m.queueOpen) { Haptics.tick(); m.queueOpen = q } },
                )
            }
            .pointerInput(Unit) {
                var raw = 0f
                detectHorizontalDragGestures(
                    onDragStart = { hold = true; raw = lens.value },
                    onDragEnd = {
                        hold = false
                        val q = lens.value >= segPx / 2
                        if (q != m.queueOpen) m.queueOpen = q
                        scope.launch { lens.animateTo(if (q) segPx else 0f, spring(dampingRatio = 0.62f, stiffness = 500f)) }
                    },
                    onDragCancel = { hold = false; scope.launch { lens.animateTo(if (m.queueOpen) segPx else 0f) } },
                ) { ch, d ->
                    ch.consume()
                    val før = lens.value
                    raw += d
                    val nx = gummi(raw)
                    if ((nx >= segPx / 2) != (før >= segPx / 2)) Haptics.tick()
                    scope.launch { lens.snapTo(nx) }
                }
            },
    ) {
        Box(
            Modifier.offset { IntOffset(lens.value.roundToInt(), 0) }.width(segW).height(32.dp)
                .graphicsLayer { scaleX = sx; scaleY = sy }.clip(CircleShape).background(SkG.segLens),
        )
        Row {
            for ((q, label) in listOf(false to "Låt", true to "Kø")) {
                Box(Modifier.width(segW).height(32.dp), contentAlignment = Alignment.Center) {
                    T(label, sora(14f, W.Semibold, if (onQ == q) C.ink else C.ink.copy(alpha = 0.6f)))
                }
            }
        }
    }
}

/** v4 «Mer»-arket (Android): fra bunnkanten, radius 28/28/0/0, dempelag rgba(5,5,6,.88). */
@Composable
private fun MoreSheet(m: AppModel, close: () -> Unit) {
    var crossfade by remember { mutableStateOf(false) }
    var sleep by remember { mutableStateOf("Av") }
    Box(Modifier.fillMaxSize().background(SkG.dimBg).press { close() }, contentAlignment = Alignment.BottomCenter) {
        Column(
            Modifier.fillMaxWidth().clip(RoundedCornerShape(topStart = 28.dp, topEnd = 28.dp)).background(SkG.menuBg)
                .press { }.windowInsetsPadding(WindowInsets.systemBars).padding(top = 10.dp, bottom = 12.dp),
        ) {
            Box(Modifier.align(Alignment.CenterHorizontally).width(36.dp).height(4.dp).clip(CircleShape).background(C.ink.copy(alpha = 0.3f)))
            Row(Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 14.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                ArtFill(m.playerArt.key, Modifier.size(48.dp).clip(RoundedCornerShape(12.dp)))
                Column(Modifier.weight(1f)) {
                    T(m.np.t, sora(15f, W.Semibold), maxLines = 1)
                    T(m.np.s, sora(12f, W.Regular, SkG.miniSub), maxLines = 1)
                }
            }
            val radioSt = if (m.input == 3) m.curRadio else null
            MoreRow(Icons.plus, if (radioSt != null && m.favIndex(radioSt.name) != null) "Fjern fra Skjold-favoritter" else "Lagre i Skjold-favoritter", enabled = radioSt != null) {
                if (radioSt != null) m.toggleFav(radioSt); close()
            }
            MoreRow(Icons.queue, "Spill neste", enabled = m.lq != null) { Haptics.tick(); close() }
            MoreRow(Icons.favList, "Legg til i spilleliste", enabled = m.lq != null) { Haptics.tick(); close() }
            MoreRow(Icons.search, "Søk etter artist", enabled = m.np.s.isNotBlank()) {
                // åpner kildesiden (biblioteket som spiller, ellers Navidrome) med artisten i søkefeltet
                m.openLib(if (m.libTrack != null) m.lib else "nd"); m.lq2 = m.np.s.substringBefore(" · ").trim(); m.full = false; close()
            }
            MoreRow(Icons.close, "Fjern fra køen", enabled = m.lq != null) { Haptics.tick(); close() }
            Row(Modifier.fillMaxWidth().heightIn(min = 52.dp).padding(horizontal = 20.dp), verticalAlignment = Alignment.CenterVertically) {
                T("Krysstoning", sora(15f), Modifier.weight(1f))
                SKToggle(crossfade, onColor = C.accent) { crossfade = !crossfade }
            }
            Column(Modifier.padding(horizontal = 20.dp, vertical = 8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                T("Sovetimer", sora(15f))
                Flow(6.dp) { for (o in listOf("Av", "15 min", "30 min", "60 min", "Etter låten")) SKChip(o, on = sleep == o) { sleep = o } }
            }
        }
    }
}

@Composable
private fun MoreRow(icon: String, label: String, enabled: Boolean = true, action: () -> Unit) {
    Row(
        Modifier.fillMaxWidth().heightIn(min = 52.dp).alpha(if (enabled) 1f else 0.4f).press(enabled = enabled, onClick = action).padding(horizontal = 20.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        SKIcon(icon, 22.dp, 1.8f, C.ink)
        T(label, sora(15f))
    }
}

/** Top bar (YouTube Music style): close ⌄ · Låt/Kø switch · speakers · more ⋮ */
@Composable
private fun TopBar(m: AppModel, openMore: () -> Unit) {
    val ctx = androidx.compose.ui.platform.LocalContext.current
    Box(Modifier.fillMaxWidth().padding(top = 8.dp, bottom = 4.dp), contentAlignment = Alignment.Center) {
        SongQueueSwitch(m)
        Row(Modifier.fillMaxWidth().padding(horizontal = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            TopButton(Icons.chevronDown, 26.dp, 2.2f) { m.full = false }
            Spacer(Modifier.weight(1f))
            TopButton(Icons.speaker, 22.dp, 1.8f) { if (!SkjoldRoutes.showOutputSwitcher(ctx)) { m.full = false; m.tab = 2 } }   // «Spill på»: systemets Medieutgang, ellers Rom
            TopButton(Icons.moreVertical, 22.dp, fill = true) { openMore() }
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
private fun androidx.compose.foundation.layout.ColumnScope.PlayerContent(m: AppModel, pa: AppModel.PlayerArt, openMore: () -> Unit) {
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
        if (LocalPlay.on) {   // «Denne telefonen»: glideren styrer volumet på telefonen
            SKSlider(LocalPlay.vol.toDouble(), { LocalPlay.setVol(it.toInt()) }, tint = C.accent, modifier = Modifier.weight(1f))
            T("${LocalPlay.vol}", mono(12f, C.accent), Modifier.width(22.dp), align = androidx.compose.ui.text.style.TextAlign.End)
        } else {
            SKSlider(m.vol.toDouble(), { m.setVol(it.toInt()) }, tint = C.ink, modifier = Modifier.weight(1f))
            T("${m.vol}", mono(12f, C.ink.copy(alpha = 0.7f)), Modifier.width(22.dp), align = androidx.compose.ui.text.style.TextAlign.End)
        }
    }
    ListenHere(m)
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
        CircleButton(Icons.more, false, fill = true) { openMore() }
    }
}

// MARK: Cover

@Composable
private fun Cover(m: AppModel, pa: AppModel.PlayerArt) {
    val a = art(pa.key)
    Box(Modifier.widthIn(max = 322.dp).heightIn(max = 322.dp).fillMaxHeight().aspectRatio(1f, matchHeightConstraintsFirst = true).shadow(30.dp, RoundedCornerShape(22.dp)).clip(RoundedCornerShape(22.dp))) {
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

/** Fremdriften. Trykk eller dra for å spole når kilden støtter det (m.canSeek). */
@Composable
private fun Progress(m: AppModel) {
    var drag by remember { mutableStateOf<Float?>(null) }   // 0…1 mens du drar
    val dur = maxOf(1, m.duration)
    val frac = drag ?: (m.position.toFloat() / dur).coerceIn(0f, 1f)
    val shown = drag?.let { (it * dur).toInt() } ?: m.position
    val seek = m.canSeek
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        BoxWithConstraints(
            Modifier.fillMaxWidth().height(22.dp)
                .pointerInput(seek, dur) {
                    if (!seek) return@pointerInput
                    detectTapGestures { p -> Haptics.tick(); m.seekTo(((p.x / size.width).coerceIn(0f, 1f) * dur).toInt()) }
                }
                .pointerInput(seek, dur) {
                    if (!seek) return@pointerInput
                    detectHorizontalDragGestures(
                        onDragStart = { o -> Haptics.tick(); drag = (o.x / size.width).coerceIn(0f, 1f) },
                        onDragEnd = { drag?.let { f -> Haptics.tick(); m.seekTo((f * dur).toInt()) }; drag = null },
                        onDragCancel = { drag = null },
                    ) { ch, d -> ch.consume(); drag = ((drag ?: 0f) + d / size.width).coerceIn(0f, 1f) }
                },
            contentAlignment = Alignment.CenterStart,
        ) {
            val h = if (drag != null) 8.dp else 5.dp
            Box(Modifier.fillMaxWidth().height(h).clip(CircleShape).background(C.ink.copy(alpha = 0.22f)))
            Box(Modifier.width(maxWidth * frac).height(h).clip(CircleShape).background(C.ink.copy(alpha = 0.9f)))
            if (seek) {
                val knob = if (drag != null) 18.dp else 14.dp
                Box(Modifier.offset(x = maxWidth * frac - knob / 2).size(knob).clip(CircleShape).background(C.ink))
            }
        }
        Row(Modifier.fillMaxWidth()) {
            T(fmt(shown), mono(10f, C.ink.copy(alpha = 0.6f)))
            Spacer(Modifier.weight(1f))
            T("−" + fmt(m.duration - shown), mono(10f, C.ink.copy(alpha = 0.6f)))
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


/** «Spill på denne telefonen»: lyden flyttes hit, rommet dempes og følger med (kø, pause, spoling). Se LocalPlay. */
@Composable
private fun ListenHere(m: AppModel) {
    val ctx = androidx.compose.ui.platform.LocalContext.current
    val on = LocalPlay.on
    if (!on && !LocalPlay.can(m)) return
    Row(
        Modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp))
            .background(if (on) C.accent.copy(alpha = 0.16f) else C.ink.copy(alpha = 0.06f))
            .skBorder(if (on) C.accent else C.ink.copy(alpha = 0.16f), 14.dp)
            .press { if (on) LocalPlay.stop() else LocalPlay.start(ctx, m) }
            .padding(horizontal = 14.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        SKIcon("M8 2h8a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2zM11 18h2", 20.dp, 1.8f, if (on) C.accent else C.ink)
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            T(if (on) "Spiller på denne telefonen" else "Spill på denne telefonen", sora(14f, W.Semibold))
            T(if (on) "Trykk for å flytte lyden tilbake til rommet" else "Rommet dempes og følger med", sora(12f, W.Regular, C.ink.copy(alpha = 0.6f)))
        }
    }
}
