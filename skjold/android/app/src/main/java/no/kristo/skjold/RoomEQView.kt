package no.kristo.skjold

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioRecord
import android.media.MediaRecorder
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBars
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.UUID
import kotlin.math.ln

/*
 * Romkorreksjon med telefonens mikrofon: Skjold spiller en sweep (POST /api/roomeq/sweep), telefonen tar opp 48 kHz mono
 * 16-bit med AudioSource.UNPROCESSED når enheten støtter det (ellers VOICE_RECOGNITION, som også er uten AGC på de fleste
 * telefoner), opptaket analyseres på Skjold (POST /api/roomeq/analyze) og flere punkter snittes. Bare kutt 40–300 Hz.
 */

data class EqPt(val f: Double, val db: Double)
data class EqCut(val f: Double, val q: Double, val g: Double)

internal object RoomEQRec {
    const val SR = 48000

    fun source(ctx: Context): Int {
        val am = ctx.getSystemService(Context.AUDIO_SERVICE) as? AudioManager
        val ok = am?.getProperty(AudioManager.PROPERTY_SUPPORT_AUDIO_SOURCE_UNPROCESSED) == "true"
        return if (ok) MediaRecorder.AudioSource.UNPROCESSED else MediaRecorder.AudioSource.VOICE_RECOGNITION
    }

