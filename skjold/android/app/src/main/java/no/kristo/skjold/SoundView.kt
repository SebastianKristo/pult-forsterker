package no.kristo.skjold

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.drag
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.text.drawText
import androidx.compose.ui.unit.dp
import kotlin.math.abs
import kotlin.math.roundToInt

/** Lyd: EQ profile per source, an interactive EQ curve, preset tiles, tone controls and loudness. */
@Composable
fun SoundView(m: AppModel) {
    var band by rememberSaveable { mutableIntStateOf(2) }
    val prof = m.prof
    // MARK: Source
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            SKMonoLabel("LYDPROFIL FOR")
            Spacer(Modifier.weight(1f))
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                Dot(C.ok)
                T(activeName(m.actSrc) + " spiller nå", sora(11f, W.Regular, C.muted))
            }
        }
        EdgeScroll(8.dp) {
            for ((k, label) in SK.eqSources) {
                val on = m.eqEditing == k
                Row(
                    Modifier.height(40.dp).clip(CircleShape).background(if (on) C.selBg else C.card).skCapsuleBorder(if (on) C.accent else C.line2)
                        .press { if (!on) { Haptics.tick(); m.eqSrc = k } }.padding(start = 6.dp, end = 14.dp),
                    verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    SourceGlyph(label, 24.dp)
                    T(label, sora(13f, if (on) W.Semibold else W.Regular, if (on) C.accent2 else C.ink))
                    if (m.actSrc == k) Dot(C.ok)
                }
            }
        }
        if (m.eqEditing != m.actSrc) T("Du redigerer ${activeName(m.eqEditing)}. Profilen brukes neste gang den inngangen spiller.", sora(11f, W.Regular, C.muted))
    }

    // MARK: EQ
    val presetName = if (prof.preset >= 0 && prof.preset < SK.eqPresets.size) SK.eqPresets[prof.preset].first else "Egendefinert"
    Column(Modifier.fillMaxWidth().skBox(C.card, C.line, 18.dp).padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            T("Equalizer", sora(17f, W.Semibold))
            Box(Modifier.height(20.dp).clip(CircleShape).background(C.selBg2).padding(horizontal = 8.dp), contentAlignment = Alignment.Center) {
                T(presetName, mono(10f, C.accent2, 0.08f))
            }
            Spacer(Modifier.weight(1f))
            if (prof.eq.any { it != 0 }) SKLinkButton("Nullstill") {
                Haptics.bump()
                m.setProf { it.copy(preset = 0, eq = listOf(0, 0, 0, 0, 0)) }
            }
        }
        EQGraph(prof.eq, band, { band = it }) { i, v -> m.setProf { p -> p.copy(eq = p.eq.toMutableList().also { it[i] = v }, preset = -1) } }
        // band labels under the graph, tap to select
        Row(Modifier.fillMaxWidth()) {
            for (i in 0 until 5) {
                Column(Modifier.weight(1f).press { Haptics.tick(); band = i }, horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    T(SK.eqBands[i], mono(10f, if (i == band) C.accent2 else C.muted))
                    T(SK.eqNames[i], sora(10f, if (i == band) W.Semibold else W.Regular, if (i == band) C.ink else C.ink2), maxLines = 1)
                }
            }
        }
        // what the selected band does
        Row(Modifier.fillMaxWidth().skBox(C.bg.copy(alpha = 0.6f), C.line, 12.dp).padding(12.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Column(Modifier.width(70.dp), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                T(dB(prof.eq[band]), mono(20f, C.accent2, weight = W.Medium))
                T(SK.eqHz[band], mono(10f))
            }
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                T(SK.eqNames[band], sora(13f, W.Semibold))
                T(SK.eqDesc[band], sora(12f, W.Regular, C.body, 1.4f))
            }
        }
    }

    // MARK: Presets
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        SKMonoLabel("FORHÅNDSINNSTILLINGER")
        EdgeScroll(10.dp) {
            SK.eqPresets.forEachIndexed { i, p ->
                val on = prof.preset == i
                Column(
                    Modifier.width(96.dp).clip(RoundedCornerShape(14.dp)).background(if (on) C.selBg else C.card).skBorder(if (on) C.accent else C.line, 14.dp)
                        .press { if (!on) { Haptics.tick(); m.setProf { it.copy(preset = i, eq = p.second) } } }.padding(10.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    // exaggerated so the shape reads at thumbnail size
                    EQCurve(p.second.map { (it * 2).coerceIn(-12, 12) }, Modifier.fillMaxWidth().height(30.dp))
                    T(p.first, sora(12f, if (on) W.Semibold else W.Regular, if (on) C.accent2 else C.ink))
                }
            }
        }
    }

    // MARK: Tone
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        SKMonoLabel("TONE")
        SKCard(radius = 18.dp) {
            ToneRow(m, "Bass", "bass", -6..6, NumFormat.DB, "", "", Color.Transparent)
            ToneRow(m, "Diskant", "treb", -6..6, NumFormat.DB, "", "", C.line)
            ToneRow(m, "Balanse", "bal", -5..5, NumFormat.BAL, "V", "H", C.line)
            Row(Modifier.fillMaxWidth().topLine(C.line).padding(vertical = 14.dp, horizontal = 16.dp), verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    T("Loudness", sora(14f))
                    T("Mer bass og diskant ved lavt volum", sora(11f, W.Regular, C.muted))
                }
                SKToggle(prof.loud) { Haptics.tick(); m.setProf { it.copy(loud = !it.loud) } }
            }
        }
    }
}

