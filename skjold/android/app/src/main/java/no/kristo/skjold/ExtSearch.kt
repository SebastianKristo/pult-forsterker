package no.kristo.skjold

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

/** Ett treff fra Music Assistant (låt/album/spilleliste/podkast) eller NRK (episode). Spilles via Skjold. */
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
            val title = e.optString("title")
            val series = e.optString("series")
            val date = e.optString("date")
            // som iOS: bilde, varighet og podkast bare når de finnes
            val body = HashMap<String, Any?>()
            body["id"] = id; body["title"] = title; body["series"] = series
            if (e.has("image") && !e.isNull("image")) body["image"] = e.optString("image")
            if (e.has("duration") && !e.isNull("duration")) body["duration"] = e.optDouble("duration")
            if (e.has("podcast") && !e.isNull("podcast")) body["podcast"] = e.optBoolean("podcast")
            val sub = if (series.isEmpty()) date else if (date.isEmpty()) series else "$series · $date"
            out += ExtHit("nrk:$id", title, sub, "NRK", "/api/nrk/play", body)
        }
        return out
    }

    /** Treff fra Music Assistant og NRK via Skjold (/api/ma/search og /api/nrk/search). */
    suspend fun load(host: String?, q: String): List<ExtHit> {
        val enc = YtmLib.q(q)   // & + # i søket må kodes (AC&DC)
        return fromMA(DeviceLink.get("/api/ma/search?q=$enc", on = host, timeout = 12.0)) +
            fromNRK(DeviceLink.get("/api/nrk/search?q=$enc", on = host, timeout = 12.0))
    }

    /** «Spill noe til …» (POST /api/ask). Gir teksten som vises under knappen. */
    suspend fun ask(host: String?, text: String): String {
        val raw = DeviceLink.send("/api/ask", mapOf("text" to text), on = host, timeout = 60.0)
        val o = try { raw?.let { JSONObject(String(it)) } } catch (_: Exception) { null }
        return when {
            o == null -> "Fant ikke noe som passet"
            o.optBoolean("ok") -> "Spiller " + o.optString("summary")
            else -> o.optString("error", "Fant ikke noe som passet") + " (" + o.optString("summary") + ")"
        }
    }

    /** Spiller et treff via Skjold. */
    suspend fun play(host: String?, h: ExtHit) {
        DeviceLink.send(h.path, h.body, on = host, timeout = 12.0)
    }
}

/** «MUSIC ASSISTANT OG NRK»: omslag 52 r9, tittel 15/600, undertekst 12, merke i mono gull. */
@Composable
fun ExtHitList(m: AppModel, ext: List<ExtHit>) {
    val scope = rememberCoroutineScope()
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        SourceKicker("MUSIC ASSISTANT OG NRK")
        for (h in ext) {
            Row(
                Modifier.fillMaxWidth().press { val host = m.activeHost; scope.launch { ExtSearch.play(host, h) } }.padding(vertical = 4.dp),
                verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp),
            ) {
                SourceCover(h.title, 52.dp, 9.dp)
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    T(h.title, sora(15f, W.Semibold), maxLines = 1)
                    T(h.sub, sora(12f, W.Regular, SourceTok.muted), maxLines = 1)
                }
                T(h.badge, mono(10f, SourceTok.gold, 0.1f))
            }
        }
    }
}

/** «Spill noe til …» og treff fra Music Assistant og NRK for et søk (samme som nederst i søket). */
@Composable
fun ExtSearchResults(m: AppModel, q: String) {
    var hits by remember { mutableStateOf<List<ExtHit>>(emptyList()) }
    var askMsg by remember(q) { mutableStateOf("") }
    val scope = rememberCoroutineScope()
    LaunchedEffect(q) {
        hits = emptyList()
        if (m.demo || q.isBlank()) return@LaunchedEffect
        delay(350)
        hits = ExtSearch.load(m.activeHost, q)
    }
    if (!m.demo && q.isNotBlank()) {
        Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Row(
                Modifier.fillMaxWidth().press {
                    askMsg = "Finner noe …"
                    val host = m.activeHost
                    scope.launch { askMsg = ExtSearch.ask(host, q) }
                }.padding(vertical = 6.dp),
                verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                SKIcon(SourceTok.search, 18.dp, 2.2f, SourceTok.gold)
                T("Spill noe til «$q»", sora(15f, W.Semibold), Modifier.weight(1f), maxLines = 1)
            }
            if (askMsg.isNotEmpty()) T(askMsg, sora(12f, W.Regular, SourceTok.muted))
        }
    }
    if (hits.isNotEmpty()) ExtHitList(m, hits)
}
