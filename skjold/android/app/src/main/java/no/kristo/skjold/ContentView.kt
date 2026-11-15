package no.kristo.skjold

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.fadeIn
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeOut
import androidx.compose.animation.scaleOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
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
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBars
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
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.withFrameMillis
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.foundation.layout.heightIn
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.platform.LocalDensity
import kotlinx.coroutines.delay
import kotlin.math.max
import kotlin.math.min

/** Root: dark background edge to edge, intro on top, then welcome → setup → app. */
@Composable
fun ContentView(m: AppModel) {
    Box(Modifier.fillMaxSize().background(C.bg)) {
        when (m.mode) {
            Mode.ONBOARD -> Box(Modifier.fillMaxSize().windowInsetsPadding(WindowInsets.systemBars).imePadding()) {
                if (m.welcome) WelcomeView(m) else OnboardingView(m)
            }
            Mode.APP -> AppShell(m)
        }
        if (m.mode == Mode.APP) Banner(m)
        WhatsNewOverlay(m)
        AnimatedVisibility(m.intro, enter = androidx.compose.animation.EnterTransition.None, exit = fadeOut(tween(300)) + scaleOut(tween(300), targetScale = 1.04f)) {
            IntroView(m)
        }
    }
    // system back: close the player, leave sub pages, step back in setup
    BackHandler(enabled = DockUi.dial || m.full || m.sub.isNotEmpty() || m.setCat >= 0 || m.libPl != null || m.rAdd || (m.mode == Mode.ONBOARD && (m.ob > 0 || m.scan || !m.welcome))) {
        when {
            DockUi.dial -> DockUi.dial = false
            m.full -> m.full = false
            m.mode == Mode.ONBOARD -> if (m.ob > 0 || m.scan) m.obBack() else if (m.known.isEmpty() && !m.welcome && m.ob == 0) m.welcome = true
            m.rAdd -> m.rAdd = false
            m.libPl != null -> m.libPl = null
            m.sub.isNotEmpty() -> m.sub = ""
            m.setCat >= 0 -> { m.setCat = -1; m.openK = "" }
        }
    }
}

/**
 * Hovedskallet (V4App på iOS): fanene, dokken (minispiller + fanelinje med linse, sammenslått ved rulling), hintboblen,
 * arkene, Nå spilles og volumknotten. Brett/nettbrett (≥ 600 dp, iPad på iOS): fanene som kapsel øverst og
 * minispilleren nederst, Nå spilles som panel (400) fra høyre.
 */
