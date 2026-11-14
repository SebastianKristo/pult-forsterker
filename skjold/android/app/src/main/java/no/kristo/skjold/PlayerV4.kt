package no.kristo.skjold

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.gestures.drag
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import kotlin.math.atan2
import kotlin.math.roundToInt

/*
 * Felles for Nå spilles (PlayerView.kt): UI-tilstand (V4State på iOS), ikonene fra V4Tokens.swift, v4-avledningene fra
 * V4Model.swift som spilleren trenger, «Mer»-arket og volumknotten (V4MoreSheet.swift).
 */

// MARK: - UI-tilstand

/** UI-tilstand for Nå spilles, «Mer» og volumknotten (fm, more, moreTrack, dial og sleep i V4State på iOS). */
object PlayerUi {
    private const val FAVS = "skjold-v4-favs"

    /** "ctrl" | "queue" | "rooms" */
    var fm by mutableStateOf("ctrl")
    var more by mutableStateOf(false)
    /** Låten «Mer» gjelder (fra køen eller en liste). null = det som spiller. */
    var moreTrack by mutableStateOf<Track?>(null)
    /** Volumknotten (hold på minispilleren på iOS). Vises av PlayerVolumeDial(m). */
    var dial by mutableStateOf(false)
    /** Sovetimer: 0 av, 1 15 min, 2 30 min, 3 60 min (lagres ikke, som på iOS). */
    var sleep by mutableStateOf(0)

    // Skjold-favoritter for låter: @AppStorage("skjold-v4-favs") på iOS, linjeskilt tekst under samme nøkkel.
    private val favsState = mutableStateOf<String?>(null)
    var favsRaw: String
        get() = favsState.value ?: Store.string(FAVS) ?: ""
        set(v) { favsState.value = v; Store.setString(FAVS, v) }
    val favs: Set<String> get() = favsRaw.split("\n").filter { it.isNotEmpty() }.toSet()

    fun openMore(t: Track? = null) { moreTrack = t; more = true }
    fun closeMore() { more = false }
}

/** Ikonstier fra V4Tokens.swift (viewBox 24). */
object PlayerIcons {
    const val chevDown = "M6 9l6 6 6-6"
    const val chevRight = "M9 6l6 6-6 6"
    const val search = "M11 18a7 7 0 1 0 0-14a7 7 0 1 0 0 14M20 20l-4-4"
    const val close = "M6 6l12 12M18 6L6 18"
    const val vol = "M4 9v6h4l5 4V5L8 9zM16 9a4 4 0 0 1 0 6"
    const val play = "M8 5.2v13.6a1 1 0 0 0 1.52.85l10.6-6.8a1 1 0 0 0 0-1.7L9.52 4.35A1 1 0 0 0 8 5.2z"
    val pause = SVG.rect(6f, 4.5f, 4f, 15f, 1.2f) + SVG.rect(14f, 4.5f, 4f, 15f, 1.2f)
    const val skip = "M5 5.5v13a.8.8 0 0 0 1.25.66L15 13.1V18a1 1 0 0 0 2 0V6a1 1 0 0 0-2 0v4.9L6.25 4.84A.8.8 0 0 0 5 5.5z"
    const val shuffle = "M4 7h3l10 10h3M4 17h3l3-3M14 10l3-3h3M18 5l2 2-2 2M18 15l2 2-2 2"
    const val repeatP = "M4 12V9a3 3 0 0 1 3-3h12M16 3l3 3-3 3M20 12v3a3 3 0 0 1-3 3H5M8 21l-3-3 3-3"
    const val queue = "M4 6h11M4 12h11M4 18h7M18 14v6l4-3z"
    const val speaker = "M7 3h10v18H7zM12 7h.01M12 17a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"
    val dots = SVG.circle(5f, 12f, 1.8f) + SVG.circle(12f, 12f, 1.8f) + SVG.circle(19f, 12f, 1.8f)
    val dotsSmall = SVG.circle(5f, 12f, 1.7f) + SVG.circle(12f, 12f, 1.7f) + SVG.circle(19f, 12f, 1.7f)
    val dotsV = SVG.circle(12f, 5f, 1.9f) + SVG.circle(12f, 12f, 1.9f) + SVG.circle(12f, 19f, 1.9f)
    const val handle = "M5 8h14M5 12h14M5 16h14"
    const val sync = "M4 12a8 8 0 0 1 14-5l2 2M20 12a8 8 0 0 1-14 5l-2-2M20 4v5h-5M4 20v-5h5"
    const val heart = "M12 20s-7-4.5-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.5-7 10-7 10z"
    const val sleep = "M12 21a8 8 0 1 0 0-16a8 8 0 1 0 0 16M12 9v4l2 2M5 3L2 6M19 3l3 3"
    const val phone = "M8 2h8a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2zM11 18h2"
}

