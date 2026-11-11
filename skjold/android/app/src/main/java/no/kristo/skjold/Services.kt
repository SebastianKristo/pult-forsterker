package no.kristo.skjold

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.awaitCancellation
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

// MARK: - JSON helpers (the daemon and the services answer with loose JSON, like [String: Any] in Swift)

fun JSONObject.str(k: String): String {
    val v = opt(k) ?: return ""
    return when (v) {
        JSONObject.NULL -> ""
        is String -> v
        is Number, is Boolean -> v.toString()
        else -> ""
    }
}

fun JSONObject.num(k: String): Int {
    val v = opt(k)
    return when (v) {
        is Number -> v.toInt()
        is String -> v.toIntOrNull() ?: v.toDoubleOrNull()?.toInt() ?: 0
        else -> 0
    }
}

fun JSONObject.dbl(k: String): Double = when (val v = opt(k)) { is Number -> v.toDouble(); is String -> v.toDoubleOrNull() ?: 0.0; else -> 0.0 }

fun JSONObject.bool(k: String): Boolean = when (val v = opt(k)) { is Boolean -> v; is Number -> v.toInt() != 0; else -> false }

/** A list or a single object, as a list of objects (Subsonic and Plex return either). */
fun jsonList(x: Any?): List<JSONObject> = when (x) {
    is JSONArray -> (0 until x.length()).mapNotNull { x.optJSONObject(it) }
    is JSONObject -> listOf(x)
    else -> emptyList()
}

fun jsonObject(d: ByteArray?): JSONObject? = try { d?.let { JSONObject(String(it)) } } catch (_: Exception) { null }

/** Builds a JSON body from Kotlin maps/lists (DeviceLink.json). */
fun toJson(v: Any?): Any? = when (v) {
    null -> JSONObject.NULL
    is Map<*, *> -> JSONObject().also { o -> v.forEach { (k, x) -> o.put(k.toString(), toJson(x)) } }
    is List<*> -> JSONArray().also { a -> v.forEach { a.put(toJson(it)) } }
    else -> v
}

// MARK: - HTTP helper

object Net {
    val client: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(6, TimeUnit.SECONDS)
        .readTimeout(10, TimeUnit.SECONDS)
        .retryOnConnectionFailure(false)
        .addInterceptor(Hjem.cookieInterceptor)
        .build()

    private val JSON_TYPE = "application/json".toMediaType()

    /** Plain request. Returns body and status code, or null when the host could not be reached. */
    suspend fun data(
        url: String, method: String = "GET", body: ByteArray? = null, timeout: Double = 6.0,
        headers: Map<String, String> = emptyMap(),
    ): Pair<ByteArray, Int>? = withContext(Dispatchers.IO) {
        try {
            val ms = (timeout * 1000).toLong()
            val c = client.newBuilder().callTimeout(ms, TimeUnit.MILLISECONDS).connectTimeout(minOf(ms, 6000), TimeUnit.MILLISECONDS)
                .readTimeout(ms, TimeUnit.MILLISECONDS).build()
            val rb = when {
                body != null -> body.toRequestBody(JSON_TYPE)
                method == "POST" || method == "PUT" -> ByteArray(0).toRequestBody(JSON_TYPE)
                else -> null
            }
            val req = Request.Builder().url(url).method(method, rb).header("Cache-Control", "no-cache")
            headers.forEach { (k, v) -> req.header(k, v) }
            c.newCall(req.build()).execute().use { r ->
                // Relé via Skjold-hjem: Cloudflare Access omdirigerer til innloggingen når informasjonskapselen mangler
                Pair(r.body?.bytes() ?: ByteArray(0), if (Hjem.accessBlocked(r.request.url.host, r.request.url.encodedPath)) 401 else r.code)
            }
        } catch (_: Exception) {
            null
        }
    }

    /** "http://" + host + path for a bare "ip:port" / "name.local:port", or a full URL. */
    fun url(base: String, path: String): String? {
        var b = base.trim()
        if (!b.lowercase().startsWith("http")) b = "http://$b"
        while (b.endsWith("/")) b = b.dropLast(1)
        val u = b + path
        return if (u.toHttpUrlOrNull() != null) u else null
    }