@Composable
fun AppShell(m: AppModel) {
    BoxWithConstraints(Modifier.fillMaxSize()) {
        val wide = maxWidth >= 600.dp
        val panelW = 400.dp
        // Fanene ligger under Nå spilles (rulleposisjonene beholdes); de skjules først når panelet har glidd helt inn.
        val shown by animateFloatAsState(
            if (m.full && !wide) 0f else 1f,
            if (m.full && !wide) tween(1, delayMillis = 450) else tween(0), label = "tabs",
        )
        Box(Modifier.fillMaxSize().alpha(shown)) {
            if (wide) {
                Column(Modifier.fillMaxSize().windowInsetsPadding(WindowInsets.statusBars)) {
                    DockTopNav(m)
                    Box(Modifier.weight(1f).imePadding()) { if (SourceUi.active) SourceOverlays(m, true) else Page(m, m.tab, true) }
                }
                DockWideMini(m)
            } else {
                Box(Modifier.fillMaxSize().windowInsetsPadding(WindowInsets.statusBars).imePadding()) { if (SourceUi.active) SourceOverlays(m, false) else Page(m, m.tab, false) }
                DockV4(m)
            }
            // «Hold på minispilleren for volumknotten» (første gang, på Hjem)
            AnimatedVisibility(
                DockUi.hint && m.tab == 0 && !m.full && !wide && m.sub.isEmpty() && !DockUi.dial,
                Modifier.align(Alignment.BottomCenter).fillMaxWidth(),
                enter = fadeIn(tween(250)), exit = fadeOut(tween(250)),
            ) { Box(Modifier.fillMaxWidth().height(300.dp)) { DockHint() } }
        }
        // søket (V4SearchPage) ligger over fanene og dokken; tegner ingenting når det er lukket
        SearchPage(m)
        if (m.hjemLogin) HjemLoginView(m)
        if (m.showRoomEQ) RoomEQView(m)
        if (m.showKassett) KassettView(m)
        if (m.showSpeakers) SpeakerView(m)
        if (wide) {
            // dempelag rgba(0,0,0,.45) bak panelet; trykk lukker
            AnimatedVisibility(m.full, enter = fadeIn(tween(450, easing = DockPanelEase)), exit = fadeOut(tween(450, easing = DockPanelEase))) {
                Box(Modifier.fillMaxSize().background(Color.Black.copy(alpha = 0.45f)).clickable(remember { MutableInteractionSource() }, null) { m.full = false })
            }
            AnimatedVisibility(
                m.full, modifier = Modifier.align(Alignment.CenterEnd),
                enter = slideInHorizontally(tween(450, easing = DockPanelEase)) { (it * 1.05f).toInt() },
                exit = slideOutHorizontally(tween(450, easing = DockPanelEase)) { (it * 1.05f).toInt() },
            ) {
                Box(Modifier.width(panelW).fillMaxHeight()) {
                    FullPlayerView(m)
                    Box(Modifier.width(1.dp).fillMaxHeight().background(Color.White.copy(alpha = 0.08f)))
                }
            }
        } else {
            AnimatedVisibility(
                m.full,
                enter = slideInVertically(tween(450, easing = DockPanelEase)) { (it * 1.04f).toInt() },
                exit = slideOutVertically(tween(450, easing = DockPanelEase)) { (it * 1.04f).toInt() },
            ) { FullPlayerView(m) }
        }
        AnimatedVisibility(DockUi.dial, enter = fadeIn(tween(250)), exit = fadeOut(tween(250))) { DockVolumeDial(m) }
    }
    // Radio og bibliotekene åpnes som kildesider (V4SourcePage), også når noe fortsatt setter m.sub
    LaunchedEffect(m.sub, m.lib) {
        when (m.sub) {
            "radio" -> { m.sub = ""; m.openSource("Radio") }
            "lib" -> { m.sub = ""; m.openSource(SK.lib[m.lib]?.name ?: "Navidrome") }
        }
    }
    // hintet forsvinner for godt etter 4,5 s
    LaunchedEffect(Unit) {
        delay(4500)
        DockUi.hideHint()
    }
}

/** Én fane: rullbar side (padding 20 / 6, brett 40 / 24 og maks 860 bred), tittelraden øverst og 22 mellom delene. */
@Composable
private fun Page(m: AppModel, tab: Int, wide: Boolean) {
    val inset = dockContentInset(wide)
    val density = LocalDensity.current.density
    // ny rulleposisjon når siden som vises endres
    key("$tab-${m.sub}-${m.lib}-${m.setCat}-${m.libPl ?: -1}") {
        val scroll = rememberScrollState()
        if (!wide) LaunchedEffect(scroll) {
            snapshotFlow { scroll.value }.collect { DockUi.scrolled(it / density) }
        }
        Column(
            Modifier.fillMaxSize().verticalScroll(scroll)
                .padding(start = if (wide) 40.dp else 20.dp, end = if (wide) 40.dp else 20.dp, top = if (wide) 24.dp else 6.dp, bottom = 40.dp + inset),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Column(
                (if (wide) Modifier.widthIn(max = 860.dp) else Modifier).fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(22.dp),
            ) {
                DockTitleRow(m, tab)
                when (tab) {
                    0 -> if (m.sub == "radio") RadioView(m) else if (m.sub == "lib") LibraryView(m) else HomeView(m)
                    1 -> SoundView(m)
                    2 -> RoomsView(m)
                    else -> SettingsView(m)
                }
            }
        }
    }
}

// MARK: - Intro (simplified port of IntroView.swift: lightning, flash, bars and the SKJOLD word mark, 4.7 s)

