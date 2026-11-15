package no.kristo.skjold

import androidx.activity.compose.BackHandler
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.snap
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.Orientation
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
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
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
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
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawWithContent
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.BlendMode
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.CompositingStrategy
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.layout
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlin.math.roundToInt

/*
 * Nå spilles (v4), som V4NowPlaying.swift på iOS: bakgrunn farget fra omslaget, Låt/Kø-bryter, omslag 322, tittel og
 * kvalitet, fremdrift, kontroller, volum, «Spill på»-panelet (rom) og bunnraden med kø, gruppe og «Mer».
 * UI-tilstanden ligger i PlayerUi (PlayerV4.kt). Dra ned for å lukke.
 */

@Composable
fun FullPlayerView(m: AppModel) {
    val wide = LocalConfiguration.current.screenWidthDp >= 600   // panel fra høyre på brett og nettbrett
    val scope = rememberCoroutineScope()
    val drag = remember { Animatable(0f) }
    val closeAt = with(LocalDensity.current) { 120.dp.toPx() }
    val fm = PlayerUi.fm
    val info = art(m.playerArt.key)
    val top = info.stops.firstOrNull()?.second ?: hex(0x145a67)
    val mid = info.stops.lastOrNull()?.second ?: hex(0x0b2f38)
    val panelScroll = rememberScrollState()

    DisposableEffect(Unit) { onDispose { PlayerUi.fm = "ctrl"; PlayerUi.more = false } }
    // tilbake-knappen lukker «Mer» før spilleren (ContentView lukker spilleren)
    BackHandler(enabled = PlayerUi.more) { PlayerUi.closeMore() }

    Box(Modifier.fillMaxSize()) {
        Box(
            Modifier.fillMaxSize()
                // Dra ned for å lukke. Måles før offset, så draget ikke hakker når spilleren flytter seg med fingeren.
                // I Kø-visningen og «Spill på»-panelet ruller lista først.
                .draggable(
                    rememberDraggableState { d ->
                        val new = maxOf(0f, drag.value + d)
                        if ((drag.value <= closeAt) != (new <= closeAt)) Haptics.tick()
                        scope.launch { drag.snapTo(new) }
                    },
                    Orientation.Vertical,
                    enabled = !wide,
                    onDragStopped = { v ->
                        if (drag.value > closeAt || (drag.value > 20 && v > 1800f)) { close(m); delay(350); drag.snapTo(0f) }
                        else drag.animateTo(0f, spring(dampingRatio = 0.85f, stiffness = 380f))
                    },
                )
                .offset { IntOffset(0, drag.value.roundToInt()) }
                // linear-gradient(180deg, topp 0 %, midt 46 %, #090d0f 100 %), helt bak status- og navigasjonslinja
                .background(Brush.verticalGradient(0f to top, 0.46f to mid, 1f to PlayerColors.playerEnd)),
        ) {
            Column(Modifier.fillMaxSize().windowInsetsPadding(WindowInsets.systemBars)) {
                Header(m)
                Column(
                    Modifier.weight(1f).fillMaxWidth()
                        .then(if (fm == "rooms") Modifier.verticalScroll(panelScroll) else Modifier)
                        .padding(start = 24.dp, end = 24.dp, top = 16.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp),
                ) {
                    if (fm == "queue") Queue(m, wide) else Cover(m, info, wide)
                    TitleRow(m)
                    if (fm == "rooms") RoomsPanel(m) else if (fm == "ctrl") Controls(m)
                }
                BottomRow(m, wide)
            }
        }
        PlayerMoreSheet(m)
    }
}

private fun close(m: AppModel) { m.full = false; PlayerUi.more = false; PlayerUi.fm = "ctrl" }

private fun toggle(f: String) { Haptics.tick(); PlayerUi.fm = if (PlayerUi.fm == f) "ctrl" else f }

private fun openMore(t: Track? = null) = PlayerUi.openMore(t)

// MARK: Topp

