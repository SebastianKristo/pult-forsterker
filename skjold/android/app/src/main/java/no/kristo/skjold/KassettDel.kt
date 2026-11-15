package no.kristo.skjold

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Color as AColor
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.compose.foundation.Image
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
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBars
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
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
import androidx.compose.ui.graphics.FilterQuality
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import coil.compose.AsyncImage
import com.google.zxing.BarcodeFormat
import com.google.zxing.EncodeHintType
import com.google.zxing.qrcode.QRCodeWriter
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject

/** Kassett-Wrapped (GET /api/nfc/stats) og deling av kassetter (POST /api/nfc/share, /api/nfc/share/import), som V4KassettDel.swift. */

/** QR-kode som Bitmap (ZXing). */
fun qrBitmap(text: String, size: Int = 600): Bitmap? = try {
    val m = QRCodeWriter().encode(text, BarcodeFormat.QR_CODE, size, size, mapOf(EncodeHintType.MARGIN to 2))
    val px = IntArray(size * size) { i -> if (m[i % size, i / size]) AColor.BLACK else AColor.WHITE }
    Bitmap.createBitmap(px, size, size, Bitmap.Config.ARGB_8888)
} catch (_: Exception) { null }

/** Topp 3 og glemte kassetter – vises øverst i «Lag kassett». */
@Composable
fun KassettWrappedCard(host: String?) {
    var stats by remember { mutableStateOf<JSONObject?>(null) }
    var lastet by remember { mutableStateOf(false) }
    LaunchedEffect(host) {
        stats = DeviceLink.get("/api/nfc/stats?periode=%C3%A5r&glemt=8", on = host, timeout = 8.0)
            ?.let { runCatching { JSONObject(String(it)) }.getOrNull() }
        lastet = true
    }
    Column(
        Modifier.fillMaxWidth().clip(RoundedCornerShape(16.dp)).background(SourceTok.card).skBorder(SourceTok.line, 16.dp).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        T("KASSETT-WRAPPED", mono(10f, SourceTok.gold, 0.12f))
        val s = stats
        val totalt = s?.optJSONObject("totalt")?.optInt("spilt") ?: 0
        when {
            !lastet -> KassettSpinner()
            totalt == 0 -> T("Ingen kassetter spilt i år ennå.", sora(13f, W.Regular, SourceTok.muted))
            else -> {
                T("$totalt avspillinger i år", sora(20f, W.Semibold))
                val topp = s?.optJSONArray("topp") ?: JSONArray()
                for (i in 0 until minOf(3, topp.length())) {
                    val r = topp.optJSONObject(i) ?: continue
                    KassettRad(r, host, "${i + 1}", "${r.optInt("spilt")}×")
                }
                val glemte = s?.optJSONArray("glemte") ?: JSONArray()
                if (glemte.length() > 0) {
                    T("Glemte kassetter", sora(13f, W.Semibold), Modifier.padding(top = 4.dp))
                    for (i in 0 until minOf(3, glemte.length())) {
                        val r = glemte.optJSONObject(i) ?: continue
                        KassettRad(r, host, "·", if (r.optBoolean("aldri")) "aldri" else "${r.optInt("uker_siden")} uker")
                    }
                }
            }
        }
    }
}

@Composable
private fun KassettRad(r: JSONObject, host: String?, venstre: String, hoyre: String) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        T(venstre, sora(13f, W.Regular, SourceTok.gold), Modifier.width(16.dp))
        AsyncImage(model = DeviceLink.coverURL(r.optString("omslag"), on = host), contentDescription = null,
            modifier = Modifier.size(34.dp).clip(RoundedCornerShape(7.dp)).background(SourceTok.row))
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(1.dp)) {
            T(r.optString("navn"), sora(14f), maxLines = 1)
            T(r.optString("undertittel"), sora(12f, W.Regular, SourceTok.muted), maxLines = 1)
        }
        T(hoyre, sora(12f, W.Regular, SourceTok.muted))
    }
}

/**
 * «Del kassetter» (V4KassettDelSheet): kort kode via Skjold Cloud (kryptert, 14 dager) som QR, lenke og
 * Androids delingsark. Lages med en gang arket åpnes; uten svar fra skyen lages en kode uten sky.
 */
