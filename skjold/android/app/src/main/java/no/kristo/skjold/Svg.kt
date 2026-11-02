package no.kristo.skjold

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.scale
import androidx.compose.ui.graphics.drawscope.translate
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import kotlin.math.abs
import kotlin.math.atan2
import kotlin.math.ceil
import kotlin.math.cos
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sin
import kotlin.math.sqrt
import kotlin.math.tan

/** SVG path data parser (all commands, also arcs with compact flags) – port of SVGPathParser in SVGShape.swift. */
object SvgPath {
    private val cache = HashMap<String, Path>()

    fun get(d: String): Path = synchronized(cache) { cache.getOrPut(d) { parse(d) } }

    private class Sc(val b: String) {
        var i = 0
        fun peek(): Char? = if (i < b.length) b[i] else null
        fun skip() { while (i < b.length && (b[i] == ' ' || b[i] == ',' || b[i] == '\n' || b[i] == '\r' || b[i] == '\t')) i++ }
        fun flag(): Boolean? {
            skip()
            if (i >= b.length) return null
            val c = b[i]
            if (c != '0' && c != '1') return null
            i++
            return c == '1'
        }
        fun num(): Float? {
            skip()
            val st = i
            if (i < b.length && (b[i] == '+' || b[i] == '-')) i++
            var digits = false; var dot = false
            while (i < b.length) {
                val c = b[i]
                if (c in '0'..'9') { digits = true; i++ } else if (c == '.' && !dot) { dot = true; i++ } else break
            }
            if (i < b.length && digits && (b[i] == 'e' || b[i] == 'E')) {
                var j = i + 1
                if (j < b.length && (b[j] == '+' || b[j] == '-')) j++
                if (j < b.length && b[j] in '0'..'9') { i = j; while (i < b.length && b[i] in '0'..'9') i++ }
            }
            if (!digits) { i = st; return null }
            return b.substring(st, i).toFloatOrNull() ?: run { i = st; null }
        }
    }

    private fun isCmd(c: Char) = c in "MmLlHhVvCcSsQqTtAaZz"

    fun parse(d: String): Path {
        val s = Sc(d)
        val p = Path()
        var cx = 0f; var cy = 0f; var sx = 0f; var sy = 0f
        var lastC: Offset? = null; var lastQ: Offset? = null
        var cmd = ' '
        while (true) {
            s.skip()
            val c = s.peek() ?: break
            if (isCmd(c)) { cmd = c; s.i++ } else if (cmd == ' ') break
            val rel = cmd.isLowerCase()
            val bx = if (rel) cx else 0f; val by = if (rel) cy else 0f
            var ctrlSet = false; var quadSet = false
            when (cmd.uppercaseChar()) {
                'M' -> {
                    val x = s.num() ?: return p; val y = s.num() ?: return p
                    cx = bx + x; cy = by + y; p.moveTo(cx, cy); sx = cx; sy = cy
                    cmd = if (rel) 'l' else 'L'
                }
                'L' -> {
                    val x = s.num() ?: return p; val y = s.num() ?: return p
                    cx = bx + x; cy = by + y; p.lineTo(cx, cy)
                }
                'H' -> { val x = s.num() ?: return p; cx = (if (rel) cx else 0f) + x; p.lineTo(cx, cy) }
                'V' -> { val y = s.num() ?: return p; cy = (if (rel) cy else 0f) + y; p.lineTo(cx, cy) }
                'C' -> {
                    val x1 = s.num() ?: return p; val y1 = s.num() ?: return p; val x2 = s.num() ?: return p
                    val y2 = s.num() ?: return p; val x = s.num() ?: return p; val y = s.num() ?: return p
                    p.cubicTo(bx + x1, by + y1, bx + x2, by + y2, bx + x, by + y)
                    lastC = Offset(bx + x2, by + y2); ctrlSet = true
                    cx = bx + x; cy = by + y
                }
                'S' -> {
                    val x2 = s.num() ?: return p; val y2 = s.num() ?: return p; val x = s.num() ?: return p; val y = s.num() ?: return p
                    val c1 = lastC?.let { Offset(2 * cx - it.x, 2 * cy - it.y) } ?: Offset(cx, cy)
                    p.cubicTo(c1.x, c1.y, bx + x2, by + y2, bx + x, by + y)
                    lastC = Offset(bx + x2, by + y2); ctrlSet = true
                    cx = bx + x; cy = by + y
                }
                'Q' -> {
                    val x1 = s.num() ?: return p; val y1 = s.num() ?: return p; val x = s.num() ?: return p; val y = s.num() ?: return p
                    val q = Offset(bx + x1, by + y1)
                    quad(p, cx, cy, q, bx + x, by + y); lastQ = q; quadSet = true
                    cx = bx + x; cy = by + y
                }
                'T' -> {
                    val x = s.num() ?: return p; val y = s.num() ?: return p
                    val q = lastQ?.let { Offset(2 * cx - it.x, 2 * cy - it.y) } ?: Offset(cx, cy)
                    quad(p, cx, cy, q, bx + x, by + y); lastQ = q; quadSet = true
                    cx = bx + x; cy = by + y
                }
                'A' -> {
                    val rx = s.num() ?: return p; val ry = s.num() ?: return p; val rot = s.num() ?: return p
                    val large = s.flag() ?: return p; val sweep = s.flag() ?: return p
                    val x = s.num() ?: return p; val y = s.num() ?: return p
                    arc(p, cx, cy, bx + x, by + y, rx, ry, rot, large, sweep)
                    cx = bx + x; cy = by + y
                }
                'Z' -> {
                    p.close(); cx = sx; cy = sy
                    cmd = ' '
                    s.skip()
                    val n = s.peek()
                    if (n != null && !isCmd(n)) return p
                    continue
                }
                else -> return p
            }
            if (!ctrlSet) lastC = null
            if (!quadSet) lastQ = null
        }
        return p
    }