/** ⌄ · Låt/Kø · rom · ⋮ */
@Composable
private fun Header(m: AppModel) {
    val rooms = PlayerUi.fm == "rooms"
    Row(
        Modifier.fillMaxWidth().padding(start = 16.dp, end = 16.dp, top = 4.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        IconButton(PlayerIcons.chevDown, 24.dp, 2.4f, C.ink, 44.dp, "Lukk spiller") { close(m) }
        Spacer(Modifier.weight(1f))
        Segment()
        Spacer(Modifier.weight(1f))
        IconButton(PlayerIcons.speaker, 22.dp, 1.8f, if (rooms) PlayerColors.gold else C.ink, 44.dp, "Rom") { toggle("rooms") }
        IconButton(PlayerIcons.dotsV, 22.dp, 1.8f, C.ink, 36.dp, "Mer", fill = true) { openMore() }
    }
}

@Composable
private fun IconButton(d: String, size: Dp, stroke: Float, color: Color, w: Dp, label: String, fill: Boolean = false, act: () -> Unit) {
    Box(Modifier.size(w, 44.dp).press(label = label) { act() }, contentAlignment = Alignment.Center) {
        SKIcon(d, size, stroke, color, fill)
    }
}

// Linsen glir som V4.segLens: timingCurve(0.3, 1.3, 0.45, 1), 0.4 s
private val LensEase = CubicBezierEasing(0.3f, 1.3f, 0.45f, 1f)

/**
 * Låt/Kø: én linse som kan dras mellom knappene (Liquid Glass-segmentet på iOS; Android har ikke glass, så linsen er
 * rgba(240,196,106,.24) i en kapsel med kant .4). Mens du holder strekker linsen seg (bredere og lavere), følger
 * fingeren med gummistrikk forbi kantene, gir et tikk når den passerer midten og fjærer på plass når du slipper.
 */
@Composable
private fun Segment() {
    val segW = 81.dp
    val segPx = with(LocalDensity.current) { segW.toPx() }
    val scope = rememberCoroutineScope()
    val q = PlayerUi.fm == "queue"
    val lens = remember { Animatable(if (q) segPx else 0f) }
    var hold by remember { mutableStateOf(false) }
    val sx by animateFloatAsState(if (hold) 1.14f else 1f, spring(dampingRatio = 0.62f, stiffness = 500f), label = "lensX")
    val sy by animateFloatAsState(if (hold) 0.9f else 1f, spring(dampingRatio = 0.62f, stiffness = 500f), label = "lensY")
    LaunchedEffect(q) { if (!hold) lens.animateTo(if (q) segPx else 0f, tween(400, easing = LensEase)) }
    val gummi = { r: Float -> if (r < 0f) -Math.pow((-r).toDouble(), 0.7).toFloat() else if (r > segPx) segPx + Math.pow((r - segPx).toDouble(), 0.7).toFloat() else r }
    val onQ = lens.value >= segPx / 2
    val pick = { ko: Boolean -> PlayerUi.fm = if (ko) "queue" else "ctrl" }
    Box(
        Modifier.width(170.dp).height(42.dp).clip(CircleShape).skCapsuleBorder(SkG.segLine).padding(4.dp)
            .semantics { contentDescription = if (q) "Kø" else "Låt"; stateDescription = "Bytt mellom låt og kø" }
            .pointerInput(Unit) {
                detectTapGestures(
                    onPress = { hold = true; tryAwaitRelease(); hold = false },
                    onTap = { o -> val ko = o.x > segPx; if (ko != (PlayerUi.fm == "queue")) { Haptics.tick(); pick(ko) } },
                )
            }
            .pointerInput(Unit) {
                var raw = 0f
                detectHorizontalDragGestures(
                    onDragStart = { hold = true; raw = lens.value },
                    onDragEnd = {
                        hold = false
                        val ko = lens.value >= segPx / 2
                        pick(ko)
                        scope.launch { lens.animateTo(if (ko) segPx else 0f, spring(dampingRatio = 0.72f, stiffness = 400f)) }
                    },
                    onDragCancel = { hold = false; scope.launch { lens.animateTo(if (PlayerUi.fm == "queue") segPx else 0f) } },
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
            Modifier.offset { IntOffset(lens.value.roundToInt(), 0) }.width(segW).height(34.dp)
                .graphicsLayer { scaleX = sx; scaleY = sy }.clip(CircleShape).background(SkG.segLens),
        )
        Row {
            for ((ko, label) in listOf(false to "Låt", true to "Kø")) {
                Box(Modifier.width(segW).height(34.dp), contentAlignment = Alignment.Center) {
                    T(label, sora(15f, W.Semibold, if (onQ == ko) C.ink else C.ink.copy(alpha = 0.55f)))
                }
            }
        }
    }
}

// MARK: Omslag

@Composable
private fun Cover(m: AppModel, a: ArtInfo, wide: Boolean) {
    val pa = m.playerArt
    val rooms = PlayerUi.fm == "rooms"
    BoxWithConstraints(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
        val base = minOf(if (wide) 300.dp else 322.dp, maxWidth)
        val target = if (rooms) (base.value * 0.62f).roundToInt().dp else base
        val side by animateDpAsState(target, tween(350, easing = FastOutSlowInEasing), label = "cover")
        val shape = RoundedCornerShape(22.dp)
        Box(Modifier.size(side).shadow(30.dp, shape, ambientColor = Color.Black, spotColor = Color.Black).clip(shape)) {
            ArtFill(a)
            if (!a.hasLogo) Column(Modifier.fillMaxSize().padding(22.dp)) {
                T(pa.kicker, mono(11f, a.ink.copy(alpha = 0.8f), 0.14f), maxLines = 1)
                Spacer(Modifier.weight(1f))
                // 48 (30 i rom-visningen), krymper ned til halvparten når det lengste ordet ikke får plass (minimumScaleFactor .5)
                val want = if (rooms) 30f else 48f
                val longest = pa.big.split(' ').maxOfOrNull { it.length } ?: 1
                val fit = (side.value - 44f) / (0.6f * maxOf(1, longest))
                val fs = fit.coerceIn(want * 0.5f, want)
                T(pa.big, sora(fs, W.Semibold, a.ink, 1f).copy(letterSpacing = (-0.02f).em), maxLines = 3)
            }
        }
    }
}

@Composable
private fun TitleRow(m: AppModel) {
    val np = m.np
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
            T(np.t, sora(22f, W.Semibold), maxLines = 1)
            val l = m.playerLinks
            if (l != null && !(l.first.isEmpty() && l.second.isEmpty())) {
                // artist og album som diskré lenker: åpner søket på artisten eller albumet
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    if (l.first.isNotEmpty()) NpLink(m, l.first, "Gå til artisten", Modifier.weight(1f, fill = false))
                    if (l.first.isNotEmpty() && l.second.isNotEmpty()) T("·", sora(14f, W.Regular, C.ink.copy(alpha = 0.45f)))
                    if (l.second.isNotEmpty()) NpLink(m, l.second, "Gå til albumet", Modifier.weight(1f, fill = false))
                }
            } else {
                T(np.s, sora(14f, W.Regular, C.ink.copy(alpha = 0.7f)), maxLines = 1)
            }
        }
        T(m.quality, mono(10f, C.ink.copy(alpha = 0.65f), 0.06f), maxLines = 1)
    }
}

