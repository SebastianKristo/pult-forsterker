package no.kristo.skjold

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.core.spring
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.State
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableDoubleStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.withFrameNanos
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.delay
import kotlin.math.PI
import kotlin.math.floor
import kotlin.math.hypot
import kotlin.math.max
import kotlin.math.min
import kotlin.math.pow
import kotlin.math.sin

/**
 * Illustrasjonene i «Lag kassett»-veiviseren (V4KassettGuide.swift): tegnet med Canvas og animert med en
 * bildetakt-klokke (withFrameNanos), så de er skarpe på alle skjermer og ikke trenger bildefiler. Hver animasjon går
 * i en løkke og viser ett grep: hold telefonen mot kassetten, sett kassetten i spilleren, lim på etiketten, ferdig.
 */

// MARK: - Klokke og hjelpere

/** Sekunder siden visningen kom fram, oppdatert hver bildetakt (TimelineView(.animation) på iOS). */
@Composable
private fun rememberSekunder(): State<Double> {
    val t = remember { mutableDoubleStateOf(0.0) }
    LaunchedEffect(Unit) {
        val start = withFrameNanos { it }
        while (true) withFrameNanos { t.doubleValue = (it - start) / 1e9 }
    }
    return t
}

private fun clamp(x: Double): Double = min(1.0, max(0.0, x))
private fun ease(x: Double): Double = if (x < 0.5) 4 * x * x * x else 1 - (-2 * x + 2).pow(3) / 2
private fun frac(x: Double): Double = x - floor(x)

// MARK: - Kassetten

/**
 * Kassetten sett forfra: kropp, forsenkning for etiketten, etiketten, vindu med to spoler og trapesen nederst.
 * [spinn] i grader, [etikettPaa] 0 = ingen etikett … 1 = etiketten sitter, [glod] lysring (NFC-kontakt).
 * Bredden settes av [modifier]; høyden følger (1,58 : 1).
 */
@Composable
fun KassettFigur(
    modifier: Modifier = Modifier,
    etikett: String = "",
    under: String = "",
    spinn: Float = 0f,
    etikettPaa: Float = 1f,
    glod: Float = 0f,
) {
    BoxWithConstraints(modifier.aspectRatio(1.58f)) {
        val w = maxWidth
        val h = maxHeight
        // kropp med lysring og forsenkningen der etiketten limes
        Canvas(Modifier.fillMaxSize()) {
            val bw = size.width; val bh = size.height
            val r = bw * 0.06f
            if (glod > 0.01f) {
                for (i in 1..7) {
                    val inf = i * 3.dp.toPx()
                    drawRoundRect(
                        SourceTok.gold.copy(alpha = (0.55f * glod * (1f - i / 8f) * 0.32f).coerceIn(0f, 1f)),
                        topLeft = Offset(-inf, -inf), size = Size(bw + 2 * inf, bh + 2 * inf), cornerRadius = CornerRadius(r + inf),
                    )
                }
            }
            drawRoundRect(Brush.verticalGradient(listOf(hex(0x2c2c30), hex(0x19191b))), cornerRadius = CornerRadius(r))
            val sw = 1.dp.toPx()
            drawRoundRect(
                Color.White.copy(alpha = 0.12f), topLeft = Offset(sw / 2, sw / 2), size = Size(bw - sw, bh - sw),
                cornerRadius = CornerRadius(r), style = Stroke(sw),
            )
            drawRoundRect(
                Color.Black.copy(alpha = 0.35f), topLeft = Offset(bw * 0.08f, bh * 0.09f), size = Size(bw * 0.84f, bh * 0.58f),
                cornerRadius = CornerRadius(bw * 0.035f),
            )
        }
        // etiketten (faller ned ovenfra når etikettPaa går mot 1)
        if (etikettPaa > 0.001f) {
            EtikettFlate(
                etikett, under, w, h,
                Modifier.offset(x = w * 0.08f, y = h * 0.09f - h * (0.9f * (1f - etikettPaa)))
                    .size(w * 0.84f, h * 0.58f).alpha(etikettPaa.coerceIn(0f, 1f)),
            )
        }
        // vinduet med spolene, trapesen nederst og skruehullene
        Canvas(Modifier.fillMaxSize()) {
            val bw = size.width; val bh = size.height
            val sw = 1.dp.toPx()
            val vr = CornerRadius(bh * 0.08f)
            drawRoundRect(hex(0x0d0d0e), topLeft = Offset(bw * 0.25f, bh * 0.32f), size = Size(bw * 0.5f, bh * 0.2f), cornerRadius = vr)
            drawRoundRect(
                Color.White.copy(alpha = 0.1f), topLeft = Offset(bw * 0.25f + sw / 2, bh * 0.32f + sw / 2),
                size = Size(bw * 0.5f - sw, bh * 0.2f - sw), cornerRadius = vr, style = Stroke(sw),
            )
            spole(Offset(bw * 0.36f, bh * 0.42f), bh * 0.075f, spinn)
            spole(Offset(bw * 0.64f, bh * 0.42f), bh * 0.075f, spinn)
            val l = bw * 0.19f; val rr = bw * 0.81f; val top = bh * 0.78f; val bot = bh * 0.98f
            val tw = rr - l
            val bunn = Path().apply {
                moveTo(l + tw * 0.1f, top); lineTo(rr - tw * 0.1f, top); lineTo(rr, bot); lineTo(l, bot); close()
            }
            drawPath(bunn, hex(0x242427))
            drawPath(bunn, Color.White.copy(alpha = 0.08f), style = Stroke(sw))
            for (x in listOf(0.12f, 0.88f)) drawCircle(Color.Black.copy(alpha = 0.5f), bw * 0.0175f, Offset(bw * x, bh * 0.1f))
        }
    }
}

