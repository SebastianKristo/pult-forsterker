package no.kristo.skjold

import androidx.activity.compose.BackHandler
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.MutableTransitionState
import androidx.compose.animation.core.tween
import androidx.compose.animation.slideInVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBars
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.SideEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.compose.ui.window.DialogWindowProvider
import kotlinx.coroutines.delay

/*
 * Kildesiden og spillelisten (v4), som V4SourcePage.swift på iOS: radial glød i kildens farge, kildeikon og status,
 * søkefelt, spillelister (mosaikk) og låter – eller forklaring og knapp for innganger (AirPlay, Blåtann, AUX …).
 * Liquid Glass (tilbakeknapp, søkefelt) blir heldekkende mørke flater på Android.
 */

// MARK: - Tokens

/** Farger og ikoner fra V4Tokens.swift som kildesidene, søket og kassettene bruker. */
object SourceTok {
    val bg = C.bg
    val searchBg = hex(0x050506)
    val ink = C.ink
    val ink2 = C.ink2
    val body = C.body
    val muted = C.muted
    val chev = hex(0x6a6a65)
    val gold = C.accent2          // #f0c46a
    val goldDark = C.accent       // #d9a441
    val green = C.ok              // #6fcf7f
    val red = hex(0xe8564a)
    val selBg = C.selBg
    val card = C.card
    val sheet = hex(0x1a1a1c)
    val row = hex(0x232326)
    val line = C.line
    val line2 = C.line2
    val mosaicEmpty = hex(0x1b1b1d)

    /** Glass (v4GlassButton / søkefelt) → mørk flate med tynn kant. */
    val glassBg = hex(0x28282a).copy(alpha = 0.6f)
    val glassLine = Color.White.copy(alpha = 0.12f)
    val fieldBg = SkG.panelBg
    val fieldLine = SkG.panelLine

    const val back = "M15 5l-7 7 7 7"
    const val close = "M6 6l12 12M18 6L6 18"
    const val search = "M11 18a7 7 0 1 0 0-14a7 7 0 1 0 0 14M20 20l-4-4"
    const val chevRight = "M9 6l6 6-6 6"
    const val shuffle = "M4 7h3l10 10h3M4 17h3l3-3M14 10l3-3h3M18 5l2 2-2 2M18 15l2 2-2 2"
    const val heart = "M12 20s-7-4.5-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.5-7 10-7 10z"
    const val queue = "M4 6h11M4 12h11M4 18h7M18 14v6l4-3z"
    const val sleep = "M12 21a8 8 0 1 0 0-16a8 8 0 1 0 0 16M12 9v4l2 2M5 3L2 6M19 3l3 3"
    const val play = "M8 5.2v13.6a1 1 0 0 0 1.52.85l10.6-6.8a1 1 0 0 0 0-1.7L9.52 4.35A1 1 0 0 0 8 5.2z"
    val pause = SVG.rect(6f, 4.5f, 4f, 15f, 1.2f) + SVG.rect(14f, 4.5f, 4f, 15f, 1.2f)
    val dots = SVG.circle(5f, 12f, 1.8f) + SVG.circle(12f, 12f, 1.8f) + SVG.circle(19f, 12f, 1.8f)
    val dotsSmall = SVG.circle(5f, 12f, 1.7f) + SVG.circle(12f, 12f, 1.7f) + SVG.circle(19f, 12f, 1.7f)

    /** V4.moreSheet: cubic-bezier(.2,.8,.2,1) 0,42 s. */
    val moreEase = CubicBezierEasing(0.2f, 0.8f, 0.2f, 1f)

    /** Kildefarger (SRCICON-bakgrunnen) til gløden (V4Src.color). */
    fun color(n: String): Color = when (n) {
        "Radio" -> goldDark
        "AirPlay" -> hex(0x3a3a3e)
        "Blåtann" -> hex(0x0082fc)
        "Spotify" -> hex(0x1ed760)
        "YouTube Music", "YT Music" -> hex(0xff0000)
        "Navidrome" -> hex(0x1e5aa8)
        "Plex" -> hex(0xe5a00d)
        "UPnP/DLNA" -> hex(0xf2f2ee)
        else -> hex(0x3a3a37)
    }
}

// MARK: - UI-tilstand (V4State: src, srcQ, pl, search, sq, sSrc, more, moreTrack, sleep). Ikke lagret, som på iOS.

object SourceUi {
    /** Kildesiden som er åpen («Radio», «Navidrome», «AirPlay» …), null = ingen. */
    var src by mutableStateOf<String?>(null)
    var srcQ by mutableStateOf("")
    /** Spillelisten som er åpen (ligger over kildesiden). */
    var pl by mutableStateOf<SourcePlaylist?>(null)
    /** Søkesiden (helskjerm, over dokken). */
    var search by mutableStateOf(false)
    var sq by mutableStateOf("")
    var sSrc by mutableStateOf<Int?>(null)
    /** «Mer»-arket for en låt. */
    var more by mutableStateOf(false)
    var moreTrack by mutableStateOf<Track?>(null)
    var sleep by mutableStateOf(0)

    /** Er en kildeside eller spilleliste åpen (da tegnes SourceOverlays i stedet for fanesiden)? */
    val active: Boolean get() = src != null || pl != null
}

