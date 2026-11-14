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
import androidx.compose.foundation.background
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBars
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.layout.imePadding
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull
import org.json.JSONObject
import java.net.URLEncoder

/**
 * «Lag kassett» (V4Kassett.swift): velg album, radio, spilleliste eller podkast → hold telefonen mot NFC-brikken
 * (UID leses, NDEF-lenken skjold://kassett/<UID> skrives) → kassetten registreres på Skjold (POST /api/nfc/cards) →
 * etiketten (GET /api/nfc/label) skrives ut via Android-utskrift (skriver eller «Lagre som PDF», i stedet for iOS'
 * delingsark). Uten NFC brukes Kassett-spilleren i læremodus.
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

/** Tekstfelt som iOS' TextField med v4Card(radius: 12) og padding 12. Enter/Søk kaller [submit]. */
@Composable
fun KassettField(placeholder: String, text: String, onChange: (String) -> Unit, caps: Boolean = true, submit: () -> Unit = {}) {
    val focus = LocalFocusManager.current
    BasicTextField(
        value = text, onValueChange = onChange, singleLine = true,
        textStyle = sora(17f, W.Regular, SourceTok.ink), cursorBrush = SolidColor(SourceTok.goldDark),
        keyboardOptions = KeyboardOptions(capitalization = if (caps) KeyboardCapitalization.Sentences else KeyboardCapitalization.None,
            autoCorrectEnabled = false, imeAction = ImeAction.Search),
        keyboardActions = KeyboardActions(onSearch = { focus.clearFocus(); submit() }),
        modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(SourceTok.card).skBorder(SourceTok.line, 12.dp),
        decorationBox = { inner ->
            Box(Modifier.fillMaxWidth().padding(12.dp), contentAlignment = Alignment.CenterStart) {
                if (text.isEmpty()) T(placeholder, sora(17f, W.Regular, SourceTok.muted), maxLines = 1)
                inner()
            }
        },
    )
}