    /** Adds query parameters (URLComponents.queryItems). */
    fun withQuery(url: String, q: List<Pair<String, String>>): String? {
        val u = url.toHttpUrlOrNull() ?: return null
        val b = u.newBuilder()
        q.forEach { (k, v) -> b.addQueryParameter(k, v) }
        return b.build().toString()
    }
}

// MARK: - Radio Browser (https://de1.api.radio-browser.info)

data class RadioResult(val name: String, val genre: String, val url: String, val country: String, val br: Int, val codec: String)

object RadioBrowser {
    private const val BASE = "https://de1.api.radio-browser.info/json/stations/search"

    private suspend fun raw(q: List<Pair<String, String>>): JSONArray? {
        val url = Net.withQuery(BASE, q) ?: return null
        val (d, code) = Net.data(url, timeout = 10.0, headers = mapOf("User-Agent" to "Skjold-Android")) ?: return null
        if (code != 200) return null
        return try { JSONArray(String(d)) } catch (_: Exception) { null }
    }

    suspend fun search(q: String): List<RadioResult> {
        val list = raw(listOf("limit" to "20", "hidebroken" to "true", "order" to "clickcount", "reverse" to "true", "name" to q)) ?: return emptyList()
        return jsonList(list).mapNotNull { s ->
            val name = s.str("name").trim()
            val u = s.str("url_resolved").ifEmpty { s.str("url") }
            if (name.isEmpty() || u.isEmpty()) return@mapNotNull null
            val genre = s.str("tags").split(",").filter { it.isNotEmpty() }.take(2).joinToString(", ")
            RadioResult(name, genre, u, s.str("countrycode"), s.num("bitrate"), s.str("codec"))
        }
    }

    /** Stream URL for a catalog station that only has a name (the amplifier needs a URL to save or play it). */
    suspend fun streamURL(name: String): String? {
        val q = mapOf("P4 Norge" to "P4", "P5 Hits" to "P5", "NRJ" to "NRJ Norge")[name] ?: name
        val hits = search(q)
        val n = name.lowercase(); val ql = q.lowercase()
        return (hits.firstOrNull { it.name.lowercase() == n } ?: hits.firstOrNull { it.name.lowercase() == ql }
            ?: hits.firstOrNull { it.name.lowercase().startsWith(ql) } ?: hits.firstOrNull())?.url
    }

    /** Best logo for a station, scored like fetchLogos() in the design. null = request failed, "" = none found. */
    suspend fun logo(q: String, cc: String): String? {
        val list = raw(listOf("name" to q, "countrycode" to cc, "hidebroken" to "true", "order" to "clickcount", "reverse" to "true", "limit" to "25")) ?: return null
        val ql = q.lowercase()
        val ico = Regex("""\.ico(\?|$)""")
        fun score(s: JSONObject): Int {
            val n = s.str("name").trim().lowercase(); val f = s.str("favicon")
            return (if (n == ql) 4 else if (n.startsWith(ql)) 2 else 0) + (if (ico.containsMatchIn(f)) -3 else 2) + (if (f.lowercase().contains("logo")) 1 else 0)
        }
        val hits = jsonList(list).filter { it.str("favicon").startsWith("https:") }.sortedByDescending { score(it) }
        val f = hits.firstOrNull()?.str("favicon") ?: return ""
        if (Regex("""\.ico(\?|$)|16x16|32x32|\.svg""", RegexOption.IGNORE_CASE).containsMatchIn(f)) return ""
        return f
    }

    /** Checks that a stream answers with audio or a playlist (testStream() in the design; iOS uses AVPlayer). */
    suspend fun testStream(urlString: String): Boolean = withContext(Dispatchers.IO) {
        if (!urlString.lowercase().startsWith("http") || urlString.toHttpUrlOrNull() == null) return@withContext false
        try {
            val c = Net.client.newBuilder().callTimeout(8, TimeUnit.SECONDS).build()
            c.newCall(Request.Builder().url(urlString).header("Icy-MetaData", "0").build()).execute().use { r ->
                if (!r.isSuccessful) return@use false
                val ct = (r.header("Content-Type") ?: "").lowercase()
                val got = r.body?.source()?.request(1) ?: false
                (ct.startsWith("audio/") || ct.contains("ogg") || ct.contains("mpegurl") || ct.contains("scpls") || ct.contains("octet-stream")) && got
            }
        } catch (_: Exception) {
            false
        }
    }
}