private fun DrawScope.spole(c: Offset, r: Float, spinn: Float) {
    val mork = hex(0x1a1a1a)
    drawCircle(hex(0xe9e4d8), r, c)
    rotate(spinn, pivot = c) {
        for (i in 0 until 6) {
            rotate(i * 60f, pivot = c) {
                drawRoundRect(
                    mork, topLeft = Offset(c.x - r * 0.13f, c.y - r * 0.81f), size = Size(r * 0.26f, r * 0.62f),
                    cornerRadius = CornerRadius(r * 0.13f),
                )
            }
        }
    }
    drawCircle(mork, r * 0.275f, c)
}

@Composable
private fun EtikettFlate(etikett: String, under: String, w: Dp, h: Dp, modifier: Modifier) {
    // tegningen skal ikke vokse med systemets tekststørrelse
    val fs = LocalDensity.current.fontScale
    Box(modifier.clip(RoundedCornerShape(w * 0.03f)).background(Brush.verticalGradient(listOf(hex(0xf3ead6), hex(0xe4d6b8))))) {
        Box(Modifier.fillMaxWidth().height(h * 0.05f).background(SourceTok.goldDark))
        Box(Modifier.align(Alignment.BottomCenter).fillMaxWidth().height(h * 0.03f).background(hex(0xc94f3d)))
        Column(Modifier.padding(start = w * 0.04f, end = w * 0.04f, top = h * 0.08f), verticalArrangement = Arrangement.spacedBy(1.dp)) {
            T(etikett.ifEmpty { "Skjold" }, sora(max(8f, h.value * 0.085f) / fs, W.Semibold, hex(0x1d1a14), lineHeight = 1.1f), maxLines = 1)
            if (under.isNotEmpty()) T(under, sora(max(6f, h.value * 0.055f) / fs, W.Regular, hex(0x5b5244), lineHeight = 1.1f), maxLines = 1)
        }
    }
}

// MARK: - Telefonen (baksiden) og NFC-bølgene

