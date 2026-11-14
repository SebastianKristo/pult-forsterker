package no.kristo.skjold

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioRecord
import android.media.MediaRecorder
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Canvas
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
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBars
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
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
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.Locale
import java.util.UUID
import kotlin.math.ln
import kotlin.math.roundToInt

/*
 * Romkorreksjon med telefonens mikrofon (V4RoomEQ.swift på iOS): Skjold spiller en sweep (POST /api/roomeq/sweep),
 * telefonen tar opp 48 kHz mono 16-bit med AudioSource.UNPROCESSED når enheten støtter det (ellers VOICE_RECOGNITION,
 * som også er uten AGC på de fleste telefoner), opptaket analyseres på Skjold (POST /api/roomeq/analyze) og flere
 * punkter snittes. Forslaget (bare kutt 40–300 Hz) lagres med POST /api/plugins/roomeq.
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

    private fun bufSize() = maxOf(AudioRecord.getMinBufferSize(SR, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT), SR / 5 * 2)

    @SuppressLint("MissingPermission")
    private fun open(ctx: Context, size: Int): AudioRecord {
        val rec = AudioRecord(source(ctx), SR, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, size * 2)
        if (rec.state != AudioRecord.STATE_INITIALIZED) {
            rec.release()
            throw IllegalStateException("Fikk ikke startet mikrofonen")
        }
        return rec
    }

    /** Tar opp i [secs] sekunder og returnerer 16-bit mono WAV. Kjøres på IO-tråd. */
    fun record(ctx: Context, secs: Double): ByteArray {
        val size = bufSize()
        val rec = open(ctx, size)
        val out = ByteArrayOutputStream()
        val buf = ByteArray(size)
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

    /** Opptak som startes og stoppes (RoomEQRecorder.start/stop på iOS). Lesingen går på en egen tråd. */
    class Session(private val ctx: Context) {
        @Volatile private var running = false
        private var thread: Thread? = null
        private var rec: AudioRecord? = null
        private val out = ByteArrayOutputStream()

        fun start() {
            val size = bufSize()
            val r = open(ctx, size)
            rec = r
            running = true
            r.startRecording()
            thread = Thread {
                val buf = ByteArray(size)
                while (running) {
                    val n = r.read(buf, 0, buf.size)
                    if (n < 0) break
                    if (n > 0) synchronized(out) { out.write(buf, 0, n) }
                }
            }.also { it.start() }
        }

        /** Stopper og returnerer opptaket som 16-bit mono WAV. Kjøres på IO-tråd. */
        fun stop(): ByteArray {
            running = false
            thread?.join(1500)
            thread = null
            rec?.let { try { it.stop() } catch (_: Exception) {}; it.release() }
            rec = null
            val pcm = synchronized(out) { out.toByteArray().also { out.reset() } }
            return wav(pcm, SR)
        }
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

/** Kurvepunkter 20–1000 Hz (RoomEQModel.curve). */
private fun parseCurve(a: JSONArray?): List<EqPt> {
    if (a == null) return emptyList()
    val out = ArrayList<EqPt>()
    for (i in 0 until a.length()) {
        val o = a.optJSONObject(i) ?: continue
        val f = o.optDouble("f", 0.0)
        val db = o.optDouble("db", 0.0)
        if (f >= 20 && f <= 1000) out.add(EqPt(f, db))
    }
    return out
}

private fun parseCuts(a: JSONArray?): List<EqCut> {
    if (a == null) return emptyList()
    val out = ArrayList<EqCut>()
    for (i in 0 until a.length()) {
        val o = a.optJSONObject(i) ?: continue
        out.add(EqCut(o.optDouble("f", 0.0), o.optDouble("q", 1.0), o.optDouble("g", 0.0)))
    }
    return out
}

private fun jsonObj(b: ByteArray?): JSONObject = try { JSONObject(String(b ?: ByteArray(0))) } catch (_: Exception) { JSONObject() }

/** Skjermen «Romkorreksjon», åpnet fra Lyd-fanen og fra Innstillinger → Lyd (V4RoomEQSheet). */
@Composable
fun RoomEQView(m: AppModel) {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    val session = remember { UUID.randomUUID().toString() }
    val recorder = remember { RoomEQRec.Session(ctx.applicationContext) }
    var phase by remember { mutableStateOf("intro") }   // intro | measuring | result | error
    var errMsg by remember { mutableStateOf("") }
    var points by remember { mutableIntStateOf(0) }
    var status by remember { mutableStateOf("") }
    var before by remember { mutableStateOf(emptyList<EqPt>()) }
    var after by remember { mutableStateOf(emptyList<EqPt>()) }
    var cuts by remember { mutableStateOf(emptyList<EqCut>()) }
    var saved by remember { mutableStateOf(false) }
    var placeStatus by remember { mutableStateOf("") }
    var placeBusy by remember { mutableStateOf(false) }
    val tip = TIPS[minOf(points, TIPS.size - 1)]
    val close = { m.showRoomEQ = false }
    BackHandler { close() }
    // Mikrofonen skal ikke stå på hvis skjermen lukkes midt i et opptak
    DisposableEffect(recorder) { onDispose { Thread { recorder.stop() }.start() } }

    fun fail(msg: String) { errMsg = msg; phase = "error" }

    fun measure() {
        val host = m.settingsHost ?: run { fail("Ingen Skjold valgt."); return }
        phase = "measuring"; status = "Tar opp … vær stille"
        scope.launch {
            try {
                withContext(Dispatchers.IO) { recorder.start() }
            } catch (e: Exception) { fail("Fikk ikke startet mikrofonen: ${e.message ?: ""}"); return@launch }
            DeviceLink.send("/api/roomeq/sweep", mapOf("level" to 0.5, "delay" to 1.0), on = host)
            delay(8500)
            val wav = withContext(Dispatchers.IO) { recorder.stop() }
            status = "Regner ut …"
            val reset = if (points == 0) "1" else "0"
            val url = Net.url(host, "/api/roomeq/analyze?session=$session&reset=$reset") ?: run { fail("Ugyldig adresse."); return@launch }
            val res = Net.data(url, "POST", wav, 60.0, mapOf("Content-Type" to "audio/wav")) ?: run { fail("Fikk ikke kontakt med Skjold."); return@launch }
            val o = jsonObj(res.first)
            if (res.second >= 300) { fail(o.optString("error").ifEmpty { "Analysen feilet (${res.second})." }); return@launch }
            before = parseCurve(o.optJSONArray("curve"))
            after = parseCurve(o.optJSONArray("after"))
            cuts = parseCuts(o.optJSONArray("filters"))
            points = if (o.has("points")) o.optInt("points", points + 1) else points + 1
            saved = false
            status = if (o.optBoolean("clipped")) "Opptaket ble overstyrt – skru ned volumet litt og mål på nytt." else ""
            phase = "result"
        }
    }

    // Høyttalerplassering (POST /api/placement/start → opptak → /api/placement/analyze → /api/placement/apply):
    // hver høyttaler spiller en kort sweep etter tur, Skjold regner ut forsinkelse og nivå så alt treffer lytteplassen likt.
    fun measurePlacement() {
        val host = m.settingsHost ?: run { placeStatus = "Ingen Skjold valgt."; return }
        placeBusy = true
        placeStatus = "Hold telefonen der du sitter …"
        scope.launch {
            try {
                try {
                    withContext(Dispatchers.IO) { recorder.start() }
                } catch (_: Exception) { placeStatus = "Fikk ikke startet mikrofonen."; return@launch }
                val tRec = System.currentTimeMillis() / 1000.0
                val t1 = System.currentTimeMillis() / 1000.0
                val d = DeviceLink.send("/api/placement/start", emptyMap(), on = host)
                val o = d?.let { try { JSONObject(String(it)) } catch (_: Exception) { null } }
                if (o == null || !o.has("start_at") || !o.has("now")) {
                    withContext(Dispatchers.IO) { recorder.stop() }
                    placeStatus = "Fikk ikke kontakt med Skjold."; return@launch
                }
                val startAt = o.optDouble("start_at")
                val now = o.optDouble("now")
                val t2 = System.currentTimeMillis() / 1000.0
                val n = o.optInt("n", 2)
                val recS = o.optDouble("record_s", 6.0)
                val skip = maxOf(0.0, startAt - (now - (t1 + t2) / 2) - tRec)
                delay(((maxOf(0.0, startAt - now) + recS) * 1000).toLong())
                val wav = withContext(Dispatchers.IO) { recorder.stop() }
                placeStatus = "Regner ut …"
                val url = Net.url(host, "/api/placement/analyze?n=$n&skip=${String.format(Locale.US, "%.3f", skip)}")
                val res = if (url != null) Net.data(url, "POST", wav, 60.0, mapOf("Content-Type" to "audio/wav")) else null
                if (res == null) { placeStatus = "Analysen feilet."; return@launch }
                val r = jsonObj(res.first)
                if (res.second >= 300) { placeStatus = r.optString("error").ifEmpty { "Analysen feilet (${res.second})." }; return@launch }
                val al = r.optJSONArray("align") ?: JSONArray()
                val parts = (0 until al.length()).map { i ->
                    val a = al.optJSONObject(i) ?: JSONObject()
                    String.format(Locale.US, "#%d +%.2f ms %.1f dB", i + 1, a.optDouble("delay_ms", 0.0), a.optDouble("gain_db", 0.0))
                }
                DeviceLink.send("/api/placement/apply", emptyMap(), on = host)
                val warn = r.optString("warning").takeIf { r.has("warning") && it.isNotEmpty() }
                placeStatus = (warn?.let { "$it. " } ?: "") + "Justert: " + parts.joinToString(" · ")
                Haptics.success()
            } finally { placeBusy = false }
        }
    }

    fun save() {
        val host = m.settingsHost ?: return
        scope.launch {
            val body = mapOf("enabled" to true, "filters" to cuts.map { mapOf("f" to it.f, "q" to it.q, "g" to it.g) })
            val r = DeviceLink.send("/api/plugins/roomeq", body, on = host)
            saved = r != null
            status = if (saved) "Lagret. Romkorreksjonen er på." else "Fikk ikke lagret – prøv igjen."
            if (saved) Haptics.success()
        }
    }

    fun turnOff() {
        val host = m.settingsHost ?: return
        scope.launch {
            val r = DeviceLink.send("/api/plugins/roomeq", mapOf("enabled" to false), on = host)
            status = if (r != null) "Romkorreksjon er slått av." else "Fikk ikke kontakt med Skjold."
        }
    }

    // Mikrofontilgang spørres før måling (AVAudioApplication.requestRecordPermission på iOS)
    var pending by remember { mutableStateOf("") }   // "measure" | "placement"
    val perm = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { ok ->
        val what = pending
        pending = ""
        if (what == "placement") {
            if (ok) measurePlacement() else placeStatus = "Skjold trenger mikrofontilgang."
        } else {
            if (ok) measure() else fail("Skjold trenger mikrofontilgang. Slå det på i Innstillinger → Apper → Skjold → Tillatelser → Mikrofon.")
        }
    }
    fun withMic(what: String, run: () -> Unit) {
        if (ContextCompat.checkSelfPermission(ctx, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) run()
        else { pending = what; perm.launch(Manifest.permission.RECORD_AUDIO) }
    }

    Column(
        Modifier.fillMaxSize().background(C.bg).windowInsetsPadding(WindowInsets.statusBars).windowInsetsPadding(WindowInsets.navigationBars)
            .verticalScroll(rememberScrollState()).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(18.dp),
    ) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            T("Romkorreksjon", sora(24f, W.Semibold), Modifier.weight(1f))
            T("Lukk", sora(15f, W.Regular, C.accent2), Modifier.press { close() })
        }
        when (phase) {
            "intro" -> Card(14) {
                T("Rommet former bassen mer enn høyttalerne gjør. Skjold spiller en glidetone, telefonen lytter, og Skjold demper topper der rommet buldrer.",
                    sora(14f, W.Regular, C.ink))
                StepRow(1, "Gjør rommet stille, og skru volumet på Skjold til vanlig lyttenivå.")
                StepRow(2, "Sitt der du lytter, med telefonen i ørehøyde.")
                StepRow(3, "Mål 3–5 punkter rundt lytteplassen. Snittet blir mest riktig.")
                Primary("Start måling") { withMic("measure") { measure() } }
                Secondary(if (placeBusy) "Måler plassering …" else "Mål høyttalerplassering", enabled = !placeBusy) { withMic("placement") { measurePlacement() } }
                if (placeStatus.isNotEmpty()) T(placeStatus, sora(13f, W.Regular, C.muted))
            }
            "measuring" -> Card(12) {
                SKMonoLabel("PUNKT ${points + 1}")
                T(tip, sora(15f, W.Regular, C.ink))
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    androidx.compose.material3.CircularProgressIndicator(Modifier.size(20.dp), color = C.accent2, strokeWidth = 2.dp)
                    T(status, sora(13f, W.Regular, C.muted))
                }
            }
            "result" -> Card(14) {
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    SKMonoLabel("$points PUNKT" + if (points == 1) "" else "ER")
                    Spacer(Modifier.weight(1f))
                    Legend(C.muted, "Før"); Legend(C.accent2, "Etter")
                }
                EqChart(before, after, Modifier.fillMaxWidth().height(190.dp))
                val summary = if (cuts.isEmpty()) "Rommet er jevnt i bassen – ingen kutt trengs."
                    else "${cuts.size} kutt: " + cuts.joinToString(" · ") { "${it.f.roundToInt()} Hz ${String.format(Locale.US, "%.1f", it.g)} dB" }
                T(summary, sora(13f, W.Regular, C.muted))
                if (status.isNotEmpty()) T(status, sora(13f, W.Regular, if (saved) C.ok else C.accent2))
                if (points < 5) {
                    T("Neste: $tip", sora(13f, W.Regular, C.ink))
                    Secondary("Mål et punkt til") { withMic("measure") { measure() } }
                }
                Primary(if (saved) "Lagret" else "Lagre korreksjon", enabled = cuts.isNotEmpty() && !saved) { save() }
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    Secondary("Start på nytt", Modifier.weight(1f)) {
                        points = 0; before = emptyList(); after = emptyList(); cuts = emptyList(); saved = false; status = ""; phase = "intro"
                    }
                    Secondary("Slå av romkorreksjon", Modifier.weight(1f)) { turnOff() }
                }
            }
            else -> Card(12) {
                T(errMsg, sora(14f, W.Regular, C.ink))
                Primary("Prøv igjen") { phase = if (points > 0) "result" else "intro" }
            }
        }
        T("Telefonmikrofoner er unøyaktige under 40 Hz og over ca. 10 kHz. Derfor retter Skjold bare 40–300 Hz, og bare med kutt – aldri mer enn 10 dB.",
            sora(12f, W.Regular, C.muted))
    }
}

