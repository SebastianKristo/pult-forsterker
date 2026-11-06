package no.kristo.skjold

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
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
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import org.json.JSONArray
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/** GET /api/changelog: release-notater fra GitHub Releases (cachet på enheten, virker uten nett). */
data class ReleaseNote(val tag: String, val body: String, val date: String, val prerelease: Boolean) {
    companion object {
        fun of(j: JSONObject?): ReleaseNote? = j?.optString("tag")?.ifEmpty { null }?.let {
            ReleaseNote(it, j.optString("body"), j.optString("date"), j.optBoolean("prerelease", false))
        }
    }
}

data class ChangelogData(val current: String?, val notes: ReleaseNote?, val history: List<ReleaseNote>, val offline: Boolean) {
    companion object {
        suspend fun fetch(host: String): ChangelogData? {
            val url = Net.url(host, "/api/changelog") ?: return null
            val (d, code) = Net.data(url, timeout = 12.0) ?: return null
            if (code >= 300) return null
            return try {
                val j = JSONObject(String(d))
                val arr = j.optJSONArray("history") ?: JSONArray()
                ChangelogData(if (j.isNull("current")) null else j.optString("current"), ReleaseNote.of(j.optJSONObject("notes")),
                    (0 until arr.length()).mapNotNull { ReleaseNote.of(arr.optJSONObject(it)) }, j.optBoolean("offline", false))
            } catch (_: Exception) { null }
        }

        /** «Hva er nytt» én gang etter versjonsbytte. Første gang appen ser enheten vises ingenting. */
        suspend fun whatsNew(host: String): ReleaseNote? {
            val c = fetch(host) ?: return null
            val cur = c.current ?: return null
            val n = c.notes ?: return null
            val key = "skjold-seenRelease-$host"
            val seen = Store.prefs?.getString(key, null)
            if (seen == null) { Store.prefs?.edit()?.putString(key, cur)?.apply(); return null }
            return if (seen == cur) null else n
        }

        fun markSeen(tag: String, host: String) { Store.prefs?.edit()?.putString("skjold-seenRelease-$host", tag)?.apply() }
    }
}

/** Enkel markdown: ## overskrift, * / - punkt, ellers avsnitt. */
@Composable
fun ReleaseNotesText(text: String) {
    val lines = text.split("\n").filter { it.isNotBlank() }
    Column(verticalArrangement = Arrangement.spacedBy(5.dp)) {
        if (lines.isEmpty()) T("Ingen notater for denne versjonen.", sora(13f, W.Regular, C.muted))
        val bullet = Regex("^\\s*[*-]\\s+")
        lines.forEach { raw ->
            val l = raw.replace("**", "").replace("`", "")
            when {
                l.startsWith("#") -> T(l.trimStart('#', ' '), sora(14f, W.Semibold), Modifier.padding(top = 6.dp))
                bullet.containsMatchIn(l) -> T("•  " + l.replace(bullet, ""), sora(13f, W.Regular, C.ink, 1.45f))
                else -> T(l, sora(13f, W.Regular, C.ink2, 1.45f))
            }
        }
    }
}

/** Innstillinger → Endringslogg. */
@Composable
fun ChangelogView(m: AppModel) {
    var data by remember { mutableStateOf<ChangelogData?>(null) }
    var loading by remember { mutableStateOf(true) }
    LaunchedEffect(m.activeHost) { data = m.activeHost?.let { ChangelogData.fetch(it) }; loading = false }
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        val d = data
        when {
            loading -> T("Henter …", sora(13f, W.Regular, C.muted))
            d == null -> T("Endringsloggen krever nyere Skjold-programvare.", sora(13f, W.Regular, C.muted))
            else -> {
                if (d.offline) T("Uten nett – viser lagrede notater.", sora(12f, W.Regular, Color(0xffc9b48a)))
                if (d.history.isEmpty()) T("Ingen release-notater ennå.", sora(13f, W.Regular, C.muted))
                d.history.forEach { r ->
                    SKCard {
                        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                T(r.tag.removePrefix("skjold-") + (if (r.tag == d.current) " · installert" else "") + (if (r.prerelease) " · beta" else ""),
                                    sora(15f, W.Semibold), Modifier.weight(1f))
                                T(r.date.take(10), mono(11f))
                            }
                            ReleaseNotesText(r.body)
                        }
                    }
                }
            }
        }
    }
}

