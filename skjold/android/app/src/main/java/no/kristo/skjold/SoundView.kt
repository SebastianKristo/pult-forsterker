package no.kristo.skjold

import androidx.compose.animation.Crossfade
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.drag
import androidx.compose.foundation.gestures.waitForUpOrCancellation
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
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
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.lerp
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.layout
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import kotlin.math.abs
import kotlin.math.exp
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

/*
 * Lyd (v4), som V4Sound.swift (V4SoundTab) på iOS: kildechips, EQ-kort med kurve (5 bånd, dra), båndverdier,
 * båndinfo med −/+, «Hold for å sammenligne» og «Nullstill», profiler og lydbilde. Tittelen «Lyd» og
 * gruppekapselen tegnes av ContentView. Modellhjelpere og UI-tilstand ligger i SoundV4.kt.
 */

private val XS = listOf(0.08f, 0.29f, 0.5f, 0.71f, 0.92f)
private const val GRAPH_H = 196f
private const val GRAPH_PAD = 8f
private val GRID = listOf(8f to 0.05f, 53f to 0.04f, 98f to 0.14f, 143f to 0.04f, 188f to 0.05f)

/** Summen av fem gauss-klokker (bredde 0,13) over x 0…1, klemt til ±12. */
private fun curvePoints(eq: List<Int>, n: Int): List<Offset> = (0..n).map { k ->
    val x = k.toFloat() / n
    var v = 0f
    eq.forEachIndexed { i, g ->
        if (i < 5) {
            val d = (x - XS[i]) / 0.13f
            v += g * exp(-(d * d))
        }
    }
    Offset(x, v.coerceIn(-12f, 12f))
}

/** padding(.horizontal, −x): utvider bredden med x på hver side. */
private fun Modifier.bleed(x: Dp): Modifier = this.layout { measurable, constraints ->
    val extra = x.roundToPx() * 2
    val w = constraints.maxWidth + extra
    val p = measurable.measure(constraints.copy(minWidth = w, maxWidth = w))
    layout(constraints.maxWidth, p.height) { p.place(-extra / 2, 0) }
}

@Composable
fun SoundView(m: AppModel) {
    Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(22.dp)) {
        SrcChips(m)
        EqCard(m)
        Profiles(m)
        SoundImage(m)
    }
}

// MARK: Kilder

@Composable
private fun SrcChips(m: AppModel) {
    EdgeScroll(8.dp) {
        for ((k, label) in SK.eqSources) {
            val on = m.eqEditing == k
            Row(
                Modifier.height(36.dp).clip(CircleShape).background(if (on) C.selBg else C.card).skCapsuleBorder(if (on) C.accent else C.line2)
                    .press { Haptics.tick(); m.eqSrc = k }.padding(horizontal = 14.dp),
                verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(7.dp),
            ) {
                T(label, sora(13f, W.Regular, if (on) C.accent2 else C.ink), maxLines = 1)
                if (m.actSrc == k) Dot(C.ok)
            }
        }
    }
}

// MARK: EQ-kort

@Composable
private fun EqCard(m: AppModel) {
    val eqOn = m.soundEqOn
    Column(
        Modifier.fillMaxWidth().clip(RoundedCornerShape(26.dp)).background(Brush.verticalGradient(listOf(hex(0x17171a), hex(0x111113))))
            .skBorder(C.line, 26.dp).padding(start = 16.dp, end = 16.dp, top = 16.dp, bottom = 14.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                T("Equalizer", sora(15f, W.Semibold))
                T((if (eqOn) m.soundPresetName.uppercase() else "AV") + " · " + m.soundSrcLabel.uppercase(), mono(10f, C.muted, 0.06f), maxLines = 1)
            }
            SoundSwitch(eqOn, "Equalizer av/på") { m.soundToggleEq() }
        }
        Graph(m, eqOn)
        BandTabs(m)
        BandInfo(m)
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            CompareButton(m, Modifier.weight(1f))
            Box(
                Modifier.height(40.dp).clip(CircleShape).skCapsuleBorder(C.line2)
                    .press { Haptics.tick(); m.setProf { it.copy(eq = SoundUi.zeros, preset = 0) } }.padding(horizontal = 16.dp),
                contentAlignment = Alignment.Center,
            ) { T("Nullstill", sora(13f)) }
        }
    }
}