/** v4Card (radius 22, #141415, kant #242426) med padding 16. */
@Composable
private fun Card(spacing: Int, content: @Composable () -> Unit) {
    Column(
        Modifier.fillMaxWidth().clip(RoundedCornerShape(22.dp)).background(C.card).skBorder(C.line, 22.dp).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(spacing.dp),
    ) { content() }
}

@Composable
private fun StepRow(n: Int, text: String) {
    Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.Top) {
        Box(Modifier.size(22.dp).skCapsuleBorder(C.accent), contentAlignment = Alignment.Center) {
            T("$n", mono(11f, C.accent2))
        }
        T(text, sora(13f, W.Regular, C.ink), Modifier.weight(1f))
    }
}

@Composable
private fun Legend(color: Color, text: String) {
    Row(horizontalArrangement = Arrangement.spacedBy(5.dp), verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.width(12.dp).height(3.dp).clip(CircleShape).background(color))
        T(text, mono(10f, C.muted))
    }
}

/** Hovedknapp: kapsel 48 høy, #d9a441, tekst 15 halvfet i bakgrunnsfargen. */
@Composable
private fun Primary(t: String, enabled: Boolean = true, action: () -> Unit) {
    Box(
        Modifier.fillMaxWidth().height(48.dp).clip(CircleShape).background(C.accent).press(enabled = enabled) { action() },
        contentAlignment = Alignment.Center,
    ) { T(t, sora(15f, W.Semibold, C.bg)) }
}