/** Baksiden av en Android-telefon med kameraøy. NFC-antennen sitter midt på baksiden; den lyser ved [kontakt]. */
@Composable
private fun TelefonBakside(kontakt: Float, modifier: Modifier) {
    Canvas(modifier.aspectRatio(0.49f)) {
        val w = size.width; val h = size.height
        val sw = 1.dp.toPx()
        drawRoundRect(Brush.verticalGradient(listOf(hex(0x3a3a3e), hex(0x2a2a2d))), cornerRadius = CornerRadius(w * 0.2f))
        drawRoundRect(
            Color.White.copy(alpha = 0.14f), topLeft = Offset(sw / 2, sw / 2), size = Size(w - sw, h - sw),
            cornerRadius = CornerRadius(w * 0.2f), style = Stroke(sw),
        )
        // kameraøya oppe til venstre
        drawRoundRect(hex(0x1f1f22), topLeft = Offset(w * 0.1f, w * 0.1f), size = Size(w * 0.42f, w * 0.5f), cornerRadius = CornerRadius(w * 0.12f))
        for (y in listOf(0.23f, 0.47f)) {
            drawCircle(hex(0x0b0b0c), w * 0.085f, Offset(w * 0.24f, w * y))
            drawCircle(Color.White.copy(alpha = 0.18f), w * 0.085f, Offset(w * 0.24f, w * y), style = Stroke(sw))
        }
        drawCircle(hex(0xe9e4d8).copy(alpha = 0.7f), w * 0.03f, Offset(w * 0.42f, w * 0.23f))
        // NFC-antennen
        val c = Offset(w / 2, h * 0.5f)
        drawCircle(Color.White.copy(alpha = 0.06f), w * 0.2f, c, style = Stroke(sw))
        if (kontakt > 0.01f) {
            drawCircle(SourceTok.gold.copy(alpha = 0.18f * kontakt), w * 0.2f, c)
            drawCircle(SourceTok.gold.copy(alpha = 0.8f * kontakt), w * 0.2f, c, style = Stroke(1.5.dp.toPx()))
        }
    }
}

/** Bølger som sendes ut fra et punkt (NFC). [t] 0…1 i syklusen. */
private fun DrawScope.nfcBolger(c: Offset, t: Float, styrke: Float) {
    for (i in 0 until 3) {
        val f = ((t + i / 3f) % 1f)
        val d = (20f + f * 90f).dp.toPx()
        drawCircle(SourceTok.gold.copy(alpha = ((1f - f) * 0.8f * styrke).coerceIn(0f, 1f)), d / 2, c, style = Stroke(2.dp.toPx()))
    }
}

// MARK: - Animasjonene

/**
 * «Hold baksiden av telefonen mot kassetten»: telefonen (baksiden ned) senkes flatt ned på kassetten – den vippes
 * rett og blir litt mindre, som om den legges ned mot bordet – bølger, kassetten lyser.
 */
@Composable
fun KassettNFCAnimasjon(etikett: String = "") {
    val sek by rememberSekunder()
    val t = frac(sek / 3.4)
    val ned = ease(clamp((t - 0.05) / 0.35))               // telefonen kommer ned
    val opp = ease(clamp((t - 0.8) / 0.18))                 // og løftes igjen
    val pos = (ned - opp).toFloat()
    val kontakt = (clamp((t - 0.4) / 0.08) * (1 - clamp((t - 0.78) / 0.06))).toFloat()
    val bolge = frac(sek / 1.1).toFloat()
    Box(
        Modifier.fillMaxWidth().height(260.dp).semantics { contentDescription = "Animasjon: hold baksiden av telefonen mot kassetten" },
        contentAlignment = Alignment.Center,
    ) {
        KassettFigur(Modifier.offset(y = 50.dp).width(200.dp), etikett = etikett, glod = kontakt)
        // skyggen fra telefonen på kassetten
        Canvas(Modifier.offset(y = 50.dp).size(150.dp, 120.dp)) {
            if (pos > 0.01f) drawOval(
                Brush.radialGradient(listOf(Color.Black.copy(alpha = 0.5f * pos), Color.Transparent)),
                topLeft = Offset.Zero, size = size,
            )
        }
        TelefonBakside(
            kontakt,
            Modifier.offset(y = (-40f + pos * 90f).dp).width(72.dp).graphicsLayer {
                rotationX = (1f - pos) * 38f
                val s = 1.12f - 0.12f * pos
                scaleX = s; scaleY = s
                cameraDistance = 12f * density
            },
        )
        if (kontakt > 0.01f) Canvas(Modifier.offset(y = 50.dp).size(120.dp)) { nfcBolger(center, bolge, kontakt) }
    }
}