/** Farger fra V4Tokens.swift som ikke finnes i C. */
object PlayerColors {
    val gold = hex(0xf0c46a)
    val goldDark = hex(0xd9a441)
    val red = hex(0xe8564a)
    val green = hex(0x6fcf7f)
    /** Bunnen av bakgrunnen i Nå spilles: linear-gradient(…, #090d0f 100%). */
    val playerEnd = hex(0x090d0f)
}

// MARK: - Modell (V4Model.swift / AppModel.swift på iOS)

data class PlayerQueueRow(val t: String, val s: String, val key: String, val cur: Boolean, val i: Int)

/** Køen: bibliotekskø, ellers demolåtene, ellers bare det som spiller (v4Queue). */
val AppModel.playerQueue: List<PlayerQueueRow>
    get() {
        val q = lq
        if (q != null && libTrack != null) return q.mapIndexed { i, x -> PlayerQueueRow(x.t, x.artist, x.album, i == li, i) }
        if (!live) return SK.tr.mapIndexed { i, x -> PlayerQueueRow(x.first, x.second, x.first, i == trk, i) }
        return listOf(PlayerQueueRow(np.t, np.s, playerArt.key, true, 0))
    }

/** Spill plass [i] i køen (v4PlayQueue). */
fun AppModel.playerPlayQueue(i: Int) {
    val q = lq
    if (q != null && libTrack != null) playLib(q, i, keepOpen = true)
    else if (!live) { trk = i; pos = 0; playing = true }
}

/** Flytt en låt i bibliotekskøen ett hakk opp (v4QueueUp). */
fun AppModel.playerQueueUp(i: Int) {
    val q = lq?.toMutableList() ?: return
    if (libTrack == null || i <= 0 || i >= q.size) return
    val t = q[i - 1]; q[i - 1] = q[i]; q[i] = t
    if (li == i) li = i - 1 else if (li == i - 1) li = i
    lq = q
}

/** Fjern en låt fra bibliotekskøen (ikke den som spiller) (v4QueueRemove). */
fun AppModel.playerQueueRemove(t: Track) {
    val q = lq?.toMutableList() ?: return
    if (libTrack == null) return
    val i = q.indexOf(t)
    if (i < 0 || i == li) return
    q.removeAt(i)
    if (i < li) li -= 1
    lq = q
}

/** Legg en låt rett etter den som spiller (v4PlayNext). */
fun AppModel.playerPlayNext(t: Track) {
    val q = lq?.toMutableList() ?: return
    if (libTrack == null) return
    val i = q.indexOf(t)
    if (i >= 0 && i != li) { q.removeAt(i); if (i < li) li -= 1 }
    q.add(minOf(q.size, li + 1), t)
    lq = q
}

/** Legg til / fjern et rom i gruppen til det aktive rommet (v4ToggleInGroup). */
fun AppModel.playerToggleInGroup(id: String) = setSys(sys.toggledInGroup(actRoom.id, id))

/** Kildenavnet i «Mer» (v4Src). */
val AppModel.playerSrc: String get() = if (headphones && input == 4) "USB" else srcName

/** Fremdrift 0…1 (radio = full) (v4Progress). */
val AppModel.playerProgress: Float
    get() {
        if (!hasProgress || duration <= 0) return if (input == 3) 1f else 0f
        return (position.toFloat() / duration).coerceIn(0f, 1f)
    }

/** Artist og album som lenker under tittelen (npLinks). Android-statusen har ikke sourceLabel, så bare bibliotekslåter. */
val AppModel.playerLinks: Pair<String, String>? get() = libTrack?.let { it.artist to it.album }

/** «Søk etter …»: Android har ingen egen søkeside ennå, så kildesiden åpnes med teksten i søkefeltet. */
fun AppModel.playerSearch(text: String) {
    PlayerUi.more = false
    full = false
    PlayerUi.fm = "ctrl"
    openLib(if (libTrack != null) lib else "nd")
    lq2 = text
}

// MARK: - Glidebryter (V4Bar)

/**
 * Glidebryter uten knott (V4Bar): spor [height] høyt, treffflate 24 dp høyere. Mens fingeren er nede følger linja
 * fingeren (statusoppdateringer overskriver den ikke), onChange sendes høyst hvert 70. ms og alltid når fingeren slippes.
 */