private fun ease(t: Float, dur: Float, delay: Float): Float {
    val x = ((t - delay) / dur).coerceIn(0f, 1f)
    // cubic-bezier(.2,.7,.2,1) approximated by an ease-out curve
    return 1f - (1f - x) * (1f - x) * (1f - x)
}

private fun keys(x: Float, k: List<Pair<Float, Float>>): Float {
    if (x <= k.first().first) return k.first().second
    for (i in 1 until k.size) if (x <= k[i].first) {
        val a = k[i - 1]; val b = k[i]
        return a.second + (b.second - a.second) * (x - a.first) / (b.first - a.first)
    }
    return k.last().second
}

@Composable
fun IntroView(m: AppModel) {
    var t by remember { mutableLongStateOf(0L) }
    LaunchedEffect(Unit) {
        val start = withFrameMillis { it }
        while (true) { val now = withFrameMillis { it }; t = now - start }
    }
    val s = t / 1000f
    val out = ease(s, 0.6f, 4.05f)
    BoxWithConstraints(
        Modifier.fillMaxSize().background(hex(0x060607)).graphicsLayer { alpha = 1f - out; scaleX = 1f + 0.04f * out; scaleY = 1f + 0.04f * out }
            .clickable(remember { MutableInteractionSource() }, null) { m.intro = false },
    ) {
        val w = constraints.maxWidth.toFloat(); val h = constraints.maxHeight.toFloat()
        Canvas(Modifier.fillMaxSize()) {
            // SVG 350×760, xMidYMax slice
            val sc = max(w / 350f, h / 760f)
            val ox = (w - 350f * sc) / 2f; val oy = h - 760f * sc
            fun layer(d: String, color: Color, p: Float, dy: Float) {
                if (p <= 0f) return
                drawContext.canvas.save()
                drawContext.transform.translate(ox, oy + dy * (1 - p) * sc)
                drawContext.transform.scale(sc, sc, Offset.Zero)
                drawPath(SvgPath.get(d), color.copy(alpha = color.alpha * p))
                drawContext.canvas.restore()
            }
            layer("M0 560 L40 500 L70 520 L120 430 L150 470 L190 400 L235 470 L262 445 L300 500 L350 470 L350 600 L0 600 Z", hex(0x10161b), ease(s, 1.4f, 0.05f), 24f)
            layer("M0 600 L30 560 L75 585 L110 520 L150 590 L0 600 Z M200 600 L245 535 L280 570 L320 525 L350 555 L350 600 Z", hex(0x0b0f12), ease(s, 1.4f, 0.2f), 24f)
            layer("M0 600 L30 640 L75 615 L110 680 L150 610 L0 600 Z M200 600 L245 665 L280 630 L320 675 L350 645 L350 600 Z", hex(0x0b0f12, 0.45f), ease(s, 1.2f, 0.4f), 6f)
            // lightning bolts
            for ((d, wd, delay) in listOf(Triple("M196 0 L184 92 L200 98 L172 196 L190 202 L160 300", 2.4f, 0.6f), Triple("M184 92 L160 140 L166 150 L150 190", 1.2f, 0.68f))) {
                if (s < delay) continue
                val x = ((s - delay) / 0.9f).coerceIn(0f, 1f)
                val op = keys(x, listOf(0f to 1f, 0.35f to 1f, 0.55f to 0.2f, 0.62f to 1f, 1f to 0f))
                if (op <= 0f) continue
                drawContext.canvas.save()
                drawContext.transform.translate(ox, oy)
                drawContext.transform.scale(sc, sc, Offset.Zero)
                drawPath(SvgPath.get(d), C.accent2.copy(alpha = 0.35f * op), style = Stroke(wd * 3f, join = StrokeJoin.Miter))
                drawPath(SvgPath.get(d), hex(0xfdf3d6).copy(alpha = op), style = Stroke(wd, join = StrokeJoin.Miter))
                drawContext.canvas.restore()
            }
            // flash
            if (s >= 0.78f) {
                val fx = ((s - 0.78f) / 0.9f).coerceIn(0f, 1f)
                val fo = keys(fx, listOf(0f to 0f, 0.12f to 0.75f, 0.3f to 0.1f, 0.38f to 0.5f, 1f to 0f))
                if (fo > 0f) drawRect(Brush.radialGradient(listOf(hex(0xfff6dc).copy(alpha = fo), C.accent2.copy(alpha = 0.4f * fo), Color.Transparent), Offset(w / 2, h * 0.3f), w * 0.7f))
            }
            // warm glow behind the mark
            val glow = ease(s, 1.8f, 0.85f)
            if (glow > 0f) drawCircle(Brush.radialGradient(listOf(C.accent.copy(alpha = 0.22f * glow), Color.Transparent), Offset(w / 2, h / 2 - 40 * density), 210 * density * (0.8f + 0.2f * glow)), 210 * density, Offset(w / 2, h / 2 - 40 * density))
        }
        Column(Modifier.align(Alignment.Center), horizontalAlignment = Alignment.CenterHorizontally) {
            val shake = ((s - 0.82f) / 0.35f).coerceIn(0f, 1f)
            val sx = if (s < 0.82f) 0f else keys(shake, listOf(0f to 0f, 0.2f to -2f, 0.4f to 2f, 0.6f to -1f, 1f to 0f))
            Row(Modifier.height(56.dp).offset(x = sx.dp, y = (-80).dp), verticalAlignment = Alignment.Bottom, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                listOf(26, 40, 56, 40, 26).forEachIndexed { i, hh ->
                    val d = 1.05f + i * 0.1f
                    val b = ease(s, 0.5f, d)
                    val inkT = ((ease(s, 1.6f, d) - 0.7f) / 0.3f).coerceIn(0f, 1f)
                    Box(
                        Modifier.width(7.dp).height(hh.dp).graphicsLayer {
                            scaleY = b; transformOrigin = androidx.compose.ui.graphics.TransformOrigin(0.5f, 1f)
                            alpha = if (s < d) 0f else min(1f, ((s - d) / 0.5f) / 0.6f)
                        }.clip(RoundedCornerShape(4.dp)).background(mix(C.accent, C.ink, inkT)),
                    )
                }
            }
            val word = ease(s, 1.3f, 1.6f)
            T("SKJOLD", sora(30f, W.Semibold).copy(letterSpacing = (0.9f - 0.66f * word).em), Modifier.padding(top = 30.dp).offset(y = (-80).dp).alpha(word))
            val line = ease(s, 1f, 2.4f)
            Box(
                Modifier.padding(top = 18.dp).offset(y = (-80).dp).width(150.dp).height(1.dp).graphicsLayer { scaleX = line; alpha = line }
                    .background(Brush.horizontalGradient(listOf(Color.Transparent, C.accent, Color.Transparent))),
            )
        }
    }
}