/** «Sett kassetten inn i spilleren»: kassetten glir ned i luka på Skjold Kassett, lampen blir grønn. */
@Composable
fun KassettSpillerAnimasjon(etikett: String = "") {
    val sek by rememberSekunder()
    val t = frac(sek / 3.6)
    val inn = (ease(clamp((t - 0.08) / 0.4)) - ease(clamp((t - 0.86) / 0.12))).toFloat()
    val lest = (clamp((t - 0.5) / 0.05) * (1 - clamp((t - 0.84) / 0.04))).toFloat()
    Box(
        Modifier.fillMaxWidth().height(260.dp).clipToBounds()
            .semantics { contentDescription = "Animasjon: sett kassetten inn i Skjold Kassett-spilleren" },
        contentAlignment = Alignment.TopCenter,
    ) {
        KassettFigur(Modifier.offset(y = (inn * 96f).dp).width(170.dp), etikett = etikett, spinn = (sek * 160.0 * lest).toFloat() % 360f)
        // spilleren foran kassetten (luka skjuler den nederste delen)
        Box(Modifier.offset(y = 150.dp).size(230.dp, 96.dp)) {
            Canvas(Modifier.fillMaxSize()) {
                val r = CornerRadius(22.dp.toPx())
                val sw = 1.dp.toPx()
                drawRoundRect(Brush.verticalGradient(listOf(hex(0x2a2a2e), hex(0x161618))), cornerRadius = r)
                drawRoundRect(
                    Color.White.copy(alpha = 0.12f), topLeft = Offset(sw / 2, sw / 2), size = Size(size.width - sw, size.height - sw),
                    cornerRadius = r, style = Stroke(sw),
                )
                val lw = 190.dp.toPx(); val lh = 10.dp.toPx()
                drawRoundRect(Color.Black, topLeft = Offset((size.width - lw) / 2, 14.dp.toPx()), size = Size(lw, lh), cornerRadius = CornerRadius(lh / 2))
            }
            Row(
                Modifier.align(Alignment.TopCenter).padding(top = 54.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically,
            ) {
                Box(
                    Modifier.size(8.dp)
                        .drawBehind { if (lest > 0.01f) drawCircle(SourceTok.green.copy(alpha = 0.45f * lest), size.minDimension * 1.3f) }
                        .clip(CircleShape).background(if (lest > 0.5f) SourceTok.green else hex(0x3a3a3c)),
                )
                T(if (lest > 0.5f) "LEST" else "SKJOLD KASSETT", mono(9f, SourceTok.muted, 0.16f), maxLines = 1)
            }
        }
    }
}

/** «Lim etiketten i forsenkningen»: etiketten senkes ned på kassetten og trykkes fast. */
@Composable
fun KassettEtikettAnimasjon(etikett: String = "", under: String = "") {
    val sek by rememberSekunder()
    val t = frac(sek / 3.2)
    val paa = ease(clamp((t - 0.1) / 0.45))
    val ut = clamp((t - 0.9) / 0.1)
    val sc = (1 + 0.03 * sin(clamp((t - 0.55) / 0.12) * PI)).toFloat()
    Box(
        Modifier.fillMaxWidth().height(170.dp).semantics { contentDescription = "Animasjon: lim etiketten i forsenkningen på kassetten" },
        contentAlignment = Alignment.Center,
    ) {
        KassettFigur(
            Modifier.width(210.dp).graphicsLayer { scaleX = sc; scaleY = sc },
            etikett = etikett, under = under, etikettPaa = (paa * (1 - ut)).toFloat(),
        )
    }
}

/** Kassetten med etiketten som spiller (spolene går) og svever litt: forsiden av veiviseren. */
@Composable
fun KassettHelt(etikett: String = "Skjold", under: String = "") {
    val sek by rememberSekunder()
    val vipp = sin(sek / 2.2).toFloat()
    val sveve = sin(sek / 1.7).toFloat()
    Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
        KassettFigur(
            Modifier.width(230.dp).graphicsLayer {
                rotationY = vipp * 7f
                rotationX = vipp * 1.4f
                translationY = sveve * 4f * density
                cameraDistance = 10f * density
            },
            etikett = etikett, under = under, spinn = ((sek * 90.0) % 360.0).toFloat(),
        )
    }
}