@Composable
private fun NpLink(m: AppModel, text: String, hint: String, modifier: Modifier) {
    T(text, sora(14f, W.Regular, C.ink.copy(alpha = 0.7f)), modifier.press(label = hint) { m.playerSearch(text) }, maxLines = 1)
}

// MARK: Kontroller

@Composable
private fun Controls(m: AppModel) {
    Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
        if (m.hasProgress) Progress(m) else LiveTag()
        Row(Modifier.fillMaxWidth().padding(horizontal = 4.dp), verticalAlignment = Alignment.CenterVertically) {
            ToggleIcon(PlayerIcons.shuffle, m.shuffle, "Tilfeldig rekkefølge") { m.shuffle = !m.shuffle }
            Spacer(Modifier.weight(1f))
            Box(Modifier.size(46.dp).press(label = "Forrige") { m.prev() }, contentAlignment = Alignment.Center) {
                SKIcon(PlayerIcons.skip, 30.dp, color = C.ink, fill = true, modifier = Modifier.graphicsLayer { scaleX = -1f })
            }
            Spacer(Modifier.weight(1f))
            Box(
                Modifier.size(72.dp).clip(CircleShape).background(C.ink.copy(alpha = 0.14f)).skCapsuleBorder(Color.White.copy(alpha = 0.16f))
                    .press(label = if (m.playing) "Pause" else "Spill") { m.togglePlay() },
                contentAlignment = Alignment.Center,
            ) { SKIcon(if (m.playing) PlayerIcons.pause else PlayerIcons.play, 28.dp, color = C.ink, fill = true) }
            Spacer(Modifier.weight(1f))
            Box(Modifier.size(46.dp).press(label = "Neste") { m.next() }, contentAlignment = Alignment.Center) {
                SKIcon(PlayerIcons.skip, 30.dp, color = C.ink, fill = true)
            }
            Spacer(Modifier.weight(1f))
            ToggleIcon(PlayerIcons.repeatP, m.repeatOn, "Gjenta") { m.repeatOn = !m.repeatOn }
        }
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            SKIcon(PlayerIcons.vol, 18.dp, 1.8f, C.ink.copy(alpha = 0.8f))
            if (LocalPlay.on) {   // «Denne telefonen»: glideren styrer volumet på telefonen
                PlayerBar(LocalPlay.vol / 100.0, { LocalPlay.changeVol((it * 100).roundToInt()) }, Modifier.weight(1f), label = "Volum på denne telefonen")
                T("${LocalPlay.vol}", mono(13f, PlayerColors.gold), Modifier.width(24.dp), align = TextAlign.End)
            } else {
                PlayerBar(m.v4GroupVol / 100.0, { m.v4SetGroupVol((it * 100).roundToInt()) }, Modifier.weight(1f))
                T("${m.v4GroupVol}", mono(13f, C.ink), Modifier.width(24.dp), align = TextAlign.End)
            }
        }
    }
}