/** «Hva er nytt»-arket over appen (legges i ContentView). */
@Composable
fun WhatsNewOverlay(m: AppModel) {
    var note by remember { mutableStateOf<ReleaseNote?>(null) }
    LaunchedEffect(m.activeHost, m.mode) { if (m.mode == Mode.APP) note = m.activeHost?.let { ChangelogData.whatsNew(it) } }
    val n = note ?: return
    val close = { m.activeHost?.let { ChangelogData.markSeen(n.tag, it) }; note = null }
    Box(Modifier.fillMaxSize().background(Color(0x8c000000)).clickable(remember { MutableInteractionSource() }, null) { close() },
        contentAlignment = Alignment.BottomCenter) {
        Column(
            Modifier.fillMaxWidth().heightIn(max = 620.dp).clip(RoundedCornerShape(topStart = 18.dp, topEnd = 18.dp)).background(Color(0xff141415))
                .clickable(remember { MutableInteractionSource() }, null) {}.verticalScroll(rememberScrollState()).navigationBarsPadding().padding(22.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            T(n.tag.removePrefix("skjold-"), mono(12f, C.accent))
            T("Hva er nytt", sora(22f, W.Semibold))
            ReleaseNotesText(n.body)
            Box(Modifier.fillMaxWidth().height(46.dp).clip(RoundedCornerShape(23.dp)).background(C.accent).press { close() },
                contentAlignment = Alignment.Center) { T("OK", sora(15f, W.Semibold, C.bg)) }
        }
    }
}

/** Innstillinger → Radioprogrammer: planlagte programopptak (episoder) fra /api/recordings. Planlegging gjøres i web-appen. */
@Composable
fun RecordedProgramsView(m: AppModel) {
    val scope = rememberCoroutineScope()
    var progs by remember { mutableStateOf<List<JSONObject>>(emptyList()) }
    var feed by remember { mutableStateOf("") }
    var loaded by remember { mutableStateOf(false) }
    LaunchedEffect(m.activeHost) {
        val h = m.activeHost
        val url = h?.let { Net.url(it, "/api/recordings") }
        val r = url?.let { Net.data(it, timeout = 8.0) }
        if (r != null && r.second < 300) try {
            val j = JSONObject(String(r.first))
            val a = j.optJSONArray("programs") ?: JSONArray()
            progs = (0 until a.length()).mapNotNull { a.optJSONObject(it) }
            feed = j.optString("feed")
        } catch (_: Exception) {}
        loaded = true
    }
    val fmt = remember { SimpleDateFormat("EEE d. MMM", Locale("nb", "NO")) }
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        T("Planlegg opptak (f.eks. «Nitimen hver lørdag») under Plugins → Radioopptak i web-appen. Episodene vises her og som podkast.", sora(12.5f, W.Regular, C.muted, 1.45f))
        if (feed.isNotEmpty()) T(feed, mono(11f, C.accent))
        if (loaded && progs.isEmpty()) T("Ingen programmer tatt opp ennå.", sora(13f, W.Regular, C.muted))
        progs.forEach { p ->
            val id = p.optString("id")
            SKCard {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    T(p.optString("name") + " · " + p.optString("channel"), sora(14f, W.Semibold))
                    val eps = p.optJSONArray("episodes") ?: JSONArray()
                    (0 until eps.length()).mapNotNull { eps.optJSONObject(it) }.forEach { e ->
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            T(fmt.format(Date(e.optLong("t") * 1000)) + " · ${e.optInt("dur") / 60} min", sora(13f, W.Regular, C.ink2), Modifier.weight(1f))
                            T("Spill", sora(13f, W.Regular, C.accent), Modifier.press {
                                scope.launch {
                                    val h = m.activeHost ?: return@launch
                                    val url = Net.url(h, "/api/recordings") ?: return@launch
                                    Net.data(url, "POST", DeviceLink.json(mapOf("play_episode" to mapOf("prog" to id, "file" to e.optString("file"), "title" to e.optString("title")))), 8.0)
                                }
                            })
                        }
                    }
                }
            }
        }
        Spacer(Modifier.height(4.dp))
    }
}