    /** Tar opp i [secs] sekunder og returnerer 16-bit mono WAV. Kjøres på IO-tråd. */
    @SuppressLint("MissingPermission")
    fun record(ctx: Context, secs: Double): ByteArray {
        val minBuf = AudioRecord.getMinBufferSize(SR, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
        val bufSize = maxOf(minBuf, SR / 5 * 2)
        val rec = AudioRecord(source(ctx), SR, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, bufSize * 2)
        if (rec.state != AudioRecord.STATE_INITIALIZED) {
            rec.release()
            throw IllegalStateException("Fikk ikke startet mikrofonen")
        }
        val out = ByteArrayOutputStream()
        val buf = ByteArray(bufSize)
        val total = (secs * SR * 2).toInt()
        try {
            rec.startRecording()
            while (out.size() < total) {
                val n = rec.read(buf, 0, buf.size)
                if (n < 0) break
                if (n > 0) out.write(buf, 0, n)
            }
        } finally {
            try { rec.stop() } catch (_: Exception) {}
            rec.release()
        }
        return wav(out.toByteArray(), SR)
    }

    fun wav(pcm: ByteArray, sr: Int): ByteArray {
        val h = ByteBuffer.allocate(44).order(ByteOrder.LITTLE_ENDIAN)
        h.put("RIFF".toByteArray()); h.putInt(36 + pcm.size); h.put("WAVE".toByteArray())
        h.put("fmt ".toByteArray()); h.putInt(16); h.putShort(1); h.putShort(1); h.putInt(sr); h.putInt(sr * 2)
        h.putShort(2); h.putShort(16)
        h.put("data".toByteArray()); h.putInt(pcm.size)
        return h.array() + pcm
    }
}

private val TIPS = listOf(
    "Sitt der du pleier å lytte, og hold telefonen i ørehøyde med mikrofonen opp.",
    "Flytt telefonen 50 cm til venstre.",
    "Flytt telefonen 50 cm til høyre.",
    "Flytt telefonen 30 cm fram.",
    "Flytt telefonen 30 cm bak.",
)

private fun parseCurve(a: JSONArray?): List<EqPt> {
    if (a == null) return emptyList()
    val out = ArrayList<EqPt>()
    for (i in 0 until a.length()) {
        val o = a.optJSONObject(i) ?: continue
        out.add(EqPt(o.optDouble("f"), o.optDouble("db")))
    }
    return out
}

private fun parseCuts(a: JSONArray?): List<EqCut> {
    if (a == null) return emptyList()
    val out = ArrayList<EqCut>()
    for (i in 0 until a.length()) {
        val o = a.optJSONObject(i) ?: continue
        out.add(EqCut(o.optDouble("f"), o.optDouble("q", 1.0), o.optDouble("g")))
    }
    return out
}

@Composable
fun RoomEQView(m: AppModel) {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    val session = remember { UUID.randomUUID().toString() }
    var phase by remember { mutableStateOf("intro") }   // intro | measuring | result | error
    var points by remember { mutableIntStateOf(0) }
    var status by remember { mutableStateOf("") }
    var before by remember { mutableStateOf(emptyList<EqPt>()) }
    var after by remember { mutableStateOf(emptyList<EqPt>()) }
    var cuts by remember { mutableStateOf(emptyList<EqCut>()) }
    var saved by remember { mutableStateOf(false) }

    fun measure() {
        val host = m.settingsHost
        if (host == null) { status = "Ingen Skjold valgt."; phase = "error"; return }
        phase = "measuring"; status = "Tar opp … vær stille"
        scope.launch {
            try {
                DeviceLink.send("/api/roomeq/sweep", mapOf("level" to 0.5, "delay" to 1.0), on = host)
                val wav = withContext(Dispatchers.IO) { RoomEQRec.record(ctx, 8.5) }
                status = "Regner ut …"
                val reset = if (points == 0) "1" else "0"
                val url = Net.url(host, "/api/roomeq/analyze?session=$session&reset=$reset")
                val res = if (url != null) Net.data(url, "POST", wav, 60.0, mapOf("Content-Type" to "audio/wav")) else null
                if (res == null) { status = "Fikk ikke kontakt med Skjold."; phase = "error"; return@launch }
                val o = try { JSONObject(String(res.first)) } catch (_: Exception) { JSONObject() }
                if (res.second >= 300) { status = o.optString("error", "Analysen feilet (${res.second})."); phase = "error"; return@launch }
                before = parseCurve(o.optJSONArray("curve"))
                after = parseCurve(o.optJSONArray("after"))
                cuts = parseCuts(o.optJSONArray("filters"))
                points = o.optInt("points", points + 1)
                saved = false
                status = if (o.optBoolean("clipped")) "Opptaket ble overstyrt – skru ned volumet litt og mål på nytt." else ""
                phase = "result"
            } catch (e: Exception) {
                status = e.message ?: "Målingen feilet."
                phase = "error"
            }
        }
    }

    // Høyttalerplassering: hver høyttaler spiller en kort sweep etter tur (POST /api/placement/start), telefonen tar opp,
    // Skjold finner ankomsttid og nivå (/api/placement/analyze) og justerer forsinkelse/nivå (/api/placement/apply).
    var placeStatus by remember { mutableStateOf("") }
    var placeBusy by remember { mutableStateOf(false) }
    fun measurePlacement() {
        val host = m.settingsHost ?: run { placeStatus = "Ingen Skjold valgt."; return }
        if (ContextCompat.checkSelfPermission(ctx, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            placeStatus = "Gi Skjold mikrofontilgang først (trykk «Start måling» én gang)."; return
        }
        placeBusy = true; placeStatus = "Hold telefonen der du sitter …"
        scope.launch {
            try {
                val pl = DeviceLink.get("/api/placement", on = host)?.let { JSONObject(String(it)) }
                val n = pl?.optJSONArray("speakers_eff")?.length() ?: 2
                val secs = 2.0 + 0.5 + n * 1.6 + 2.0
                var tRec = 0.0
                val rec = async(Dispatchers.IO) { tRec = System.currentTimeMillis() / 1000.0; RoomEQRec.record(ctx, secs) }
                delay(300)
                val t1 = System.currentTimeMillis() / 1000.0
                val st = DeviceLink.send("/api/placement/start", on = host)?.let { JSONObject(String(it)) }
                val t2 = System.currentTimeMillis() / 1000.0
                if (st == null) { rec.cancel(); placeStatus = "Fikk ikke kontakt med Skjold."; return@launch }
                val skip = maxOf(0.0, st.optDouble("start_at") - (st.optDouble("now") - (t1 + t2) / 2) - tRec)
                val wav = rec.await()
                placeStatus = "Regner ut …"
                val url = Net.url(host, "/api/placement/analyze?n=$n&skip=${"%.3f".format(java.util.Locale.US, skip)}")
                val res = if (url != null) Net.data(url, "POST", wav, 60.0, mapOf("Content-Type" to "audio/wav")) else null
                val o = res?.let { try { JSONObject(String(it.first)) } catch (_: Exception) { null } }
                if (res == null || o == null || res.second >= 300) { placeStatus = o?.optString("error")?.takeIf { it.isNotEmpty() } ?: "Analysen feilet."; return@launch }
                val al = o.optJSONArray("align") ?: JSONArray()
                val parts = (0 until al.length()).map { i -> val a = al.getJSONObject(i); "#${i + 1} +${"%.2f".format(a.optDouble("delay_ms"))} ms ${"%.1f".format(a.optDouble("gain_db"))} dB" }
                DeviceLink.send("/api/placement/apply", on = host)
                placeStatus = (if (o.has("warning")) o.optString("warning") + ". " else "") + "Justert: " + parts.joinToString(" · ")
                Haptics.success()
            } catch (e: Exception) {
                placeStatus = e.message ?: "Målingen feilet."
            } finally { placeBusy = false }
        }
    }

    val perm = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { ok ->
        if (ok) measure() else { status = "Skjold trenger mikrofontilgang for å måle rommet."; phase = "error" }
    }
    fun start() {
        val granted = ContextCompat.checkSelfPermission(ctx, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED
        if (granted) measure() else perm.launch(Manifest.permission.RECORD_AUDIO)
    }

    Column(
        Modifier.fillMaxSize().background(C.bg).windowInsetsPadding(WindowInsets.statusBars).verticalScroll(rememberScrollState())
            .padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            T("Romkorreksjon", sora(24f, W.Semibold), Modifier.weight(1f))
            SKLinkButton("Lukk") { m.showRoomEQ = false }
        }
        SKCard(radius = 18.dp) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                when (phase) {
                    "intro" -> {
                        T("Rommet former bassen mer enn høyttalerne gjør. Skjold spiller en glidetone, telefonen lytter, og Skjold demper topper der rommet buldrer.", sora(14f))
                        Step(1, "Gjør rommet stille, og skru volumet på Skjold til vanlig lyttenivå.")
                        Step(2, "Sitt der du lytter, med telefonen i ørehøyde.")
                        Step(3, "Mål 3–5 punkter rundt lytteplassen. Snittet blir mest riktig.")
                        SKPill("Start måling", primary = true, height = 46.dp) { start() }
                        SKPill(if (placeBusy) "Måler plassering …" else "Mål høyttalerplassering", height = 42.dp) { if (!placeBusy) measurePlacement() }
                        if (placeStatus.isNotEmpty()) T(placeStatus, sora(13f, W.Regular, C.muted))
                    }
                    "measuring" -> {
                        SKMonoLabel("PUNKT ${points + 1}")
                        T(TIPS[minOf(points, TIPS.size - 1)], sora(15f))
                        T(status, sora(13f, W.Regular, C.muted))
                    }
                    "result" -> {
                        SKMonoLabel("$points PUNKT" + if (points == 1) "" else "ER")
                        EqChart(before, after, Modifier.fillMaxWidth().height(190.dp))
                        Row(horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                            Legend(C.muted, "Før"); Legend(C.accent2, "Etter")
                        }
                        val summary = if (cuts.isEmpty()) "Rommet er jevnt i bassen – ingen kutt trengs."
                            else "${cuts.size} kutt: " + cuts.joinToString(" · ") { "${it.f.toInt()} Hz ${"%.1f".format(it.g)} dB" }
                        T(summary, sora(13f, W.Regular, C.muted))
                        if (status.isNotEmpty()) T(status, sora(13f, W.Regular, if (saved) C.ok else C.accent2))
                        if (points < 5) {
                            T("Neste: " + TIPS[minOf(points, TIPS.size - 1)], sora(13f))
                            SKPill("Mål et punkt til", height = 42.dp) { start() }
                        }
                        if (cuts.isNotEmpty() && !saved) {
                            SKPill("Lagre korreksjon", primary = true, height = 46.dp) {
                                val host = m.settingsHost
                                scope.launch {
                                    val body = mapOf("enabled" to true, "filters" to cuts.map { mapOf("f" to it.f, "q" to it.q, "g" to it.g) })
                                    val r = if (host != null) DeviceLink.send("/api/plugins/roomeq", body, on = host) else null
                                    saved = r != null
                                    status = if (saved) "Lagret. Romkorreksjonen er på." else "Fikk ikke lagret – prøv igjen."
                                    if (saved) Haptics.success()
                                }
                            }
                        }
                        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                            SKPill("Start på nytt", height = 40.dp) {
                                points = 0; before = emptyList(); after = emptyList(); cuts = emptyList(); saved = false; status = ""; phase = "intro"
                            }
                            SKPill("Slå av", height = 40.dp) {
                                val host = m.settingsHost
                                scope.launch {
                                    val r = if (host != null) DeviceLink.send("/api/plugins/roomeq", mapOf("enabled" to false), on = host) else null
                                    status = if (r != null) "Romkorreksjon er slått av." else "Fikk ikke kontakt med Skjold."
                                }
                            }
                        }
                    }
                    else -> {
                        T(status, sora(14f))
                        SKPill("Prøv igjen", primary = true, height = 44.dp) { phase = if (points > 0) "result" else "intro" }
                    }
                }
            }
        }
        T("Telefonmikrofoner er unøyaktige under 40 Hz og over ca. 10 kHz. Derfor retter Skjold bare 40–300 Hz, og bare med kutt – aldri mer enn 10 dB.",
            sora(12f, W.Regular, C.muted))
    }
}

