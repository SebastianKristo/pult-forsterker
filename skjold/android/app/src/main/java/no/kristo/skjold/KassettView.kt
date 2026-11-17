package no.kristo.skjold

import android.app.Activity
import android.content.Context
import android.content.ContextWrapper
import android.nfc.NdefMessage
import android.nfc.NdefRecord
import android.nfc.NfcAdapter
import android.nfc.Tag
import android.nfc.tech.Ndef
import android.nfc.tech.NdefFormatable
import android.print.PrintAttributes
import android.print.PrintManager
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.compose.BackHandler
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
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
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.NonCancellable
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull
import org.json.JSONObject
import java.net.URLEncoder

/**
 * «Lag kassett» (V4Kassett.swift): en veiviser i Apple-stil (intro → velg → navn → skriv → ferdig) med én ting per
 * side, stor tittel, forklaring og én hovedknapp nederst. Velg album, radio, spilleliste eller podkast → hold baksiden
 * av telefonen mot NFC-brikken (UID leses, NDEF-lenken skjold://kassett/<UID> skrives) → kassetten registreres på
 * Skjold (POST /api/nfc/cards) → etiketten (GET /api/nfc/label) skrives ut via Android-utskrift (skriver eller
 * «Lagre som PDF», i stedet for iOS' delingsark). Uten NFC brukes Kassett-spilleren i læremodus.
 * Illustrasjonene ligger i KassettGuide.kt.
 */
private data class KPick(val navn: String, val under: String, val omslag: String, val handling: String, val verdi: Any)

/** «Artist - Album» → album-kassett. Skjold slår opp om den spilles fra Navidrome eller YouTube Music. */
private fun albumPick(text: String, kilde: String = ""): KPick {
    val i = text.indexOf(" - ")
    val artist = if (i > 0) text.substring(0, i).trim() else ""
    val album = (if (i > 0) text.substring(i + 3) else text).trim()
    val cover = "/api/nfc/cover?artist=" + URLEncoder.encode(artist, "UTF-8").replace("+", "%20") + "&album=" + URLEncoder.encode(album, "UTF-8").replace("+", "%20")
    return KPick(album, if (kilde.isEmpty()) artist else "$artist · $kilde", cover, "album", "$artist - $album")
}

private tailrec fun Context.activity(): Activity? = when (this) {
    is Activity -> this
    is ContextWrapper -> baseContext.activity()
    else -> null
}

private fun uidOf(tag: Tag): String = tag.id.joinToString("-") { "%02X".format(it) }

/** Skriver lenken på brikken. Låste/ikke-NDEF-brikker hoppes over – UID-en er det leseren bruker. */
private fun writeNdef(tag: Tag, uid: String) {
    val msg = NdefMessage(arrayOf(NdefRecord.createUri("skjold://kassett/$uid")))
    try {
        Ndef.get(tag)?.let { n -> n.connect(); try { if (n.isWritable) n.writeNdefMessage(msg) } finally { n.close() }; return }
        NdefFormatable.get(tag)?.let { f -> f.connect(); try { f.format(msg) } finally { f.close() } }
    } catch (_: Exception) { /* UID holder */ }
}

private fun printLabel(ctx: Context, svg: String, name: String) {
    val wv = WebView(ctx)
    wv.webViewClient = object : WebViewClient() {
        override fun onPageFinished(view: WebView, url: String?) {
            val pm = ctx.getSystemService(Context.PRINT_SERVICE) as PrintManager
            pm.print("Kassett – $name", view.createPrintDocumentAdapter("Kassett – $name"),
                PrintAttributes.Builder().setMediaSize(PrintAttributes.MediaSize.ISO_A4).setMinMargins(PrintAttributes.Margins.NO_MARGINS).build())
        }
    }
    val html = "<!doctype html><meta charset=utf-8><style>@page{size:A4;margin:0}body{margin:0}svg{width:210mm;height:297mm}</style>$svg"
    wv.loadDataWithBaseURL(null, html, "text/html", "utf-8", null)
}

/** iOS' ProgressView: liten spinner i gull. */
@Composable
fun KassettSpinner() = CircularProgressIndicator(Modifier.size(20.dp), color = SourceTok.gold, strokeWidth = 2.dp)