// MARK: - 01 Velkomst

@Composable
fun WelcomeView(m: AppModel) {
    Column(
        Modifier.fillMaxSize().padding(start = 20.dp, end = 20.dp, top = 8.dp, bottom = 18.dp),
        verticalArrangement = Arrangement.spacedBy(18.dp),
    ) {
        Box(Modifier.padding(top = 4.dp)) { SKLogo(barW = 3.dp, gap = 3.dp, size = 14f, tracking = 3f, bottomAligned = false, spacing = 10.dp) }
        HeroCarousel(m)
        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            SKMonoLabel("VELKOMMEN")
            T("Musikk i hvert rom", sora(28f, W.Semibold, lineHeight = 1.15f))
            T("Appen styrer Skjold S1 og Skjold Node. Velg kilde, juster lyden og samle rommene til ett system.", sora(13f, W.Regular, C.body, 1.5f))
        }
        Spacer(Modifier.weight(1f))
        SKButton("Legg til Skjold-enhet") { m.welcome = false }
        Box(Modifier.fillMaxWidth().padding(top = 2.dp), contentAlignment = Alignment.Center) {
            SKLinkButton("Hopp over og gå til appen") { m.skipSetup() }
        }
    }
}

/** heroView(): renders that cross-fade, with label and page dots. Only the S1 cut-out and the Node outline ship. */
@Composable
fun HeroCarousel(m: AppModel) {
    val slides = listOf(
        Triple("s1", "Skjold S1", "Forsterker med skjerm og knapper"), Triple("s1", "Skjold S1", "Forsterker med skjerm og knapper"),
        Triple("node", "Skjold Node", "Liten spiller for flere rom"), Triple("node", "Skjold Node", "Liten spiller for flere rom"),
    )
    val i = m.heroI % slides.size
    val cur = slides[i]
    BoxWithConstraints(Modifier.fillMaxWidth().height(250.dp)) {
        val w = maxWidth
        // warm glow behind the product
        Box(Modifier.fillMaxSize().background(Brush.radialGradient(listOf(C.accent.copy(alpha = 0.16f), C.accent.copy(alpha = 0.04f), Color.Transparent))))
        slides.forEachIndexed { j, sl ->
            val a by animateFloatAsState(if (j == i) 1f else 0f, tween(900), label = "hero")
            val dx by animateDpAsState(if (j == i) 0.dp else if (j < i) (-14).dp else 14.dp, tween(900), label = "herox")
            Box(Modifier.fillMaxSize().offset(x = dx).alpha(a).scale(0.97f + 0.03f * a), contentAlignment = Alignment.Center) {
                if (sl.first == "s1") HeroImage(Modifier.width(w * (230f / 330f)).offset(x = w * (103.3f / 330f) - w * 0.15f, y = (-6).dp))
                else SKIcon(SK.dev("node").icon, 150.dp, 0.5f, C.ink2, modifier = Modifier.offset(y = (-20).dp))
            }
        }
        Row(Modifier.align(Alignment.BottomStart).fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                T(cur.second, sora(14f, W.Semibold))
                T(cur.third, sora(12f, W.Regular, C.muted))
            }
            Row(horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                slides.indices.forEach { j ->
                    val ww by animateDpAsState(if (j == i) 18.dp else 6.dp, tween(300), label = "dot")
                    Box(Modifier.size(ww, 6.dp).clip(CircleShape).background(if (j == i) C.accent else C.off).press { m.restartHero(j) })
                }
            }
        }
    }
}

