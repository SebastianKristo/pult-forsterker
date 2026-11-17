package no.kristo.skjold

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.MutableTransitionState
import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.SideEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.compose.ui.window.DialogWindowProvider
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.launch

/*
 * Felles byggeklosser for Hjem (v4), som V4Tokens.swift på iOS: farger, ikoner, kildeikon, hylletittel, mosaikk,
 * spiller-stolper og stedsmenyen (V4HomeMenu). Liquid Glass blir heldekkende mørke flater på Android.
 */

/** Farger og ikoner fra V4Tokens.swift som Hjem trenger. */
object HomeV4 {
    val gold = hex(0xf0c46a)
    val goldDark = hex(0xd9a441)
    val green = hex(0x6fcf7f)
    val body = hex(0xa9a9a3)
    val muted = hex(0x8b8b86)
    val ink = hex(0xf2f2ee)
    val ink2 = hex(0xc9c9c4)
    val card2 = hex(0x151517)
    val line = hex(0x242426)
    val mosaicEmpty = hex(0x1b1b1d)
    /** Flytende meny (v4Menu): glass på iOS, heldekkende #26262a med tynn kant her. */
    val menuBg = SkG.menuBg

    const val search = "M11 18a7 7 0 1 0 0-14a7 7 0 1 0 0 14M20 20l-4-4"
    const val gear = "M12 15a3 3 0 1 0 0-6a3 3 0 1 0 0 6M12 2v3M12 19v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2 12h3M19 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1"
    const val chevDown = "M6 9l6 6 6-6"
    const val chevRight = "M9 6l6 6-6 6"
    const val plus = "M12 5v14M5 12h14"
    const val handle = "M5 8h14M5 12h14M5 16h14"
    const val home = "M3 11l9-7 9 7M5 10v10h5v-6h4v6h5V10"
    const val sted = "M3 20h18M5 20V11l7-6 7 6v9M10 20v-5h4v5"

    /** V4.chevron: easeInOut 0,2 s. */
    val easeInOut = CubicBezierEasing(0.42f, 0f, 0.58f, 1f)
}

/** Navn på bibliotekene (V4Lib.names). */
val HomeLibNames = mapOf("nd" to "Navidrome", "plex" to "Plex", "ytm" to "YouTube Music")

/** v4DarkPill: rgba(40,40,42,.6) + 1 px rgba(255,255,255,.1) + lys kant øverst (fallback for glasskapselen). */
fun Modifier.homeDarkPill(): Modifier = this
    .clip(CircleShape)
    .background(SkG.pillBg)
    .skCapsuleBorder(SkG.pillLine)
    .drawBehind {
        val w = 1.dp.toPx()
        drawRoundRect(
            Brush.verticalGradient(0f to Color.White.copy(alpha = 0.1f), 0.5f to Color.Transparent, endY = size.height),
            Offset(w / 2, w / 2), Size(size.width - w, size.height - w), CornerRadius(size.height / 2), style = Stroke(w),
        )
    }

/** Kildeikon i en sirkel med kant rgba(255,255,255,.08) (V4SourceIcon). */
@Composable
fun HomeSourceIcon(label: String, size: Dp) {
    val s = SourceLogos.style(label)
    Box(Modifier.size(size).clip(CircleShape), contentAlignment = Alignment.Center) {
        s.bg(Modifier.fillMaxSize())
        if (s.size > 0) {
            if (s.stroke.isNotEmpty()) SKIcon(s.stroke, size * s.size, 1.8f, s.fg)
            if (s.fillPath.isNotEmpty()) SKIcon(s.fillPath, size * s.size, color = s.fg, fill = true)
            if (s.brand.isNotEmpty()) SKIcon(s.brand, size * s.size, color = s.fg, fill = true)
        }
        Box(Modifier.fillMaxSize().skCapsuleBorder(Color.White.copy(alpha = 0.08f)))
    }
}

/** Omslag med avrundede hjørner og gull ring når den spiller (V4Art). */
@Composable
fun HomeArt(key: String, size: Dp, radius: Dp, ring: Dp = 0.dp) {
    Box(Modifier.size(size).clip(RoundedCornerShape(radius))) {
        ArtFill(art(key))
        if (ring > 0.dp) Box(Modifier.fillMaxSize().skBorder(HomeV4.gold, radius, ring))
    }
}