/** Tekstfelt som iOS' TextField med v4Card(radius: 12) og padding 12. Enter/Søk/Ferdig kaller [submit]. */
@Composable
fun KassettField(
    placeholder: String, text: String, onChange: (String) -> Unit, caps: Boolean = true,
    ime: ImeAction = ImeAction.Search, submit: () -> Unit = {},
) {
    val focus = LocalFocusManager.current
    BasicTextField(
        value = text, onValueChange = onChange, singleLine = true,
        textStyle = sora(17f, W.Regular, SourceTok.ink), cursorBrush = SolidColor(SourceTok.goldDark),
        keyboardOptions = KeyboardOptions(capitalization = if (caps) KeyboardCapitalization.Sentences else KeyboardCapitalization.None,
            autoCorrectEnabled = false, imeAction = ime),
        keyboardActions = KeyboardActions(
            onSearch = { focus.clearFocus(); submit() },
            onDone = { focus.clearFocus(); submit() },
        ),
        modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(SourceTok.card).skBorder(SourceTok.line, 12.dp),
        decorationBox = { inner ->
            Box(Modifier.fillMaxWidth().padding(12.dp), contentAlignment = Alignment.CenterStart) {
                if (text.isEmpty()) T(placeholder, sora(17f, W.Regular, SourceTok.muted), maxLines = 1)
                inner()
            }
        },
    )
}

/** Gullknapp 48 (brukes også av KassettDelSheet). */
@Composable
fun KassettPrimary(t: String, bg: Color = SourceTok.goldDark, action: () -> Unit) {
    Box(Modifier.fillMaxWidth().height(48.dp).clip(CircleShape).background(bg).press(onClick = action), contentAlignment = Alignment.Center) {
        T(t, sora(15f, W.Semibold, SourceTok.bg), maxLines = 1)
    }
}

/** Kantknapp 44 (secondary). */
@Composable
fun KassettSecondary(t: String, action: () -> Unit) {
    Box(Modifier.fillMaxWidth().height(44.dp).clip(CircleShape).skCapsuleBorder(SourceTok.line2).press(onClick = action), contentAlignment = Alignment.Center) {
        T(t, sora(14f, W.Regular, SourceTok.ink), maxLines = 1)
    }
}

/** v4Card: #141415, kant #242426. */
private fun Modifier.kCard(radius: androidx.compose.ui.unit.Dp = 22.dp): Modifier =
    this.fillMaxWidth().clip(RoundedCornerShape(radius)).background(SourceTok.card).skBorder(SourceTok.line, radius)

private val kSrcs = listOf("album" to "Album", "radio" to "Radio", "liste" to "Spilleliste", "podkast" to "Podkast")

/** Stegene i veiviseren (som Apples oppsettsflyter: én ting per side, stor tittel, forklaring, én hovedknapp). */
private enum class KFase { Intro, Velg, Navn, Skriv, Ferdig }

/** Hovedknappen nederst: gullkapsel 52 høy, grå når den ikke kan trykkes ennå. */
@Composable
private fun KHovedknapp(t: String, enabled: Boolean = true, ikon: String? = null, action: () -> Unit) {
    val bg by animateColorAsState(if (enabled) SourceTok.goldDark else C.dim, label = "hovedknapp")
    Row(
        Modifier.fillMaxWidth().height(52.dp).clip(CircleShape).background(bg).press(enabled = enabled, onClick = action),
        horizontalArrangement = Arrangement.spacedBy(8.dp, Alignment.CenterHorizontally),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        if (ikon != null) SKIcon(ikon, 20.dp, 1.9f, SourceTok.bg)
        T(t, sora(16f, W.Semibold, SourceTok.bg), maxLines = 1)
    }
}

/** Sekundærknapp: dempet glasskapsel 48 høy. */
@Composable
private fun KSekundaerknapp(t: String, action: () -> Unit) {
    Box(
        Modifier.fillMaxWidth().height(48.dp).clip(CircleShape).background(SourceTok.glassBg).skCapsuleBorder(SourceTok.glassLine)
            .press(onClick = action),
        contentAlignment = Alignment.Center,
    ) { T(t, sora(15f, W.Regular, SourceTok.ink), maxLines = 1) }
}