/** Øverst i appen: vekkeklokka som ringer (Slumre / Slå av), eller en kort beskjed fra enheten. */
@Composable
private fun androidx.compose.foundation.layout.BoxScope.Banner(m: AppModel) {
    val d = m.dev
    val ringing = d?.alarmRinging == true
    val notice = m.notice
    if (!ringing && notice == null) return
    Column(
        Modifier.align(Alignment.TopCenter).windowInsetsPadding(WindowInsets.statusBars).padding(horizontal = 14.dp, vertical = 6.dp).widthIn(max = 560.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp), horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        if (ringing && d != null) {
            Row(
                Modifier.fillMaxWidth().clip(RoundedCornerShape(20.dp)).background(C.card).skBorder(C.accent, 20.dp).padding(start = 16.dp, end = 10.dp, top = 10.dp, bottom = 10.dp),
                verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                Column(Modifier.weight(1f)) {
                    T("Alarmen ringer", sora(15f, W.Semibold))
                    T(if (d.alarmName.isEmpty()) d.name else d.alarmName + " · " + d.name, sora(12f, W.Regular, C.ink2), maxLines = 1)
                }
                Box(Modifier.heightIn(min = 44.dp).clip(CircleShape).background(C.accent2).press { m.devSend("/api/alarm", mapOf("action" to "snooze")) }.padding(horizontal = 16.dp), contentAlignment = Alignment.Center) {
                    T("Slumre", sora(14f, W.Semibold, C.bg))
                }
                Box(Modifier.heightIn(min = 44.dp).clip(CircleShape).skBorder(C.line2, 22.dp).press { m.devSend("/api/alarm", mapOf("action" to "stop")) }.padding(horizontal = 16.dp), contentAlignment = Alignment.Center) {
                    T("Slå av", sora(14f, W.Semibold))
                }
            }
        }
        if (notice != null) {
            Box(Modifier.clip(CircleShape).background(C.card).skBorder(C.line2, 24.dp).padding(horizontal = 16.dp, vertical = 11.dp)) {
                T(notice, sora(13f))
            }
        }
    }
}