private fun activeName(k: String) = SK.eqSources.firstOrNull { it.first == k }?.second ?: ""

private fun dB(v: Int) = (if (v > 0) "+" else if (v < 0) "−" else "") + "${abs(v)} dB"

@Composable
private fun ToneRow(m: AppModel, n: String, k: String, r: IntRange, f: NumFormat, left: String, right: String, line: Color) {
    val v = m.sset[k] ?: 0
    Column(Modifier.fillMaxWidth().topLine(line).padding(vertical = 14.dp, horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(Modifier.fillMaxWidth()) {
            T(n, sora(14f))
            Spacer(Modifier.weight(1f))
            T(f.format(v), mono(12f, if (v == 0) C.muted else C.accent2))
        }
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            if (left.isNotEmpty()) T(left, mono(10f))
            SKCenterSlider(v, r, Modifier.weight(1f)) { m.setS(k, it) }
            if (right.isNotEmpty()) T(right, mono(10f))
        }
    }
}

// MARK: - Interactive EQ graph

/** Five draggable band nodes on a smooth curve with a dB grid. Drag anywhere: the nearest band follows the finger. */
@Composable
fun EQGraph(eq: List<Int>, selected: Int, onSelect: (Int) -> Unit, onChange: (Int, Int) -> Unit) {
    var dragging by remember { mutableStateOf(false) }
    val eqNow by rememberUpdatedState(eq)
    val sel by rememberUpdatedState(selected)
    val cbSel by rememberUpdatedState(onSelect)
    val cb by rememberUpdatedState(onChange)
    val anim = (0 until 5).map { i -> animateFloatAsState(eq[i].toFloat(), label = "eq$i").value }
    val tm = rememberTextMeasurer()
    val padPx = 16f
    Canvas(
        Modifier.fillMaxWidth().height(190.dp).pointerInput(Unit) {
            awaitEachGesture {
                val down = awaitFirstDown()
                val w = size.width.toFloat(); val h = size.height.toFloat(); val pad = padPx * density
                val i = (down.position.x / (w / 5)).toInt().coerceIn(0, 4)
                if (i != sel) Haptics.tick()
                cbSel(i)
                dragging = true
                var last = eqNow[i]
                fun upd(y: Float) {
                    val raw = (h / 2 - y) / (h / 2 - pad) * 12
                    val v = raw.roundToInt().coerceIn(-12, 12)
                    if (v != last) {
                        if (v == 0 || abs(v) == 12) Haptics.bump() else Haptics.tick()
                        last = v
                        cb(i, v)
                    }
                }
                upd(down.position.y)
                drag(down.id) { c -> upd(c.position.y); c.consume() }
                dragging = false
            }
        },
    ) {
        val w = size.width; val h = size.height; val pad = padPx * density
        fun x(i: Int) = w * (i + 0.5f) / 5
        fun y(v: Float) = h / 2 - v * (h / 2 - pad) / 12
        // grid
        for (v in listOf(12, 6, 0, -6, -12)) {
            val yy = y(v.toFloat())
            drawLine(C.ink.copy(alpha = if (v == 0) 0.16f else 0.06f), Offset(0f, yy), Offset(w, yy), density,
                pathEffect = if (v == 0) null else PathEffect.dashPathEffect(floatArrayOf(3 * density, 4 * density)))
            drawText(tm, if (v > 0) "+$v" else "$v", Offset(3 * density, yy - 13 * density), mono(8f, C.muted.copy(alpha = 0.7f)))
        }
        val pts = (0 until 5).map { Offset(x(it), y(anim[it])) }
        // selected band guide
        drawRect(C.accent.copy(alpha = if (dragging) 0.25f else 0.12f), Offset(pts[selected].x, 0f), Size(density, h))
        drawPath(curve(pts, w, h / 2), Brush.verticalGradient(listOf(C.accent.copy(alpha = 0.32f), C.accent.copy(alpha = 0.02f))))
        val line = curve(pts, w, null)
        drawPath(line, C.accent.copy(alpha = 0.25f), style = Stroke(8 * density, cap = StrokeCap.Round, join = StrokeJoin.Round))
        drawPath(line, C.accent, style = Stroke(2.5f * density, cap = StrokeCap.Round, join = StrokeJoin.Round))
        // nodes
        pts.forEachIndexed { i, p ->
            val on = i == selected
            val r = (if (on) 11f else 7f) * density
            drawCircle(Color.Black.copy(alpha = 0.4f), r, p + Offset(0f, density))
            drawCircle(if (on) C.ink else C.card, r, p)
            val bw = (if (on) 3f else 2f) * density
            drawCircle(C.accent, r - bw / 2, p, style = Stroke(bw))
        }
        // value bubble while dragging
        if (dragging) {
            val v = eq[selected]
            val txt = (if (v > 0) "+" else if (v < 0) "−" else "") + "${abs(v)} dB"
            val layout = tm.measure(txt, mono(11f, C.bg, weight = W.Medium))
            val bw = layout.size.width + 16 * density; val bh = 22 * density
            val p = pts[selected]
            val cx = p.x.coerceIn(30 * density, w - 30 * density)
            val cy = if (p.y > 50 * density) p.y - 34 * density else p.y + 34 * density
            drawRoundRect(C.accent2, Offset(cx - bw / 2, cy - bh / 2), Size(bw, bh), CornerRadius(bh / 2))
            drawText(layout, topLeft = Offset(cx - layout.size.width / 2f, cy - layout.size.height / 2f))
        }
    }
}