@Composable
fun PlayerBar(
    value: Double, onChange: (Double) -> Unit, modifier: Modifier = Modifier, height: Dp = 8.dp,
    track: Color = C.ink.copy(alpha = 0.2f), fill: Color = C.ink, label: String = "Volum",
) {
    val cb by rememberUpdatedState(onChange)
    var local by remember { mutableStateOf<Float?>(null) }
    val shown = (local ?: value.toFloat()).coerceIn(0f, 1f)
    Canvas(
        modifier.height(height + 24.dp)
            .semantics { contentDescription = label; stateDescription = "${(shown * 100).roundToInt()} prosent" }
            .pointerInput(Unit) {
                awaitEachGesture {
                    var last = -1
                    var lastSent = 0L
                    fun upd(px: Float, final: Boolean) {
                        val f = (px / size.width).coerceIn(0f, 1f)
                        local = f
                        val n = (f * 100).roundToInt()
                        if (last >= 0 && n != last) Haptics.sliderStep(last, n, 0, 100, null)
                        last = n
                        val now = System.currentTimeMillis()
                        if (final || now - lastSent > 70) { lastSent = now; cb(n / 100.0) }
                    }
                    val down = awaitFirstDown(requireUnconsumed = false)
                    down.consume()
                    upd(down.position.x, false)
                    var x = down.position.x
                    drag(down.id) { c -> x = c.position.x; upd(x, false); c.consume() }
                    upd(x, true)
                    Haptics.sliderRelease()
                    local = null
                },
            },
    ) {
        val h = height.toPx(); val cy = size.height / 2
        drawRoundRect(track, Offset(0f, cy - h / 2), Size(size.width, h), CornerRadius(h / 2))
        if (shown > 0f) drawRoundRect(fill, Offset(0f, cy - h / 2), Size(size.width * shown, h), CornerRadius(h / 2))
    }
}

// MARK: - «Mer»-arket

private val SheetEase = CubicBezierEasing(0.2f, 0.8f, 0.2f, 1f)
private val SleepLabels = listOf("Av", "15 min", "30 min", "60 min")
private val SleepMinutes = listOf(0, 15, 30, 60)

private class MoreRowData(val n: String, val p: String, val fill: Boolean, val ic: Color, val value: String? = null, val act: () -> Unit)

/**
 * «Mer»-arket (V4MoreSheet.swift): dempelag 0.45, ark fra bunnen med radius 34, farget fra låten. Styres av PlayerUi.more.
 * FullPlayerView viser det; åpnes det fra andre sider (PlayerUi.openMore) må roten vise PlayerMoreSheet(m) når spilleren er lukket.
 */
@Composable
fun PlayerMoreSheet(m: AppModel) {
    Box(Modifier.fillMaxSize()) {
        AnimatedVisibility(PlayerUi.more, enter = fadeIn(tween(300)), exit = fadeOut(tween(300))) {
            Box(Modifier.fillMaxSize().background(Color.Black.copy(alpha = 0.45f)).pointerInput(Unit) { detectTapGestures { PlayerUi.closeMore() } })
        }
        AnimatedVisibility(
            PlayerUi.more, modifier = Modifier.align(Alignment.BottomCenter),
            enter = slideInVertically(tween(420, easing = SheetEase)) { it }, exit = slideOutVertically(tween(420, easing = SheetEase)) { it },
        ) { MoreSheetBody(m) }
    }
}