/** Åpner kildesiden for en kilde (som `ui.srcQ = ""; ui.pl = nil; ui.src = …` i V4Home.swift). */
fun AppModel.openSource(label: String) {
    SourceUi.srcQ = ""; SourceUi.pl = null; SourceUi.src = label
    full = false
}

/** Åpner en spilleliste (Hjem → «Dine spillelister», søket). */
fun AppModel.openSourcePlaylist(p: SourcePlaylist) {
    SourceUi.pl = p
    full = false
}

/** Åpner søket, eventuelt med en tekst («Søk etter M83» fra «Mer»). */
fun AppModel.openSearch(text: String = "") {
    SourceUi.sq = text
    SourceUi.search = true
    full = false
}

// MARK: - Bibliotekene (V4Playlist / V4Lib)

/** Spilleliste/album fra et bibliotek (eller demobiblioteket). */
data class SourcePlaylist(
    val id: String,
    val name: String,
    val owner: String,
    /** Visningsnavn: «Navidrome», «Plex», «YouTube Music». */
    val src: String,
    /** «nd», «plex», «ytm». */
    val lib: String,
    /** Omslag til mosaikken. */
    val keys: List<String>,
    val demoIdx: List<Int> = emptyList(),
    val coll: LibColl? = null,
    val count: Int = 0,
)

object SourceLib {
    val names = mapOf("nd" to "Navidrome", "plex" to "Plex", "ytm" to "YouTube Music")

    /** Kildeside-navn → bibliotek-id. */
    fun id(label: String): String? = when (label) {
        "Navidrome" -> "nd"
        "Plex" -> "plex"
        "YouTube Music", "YT Music" -> "ytm"
        else -> null
    }

    /** Spillelister for ett bibliotek: demodata eller det som er lastet fra tjenesten. */
    fun playlists(m: AppModel, lib: String): List<SourcePlaylist> {
        val src = names[lib] ?: lib
        if (m.demo) {
            val pls = SK.lib[lib]?.pls ?: emptyList()
            return pls.mapIndexed { i, p ->
                val keys = p.second.take(4).map { SK.lt[it % SK.lt.size].album }
                SourcePlaylist(lib + "/$i", p.first, if (i == 0) "Deg" else "Laget for deg", src, lib, keys, p.second, null, p.second.size)
            }
        }
        val d = m.libs[lib]
        // YouTube Music: også «Til deg» (mikser og anbefalte album fra forsiden), så det er noe å spille uten innlogging
        val colls = (d?.playlists ?: emptyList()) + (d?.newest ?: emptyList()).take(8) +
            (if (lib == "ytm") (d?.frequent ?: emptyList()).take(8) + (d?.other ?: emptyList()).take(8) else emptyList())
        return colls.distinctBy { it.id }.map { c ->
            SourcePlaylist(lib + "/" + c.id, c.name, if (c.playlist) "Spilleliste" else c.artist, src, lib,
                listOf(c.name, c.name + " 2", c.name + " 3", c.name + " 4"), emptyList(), c, c.count)
        }
    }

    suspend fun tracks(m: AppModel, p: SourcePlaylist): List<Track> {
        val c = p.coll
        if (c != null) return m.collTracks(p.lib, c)
        return p.demoIdx.map { SK.lt[it % SK.lt.size] }
    }
}

// MARK: - Byggeklosser (V4SourceIcon, V4Art, V4Mosaic, V4MoreButton …)

/** Kildeikon i en sirkel med kant rgba(255,255,255,.08), og gull ring når valgt (V4SourceIcon). */
@Composable
fun SourceIcon(label: String, size: Dp, ring: Dp = 0.dp, modifier: Modifier = Modifier) {
    val s = SourceLogos.style(label)
    Box(modifier.size(size), contentAlignment = Alignment.Center) {
        Box(Modifier.fillMaxSize().clip(CircleShape), contentAlignment = Alignment.Center) {
            s.bg(Modifier.fillMaxSize())
            if (s.size > 0) {
                if (s.stroke.isNotEmpty()) SKIcon(s.stroke, size * s.size, 1.8f, s.fg)
                if (s.fillPath.isNotEmpty()) SKIcon(s.fillPath, size * s.size, color = s.fg, fill = true)
                if (s.brand.isNotEmpty()) SKIcon(s.brand, size * s.size, color = s.fg, fill = true)
            }
        }
        Box(Modifier.fillMaxSize().skCapsuleBorder(Color.White.copy(alpha = 0.08f)))
        if (ring > 0.dp) Box(Modifier.fillMaxSize().skCapsuleBorder(SourceTok.gold, ring))
    }
}

/** Omslag: ekte bilde / logo når det finnes, ellers gradienten. Gull ring når den spiller (V4Art). */
@Composable
fun SourceCover(key: String, size: Dp, radius: Dp, ring: Dp = 0.dp, modifier: Modifier = Modifier) {
    Box(modifier.size(size).clip(RoundedCornerShape(radius))) {
        ArtFill(art(key))
        if (ring > 0.dp) Box(Modifier.fillMaxSize().skBorder(SourceTok.gold, radius, ring))
    }
}