/** Rund glassknapp 44 i toppen (tilbake / lukk). */
@Composable
private fun KRundknapp(ikon: String, label: String, action: () -> Unit) {
    Box(
        Modifier.size(44.dp).clip(CircleShape).background(SourceTok.glassBg).skCapsuleBorder(SourceTok.glassLine)
            .press(label = label, onClick = action),
        contentAlignment = Alignment.Center,
    ) { SKIcon(ikon, 18.dp, 2.4f, SourceTok.ink) }
}

/** Stor sidetittel med forklaring under (venstrejustert). */
@Composable
private fun KTittel(tittel: String, tekst: String, storrelse: Float = 28f) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        T(tittel, sora(storrelse, W.Semibold).copy(letterSpacing = (-0.02f * storrelse).sp))
        T(tekst, sora(14f, W.Regular, SourceTok.body, lineHeight = 1.45f))
    }
}

/** «Lag kassett» som helskjermsark over appen (m.showKassett). */
@Composable
fun KassettView(m: AppModel) {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    val nfc = remember { NfcAdapter.getDefaultAdapter(ctx) }
    val canNfc = nfc?.isEnabled == true
    var src by remember { mutableStateOf("album") }
    var query by remember { mutableStateOf("") }
    var submitted by remember { mutableStateOf(0) }
    var hits by remember { mutableStateOf(listOf<KPick>()) }
    var busy by remember { mutableStateOf(false) }
    var pick by remember { mutableStateOf<KPick?>(null) }
    var navn by remember { mutableStateOf("") }
    var phase by remember { mutableStateOf(KFase.Intro) }
    var status by remember { mutableStateOf("") }
    var svg by remember { mutableStateOf<String?>(null) }
    var showDel by remember { mutableStateOf(false) }
    // jobben som venter på brikken / kassetten; null når ingenting kan avbrytes
    var jobb by remember { mutableStateOf<Job?>(null) }
    val host = m.settingsHost

    fun go(p: KFase) { Haptics.tick(); phase = p }

    /** Avbryter ventingen på brikken. I læremodus sender jobben selv /api/nfc/learn {stop:true} når den avsluttes. */
    fun avbryt() {
        val j = jobb ?: return
        jobb = null
        j.cancel()
        status = ""
        go(KFase.Navn)
    }

    fun lukk() { jobb?.cancel(); jobb = null; m.showKassett = false }

    BackHandler {
        when {
            showDel -> showDel = false
            phase == KFase.Velg -> go(KFase.Intro)
            phase == KFase.Navn -> go(KFase.Velg)
            phase == KFase.Skriv -> avbryt()
            else -> lukk()
        }
    }

    // Som iOS: lastes når kilden byttes, og når du trykker Søk i feltet (album/podkast)
    LaunchedEffect(src, submitted) {
        hits = emptyList(); busy = true
        try {
            hits = when (src) {
                "album" -> {
                    val q = query.trim()
                    if (q.length < 2) emptyList() else {
                        val d = DeviceLink.get("/api/nfc/sok?q=" + URLEncoder.encode(q, "UTF-8"), on = host, timeout = 12.0)
                        val arr = d?.let { runCatching { JSONObject(String(it)).optJSONArray("treff") }.getOrNull() }
                        listOf(albumPick(q)) + (0 until minOf(10, arr?.length() ?: 0)).mapNotNull { i ->
                            val o = arr!!.getJSONObject(i)
                            val al = o.optString("album")
                            if (al.isEmpty()) null else albumPick(o.optString("artist") + " - " + al, o.optString("kilde"))
                        }
                    }
                }
                "radio" -> m.radio.mapIndexed { i, s -> KPick(s.name, s.genre.ifEmpty { "Radio" }, s.image ?: "", "preset", i + 1) }
                "liste" -> if (!m.ndConf.ok) emptyList() else Subsonic.playlists(m.ndConf).getOrNull().orEmpty()
                    .map { KPick(it.name, "Spilleliste · ${it.count} låter", it.cover, "navidrome_playlist", it.id) }
                else -> {
                    val q = query.trim()
                    if (q.length < 2) emptyList() else {
                        val d = DeviceLink.get("/api/nrk/search?q=" + URLEncoder.encode(q, "UTF-8"), on = host, timeout = 12.0)
                        val arr = d?.let { runCatching { JSONObject(String(it)).optJSONArray("series") }.getOrNull() }
                        (0 until (arr?.length() ?: 0)).map { i ->
                            val o = arr!!.getJSONObject(i)
                            KPick(o.optString("title"), o.optString("subtitle", "NRK"), o.optString("image"), "nrk", mapOf("series" to o.optString("id")))
                        }
                    }
                }
            }
        } finally { busy = false }
    }

    fun draft(uid: String?): Map<String, Any?> {
        val p = pick!!
        return buildMap {
            if (uid != null) put("uid", uid)
            put("navn", navn.ifBlank { p.navn }); put("handling", p.handling); put("verdi", p.verdi)
            put("omslag", p.omslag); put("undertittel", if (p.handling == "album") p.under.substringBefore(" · ") else p.under)
            put("ved_uttak", "pause"); put("rom", emptyList<String>())
        }
    }

    suspend fun finish(uid: String) {
        jobb = null   // kassetten er registrert – ikke lenger mulig å avbryte
        Haptics.success()
        status = "Lager etiketten …"
        svg = DeviceLink.get("/api/nfc/label?uids=$uid", on = host, timeout = 20.0)?.let { String(it) }
        go(KFase.Ferdig)
    }

    // NFC: lesermodus mens vi venter på brikken
    val tagWait = remember { mutableStateOf<CompletableDeferred<Tag>?>(null) }
    DisposableEffect(phase) {
        val act = ctx.activity()
        if (phase == KFase.Skriv && canNfc && act != null) {
            nfc!!.enableReaderMode(act, { tag -> tagWait.value?.complete(tag) },
                NfcAdapter.FLAG_READER_NFC_A or NfcAdapter.FLAG_READER_SKIP_NDEF_CHECK or NfcAdapter.FLAG_READER_NO_PLATFORM_SOUNDS, null)
        }
        onDispose { if (act != null && canNfc) runCatching { nfc!!.disableReaderMode(act) } }
    }

    fun start() {
        if (pick == null) return
        status = ""; go(KFase.Skriv)
        jobb = scope.launch {
            if (canNfc) {
                status = "Venter på brikken …"
                val wait = CompletableDeferred<Tag>(); tagWait.value = wait
                val tag = try { withTimeoutOrNull(60_000) { wait.await() } } finally { tagWait.value = null }
                if (tag == null) { jobb = null; status = "Fant ingen brikke. Prøv igjen."; go(KFase.Navn); return@launch }
                Haptics.thump()
                status = "Kobler kassetten …"
                val uid = uidOf(tag)
                withContext(Dispatchers.IO) { writeNdef(tag, uid) }
                if (DeviceLink.send("/api/nfc/cards", draft(uid), on = host, timeout = 8.0) == null) {
                    jobb = null; status = "Skjold tok ikke imot kassetten"; go(KFase.Navn); return@launch
                }
                finish(uid)
            } else {
                status = "Venter på kassetten (60 s) …"
                fun last(d: ByteArray?): JSONObject? = d?.let { runCatching { JSONObject(String(it)).optJSONObject("last") }.getOrNull() }
                val before = last(DeviceLink.get("/api/nfc", on = host))?.optDouble("t") ?: 0.0
                var funnet: String? = null
                try {
                    DeviceLink.send("/api/nfc/learn", mapOf("timeout" to 60, "kort" to draft(null)), on = host)
                    for (n in 0 until 60) {
                        delay(1000)
                        val l = last(DeviceLink.get("/api/nfc", on = host))
                        if (l != null && l.optDouble("t") > before && l.optBoolean("known")) { funnet = l.optString("uid"); break }
                    }
                } finally {
                    // tidsavbrudd, «Avbryt» eller lukket ark: be spilleren slutte å lære
                    if (funnet == null) withContext(NonCancellable) { DeviceLink.send("/api/nfc/learn", mapOf("stop" to true), on = host) }
                }
                val uid = funnet
                if (uid != null) finish(uid)
                else { jobb = null; status = "Fant ingen kassett. Prøv igjen."; go(KFase.Navn) }
            }
        }
    }

    val visNavn = navn.ifEmpty { pick?.navn ?: "" }

    Column(
        Modifier.fillMaxSize().background(SourceTok.sheet).windowInsetsPadding(WindowInsets.statusBars).imePadding(),
    ) {
        // gripehåndtak som iOS' presentationDragIndicator
        Box(Modifier.fillMaxWidth().padding(top = 6.dp), contentAlignment = Alignment.Center) {
            Box(Modifier.size(36.dp, 5.dp).clip(CircleShape).background(SourceTok.ink.copy(alpha = 0.3f)))
        }
        // toppen: tilbake, stegprikker, lukk
        Row(
            Modifier.fillMaxWidth().padding(start = 16.dp, end = 16.dp, top = 8.dp, bottom = 6.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            if (phase == KFase.Velg || phase == KFase.Navn) {
                KRundknapp(Icons.back, "Tilbake") { go(if (phase == KFase.Navn) KFase.Velg else KFase.Intro) }
            } else {
                Spacer(Modifier.size(44.dp))
            }
            Box(Modifier.weight(1f), contentAlignment = Alignment.Center) {
                if (phase != KFase.Intro) KassettStegPrikker(steg = phase.ordinal - 1, antall = 4)
            }
            KRundknapp(Icons.close, "Lukk") { lukk() }
        }

        AnimatedContent(
            targetState = phase,
            transitionSpec = {
                (slideInHorizontally(tween(350)) { it / 4 } + fadeIn(tween(350))) togetherWith fadeOut(tween(180))
            },
            modifier = Modifier.weight(1f).fillMaxWidth(),
            label = "kassettsteg",
        ) { p ->
            Column(
                Modifier.fillMaxSize().verticalScroll(rememberScrollState())
                    .padding(start = 24.dp, end = 24.dp, top = 8.dp, bottom = 24.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Column(Modifier.widthIn(max = 560.dp).fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(22.dp)) {
                    when (p) {
                        KFase.Intro -> IntroSide(canNfc, host) { showDel = true }
                        KFase.Velg -> VelgSide(
                            m, host, src, { src = it; pick = null }, query, { query = it }, { submitted++ },
                            busy, hits, pick, { pick = it; navn = it.navn }, status,
                        )
                        KFase.Navn -> NavnSide(visNavn, pick?.under ?: "", navn, { navn = it }, canNfc, nfc != null, status)
                        KFase.Skriv -> SkrivSide(canNfc, visNavn, status)
                        KFase.Ferdig -> FerdigSide(visNavn.ifEmpty { "kassetten" }, visNavn, pick?.under ?: "", svg != null)
                    }
                }
            }
        }

        // bunnen: én hovedknapp
        Column(
            Modifier.fillMaxWidth().navigationBarsPadding().padding(start = 24.dp, end = 24.dp, top = 10.dp, bottom = 12.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Column(Modifier.widthIn(max = 560.dp).fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                when (phase) {
                    KFase.Intro -> KHovedknapp("Kom i gang") { go(KFase.Velg) }
                    KFase.Velg -> KHovedknapp("Fortsett", enabled = pick != null) { go(KFase.Navn) }
                    KFase.Navn -> KHovedknapp(if (canNfc) "Skriv kassetten" else "Koble kassetten") { start() }
                    // Android har ikke systemets NFC-ark med Avbryt (iOS), så begge modusene får en egen
                    KFase.Skriv -> { if (jobb != null) KSekundaerknapp("Avbryt") { avbryt() } }
                    KFase.Ferdig -> {
                        val s = svg
                        if (s != null) KHovedknapp("Skriv ut eller del etiketten", ikon = KassettIkon.skriver) {
                            printLabel(ctx, s, navn.ifBlank { pick?.navn ?: "Kassett" })
                        }
                        KSekundaerknapp("Lag en kassett til") {
                            pick = null; navn = ""; svg = null; status = ""; go(KFase.Velg)
                        }
                    }
                }
            }
        }
    }
    if (showDel) KassettDelSheet(host) { showDel = false }
}

// MARK: 0 – introduksjon

@Composable
private fun IntroSide(canNfc: Boolean, host: String?, visDel: () -> Unit) {
    Box(Modifier.fillMaxWidth().padding(vertical = 18.dp)) { KassettHelt(etikett = "Skjold", under = "Lag din egen") }
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        T("Lag en kassett", sora(30f, W.Semibold).copy(letterSpacing = (-0.6f).sp))
        T(
            "Gjør et album, en radiokanal, en spilleliste eller en podkast om til en kassett. Sett den i Skjold Kassett, så begynner musikken.",
            sora(15f, W.Regular, SourceTok.body, lineHeight = 1.45f),
        )
    }
    Column(verticalArrangement = Arrangement.spacedBy(18.dp)) {
        KassettForklaring(KassettIkon.musikk, "Velg hva den skal spille", "Album, radiokanal, spilleliste fra Navidrome eller podkast fra NRK.")
        if (canNfc) KassettForklaring(KassettIkon.nfc, "Hold telefonen mot kassetten", "Baksiden av telefonen mot brikken i kassetten. Det tar et par sekunder.")
        else KassettForklaring(KassettIkon.settInn, "Sett kassetten i spilleren", "Skjold Kassett leser brikken og husker hva den skal spille.")
        KassettForklaring(KassettIkon.skriver, "Skriv ut etiketten", "Du får en ferdig etikett med omslag og navn som limes på kassetten.")
    }
    Box(Modifier.fillMaxWidth().height(1.dp).background(SourceTok.line))
    KassettWrappedCard(host)
    Row(Modifier.press(onClick = visDel), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
        SKIcon(KassettIkon.del, 18.dp, 1.8f, SourceTok.gold)
        T("Del kassettene med en venn", sora(14f, W.Regular, SourceTok.gold))
    }
}

// MARK: 1 – velg hva kassetten skal spille

@Composable
private fun VelgSide(
    m: AppModel, host: String?, src: String, setSrc: (String) -> Unit, query: String, setQuery: (String) -> Unit, submit: () -> Unit,
    busy: Boolean, hits: List<KPick>, pick: KPick?, velg: (KPick) -> Unit, status: String,
) {
    Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        KTittel("Hva skal den spille?", "Velg én ting. Du kan lage så mange kassetter du vil.")
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            for ((k, label) in kSrcs) {
                val on = src == k
                Box(
                    Modifier.height(34.dp).clip(CircleShape).background(if (on) SourceTok.selBg else SourceTok.card)
                        .skCapsuleBorder(if (on) SourceTok.goldDark else SourceTok.line2)
                        .press { setSrc(k) }.padding(horizontal = 14.dp),
                    contentAlignment = Alignment.Center,
                ) { T(label, sora(13f, W.Regular, if (on) SourceTok.gold else SourceTok.ink), maxLines = 1) }
            }
        }
        if (src == "album") {
            KassettField("Artist - Album", query, setQuery, submit = submit)
            T("Spilles fra Navidrome hvis du har albumet, ellers fra YouTube Music. Skriv f.eks. «Linkin Park - Meteora».", sora(12f, W.Regular, SourceTok.muted))
        }
        if (src == "podkast") KassettField("Søk i NRK-podkaster", query, setQuery, caps = false, submit = submit)
        if (busy) KassettSpinner()
        if (hits.isEmpty() && !busy) T(when (src) {
            "radio" -> "Ingen radiofavoritter på denne Skjold ennå."
            "liste" -> if (m.ndConf.ok) "Fant ingen spillelister i Navidrome." else "Navidrome er ikke satt opp i Innstillinger."
            "podkast" -> "Søk etter en podkast eller et program."
            else -> "Skriv artist og album, og trykk Enter."
        }, sora(13f, W.Regular, SourceTok.muted))
        if (hits.isNotEmpty()) Column(Modifier.kCard()) {
            hits.forEach { h ->
                val valgt = pick == h
                Row(
                    Modifier.fillMaxWidth().press { velg(h) }.padding(horizontal = 14.dp, vertical = 10.dp),
                    verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    AsyncImage(model = DeviceLink.coverURL(h.omslag, on = host), contentDescription = null,
                        modifier = Modifier.size(40.dp).clip(RoundedCornerShape(8.dp)).background(SourceTok.row))
                    Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                        T(h.navn, sora(15f), maxLines = 1)
                        T(h.under, sora(12f, W.Regular, SourceTok.muted), maxLines = 1)
                    }
                    // avkrysningsring som iOS' checkmark.circle.fill / circle
                    Box(
                        Modifier.size(22.dp).clip(CircleShape).background(if (valgt) SourceTok.gold else Color.Transparent)
                            .skCapsuleBorder(if (valgt) SourceTok.gold else C.dim, 1.5.dp),
                        contentAlignment = Alignment.Center,
                    ) { if (valgt) SKIcon(Icons.check, 14.dp, 2.6f, SourceTok.bg) }
                }
            }
        }
        if (status.isNotEmpty()) T(status, sora(13f, W.Regular, SourceTok.red))
    }
}

