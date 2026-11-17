package no.kristo.skjold

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.SizeTransform
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.asPaddingValues
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Paint
import androidx.compose.ui.graphics.Shadow
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.drawIntoCanvas
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalViewConfiguration
import androidx.compose.ui.platform.ViewConfiguration
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import kotlinx.serialization.builtins.serializer
import kotlin.math.PI
import kotlin.math.atan2
import kotlin.math.roundToInt

/*
 * v4-dokken, som V4Dock.swift og skallet i V4Root.swift på iOS:
 *  - telefon: minispilleren (tabViewBottomAccessory: omslag 34, tittel, «gruppe · artist», spill/pause med
 *    fremdriftsring) over fanelinjen med linse; ved rulling nedover slås dokken sammen til en rund faneknapp
 *    og en innfelt minispiller (omslag 28, bare tittel, ring 32).
 *  - brett/nettbrett (≥ 600 dp, iPad på iOS): fanene som kapsel øverst (V4TopNav) og minispilleren nederst.
 *  - hold 450 ms på minispilleren = volumknotten (V4VolumeDial), med hintboblen første gang.
 * Liquid Glass finnes ikke på Android: flatene er iOS-ens glasslag uten systemglass (topp-gradient, kantlys og
 * skygge fra v4Glass før iOS 26-glasset) over en tett, mørk, gjennomskinnelig flate.
 */

/** UI-tilstand for dokken (V4State.col / dial / hint / lastY på iOS). */
object DockUi {
    private const val HINT_KEY = "skjold-v4-hint-seen"

    /** Sammenslått dokk (fanelinjen minimert ved rulling). */
    var col by mutableStateOf(false)
    /** Volumknotten er åpen. */
    var dial by mutableStateOf(false)
    /** «Hold på minispilleren for volumknotten» – vises til den er sett én gang (samme nøkkel som iOS). */
    var hint by mutableStateOf(!(Store.load(HINT_KEY, Boolean.serializer()) ?: false))
    private var lastY = 0f

    fun hideHint() {
        if (!hint) return
        hint = false
        Store.save(HINT_KEY, true, Boolean.serializer())
    }

    /** onScr: slå sammen ved rulling nedover forbi 60, fold ut ved rulling opp > 4 eller nær toppen (y i dp). */
    fun scrolled(y: Float) {
        val d = y - lastY
        lastY = y
        var c = col
        if (y > 60f && d > 0f) c = true else if (d < -4f || y < 20f) c = false
        if (c != col) col = c
    }
}

/** Fremdrift 0…1 for ringen (radio = full ring), som v4Progress på iOS. */
val AppModel.dockProgress: Float
    get() {
        if (!hasProgress || duration <= 0) return if (input == 3) 1f else 0f
        return (position.toFloat() / duration).coerceIn(0f, 1f)
    }

/** Fanevalg (pickTab på iOS): lukker det som ligger over fanene og Nå spilles. */
fun dockPick(m: AppModel, i: Int) {
    if (i != m.tab) Haptics.tick()
    m.roomSortOpen = false; m.libPl = null; m.sub = ""
    m.full = false
    m.tab = i
    if (i == 3) m.setCat = -1
}

// MARK: - Mål og farger (V4Tokens.swift)

private val Gold = hex(0xf0c46a)
private val TabIdle = hex(0xe4e4df)
private val Sub = hex(0xd0d0cb)
/** Den mørke, gjennomskinnelige flaten som erstatter Liquid Glass. */
private val GlassBase = hex(0x1c1c1e, 0.88f)
private val BarH = 64.dp
private val AccH = 48.dp
private val Gap = 8.dp
/** SKTabBar: 18 over, indikator 32, 4, etikett ~17, 18 under (litt høyere enn før – lettere å treffe). */
private val TabBarH = 89.dp
private val LensEase = CubicBezierEasing(0.3f, 1.35f, 0.45f, 1f)
private val PanelEase = CubicBezierEasing(0.2f, 0.7f, 0.2f, 1f)

