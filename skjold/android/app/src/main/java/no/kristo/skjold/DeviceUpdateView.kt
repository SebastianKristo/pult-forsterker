package no.kristo.skjold

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import org.json.JSONObject

/** GET/POST /api/update: installed and newest skjold-v* release, and update from the app (git pull + update.sh on the device). */
data class DeviceUpdateInfo(
    val current: String?, val latest: String?, val available: Boolean, val running: Boolean,
    val result: String?, val log: List<String>, val canUpdate: Boolean, val error: String?,
) {
    companion object {
        private fun JSONObject.str(k: String): String? = if (isNull(k)) null else optString(k).ifEmpty { null }

        fun parse(d: ByteArray): DeviceUpdateInfo? = try {
            val j = JSONObject(String(d))
            val arr = j.optJSONArray("log")
            val log = mutableListOf<String>()
            if (arr != null) for (i in 0 until arr.length()) log.add(arr.optString(i))
            DeviceUpdateInfo(j.str("current"), j.str("latest"), j.optBoolean("available", false), j.optBoolean("running", false),
                j.str("result"), log, j.optBoolean("can_update", false), j.str("error"))
        } catch (_: Exception) { null }
    }
}

/** Innstillinger → Oppdatering: update Skjold on the device to the newest release. */
@Composable
fun DeviceUpdateView(m: AppModel) {
    val scope = rememberCoroutineScope()
    var info by remember { mutableStateOf<DeviceUpdateInfo?>(null) }
    var loading by remember { mutableStateOf(true) }
    var err by remember { mutableStateOf("") }
    var phase by remember { mutableStateOf("") }   // "", running, gone, done, failed
    var log by remember { mutableStateOf(listOf<String>()) }
    var alive by remember { mutableStateOf(true) }
    DisposableEffect(Unit) { onDispose { alive = false } }
    val working = phase == "running" || phase == "gone"

    suspend fun fetch(check: Boolean): DeviceUpdateInfo? {
        val h = m.activeHost ?: return null
        val url = Net.url(h, if (check) "/api/update" else "/api/update?check=0") ?: return null
        val r = Net.data(url, timeout = 15.0) ?: return null
        if (r.second >= 300) return null
        return DeviceUpdateInfo.parse(r.first)
    }

    /** Poll every 2 s until done. The service restarts during the update – tolerate up to 3 min without answer. */
    suspend fun follow() {
        phase = "running"
        var lastOk = System.currentTimeMillis()
        while (alive) {
            delay(2000)
            val r = fetch(false)
            if (r != null) {
                lastOk = System.currentTimeMillis(); log = r.log
                if (!r.running) {
                    val ok = (r.result ?: "").startsWith("ok")
                    phase = if (ok) "done" else "failed"
                    if (ok) Haptics.success() else Haptics.error()
                    info = fetch(true) ?: r
                    return
                }
                phase = "running"
            } else {
                phase = "gone"
                if (System.currentTimeMillis() - lastOk > 180_000) {
                    phase = "failed"
                    err = "Enheten har ikke svart på 3 minutter. Den kan fortsatt holde på – prøv igjen litt senere."
                    return
                }
            }
        }
    }

    suspend fun load() {
        loading = true; err = ""
        val i = fetch(true)
        if (i == null) err = "Fikk ikke kontakt med enheten." else { info = i; log = i.log }
        loading = false
        if (i != null && i.running && !working) follow()
    }

    suspend fun start() {
        val h = m.activeHost ?: return
        val url = Net.url(h, "/api/update") ?: return
        err = ""; log = emptyList()
        val r = Net.data(url, "POST", DeviceLink.json(emptyMap()), 15.0)
        if (r == null) { err = "Fikk ikke kontakt med enheten."; return }
        if (r.second >= 300) { err = WifiNet.errText(r.first, r.second); return }
        follow()
    }

    LaunchedEffect(m.activeHost) { load() }

    val cur = when {
        loading && info == null -> "…"
        info?.current == null -> "Ukjent versjon"
        info?.current == "lokal" -> "Lokal utviklerversjon"
        else -> info?.current ?: ""
    }

    @Composable
    fun Msg(t: String, bad: Boolean) {
        Box(Modifier.fillMaxWidth().skBox(Color(if (bad) 0xff2a1412 else 0xff16201a), Color(if (bad) 0xff5a2620 else 0xff2a4a33), 8.dp).padding(10.dp)) {
            T(t, sora(13f, W.Regular, if (bad) C.danger else C.ok, 1.45f))
        }
    }

    SKCard {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                T("Installert på enheten", sora(12f, W.Regular, C.muted))
                T(cur, sora(22f, W.Semibold))
                info?.latest?.let { T("NYESTE: $it", mono(11f)) }
            }
            if (working) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Box(Modifier.size(8.dp).clip(CircleShape).background(C.accent))
                    T(if (phase == "gone") "Starter Skjold på nytt … venter på enheten" else "Oppdaterer … ikke slå av enheten", sora(13f))
                }
            } else {
                if (phase == "done") Msg("Oppdatert" + (info?.current?.let { " til $it" } ?: "") + ".", false)
                if (phase == "failed") Msg("Oppdateringen feilet. Se loggen under.", true)
                val i = info
                if (i != null && phase != "done") {
                    val latest = i.latest
                    if (i.available && latest != null) {
                        T("En ny versjon er klar: $latest", sora(13f, W.Regular, C.ink2))
                        if (i.canUpdate) {
                            Box(
                                Modifier.fillMaxWidth().height(44.dp).clip(RoundedCornerShape(14.dp)).background(C.accent)
                                    .press { scope.launch { start() } },
                                contentAlignment = Alignment.Center,
                            ) { T("Oppdater til $latest", sora(14f, W.Semibold, C.bg)) }
                        } else {
                            T("Denne enheten må oppdateres fra terminalen én gang før den kan oppdateres herfra:\ngit pull && sudo bash pi/update.sh",
                                sora(12f, W.Regular, C.accent2, 1.5f))
                        }
                    } else if (i.error == null) {
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Box(Modifier.size(8.dp).clip(CircleShape).background(C.ok))
                            T("Skjold er oppdatert", sora(13f))
                        }
                    }
                    i.error?.let { Msg(it, true) }
                }
                Box(
                    Modifier.fillMaxWidth().height(42.dp).skBox(C.card2, C.line2).press(enabled = !loading) { phase = ""; scope.launch { load() } },
                    contentAlignment = Alignment.Center,
                ) { T(if (loading) "Sjekker …" else "Se etter oppdateringer", sora(13f)) }
            }
            if (err.isNotEmpty()) Msg(err, true)
            if (log.isNotEmpty() && (working || phase == "failed" || phase == "done")) {
                Box(Modifier.fillMaxWidth().heightIn(max = 220.dp).skBox(Color(0xff0f0f10), C.line, 10.dp).verticalScroll(rememberScrollState()).padding(10.dp)) {
                    T(log.takeLast(30).joinToString("\n"), mono(11f, C.ink2))
                }
            }
        }
    }
}