/** 2 × 2-mosaikk for spillelister (V4Mosaic). */
@Composable
fun SourceMosaic(keys: List<String>, size: Dp, radius: Dp, modifier: Modifier = Modifier) {
    val k = keys.take(4) + List(maxOf(0, 4 - keys.size)) { "" }
    val cell = size / 2
    Column(modifier.size(size).clip(RoundedCornerShape(radius))) {
        for (r in 0 until 2) Row {
            for (c in 0 until 2) {
                val key = k[r * 2 + c]
                Box(Modifier.size(cell).background(SourceTok.mosaicEmpty)) { if (key.isNotEmpty()) ArtFill(art(key)) }
            }
        }
    }
}

/** Rund «⋯»-knapp i lister (V4MoreButton): ikon 18, treffflate 36. */
@Composable
fun SourceMoreButton(size: Dp = 18.dp, action: () -> Unit) {
    Box(Modifier.size(36.dp).press(label = "Mer", onClick = action), contentAlignment = Alignment.Center) {
        SKIcon(SourceTok.dotsSmall, size, color = SourceTok.ink, fill = true)
    }
}

/** Mono-kicker 10/.12em (V4Kicker). */
@Composable
fun SourceKicker(text: String, color: Color = SourceTok.muted) = T(text, mono(10f, color, 0.12f))

/** Rund tilbakeknapp 46 (glass på iOS). */
@Composable
private fun BackCircle(action: () -> Unit) {
    Box(
        Modifier.size(46.dp).clip(CircleShape).background(SourceTok.glassBg).skCapsuleBorder(SourceTok.glassLine)
            .press(label = "Tilbake", onClick = action),
        contentAlignment = Alignment.Center,
    ) { SKIcon(SourceTok.back, 20.dp, 2.4f, SourceTok.ink) }
}

/** «SPILLELISTER» 15/700, +0.6, strek rgba(255,255,255,.08) under. */
@Composable
private fun SectionTitle(t: String) {
    T(
        t.uppercase(), sora(15f, W.Semibold).copy(letterSpacing = 0.6.sp),
        Modifier.fillMaxWidth()
            .drawBehind { drawRect(Color.White.copy(alpha = 0.08f), Offset(0f, size.height - 1.dp.toPx()), Size(size.width, 1.dp.toPx())) }
            .padding(bottom = 10.dp),
        maxLines = 1,
    )
}

/** radial-gradient(… at x y, farge 0%, transparent) – UnitPoint i rammen, radius i dp. */
private fun Modifier.radialGlow(color: Color, cx: Float, cy: Float, radius: Dp): Modifier = drawBehind {
    drawRect(Brush.radialGradient(listOf(color, Color.Transparent), center = Offset(size.width * cx, size.height * cy), radius = radius.toPx()))
}

// MARK: - Kildesiden (srcOn)

/**
 * Kildesiden og spillelisten som lag over fanesiden (som V4Root.swift: V4SourcePage under V4PlaylistPage).
 * Tegnes av skallet når [SourceUi.active] er sann. Dokken (minispiller + faner) kan ligge over.
 */
@Composable
fun SourceOverlays(m: AppModel, wide: Boolean = false) {
    Box(Modifier.fillMaxSize()) {
        SourceUi.src?.let { SourcePage(m, it, wide) }
        SourceUi.pl?.let { PlaylistPage(m, it, wide) }
    }
    SourceMoreSheet(m)
}

/** Kildeside (helside med egen rulling og glød). */
@Composable
fun SourcePage(m: AppModel, n: String, wide: Boolean = false) {
    BackHandler(enabled = SourceUi.pl == null) { SourceUi.src = null; SourceUi.srcQ = "" }
    Box(Modifier.fillMaxSize().background(SourceTok.bg)) {
        // radial-gradient(90% 70% at 20% 0%, kildefarge55 0%, transparent 70%), 420 høy, ligger fast bak rullingen
        Box(Modifier.fillMaxWidth().height(420.dp).radialGlow(SourceTok.color(n).copy(alpha = 0.33f), 0.2f, 0f, 330.dp))
        Column(
            Modifier.fillMaxSize().windowInsetsPadding(WindowInsets.statusBars).verticalScroll(rememberScrollState())
                .padding(start = if (wide) 40.dp else 20.dp, end = if (wide) 40.dp else 20.dp, top = 6.dp, bottom = if (wide) 130.dp else 230.dp),
            verticalArrangement = Arrangement.spacedBy(22.dp),
        ) {
            SourceBody(m, n, if (wide) 40.dp else 20.dp) { SourceUi.src = null; SourceUi.srcQ = "" }
        }
    }
}