/** Avstand fra skjermkanten til dokken (iOS: 28 fra bunnen, men aldri oppå Androids navigasjonslinje). */
@Composable
private fun dockBottom(): Dp {
    val nav = WindowInsets.navigationBars.asPaddingValues().calculateBottomPadding()
    return maxOf(28.dp, nav + 6.dp)
}

/** Hvor mye plass sidene må ha under innholdet så det kan rulles fri av dokken. */
@Composable
fun dockContentInset(wide: Boolean): Dp =
    if (wide) AccH + 22.dp + WindowInsets.navigationBars.asPaddingValues().calculateBottomPadding()
    else AccH + 8.dp + TabBarH + WindowInsets.navigationBars.asPaddingValues().calculateBottomPadding()

// MARK: - Glassflate

/**
 * v4Glass: fyll (mørk base + hvit gradient topp → bunn), kantlys 1 px (gradient) og myk skygge under.
 * `radius` = null gir kapsel/sirkel.
 */
private fun Modifier.dockGlass(
    radius: Dp? = null, base: Color? = GlassBase, top: Float = 0.13f, bottom: Float = 0.05f,
    highlight: Float = 0.45f, edge: Float = 0.12f, shadowR: Dp = 17.dp, shadowY: Dp = 12.dp, shadowA: Float = 0.5f,
): Modifier {
    val shape = if (radius == null) RoundedCornerShape(50) else RoundedCornerShape(radius)
    return this
        .drawBehind { dockShadow(radius, shadowR, shadowY, shadowA) }
        .clip(shape)
        .then(if (base != null) Modifier.background(base, shape) else Modifier)
        .background(Brush.verticalGradient(listOf(Color.White.copy(alpha = top), Color.White.copy(alpha = bottom))), shape)
        .border(1.dp, Brush.verticalGradient(listOf(Color.White.copy(alpha = highlight), Color.White.copy(alpha = edge))), shape)
}

/** Skygge som CSS box-shadow (setShadowLayer; tegnes fra Android 9, eldre versjoner får ingen skygge). */
private fun DrawScope.dockShadow(radius: Dp?, blur: Dp, dy: Dp, alpha: Float) {
    val r = radius?.toPx() ?: (size.minDimension / 2)
    drawIntoCanvas { c ->
        val p = Paint().asFrameworkPaint()
        p.isAntiAlias = true
        p.color = android.graphics.Color.TRANSPARENT
        p.setShadowLayer(blur.toPx(), 0f, dy.toPx(), Color.Black.copy(alpha = alpha).toArgb())
        c.nativeCanvas.drawRoundRect(0f, 0f, size.width, size.height, r, r, p)
    }
}

/** Hold-tid 450 ms (onLongPressGesture(minimumDuration: 0.45) på iOS). */
private class DockLongPress(base: ViewConfiguration) : ViewConfiguration by base {
    override val longPressTimeoutMillis: Long get() = 450L
}

// MARK: - Telefon: dokken

/**
 * Dokken nederst på telefon, Android-variant: minispilleren (samme innhold som iOS) som et flatt kort over Androids
 * heldekkende fanelinje (SKTabBar: #161618, pilleindikator 64 × 32). Ingen Liquid Glass-kopi og ingen sammenslåing.
 */
@Composable
fun BoxScope.DockV4(m: AppModel) {
    Column(Modifier.align(Alignment.BottomCenter).fillMaxWidth()) {
        DockMini(m, inline = false, Modifier.fillMaxWidth().padding(start = SkG.miniM, end = SkG.miniM, bottom = 8.dp))
        SKTabBar(m.tab.coerceIn(0, 3)) { dockPick(m, it) }
    }
}