@Composable
private fun ToggleIcon(d: String, on: Boolean, label: String, act: () -> Unit) {
    Box(
        Modifier.size(44.dp).press(label = "$label, ${if (on) "på" else "av"}") { Haptics.tick(); act() },
        contentAlignment = Alignment.Center,
    ) { SKIcon(d, 22.dp, 1.8f, if (on) PlayerColors.gold else C.ink.copy(alpha = 0.7f)) }
}

/** Fremdriften. Trykk eller dra for å spole når kilden støtter det (m.canSeek). */
@Composable
private fun Progress(m: AppModel) {
    var drag by remember { mutableStateOf<Float?>(null) }   // 0…1 mens du drar
    val dur = maxOf(1, m.duration)
    val anim by animateFloatAsState(m.playerProgress, if (drag == null) tween(1000, easing = LinearEasing) else snap(), label = "pos")
    val frac = drag ?: anim
    val shown = drag?.let { (it * dur).toInt() } ?: m.position
    val seek = m.canSeek
    val knobScale by animateFloatAsState(if (drag == null) 1f else 1.3f, spring(dampingRatio = 0.7f, stiffness = 600f), label = "knob")
    Column(
        Modifier.semantics { contentDescription = "Fremdrift"; stateDescription = "${fmt(m.position)} av ${fmt(m.duration)}" },
        verticalArrangement = Arrangement.spacedBy(7.dp),
    ) {
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
            Box(Modifier.fillMaxWidth().height(h).clip(CircleShape).background(C.ink.copy(alpha = 0.2f)))
            Box(Modifier.width(maxWidth * frac).height(h).clip(CircleShape).background(C.ink))
            if (seek) Box(
                Modifier.offset(x = maxWidth * frac - 7.dp).size(14.dp)
                    .graphicsLayer { scaleX = knobScale; scaleY = knobScale }
                    .shadow(3.dp, CircleShape).clip(CircleShape).background(C.ink),
            )
        }
        Row(Modifier.fillMaxWidth()) {
            T(fmt(shown), mono(11f, C.ink.copy(alpha = 0.6f)))
            Spacer(Modifier.weight(1f))
            T("−" + fmt(maxOf(0, m.duration - shown)), mono(11f, C.ink.copy(alpha = 0.6f)))
        }
    }
}