@Composable
private fun Graph(m: AppModel, eqOn: Boolean) {
    val live = m.soundLive
    val band = SoundUi.band
    val tm = rememberTextMeasurer()
    val fade by animateFloatAsState(if (eqOn) 1f else 0.45f, tween(250), label = "eqFade")
    val sizes = (0 until 5).map { i -> animateFloatAsState(if (band == i) 22f else 14f, tween(150), label = "eqDot$i").value }
    val model by rememberUpdatedState(m)
    Canvas(
        Modifier.bleed(4.dp).height(GRAPH_H.dp).alpha(fade).pointerInput(Unit) {
            awaitEachGesture {
                val down = awaitFirstDown()
                down.consume()
                val w = max(1f, size.width.toFloat())
                val x = down.position.x / w
                var best = 9f
                var idx = SoundUi.band
                XS.forEachIndexed { j, xx -> if (abs(xx - x) < best) { best = abs(xx - x); idx = j } }
                if (idx != SoundUi.band) Haptics.tick()
                SoundUi.band = idx
                val pad = GRAPH_PAD * density
                fun upd(y: Float) {
                    val v = 12f - (y - pad) / (size.height - 2 * pad) * 24f
                    model.soundSetBand(SoundUi.band, v.roundToInt())
                }
                upd(down.position.y)
                drag(down.id) { c -> upd(c.position.y); c.consume() }
                Haptics.sliderRelease()
            }
        },
    ) {
        val d = density
        val w = size.width
        fun yOf(v: Float) = (GRAPH_PAD + (12f - v) / 24f * (GRAPH_H - 2 * GRAPH_PAD)) * d
        // rutenett, dB-merker og linja for valgt bånd
        for ((y, a) in GRID) drawRect(Color.White.copy(alpha = a), Offset(0f, y * d), Size(w, d))
        drawText(tm, "+12", Offset(w - 22 * d, 10 * d), mono(9f, C.dim))
        drawText(tm, "0", Offset(w - 10 * d, 100 * d), mono(9f, C.dim))
        drawText(tm, "−12", Offset(w - 22 * d, 170 * d), mono(9f, C.dim))
        drawRect(C.accent2.copy(alpha = 0.22f), Offset(XS[band] * w, 8 * d), Size(d, (GRAPH_H - 16) * d))
        // kurven
        val pts = curvePoints(live, 60)
        val line = Path()
        val fill = Path()
        pts.forEachIndexed { i, p ->
            if (i == 0) { line.moveTo(p.x * w, yOf(p.y)); fill.moveTo(p.x * w, yOf(p.y)) }
            else { line.lineTo(p.x * w, yOf(p.y)); fill.lineTo(p.x * w, yOf(p.y)) }
        }
        fill.lineTo(w, yOf(0f)); fill.lineTo(0f, yOf(0f)); fill.close()
        val b = fill.getBounds()
        drawPath(fill, Brush.verticalGradient(listOf(C.accent.copy(alpha = 0.38f), C.accent.copy(alpha = 0f)), startY = b.top, endY = max(b.bottom, b.top + 1f)))
        // glød (shadow gold .5, radius 6)
        for ((sw, a) in listOf(12f to 0.05f, 8f to 0.08f, 5f to 0.12f)) {
            drawPath(line, C.accent2.copy(alpha = a), style = Stroke(sw * d, join = StrokeJoin.Round))
        }
        drawPath(line, C.accent2, style = Stroke(2.2f * d, join = StrokeJoin.Round))
        // punktene
        for (i in 0 until 5) {
            val sz = sizes[i]
            val f = ((sz - 14f) / 8f).coerceIn(0f, 1f)
            val c = Offset(XS[i] * w, yOf(live[i].toFloat()))
            if (f > 0f) {
                val gr = (sz / 2 + 10) * d
                drawCircle(Brush.radialGradient(listOf(C.accent2.copy(alpha = 0.45f * f), C.accent2.copy(alpha = 0f)), c, gr), gr, c)
                drawCircle(C.accent2.copy(alpha = 0.18f * f), (sz + 12) / 2 * d, c)
            }
            drawCircle(lerp(C.card, C.accent2, f), sz / 2 * d, c)
            drawCircle(C.accent2, (sz / 2 - 1) * d, c, style = Stroke(2 * d))
        }
    }
}