@Composable
private fun dockTabs(): List<Pair<String, String>> = listOf(
    stringResource(R.string.tab_home) to Icons.tabHome, stringResource(R.string.tab_sound) to Icons.tabSound,
    stringResource(R.string.tab_rooms) to Icons.tabRooms, stringResource(R.string.tab_settings) to Icons.tabSettings,
)

/**
 * Minispilleren (V4MiniAccessory): utvidet 48 høy med omslag 34 r9, tittel 14/600 og «gruppe · artist» 11,
 * ring 38; innfelt omslag 28 r7, tittel 13/600, ring 32. Trykk = Nå spilles, hold 450 ms = volumknotten.
 */
@Composable
private fun DockMini(m: AppModel, inline: Boolean, modifier: Modifier) {
    val np = m.np
    val base = LocalViewConfiguration.current
    val vc = remember(base) { DockLongPress(base) }
    CompositionLocalProvider(LocalViewConfiguration provides vc) {
        Row(
            modifier.height(AccH)
                .then(if (inline) Modifier.dockGlass() else Modifier.shadow(8.dp, RoundedCornerShape(SkG.miniR)).clip(RoundedCornerShape(SkG.miniR)).background(SkG.miniBg))
                .pointerInput(Unit) {
                    detectTapGestures(
                        onTap = { Haptics.thump(); m.full = true },
                        onLongPress = { Haptics.thump(); DockUi.hideHint(); DockUi.dial = true },
                    )
                }
                .semantics { contentDescription = "Spiller nå: ${np.t}" }
                .padding(start = if (inline) 6.dp else 8.dp, end = 4.dp),
            verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            val s = if (inline) 28.dp else 34.dp
            ArtFill(m.playerArt.key, Modifier.size(s).clip(RoundedCornerShape(if (inline) 7.dp else 9.dp)))
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(1.dp)) {
                T(np.t, sora(if (inline) 13f else 14f, W.Semibold), maxLines = 1)
                if (!inline) T(m.v4GroupName + " · " + np.s, sora(11f, W.Regular, Sub), maxLines = 1)
            }
            DockRingPlay(m, if (inline) 32.dp else 38.dp)
        }
    }
}

/** Spill/pause med fremdriftsring (strek 3, spor ink .18, fremdrift #f0c46a, 1 s lineær). */
@Composable
private fun DockRingPlay(m: AppModel, size: Dp) {
    val prog by animateFloatAsState(m.dockProgress, tween(1000, easing = LinearEasing), label = "ring")
    Box(
        Modifier.size(size).clip(CircleShape).press(label = "Spill/pause") { m.togglePlay() },
        contentAlignment = Alignment.Center,
    ) {
        Canvas(Modifier.fillMaxSize()) {
            val sw = 3.dp.toPx(); val inset = 1.5.dp.toPx()
            drawCircle(Color.Black.copy(alpha = 0.25f))
            drawCircle(C.ink.copy(alpha = 0.18f), radius = this.size.minDimension / 2 - inset, style = Stroke(sw))
            if (prog > 0f) drawArc(
                Gold, -90f, 360f * prog, false, Offset(inset, inset), Size(this.size.width - 2 * inset, this.size.height - 2 * inset),
                style = Stroke(sw, cap = StrokeCap.Round),
            )
        }
        SKIcon(if (m.playing) Icons.pause else Icons.playRound, 18.dp, color = C.ink, fill = true)
    }
}

