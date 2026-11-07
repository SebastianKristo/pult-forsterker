package no.kristo.skjold

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.widget.Toast
import androidx.core.content.pm.ShortcutInfoCompat
import androidx.core.content.pm.ShortcutManagerCompat
import androidx.core.graphics.drawable.IconCompat
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import kotlin.concurrent.thread

/**
 * Snarveier, deep links og Google Assistant (App Actions).
 *
 * Deep links (alle åpner denne usynlige aktiviteten, som sender kallet, viser en kort melding og lukker seg):
 *   skjold://spill?favoritt=NRK%20Jazz&rom=Kjøkken   · skjold://spill?n=2   · skjold://spill?kanal=P4
 *   skjold://volum?prosent=30   · skjold://volum?delta=8   · skjold://pause · skjold://play · skjold://neste · skjold://av
 *   skjold://routine/<id>   · skjold://recognize   · skjold://doorbell
 *   skjold://feature?feature=<tekst>   (Google Assistant «Åpne NRK Jazz i Skjold»: favoritt, rutine eller kommando)
 * «rom» er rommets navn slik appen kjenner det (skjold-known); uten rom brukes enheten appen styrer nå.
 *
 * Langt trykk på app-ikonet: de 4 første radiofavorittene (dynamiske), så rutiner hvis det er plass.
 * Stemmekommandoer i Google Assistant via App Actions krever at appen er publisert i Google Play; snarveiene og
 * deep linkene virker uansett (også fra snarvei-apper, NFC-brikker og Tasker).
 */
class ShortcutActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        Store.init(applicationContext)
        val u = intent?.data
        if (u == null) { finish(); return }
        val app = applicationContext
        thread {
            val msg = try { Shortcuts.handle(app, u) } catch (_: Exception) { null }
            runOnUiThread { Toast.makeText(app, msg ?: "Fikk ikke kontakt med Skjold", Toast.LENGTH_SHORT).show() }
        }
        finish()
    }
}

object Shortcuts {
    private const val MAX_FAVS = 4

    private fun known(): JSONArray = try { JSONArray(Store.string("skjold-known") ?: "[]") } catch (_: Exception) { JSONArray() }

    /** Vert for rommet (navn eller id i skjold-known), ellers enheten appen styrer nå. */
    fun host(ctx: Context, rom: String?): String? {
        Store.init(ctx)
        if (!rom.isNullOrBlank()) {
            val q = rom.trim().lowercase()
            val arr = known()
            for (i in 0 until arr.length()) {
                val d = arr.optJSONObject(i) ?: continue
                val name = d.optString("name").lowercase()
                if (name == q || d.optString("id").lowercase() == q || (name.isNotEmpty() && (q.contains(name) || name.contains(q)))) {
                    val h = d.optString("host")
                    if (h.isNotEmpty()) return h
                }
            }
        }
        return Store.string("skjold-host")?.takeIf { it.isNotBlank() } ?: WidgetStore.load(ctx).host.takeIf { it.isNotBlank() }
    }

    private fun roomName(h: String?): String {
        val arr = known()
        for (i in 0 until arr.length()) {
            val d = arr.optJSONObject(i) ?: continue
            if (d.optString("host") == h) return d.optString("name").ifEmpty { "Skjold" }
        }
        return "Skjold"
    }

    internal fun http(h: String?, method: String, path: String, body: JSONObject? = null): String? = try {
        val raw = (h ?: "").trim().trimEnd('/')
        if (raw.isEmpty()) null else {
            val base = if (raw.startsWith("http")) raw else "http://$raw"
            val c = URL(base + path).openConnection() as HttpURLConnection
            c.requestMethod = method; c.connectTimeout = 4000; c.readTimeout = 8000
            // Fjerntilgang via Skjold-hjem: samme innloggings-informasjonskapsel som appen (Hjem.cookieInterceptor)
            val t = Hjem.token
            if (t != null && c.url.host == Hjem.host) c.setRequestProperty("Cookie", "${Hjem.COOKIE}=$t")
            if (method == "POST") {
                c.doOutput = true; c.setRequestProperty("Content-Type", "application/json")
                c.outputStream.use { it.write((body ?: JSONObject()).toString().toByteArray()) }
            }
            if (c.responseCode in 200..299) c.inputStream.bufferedReader().readText() else null
        }
    } catch (_: Exception) { null }