/** 2 × 2-mosaikk for spillelister (V4Mosaic). */
@Composable
fun HomeMosaic(keys: List<String>, size: Dp = 148.dp, radius: Dp = 14.dp) {
    // Bare ruter med ekte omslag. Færre enn fire (typisk YouTube Music: ett bilde per liste) → ett omslag over hele flisen.
    val ekte = keys.filter { it.isNotEmpty() && art(it).hasLogo }.distinct()
    if (ekte.size in 1..3) { HomeArt(ekte[0], size, radius); return }
    val k = (if (ekte.size >= 4) ekte else keys).take(4).let { it + List(maxOf(0, 4 - it.size)) { "" } }
    val cell = size / 2
    Column(Modifier.size(size).clip(RoundedCornerShape(radius))) {
        for (r in 0 until 2) Row {
            for (c in 0 until 2) {
                val key = k[r * 2 + c]
                Box(Modifier.size(cell).background(HomeV4.mosaicEmpty)) { if (key.isNotEmpty()) ArtFill(art(key)) }
            }
        }
    }
}

/** Seksjonstittel med strek under: kicker i mono, tittel i store bokstaver 15/700 og pil (V4ShelfHeader). */
@Composable
fun HomeShelfHeader(title: String, kicker: String = "", icon: String = "", action: (() -> Unit)? = null) {
    Row(
        Modifier.fillMaxWidth()
            .then(if (action != null) Modifier.press(label = "Åpner $title", onClick = action) else Modifier)
            .drawBehind { drawRect(Color.White.copy(alpha = 0.08f), Offset(0f, size.height - 1.dp.toPx()), Size(size.width, 1.dp.toPx())) }
            .padding(bottom = 10.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Row(Modifier.weight(1f), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(9.dp)) {
            if (icon.isNotEmpty()) HomeSourceIcon(icon, 20.dp)
            Column(verticalArrangement = Arrangement.spacedBy(1.dp)) {
                if (kicker.isNotEmpty()) T(kicker, mono(10f, HomeV4.muted, 0.12f))
                T(title.uppercase(), sora(15f, W.Semibold).copy(letterSpacing = 0.04f.em), maxLines = 1)
            }
        }
        if (action != null) SKIcon(HomeV4.chevRight, 18.dp, 2.2f, HomeV4.ink2)
    }
}

/** Spiller-indikator: tre gule stolper i en mørk kapsel (V4NowBars). */
@Composable
fun HomeNowBars(modifier: Modifier = Modifier) {
    Row(
        modifier.height(22.dp).clip(CircleShape).background(Color.Black.copy(alpha = 0.55f)).padding(start = 8.dp, end = 8.dp, bottom = 6.dp),
        verticalAlignment = Alignment.Bottom, horizontalArrangement = Arrangement.spacedBy(2.dp),
    ) {
        for (h in listOf(6, 10, 7)) Box(Modifier.size(2.5.dp, h.dp).clip(RoundedCornerShape(1.dp)).background(HomeV4.gold))
    }
}

/** Fjerner vinduets egen demping i en Dialog (vi tegner dempelaget selv, som på iOS). */
@Composable
fun HomeNoDialogDim() {
    val w = (LocalView.current.parent as? DialogWindowProvider)?.window
    SideEffect { w?.setDimAmount(0f) }
}

// MARK: - Stedsmenyen (V4HomeMenu)

/**
 * STEDER under tittelen på Hjem: «Hjemme» (dette nettverket), stedene fra Skjold-hjem og «Legg til sted».
 * Dempelag rgba(0,0,0,.35), menyen 270 bred, 16 fra venstre og 54 (brett 108) under toppen. Toner inn/ut på 0,2 s.
 */
@Composable
fun HomePlaceMenu(m: AppModel, open: Boolean, onClose: () -> Unit) {
    val vis = remember { MutableTransitionState(false) }
    vis.targetState = open
    if (!vis.currentState && !vis.targetState) return
    // valget av sted skal fullføres selv om menyen (eller Hjem) forsvinner, som Task {} på iOS
    val scope = m.viewModelScope
    // brett/nettbrett (≥ 600 dp, iPad på iOS): fanene ligger øverst, så menyen står lavere (108)
    val wide = LocalConfiguration.current.screenWidthDp >= 600
    LaunchedEffect(Unit) { m.loadSteder() }
    Dialog(onDismissRequest = onClose, properties = DialogProperties(usePlatformDefaultWidth = false, decorFitsSystemWindows = false)) {
        HomeNoDialogDim()
        AnimatedVisibility(vis, enter = fadeIn(tween(200, easing = HomeV4.easeInOut)), exit = fadeOut(tween(200, easing = HomeV4.easeInOut))) {
            Box(Modifier.fillMaxSize().background(Color.Black.copy(alpha = 0.35f)).pointerInput(Unit) { detectTapGestures { onClose() } }) {
                Column(
                    Modifier.statusBarsPadding().padding(start = 16.dp, top = if (wide) 108.dp else 54.dp).width(270.dp)
                        .shadow(24.dp, RoundedCornerShape(22.dp)).clip(RoundedCornerShape(22.dp)).background(HomeV4.menuBg)
                        .skBorder(Color.White.copy(alpha = 0.1f), 22.dp)
                        .pointerInput(Unit) { detectTapGestures { } }   // trykk i menyen lukker den ikke
                        .padding(8.dp),
                ) {
                    T("STEDER", mono(10f, HomeV4.body, 0.12f), Modifier.padding(start = 12.dp, end = 12.dp, top = 8.dp, bottom = 6.dp))
                    PlaceRow("Hjemme", "${m.sys.rooms.size} rom · samme nett", HomeV4.green, hex(0x3a2e14), HomeV4.home, m.stedId.isEmpty()) {
                        onClose(); scope.launch { m.selectSted("") }
                    }
                    for (s in m.steder) {
                        PlaceRow(s.navn, "${s.enheter} rom · via Skjold-hjem", if (s.online > 0) HomeV4.goldDark else HomeV4.muted, hex(0x1e3426), HomeV4.sted, s.id == m.stedId) {
                            onClose(); scope.launch { m.selectSted(s.id) }
                        }
                    }
                    Box(Modifier.padding(horizontal = 8.dp, vertical = 6.dp).fillMaxWidth().height(1.dp).background(Color.White.copy(alpha = 0.1f)))
                    Row(
                        Modifier.fillMaxWidth().height(44.dp).press { onClose(); m.openStederSettings() }.padding(horizontal = 12.dp),
                        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp),
                    ) {
                        SKIcon(HomeV4.plus, 16.dp, 2f, HomeV4.ink)
                        T("Legg til sted", sora(14f))
                    }
                }
            }
        }
    }
}