/** Fanelinjen: 64 høy kapsel, linse (100 % − 10) / 4 × 54 som glir med fjærende overskyting. */
@Composable
private fun DockTabBar(m: AppModel) {
    val tabs = dockTabs()
    BoxWithConstraints(
        Modifier.fillMaxWidth().height(BarH).dockGlass()
            .drawBehind {
                // toppglans: 22 høy, 23 inn fra sidene, hvit .16 → 0
                val inset = 23.dp.toPx(); val h = 22.dp.toPx()
                drawRoundRect(
                    Brush.verticalGradient(listOf(Color.White.copy(alpha = 0.16f), Color.Transparent), startY = 1.dp.toPx(), endY = 1.dp.toPx() + h),
                    Offset(inset, 1.dp.toPx()), Size(size.width - 2 * inset, h), CornerRadius(h / 2),
                )
            },
    ) {
        val w = (maxWidth - 10.dp) / 4
        val x by animateDpAsState(5.dp + w * m.tab.coerceIn(0, 3), tween(500, easing = LensEase), label = "lens")
        Box(
            Modifier.offset(x = x, y = 5.dp).size(w, 54.dp)
                .dockGlass(base = null, top = 0.2f, bottom = 0.07f, highlight = 0.55f, edge = 0.14f, shadowR = 7.dp, shadowY = 4.dp, shadowA = 0.3f),
        )
        Row(Modifier.fillMaxSize().padding(5.dp)) {
            tabs.forEachIndexed { i, t ->
                val on = m.tab == i
                val col by animateColorAsState(if (on) Gold else TabIdle, tween(250), label = "tabc")
                val sc by animateFloatAsState(if (on) 1.04f else 1f, tween(250), label = "tabs")
                Column(
                    Modifier.weight(1f).fillMaxHeight().press(label = t.first) { dockPick(m, i) }
                        .graphicsLayer { scaleX = sc; scaleY = sc },
                    horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center,
                ) {
                    SKIcon(t.second, 22.dp, 1.8f, col)
                    Spacer(Modifier.height(3.dp))
                    T(t.first, sora(10f, W.Semibold, col).copy(shadow = Shadow(Color.Black.copy(alpha = 0.4f), Offset(0f, 2f), 3f)), maxLines = 1)
                }
            }
        }
    }
}

// MARK: - Brett/nettbrett

/** Fanene som sentrert kapsel øverst (V4TopNav): 46 høy, knapper 38 høye, valgt = hvit .16 og gull tekst. */
@Composable
fun DockTopNav(m: AppModel) {
    Box(Modifier.fillMaxWidth().padding(top = 4.dp), contentAlignment = Alignment.Center) {
        Row(
            Modifier.height(46.dp)
                .dockGlass(top = 0.18f, bottom = 0.06f, shadowR = 9.dp, shadowY = 6.dp, shadowA = 0.35f)
                .padding(4.dp),
            horizontalArrangement = Arrangement.spacedBy(2.dp), verticalAlignment = Alignment.CenterVertically,
        ) {
            dockTabs().forEachIndexed { i, t ->
                val on = m.tab == i
                val bg by animateColorAsState(if (on) Color.White.copy(alpha = 0.16f) else Color.Transparent, tween(200), label = "navbg")
                val fg by animateColorAsState(if (on) Gold else TabIdle, tween(200), label = "navfg")
                Box(
                    Modifier.height(38.dp).clip(CircleShape).background(bg).press { dockPick(m, i) }.padding(horizontal = 18.dp),
                    contentAlignment = Alignment.Center,
                ) { T(t.first, sora(14f, W.Semibold, fg), maxLines = 1) }
            }
        }
    }
}

/** Minispilleren nederst på brett/nettbrett (tilbehøret under innholdet). */
@Composable
fun BoxScope.DockWideMini(m: AppModel) {
    val nav = WindowInsets.navigationBars.asPaddingValues().calculateBottomPadding()
    Box(
        Modifier.align(Alignment.BottomCenter).fillMaxWidth().padding(start = 20.dp, end = 20.dp, bottom = nav + 22.dp),
        contentAlignment = Alignment.Center,
    ) { DockMini(m, inline = false, Modifier.widthIn(max = 640.dp).fillMaxWidth()) }
}

// MARK: - Hint og volumknott