/** Sekundærknapp: kapsel 44 høy med kant #2e2e30. */
@Composable
private fun Secondary(t: String, modifier: Modifier = Modifier.fillMaxWidth(), enabled: Boolean = true, action: () -> Unit) {
    Box(
        modifier.height(44.dp).clip(CircleShape).skCapsuleBorder(C.line2).press(enabled = enabled) { action() },
        contentAlignment = Alignment.Center,
    ) { T(t, sora(14f, W.Regular, C.ink), Modifier.padding(horizontal = 12.dp), align = TextAlign.Center) }
}

/** Kurve 20–1000 Hz (log), ±15 dB, med 40–300 Hz markert (RoomEQChart). */
@Composable
private fun EqChart(before: List<EqPt>, after: List<EqPt>, modifier: Modifier) {
    Canvas(modifier) {
        val w = size.width
        val h = size.height
        val d = density
        fun x(f: Double): Float = (ln(f / 20.0) / ln(1000.0 / 20.0)).toFloat() * w
        fun y(db: Double): Float = h / 2f - (db.coerceIn(-15.0, 15.0) / 15.0).toFloat() * (h / 2f)
        drawRect(C.accent2.copy(alpha = 0.07f), topLeft = Offset(x(40.0), 0f), size = Size(x(300.0) - x(40.0), h))
        for (db in listOf(-10.0, 0.0, 10.0)) drawLine(C.line2, Offset(0f, y(db)), Offset(w, y(db)), strokeWidth = d)
        for (f in listOf(50.0, 100.0, 200.0, 500.0)) drawLine(C.line2, Offset(x(f), 0f), Offset(x(f), h), strokeWidth = d)
        fun curve(pts: List<EqPt>): Path {
            val p = Path()
            pts.forEachIndexed { i, pt -> if (i == 0) p.moveTo(x(pt.f), y(pt.db)) else p.lineTo(x(pt.f), y(pt.db)) }
            return p
        }
        drawPath(curve(before), C.muted, style = Stroke(width = 1.5f * d, join = StrokeJoin.Round))
        drawPath(curve(after), C.accent2, style = Stroke(width = 2f * d, join = StrokeJoin.Round))
    }
}