    private fun post(h: String?, path: String, body: JSONObject? = null): Boolean = http(h, "POST", path, body) != null

    /** Enheten appen styrer nå (brukes av eldre kode). */
    fun post(ctx: Context, path: String): Boolean = post(host(ctx, null), path)

    /** Senk musikken (telefonsamtale m.m.) på enheten appen styrer: POST /api/duck. Blokkerer – kall fra en bakgrunnstråd. */
    fun duck(ctx: Context, body: JSONObject): Boolean = post(host(ctx, null), "/api/duck", body)

    private fun presets(h: String?): List<Pair<Int, String>> {
        val body = http(h, "GET", "/api/presets") ?: return emptyList()
        val arr = try { JSONObject(body).optJSONArray("presets") } catch (_: Exception) { null } ?: return emptyList()
        return (0 until arr.length()).mapNotNull { i ->
            val p = arr.optJSONObject(i)
            val t = p?.optString("title") ?: ""
            if (p == null || t.isEmpty()) null else p.optInt("n", i + 1) to t
        }
    }

    private fun routines(h: String?): List<Pair<String, String>> {
        val body = http(h, "GET", "/api/routines") ?: return emptyList()
        val arr = try { JSONObject(body).optJSONArray("routines") } catch (_: Exception) { null } ?: return emptyList()
        return (0 until arr.length()).mapNotNull { i ->
            val r = arr.optJSONObject(i)
            val id = r?.optString("id") ?: ""
            if (r == null || id.isEmpty()) null else id to r.optString("navn", r.optString("name", id)).ifEmpty { id }
        }
    }

    // MARK: - Deep links

    /** Utfører en skjold://-lenke. Returnerer meldingen som vises, eller null ved feil. */
    fun handle(ctx: Context, u: Uri): String? {
        val h = host(ctx, u.getQueryParameter("rom"))
        val rom = roomName(h)
        return when (u.host) {
            "spill" -> {
                post(h, "/api/power", JSONObject().put("on", true))
                val n = u.getQueryParameter("n")?.toIntOrNull()
                val fav = u.getQueryParameter("favoritt")
                val kanal = u.getQueryParameter("kanal")
                when {
                    n != null -> if (post(h, "/api/preset", JSONObject().put("n", n))) "Spiller favoritt $n i $rom" else null
                    !fav.isNullOrBlank() -> playByName(h, fav, rom)
                    !kanal.isNullOrBlank() -> playByName(h, kanal, rom)
                    else -> if (post(h, "/api/transport", JSONObject().put("action", "play"))) "Spiller i $rom" else null
                }
            }
            "volum" -> {
                val p = u.getQueryParameter("prosent")?.toIntOrNull()
                val d = u.getQueryParameter("delta")?.toIntOrNull()
                when {
                    p != null -> if (post(h, "/api/volume", JSONObject().put("volume", p.coerceIn(0, 100)))) "Volum $p % i $rom" else null
                    d != null -> if (post(h, "/api/volume", JSONObject().put("delta", d))) (if (d > 0) "Skrudde opp i $rom" else "Skrudde ned i $rom") else null
                    else -> null
                }
            }
            "pause" -> if (post(h, "/api/transport", JSONObject().put("action", "pause"))) "Pause i $rom" else null
            "play" -> if (post(h, "/api/transport", JSONObject().put("action", "play"))) "Spiller i $rom" else null
            "neste" -> if (post(h, "/api/transport", JSONObject().put("action", "next"))) "Neste" else null
            "av" -> if (post(h, "/api/power", JSONObject().put("on", false))) "Slo av $rom" else null
            "routine" -> if (post(h, "/api/routines/${Uri.encode(u.lastPathSegment ?: "")}/run")) "Kjører rutine" else null
            "recognize" -> if (post(h, "/api/recognize")) "Lytter …" else null
            "doorbell" -> if (post(h, "/api/doorbell")) "Ringer på" else null
            "feature" -> feature(h, u.getQueryParameter("feature") ?: "", rom)
            else -> null
        }
    }

