package no.kristo.skjold

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import org.json.JSONObject
import java.net.URLEncoder

/** Ett treff fra Music Assistant eller NRK. Spilles via Skjold (/api/ma/play, /api/nrk/play). */
data class ExtHit(val id: String, val title: String, val sub: String, val badge: String, val path: String, val body: Map<String, Any?>)

object ExtSearch {
    fun fromMA(raw: ByteArray?): List<ExtHit> {
        val o = try { JSONObject(String(raw ?: return emptyList())) } catch (_: Exception) { return emptyList() }
        val out = mutableListOf<ExtHit>()
        for (key in listOf("tracks", "albums", "playlists", "podcasts")) {
            val arr = o.optJSONArray(key) ?: continue
            val n = minOf(arr.length(), if (key == "tracks") 8 else 4)
            for (i in 0 until n) {
                val it = arr.optJSONObject(i) ?: continue
                val uri = it.optString("uri")
                if (uri.isEmpty()) continue
                val artist = it.optString("artist")
                val prov = it.optString("provider").ifEmpty { "MA" }
                out += ExtHit("ma:$uri", it.optString("name"), if (artist.isEmpty()) prov else "$artist · $prov", prov.uppercase(),
                    "/api/ma/play", mapOf("uri" to uri, "enqueue" to "play"))
            }
        }
        return out
    }

    fun fromNRK(raw: ByteArray?): List<ExtHit> {
        val o = try { JSONObject(String(raw ?: return emptyList())) } catch (_: Exception) { return emptyList() }
        val arr = o.optJSONArray("episodes") ?: return emptyList()
        val out = mutableListOf<ExtHit>()
        for (i in 0 until minOf(arr.length(), 8)) {
            val e = arr.optJSONObject(i) ?: continue
            val id = e.optString("id")
            if (id.isEmpty()) continue
            val series = e.optString("series")
            val date = e.optString("date")
            val body = mapOf<String, Any?>("id" to id, "title" to e.optString("title"), "series" to series,
                "image" to e.optString("image"), "duration" to e.optDouble("duration", 0.0), "podcast" to e.optBoolean("podcast"))
            out += ExtHit("nrk:$id", e.optString("title"), listOf(series, date).filter { it.isNotEmpty() }.joinToString(" · "), "NRK", "/api/nrk/play", body)
        }
        return out
    }
}

/** Søkeresultater fra Music Assistant og NRK under bibliotekets søkefelt. */
@Composable
fun ExtSearchResults(m: AppModel, q: String) {
    var hits by remember { mutableStateOf<List<ExtHit>>(emptyList()) }
    val scope = rememberCoroutineScope()
    LaunchedEffect(q) {
        hits = emptyList()
        if (!m.live || q.isBlank()) return@LaunchedEffect
        delay(400)
        val h = m.settingsHost
        val enc = URLEncoder.encode(q, "UTF-8")
        val found = ExtSearch.fromMA(DeviceLink.get("/api/ma/search?q=$enc", on = h, timeout = 12.0)) +
            ExtSearch.fromNRK(DeviceLink.get("/api/nrk/search?q=$enc", on = h, timeout = 12.0))
        hits = found
    }
    var askMsg by remember(q) { mutableStateOf("") }
    if (m.live && q.isNotBlank()) {
        Column(Modifier.fillMaxWidth().padding(top = 12.dp)) {
            Row(
                Modifier.fillMaxWidth().clickable {
                    val host = m.settingsHost
                    askMsg = "Finner noe …"
                    scope.launch {
                        val raw = DeviceLink.send("/api/ask", mapOf("text" to q), on = host, timeout = 60.0)
                        val o = try { JSONObject(String(raw ?: ByteArray(0))) } catch (_: Exception) { null }
                        askMsg = when {
                            o == null -> "Fant ikke noe som passet"
                            o.optBoolean("ok") -> "Spiller " + o.optString("summary")
                            else -> o.optString("error", "Fant ikke noe som passet") + " (" + o.optString("summary") + ")"
                        }
                    }
                }.padding(vertical = 6.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                T("Spill noe til «$q»", sora(15f, W.Semibold, C.accent2), maxLines = 1)
            }
            if (askMsg.isNotEmpty()) T(askMsg, sora(12f, W.Regular, C.muted))
        }
    }
    if (hits.isEmpty()) return
    Column(Modifier.fillMaxWidth().padding(top = 12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        T("MUSIC ASSISTANT OG NRK", mono(10f, C.muted, 0.12f))
        for (h in hits) {
            Row(
                Modifier.fillMaxWidth().clickable {
                    val host = m.settingsHost
                    scope.launch { DeviceLink.send(h.path, h.body, on = host, timeout = 12.0) }
                }.padding(vertical = 6.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                Column(Modifier.weight(1f)) {
                    T(h.title, sora(15f, W.Semibold), maxLines = 1)
                    T(h.sub, sora(12f, W.Regular, C.muted), maxLines = 1)
                }
                T(h.badge, mono(10f, C.accent2, 0.1f))
            }
        }
    }
}