@Composable
private fun PlaceRow(name: String, sub: String, dot: Color, tile: Color, icon: String, on: Boolean, pick: () -> Unit) {
    Row(
        Modifier.fillMaxWidth().heightIn(min = 56.dp).clip(RoundedCornerShape(14.dp))
            .background(if (on) HomeV4.ink.copy(alpha = 0.08f) else Color.Transparent)
            .press { Haptics.tick(); pick() }.padding(horizontal = 12.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Box(Modifier.size(36.dp).clip(RoundedCornerShape(10.dp)).background(tile), contentAlignment = Alignment.Center) {
            SKIcon(icon, 18.dp, 1.8f, HomeV4.ink)
        }
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            T(name, sora(15f, W.Semibold), maxLines = 1)
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                Box(Modifier.size(6.dp).clip(CircleShape).background(dot))
                T(sub, sora(11f, W.Regular, HomeV4.body), maxLines = 1)
            }
        }
        T(if (on) "✓" else "", sora(14f, W.Regular, HomeV4.gold), Modifier.width(16.dp))
    }
}

// MARK: - Bryter (iOS-bryteren 51 × 31 i «Rediger hjemskjerm»)

@Composable
fun HomeSwitch(on: Boolean, label: String, toggle: () -> Unit) {
    val x by animateDpAsState(if (on) 22.dp else 2.dp, tween(200, easing = HomeV4.easeInOut), label = "homeSwitch")
    Box(
        Modifier.size(51.dp, 31.dp).clip(CircleShape).background(if (on) HomeV4.gold else hex(0x3a3a3c))
            .press(label = label) { Haptics.tick(); toggle() },
    ) {
        Box(Modifier.offset(x = x, y = 2.dp).size(27.dp).shadow(3.dp, CircleShape).clip(CircleShape).background(Color.White))
    }
}
