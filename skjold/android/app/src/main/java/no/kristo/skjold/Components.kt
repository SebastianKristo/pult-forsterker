package no.kristo.skjold

import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.detectVerticalDragGestures
import androidx.compose.foundation.gestures.drag
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.layout.layout
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import androidx.compose.runtime.rememberUpdatedState
import kotlin.math.floor
import kotlin.math.roundToInt

// Components drawn by hand to match the design 1:1 (Components.swift) – no Material widgets.

// MARK: - Text helpers

@Composable
fun SKMonoLabel(text: String, color: Color = C.muted, size: Float = 10f, modifier: Modifier = Modifier) =
    T(text, mono(size, color, 0.12f), modifier)

@Composable
fun SKSectionHeader(title: String, size: Float = 17f, kicker: String? = null) {
    Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(2.dp)) {
        if (!kicker.isNullOrEmpty()) SKMonoLabel(kicker)
        T(title, sora(size, W.Semibold))
    }
}

// MARK: - Buttons

enum class SKButtonKind { PRIMARY, SECONDARY, DISABLED }

@Composable
fun SKButton(title: String, kind: SKButtonKind = SKButtonKind.PRIMARY, height: Dp = 52.dp, size: Float = 15f, radius: Dp = 14.dp, modifier: Modifier = Modifier, action: () -> Unit) {
    val bg = when (kind) { SKButtonKind.PRIMARY -> C.accent; SKButtonKind.DISABLED -> C.line; else -> Color.Transparent }
    val fg = when (kind) { SKButtonKind.PRIMARY -> C.bg; SKButtonKind.DISABLED -> C.muted; else -> C.ink }
    Box(
        modifier.fillMaxWidth().height(height).clip(RoundedCornerShape(radius)).background(bg)
            .then(if (kind == SKButtonKind.SECONDARY) Modifier.skBorder(C.line2, radius) else Modifier)
            .press(onClick = action),
        contentAlignment = Alignment.Center,
    ) { T(title, sora(size, if (kind == SKButtonKind.SECONDARY) W.Regular else W.Semibold, fg)) }
}

/** Gold text button ("Tilbake", "Administrer", …). */
@Composable
fun SKLinkButton(title: String, size: Float = 13f, color: Color = C.accent, modifier: Modifier = Modifier, action: () -> Unit) =
    T(title, sora(size, W.Regular, color), modifier.press(onClick = action))

/** "‹ Hjem" style back link. */
@Composable
fun SKBackButton(title: String, modifier: Modifier = Modifier, action: () -> Unit) {
    Row(modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Row(Modifier.press(onClick = action), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            SKIcon(Icons.back, 16.dp, 2f, C.accent)
            T(title, sora(14f, W.Regular, C.accent))
        }
    }
}

/** Pill with gold primary fill (Spill) or outline. */
@Composable
fun SKPill(
    title: String, primary: Boolean = false, icon: String? = null, height: Dp = 38.dp, hPad: Dp = 16.dp,
    border: Color = C.line2, bg: Color = Color.Transparent, fg: Color = C.ink, action: () -> Unit,
) {
    Row(
        Modifier.height(height).clip(CircleShape).background(if (primary) C.accent else bg)
            .then(if (!primary) Modifier.skCapsuleBorder(border) else Modifier)
            .press(onClick = action).padding(horizontal = hPad),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        if (icon != null) SKIcon(icon, 12.dp, color = C.bg, fill = true)
        T(title, sora(13f, if (primary) W.Semibold else W.Regular, if (primary) C.bg else fg), maxLines = 1)
    }
}

// MARK: - Fields