@Composable
private fun MoreSheetBody(m: AppModel) {
    val t = PlayerUi.moreTrack ?: m.libTrack
    val title = t?.t ?: m.np.t
    val artist = t?.artist ?: m.np.s
    val key = t?.album ?: m.playerArt.key
    val a = art(m.playerArt.key)
    val top = a.stops.firstOrNull()?.second ?: hex(0x145a67)
    val mid = a.stops.lastOrNull()?.second ?: hex(0x0b2f38)
    val shape = RoundedCornerShape(topStart = 34.dp, topEnd = 34.dp)
    val close = { PlayerUi.closeMore() }

    val rows = buildList {
        val radioNow = m.input == 3 && t == null
        val isFav = if (radioNow) m.favIndex(m.curRadio.name) != null else PlayerUi.favs.contains(title)
        add(MoreRowData(if (isFav) "Lagret i Skjold-favoritter" else "Lagre i Skjold-favoritter", PlayerIcons.heart, isFav, if (isFav) PlayerColors.gold else C.ink) {
            if (radioNow) m.toggleFav(m.curRadio)
            else {
                val f = PlayerUi.favs.toMutableSet()
                if (title in f) f.remove(title) else { f.add(title); Haptics.success() }
                PlayerUi.favsRaw = f.sorted().joinToString("\n")
            }
        })
        add(MoreRowData("Spill neste", PlayerIcons.queue, false, C.ink) {
            if (t != null) { m.playerPlayNext(t); Haptics.success() } else Haptics.warning()
            close()
        })
        val who = artist.split(" · ").first()
        add(MoreRowData("Søk etter $who", PlayerIcons.search, false, C.ink) { m.playerSearch(who) })
        add(MoreRowData("Fjern fra køen", PlayerIcons.close, false, C.ink) {
            if (t != null) m.playerQueueRemove(t)
            close()
        })
        add(MoreRowData("Sovetimer", PlayerIcons.sleep, false, if (PlayerUi.sleep > 0) PlayerColors.gold else C.ink,
            value = SleepLabels[PlayerUi.sleep.coerceIn(0, SleepLabels.size - 1)]) {
            // sovetimeren går på enheten (skrur ned det siste minuttet og slår av), så den virker også når appen lukkes
            PlayerUi.sleep = (PlayerUi.sleep + 1) % SleepLabels.size
            val mins = SleepMinutes[PlayerUi.sleep]
            m.devSend("/api/plugins/sleep", if (mins > 0) mapOf("enabled" to true, "minutes" to mins) else mapOf("enabled" to false))
        })
    }

    Column(
        Modifier.fillMaxWidth().clip(shape).background(Brush.verticalGradient(listOf(top, mid)))
            .skBorder(Color.White.copy(alpha = 0.1f), 34.dp)
            .pointerInput(Unit) { detectTapGestures { } }   // trykk på arket lukker det ikke
            .windowInsetsPadding(WindowInsets.navigationBars)
            .padding(start = 16.dp, end = 16.dp, top = 10.dp, bottom = 26.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
            Box(Modifier.size(60.dp, 14.dp).press(label = "Lukk") { close() }, contentAlignment = Alignment.Center) {
                Box(Modifier.size(40.dp, 5.dp).clip(CircleShape).background(C.ink.copy(alpha = 0.4f)))
            }
        }
        Row(
            Modifier.padding(start = 4.dp, end = 4.dp, top = 4.dp, bottom = 8.dp),
            verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            ArtFill(key, Modifier.size(56.dp).shadow(8.dp, RoundedCornerShape(10.dp)).clip(RoundedCornerShape(10.dp)))
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                T(title, sora(18f, W.Semibold), maxLines = 1)
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    SourceGlyph(m.v4SrcIcon, 16.dp)
                    T(artist, sora(14f, W.Regular, C.ink.copy(alpha = 0.7f)), maxLines = 1)
                }
            }
        }
        rows.forEach { r -> MoreRow(r) }
        Box(Modifier.padding(horizontal = 4.dp, vertical = 6.dp).fillMaxWidth().height(1.dp).background(Color.White.copy(alpha = 0.1f)))
        Row(
            Modifier.padding(horizontal = 4.dp).heightIn(min = 48.dp),
            verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Box(Modifier.width(40.dp), contentAlignment = Alignment.Center) { SourceGlyph(m.v4SrcIcon, 34.dp) }
            Column(verticalArrangement = Arrangement.spacedBy(1.dp)) {
                T(m.playerSrc, sora(15f, W.Semibold), maxLines = 1)
                T(m.quality, mono(11f, C.ink.copy(alpha = 0.6f)), maxLines = 1)
            }
        }
    }
}

@Composable
private fun MoreRow(r: MoreRowData) {
    Row(
        Modifier.fillMaxWidth().heightIn(min = 50.dp).press { r.act() }.padding(horizontal = 4.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Box(Modifier.size(40.dp).clip(CircleShape).background(C.ink.copy(alpha = 0.12f)), contentAlignment = Alignment.Center) {
            if (r.fill) SKIcon(r.p, 21.dp, color = r.ic, fill = true)
            SKIcon(r.p, 21.dp, 1.8f, r.ic)
        }
        T(r.n, sora(16f, W.Semibold, lineHeight = 1.3f), Modifier.weight(1f))
        if (r.value != null) Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            T(r.value, sora(14f, W.Regular, C.ink.copy(alpha = 0.65f)))
            SKIcon(PlayerIcons.chevRight, 16.dp, 2.2f, C.ink)
        }
    }
}

// MARK: - Volumknotten