/** Innholdet på kildesiden (tilbake, topp, søk, inngangskort, lister). Brukes også innebygd av LibraryView/RadioView. */
@Composable
fun SourceBody(m: AppModel, n: String, inset: Dp = 20.dp, close: () -> Unit) {
    val lib = SourceLib.id(n)
    val isRadio = n == "Radio"
    val isInput = n in listOf("AirPlay", "Blåtann", "UPnP/DLNA", "AUX", "USB", "Spotify")
    val q = SourceUi.srcQ.trim()
    var libHits by remember { mutableStateOf(listOf<Track>()) }
    var busy by remember { mutableStateOf(false) }

    LaunchedEffect(n) { if (lib != null) m.loadLib(lib) }
    LaunchedEffect(q, lib) {
        if (lib == null || m.demo || q.isEmpty()) { libHits = emptyList(); busy = false; return@LaunchedEffect }
        delay(350)
        busy = true
        val r = m.searchLib(lib, q)
        libHits = r; busy = false
    }

    BackCircle(close)
    Head(m, n, isInput)
    if (!isInput) SourceSearchField(SourceUi.srcQ, { SourceUi.srcQ = it }, if (isRadio) "Søk etter kanal" else "Søk i $n")
    if (isInput) InputCard(m, n)
    if (isRadio) RadioList(m, q)
    else if (lib != null) {
        val pls = SourceLib.playlists(m, lib).filter { q.isEmpty() || it.name.contains(q, ignoreCase = true) }
        val trs: List<Track> = when {
            q.isNotEmpty() -> if (m.demo) SK.lt.filter { (it.t + " " + it.artist + " " + it.album).contains(q, ignoreCase = true) } else libHits
            m.demo -> (SK.lib[lib]?.hist ?: emptyList()).map { SK.lt[it.first % SK.lt.size] }
            else -> (m.hist[lib] ?: emptyList()).map { it.track }
        }
        if (q.isNotEmpty() && pls.isEmpty() && trs.isEmpty() && !busy) {
            T("Fant ingenting for «$q» i $n", sora(15f, W.Regular, SourceTok.muted), Modifier.fillMaxWidth().padding(vertical = 20.dp),
                align = androidx.compose.ui.text.style.TextAlign.Center)
        }
        if (pls.isEmpty() && trs.isEmpty() && q.isEmpty()) {
            val s = m.libs[lib]?.state ?: ""
            val text = if (s == "busy") "Henter biblioteket …" else if (s.isEmpty() || s == "ok") "Ingen spillelister ennå." else s
            T(text, sora(14f, W.Regular, SourceTok.muted, 1.45f))
        }
        if (pls.isNotEmpty()) {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                SectionTitle("Spillelister")
                EdgeScroll(12.dp, inset) {
                    for (p in pls) {
                        Column(Modifier.width(148.dp).press { m.openSourcePlaylist(p) }, verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            SourceMosaic(p.keys, 148.dp, 14.dp)
                            T(p.name, sora(14f, W.Semibold), maxLines = 1)
                            T("${p.count} låter", sora(12f, W.Regular, SourceTok.muted))
                        }
                    }
                }
            }
        }
        if (trs.isNotEmpty()) {
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                SectionTitle("Låter")
                trs.forEachIndexed { i, t ->
                    SourceTrackRow(t.t, t.artist, t.album, m.libTrack?.t == t.t, play = { m.lib = lib; m.playLib(trs, i, keepOpen = true) }) {
                        SourceUi.moreTrack = t; SourceUi.more = true
                    }
                }
            }
        }
    }
}

/** Kildeikon 72 (skygge), navn 30/700 og status med prikk. */
@Composable
private fun Head(m: AppModel, n: String, isInput: Boolean) {
    val here = m.v4SrcIcon == n || (n == "YT Music" && m.v4SrcIcon == "YouTube Music")
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(16.dp)) {
        SourceIcon(n, 72.dp, modifier = Modifier.shadow(15.dp, CircleShape, ambientColor = Color.Black.copy(alpha = 0.4f), spotColor = Color.Black.copy(alpha = 0.4f)))
        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
            T(n, sora(30f, W.Semibold).copy(letterSpacing = (-0.6).sp), maxLines = 1)
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                Box(Modifier.size(7.dp).clip(CircleShape).background(if (here) SourceTok.green else if (isInput) SourceTok.muted else SourceTok.goldDark))
                T(if (here) "Spiller nå i " + m.v4GroupName else if (isInput) "Inngang · klar" else "Koblet til",
                    sora(13f, W.Regular, SourceTok.ink.copy(alpha = 0.75f)), maxLines = 1)
            }
        }
    }
}

/** Søkefeltet på kildesiden: kapsel 48 (glass på iOS), ikon 18, tøm-knapp 28. */
@Composable
fun SourceSearchField(text: String, onChange: (String) -> Unit, placeholder: String) {
    val focus = LocalFocusManager.current
    Row(
        Modifier.fillMaxWidth().height(48.dp).clip(CircleShape).background(SourceTok.fieldBg).skCapsuleBorder(SourceTok.fieldLine).padding(horizontal = 16.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        SKIcon(SourceTok.search, 18.dp, 2f, SourceTok.body)
        BasicTextField(
            value = text, onValueChange = onChange, singleLine = true,
            textStyle = sora(16f, W.Regular, SourceTok.ink), cursorBrush = SolidColor(SourceTok.goldDark),
            keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.None, autoCorrectEnabled = false, imeAction = ImeAction.Search),
            keyboardActions = KeyboardActions(onSearch = { focus.clearFocus() }),
            modifier = Modifier.weight(1f),
            decorationBox = { inner ->
                Box(contentAlignment = Alignment.CenterStart) {
                    if (text.isEmpty()) T(placeholder, sora(16f, W.Regular, SourceTok.muted), maxLines = 1)
                    inner()
                }
            },
        )
        if (text.trim().isNotEmpty()) {
            Box(Modifier.size(28.dp).clip(CircleShape).background(Color.White.copy(alpha = 0.14f)).press(label = "Tøm") { onChange("") }, contentAlignment = Alignment.Center) {
                SKIcon(SourceTok.close, 12.dp, 2.6f, SourceTok.ink)
            }
        }
    }
}

