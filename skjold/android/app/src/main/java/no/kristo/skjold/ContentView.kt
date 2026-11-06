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
        WhatsNewOverlay(m)
        AnimatedVisibility(m.intro, enter = androidx.compose.animation.EnterTransition.None, exit = fadeOut(tween(300)) + scaleOut(tween(300), targetScale = 1.04f)) {
            IntroView(m)
        }
    }
    // system back: close the player, leave sub pages, step back in setup
    BackHandler(enabled = m.full || m.sub.isNotEmpty() || m.setCat >= 0 || m.libPl != null || m.rAdd || (m.mode == Mode.ONBOARD && (m.ob > 0 || m.scan || !m.welcome))) {
        when {
            m.full -> m.full = false
            m.mode == Mode.ONBOARD -> if (m.ob > 0 || m.scan) m.obBack() else if (m.known.isEmpty() && !m.welcome && m.ob == 0) m.welcome = true
            m.rAdd -> m.rAdd = false
            m.libPl != null -> m.libPl = null
            m.sub.isNotEmpty() -> m.sub = ""
            m.setCat >= 0 -> { m.setCat = -1; m.openK = "" }
        }
    }
}

/** Main app: tab content with the classic tab bar and mini player – plus the full-screen player. */
@Composable
fun AppShell(m: AppModel) {
    BoxWithConstraints(Modifier.fillMaxSize()) {
        // v4: brettbar (≥ 600) og nettbrett (≥ 1000) – faner i en kolonne til venstre, Nå spilles som panel fra høyre
        val wide = maxWidth >= 600.dp
        val panelW = if (maxWidth >= 1000.dp) 420.dp else 360.dp
        val pick: (Int) -> Unit = { i ->
            m.tab = i; m.sub = ""
            if (i == 3) m.setCat = -1
        }
        if (wide) {
            Row(Modifier.fillMaxSize()) {
                SKNavRail(m.tab, pick)
                Column(Modifier.weight(1f).fillMaxHeight()) {
                    Box(Modifier.weight(1f).windowInsetsPadding(WindowInsets.statusBars).imePadding()) {
                        Box(Modifier.fillMaxWidth().padding(horizontal = 8.dp)) { Page(m, m.tab) }
                    }
                    if (m.tab != 2) Box(
                        Modifier.fillMaxWidth().windowInsetsPadding(WindowInsets.navigationBars).padding(start = 12.dp, end = 12.dp, bottom = 14.dp),
                        contentAlignment = Alignment.Center,
                    ) { Box(Modifier.widthIn(max = 1000.dp)) { SKMiniPlayer(m) } }
                }
            }
        } else {
            // The tabs stay mounted under the player so scroll positions survive opening/closing it.
            Column(Modifier.fillMaxSize().alpha(if (m.full) 0f else 1f)) {
                Box(Modifier.weight(1f).windowInsetsPadding(WindowInsets.statusBars).imePadding()) { Page(m, m.tab) }
                if (m.tab != 2) SKMiniPlayer(m)   // v4: Rom-fanen har volum per rom og ingen minispiller
                SKTabBar(m.tab, pick)
            }
        }
        if (m.hjemLogin) HjemLoginView(m)
        if (m.showRoomEQ) RoomEQView(m)
        if (m.showKassett) KassettView(m)
        if (m.showSpeakers) SpeakerView(m)
        if (wide) {
            // dempelag rgba(0,0,0,.45) bak panelet; trykk lukker
            AnimatedVisibility(m.full, enter = fadeIn(tween(450)), exit = fadeOut(tween(300))) {
                Box(Modifier.fillMaxSize().background(Color.Black.copy(alpha = 0.45f)).clickable(remember { MutableInteractionSource() }, null) { m.full = false })
            }
            AnimatedVisibility(
                m.full, modifier = Modifier.align(Alignment.CenterEnd),
                enter = slideInHorizontally(tween(450, easing = CubicBezierEasing(0.2f, 0.7f, 0.2f, 1f))) { it },
                exit = slideOutHorizontally(tween(350)) { it },
            ) { Box(Modifier.width(panelW).fillMaxHeight()) { FullPlayerView(m) } }
        } else {
            AnimatedVisibility(m.full, enter = slideInVertically(tween(280)) { it }, exit = slideOutVertically(tween(280)) { it }) {
                FullPlayerView(m)
            }
        }
    }
}

/** Title + scrolling content for a tab. */
@Composable
private fun Page(m: AppModel, tab: Int) {
    val title: String? = when (tab) {
        0 -> if (m.sub == "radio") "Radio" else if (m.sub == "lib") SK.lib[m.lib]?.name else null
        1 -> "Lyd"
        2 -> "Rom"
        else -> if (m.setCat >= 0 && m.setCat < m.cats.size) m.cats[m.setCat].n else "Innstillinger"
    }
    Column(Modifier.fillMaxSize()) {
        if (tab == 2 && m.visSted) Box(Modifier.fillMaxWidth().padding(start = 20.dp, end = 20.dp, top = 6.dp, bottom = 8.dp)) { StedPicker(m, 32f) }
        else if (title != null) Row(Modifier.fillMaxWidth().padding(start = 20.dp, end = 20.dp, top = 6.dp, bottom = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            T(title, sora(32f, W.Semibold).copy(letterSpacing = (-0.02f).em), Modifier.weight(1f), maxLines = 1)
            // v4 Lyd: kapsel med gruppen som spiller (grønn prikk)
            if (tab == 1) Row(
                Modifier.height(36.dp).clip(RoundedCornerShape(18.dp)).background(SkG.pillBg).skBorder(SkG.pillLine, 18.dp).padding(horizontal = 14.dp),
                verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Box(Modifier.size(6.dp).clip(CircleShape).background(C.ok))
                T(m.groupName, sora(13f), maxLines = 1)
            }
        }
        // new scroll position when the visible page changes
        key("$tab-${m.sub}-${m.lib}-${m.setCat}-${m.libPl ?: -1}") {
            Column(
                Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(start = 20.dp, end = 20.dp, top = 10.dp, bottom = 16.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp),
            ) {
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