/** Grønn hake som tegnes opp (ferdig). */
@Composable
fun KassettFerdigHake() {
    val vis = remember { Animatable(0f) }
    LaunchedEffect(Unit) {
        Haptics.success()
        delay(100)
        vis.animateTo(1f, spring(dampingRatio = 0.75f, stiffness = 80f))
    }
    val gronn = SourceTok.green
    Canvas(Modifier.size(96.dp).semantics { contentDescription = "Ferdig" }) {
        val v = vis.value
        val trim = v.coerceIn(0f, 1f)
        val c = center
        drawCircle(gronn.copy(alpha = 0.14f), size.minDimension / 2 * (0.6f + 0.4f * v), c)
        val r = 42.dp.toPx()
        if (trim > 0f) drawArc(
            gronn, startAngle = -90f, sweepAngle = 360f * trim, useCenter = false,
            topLeft = Offset(c.x - r, c.y - r), size = Size(2 * r, 2 * r), style = Stroke(4.dp.toPx(), cap = StrokeCap.Round),
        )
        // haken: 40 × 30, tegnes fra venstre
        val hw = 40.dp.toPx(); val hh = 30.dp.toPx()
        val l = c.x - hw / 2; val tp = c.y - hh / 2
        val p0 = Offset(l, tp + hh / 2)
        val p1 = Offset(l + hw * 0.36f, tp + hh)
        val p2 = Offset(l + hw, tp)
        val l1 = hypot(p1.x - p0.x, p1.y - p0.y)
        val l2 = hypot(p2.x - p1.x, p2.y - p1.y)
        val d = trim * (l1 + l2)
        if (d > 0f) {
            val hake = Path().apply {
                moveTo(p0.x, p0.y)
                if (d <= l1) {
                    val e = p0 + (p1 - p0) * (d / l1)
                    lineTo(e.x, e.y)
                } else {
                    lineTo(p1.x, p1.y)
                    val e = p1 + (p2 - p1) * ((d - l1) / l2)
                    lineTo(e.x, e.y)
                }
            }
            drawPath(hake, gronn, style = Stroke(6.dp.toPx(), cap = StrokeCap.Round, join = StrokeJoin.Round))
        }
    }
}

/** Prikker øverst som viser hvor langt du er kommet. */
@Composable
fun KassettStegPrikker(steg: Int, antall: Int) {
    Row(
        Modifier.semantics { contentDescription = "Steg ${steg + 1} av $antall" },
        horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically,
    ) {
        for (i in 0 until antall) {
            val bredde by animateDpAsState(if (i == steg) 18.dp else 6.dp, label = "stegprikk")
            val farge by animateColorAsState(
                if (i == steg) SourceTok.gold else SourceTok.ink.copy(alpha = if (i < steg) 0.5f else 0.18f), label = "stegfarge",
            )
            Box(Modifier.size(bredde, 6.dp).clip(CircleShape).background(farge))
        }
    }
}

/** Ikoner til forklaringsradene (viewBox 24, strek). */
object KassettIkon {
    val musikk = "M3 6h10M3 11h10M3 16h6M18 16V5l4-1.5" + SVG.circle(16f, 16f, 2f)
    val nfc = "M8.5 9a4 4 0 0 1 0 6M12 6.5a7.5 7.5 0 0 1 0 11M15.5 4a11 11 0 0 1 0 16" + SVG.circle(4.5f, 12f, 1.3f)
    val settInn = SVG.rect(4f, 11f, 16f, 10f, 2f) + "M12 2v8M9 7l3 3 3-3"
    val skriver = "M7 9V3h10v6M7 17H4v-7a1 1 0 0 1 1-1h14a1 1 0 0 1 1 1v7h-3" + SVG.rect(7f, 14f, 10f, 7f)
    val info = SVG.circle(12f, 12f, 9f) + "M12 11v6M12 7.5v0.5"
    const val del = "M12 3v12M8 7l4-4 4 4M5 12v7a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-7"
}

/** Én forklaringsrad med ikon (som i Apples oppsettsskjermer). Med [nummer] vises et tall i en ring i stedet for ikonet. */
@Composable
fun KassettForklaring(ikon: String, tittel: String, tekst: String, nummer: Int? = null) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(14.dp), verticalAlignment = Alignment.Top) {
        Box(Modifier.width(34.dp), contentAlignment = Alignment.TopCenter) {
            if (nummer != null) {
                Box(Modifier.size(24.dp).skCapsuleBorder(SourceTok.gold, 1.6.dp), contentAlignment = Alignment.Center) {
                    T("$nummer", sora(12f, W.Semibold, SourceTok.gold), maxLines = 1)
                }
            } else {
                SKIcon(ikon, 24.dp, 1.7f, SourceTok.gold)
            }
        }
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
            T(tittel, sora(15f, W.Semibold))
            T(tekst, sora(13f, W.Regular, SourceTok.body, lineHeight = 1.4f))
        }
    }
}