// MARK: Innganger

private data class InputDev(val name: String, val sub: String, val badge: String, val color: Color, val pick: (() -> Unit)? = null)

@Composable
private fun InputCard(m: AppModel, n: String) {
    val room = "«Skjold " + m.actRoom.name + "»"
    val r: Triple<String, List<InputDev>, String> = when (n) {
        "AirPlay" -> {
            val d = m.dev?.airplayDevice ?: ""
            Triple("Velg $room i kontrollsenteret på iPhone, iPad eller Mac. Lyden kommer uten tap i kvalitet.",
                if (d.isEmpty()) emptyList() else listOf(InputDev(d, "Spiller nå", "TILKOBLET", SourceTok.green)), "Bytt til AirPlay")
        }
        "Blåtann" -> {
            val d = m.dev?.btDevice ?: ""
            Triple("Koble til $room fra Blåtann-innstillingene på telefonen. Forsterkeren husker åtte enheter.",
                if (d.isEmpty()) emptyList() else listOf(InputDev(d, "Tilkoblet", "PARET", SourceTok.green)), "Gjør synlig i 2 minutter")
        }
        "UPnP/DLNA" -> Triple("Skjold vises som høyttaler i apper som BubbleUPnP, foobar2000 og Plex.", emptyList(), "Vis navnet på nettverket")
        "Spotify" -> Triple("Åpne Spotify, trykk på høyttalerikonet og velg $room. Skjold spiller via Spotify Connect.", emptyList(), "Bruk Spotify")
        "USB" -> {
            // USB-lyd fra PC: med USB-switchen velges PC 1 eller PC 2 (samme som USB-knappen på forsterkeren)
            val d = m.dev
            val cur = d?.input == "usb"
            val names = d?.usbNames.orEmpty()
            val pcs = if (d?.usbsw == true) (1..2).map { pc ->
                val on = cur && d.usbPc == pc
                InputDev(names.getOrNull(pc - 1)?.takeIf { it.isNotBlank() } ?: "PC $pc", if (on) "Spiller via USB" else "Trykk for å bytte",
                    if (on) "AKTIV" else "VELG", if (on) SourceTok.green else SourceTok.muted) { Haptics.tick(); m.setUsbPc(pc) }
            } else listOf(InputDev("USB-lyd", if (cur) "Aktiv" else "Ingen PC valgt", if (cur) "AKTIV" else "LEDIG", if (cur) SourceTok.green else SourceTok.muted))
            Triple("Lyd fra datamaskinen over USB. Med USB-switchen velger du hvilken PC som spiller.", pcs, "Bytt til USB nå")
        }
        else -> {
            // AUX 1 og AUX 2 (S1 har to analoge innganger; AUX-knappen veksler mellom dem)
            val cur = m.dev?.input ?: ""
            val two = m.dev?.inputs?.contains("aux2") == true
            val rows = (if (two) listOf("aux" to 1, "aux2" to 2) else listOf("aux" to 1)).map { (key, k) ->
                val on = cur == key || (!m.live && m.input == 2 && k == 1)
                val name = m.names["nAux$k"]?.takeIf { it.isNotBlank() } ?: if (two) "AUX $k" else "AUX-inngang"
                InputDev(name, if (on) "Aktiv" else if (two) "Trykk for å bytte" else "Ingen signal", if (on) "AKTIV" else if (two) "VELG" else "LEDIG",
                    if (on) SourceTok.green else SourceTok.muted, if (two) ({ Haptics.tick(); m.pickInputName(key) }) else null)
            }
            Triple("Analog inngang bak på forsterkeren. Bytter automatisk når det kommer signal.", rows, "Bytt til AUX nå")
        }
    }
    val (text, devs, button) = r
    Column(
        Modifier.fillMaxWidth().clip(RoundedCornerShape(22.dp)).background(SourceTok.card).skBorder(SourceTok.line, 22.dp).padding(18.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        T(text, sora(15f, W.Regular, SourceTok.ink2, 1.5f))
        for (d in devs) {
            Row(Modifier.fillMaxWidth().topLine(SourceTok.line).let { mod -> d.pick?.let { p -> mod.press { p() } } ?: mod }.padding(top = 12.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    T(d.name, sora(15f), maxLines = 1)
                    T(d.sub, sora(12f, W.Regular, SourceTok.muted))
                }
                T(d.badge, mono(10f, d.color, 0.1f))
            }
        }
        Box(
            Modifier.fillMaxWidth().height(48.dp).clip(CircleShape).background(SourceTok.ink).press {
                Haptics.thump()
                when (n) {
                    "AirPlay" -> m.pickInput(0)
                    "Blåtann" -> { m.pickInput(1); if (m.live) m.devSend("/api/bt", mapOf("pairing" to true)) }
                    "UPnP/DLNA" -> m.pickService("upnp")
                    "Spotify" -> m.pickService("spotify")
                    "USB" -> m.pickInputName("usb")
                    else -> m.pickInput(2)
                }
            },
            contentAlignment = Alignment.Center,
        ) { T(button, sora(15f, W.Semibold, SourceTok.bg)) }
    }
}

// MARK: Radio

@Composable
private fun RadioList(m: AppModel, q: String) {
    LaunchedEffect(q) { if (q != m.q.trim()) m.setQ(q) }
    val hits: List<Station> = if (q.isEmpty()) emptyList() else (m.rRes ?: emptyList()).map { Station(it.name, it.genre, it.url) }
    val favs = m.radio.withIndex().filter { q.isEmpty() || it.value.name.contains(q, ignoreCase = true) }
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        SectionTitle("Kanaler")
        for ((i, st) in favs) {
            SourceTrackRow(st.name, st.genre, st.name, m.input == 3 && m.stIdx == i && m.rTmp == null, play = { m.playStation(i, open = false) }) { m.toggleFav(st) }
        }
        if (q.isNotEmpty()) {
            if (m.rBusy) T("Søker …", sora(13f, W.Regular, SourceTok.muted), Modifier.padding(vertical = 8.dp))
            for (st in hits) {
                SourceTrackRow(st.name, st.genre, st.name, m.curRadioName == st.name, play = { m.playRadio(st) }) { m.toggleFav(st) }
            }
            if (!m.rBusy && hits.isEmpty() && favs.isEmpty()) {
                T("Fant ingenting for «$q» i Radio", sora(15f, W.Regular, SourceTok.muted), Modifier.fillMaxWidth().padding(vertical = 20.dp),
                    align = androidx.compose.ui.text.style.TextAlign.Center)
            }
        }
    }
}