@Composable
private fun LiveTag() {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Box(Modifier.size(7.dp).clip(CircleShape).background(PlayerColors.red))
        T("DIREKTE", mono(11f, PlayerColors.gold, 0.12f))
    }
}

fun fmt(s: Int): String = "${s / 60}:" + "%02d".format(s % 60)

// MARK: Kø

@Composable
private fun Queue(m: AppModel, wide: Boolean) {
    val rows = m.playerQueue
    val curIdx = rows.indexOfFirst { it.cur }.coerceAtLeast(0)
    val from = if (m.libTrack != null) (mapOf("nd" to "Navidrome", "plex" to "Plex", "ytm" to "YouTube Music")[m.lib] ?: "køen") else "køen"
    Column(Modifier.fillMaxWidth().height(if (wide) 360.dp else 400.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            T("Neste fra $from", sora(13f, W.Semibold, C.ink.copy(alpha = 0.75f)), Modifier.weight(1f), maxLines = 1)
            T("${rows.size} låter", sora(13f, W.Regular, C.ink.copy(alpha = 0.6f)))
        }
        Column(
            Modifier.weight(1f).bleed(10.dp)
                // maske: rader tones ut nederst (svart 82 % → klar 100 %)
                .graphicsLayer { compositingStrategy = CompositingStrategy.Offscreen }
                .drawWithContent {
                    drawContent()
                    drawRect(Brush.verticalGradient(0.82f to Color.Black, 1f to Color.Transparent), blendMode = BlendMode.DstIn)
                }
                .verticalScroll(rememberScrollState()),
        ) {
            rows.forEach { r -> QueueRow(m, r, curIdx) }
        }
    }
}

/** padding(.horizontal, −10): raden går litt ut over sidemargen. */
private fun Modifier.bleed(x: Dp): Modifier = layout { measurable, constraints ->
    val px = x.roundToPx()
    val w = constraints.maxWidth + 2 * px
    val p = measurable.measure(constraints.copy(minWidth = w, maxWidth = w))
    layout(constraints.maxWidth, p.height) { p.place(-px, 0) }
}

@Composable
private fun QueueRow(m: AppModel, r: PlayerQueueRow, curIdx: Int) {
    Row(
        Modifier.fillMaxWidth().alpha(if (r.i < curIdx) 0.45f else 1f).clip(RoundedCornerShape(14.dp))
            .background(if (r.cur) C.ink.copy(alpha = 0.1f) else Color.Transparent)
            .padding(horizontal = 10.dp, vertical = 7.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Row(Modifier.weight(1f).press { m.playerPlayQueue(r.i) }, verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            ArtFill(r.key, Modifier.size(48.dp).clip(RoundedCornerShape(9.dp)))
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    if (r.cur) EqBars()
                    T(r.t, sora(15f, W.Semibold), maxLines = 1)
                }
                T(r.s, sora(13f, W.Regular, C.ink.copy(alpha = 0.6f)), maxLines = 1)
            }
        }
        Box(Modifier.size(36.dp).press(label = "Mer") { openMore(track(m, r.i)) }, contentAlignment = Alignment.Center) {
            SKIcon(PlayerIcons.dotsSmall, 18.dp, color = C.ink, fill = true)
        }
        Box(Modifier.size(30.dp, 36.dp).press(label = "Flytt opp") { Haptics.tick(); m.playerQueueUp(r.i) }, contentAlignment = Alignment.Center) {
            SKIcon(PlayerIcons.handle, 20.dp, 1.8f, C.ink.copy(alpha = 0.45f))
        }
    }
}

