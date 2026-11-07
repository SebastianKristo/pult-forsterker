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
 * «Lag kassett»: velg radio, spilleliste eller podkast → hold telefonen mot NFC-brikken (UID leses, NDEF-lenken
 * skjold://kassett/<UID> skrives) → kassetten registreres på Skjold (POST /api/nfc/cards) → etiketten (GET /api/nfc/label)
 * skrives ut via Android-utskrift (lagre som PDF eller skriver). Uten NFC brukes Kassett-spilleren i læremodus.
 */
private data class KPick(val navn: String, val under: String, val omslag: String, val handling: String, val verdi: Any)

/** «Artist - Album» → album-kassett. Skjold slår opp om den spilles fra Navidrome eller YouTube Music. */
private fun albumPick(text: String, kilde: String = ""): KPick {
    val i = text.indexOf(" - ")
    val artist = if (i > 0) text.substring(0, i).trim() else ""
    val album = (if (i > 0) text.substring(i + 3) else text).trim()
    val cover = "/api/nfc/cover?artist=" + URLEncoder.encode(artist, "UTF-8") + "&album=" + URLEncoder.encode(album, "UTF-8")
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

@Composable
fun KassettView(m: AppModel) {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    val nfc = remember { NfcAdapter.getDefaultAdapter(ctx) }
    val canNfc = nfc?.isEnabled == true
    var src by remember { mutableStateOf("album") }
    var query by remember { mutableStateOf("") }
    var hits by remember { mutableStateOf(listOf<KPick>()) }
    var pick by remember { mutableStateOf<KPick?>(null) }
    var navn by remember { mutableStateOf("") }
    var phase by remember { mutableStateOf("velg") }
    var status by remember { mutableStateOf("") }
    var svg by remember { mutableStateOf<String?>(null) }
    val host = m.settingsHost

    LaunchedEffect(src, query) {
        hits = emptyList()
        hits = when (src) {
            "album" -> {
                val q = query.trim()
                if (q.length < 2) emptyList() else {
                    delay(400)
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
                    delay(350)
                    val d = DeviceLink.get("/api/nrk/search?q=" + URLEncoder.encode(q, "UTF-8"), on = host, timeout = 12.0)
                    val arr = d?.let { runCatching { JSONObject(String(it)).optJSONArray("series") }.getOrNull() }
                    (0 until (arr?.length() ?: 0)).map { i ->
                        val o = arr!!.getJSONObject(i)
                        KPick(o.optString("title"), o.optString("subtitle", "NRK"), o.optString("image"), "nrk", mapOf("series" to o.optString("id")))
                    }
                }
            }
        }
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
                status = "Hold baksiden av telefonen mot kassetten …"
                val wait = CompletableDeferred<Tag>(); tagWait.value = wait
                val tag = withTimeoutOrNull(60_000) { wait.await() }
                tagWait.value = null
                if (tag == null) { status = "Fant ingen brikke. Prøv igjen."; phase = "velg"; return@launch }
                val uid = uidOf(tag)
                withContext(Dispatchers.IO) { writeNdef(tag, uid) }
                if (DeviceLink.send("/api/nfc/cards", draft(uid), on = host, timeout = 8.0) == null) {
                    status = "Skjold tok ikke imot kassetten."; phase = "velg"; return@launch
                }
                finish(uid)
            } else {
                status = "Sett kassetten inn i Skjold Kassett-spilleren (60 s) …"
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
        Modifier.fillMaxSize().background(C.bg).windowInsetsPadding(WindowInsets.statusBars).verticalScroll(rememberScrollState()).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            T("Lag kassett", sora(24f, W.Semibold), Modifier.weight(1f))
            SKLinkButton("Lukk") { m.showKassett = false }
        }
        when (phase) {
            "velg" -> {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    SKFilterChip("Album", src == "album") { src = "album"; pick = null }
                    SKFilterChip("Radio", src == "radio") { src = "radio"; pick = null }
                    SKFilterChip("Spilleliste", src == "liste") { src = "liste"; pick = null }
                    SKFilterChip("Podkast", src == "podkast") { src = "podkast"; pick = null }
                }
                if (src == "podkast") SKField("Søk i NRK-podkaster", query, { query = it }, Modifier.fillMaxWidth())
                if (src == "album") {
                    SKField("Artist - Album", query, { query = it }, Modifier.fillMaxWidth())
                    T("Spilles fra Navidrome hvis du har albumet, ellers fra YouTube Music.", sora(12f, W.Regular, C.muted))
                }
                if (hits.isEmpty()) T(when (src) {
                    "radio" -> "Ingen radiofavoritter på denne Skjold ennå."
                    "liste" -> if (m.ndConf.ok) "Fant ingen spillelister i Navidrome." else "Navidrome er ikke satt opp i Innstillinger."
                    "album" -> "Skriv artist og album, f.eks. «Linkin Park - Meteora»."
                    else -> "Søk etter en podkast eller et program."
                }, sora(13f, W.Regular, C.muted))
                SKCard(radius = 18.dp) {
                    Column {
                        hits.forEach { h ->
                            Row(Modifier.fillMaxWidth().press { pick = h; navn = h.navn }.padding(horizontal = 14.dp, vertical = 10.dp),
                                verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                                AsyncImage(model = DeviceLink.coverURL(h.omslag, on = host), contentDescription = null,
                                    modifier = Modifier.size(40.dp).clip(RoundedCornerShape(8.dp)).background(C.card2))
                                Column(Modifier.weight(1f)) {
                                    T(h.navn, sora(15f), maxLines = 1)
                                    T(h.under, sora(12f, W.Regular, C.muted), maxLines = 1)
                                }
                                if (pick == h) T("Valgt", sora(13f, W.Regular, C.accent2))
                            }
                        }
                    }
                }
                if (pick != null) {
                    SKField("Navn på etiketten", navn, { navn = it }, Modifier.fillMaxWidth())
                    SKPill(if (canNfc) "Hold telefonen mot brikken" else "Koble med Kassett-spilleren", primary = true, height = 46.dp) { start() }
                    if (!canNfc) T(if (nfc == null) "Telefonen har ikke NFC. Sett kassetten i Skjold Kassett-spilleren når du blir bedt om det."
                        else "NFC er slått av i telefonens innstillinger – slå det på, eller bruk Kassett-spilleren.", sora(12f, W.Regular, C.muted))
                }
                if (status.isNotEmpty()) T(status, sora(13f, W.Regular, C.live))
            }
            "skriv" -> SKCard(radius = 18.dp) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    SKMonoLabel(if (canNfc) "NFC" else "LÆREMODUS")
                    T(status, sora(15f))
                    SKPill("Avbryt", height = 40.dp) { tagWait.value?.cancel(); tagWait.value = null; phase = "velg" }
                }
            }
            else -> SKCard(radius = 18.dp) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    T("✓ Kassetten er klar", sora(18f, W.Semibold, C.ok))
                    T("Skriv ut etiketten på A4 (100 %), klipp langs den røde linja og lim den i forsenkningen.", sora(13f))
                    val s = svg
                    if (s != null) SKPill("Skriv ut eller lagre som PDF", primary = true, height = 46.dp) { printLabel(ctx, s, navn.ifBlank { "Kassett" }) }
                    else T("Fikk ikke hentet etiketten – skriv ut fra Kassetter i web-appen.", sora(13f, W.Regular, C.muted))
                    SKPill("Lag en kassett til", height = 42.dp) { pick = null; navn = ""; svg = null; status = ""; phase = "velg" }
                }
            }
        }
    }
}