/** Låt-/kanalrad: omslag 56 r10 (ring når den spiller), tittel 15/600, undertekst 13, «⋯». */
@Composable
fun SourceTrackRow(t: String, s: String, key: String, cur: Boolean, play: () -> Unit, more: () -> Unit) {
    Row(Modifier.fillMaxWidth().padding(vertical = 5.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp)) {
        Row(Modifier.weight(1f).press(onClick = play), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp)) {
            SourceCover(key, 56.dp, 10.dp, if (cur) 2.dp else 0.dp)
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                T(t, sora(15f, W.Semibold, if (cur) SourceTok.gold else SourceTok.ink), maxLines = 1)
                T(s, sora(13f, W.Regular, SourceTok.muted), maxLines = 1)
            }
        }
        SourceMoreButton(action = more)
    }
}

// MARK: - Spillelisten (plOn)

/** Spilleliste: gradient 560, mosaikk 240, meta, Spill / tilfeldig / mer, låtliste. */
@Composable
fun PlaylistPage(m: AppModel, p: SourcePlaylist, wide: Boolean = false) {
    BackHandler { SourceUi.pl = null }
    Box(Modifier.fillMaxSize().background(SourceTok.bg)) {
        val a = art(p.keys.firstOrNull() ?: p.name)
        val b = art(if (p.keys.size > 1) p.keys[1] else p.name)
        Box(
            Modifier.fillMaxWidth().height(560.dp)
                .radialGlow(a.base, 0.2f, 0.1f, 360.dp)
                .radialGlow(b.base, 0.85f, 0.25f, 360.dp)
                .drawBehind { drawRect(Brush.verticalGradient(300f / 560f to Color.Transparent, 1f to SourceTok.bg)) },
        )
        Column(
            Modifier.fillMaxSize().windowInsetsPadding(WindowInsets.statusBars).verticalScroll(rememberScrollState()),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Column(
                Modifier.then(if (wide) Modifier.widthIn(max = 760.dp) else Modifier).fillMaxWidth()
                    .padding(start = 20.dp, end = 20.dp, top = 6.dp, bottom = 240.dp),
                verticalArrangement = Arrangement.spacedBy(18.dp),
            ) { PlaylistBody(m, p) }
        }
    }
}