// MARK: - Plex Media Server

object PlexAPI {
    sealed class Result {
        data class Ok(val n: Int) : Result()
        object Unauthorized : Result()
        object Unreachable : Result()
        object BadURL : Result()
    }

    /** Checks the server address and token by listing the library sections. `Ok` carries the number of music libraries. */
    suspend fun test(server: String, token: String): Result {
        var base = server.trim()
        if (!base.lowercase().startsWith("http")) base = "http://$base"
        while (base.endsWith("/")) base = base.dropLast(1)
        val url = Net.withQuery("$base/library/sections", listOf("X-Plex-Token" to token.trim())) ?: return Result.BadURL
        val (d, code) = Net.data(url, timeout = 6.0, headers = mapOf("Accept" to "application/json", "X-Plex-Product" to "Skjold", "X-Plex-Client-Identifier" to "skjold-android"))
            ?: return Result.Unreachable
        if (code == 401) return Result.Unauthorized
        if (code != 200) return Result.Unreachable
        val mc = jsonObject(d)?.optJSONObject("MediaContainer")
        return Result.Ok(jsonList(mc?.opt("Directory")).count { it.str("type") == "artist" })
    }
}

// MARK: - Device status (GET /api/status, SSE /api/events)

/** The parts of ki_amp_daemon.py's status the app uses. */
data class DevStatus(
    val name: String = "", val id: String = "", val product: String = "", val board: String = "", val version: String = "",
    val input: String = "", val source: String = "", val title: String = "", val artist: String = "", val album: String = "",
    val coverURL: String = "", val btDevice: String = "", val airplayDevice: String = "", val lyrionServer: String = "", val lyrionPlayer: String = "",
    val power: Boolean = true, val playing: Boolean = false, val paused: Boolean = false, val mute: Boolean = false,
    val headphones: Boolean = false, val lyrion: Boolean = false, val btPairing: Boolean = false,
    val volume: Int = 0, val duration: Int = 0, val position: Int = 0, val preset: Int = 0, val presetsCount: Int = 0, val btPairingLeft: Int = 0,
    val inputs: List<String> = emptyList(), val presetTitles: List<String> = emptyList(), val radioNow: RadioNow? = null,
    /** Strømmen som spilles, via Skjold (/api/stream/…), for «Denne telefonen». Tom når kilden ikke kan spilles her. */
    val listen: String = "",
    /** Vekkeklokka på enheten ringer (status.alarm). Slumre og slå av med POST /api/alarm. */
    val alarmRinging: Boolean = false, val alarmName: String = "",
) {
    data class RadioNow(val name: String = "", val genre: String = "", val now: String = "", val image: String = "", val url: String = "", val n: Int = 0, val playing: Boolean = false, val logo: String = "")

    companion object {
        fun parse(d: ByteArray?): DevStatus? = jsonObject(d)?.let { parse(it) }

        fun parse(j: JSONObject): DevStatus? {
            if (!j.has("volume")) return null
            val board = j.str("board")
            var product = j.str("product")
            if (product.isEmpty()) product = if (board == "node") "node" else "s1"
            var cover = j.str("cover_url")
            if (cover.isEmpty() && j.str("cover").isNotEmpty()) cover = "/api/cover?v=" + j.str("cover")
            val inputs = j.optJSONArray("inputs")?.let { a -> (0 until a.length()).map { a.optString(it) } } ?: emptyList()
            val presets = jsonList(j.opt("presets")).map { it.str("title") }
            val rn = j.optJSONObject("radio_now")?.let { r ->
                RadioNow(r.str("name"), r.str("genre"), r.str("now"), r.str("image"), r.str("url"), r.num("n"), r.bool("playing"), r.str("logo"))
            }
            return DevStatus(
                name = j.str("name"), id = j.str("id"), product = product, board = board, version = j.str("version"),
                input = j.str("input"), source = j.str("source"), title = j.str("title"), artist = j.str("artist"), album = j.str("album"),
                coverURL = cover, btDevice = j.str("bt_device"), airplayDevice = j.str("airplay_device"),
                lyrionServer = j.str("lyrion_server"), lyrionPlayer = j.str("lyrion_player"),
                power = if (j.has("power")) j.bool("power") else true, playing = j.bool("playing"), paused = j.bool("paused"), mute = j.bool("mute"),
                headphones = j.bool("headphones"), lyrion = j.bool("lyrion"), btPairing = j.bool("bt_pairing"),
                volume = j.num("volume"), duration = j.num("duration"), position = j.num("position"), preset = j.num("preset"),
                presetsCount = j.num("presets_count"), btPairingLeft = j.num("bt_pairing_left"),
                inputs = inputs, presetTitles = presets, radioNow = rn, listen = j.str("listen"),
                alarmRinging = j.optJSONObject("alarm")?.bool("ringing") ?: false, alarmName = j.optJSONObject("alarm")?.str("name") ?: "",
            )
        }
    }
}