@Composable
private fun BandTabs(m: AppModel) {
    Row(Modifier.bleed(4.dp), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
        for (i in 0 until 5) {
            val v = if (m.prof.eq.size == 5) m.prof.eq[i] else 0
            Column(
                Modifier.weight(1f).height(46.dp).clip(RoundedCornerShape(12.dp))
                    .background(if (SoundUi.band == i) C.accent2.copy(alpha = 0.12f) else Color.Transparent)
                    .press { Haptics.tick(); SoundUi.band = i },
                horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(2.dp, Alignment.CenterVertically),
            ) {
                T((if (v > 0) "+" else "") + "$v", mono(12f, if (v != 0) C.accent2 else C.muted))
                T(SoundUi.bandNames[i].third, mono(9f, C.muted))
            }
        }
    }
}

@Composable
private fun BandInfo(m: AppModel) {
    val band = SoundUi.band
    val cur = if (m.prof.eq.size == 5) m.prof.eq[band] else 0
    Row(
        Modifier.fillMaxWidth().clip(RoundedCornerShape(16.dp)).background(Color.White.copy(alpha = 0.04f))
            .padding(start = 14.dp, end = 12.dp, top = 12.dp, bottom = 12.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
            Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                T(SoundUi.bandNames[band].first, sora(14f, W.Semibold), Modifier.alignByBaseline())
                T(SoundUi.bandNames[band].second, mono(11f, C.muted), Modifier.alignByBaseline())
            }
            Crossfade(band, animationSpec = tween(250), label = "bandDesc") { b ->
                T(SoundUi.desc[b], sora(12f, W.Regular, C.body, 1.4f))
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            SoundStepButton("−", "Senk") { m.soundSetBand(band, cur - 1) }
            SoundStepButton("+", "Øk") { m.soundSetBand(band, cur + 1) }
        }
    }
}

@Composable
private fun SoundStepButton(s: String, label: String, act: () -> Unit) {
    Box(
        Modifier.size(36.dp).clip(CircleShape).background(C.ink.copy(alpha = 0.1f)).press(label = label) { Haptics.tick(); act() },
        contentAlignment = Alignment.Center,
    ) { T(s, sora(18f)) }
}

@Composable
private fun CompareButton(m: AppModel, modifier: Modifier) {
    val on = SoundUi.cmp != null
    val model by rememberUpdatedState(m)
    Box(
        modifier.height(40.dp).clip(CircleShape).background(if (on) C.selBg else Color.Transparent).skCapsuleBorder(if (on) C.accent else C.line2)
            .semantics { contentDescription = "Hold for å sammenligne" }
            .pointerInput(Unit) {
                awaitEachGesture {
                    awaitFirstDown(requireUnconsumed = false)
                    model.soundCompareStart()
                    waitForUpOrCancellation()
                    model.soundCompareEnd()
                }
            },
        contentAlignment = Alignment.Center,
    ) {
        T(if (on) "Uten EQ – slipp for å høre med" else "Hold for å sammenligne", sora(13f, W.Regular, if (on) C.accent2 else C.ink), maxLines = 1)
    }
}

// MARK: Profiler (fliser 104)

@Composable
private fun Profiles(m: AppModel) {
    val eqOn = m.soundEqOn
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        SKMonoLabel("PROFILER")
        EdgeScroll(10.dp) {
            SK.eqPresets.forEachIndexed { i, p ->
                ProfileTile(p.first, p.second, eqOn && m.prof.preset == i) { m.soundPickPreset(i) }
            }
            ProfileTile("Egendefinert", m.prof.eq, eqOn && m.prof.preset < 0) {}
        }
    }
}