/** Smooth curve through the nodes, flat to both edges; optionally closed down to the 0 dB line. */
private fun DrawScope.curve(pts: List<Offset>, w: Float, base: Float?): Path {
    val p = Path()
    p.moveTo(0f, pts[0].y)
    p.lineTo(pts[0].x, pts[0].y)
    for (i in 0 until 4) {
        val mx = (pts[i].x + pts[i + 1].x) / 2
        p.cubicTo(mx, pts[i].y, mx, pts[i + 1].y, pts[i + 1].x, pts[i + 1].y)
    }
    p.lineTo(w, pts[4].y)
    if (base != null) { p.lineTo(w, base); p.lineTo(0f, base); p.close() }
    return p
}

/** Small EQ curve, viewBox 0 0 300 90 (curve() in the design). Used for preset previews. */
@Composable
fun EQCurve(eq: List<Int>, modifier: Modifier = Modifier) {
    val xs = listOf(15f, 82.5f, 150f, 217.5f, 285f)
    val ys = eq.map { 45f - it * 3.2f }
    var d = "M0 ${ys[0]} L${xs[0]} ${ys[0]}"
    for (i in 0 until 4) { val mx = (xs[i] + xs[i + 1]) / 2; d += " C$mx ${ys[i]} $mx ${ys[i + 1]} ${xs[i + 1]} ${ys[i + 1]}" }
    d += " L300 ${ys[4]}"
    val area = "$d L300 45 L0 45 Z"
    Canvas(modifier) {
        drawSvg("M0 45 L300 45", hex(0x2a2a28), 300f, 90f, strokePx = density)
        drawSvg(area, C.accent.copy(alpha = 0.18f), 300f, 90f, fill = true)
        drawSvg(d, C.accent, 300f, 90f, strokePx = 1.5f * density)
    }
}

// MARK: - Center slider

/** Slider for ± values: fills from the centre, detent at 0. */
@Composable
fun SKCenterSlider(value: Int, range: IntRange, modifier: Modifier = Modifier, onChange: (Int) -> Unit) {
    val cur by rememberUpdatedState(value)
    val cb by rememberUpdatedState(onChange)
    BoxWithConstraints(modifier.height(28.dp)) {
        Canvas(
            Modifier.matchParentSize().pointerInput(range) {
                awaitEachGesture {
                    var last = cur
                    fun upd(px: Float) {
                        val thumb = 22 * density
                        val f = ((px - thumb / 2) / (size.width - thumb)).coerceIn(0f, 1f)
                        val v = range.first + (f * (range.last - range.first)).roundToInt()
                        if (v != last) {
                            if (v == 0 || v == range.first || v == range.last) Haptics.bump() else Haptics.tick()
                            last = v
                            cb(v)
                        }
                    }
                    val down = awaitFirstDown()
                    upd(down.position.x)
                    drag(down.id) { c -> upd(c.position.x); c.consume() }
                }
            },
        ) {
            val w = size.width; val h = size.height; val thumb = 22 * density
            val span = (range.last - range.first).toFloat()
            fun px(v: Int) = thumb / 2 + (w - thumb) * (v - range.first) / span
            val cx = px(0); val vx = px(value); val cy = h / 2
            drawRoundRect(hex(0x2a2a2c), Offset(0f, cy - 3 * density), Size(w, 6 * density), CornerRadius(3 * density))
            for (t in range) {
                val tw = (if (t == 0) 2 else 1) * density; val th = (if (t == 0) 14 else 8) * density
                drawRect(C.ink.copy(alpha = if (t == 0) 0.35f else 0.1f), Offset(px(t) - tw / 2, cy - th / 2), Size(tw, th))
            }
            drawRoundRect(C.accent, Offset(minOf(cx, vx), cy - 3 * density), Size(abs(vx - cx), 6 * density), CornerRadius(3 * density))
            drawCircle(Color.Black.copy(alpha = 0.35f), thumb / 2, Offset(vx, cy + density))
            drawCircle(C.ink, thumb / 2, Offset(vx, cy))
            drawCircle(if (value == 0) C.line2 else C.accent, thumb / 2 - density, Offset(vx, cy), style = Stroke(2 * density))
        }
    }
}