/** Innholdet i spillelisten (brukes også innebygd i LibraryView). */
@Composable
fun PlaylistBody(m: AppModel, p: SourcePlaylist) {
    var tracks by remember(p.id) { mutableStateOf(listOf<Track>()) }
    LaunchedEffect(p.id) { tracks = SourceLib.tracks(m, p) }
    val isPlaying = tracks.isNotEmpty() && m.playing && m.lq == tracks
    val play: (Int, Boolean) -> Unit = { i, shuffle ->
        if (tracks.isNotEmpty()) {
            if (isPlaying && !shuffle && i == 0) m.togglePlay()
            else {
                val list = if (shuffle) tracks.shuffled() else tracks
                m.lib = p.lib
                m.shuffle = shuffle
                m.playLib(list, i, keepOpen = true)
            }
        }
    }

    BackCircle { SourceUi.pl = null }
    Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
        SourceMosaic(p.keys, 240.dp, 18.dp, Modifier.shadow(30.dp, RoundedCornerShape(18.dp), ambientColor = Color.Black.copy(alpha = 0.5f), spotColor = Color.Black.copy(alpha = 0.5f)))
    }
    Column(Modifier.padding(top = 8.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
        T(p.name, sora(34f, W.Semibold, lineHeight = 1.05f).copy(letterSpacing = (-0.68).sp), maxLines = 2)
        T(p.owner, sora(17f, W.Semibold), maxLines = 1)
        Row(Modifier.padding(top = 4.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(7.dp)) {
            SourceIcon(p.src, 18.dp)
            val mins = tracks.sumOf { it.dur } / 60
            T(p.src + " · Spilleliste · ${tracks.size} låter · $mins min", sora(13f, W.Regular, SourceTok.ink.copy(alpha = 0.72f)), maxLines = 1)
        }
    }
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Row(
            Modifier.widthIn(max = 200.dp).height(52.dp).clip(CircleShape).background(SourceTok.ink).press { play(0, false) }
                .padding(start = 18.dp, end = 22.dp),
            verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp, Alignment.CenterHorizontally),
        ) {
            SKIcon(if (isPlaying) SourceTok.pause else SourceTok.play, 20.dp, color = SourceTok.bg, fill = true)
            T(m.v4GroupName, sora(16f, W.Semibold, SourceTok.bg), maxLines = 1)
        }
        Box(Modifier.size(52.dp).clip(CircleShape).background(SourceTok.ink).press(label = "Spill tilfeldig") { play(0, true) }, contentAlignment = Alignment.Center) {
            SKIcon(SourceTok.shuffle, 22.dp, 2f, SourceTok.bg)
        }
        Box(
            Modifier.size(52.dp).clip(CircleShape).background(SourceTok.ink.copy(alpha = 0.12f))
                .press(label = "Mer") { SourceUi.moreTrack = tracks.firstOrNull(); SourceUi.more = true },
            contentAlignment = Alignment.Center,
        ) { SKIcon(SourceTok.dots, 20.dp, color = SourceTok.ink, fill = true) }
    }
    Column(Modifier.padding(top = 6.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
        tracks.forEachIndexed { i, t ->
            val cur = m.libTrack?.t == t.t
            Row(Modifier.fillMaxWidth().padding(vertical = 6.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                Row(
                    Modifier.weight(1f).press { m.lib = p.lib; m.playLib(tracks, i, keepOpen = true) },
                    verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp),
                ) {
                    SourceCover(t.album, 60.dp, 10.dp, if (cur) 2.dp else 0.dp)
                    Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                        T(t.t, sora(16f, W.Semibold, if (cur) SourceTok.gold else SourceTok.ink), maxLines = 1)
                        T(t.artist, sora(14f, W.Regular, SourceTok.ink.copy(alpha = 0.6f)), maxLines = 1)
                    }
                }
                SourceMoreButton(20.dp) { SourceUi.moreTrack = t; SourceUi.more = true }
            }
        }
    }
}

// MARK: - «Mer»-arket for en låt (V4MoreSheet)

private fun AppModel.srcPlayNext(t: Track) {
    val q0 = lq ?: return
    if (libTrack == null) return
    val q = q0.toMutableList()
    val i = q.indexOf(t)
    if (i >= 0 && i != li) { q.removeAt(i); if (i < li) li -= 1 }
    q.add(minOf(q.size, li + 1), t)
    lq = q
}

private fun AppModel.srcQueueRemove(t: Track) {
    val q0 = lq ?: return
    if (libTrack == null) return
    val i = q0.indexOf(t)
    if (i < 0 || i == li) return
    val q = q0.toMutableList()
    q.removeAt(i)
    if (i < li) li -= 1
    lq = q
}

private val sleeps = listOf("Av", "15 min", "30 min", "60 min")
private val sleepMin = listOf(0, 15, 30, 60)

/** Fjerner vinduets egen demping i en Dialog (dempelaget tegnes selv). */
@Composable
private fun NoDialogDim() {
    val w = (LocalView.current.parent as? DialogWindowProvider)?.window
    SideEffect { w?.setDimAmount(0f) }
}

/**
 * «Mer»-arket: 8 fra kantene, radius 34, farget fra det som spiller (glass på iOS, mørk flate her).
 * Favoritter lagres som på iOS under «skjold-v4-favs» (titler skilt med linjeskift).
 */
@Composable
fun SourceMoreSheet(m: AppModel) {
    // Flere sider kan være verter (kildeside, søk, innebygd bibliotek); bare den sist komponerte tegner arket
    val me = remember { Any() }
    DisposableEffect(me) { moreHosts.add(me); onDispose { moreHosts.remove(me) } }
    if (moreHosts.lastOrNull() === me) MoreSheetContent(m)
}

private val moreHosts = mutableStateListOf<Any>()

