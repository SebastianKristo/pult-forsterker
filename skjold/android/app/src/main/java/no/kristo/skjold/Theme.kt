package no.kristo.skjold

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicText
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.composed
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.draw.drawWithCache
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.LineHeightStyle
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.pow
import kotlin.math.sin

// MARK: - Design tokens (Theme.swift / XCODE_BYGG.md)

fun hex(h: Long, alpha: Float = 1f): Color =
    Color(((h shr 16) and 0xff).toInt(), ((h shr 8) and 0xff).toInt(), (h and 0xff).toInt(), (alpha * 255).toInt())

object C {
    val bg = hex(0x0b0b0c)
    val card = hex(0x141415)
    val card2 = hex(0x1b1b1c)
    val line = hex(0x242426)
    val line2 = hex(0x2e2e30)
    val ink = hex(0xf2f2ee)
    val ink2 = hex(0xc9c9c4)
    val muted = hex(0x8b8b86)
    val accent = hex(0xd9a441)
    val accent2 = hex(0xf0c46a)
    val selBg = hex(0x1c170d)
    val selLine = hex(0x5a4420)
    val ok = hex(0x6fcf7f)
    val live = hex(0xe05a4a)
    val off = hex(0x3a3a37)

    val body = hex(0xa9a9a3)
    val dim = hex(0x55554f)
    val seg = hex(0x2a2a2c)
    val selBg2 = hex(0x2a2112)
    val danger = hex(0xff8a7a)
    val dots = hex(0x2a2a28)
}

/** Colours for the shared "selected" state (sel() in the design file). */
data class SelStyle(val bd: Color, val bg: Color, val fg: Color) {
    companion object {
        fun of(on: Boolean) = if (on) SelStyle(C.accent, C.selBg, C.accent2) else SelStyle(C.line2, C.card, C.ink)
    }
}

// MARK: - Fonts

enum class W { Light, Regular, Semibold, Medium }

val SoraFamily = FontFamily(
    Font(R.font.sora_light, FontWeight.Light),
    Font(R.font.sora_regular, FontWeight.Normal),
    Font(R.font.sora_semibold, FontWeight.SemiBold),
)
val PlexMono = FontFamily(
    Font(R.font.plexmono_regular, FontWeight.Normal),
    Font(R.font.plexmono_medium, FontWeight.Medium),
)

private val tightLines = LineHeightStyle(LineHeightStyle.Alignment.Center, LineHeightStyle.Trim.None)

/** Sora text style. `lineHeight` is the CSS multiplier (1.15, 1.5 …). */
fun sora(size: Float, weight: W = W.Regular, color: Color = C.ink, lineHeight: Float? = null) = TextStyle(
    fontFamily = SoraFamily,
    fontWeight = when (weight) { W.Light -> FontWeight.Light; W.Semibold, W.Medium -> FontWeight.SemiBold; else -> FontWeight.Normal },
    fontSize = size.sp,
    color = color,
    lineHeight = (lineHeight ?: 1.26f).em,
    lineHeightStyle = tightLines,
)

/** IBM Plex Mono label, letter-spacing in em like the CSS. */
fun mono(size: Float, color: Color = C.muted, em: Float = 0f, weight: W = W.Regular) = TextStyle(
    fontFamily = PlexMono,
    fontWeight = if (weight == W.Medium || weight == W.Semibold) FontWeight.Medium else FontWeight.Normal,
    fontSize = size.sp,
    color = color,
    letterSpacing = em.em,
)

/** Plain text (no Material defaults). */
@Composable
fun T(
    text: String,
    style: TextStyle,
    modifier: Modifier = Modifier,
    maxLines: Int = Int.MAX_VALUE,
    align: TextAlign? = null,
) {
    BasicText(
        text = text,
        modifier = modifier,
        style = if (align != null) style.copy(textAlign = align) else style,
        maxLines = maxLines,
        overflow = if (maxLines == Int.MAX_VALUE) TextOverflow.Clip else TextOverflow.Ellipsis,
        softWrap = true,
    )
}

// MARK: - Modifiers

fun Modifier.skBorder(color: Color, radius: Dp, width: Dp = 1.dp, dash: List<Float> = emptyList()): Modifier =
    this.drawBehind {
        val w = width.toPx()
        val r = radius.toPx()
        drawRoundRect(
            color = color,
            topLeft = Offset(w / 2, w / 2),
            size = Size(size.width - w, size.height - w),
            cornerRadius = CornerRadius((r - w / 2).coerceAtLeast(0f)),
            style = Stroke(width = w, pathEffect = if (dash.isEmpty()) null else PathEffect.dashPathEffect(dash.map { it * density }.toFloatArray())),
        )
    }