    private fun quad(p: Path, x0: Float, y0: Float, q: Offset, x: Float, y: Float) {
        p.cubicTo(x0 + 2f / 3f * (q.x - x0), y0 + 2f / 3f * (q.y - y0), x + 2f / 3f * (q.x - x), y + 2f / 3f * (q.y - y), x, y)
    }

    /** Endpoint arc → cubic Béziers (SVG implementation notes F.6). */
    private fun arc(p: Path, x0: Float, y0: Float, x1e: Float, y1e: Float, rx0: Float, ry0: Float, angle: Float, large: Boolean, sweep: Boolean) {
        var rx = abs(rx0).toDouble(); var ry = abs(ry0).toDouble()
        if (rx == 0.0 || ry == 0.0 || (x0 == x1e && y0 == y1e)) { p.lineTo(x1e, y1e); return }
        val phi = angle * Math.PI / 180; val cosP = cos(phi); val sinP = sin(phi)
        val dx = (x0 - x1e) / 2.0; val dy = (y0 - y1e) / 2.0
        val x1 = cosP * dx + sinP * dy; val y1 = -sinP * dx + cosP * dy
        val lambda = (x1 * x1) / (rx * rx) + (y1 * y1) / (ry * ry)
        if (lambda > 1) { val k = sqrt(lambda); rx *= k; ry *= k }
        val num = rx * rx * ry * ry - rx * rx * y1 * y1 - ry * ry * x1 * x1
        val den = rx * rx * y1 * y1 + ry * ry * x1 * x1
        var coef = sqrt(max(0.0, num / den))
        if (large == sweep) coef = -coef
        val cx1 = coef * rx * y1 / ry; val cy1 = -coef * ry * x1 / rx
        val cx = cosP * cx1 - sinP * cy1 + (x0 + x1e) / 2.0
        val cy = sinP * cx1 + cosP * cy1 + (y0 + y1e) / 2.0
        fun ang(ux: Double, uy: Double, vx: Double, vy: Double) = atan2(ux * vy - uy * vx, ux * vx + uy * vy)
        val t1 = ang(1.0, 0.0, (x1 - cx1) / rx, (y1 - cy1) / ry)
        var dt = ang((x1 - cx1) / rx, (y1 - cy1) / ry, (-x1 - cx1) / rx, (-y1 - cy1) / ry)
        if (!sweep && dt > 0) dt -= 2 * Math.PI else if (sweep && dt < 0) dt += 2 * Math.PI
        val segs = max(1, ceil(abs(dt) / (Math.PI / 2)).toInt())
        val delta = dt / segs
        val k = 4.0 / 3.0 * tan(delta / 4)
        var t = t1
        fun pt(t: Double): DoubleArray {
            val ct = cos(t); val st = sin(t)
            return doubleArrayOf(
                cx + rx * ct * cosP - ry * st * sinP, cy + rx * ct * sinP + ry * st * cosP,
                -rx * st * cosP - ry * ct * sinP, -rx * st * sinP + ry * ct * cosP,
            )
        }
        for (i in 0 until segs) {
            val a = pt(t); val b = pt(t + delta)
            val ex = if (i == segs - 1) x1e.toDouble() else b[0]
            val ey = if (i == segs - 1) y1e.toDouble() else b[1]
            p.cubicTo(
                (a[0] + k * a[2]).toFloat(), (a[1] + k * a[3]).toFloat(),
                (b[0] - k * b[2]).toFloat(), (b[1] - k * b[3]).toFloat(),
                ex.toFloat(), ey.toFloat(),
            )
            t += delta
        }
    }
}

/** Helpers that turn SVG primitives into path data. */
object SVG {
    private fun f(v: Float): String = if (v == v.toInt().toFloat()) v.toInt().toString() else v.toString()
    fun circle(cx: Float, cy: Float, r: Float) = "M${f(cx - r)} ${f(cy)} a${f(r)} ${f(r)} 0 1 0 ${f(2 * r)} 0 a${f(r)} ${f(r)} 0 1 0 ${f(-2 * r)} 0Z"
    fun rect(x: Float, y: Float, w: Float, h: Float, rx: Float = 0f): String {
        if (rx <= 0) return "M${f(x)} ${f(y)}h${f(w)}v${f(h)}h${f(-w)}Z"
        return "M${f(x + rx)} ${f(y)}H${f(x + w - rx)}A${f(rx)} ${f(rx)} 0 0 1 ${f(x + w)} ${f(y + rx)}V${f(y + h - rx)}A${f(rx)} ${f(rx)} 0 0 1 ${f(x + w - rx)} ${f(y + h)}H${f(x + rx)}A${f(rx)} ${f(rx)} 0 0 1 ${f(x)} ${f(y + h - rx)}V${f(y + rx)}A${f(rx)} ${f(rx)} 0 0 1 ${f(x + rx)} ${f(y)}Z"
    }
}