@Composable
private fun MoreSheetContent(m: AppModel) {
    if (!SourceUi.more) return
    val close = { SourceUi.more = false }
    val t = SourceUi.moreTrack ?: m.libTrack
    val title = t?.t ?: m.np.t
    val artist = t?.artist ?: m.np.s
    val key = t?.album ?: m.playerArt.key
    var favsRaw by remember { mutableStateOf(Store.string("skjold-v4-favs") ?: "") }
    val favs = favsRaw.split("\n").filter { it.isNotEmpty() }.toSet()
    val radioOnly = m.input == 3 && t == null
    val isFav = if (radioOnly) m.favIndex(m.curRadio.name) != null else title in favs
    val vis = remember { MutableTransitionState(false) }
    vis.targetState = true

    Dialog(onDismissRequest = close, properties = DialogProperties(usePlatformDefaultWidth = false, decorFitsSystemWindows = false)) {
        NoDialogDim()
        Box(Modifier.fillMaxSize().background(Color.Black.copy(alpha = 0.45f)).press(label = "Lukk") { close() }, contentAlignment = Alignment.BottomCenter) {
            AnimatedVisibility(vis, enter = slideInVertically(tween(420, easing = SourceTok.moreEase)) { it + 60 }) {
                val mid = art(m.playerArt.key).stops.lastOrNull()?.second ?: hex(0x0b2f38)
                Column(
                    Modifier.windowInsetsPadding(WindowInsets.navigationBars).padding(8.dp).fillMaxWidth()
                        .clip(RoundedCornerShape(34.dp)).background(SourceTok.sheet).background(mid.copy(alpha = 0.55f))
                        .skBorder(Color.White.copy(alpha = 0.1f), 34.dp)
                        .pointerInput(Unit) { detectTapGestures { } }   // trykk på arket lukker det ikke
                        .padding(start = 16.dp, end = 16.dp, top = 10.dp, bottom = 26.dp),
                    verticalArrangement = Arrangement.spacedBy(4.dp),
                ) {
                    Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                        Box(Modifier.size(60.dp, 14.dp).press(label = "Lukk") { close() }, contentAlignment = Alignment.Center) {
                            Box(Modifier.size(40.dp, 5.dp).clip(CircleShape).background(SourceTok.ink.copy(alpha = 0.4f)))
                        }
                    }
                    Row(
                        Modifier.padding(start = 4.dp, end = 4.dp, top = 4.dp, bottom = 8.dp),
                        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp),
                    ) {
                        SourceCover(key, 56.dp, 10.dp, modifier = Modifier.shadow(8.dp, RoundedCornerShape(10.dp)))
                        Column(verticalArrangement = Arrangement.spacedBy(3.dp)) {
                            T(title, sora(18f, W.Semibold), maxLines = 1)
                            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                SourceIcon(m.v4SrcIcon, 16.dp)
                                T(artist, sora(14f, W.Regular, SourceTok.ink.copy(alpha = 0.7f)), maxLines = 1)
                            }
                        }
                    }
                    MoreRow(if (isFav) "Lagret i Skjold-favoritter" else "Lagre i Skjold-favoritter", SourceTok.heart, isFav, if (isFav) SourceTok.gold else SourceTok.ink) {
                        if (radioOnly) m.toggleFav(m.curRadio)
                        else {
                            val f = favs.toMutableSet()
                            if (title in f) f.remove(title) else { f.add(title); Haptics.success() }
                            favsRaw = f.sorted().joinToString("\n")
                            Store.setString("skjold-v4-favs", favsRaw)
                        }
                    }
                    MoreRow("Spill neste", SourceTok.queue) {
                        if (t != null) { m.srcPlayNext(t); Haptics.success() } else Haptics.warning()
                        close()
                    }
                    val who = artist.split(" · ").firstOrNull() ?: artist
                    MoreRow("Søk etter $who", SourceTok.search) { close(); m.openSearch(who) }
                    MoreRow("Fjern fra køen", SourceTok.close) {
                        if (t != null) m.srcQueueRemove(t)
                        close()
                    }
                    MoreRow("Sovetimer", SourceTok.sleep, ic = if (SourceUi.sleep > 0) SourceTok.gold else SourceTok.ink, value = sleeps[minOf(SourceUi.sleep, sleeps.size - 1)]) {
                        // sovetimeren går på enheten (skrur ned det siste minuttet og slår av), så den virker også når appen lukkes
                        SourceUi.sleep = (SourceUi.sleep + 1) % sleeps.size
                        val mins = sleepMin[SourceUi.sleep]
                        m.devSend("/api/plugins/sleep", if (mins > 0) mapOf("enabled" to true, "minutes" to mins) else mapOf("enabled" to false))
                    }
                    Box(Modifier.padding(horizontal = 4.dp, vertical = 6.dp).fillMaxWidth().height(1.dp).background(Color.White.copy(alpha = 0.1f)))
                    Row(
                        Modifier.padding(horizontal = 4.dp).heightIn(min = 48.dp),
                        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp),
                    ) {
                        Box(Modifier.width(40.dp), contentAlignment = Alignment.Center) { SourceIcon(m.v4SrcIcon, 34.dp) }
                        Column(verticalArrangement = Arrangement.spacedBy(1.dp)) {
                            T(if (m.headphones && m.input == 4) "USB" else m.srcName, sora(15f, W.Semibold))
                            T(m.quality, mono(11f, SourceTok.ink.copy(alpha = 0.6f)))
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun MoreRow(n: String, p: String, fill: Boolean = false, ic: Color = SourceTok.ink, value: String? = null, act: () -> Unit) {
    Row(
        Modifier.fillMaxWidth().heightIn(min = 50.dp).press { Haptics.tap(); act() }.padding(horizontal = 4.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Box(Modifier.size(40.dp).clip(CircleShape).background(SourceTok.ink.copy(alpha = 0.12f)), contentAlignment = Alignment.Center) {
            if (fill) SKIcon(p, 21.dp, color = ic, fill = true)
            SKIcon(p, 21.dp, color = ic)
        }
        T(n, sora(16f, W.Semibold, lineHeight = 1.3f), Modifier.weight(1f))
        if (value != null) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                T(value, sora(14f, W.Regular, SourceTok.ink.copy(alpha = 0.65f)))
                SKIcon(SourceTok.chevRight, 16.dp, 2.2f, SourceTok.ink)
            }
        }
    }
}