@Composable
fun SKField(
    placeholder: String, text: String, onChange: (String) -> Unit, modifier: Modifier = Modifier,
    height: Dp = 48.dp, size: Float = 16f, radius: Dp = 12.dp, border: Color = C.line2, bg: Color = C.card,
    secure: Boolean = false, mono: Boolean = false, keyboard: KeyboardType = KeyboardType.Text, plainInput: Boolean = false, maxLength: Int? = null,
) {
    val style = if (mono) no.kristo.skjold.mono(size, C.ink) else sora(size, W.Regular, C.ink)
    BasicTextField(
        value = text,
        onValueChange = { v -> onChange(if (maxLength != null && v.length > maxLength) v.take(maxLength) else v) },
        singleLine = true,
        textStyle = style,
        cursorBrush = SolidColor(C.accent),
        visualTransformation = if (secure) PasswordVisualTransformation() else VisualTransformation.None,
        keyboardOptions = KeyboardOptions(
            capitalization = if (plainInput || secure) KeyboardCapitalization.None else KeyboardCapitalization.Sentences,
            autoCorrectEnabled = !plainInput && !secure,
            keyboardType = if (secure) KeyboardType.Password else keyboard,
        ),
        modifier = modifier.fillMaxWidth().height(height).clip(RoundedCornerShape(radius)).background(bg).skBorder(border, radius),
        decorationBox = { inner ->
            Box(Modifier.fillMaxSize().padding(horizontal = 14.dp), contentAlignment = Alignment.CenterStart) {
                if (text.isEmpty()) T(placeholder, (if (mono) no.kristo.skjold.mono(size, C.dim) else sora(size, W.Regular, C.dim)), maxLines = 1)
                inner()
            }
        },
    )
}

// MARK: - Chips