@Composable
fun KassettDelSheet(host: String?, onClose: () -> Unit) {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    var lenke by remember { mutableStateOf("") }
    var info by remember { mutableStateOf("") }
    var feil by remember { mutableStateOf("") }
    var sky by remember { mutableStateOf(true) }
    var runde by remember { mutableStateOf(0) }

    LaunchedEffect(runde) {
        lenke = ""; feil = ""; info = ""
        var viaSky = sky
        var d = DeviceLink.send("/api/nfc/share", mapOf("uids" to emptyList<String>(), "sky" to viaSky), on = host, timeout = 15.0)
        if (d == null && viaSky) {   // Skjold Cloud svarer ikke: lag en kode uten sky
            viaSky = false; sky = false
            d = DeviceLink.send("/api/nfc/share", mapOf("uids" to emptyList<String>(), "sky" to false), on = host, timeout = 15.0)
        }
        val o = d?.let { runCatching { JSONObject(String(it)) }.getOrNull() }
        val l = o?.optString("lenke").orEmpty()
        if (o == null || l.isEmpty()) {
            feil = "Fikk ikke laget delingskode. Har du kassetter som kan deles (album, radiostrømmer, NRK)?"
            return@LaunchedEffect
        }
        lenke = l
        val n = o.optInt("delt"); val hopp = o.optInt("hoppet_over")
        info = "$n kassett${if (n == 1) "" else "er"} delt" + (if (hopp > 0) " · $hopp kunne ikke deles" else "") +
            (if (o.optBoolean("sky")) " · gyldig i 14 dager" else "")
    }

    Dialog(onDismissRequest = onClose, properties = DialogProperties(usePlatformDefaultWidth = false, decorFitsSystemWindows = false)) {
        BackHandler { onClose() }
        Column(
            Modifier.fillMaxSize().background(SourceTok.bg).windowInsetsPadding(WindowInsets.statusBars)
                .verticalScroll(rememberScrollState()).padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                Box(Modifier.size(36.dp, 5.dp).clip(CircleShape).background(SourceTok.ink.copy(alpha = 0.3f)))
            }
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                T("Del kassetter", sora(24f, W.Semibold), Modifier.weight(1f))
                T("Lukk", sora(15f, W.Regular, SourceTok.gold), Modifier.press(onClick = onClose))
            }
            T("Vennen skanner QR-koden med kameraet eller Skjold-appen. Kassettene blir ventende hos dem, klare til å kobles til en NFC-brikke. Albumene slås opp i deres eget Navidrome eller YouTube Music – ingen passord eller private ID-er deles.",
                sora(13f, W.Regular, SourceTok.muted))
            if (lenke.isEmpty() && feil.isEmpty()) KassettSpinner()
            if (feil.isNotEmpty()) T(feil, sora(13f, W.Regular, SourceTok.red))
            if (lenke.isNotEmpty()) {
                val bmp = remember(lenke) { qrBitmap(lenke) }
                if (bmp != null) Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                    Image(bmp.asImageBitmap(), contentDescription = "QR-kode for kassettdeling", filterQuality = FilterQuality.None,
                        modifier = Modifier.widthIn(max = 264.dp).clip(RoundedCornerShape(14.dp)).background(Color.White).padding(12.dp))
                }
                if (info.isNotEmpty()) T(info, sora(12f, W.Regular, SourceTok.muted))
                SelectionContainer { T(lenke, mono(12f, SourceTok.muted)) }
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    Box(
                        Modifier.weight(1f).height(46.dp).clip(CircleShape).background(SourceTok.gold).press {
                            ctx.startActivity(Intent.createChooser(Intent(Intent.ACTION_SEND).setType("text/plain").putExtra(Intent.EXTRA_TEXT, lenke), "Del kassetter"))
                        },
                        contentAlignment = Alignment.Center,
                    ) { T("Del lenke", sora(15f, W.Semibold, SourceTok.bg)) }
                    Box(
                        Modifier.weight(1f).height(46.dp).clip(RoundedCornerShape(23.dp)).background(SourceTok.card).skBorder(SourceTok.line, 23.dp).press {
                            (ctx.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager).setPrimaryClip(ClipData.newPlainText("Skjold-kassett", lenke))
                            info = "Lenken er kopiert"
                        },
                        contentAlignment = Alignment.Center,
                    ) { T("Kopier", sora(15f)) }
                }
                T(if (sky) "Lag kode uten Skjold Cloud" else "Lag kort kode via Skjold Cloud", sora(13f, W.Regular, SourceTok.gold),
                    Modifier.press { sky = !sky; runde++ })
            }
        }
    }
}