// MARK: 2 – navn og forhåndsvisning

@Composable
private fun NavnSide(
    etikett: String, under: String, navn: String, setNavn: (String) -> Unit, canNfc: Boolean, harNfc: Boolean, status: String,
) {
    Column(verticalArrangement = Arrangement.spacedBy(20.dp)) {
        Box(Modifier.fillMaxWidth().padding(vertical = 8.dp), contentAlignment = Alignment.Center) {
            KassettFigur(Modifier.width(240.dp), etikett = etikett, under = under)
        }
        KTittel("Gi den et navn", "Navnet står på etiketten. Slik ser kassetten ut når den er ferdig.")
        KassettField("Navn på etiketten", navn, setNavn, ime = ImeAction.Done)
        if (!canNfc) KassettForklaring(
            KassettIkon.info, "Kassetten kobles med spilleren",
            if (!harNfc) "Telefonen har ikke NFC. Du setter kassetten i Skjold Kassett i neste steg."
            else "NFC er slått av i telefonens innstillinger. Slå det på, eller sett kassetten i Skjold Kassett i neste steg.",
        )
        if (status.isNotEmpty()) T(status, sora(13f, W.Regular, SourceTok.red))
    }
}

// MARK: 3 – skriv brikken

@Composable
private fun SkrivSide(canNfc: Boolean, etikett: String, status: String) {
    Column(Modifier.fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(18.dp)) {
        if (canNfc) KassettNFCAnimasjon(etikett = etikett) else KassettSpillerAnimasjon(etikett = etikett)
        T(
            if (canNfc) "Hold telefonen mot kassetten" else "Sett kassetten i spilleren",
            sora(26f, W.Semibold).copy(letterSpacing = (-0.5f).sp),
            align = TextAlign.Center,
        )
        T(
            if (canNfc) "Hold baksiden av telefonen helt inntil kassetten, midt på etiketten. Hold den stille til telefonen vibrerer."
            else "Skyv kassetten ned i luka på Skjold Kassett. Lampen blir grønn når brikken er lest.",
            sora(15f, W.Regular, SourceTok.body, lineHeight = 1.45f), align = TextAlign.Center,
        )
        Row(
            Modifier.padding(top = 4.dp),
            verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            KassettSpinner()
            if (status.isNotEmpty()) T(status, sora(13f, W.Regular, SourceTok.muted))
        }
    }
}