@Composable
fun SKChip(
    label: String, on: Boolean = false, height: Dp? = null, hPad: Dp = 12.dp, vPad: Dp = 8.dp, size: Float = 12f,
    radius: Dp = 999.dp, style: SelStyle? = null, trailingDot: Color? = null, leadingNumber: String? = null, action: () -> Unit,
) {
    val s = style ?: SelStyle.of(on)
    val shape = RoundedCornerShape(if (radius > 200.dp) 200.dp else radius)
    Row(
        Modifier.then(if (height != null) Modifier.height(height) else Modifier).clip(shape).background(s.bg).border(1.dp, s.bd, shape)
            .press(onClick = action).padding(horizontal = hPad, vertical = if (height == null) vPad else 0.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        if (leadingNumber != null) T(leadingNumber, mono(10f, s.fg.copy(alpha = 0.7f)))
        T(label, sora(size, W.Regular, s.fg), maxLines = 1)
        if (trailingDot != null) Box(Modifier.size(6.dp).clip(CircleShape).background(trailingDot))
    }
}

/** Black/white filter chips (genres, moods): selected = ink background. */
@Composable
fun SKFilterChip(label: String, on: Boolean, hPad: Dp = 14.dp, action: () -> Unit) =
    SKChip(label, height = 34.dp, hPad = hPad, size = 13f, radius = 8.dp,
        style = SelStyle(if (on) C.ink else C.line2, if (on) C.ink else C.card2, if (on) C.bg else C.ink), action = action)

// MARK: - Segmented

@Composable
fun SKSegmented(
    items: List<String>, selected: Int, height: Dp = 36.dp, bg: Color = C.card, border: Color? = C.line,
    selBg: Color = C.seg, selFg: Color = C.ink, fg: Color = C.muted, pick: (Int) -> Unit,
) {
    Row(
        Modifier.fillMaxWidth().clip(RoundedCornerShape(10.dp)).background(bg)
            .then(if (border != null) Modifier.skBorder(border, 10.dp) else Modifier).padding(3.dp),
        horizontalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        items.forEachIndexed { i, n ->
            Box(
                Modifier.weight(1f).height(height).clip(RoundedCornerShape(8.dp)).background(if (i == selected) selBg else Color.Transparent)
                    .press { pick(i) },
                contentAlignment = Alignment.Center,
            ) { T(n, sora(13f, W.Semibold, if (i == selected) selFg else fg), maxLines = 1) }
        }
    }
}

// MARK: - Toggle

@Composable
fun SKToggle(on: Boolean, onColor: Color = C.accent, action: () -> Unit) {
    val x by animateDpAsState(if (on) 21.dp else 3.dp, tween(150), label = "toggle")
    Box(Modifier.size(46.dp, 28.dp).clip(CircleShape).background(if (on) onColor else C.off).press(onClick = action)) {
        Box(Modifier.offset(x = x, y = 3.dp).size(22.dp).clip(CircleShape).background(C.ink))
    }
}

// MARK: - Slider (CSS range input with accent-color)

@Composable
fun SKSlider(value: Double, onChange: (Double) -> Unit, range: ClosedFloatingPointRange<Double> = 0.0..100.0, step: Double = 1.0, tint: Color = C.accent, modifier: Modifier = Modifier) {
    val thumb = 17.dp; val track = 5.dp
    val cb by rememberUpdatedState(onChange)
    val curValue by rememberUpdatedState(value)
    Canvas(
        modifier.fillMaxWidth().height(16.dp).pointerInput(range, step) {
            awaitEachGesture {
                var last = curValue
                fun upd(px: Float) {
                    val t = thumb.toPx()
                    val len = size.width - t
                    val p = ((px - t / 2) / len).coerceIn(0f, 1f)
                    val raw = range.start + p * (range.endInclusive - range.start)
                    val v = (raw / step).roundToInt() * step
                    if (v != last) {
                        detentHaptic(range, step, last, v)
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
        val t = thumb.toPx(); val tr = track.toPx()
        val len = size.width - t
        val frac = ((value - range.start) / (range.endInclusive - range.start)).toFloat().coerceIn(0f, 1f)
        val c = t / 2 + len * frac
        val cy = size.height / 2
        drawRoundRect(hex(0x4a4a4c), Offset(0f, cy - tr / 2), Size(size.width, tr), CornerRadius(tr / 2))
        drawRoundRect(tint, Offset(0f, cy - tr / 2), Size(c, tr), CornerRadius(tr / 2))
        drawCircle(Color.Black.copy(alpha = 0.3f), t / 2, Offset(c, cy + 0.5.dp.toPx()))
        drawCircle(tint, t / 2, Offset(c, cy))
    }
}

/** Small ranges tick on every step; large ranges (volume) every 10. Ends and centre give a firmer bump. */
private fun detentHaptic(range: ClosedFloatingPointRange<Double>, step: Double, old: Double, new: Double) {
    val span = range.endInclusive - range.start
    if (new == range.start || new == range.endInclusive || (range.start < 0 && new == 0.0)) { Haptics.bump(); return }
    val every = if (span > 30) 10.0 else step
    if (floor(old / every) != floor(new / every)) Haptics.tick()
}

// MARK: - Layout helpers

/** Horizontal scroller that bleeds to the screen edges (margin 0 -20px; padding 0 20px). */
@Composable
fun EdgeScroll(spacing: Dp = 12.dp, inset: Dp = 20.dp, alignment: Alignment.Vertical = Alignment.Top, content: @Composable RowScope.() -> Unit) {
    Row(
        Modifier
            .layout { measurable, constraints ->
                val extra = inset.roundToPx() * 2
                val w = constraints.maxWidth + extra
                val p = measurable.measure(constraints.copy(minWidth = w, maxWidth = w))
                layout(constraints.maxWidth, p.height) { p.place(-extra / 2, 0) }
            }
            .horizontalScroll(rememberScrollState())
            .padding(horizontal = inset),
        horizontalArrangement = Arrangement.spacedBy(spacing),
        verticalAlignment = alignment,
        content = content,
    )
}

/** flex-wrap row (FlowLayout). */
@OptIn(ExperimentalLayoutApi::class)
@Composable
fun Flow(spacing: Dp = 6.dp, lineSpacing: Dp? = null, modifier: Modifier = Modifier, content: @Composable () -> Unit) {
    FlowRow(modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(spacing), verticalArrangement = Arrangement.spacedBy(lineSpacing ?: spacing)) { content() }
}

/** OPPSETT · 1 AV 4: 5-column grid with 4 bars, as in the design. */
@Composable
fun SKProgressSteps(step: Int, count: Int = 4) {
    BoxWithConstraints(Modifier.fillMaxWidth().height(3.dp)) {
        val w = (maxWidth - 16.dp) / 5
        Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            for (i in 0 until count) Box(Modifier.size(w, 3.dp).clip(RoundedCornerShape(2.dp)).background(if (i <= step) C.accent else C.dots))
        }
    }
}

// MARK: - Source logo (Kilder)

data class SourceStyle(val bg: @Composable (Modifier) -> Unit, val fg: Color, val stroke: String = "", val fillPath: String = "", val brand: String = "", val size: Float)

object SourceLogos {
    const val spotify = "M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.160 5.16 9.301c-.6.179-1.2-.181-1.380-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.020.599-1.559.3z"
    const val ytm = "M12 0C5.376 0 0 5.376 0 12s5.376 12 12 12 12-5.376 12-12S18.624 0 12 0zm0 19.104c-3.924 0-7.104-3.18-7.104-7.104S8.076 4.896 12 4.896s7.104 3.18 7.104 7.104-3.18 7.104-7.104 7.104zm0-13.332c-3.432 0-6.228 2.796-6.228 6.228S8.568 18.228 12 18.228s6.228-2.796 6.228-6.228S15.432 5.772 12 5.772zM9.684 15.54V8.46L15.816 12l-6.132 3.54z"
    const val bluetooth = "M12 0C6.76 0 3.1484 2.4895 3.1484 12S6.76 24 12 24c5.24 0 8.8516-2.4895 8.8516-12S17.24 0 12 0zm-.7773 1.6816l6.2148 6.2149L13.334 12l4.1035 4.1035-6.2148 6.2149V14.125l-3.418 3.42-1.2422-1.2442L10.8515 12l-4.289-4.3008 1.2422-1.2441 3.418 3.4199V1.6816zm1.748 4.2442v3.9687l1.9844-1.9843-1.9844-1.9844zm0 8.1816v3.9668l1.9844-1.9844-1.9844-1.9824Z"
    const val airplay = "M11.908.183a12.012 12.012 0 00-8.044 3.172c-4.882 4.475-5.166 12.08-.692 16.962.204.244.448.447.692.692a.315.315 0 00.408-.04l.53-.61a.32.32 0 000-.448C.53 15.965.243 9.253 4.23 4.982 8.217.711 14.889.427 19.16 4.414c4.271 3.986 4.555 10.655.568 14.927-.203.203-.365.407-.568.57a.32.32 0 000 .447l.53.611a.37.37 0 00.446.04c4.882-4.516 5.166-12.081.692-16.962a11.98 11.98 0 00-8.92-3.864zm.387 3.518A8.607 8.607 0 006.143 6c-3.458 3.213-3.66 8.623-.447 12.080.122.123.243.285.406.407a.319.319 0 00.447 0l.53-.61a.32.32 0 000-.446A7.263 7.263 0 014.8 12.183c0-3.946 3.212-7.160 7.158-7.160s7.160 3.253 7.160 7.199a7.207 7.207 0 01-2.238 5.209.319.319 0 000 .447l.529.61c.122.121.325.162.447.04a8.599 8.599 0 00.408-12.122 8.494 8.494 0 00-5.970-2.705zm-.266 3.316A5.198 5.198 0 008.34 8.48c-2.075 1.993-2.115 5.247-.122 7.322l.121.123a.319.319 0 00.447 0l.53-.611a.32.32 0 000-.448 3.814 3.814 0 01-1.098-2.683 3.732 3.732 0 013.742-3.742 3.732 3.732 0 013.742 3.742c0 1.017-.406 1.951-1.139 2.683a.32.32 0 000 .448l.53.61a.32.32 0 00.447 0c2.034-1.992 2.116-5.246.123-7.321a5.128 5.128 0 00-3.633-1.586zm.006 7.744a.599.599 0 00-.402.146l-.04.041-7.159 8.055a.506.506 0 00.041.69.437.437 0 00.283.124h14.36a.495.495 0 00.489-.488.463.463 0 00-.121-.326l-7.080-8.055a.5.5 0 00-.37-.187z"
    const val upnp = "M23.255 12.667H13.02c-1.052 0-2.1.489-2.693 1.266v-.017a3.24 3.24 0 01-2.629 1.353 3.25 3.25 0 010-6.502c1.085 0 2.04.536 2.630 1.353v-.013c.591.776 1.640 1.273 2.692 1.273h10.129c.186-.005.873-.095.848-.981-.884-5.086-5.880-8.987-11.923-8.987-3.722 0-7.048 1.480-9.263 3.803-.356.527.014.689.350.734H9.77c1.050 0 2.100-.498 2.692-1.277v.018a3.242 3.242 0 012.630-1.355 3.252 3.252 0 010 6.503 3.240 3.240 0 01-2.630-1.355v.019c-.592-.780-1.642-1.266-2.692-1.266H2.55l.028.003s-1.068-.06-1.719.859C.361 8.9 0 10.620 0 12.002c0 1.388.198 2.650.867 3.923.564.908 1.710.850 1.710.850l-.042.005h7.233c1.050 0 2.100-.490 2.692-1.268v.020a3.242 3.242 0 012.630-1.356 3.251 3.251 0 010 6.502 3.242 3.242 0 01-2.630-1.354v.018c-.592-.779-1.642-1.277-2.692-1.277H3.164c-.328.042-.698.198-.379.700 2.216 2.336 5.555 3.823 9.289 3.823 6.054 0 11.056-3.910 11.926-9.009-.004-.713-.489-.877-.745-.912z"
    const val plex = "M11.643 0H4.68l7.679 12L4.68 24h6.963l7.677-12-7.677-12"

    private fun solid(c: Color): @Composable (Modifier) -> Unit = { m -> Box(m.background(c)) }

    fun style(label: String): SourceStyle = when (label) {
        "Radio" -> SourceStyle(solid(C.accent), C.bg, stroke = "M4 9h16v11H4zM8 9l9-5M14 13h3M14 16h3", fillPath = "M9.5 12.5a2 2 0 1 0 0 4 2 2 0 0 0 0-4z", size = 0.47f)
        "AirPlay" -> SourceStyle({ m -> Box(m.cssGradient(160.0, listOf(0f to hex(0x3a3a3e), 1f to C.bg))) }, Color.White, brand = airplay, size = 0.48f)
        "Blåtann" -> SourceStyle(solid(hex(0x0082fc)), Color.White, brand = bluetooth, size = 0.46f)
        "Spotify" -> SourceStyle(solid(Color.Black), hex(0x1ed760), brand = spotify, size = 1f)
        "YT Music", "YouTube Music" -> SourceStyle(solid(Color.White), hex(0xff0000), brand = ytm, size = 1f)
        "UPnP/DLNA" -> SourceStyle(solid(Color.White), C.card2, brand = upnp, size = 0.6f)
        "AUX" -> SourceStyle(solid(C.off), C.ink, stroke = "M12 2.5v3M9.5 5.5h5v4h-5zM10.8 9.5h2.4v8.2a1.2 1.2 0 0 1-2.4 0zM10.8 13h2.4", size = 0.47f)
        "Navidrome" -> SourceStyle({ m ->
            // fallback mark (brand PNG was not in the design hand-off)
            BoxWithConstraints(m.background(C.bg), contentAlignment = Alignment.Center) {
                Box(Modifier.fillMaxSize(0.625f).clip(CircleShape).background(hex(0x0f62fe)))
                T("N", sora(maxWidth.value * 0.34f, W.Semibold, Color.White))
            }
        }, Color.White, size = 0f)
        "USB" -> SourceStyle(solid(C.seg), C.ink, stroke = "M12 3v15M8 9v2.5l4 3M16 8v3l-4 3", fillPath = "M12 2l-2 3h4zM12 18a1.6 1.6 0 1 0 0 3.2 1.6 1.6 0 0 0 0-3.2zM7 7.5h2v2H7zM16 6.5a1.1 1.1 0 1 0 0 2.2 1.1 1.1 0 0 0 0-2.2z", size = 0.5f)
        "Hodetelefoner" -> SourceStyle(solid(hex(0x2f2a40)), C.ink, stroke = "M4 15v-3a8 8 0 0 1 16 0v3M4 15a2 2 0 0 1 2-2h1v7H6a2 2 0 0 1-2-2zM20 15a2 2 0 0 0-2-2h-1v7h1a2 2 0 0 0 2-2z", size = 0.5f)
        "Plex" -> SourceStyle(solid(hex(0x1f1f1f)), hex(0xe5a00d), brand = plex, size = 0.5f)
        "Lyrion" -> SourceStyle({ m -> BoxWithConstraints(m.background(C.bg), contentAlignment = Alignment.Center) { T("L", sora(maxWidth.value * 0.375f, W.Semibold, C.ink)) } }, Color.White, size = 0f)
        else -> SourceStyle(solid(C.seg), C.ink, size = 0.47f)
    }
}

@Composable
private fun SourceArt(s: SourceStyle, size: Dp, stroke: Float) {
    Box(Modifier.size(size).clip(CircleShape), contentAlignment = Alignment.Center) {
        s.bg(Modifier.fillMaxSize())
        if (s.size > 0) {
            if (s.stroke.isNotEmpty()) SKIcon(s.stroke, size * s.size, stroke, s.fg)
            if (s.fillPath.isNotEmpty()) SKIcon(s.fillPath, size * s.size, color = s.fg, fill = true)
            if (s.brand.isNotEmpty()) SKIcon(s.brand, size * s.size, color = s.fg, fill = true)
        }
    }
}

/** Small round source logo (same artwork as Kilder), for chips and rows. */
@Composable
fun SourceGlyph(label: String, size: Dp = 24.dp) = SourceArt(SourceLogos.style(label), size, 2f)

@Composable
fun SKSourceLogo(label: String, action: () -> Unit) {
    Column(Modifier.press(onClick = action), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(6.dp)) {
        SourceArt(SourceLogos.style(label), 64.dp, 1.8f)
        T(label, sora(11f, W.Regular, C.ink2), maxLines = 1)
    }
}

// MARK: - Logo text (5 bars + SKJOLD)

@Composable
fun SKLogo(barW: Dp = 2.5.dp, gap: Dp = 2.dp, size: Float = 15f, tracking: Float = 1.8f, bottomAligned: Boolean = true, spacing: Dp = 9.dp) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(spacing)) {
        Row(Modifier.height(16.dp), verticalAlignment = if (bottomAligned) Alignment.Bottom else Alignment.Top, horizontalArrangement = Arrangement.spacedBy(gap)) {
            for (h in listOf(8, 12, 16, 12, 8)) Box(Modifier.size(barW, h.dp).clip(RoundedCornerShape(2.dp)).background(C.ink))
        }
        T("SKJOLD", sora(size, W.Semibold).copy(letterSpacing = (tracking / size).em))
    }
}

// MARK: - Tab bar (classic design)

@Composable
fun SKTabBar(selected: Int, pick: (Int) -> Unit) {
    val items = listOf(Icons.tabHome to "Hjem", Icons.tabSound to "Lyd", Icons.tabRooms to "Rom", Icons.tabSettings to "Innstillinger")
    Column(Modifier.fillMaxWidth().background(hex(0x121213, 0.97f)).topLine(hex(0x232325)).windowInsetsPadding(WindowInsets.navigationBars)) {
        Row(Modifier.fillMaxWidth().height(70.dp).padding(start = 6.dp, end = 6.dp, top = 4.dp)) {
            items.forEachIndexed { i, it ->
                val on = i == selected
                Column(
                    Modifier.weight(1f).fillMaxHeight().press { if (i != selected) Haptics.tick(); pick(i) },
                    horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(4.dp, Alignment.CenterVertically),
                ) {
                    Box(Modifier.size(30.dp), contentAlignment = Alignment.Center) { SKIcon(it.first, 22.dp, 1.8f, if (on) C.accent2 else C.muted) }
                    T(it.second, sora(10.5f, if (on) W.Semibold else W.Regular, if (on) C.accent2 else C.muted), maxLines = 1)
                }
            }
        }
    }
}

// MARK: - Mini player

@Composable
fun SKMiniPlayer(m: AppModel) {
    val np = m.np
    Box(Modifier.padding(start = 10.dp, end = 10.dp, bottom = 8.dp)) {
        Row(
            Modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp)).background(hex(0x1b1b1d)).skBorder(hex(0x2a2a2c), 14.dp)
                .pointerInput(Unit) {
                    var dy = 0f
                    detectVerticalDragGestures(onDragStart = { dy = 0f }, onDragEnd = { if (dy < -30) { Haptics.thump(); m.full = true } }) { _, d -> dy += d }
                }
                .padding(8.dp),
            verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            ArtFill(m.playerArt.key, Modifier.size(44.dp).clip(RoundedCornerShape(8.dp)).press { m.full = true })
            Column(Modifier.weight(1f).press { m.full = true }, verticalArrangement = Arrangement.spacedBy(1.dp)) {
                T("${m.groupName} · ${m.actModel}", mono(9.5f), maxLines = 1)
                T(np.t, sora(13f, W.Semibold), maxLines = 1)
                T(np.s, sora(11f, W.Regular, C.muted), maxLines = 1)
            }
            Row(horizontalArrangement = Arrangement.spacedBy(2.dp), verticalAlignment = Alignment.CenterVertically) {
                Box(Modifier.size(34.dp, 40.dp).press { m.prev() }, contentAlignment = Alignment.Center) { SKIcon(Icons.prev, 18.dp, color = C.ink, fill = true) }
                Box(Modifier.size(38.dp).clip(CircleShape).background(C.ink.copy(alpha = 0.1f)).press { m.togglePlay() }, contentAlignment = Alignment.Center) {
                    SKIcon(if (m.playing) Icons.pause else Icons.playRound, 18.dp, color = C.ink, fill = true)
                }
                Box(Modifier.size(34.dp, 40.dp).press { m.next() }, contentAlignment = Alignment.Center) { SKIcon(Icons.next, 18.dp, color = C.ink, fill = true) }
            }
        }
        // thin progress line along the bottom edge (radio shows a live marker instead)
        val frac = if (m.hasProgress) m.position.toFloat() / maxOf(1, m.duration) else 1f
        Box(Modifier.align(Alignment.BottomStart).padding(start = 14.dp, end = 14.dp, bottom = 1.dp).fillMaxWidth().height(2.dp).clip(CircleShape).background(C.ink.copy(alpha = 0.1f))) {
            Box(Modifier.fillMaxWidth(frac.coerceIn(0f, 1f)).fillMaxHeight().clip(CircleShape).background(if (m.input == 3) C.live.copy(alpha = 0.8f) else C.accent))
        }
    }
}

/** Hero product image (hero-s1 cut from the design screenshot). */
@Composable
fun HeroImage(modifier: Modifier = Modifier) {
    Image(painterResource(R.drawable.hero_s1), contentDescription = null, contentScale = ContentScale.Fit, modifier = modifier)
}

@Composable
fun VSpace(h: Dp) = Spacer(Modifier.height(h))

@Composable
fun Dot(color: Color, size: Dp = 6.dp) = Box(Modifier.size(size).clip(CircleShape).background(color))

/** Card row container: VStack(spacing 0) in a box with border. */
@Composable
fun SKCard(bg: Color = C.card, border: Color = C.line, radius: Dp = 14.dp, modifier: Modifier = Modifier, content: @Composable () -> Unit) {
    Column(modifier.fillMaxWidth().skBox(bg, border, radius)) { content() }
}