@Composable
private fun ProfileTile(n: String, eq: List<Int>, on: Boolean, pick: () -> Unit) {
    val fg = if (on) C.accent2 else C.ink2
    // minimumScaleFactor(0.8) over 84 dp tekstbredde
    val tm = rememberTextMeasurer()
    val availPx = with(LocalDensity.current) { 84.dp.toPx() }
    val scale = remember(n) { min(1f, availPx / max(1, tm.measure(n, sora(13f)).size.width)).coerceAtLeast(0.8f) }
    Column(
        Modifier.width(104.dp).clip(RoundedCornerShape(16.dp)).background(if (on) C.selBg else C.card).skBorder(if (on) C.accent else C.line, 16.dp)
            .press { Haptics.tick(); pick() }.padding(10.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Canvas(Modifier.size(82.dp, 30.dp)) {
            val d = density
            drawRect(Color.White.copy(alpha = 0.08f), Offset(0f, 15 * d - d / 2), Size(82 * d, d))
            // viewBox 100 × 36 skalert til 82 × 30
            val path = Path()
            curvePoints(eq, 24).forEachIndexed { i, p ->
                val x = p.x * 82 * d
                val y = (18f - p.y * 2.2f) / 36f * 30f * d
                if (i == 0) path.moveTo(x, y) else path.lineTo(x, y)
            }
            drawPath(path, fg, style = Stroke(2 * d, join = StrokeJoin.Round))
        }
        T(n, sora(13f * scale, W.Regular, fg), maxLines = 1)
    }
}

// MARK: Lydbilde

@Composable
private fun SoundImage(m: AppModel) {
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        SKMonoLabel("LYDBILDE")
        Column(Modifier.fillMaxWidth().clip(RoundedCornerShape(22.dp)).background(C.card).skBorder(C.line, 22.dp)) {
            BalanceRow(m)
            ToggleRow("Lydstyrkekorreksjon", "Mer bass og diskant på lavt volum, så musikken ikke blir tynn.", m.prof.loud) {
                m.setProf { it.copy(loud = !it.loud) }
            }
            ToggleRow("Nattmodus", "Jevner ut forskjellen mellom svake og sterke partier.", SoundUi.night) { SoundUi.night = !SoundUi.night }
            ToggleRow("Små høyttalere", "Kutter den dypeste bassen så små høyttalere ikke forvrenger.", SoundUi.hpf) { SoundUi.hpf = !SoundUi.hpf }
            MaxRow(m)
            LinkRow("Romkorreksjon", "Mål rommet med telefonens mikrofon og demp basstopper.", "Mål") { m.showRoomEQ = true }
            LinkRow("Høyttalerprofil", "Hent en Skjold Sertifisert-profil for høyttalerne dine, eller mål dem selv.", "Åpne") { m.showSpeakers = true }
        }
    }
}

@Composable
private fun LinkRow(title: String, hint: String, action: String, open: () -> Unit) {
    Row(
        Modifier.fillMaxWidth().press { Haptics.tick(); open() }.padding(horizontal = 16.dp, vertical = 14.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
            T(title, sora(15f))
            T(hint, sora(12f, W.Regular, C.muted))
        }
        Spacer(Modifier.width(8.dp))   // Spacer(minLength: 8)
        T(action, sora(14f, W.Regular, C.accent2))
    }
}

