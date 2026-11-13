package no.kristo.skjold

import android.app.Activity
import android.app.AlertDialog
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Color as AColor
import android.net.Uri
import android.os.Bundle
import android.widget.Toast
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.google.zxing.BarcodeFormat
import com.google.zxing.EncodeHintType
import com.google.zxing.qrcode.QRCodeWriter
import kotlinx.coroutines.launch
import org.json.JSONArray
import org.json.JSONObject
import kotlin.concurrent.thread

/** Kassett-Wrapped (GET /api/nfc/stats) og deling av kassetter (POST /api/nfc/share, /api/nfc/share/import). */

/** QR-kode som Bitmap (ZXing). */
fun qrBitmap(text: String, size: Int = 600): Bitmap? = try {
    val m = QRCodeWriter().encode(text, BarcodeFormat.QR_CODE, size, size, mapOf(EncodeHintType.MARGIN to 2))
    val px = IntArray(size * size) { i -> if (m[i % size, i / size]) AColor.BLACK else AColor.WHITE }
    Bitmap.createBitmap(px, size, size, Bitmap.Config.ARGB_8888)
} catch (_: Exception) { null }

/** Topp 3 og glemte kassetter – øverst i «Lag kassett». */
@Composable
fun KassettWrappedCard(host: String?) {
    var stats by remember { mutableStateOf<JSONObject?>(null) }
    var lastet by remember { mutableStateOf(false) }
    LaunchedEffect(host) {
        stats = DeviceLink.get("/api/nfc/stats?periode=%C3%A5r&glemt=8", on = host, timeout = 8.0)
            ?.let { runCatching { JSONObject(String(it)) }.getOrNull() }
        lastet = true
    }
    SKCard(radius = 16.dp) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            SKMonoLabel("KASSETT-WRAPPED", color = C.accent2)
            val s = stats
            val totalt = s?.optJSONObject("totalt")?.optInt("spilt") ?: 0
            when {
                !lastet -> T("Henter …", sora(13f, W.Regular, C.muted))
                totalt == 0 -> T("Ingen kassetter spilt i år ennå.", sora(13f, W.Regular, C.muted))
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
}

@Composable
private fun KassettRad(r: JSONObject, host: String?, venstre: String, hoyre: String) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        T(venstre, sora(13f, W.Regular, C.accent2), Modifier.width(16.dp))
        AsyncImage(model = DeviceLink.coverURL(r.optString("omslag"), on = host), contentDescription = null,
            modifier = Modifier.size(34.dp).clip(RoundedCornerShape(7.dp)).background(C.card2))
        Column(Modifier.weight(1f)) {
            T(r.optString("navn"), sora(14f), maxLines = 1)
            T(r.optString("undertittel"), sora(12f, W.Regular, C.muted), maxLines = 1)
        }
        T(hoyre, sora(12f, W.Regular, C.muted))
    }
}

/** Del alle kassettene: kort kode via Skjold Cloud (kryptert, 14 dager) som QR, lenke og Androids delingsark. */
@Composable
fun KassettDelPanel(host: String?) {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    var lenke by remember { mutableStateOf("") }
    var info by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    fun lag(sky: Boolean) {
        busy = true; lenke = ""; info = ""
        scope.launch {
            var d = DeviceLink.send("/api/nfc/share", mapOf("uids" to emptyList<String>(), "sky" to sky), on = host, timeout = 15.0)
            var viaSky = sky
            if (d == null && sky) { viaSky = false; d = DeviceLink.send("/api/nfc/share", mapOf("uids" to emptyList<String>(), "sky" to false), on = host, timeout = 15.0) }
            val o = d?.let { runCatching { JSONObject(String(it)) }.getOrNull() }
            busy = false
            if (o == null || o.optString("lenke").isEmpty()) { info = "Fikk ikke laget delingskode. Har du kassetter som kan deles (album, radiostrømmer, NRK)?"; return@launch }
            lenke = o.optString("lenke")
            val n = o.optInt("delt"); val hopp = o.optInt("hoppet_over")
            info = "$n kassett${if (n == 1) "" else "er"} delt" + (if (hopp > 0) " · $hopp kunne ikke deles" else "") + (if (viaSky) " · gyldig i 14 dager" else "")
        }
    }
    SKCard(radius = 16.dp) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            T("Del kassettene med en venn", sora(15f, W.Semibold))
            T("Vennen skanner QR-koden eller åpner lenken. Kassettene blir ventende hos dem – albumene slås opp i deres eget Navidrome eller YouTube Music. Ingen passord eller private ID-er deles.",
                sora(12f, W.Regular, C.muted))
            if (lenke.isEmpty()) SKPill(if (busy) "Lager kode …" else "Lag delingskode", primary = true, height = 42.dp) { if (!busy) lag(true) }
            else {
                val bmp = remember(lenke) { qrBitmap(lenke) }
                if (bmp != null) Image(bmp.asImageBitmap(), contentDescription = "QR-kode for kassettdeling", filterQuality = FilterQuality.None,
                    modifier = Modifier.size(220.dp).clip(RoundedCornerShape(12.dp)).background(Color.White).padding(8.dp).align(Alignment.CenterHorizontally))
                T(lenke, mono(11f, C.muted))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    SKPill("Del lenke", primary = true, height = 42.dp) {
                        ctx.startActivity(Intent.createChooser(Intent(Intent.ACTION_SEND).setType("text/plain").putExtra(Intent.EXTRA_TEXT, lenke), "Del kassetter"))
                    }
                    SKPill("Kopier", height = 42.dp) {
                        (ctx.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager).setPrimaryClip(ClipData.newPlainText("Skjold-kassett", lenke))
                        info = "Lenken er kopiert"
                    }
                }
            }
            if (info.isNotEmpty()) T(info, sora(12f, W.Regular, C.muted))
        }
    }
}

/**
 * Mottatt delingslenke (skjold://kassett/del?d=… eller https://skjold-lab.com/kassett/del#…):
 * spør først, og legg så kassettene som ventende på Skjold-enheten appen styrer.
 */
class KassettDelActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        Store.init(applicationContext)
        val kode = kode(intent?.data)
        if (kode.isNullOrBlank()) { finish(); return }
        AlertDialog.Builder(this)
            .setTitle("Du har fått kassetter")
            .setMessage("Legge dem til som ventende kassetter på Skjold? Sett inn en ny NFC-brikke i kassettspilleren for å koble den første.")
            .setPositiveButton("Legg til") { _, _ ->
                val app = applicationContext
                thread {
                    val svar = Shortcuts.http(Shortcuts.host(app, null), "POST", "/api/nfc/share/import", JSONObject().put("kode", kode))
                    val o = svar?.let { runCatching { JSONObject(it) }.getOrNull() }
                    val n = o?.optInt("lagt_til") ?: -1
                    val fra = o?.optString("fra").orEmpty()
                    val msg = when {
                        o == null -> "Fikk ikke lagt til kassettene. Sjekk at du er koblet til Skjold, og at lenken ikke er utløpt."
                        n > 0 -> "$n kassett${if (n == 1) "" else "er"}${if (fra.isNotEmpty()) " fra $fra" else ""} venter på en NFC-brikke"
                        else -> "Du har disse kassettene fra før"
                    }
                    runOnUiThread { Toast.makeText(app, msg, Toast.LENGTH_LONG).show(); finish() }
                }
            }
            .setNegativeButton("Avbryt") { _, _ -> finish() }
            .setOnCancelListener { finish() }
            .show()
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