/**
 * Mottatt delingslenke (skjold://kassett/del?d=… eller https://skjold-lab.com/kassett/del#…): et ark som
 * V4KassettMottaSheet – bekreft, og legg så kassettene som ventende på Skjold-enheten appen styrer.
 */
class KassettDelActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        Store.init(applicationContext)
        val kode = kode(intent?.data)
        if (kode.isNullOrBlank()) { finish(); return }
        val host = Shortcuts.host(applicationContext, null)
        setContent { KassettMottaSheet(kode, host) { finish() } }
    }

    companion object {
        fun kode(u: Uri?): String? {
            if (u == null) return null
            if (u.scheme == "skjold" && u.host == "kassett") return u.getQueryParameter("d")
            if ((u.path ?: "").startsWith("/kassett/del")) return u.fragment
            return null
        }
    }
}

/** «Du har fått kassetter»: halvhøyt ark nederst (presentationDetents .medium på iOS). */
@Composable
private fun KassettMottaSheet(kode: String, host: String?, close: () -> Unit) {
    val scope = rememberCoroutineScope()
    var status by remember { mutableStateOf("") }
    var ferdig by remember { mutableStateOf(false) }
    var busy by remember { mutableStateOf(false) }
    BackHandler { close() }
    Box(Modifier.fillMaxSize().background(Color.Black.copy(alpha = 0.45f)).pointerInput(Unit) { detectTapGestures { close() } }, contentAlignment = Alignment.BottomCenter) {
        Column(
            Modifier.fillMaxWidth().clip(RoundedCornerShape(topStart = 28.dp, topEnd = 28.dp)).background(SourceTok.bg)
                .pointerInput(Unit) { detectTapGestures { } }
                .windowInsetsPadding(WindowInsets.navigationBars).padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            T("Du har fått kassetter", sora(24f, W.Semibold))
            T("De legges som ventende kassetter på ${host ?: "Skjold"}. Sett inn en ny NFC-brikke i kassettspilleren for å koble den første.",
                sora(13f, W.Regular, SourceTok.muted))
            if (status.isNotEmpty()) T(status, sora(14f, W.Regular, if (ferdig) SourceTok.gold else SourceTok.red))
            if (busy) KassettSpinner()
            KassettPrimary(if (ferdig) "Ferdig" else "Legg til", SourceTok.gold) {
                if (ferdig) { close(); return@KassettPrimary }
                if (busy) return@KassettPrimary
                busy = true
                scope.launch {
                    val svar = withContext(Dispatchers.IO) { Shortcuts.http(host, "POST", "/api/nfc/share/import", JSONObject().put("kode", kode)) }
                    val o = svar?.let { runCatching { JSONObject(it) }.getOrNull() }
                    busy = false
                    if (o == null) {
                        status = "Fikk ikke lagt til kassettene. Sjekk at du er koblet til Skjold, og at lenken ikke er utløpt."
                        return@launch
                    }
                    val n = o.optInt("lagt_til"); val fra = o.optString("fra")
                    status = if (n > 0) "$n kassett${if (n == 1) "" else "er"}${if (fra.isNotEmpty()) " fra $fra" else ""} venter på en NFC-brikke"
                    else "Du har disse kassettene fra før"
                    ferdig = true
                }
            }
            if (!ferdig) T("Avbryt", sora(14f, W.Regular, SourceTok.muted), Modifier.fillMaxWidth().press { close() },
                align = androidx.compose.ui.text.style.TextAlign.Center)
        }
    }
}