/** «Hold på minispilleren for volumknotten»: 32 høy kapsel #2c2c30 .85, kant hvit .12, 150 over bunnen. */
@Composable
fun BoxScope.DockHint() {
    val nav = WindowInsets.navigationBars.asPaddingValues().calculateBottomPadding()
    Box(
        Modifier.align(Alignment.BottomCenter).padding(bottom = nav + 150.dp).height(32.dp)
            .clip(CircleShape).background(hex(0x2c2c30, 0.85f)).skCapsuleBorder(Color.White.copy(alpha = 0.12f))
            .padding(horizontal = 14.dp),
        contentAlignment = Alignment.Center,
    ) { T("Hold på minispilleren for volumknotten", sora(12f), maxLines = 1) }
}

/** Volumknotten (V4VolumeDial): 31 streker over 300°, knott 200, viser 270°-vinkel = gruppevolumet. */
@Composable
fun DockVolumeDial(m: AppModel) {
    val vol = m.v4GroupVol
    Box(
        Modifier.fillMaxSize().background(hex(0x050506, 0.78f))
            .clickable(remember { MutableInteractionSource() }, null) { DockUi.dial = false },
        contentAlignment = Alignment.Center,
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(26.dp)) {
            Row(
                Modifier.height(34.dp).clip(CircleShape).background(hex(0x28282a, 0.7f)).skCapsuleBorder(Color.White.copy(alpha = 0.12f))
                    .padding(horizontal = 14.dp),
                verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Box(Modifier.size(6.dp).clip(CircleShape).background(C.ok))
                T(m.v4GroupName, sora(13f, W.Semibold), maxLines = 1)
            }
            DialKnob(m, vol)
            T("Dra rundt knotten · trykk utenfor for å lukke", sora(13f, W.Regular, C.body))
        }
    }
}

@Composable
private fun DialKnob(m: AppModel, vol: Int) {
    val lit = (vol / 100.0 * 30).roundToInt()
    fun set(p: Offset, half: Float) {
        val dx = p.x - half; val dy = p.y - half
        val a = (atan2(dx, -dy) * 180 / PI).toFloat().coerceIn(-150f, 150f)
        val n = ((a + 150f) / 3f).roundToInt()
        if (n != m.v4GroupVol) { Haptics.tick(); m.v4SetGroupVol(n) }
    }
    Box(
        Modifier.size(310.dp).clip(CircleShape)
            .pointerInput(Unit) {
                val half = size.width / 2f
                detectTapGestures(onPress = { set(it, half) })
            }
            .pointerInput(Unit) {
                val half = size.width / 2f
                detectDragGestures(onDragStart = { set(it, half) }) { c, _ -> c.consume(); set(c.position, half) }
            }
            .semantics { contentDescription = "Volum $vol" },
        contentAlignment = Alignment.Center,
    ) {
        // strekene rundt (r 140)
        Canvas(Modifier.fillMaxSize()) {
            val cx = size.width / 2; val cy = size.height / 2
            val w = 5.dp.toPx()
            for (i in 0..30) {
                val on = i <= lit && vol > 0
                val tip = i == lit
                val h = (if (tip) 24 else 15).dp.toPx()
                val col = if (on) (if (tip) hex(0xfff3d6) else Gold) else C.ink.copy(alpha = 0.16f)
                rotate(-150f + i * 10f, Offset(cx, cy)) {
                    val top = cy - 140.dp.toPx() - h / 2
                    if (on) drawRoundRect(Gold.copy(alpha = 0.22f), Offset(cx - w / 2 - 3.dp.toPx(), top - 3.dp.toPx()),
                        Size(w + 6.dp.toPx(), h + 6.dp.toPx()), CornerRadius(6.dp.toPx()))
                    drawRoundRect(col, Offset(cx - w / 2, top), Size(w, h), CornerRadius(3.dp.toPx()))
                }
            }
        }
        // knotten (200, radialgradient, skygge .7 r25 y24, kantlys øverst)
        Box(
            Modifier.size(200.dp)
                .drawBehind { dockShadow(null, 25.dp, 24.dp, 0.7f) }
                .drawBehind {
                    drawCircle(
                        Brush.radialGradient(
                            listOf(hex(0x3c3c3f), hex(0x1a1a1c), hex(0x0d0d0e)),
                            center = Offset(size.width * 0.36f, size.height * 0.28f), radius = 140.dp.toPx(),
                        ),
                    )
                    drawCircle(
                        Brush.verticalGradient(listOf(Color.White.copy(alpha = 0.14f), Color.Transparent), endY = size.height / 2),
                        radius = size.minDimension / 2 - 0.5.dp.toPx(), style = Stroke(1.dp.toPx()),
                    )
                },
        )
        // viseren (5 × 30, senter 71 fra midten)
        Box(Modifier.size(310.dp).rotate(-150f + vol * 3f), contentAlignment = Alignment.Center) {
            Box(Modifier.offset(y = (-71).dp).size(5.dp, 30.dp).clip(RoundedCornerShape(3.dp)).background(C.ink))
        }
        Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(2.dp)) {
            T("$vol", sora(56f, W.Light).copy(letterSpacing = (-0.03f).em, lineHeight = 1.0f.em), maxLines = 1)
            T("VOLUM", mono(10f, C.muted, 0.14f))
        }
    }
}