// MARK: 4 – ferdig: etikett

@Composable
private fun FerdigSide(tittel: String, etikett: String, under: String, harEtikett: Boolean) {
    Column(verticalArrangement = Arrangement.spacedBy(22.dp)) {
        Column(Modifier.fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(14.dp)) {
            KassettFerdigHake()
            T("Kassetten er klar", sora(28f, W.Semibold).copy(letterSpacing = (-0.56f).sp), align = TextAlign.Center)
            T("Sett den i Skjold Kassett, så spiller den «$tittel».", sora(15f, W.Regular, SourceTok.body, lineHeight = 1.45f), align = TextAlign.Center)
        }
        KassettEtikettAnimasjon(etikett = etikett, under = under)
        Column(verticalArrangement = Arrangement.spacedBy(18.dp)) {
            KassettForklaring("", "Skriv ut på A4", "Velg 100 % (faktisk størrelse), ikke «tilpass siden».", nummer = 1)
            KassettForklaring("", "Klipp langs den røde linja", "Etiketten passer akkurat i forsenkningen på kassetten.", nummer = 2)
            KassettForklaring("", "Lim den på", "Midt i forsenkningen, med den gule kanten opp.", nummer = 3)
        }
        if (!harEtikett) T("Fikk ikke laget etiketten her. Skriv den ut fra Kassetter i web-appen.", sora(13f, W.Regular, SourceTok.muted))
    }
}