@Composable
private fun BalanceRow(m: AppModel) {
    val bal = m.sset["bal"] ?: 0
    val model by rememberUpdatedState(m)
    Column(
        Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 14.dp).semantics(mergeDescendants = true) { contentDescription = "Balanse" },
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Row(Modifier.fillMaxWidth()) {
            T("Balanse", sora(15f), Modifier.alignByBaseline())
            Spacer(Modifier.weight(1f))
            T(if (bal == 0) "Midt" else if (bal < 0) "V ${-bal}" else "H $bal", mono(12f, if (bal != 0) C.accent2 else C.muted), Modifier.alignByBaseline())
        }
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            T("V", mono(11f, C.muted))
            Canvas(
                Modifier.weight(1f).height(30.dp).pointerInput(Unit) {
                    awaitEachGesture {
                        val down = awaitFirstDown()
                        down.consume()
                        fun upd(px: Float) {
                            val n = (px / max(1f, size.width.toFloat()) * 10f - 5f).roundToInt().coerceIn(-5, 5)
                            val cur = model.sset["bal"] ?: 0
                            if (n != cur) { Haptics.sliderStep(cur, n, -5, 5); model.setS("bal", n) }
                        }
                        upd(down.position.x)
                        drag(down.id) { c -> upd(c.position.x); c.consume() }
                    }
                },
            ) {
                val d = density
                val w = size.width
                val cy = size.height / 2
                val p = (bal + 5) / 10f
                drawRoundRect(C.seg, Offset(0f, cy - 4 * d), Size(w, 8 * d), CornerRadius(4 * d))
                drawRect(hex(0x4a4a4c), Offset(w / 2, cy - 8 * d), Size(d, 16 * d))
                val fw = abs(p - 0.5f) * w
                if (fw > 0f) drawRoundRect(C.accent, Offset(min(0.5f, p) * w, cy - 4 * d), Size(fw, 8 * d), CornerRadius(4 * d))
                val kx = p * w
                drawCircle(Color.Black.copy(alpha = 0.18f), 13 * d, Offset(kx, cy + 2 * d))
                drawCircle(Color.Black.copy(alpha = 0.25f), 11.5f * d, Offset(kx, cy + 2 * d))
                drawCircle(C.ink, 11 * d, Offset(kx, cy))
            }
            T("H", mono(11f, C.muted))
        }
    }
}

@Composable
private fun ToggleRow(n: String, hint: String, on: Boolean, toggle: () -> Unit) {
    Row(
        Modifier.fillMaxWidth().topLine(C.line).padding(horizontal = 16.dp, vertical = 13.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            T(n, sora(15f))
            T(hint, sora(12f, W.Regular, C.muted, 1.4f))
        }
        SoundSwitch(on, n, toggle)
    }
}

/** Maks volum: verdi 70–100 i trinn (sset["vmax"] 0…3), linje uten knott (V4Bar, høyde 8, spor #2a2a2c). */
@Composable
private fun MaxRow(m: AppModel) {
    val maxv = SoundUi.vmax[(m.sset["vmax"] ?: 0).coerceIn(0, 3)]
    val model by rememberUpdatedState(m)
    var local by remember { mutableStateOf<Float?>(null) }
    // Linja er 28 dp høy med 8 dp spor i midten: 10 dp over sporet = VStack(spacing: 10), 10 + 4 under = padding 14.
    Column(Modifier.fillMaxWidth().topLine(C.line).padding(start = 16.dp, end = 16.dp, top = 14.dp, bottom = 4.dp)) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.Top, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                T("Maks volum", sora(15f))
                T("Volumhjulet og appen går ikke høyere", sora(12f, W.Regular, C.muted))
            }
            T("$maxv", mono(12f, C.ink2))
        }
        Canvas(
            Modifier.fillMaxWidth().height(28.dp).semantics { contentDescription = "Maks volum" }.pointerInput(Unit) {
                awaitEachGesture {
                    val down = awaitFirstDown()
                    down.consume()
                    fun upd(px: Float) {
                        val f = (px / max(1f, size.width.toFloat())).coerceIn(0f, 1f)
                        local = f
                        val want = 40f + f * 60f
                        val idx = SoundUi.vmax.indices.minByOrNull { abs(SoundUi.vmax[it] - want) } ?: 0
                        if (idx != (model.sset["vmax"] ?: 0)) { Haptics.tick(); model.setS("vmax", idx) }
                    }
                    upd(down.position.x)
                    var lastX = down.position.x
                    drag(down.id) { c -> lastX = c.position.x; upd(lastX); c.consume() }
                    upd(lastX)
                    local = null
                }
            },
        ) {
            val d = density
            val cy = size.height / 2
            val f = (local ?: ((maxv - 40) / 60f)).coerceIn(0f, 1f)
            drawRoundRect(C.seg, Offset(0f, cy - 4 * d), Size(size.width, 8 * d), CornerRadius(4 * d))
            if (f > 0f) drawRoundRect(C.ink, Offset(0f, cy - 4 * d), Size(size.width * f, 8 * d), CornerRadius(4 * d))
        }
    }
}