/** Settings from GET /api/settings (same keys as skjold_settings.js). Booleans become 0/1 like `AppModel.sset`. */
class DevSettings private constructor(val ints: Map<String, Int>, val strings: Map<String, String>, val eq: Map<String, EQProfile>, val homeLayout: List<HomeItem>? = null) {
    companion object {
        fun parse(d: ByteArray?): DevSettings? {
            val set = jsonObject(d)?.optJSONObject("settings") ?: return null
            val ints = HashMap<String, Int>(); val strings = HashMap<String, String>(); val eq = HashMap<String, EQProfile>()
            for (k in set.keys()) {
                val v = set.opt(k)
                if (k == "homeLayout") continue
                if (k == "eq" && v is JSONObject) {
                    for (src in v.keys()) {
                        val p = v.optJSONObject(src) ?: continue
                        val arr = p.optJSONArray("eq")
                        val bands = if (arr != null) (0 until arr.length()).map { arr.optInt(it) } else emptyList()
                        eq[src] = EQProfile(p.num("preset"), if (bands.size == 5) bands else listOf(0, 0, 0, 0, 0), if (p.has("loud")) p.bool("loud") else true)
                    }
                } else when (v) {
                    is String -> strings[k] = v
                    is Boolean -> ints[k] = if (v) 1 else 0
                    is Number -> ints[k] = v.toInt()
                }
            }
            return DevSettings(ints, strings, eq, HomeLayout.parse(set.optJSONArray("homeLayout")))
        }
    }
}

/** One favourite from GET /api/presets. */
data class DevPreset(val n: Int, val title: String, val url: String, val genre: String, val image: String, val logo: String = "") {
    companion object {
        fun list(d: ByteArray?): List<DevPreset>? {
            val j = jsonObject(d) ?: return null
            val ps = j.optJSONArray("presets") ?: return null
            return jsonList(ps).mapNotNull { p ->
                val url = p.str("url")
                if (url.isEmpty()) null
                else DevPreset(p.num("n"), p.str("title"), url, p.str("genre"), p.str("image").ifEmpty { p.str("icon") }, p.str("logo"))
            }
        }
    }
}

/** Wi-Fi networks from GET /api/wifi. */
object DevWifi {
    fun list(d: ByteArray?): List<String> {
        val n = jsonObject(d)?.optJSONArray("networks") ?: return emptyList()
        val out = ArrayList<String>()
        for (x in jsonList(n)) { val s = x.str("ssid"); if (s.isNotEmpty() && !out.contains(s)) out.add(s) }
        return out
    }
}

/** Server-Sent Events from GET /api/events: one «data: <status JSON>» line per change, «: ping» every 15 s. */
object DeviceEvents {
    private val sse: OkHttpClient by lazy {
        Net.client.newBuilder().readTimeout(40, TimeUnit.SECONDS).callTimeout(0, TimeUnit.MILLISECONDS).build()
    }