/** Draws an SVG path from a vbW×vbH viewBox, scaled to fit (centred) – SVGShape. */
fun DrawScope.drawSvg(
    d: String, color: Color, vbW: Float = 24f, vbH: Float = 24f, fill: Boolean = false,
    stroke: Float = 1.8f, roundCap: Boolean = true, strokePx: Float? = null,
) {
    val path = SvgPath.get(d)
    val s = min(size.width / vbW, size.height / vbH)
    val ox = (size.width - vbW * s) / 2; val oy = (size.height - vbH * s) / 2
    translate(ox, oy) {
        scale(s, s, pivot = Offset.Zero) {
            if (fill) drawPath(path, color)
            else drawPath(
                path, color,
                style = Stroke(
                    width = strokePx?.let { it / s } ?: stroke,
                    cap = if (roundCap) StrokeCap.Round else StrokeCap.Butt, join = StrokeJoin.Round,
                ),
            )
        }
    }
}

/** Stroked/filled icon from the design (viewBox 0 0 24 24, round caps and joins). */
@Composable
fun SKIcon(d: String, size: Dp = 24.dp, stroke: Float = 1.8f, color: Color = C.ink, fill: Boolean = false, modifier: Modifier = Modifier) {
    Canvas(modifier.size(size)) { drawSvg(d, color, fill = fill, stroke = stroke) }
}

/** Paths used across the app (Icons in SVGShape.swift). */
object Icons {
    const val back = "M15 5l-7 7 7 7"
    const val chevronRight = "M9 5l7 7-7 7"
    const val chevronDown = "M6 9l6 6 6-6"
    const val chevronUp = "M6 15l6-6 6 6"
    const val plus = "M12 5v14M5 12h14"
    const val close = "M6 6l12 12M18 6L6 18"
    const val play = "M8 5v14l11-7z"
    const val playRound = "M8 5.2v13.6a1 1 0 0 0 1.52.85l10.6-6.8a1 1 0 0 0 0-1.7L9.52 4.35A1 1 0 0 0 8 5.2z"
    val pause = SVG.rect(6f, 4.5f, 4f, 15f, 1.2f) + SVG.rect(14f, 4.5f, 4f, 15f, 1.2f)
    val prev = SVG.rect(4f, 5f, 2.4f, 14f, 1f) + "M20 5.8v12.4a1 1 0 0 1-1.55.83L9.3 12.83a1 1 0 0 1 0-1.66l9.15-6.2A1 1 0 0 1 20 5.8z"
    val next = SVG.rect(17.6f, 5f, 2.4f, 14f, 1f) + "M4 5.8v12.4a1 1 0 0 0 1.55.83l9.15-6.2a1 1 0 0 0 0-1.66l-9.15-6.2A1 1 0 0 0 4 5.8z"
    const val shuffle = "M16 3h5v5M4 20L21 3M21 16v5h-5M15 15l6 6M4 4l5 5"
    const val repeatIcon = "M17 2l4 4-4 4M3 11V9a3 3 0 0 1 3-3h15M7 22l-4-4 4-4M21 13v2a3 3 0 0 1-3 3H3"
    const val volume = "M4 9h3l5-4v14l-5-4H4zM16 9a4 4 0 0 1 0 6"
    const val queue = "M10 6h11M10 12h11M10 18h11M3 5l4 3-4 3z"
    val speaker = SVG.rect(6f, 3f, 10f, 18f, 2f) + SVG.circle(11f, 15f, 2.5f) + SVG.circle(11f, 7.5f, 1f)
    val more = SVG.circle(5f, 12f, 1.8f) + SVG.circle(12f, 12f, 1.8f) + SVG.circle(19f, 12f, 1.8f)
    val moreVertical = SVG.circle(12f, 5f, 1.9f) + SVG.circle(12f, 12f, 1.9f) + SVG.circle(12f, 19f, 1.9f)
    const val favList = "M4 6h16M4 12h10M4 18h7M17 14l3 3-3 3"
    const val check = "M5 12.5l4.2 4.2L19 7"
    const val tabHome = "M3 11l9-7 9 7M5 10v10h5v-6h4v6h5V10"
    val tabSound = "M5 4v6M5 14v6M12 4v3M12 11v9M19 4v9M19 17v3" + SVG.circle(5f, 12f, 2f) + SVG.circle(12f, 9f, 2f) + SVG.circle(19f, 15f, 2f)
    const val tabRooms = "M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z"
    val tabSettings = SVG.circle(12f, 12f, 3f) + "M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"
}