@Composable
private fun EqBars() {
    Row(Modifier.height(11.dp), verticalAlignment = Alignment.Bottom, horizontalArrangement = Arrangement.spacedBy(1.5.dp)) {
        for (h in listOf(4, 8, 11, 6)) Box(Modifier.width(2.dp).height(h.dp).clip(RoundedCornerShape(1.dp)).background(C.ink))
    }
}

private fun track(m: AppModel, i: Int): Track? {
    val q = m.lq ?: return null
    if (m.libTrack == null || i >= q.size) return null
    return q[i]
}

// MARK: Rom-panel («Spill på»)

@Composable
private fun RoomsPanel(m: AppModel) {
    val group = m.v4Group
    val ids = group.map { it.id }.toSet()
    val off = m.sys.rooms.filter { it.id !in ids }
    Column(
        Modifier.fillMaxWidth().clip(RoundedCornerShape(24.dp)).background(C.ink.copy(alpha = 0.1f))
            .skBorder(Color.White.copy(alpha = 0.14f), 24.dp).padding(horizontal = 16.dp, vertical = 14.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        ListenHereRow(m)
        group.forEach { r -> GroupRow(m, r, group.size > 1) }
        if (group.size > 1) {
            Box(Modifier.fillMaxWidth().height(1.dp).background(Color.White.copy(alpha = 0.12f)))
            Row(verticalAlignment = Alignment.CenterVertically) {
                Row(Modifier.weight(1f), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    SKIcon(PlayerIcons.sync, 16.dp, 2f, PlayerColors.gold)
                    T("Gruppe", sora(16f, W.Semibold))
                }
                T("SYNKRON", mono(10f, PlayerColors.gold, 0.08f))
            }
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                StepCircle("−", "Senk alle") { m.v4SetGroupVol(m.v4GroupVol - 5) }
                BoxWithConstraints(Modifier.weight(1f).height(12.dp)) {
                    Box(Modifier.fillMaxSize().clip(CircleShape).background(C.ink.copy(alpha = 0.18f)))
                    Box(Modifier.width(maxWidth * (m.v4GroupVol / 100f)).fillMaxSize().clip(CircleShape).background(C.ink))
                }
                StepCircle("+", "Øk alle") { m.v4SetGroupVol(m.v4GroupVol + 5) }
                T("${m.v4GroupVol}", mono(13f, C.ink), Modifier.width(24.dp), align = TextAlign.End)
            }
        }
        if (off.isNotEmpty()) {
            T("Spill også i", sora(12f, W.Regular, C.ink.copy(alpha = 0.6f)))
            Flow(8.dp) {
                off.forEach { r ->
                    Box(
                        Modifier.height(34.dp).clip(CircleShape).background(C.ink.copy(alpha = 0.06f)).skCapsuleBorder(C.ink.copy(alpha = 0.25f))
                            .press { Haptics.tick(); m.playerToggleInGroup(r.id) }.padding(horizontal = 13.dp),
                        contentAlignment = Alignment.Center,
                    ) { T("+ " + r.name, sora(13f), maxLines = 1) }
                }
            }
        }
    }
}