fun Modifier.skCapsuleBorder(color: Color, width: Dp = 1.dp): Modifier = this.drawBehind {
    val w = width.toPx()
    drawRoundRect(color, Offset(w / 2, w / 2), Size(size.width - w, size.height - w), CornerRadius(size.height / 2), style = Stroke(w))
}

/** Card: background + border + radius. */
fun Modifier.skBox(bg: Color, bd: Color, radius: Dp = 14.dp): Modifier =
    this.clip(RoundedCornerShape(radius)).background(bg, RoundedCornerShape(radius)).skBorder(bd, radius)

/** CSS `border-top: 1px solid …` used for list rows. */
fun Modifier.topLine(color: Color): Modifier = this.drawBehind {
    if (color.alpha > 0f) drawRect(color, Offset.Zero, Size(size.width, 1.dp.toPx()))
}

/** Plain press (PlainPress): no ripple, 0.75 opacity while pressed and a light haptic on touch-down. */
fun Modifier.press(enabled: Boolean = true, onClick: () -> Unit): Modifier = composed {
    val src = remember { MutableInteractionSource() }
    val pressed by src.collectIsPressedAsState()
    LaunchedEffect(pressed) { if (pressed) Haptics.tap() }
    this
        .alpha(if (pressed) 0.75f else 1f)
        .clickable(interactionSource = src, indication = null, enabled = enabled, onClick = onClick)
}

// MARK: - OKLCH (generated cover art)

object OKLCH {
    data class Lab(val L: Double, val a: Double, val b: Double)

    fun lab(L: Double, Cc: Double, h: Double): Lab {
        val r = h * Math.PI / 180
        return Lab(L, Cc * cos(r), Cc * sin(r))
    }

    fun color(lab: Lab): Color {
        val l_ = lab.L + 0.3963377774 * lab.a + 0.2158037573 * lab.b
        val m_ = lab.L - 0.1055613458 * lab.a - 0.0638541728 * lab.b
        val s_ = lab.L - 0.0894841775 * lab.a - 1.2914855480 * lab.b
        val l = l_ * l_ * l_; val m = m_ * m_ * m_; val s = s_ * s_ * s_
        val r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
        val g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
        val b = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
        fun enc(x: Double): Float {
            val v = x.coerceIn(0.0, 1.0)
            return (if (v <= 0.0031308) 12.92 * v else 1.055 * v.pow(1 / 2.4) - 0.055).toFloat()
        }
        return Color(enc(r), enc(g), enc(b), 1f)
    }

    fun color(L: Double, Cc: Double, h: Double) = color(lab(L, Cc, h))

    /** CSS interpolates oklch gradients in Oklab; approximate with extra stops. */
    fun stops(a: Lab, b: Lab, count: Int = 6): List<Pair<Float, Color>> = (0..count).map { i ->
        val t = i.toDouble() / count
        Pair(t.toFloat(), color(Lab(a.L + (b.L - a.L) * t, a.a + (b.a - a.a) * t, a.b + (b.b - a.b) * t)))
    }
}

/** CSS `linear-gradient(<angle>deg, …)` that keeps the correct angle for any size. */
fun Modifier.cssGradient(angle: Double, stops: List<Pair<Float, Color>>): Modifier = this.drawWithCache {
    val w = size.width.coerceAtLeast(1f); val h = size.height.coerceAtLeast(1f)
    val a = angle * Math.PI / 180
    val dx = sin(a).toFloat(); val dy = -cos(a).toFloat()
    val len = (abs(w * sin(a)) + abs(h * cos(a))).toFloat()
    val start = Offset(w / 2 - dx * len / 2, h / 2 - dy * len / 2)
    val end = Offset(w / 2 + dx * len / 2, h / 2 + dy * len / 2)
    val brush = Brush.linearGradient(*stops.toTypedArray(), start = start, end = end)
    onDrawBehind { drawRect(brush) }
}

fun mix(a: Color, b: Color, t: Float): Color = Color(
    a.red + (b.red - a.red) * t, a.green + (b.green - a.green) * t, a.blue + (b.blue - a.blue) * t, a.alpha + (b.alpha - a.alpha) * t,
)