/** Gullknapp 48 (primary i V4Kassett.swift). */
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
    var phase by remember { mutableStateOf("velg") }
    var status by remember { mutableStateOf("") }
    var svg by remember { mutableStateOf<String?>(null) }
    var showDel by remember { mutableStateOf(false) }
    val host = m.settingsHost

    BackHandler { if (showDel) showDel = false else m.showKassett = false }

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
        Haptics.success()
        status = "Lager etiketten …"
        svg = DeviceLink.get("/api/nfc/label?uids=$uid", on = host, timeout = 20.0)?.let { String(it) }
        phase = "ferdig"
    }

    // NFC: lesermodus mens vi venter på brikken
    val tagWait = remember { mutableStateOf<CompletableDeferred<Tag>?>(null) }
    DisposableEffect(phase) {
        val act = ctx.activity()
        if (phase == "skriv" && canNfc && act != null) {
            nfc!!.enableReaderMode(act, { tag -> tagWait.value?.complete(tag) },
                NfcAdapter.FLAG_READER_NFC_A or NfcAdapter.FLAG_READER_SKIP_NDEF_CHECK or NfcAdapter.FLAG_READER_NO_PLATFORM_SOUNDS, null)
        }
        onDispose { if (act != null && canNfc) runCatching { nfc!!.disableReaderMode(act) } }
    }

    fun start() {
        if (pick == null) return
        status = ""; phase = "skriv"
        scope.launch {
            if (canNfc) {
                status = "Venter på brikken …"
                val wait = CompletableDeferred<Tag>(); tagWait.value = wait
                val tag = withTimeoutOrNull(60_000) { wait.await() }
                tagWait.value = null
                if (tag == null) { status = "Fant ingen brikke. Prøv igjen."; phase = "velg"; return@launch }
                val uid = uidOf(tag)
                withContext(Dispatchers.IO) { writeNdef(tag, uid) }
                if (DeviceLink.send("/api/nfc/cards", draft(uid), on = host, timeout = 8.0) == null) {
                    status = "Skjold tok ikke imot kassetten"; phase = "velg"; return@launch
                }
                finish(uid)
            } else {
                status = "Venter på kassetten (60 s) …"
                fun last(d: ByteArray?): JSONObject? = d?.let { runCatching { JSONObject(String(it)).optJSONObject("last") }.getOrNull() }
                val before = last(DeviceLink.get("/api/nfc", on = host))?.optDouble("t") ?: 0.0
                DeviceLink.send("/api/nfc/learn", mapOf("timeout" to 60, "kort" to draft(null)), on = host)
                repeat(60) {
                    delay(1000)
                    val l = last(DeviceLink.get("/api/nfc", on = host))
                    if (l != null && l.optDouble("t") > before && l.optBoolean("known")) { finish(l.optString("uid")); return@launch }
                }
                DeviceLink.send("/api/nfc/learn", mapOf("stop" to true), on = host)
                status = "Fant ingen kassett. Prøv igjen."; phase = "velg"
            }
        }
    }

    Column(
        Modifier.fillMaxSize().background(SourceTok.bg).windowInsetsPadding(WindowInsets.statusBars).imePadding()
            .verticalScroll(rememberScrollState()).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(18.dp),
    ) {
        // gripehåndtak som iOS' presentationDragIndicator
        Box(Modifier.fillMaxWidth().padding(bottom = 0.dp), contentAlignment = Alignment.Center) {
            Box(Modifier.size(36.dp, 5.dp).clip(CircleShape).background(SourceTok.ink.copy(alpha = 0.3f)))
        }
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            T("Lag kassett", sora(24f, W.Semibold), Modifier.weight(1f))
            T("Lukk", sora(15f, W.Regular, SourceTok.gold), Modifier.press { m.showKassett = false })
        }
        when (phase) {
            "velg" -> Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
                KassettWrappedCard(host)
                T("Del kassettene med en venn", sora(14f, W.Regular, SourceTok.gold), Modifier.press { showDel = true })
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    for ((k, label) in kSrcs) {
                        val on = src == k
                        Box(
                            Modifier.height(34.dp).clip(CircleShape).background(if (on) SourceTok.selBg else SourceTok.card)
                                .skCapsuleBorder(if (on) SourceTok.goldDark else SourceTok.line2)
                                .press { src = k; pick = null }.padding(horizontal = 14.dp),
                            contentAlignment = Alignment.Center,
                        ) { T(label, sora(13f, W.Regular, if (on) SourceTok.gold else SourceTok.ink), maxLines = 1) }
                    }
                }
                if (src == "album") {
                    KassettField("Artist - Album", query, { query = it }) { submitted++ }
                    T("Spilles fra Navidrome hvis du har albumet, ellers fra YouTube Music. Skriv f.eks. «Linkin Park - Meteora».", sora(12f, W.Regular, SourceTok.muted))
                }
                if (src == "podkast") KassettField("Søk i NRK-podkaster", query, { query = it }, caps = false) { submitted++ }
                if (busy) KassettSpinner()
                if (hits.isEmpty() && !busy) T(when (src) {
                    "radio" -> "Ingen radiofavoritter på denne Skjold ennå."
                    "liste" -> if (m.ndConf.ok) "Fant ingen spillelister i Navidrome." else "Navidrome er ikke satt opp i Innstillinger."
                    "podkast" -> "Søk etter en podkast eller et program."
                    else -> "Skriv artist og album, og trykk Enter."
                }, sora(13f, W.Regular, SourceTok.muted))
                Column(Modifier.kCard()) {
                    hits.forEach { h ->
                        Row(
                            Modifier.fillMaxWidth().press { pick = h; navn = h.navn }.padding(horizontal = 14.dp, vertical = 10.dp),
                            verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp),
                        ) {
                            AsyncImage(model = DeviceLink.coverURL(h.omslag, on = host), contentDescription = null,
                                modifier = Modifier.size(40.dp).clip(RoundedCornerShape(8.dp)).background(SourceTok.row))
                            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                                T(h.navn, sora(15f), maxLines = 1)
                                T(h.under, sora(12f, W.Regular, SourceTok.muted), maxLines = 1)
                            }
                            if (pick == h) T("Valgt", sora(13f, W.Regular, SourceTok.gold))
                        }
                    }
                }
                if (pick != null) {
                    KassettField("Navn på etiketten", navn, { navn = it })
                    KassettPrimary(if (canNfc) "Hold telefonen mot brikken" else "Koble med Kassett-spilleren") { start() }
                    if (!canNfc) T(if (nfc == null) "Telefonen har ikke NFC. Sett kassetten i Skjold Kassett-spilleren når du blir bedt om det."
                        else "NFC er slått av i telefonens innstillinger. Slå det på, eller sett kassetten i Skjold Kassett-spilleren når du blir bedt om det.",
                        sora(12f, W.Regular, SourceTok.muted))
                }
                if (status.isNotEmpty()) T(status, sora(13f, W.Regular, SourceTok.red))
            }
            "skriv" -> Column(Modifier.kCard().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                SourceKicker(if (canNfc) "NFC" else "LÆREMODUS")
                T(if (canNfc) "Hold baksiden av telefonen mot kassetten." else "Sett kassetten inn i Skjold Kassett-spilleren nå.", sora(15f, W.Regular, SourceTok.ink))
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    KassettSpinner()
                    T(status, sora(13f, W.Regular, SourceTok.muted))
                }
                // Android har ikke systemets NFC-ark med Avbryt (iOS), så vi gir en egen
                if (canNfc) KassettSecondary("Avbryt") { tagWait.value?.cancel(); tagWait.value = null; status = ""; phase = "velg" }
            }
            else -> Column(Modifier.kCard().padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                T("✓ Kassetten er klar", sora(18f, W.Semibold, SourceTok.green))
                T("Skriv ut etiketten på A4 (100 %), klipp langs den røde linja og lim den i forsenkningen.", sora(13f, W.Regular, SourceTok.ink))
                val s = svg
                if (s != null) KassettPrimary("Del eller skriv ut etikett") { printLabel(ctx, s, navn.ifBlank { pick?.navn ?: "Kassett" }) }
                else T("Fikk ikke laget PDF – skriv ut fra Kassetter i web-appen.", sora(13f, W.Regular, SourceTok.muted))
                KassettSecondary("Lag en kassett til") { pick = null; navn = ""; svg = null; status = ""; phase = "velg" }
            }
        }
    }
    if (showDel) KassettDelSheet(host) { showDel = false }
}