/** «Denne telefonen»: lyden flyttes til telefonen, rommet dempes og følger med (kø, pause, spoling). Se LocalPlay. */
@Composable
private fun ListenHereRow(m: AppModel) {
    val ctx = LocalContext.current
    val on = LocalPlay.on
    if (!on && !LocalPlay.can(m)) return
    Row(
        Modifier.fillMaxWidth().press { if (on) LocalPlay.stop() else LocalPlay.start(ctx, m) },
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        SKIcon(PlayerIcons.phone, 20.dp, 1.8f, if (on) PlayerColors.gold else C.ink)
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            T(if (on) "Spiller på denne telefonen" else "Spill på denne telefonen", sora(15f, W.Semibold))
            T(if (on) "Trykk for å flytte lyden tilbake til rommet" else "Rommet dempes og følger med", sora(12f, W.Regular, C.ink.copy(alpha = 0.6f)))
        }
        Box(
            Modifier.size(24.dp).clip(CircleShape).background(if (on) PlayerColors.gold else Color.Transparent)
                .skCapsuleBorder(if (on) PlayerColors.gold else C.ink.copy(alpha = 0.35f), 1.5.dp),
        )
    }
    Box(Modifier.fillMaxWidth().height(1.dp).background(Color.White.copy(alpha = 0.12f)))
}

@Composable
private fun GroupRow(m: AppModel, r: Room, canRemove: Boolean) {
    val v = m.v4RoomVol(r)
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Row(Modifier.weight(1f), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                T(r.name, sora(16f, W.Semibold), maxLines = 1)
                T(SK.dev(r.type).n, mono(10f, C.ink.copy(alpha = 0.6f)), maxLines = 1)
            }
            if (canRemove) StepCircle("−", "Fjern fra gruppen", 30.dp) { m.playerToggleInGroup(r.id) }
        }
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            PlayerBar(v / 100.0, { x -> m.v4SetRoomVol(r.id, (x * 100).roundToInt()) }, Modifier.weight(1f), track = C.ink.copy(alpha = 0.18f), label = "Volum i " + r.name)
            T("$v", mono(13f, C.ink), Modifier.width(24.dp), align = TextAlign.End)
        }
    }
}

@Composable
private fun StepCircle(s: String, label: String, size: Dp = 34.dp, act: () -> Unit) {
    Box(
        Modifier.size(size).clip(CircleShape).background(C.ink.copy(alpha = 0.12f)).press(label = label) { Haptics.tick(); act() },
        contentAlignment = Alignment.Center,
    ) { T(s, sora(if (size > 30.dp) 18f else 16f)) }
}

// MARK: Bunnrad

@Composable
private fun BottomRow(m: AppModel, wide: Boolean) {
    val fm = PlayerUi.fm
    val rooms = fm == "rooms"
    Row(
        Modifier.fillMaxWidth().padding(start = 24.dp, end = 24.dp, top = 16.dp, bottom = if (wide) 30.dp else 24.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        RoundButton(PlayerIcons.queue, if (fm == "queue") C.ink.copy(alpha = 0.28f) else C.ink.copy(alpha = 0.1f), "Kø", fill = false) { toggle("queue") }
        Row(
            Modifier.weight(1f).height(52.dp).clip(CircleShape)
                .background(if (rooms) PlayerColors.gold.copy(alpha = 0.16f) else C.ink.copy(alpha = 0.1f))
                .skCapsuleBorder(if (rooms) PlayerColors.goldDark else Color.White.copy(alpha = 0.14f))
                .press(label = "Spill på") { toggle("rooms") }.padding(horizontal = 16.dp),
            verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp, Alignment.CenterHorizontally),
        ) {
            SKIcon(PlayerIcons.speaker, 18.dp, 1.8f, if (rooms) PlayerColors.gold else C.ink)
            T(m.v4GroupName, sora(14f, W.Semibold, if (rooms) PlayerColors.gold else C.ink), maxLines = 1)
        }
        RoundButton(PlayerIcons.dots, if (PlayerUi.more) C.ink.copy(alpha = 0.28f) else C.ink.copy(alpha = 0.1f), "Mer", fill = true) { openMore() }
    }
}

@Composable
private fun RoundButton(d: String, bg: Color, label: String, fill: Boolean, act: () -> Unit) {
    Box(
        Modifier.size(52.dp).clip(CircleShape).background(bg).skCapsuleBorder(Color.White.copy(alpha = 0.14f)).press(label = label) { act() },
        contentAlignment = Alignment.Center,
    ) { SKIcon(d, 20.dp, 1.8f, C.ink, fill) }
}
