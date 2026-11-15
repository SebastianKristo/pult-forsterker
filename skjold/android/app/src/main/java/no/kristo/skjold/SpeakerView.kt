package no.kristo.skjold

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBars
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.URLEncoder
import java.util.UUID

/** «Høyttalerprofil» (Skjold Sertifisert): finn en delt profil i Skjold Cloud, eller mål høyttaleren (gated, ≈ 1 m foran).
 *  Analyse og EQ-tilpasning skjer på Skjold (/api/speakers/…). */
private data class SpkHit(val id: String, val name: String, val count: Int, val certified: Boolean)

@Composable
fun SpeakerView(m: AppModel) {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    val session = remember { UUID.randomUUID().toString() }
    var current by remember { mutableStateOf("") }
    var certified by remember { mutableStateOf(false) }
    var enabled by remember { mutableStateOf(false) }
    var nFilters by remember { mutableIntStateOf(0) }
    var q by remember { mutableStateOf("") }
    var hits by remember { mutableStateOf(emptyList<SpkHit>()) }
    var status by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    var measured by remember { mutableIntStateOf(0) }
    var brand by remember { mutableStateOf("") }
    var model by remember { mutableStateOf("") }
    var share by remember { mutableStateOf(true) }

    fun obj(b: ByteArray?) = try { JSONObject(String(b ?: ByteArray(0))) } catch (_: Exception) { JSONObject() }
    fun apply(o: JSONObject) {
        val p = o.optJSONObject("profile") ?: JSONObject()
        current = listOf(p.optString("brand"), p.optString("model")).filter { it.isNotBlank() }.joinToString(" ")
        certified = p.optBoolean("certified"); enabled = o.optBoolean("enabled")
        nFilters = o.optJSONArray("active_filters")?.length() ?: 0
    }
    LaunchedEffect(Unit) { m.settingsHost?.let { apply(obj(DeviceLink.get("/api/speakers", on = it))) } }

    fun search() {
        val host = m.settingsHost ?: return
        scope.launch {
            val o = obj(DeviceLink.get("/api/speakers/search?q=" + URLEncoder.encode(q, "UTF-8"), on = host, timeout = 10.0))
            val arr = o.optJSONArray("results")
            hits = (0 until (arr?.length() ?: 0)).map { i ->
                val h = arr!!.getJSONObject(i)
                SpkHit(h.optString("id"), h.optString("merke") + " " + h.optString("modell"), h.optInt("antall", 1), h.optBoolean("sertifisert"))
            }
            status = if (hits.isEmpty()) "Ingen treff – mål høyttalerne selv og del profilen." else if (o.optBoolean("offline")) "Uten nett: viser bare profiler brukt før." else ""
        }
    }

    fun measure() {
        val host = m.settingsHost ?: return
        busy = true; status = "Måler … vær stille"
        scope.launch {
            try {
                DeviceLink.send("/api/roomeq/sweep", mapOf("level" to 0.4, "delay" to 1.0), on = host)
                val wav = withContext(Dispatchers.IO) { RoomEQRec.record(ctx, 8.5) }
                val url = Net.url(host, "/api/speakers/measure?session=$session&mode=gated&reset=${if (measured == 0) 1 else 0}")
                val res = if (url != null) Net.data(url, "POST", wav, 60.0, mapOf("Content-Type" to "audio/wav")) else null
                if (res == null) { status = "Fikk ikke kontakt med Skjold."; return@launch }
                val o = obj(res.first)
                if (res.second >= 300) { status = o.optString("error", "Målingen feilet."); return@launch }
                measured = o.optInt("gated", measured + 1)
                val score = o.optJSONObject("profile")?.optInt("score") ?: 0
                status = if (o.optJSONObject("point")?.optBoolean("clipped") == true) "Overstyrt – skru ned og mål igjen."
                    else "Score $score. Mål gjerne 3–5 ganger fra litt ulike vinkler."
            } catch (e: Exception) { status = e.message ?: "Målingen feilet." } finally { busy = false }
        }
    }
    val perm = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { ok -> if (ok) measure() else status = "Skjold trenger mikrofontilgang." }
    fun start() {
        if (ContextCompat.checkSelfPermission(ctx, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) measure()
        else perm.launch(Manifest.permission.RECORD_AUDIO)
    }

    // V4SpeakerSheet: VStack 16, padding 20, kort radius 22 (#141415 / kant #242426), gull-lenker, «Lagre og bruk» i gull
    val card = Modifier.fillMaxWidth().skBox(C.card, C.line, 22.dp)
    Column(
        Modifier.fillMaxSize().background(C.bg).windowInsetsPadding(WindowInsets.statusBars).verticalScroll(rememberScrollState()).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            T("Høyttalerprofil", sora(24f, W.Semibold), Modifier.weight(1f))
            T("Lukk", sora(15f, W.Regular, C.accent2), Modifier.press { m.showSpeakers = false })
        }
        T("Retter høyttalernes egen frekvensgang. Romkorreksjonen tar seg fortsatt av bassen i rommet.", sora(13f, W.Regular, C.muted))
        if (current.isNotEmpty()) Row(card.padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                T(current, sora(15f))
                T(if (certified) "✓ Skjold Sertifisert · $nFilters filtre" else "$nFilters filtre", sora(12f, W.Regular, if (certified) C.accent2 else C.muted))
            }
            SKToggle(enabled, onColor = C.accent2) {
                val host = m.settingsHost ?: return@SKToggle
                scope.launch { apply(obj(DeviceLink.send("/api/speakers", mapOf("enabled" to !enabled), on = host))) }
            }
        }
        SKMonoLabel("FINN PROFIL")
        Row(card.padding(end = 12.dp), verticalAlignment = Alignment.CenterVertically) {
            SKField("Merke eller modell", q, { q = it }, Modifier.weight(1f), border = Color.Transparent, bg = Color.Transparent, plainInput = true)
            T("Søk", sora(14f, W.Regular, C.accent2), Modifier.press { search() })
        }
        hits.forEach { h ->
            Row(card.padding(horizontal = 14.dp, vertical = 10.dp), verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    T(h.name, sora(14f))
                    T(if (h.certified) "✓ Skjold Sertifisert" else "${h.count} måling" + if (h.count == 1) "" else "er", sora(11f, W.Regular, if (h.certified) C.accent2 else C.muted))
                }
                T("Bruk", sora(14f, W.Regular, C.accent2), Modifier.press {
                    val host = m.settingsHost ?: return@press
                    scope.launch {
                        val r = DeviceLink.send("/api/speakers", mapOf("use" to h.id), on = host, timeout = 12.0)
                        if (r == null) status = "Fikk ikke hentet profilen." else { apply(obj(r)); Haptics.success() }
                    }
                })
            }
        }
        SKMonoLabel("MÅL SELV")
        T("Spill én høyttaler. Hold telefonen 1 m foran, i høyde med diskanten og minst 1 m fra vegger og gulv. Mål 3–5 ganger fra litt ulike vinkler.", sora(12f, W.Regular, C.muted))
        Row(card) {
            SKField("Merke", brand, { brand = it }, Modifier.weight(1f), border = Color.Transparent, bg = Color.Transparent)
            SKField("Modell", model, { model = it }, Modifier.weight(1f), border = Color.Transparent, bg = Color.Transparent)
        }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(
                Modifier.weight(1f).skBox(C.card, C.line, 22.dp).press(enabled = !busy) { start() }.padding(vertical = 12.dp),
                contentAlignment = Alignment.Center,
            ) { T(if (busy) "Måler …" else if (measured == 0) "Start måling" else "Mål igjen ($measured)", sora(14f, W.Regular, C.accent2)) }
            if (measured > 0) {
                val ready = brand.isNotBlank() && model.isNotBlank()
                Box(
                    Modifier.weight(1f).alpha(if (ready) 1f else 0.4f).clip(CircleShape).background(C.accent2)
                        .press(enabled = ready) {
                            val host = m.settingsHost ?: return@press
                            scope.launch {
                                val r = DeviceLink.send("/api/speakers/save", mapOf("session" to session, "brand" to brand, "model" to model, "share" to share, "apply" to true), on = host, timeout = 20.0)
                                if (r == null) status = "Fikk ikke lagret – oppgi merke og modell og mål minst én gang."
                                else { measured = 0; status = "Lagret og i bruk."; Haptics.success(); apply(obj(DeviceLink.get("/api/speakers", on = host))) }
                            }
                        }.padding(vertical = 12.dp),
                    contentAlignment = Alignment.Center,
                ) { T("Lagre og bruk", sora(14f, W.Regular, C.bg)) }
            }
        }
        Row(verticalAlignment = Alignment.CenterVertically) {
            T("Del anonymt i Skjold Cloud", sora(13f), Modifier.weight(1f))
            SKToggle(share, onColor = C.accent2) { share = !share }
        }
        if (status.isNotEmpty()) T(status, sora(12f, W.Regular, C.muted))
    }
}