@Composable
private fun Step(n: Int, text: String) {
    Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.Top) {
        Box(Modifier.size(22.dp).clip(CircleShape).background(C.selBg), contentAlignment = Alignment.Center) {
            T("$n", mono(11f, C.accent2))
        }
        T(text, sora(13f), Modifier.weight(1f))
    }
}

@Composable
private fun Legend(color: Color, text: String) {
    Row(horizontalArrangement = Arrangement.spacedBy(5.dp), verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.width(12.dp).height(3.dp).background(color))
        T(text, mono(10f, C.muted))
    }
}

/** Kurve 20–1000 Hz (log), ±15 dB, med 40–300 Hz markert. */
@Composable
private fun EqChart(before: List<EqPt>, after: List<EqPt>, modifier: Modifier) {
    Canvas(modifier) {
        val w = size.width
        val h = size.height
        fun x(f: Double): Float = (ln(f / 20.0) / ln(1000.0 / 20.0)).toFloat() * w
        fun y(db: Double): Float = h / 2f - (db.coerceIn(-15.0, 15.0) / 15.0).toFloat() * (h / 2f)
        drawRect(C.accent2.copy(alpha = 0.07f), topLeft = Offset(x(40.0), 0f), size = Size(x(300.0) - x(40.0), h))
        for (db in listOf(-10.0, 0.0, 10.0)) drawLine(C.line2, Offset(0f, y(db)), Offset(w, y(db)), strokeWidth = 1f)
        for (f in listOf(50.0, 100.0, 200.0, 500.0)) drawLine(C.line2, Offset(x(f), 0f), Offset(x(f), h), strokeWidth = 1f)
        fun curve(pts: List<EqPt>): Path {
            val p = Path()
            pts.forEachIndexed { i, pt -> if (i == 0) p.moveTo(x(pt.f), y(pt.db)) else p.lineTo(x(pt.f), y(pt.db)) }
            return p
        }
        drawPath(curve(before), C.muted, style = Stroke(width = 3f))
        drawPath(curve(after), C.accent2, style = Stroke(width = 4f))
    }
}