// MARK: - Sidetitler (V4Title og titlene i V4SoundTab / V4RoomsTab / V4SettingsTab)

/** Sidetittel: Sora 32 / 600, −0.02 em. */
@Composable
fun DockTitle(text: String, modifier: Modifier = Modifier) =
    T(text, sora(32f, W.Semibold).copy(letterSpacing = (-0.02f).em), modifier, maxLines = 1)

/** Tett mørk kapsel med tynn kant og lys toppkant (v4DarkPill). */
private fun Modifier.dockDarkPill(): Modifier = this
    .clip(CircleShape).background(hex(0x28282a, 0.6f))
    .border(1.dp, Color.White.copy(alpha = 0.1f), CircleShape)
    .drawBehind {
        val r = size.height / 2
        drawRoundRect(
            Brush.verticalGradient(listOf(Color.White.copy(alpha = 0.1f), Color.Transparent), endY = size.height / 2),
            Offset(0.5.dp.toPx(), 0.5.dp.toPx()), Size(size.width - 1.dp.toPx(), size.height - 1.dp.toPx()), CornerRadius(r), style = Stroke(1.dp.toPx()),
        )
    }

/** Tittelraden øverst i en fane (rulles bort med innholdet, som på iOS). Hjem tegner sin egen (HomeView). */
@Composable
fun DockTitleRow(m: AppModel, tab: Int) {
    when (tab) {
        0 -> {
            val t = if (m.sub == "radio") "Radio" else if (m.sub == "lib") SK.lib[m.lib]?.name else null
            if (t != null) DockTitle(t)
        }
        1 -> Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            DockTitle("Lyd", Modifier.weight(1f))
            Row(
                Modifier.height(36.dp).dockDarkPill().padding(horizontal = 14.dp),
                verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Box(Modifier.size(6.dp).clip(CircleShape).background(C.ok))
                T(m.v4GroupName, sora(13f), maxLines = 1)
            }
        }
        2 -> Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            DockTitle("Rom", Modifier.weight(1f))
            RoomsHeaderButtons(m)
        }
        else -> if (m.setCat < 0 || m.setCat >= m.cats.size) {
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                DockTitle("Innstillinger")
                val r = m.devRoom
                val v = m.devRoomStatus?.version ?: ""
                val sub = listOf(r.name, SK.dev(r.type).n, v.ifEmpty { m.upd.version }).filter { it.isNotEmpty() }.joinToString(" · ")
                T(sub, mono(11f, C.muted), maxLines = 1)
            }
        }
    }
}

/** Kurven for Nå spilles inn/ut (V4.panel: 0.45 s, cubic-bezier(.2,.7,.2,1)). */
internal val DockPanelEase = PanelEase