    /** Favoritt med navnet først, så NRK, så Radio Browser via Skjold. */
    private fun playByName(h: String?, name: String, rom: String): String? {
        val q = name.trim().lowercase()
        val fav = presets(h).firstOrNull { val t = it.second.lowercase(); t == q || t.contains(q) || q.contains(t) }
        if (fav != null) return if (post(h, "/api/preset", JSONObject().put("n", fav.first))) "Spiller ${fav.second} i $rom" else null
        if (q.startsWith("nrk") && post(h, "/api/nrk/play", JSONObject().put("query", name))) return "Spiller $name i $rom"
        val body = http(h, "GET", "/api/radio/search?q=" + Uri.encode(name)) ?: return null
        val j = try { JSONObject(body) } catch (_: Exception) { null } ?: return null
        val st = j.optJSONArray("norway")?.optJSONObject(0) ?: j.optJSONArray("world")?.optJSONObject(0)
        val url = st?.optString("url") ?: ""
        if (st == null || url.isEmpty()) return "Fant ingen kanal som heter $name"
        val title = st.optString("name", name)
        val ok = post(h, "/api/radio/play", JSONObject().put("url", url).put("title", title)
            .put("image", st.optString("image")).put("genre", st.optString("genre")))
        return if (ok) "Spiller $title i $rom" else null
    }

    /** Google Assistant «Åpne <funksjon> i Skjold»: kommando, rutine eller favoritt/kanal. */
    private fun feature(h: String?, text: String, rom: String): String? {
        val q = text.trim().lowercase()
        if (q.isEmpty()) return null
        when (q) {
            "pause", "stopp" -> return if (post(h, "/api/transport", JSONObject().put("action", "pause"))) "Pause i $rom" else null
            "neste", "neste låt", "next" -> return if (post(h, "/api/transport", JSONObject().put("action", "next"))) "Neste" else null
            "volum opp", "skru opp" -> return if (post(h, "/api/volume", JSONObject().put("delta", 8))) "Skrudde opp i $rom" else null
            "volum ned", "skru ned" -> return if (post(h, "/api/volume", JSONObject().put("delta", -8))) "Skrudde ned i $rom" else null
            "slå av", "av" -> return if (post(h, "/api/power", JSONObject().put("on", false))) "Slo av $rom" else null
        }
        val r = routines(h).firstOrNull { it.second.lowercase() == q || it.first.lowercase() == q }
        if (r != null) return if (post(h, "/api/routines/${Uri.encode(r.first)}/run")) "Kjører ${r.second}" else null
        post(h, "/api/power", JSONObject().put("on", true))
        return playByName(h, text, rom)
    }

    // MARK: - Dynamiske snarveier (langt trykk på ikonet + Google Assistant)

    /** De 4 første favorittene, så rutiner så langt det er plass. Kalles i bakgrunnen ved oppstart. */
    fun refresh(ctx: Context) = thread {
        Store.init(ctx)
        val h = host(ctx, null) ?: return@thread
        val favs = presets(h).take(MAX_FAVS)
        val rts = routines(h)
        val max = (ShortcutManagerCompat.getMaxShortcutCountPerActivity(ctx) - 1).coerceAtLeast(1)   // 1 statisk («Hva er dette?»)
        val list = mutableListOf<ShortcutInfoCompat>()
        favs.forEachIndexed { i, (n, t) ->
            list += ShortcutInfoCompat.Builder(ctx, "fav-$n").setShortLabel(t).setLongLabel("Spill $t")
                .setIcon(IconCompat.createWithResource(ctx, R.mipmap.ic_launcher))
                .setIntent(Intent(Intent.ACTION_VIEW, Uri.parse("skjold://spill?n=$n"), ctx, ShortcutActivity::class.java))
                .addCapabilityBinding("actions.intent.OPEN_APP_FEATURE", "feature", listOf(t))
                .setRank(i).build()
        }
        rts.forEachIndexed { i, (id, navn) ->
            list += ShortcutInfoCompat.Builder(ctx, "routine-$id").setShortLabel(navn).setLongLabel("Kjør $navn")
                .setIcon(IconCompat.createWithResource(ctx, R.mipmap.ic_launcher))
                .setIntent(Intent(Intent.ACTION_VIEW, Uri.parse("skjold://routine/${Uri.encode(id)}"), ctx, ShortcutActivity::class.java))
                .addCapabilityBinding("actions.intent.OPEN_APP_FEATURE", "feature", listOf(navn))
                .setRank(favs.size + i).build()
        }
        try { ShortcutManagerCompat.setDynamicShortcuts(ctx, list.take(max)) } catch (_: Exception) {}
    }
}