/**
 * Volumknotten (V4VolumeDial): −150° … +150°, 31 streker, dra rundt knotten. Vises når PlayerUi.dial er sann
 * (på iOS: hold på minispilleren i 450 ms). Trykk utenfor lukker.
 */
@Composable
fun PlayerVolumeDial(m: AppModel) {
    if (!PlayerUi.dial) return
    Box(
        Modifier.fillMaxSize().background(hex(0x050506, 0.78f)).pointerInput(Unit) { detectTapGestures { PlayerUi.dial = false } },
        contentAlignment = Alignment.Center,
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(26.dp)) {
            Row(
                Modifier.height(34.dp).clip(CircleShape).background(hex(0x28282a, 0.7f)).skCapsuleBorder(Color.White.copy(alpha = 0.12f))
                    .padding(horizontal = 14.dp),
                verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Box(Modifier.size(6.dp).clip(CircleShape).background(PlayerColors.green))
                T(m.v4GroupName, sora(13f, W.Semibold), maxLines = 1)
            }
            Knob(m)
            T("Dra rundt knotten · trykk utenfor for å lukke", sora(13f, W.Regular, C.body))
        }
    }
}

@Composable
private fun Knob(m: AppModel) {
    val vol = m.v4GroupVol
    Box(
        Modifier.size(310.dp)
            .semantics { contentDescription = "Volum"; stateDescription = "$vol" }
            .pointerInput(Unit) {
                awaitEachGesture {
                    fun upd(p: Offset) {
                        val dx = p.x - size.width / 2f; val dy = p.y - size.height / 2f
                        val a = (Math.toDegrees(atan2(dx.toDouble(), (-dy).toDouble()))).coerceIn(-150.0, 150.0)
                        val n = ((a + 150) / 3).roundToInt()
                        if (n != m.v4GroupVol) { Haptics.tick(); m.v4SetGroupVol(n) }
                    }
                    val down = awaitFirstDown(requireUnconsumed = false)
                    down.consume()
                    upd(down.position)
                    drag(down.id) { c -> upd(c.position); c.consume() }
                }
            },
        contentAlignment = Alignment.Center,
    ) {
        val lit = (vol / 100.0 * 30).roundToInt()
        Canvas(Modifier.fillMaxSize()) {
            val c = Offset(size.width / 2, size.height / 2)
            val u = 1.dp.toPx()
            // 31 streker på en sirkel med radius 140
            for (i in 0..30) {
                val on = i <= lit && vol > 0
                val tip = i == lit
                val h = (if (tip) 24f else 15f) * u
                val w = 5f * u
                val col = if (on) (if (tip) hex(0xfff3d6) else PlayerColors.gold) else C.ink.copy(alpha = 0.16f)
                rotate(-150f + i * 10f, c) {
                    val tl = Offset(c.x - w / 2, c.y - 140f * u - h / 2)
                    if (on) drawRoundRect(PlayerColors.gold.copy(alpha = 0.22f), tl - Offset(3f * u, 3f * u), Size(w + 6f * u, h + 6f * u), CornerRadius(6f * u))
                    drawRoundRect(col, tl, Size(w, h), CornerRadius(3f * u))
                }
            }
            // selve knotten: 200, radialgradient fra øvre venstre
            val r = 100f * u
            drawCircle(Color.Black.copy(alpha = 0.35f), r + 6f * u, c + Offset(0f, 18f * u))
            drawCircle(
                Brush.radialGradient(
                    listOf(hex(0x3c3c3f), hex(0x1a1a1c), hex(0x0d0d0e)),
                    center = Offset(c.x - r + 2 * r * 0.36f, c.y - r + 2 * r * 0.28f), radius = 140f * u,
                ),
                r, c,
            )
            drawArc(
                Brush.verticalGradient(listOf(Color.White.copy(alpha = 0.14f), Color.Transparent), startY = c.y - r, endY = c.y),
                180f, 180f, false, Offset(c.x - r, c.y - r), Size(2 * r, 2 * r), style = Stroke(1f * u),
            )
            // viseren: 5 × 30, 14 inn fra kanten
            rotate(-150f + vol * 3f, c) {
                drawRoundRect(C.ink, Offset(c.x - 2.5f * u, c.y - r + 14f * u), Size(5f * u, 30f * u), CornerRadius(3f * u))
            }
        }
        Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(2.dp)) {
            T("$vol", sora(56f, W.Light).copy(letterSpacing = (-0.03f).em))
            T("VOLUM", mono(10f, C.muted, 0.14f))
        }
    }
}