    /** Reads the stream until it ends, fails or the coroutine is cancelled. `onData` runs on the caller's dispatcher. */
    suspend fun stream(url: String, onData: suspend (String) -> Unit) = coroutineScope {
        val call = sse.newCall(Request.Builder().url(url).header("Accept", "text/event-stream").build())
        // cancelling the coroutine closes the connection, so the blocking read below returns
        val watcher = launch { try { awaitCancellation() } finally { call.cancel() } }
        try {
            val resp = withContext(Dispatchers.IO) { call.execute() }
            resp.use { r ->
                if (r.code != 200) return@use
                val src = r.body?.source() ?: return@use
                while (true) {
                    coroutineContext.ensureActive()
                    val line = withContext(Dispatchers.IO) { src.readUtf8Line() } ?: break
                    if (line.startsWith("data:")) onData(line.drop(5).trim())
                }
            }
        } catch (_: Exception) {
        } finally {
            watcher.cancel()
        }
    }
}

// MARK: - Device API

/** REST API of ki_amp_daemon.py on port 8765. `host` is "ip:port" of the device being controlled. */
object DeviceLink {
    const val PORT = 8765
    @Volatile var host: String? = null

    /** Normalises "192.168.1.5", "skjold.local" or "http://x:8765/" to "host:port". */
    fun normHost(s: String): String {
        var h = s.trim()
        val i = h.indexOf("://")
        if (i >= 0) h = h.substring(i + 3)
        val slash = h.indexOf('/')
        if (slash >= 0) h = h.substring(0, slash)
        if (!h.contains(":")) h += ":$PORT"
        return h
    }

    /** Status of any device ("ip:port"), short timeout. null = unreachable or not a Skjold daemon. */
    suspend fun status(host: String, timeout: Double = 3.0): DevStatus? {
        val url = Net.url(host, "/api/status") ?: return null
        val (d, code) = Net.data(url, timeout = timeout) ?: return null
        return if (code == 200) DevStatus.parse(d) else null
    }

    suspend fun get(path: String, on: String? = null, timeout: Double = 6.0): ByteArray? {
        val base = on ?: host ?: return null
        val url = Net.url(base, path) ?: return null
        val (d, code) = Net.data(url, timeout = timeout) ?: return null
        return if (code < 300) d else null
    }

    fun json(body: Map<String, Any?>, method: String = "POST"): ByteArray? =
        if (method == "DELETE") null else (toJson(body) as JSONObject).toString().toByteArray()

    /** POST (or PUT/DELETE) with a JSON body. Returns the body on 2xx, null otherwise. */
    suspend fun send(path: String, body: Map<String, Any?> = emptyMap(), method: String = "POST", on: String? = null, timeout: Double = 6.0): ByteArray? =
        sendRaw(path, json(body, method), method, on, timeout)

    /** Som send, men gir også statuskoden – så en feil fra enheten (400/409 med {"error": …}) kan vises. */
    suspend fun sendCode(path: String, body: Map<String, Any?> = emptyMap(), method: String = "POST", on: String? = null, timeout: Double = 6.0): Pair<ByteArray, Int>? {
        val base = on ?: host ?: return null
        val url = Net.url(base, path) ?: return null
        val (d, code) = Net.data(url, method, json(body, method), timeout) ?: return null
        return Pair(d, code)
    }

    suspend fun sendRaw(path: String, data: ByteArray?, method: String = "POST", on: String? = null, timeout: Double = 6.0): ByteArray? {
        val base = on ?: host ?: return null
        val url = Net.url(base, path) ?: return null
        val (d, code) = Net.data(url, method, data, timeout) ?: return null
        return if (code < 300) d else null
    }

    /** Absolute URL for a cover_url from the status ("/api/cover?v=…" or a full https URL). */
    fun coverURL(s: String, on: String? = null): String {
        if (s.isEmpty() || s.lowercase().startsWith("http")) return s
        val base = on ?: host ?: return ""
        return Net.url(base, s) ?: ""
    }
}
