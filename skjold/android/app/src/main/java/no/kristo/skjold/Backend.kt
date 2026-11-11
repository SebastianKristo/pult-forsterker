package no.kristo.skjold

import org.json.JSONArray
import org.json.JSONObject
import java.security.MessageDigest
import java.util.UUID
import kotlin.math.abs

// Clients for the services around the amplifier: Lyrion (rooms and sync), Navidrome (Subsonic API), Plex and GitHub Releases.

/** One track from Navidrome or Plex. `stream` is a direct URL the amplifier can play (POST /api/radio/play). */
data class LibItem(val id: String, val title: String, val artist: String, val album: String, val cover: String, val stream: String, val dur: Int)

/** An album or playlist. Tracks are loaded when it is opened. */
data class LibColl(val id: String, val name: String, val artist: String, val cover: String, val count: Int, val playlist: Boolean)

// MARK: - YouTube Music (innebygd i Skjold: GET /api/ytm/home|tracks|search, pi/skjold_ytm.py)

object YtmLib {
    fun colls(x: Any?): List<LibColl> = jsonList(x).map {
        LibColl(it.str("id"), it.str("name"), it.str("artist"), it.str("cover"), it.num("count"), it.bool("playlist"))
    }.filter { it.id.isNotEmpty() }

    fun items(x: Any?): List<LibItem> = jsonList(x).map {
        LibItem(it.str("id"), it.str("title"), it.str("artist"), it.str("album"), it.str("cover"), it.str("stream"), it.num("dur"))
    }.filter { it.stream.isNotEmpty() }

    fun q(s: String): String = java.net.URLEncoder.encode(s, "UTF-8").replace("+", "%20")
}

/** Simple success/failure result with an error text (Result<_, Failure> in Swift). */
sealed class Res<out T> {
    data class Ok<T>(val v: T) : Res<T>()
    data class Err(val text: String) : Res<Nothing>()

    fun getOrNull(): T? = (this as? Ok<T>)?.v
}

// MARK: - Lyrion Music Server (JSON-RPC, POST http://server:9000/jsonrpc.js)

object Lyrion {
    data class Player(val id: String, val name: String, val model: String, val ip: String, val connected: Boolean)
    data class PStatus(
        val mode: String = "", val title: String = "", val artist: String = "", val album: String = "", val cover: String = "",
        val volume: Int = 0, val duration: Int = 0, val time: Int = 0, val syncMaster: String = "", val syncSlaves: List<String> = emptyList(),
    ) {
        val playing: Boolean get() = mode == "play"
    }

    /** `server` is "host:port" (status field "lyrion_server" from the daemon). */
    suspend fun rpc(server: String, player: String, cmd: List<String>, timeout: Double = 4.0): JSONObject? {
        val url = Net.url(server, "/jsonrpc.js") ?: return null
        val body = JSONObject().put("id", 1).put("method", "slim.request").put("params", JSONArray().put(player).put(JSONArray(cmd)))
        val (d, code) = Net.data(url, "POST", body.toString().toByteArray(), timeout) ?: return null
        if (code != 200) return null
        val j = jsonObject(d) ?: return null
        return j.optJSONObject("result") ?: JSONObject()
    }

    suspend fun players(server: String): List<Player>? {
        val r = rpc(server, "", listOf("players", "0", "100")) ?: return null
        return jsonList(r.opt("players_loop")).map {
            Player(it.str("playerid"), it.str("name"), it.str("modelname").ifEmpty { it.str("model") }, it.str("ip"), it.num("connected") == 1)
        }
    }

    suspend fun status(server: String, pid: String): PStatus? {
        val r = rpc(server, pid, listOf("status", "-", "1", "tags:aAlKcdj")) ?: return null
        var title = ""; var artist = ""; var album = ""; var cover = ""
        jsonList(r.opt("playlist_loop")).firstOrNull()?.let { t ->
            title = t.str("title"); artist = t.str("artist"); album = t.str("album")
            val art = t.str("artwork_url"); val cid = t.str("coverid")
            cover = when {
                art.lowercase().startsWith("http") -> art
                art.isNotEmpty() -> Net.url(server, if (art.startsWith("/")) art else "/$art") ?: ""
                cid.isNotEmpty() -> Net.url(server, "/music/$cid/cover.jpg") ?: ""
                else -> ""
            }
        }
        if (title.isEmpty()) title = r.str("current_title")
        return PStatus(
            mode = r.str("mode"), title = title, artist = artist, album = album, cover = cover,
            volume = abs(r.num("mixer volume")), duration = r.dbl("duration").toInt(), time = r.dbl("time").toInt(),
            syncMaster = r.str("sync_master"), syncSlaves = r.str("sync_slaves").split(",").filter { it.isNotEmpty() },
        )
    }

    suspend fun command(server: String, pid: String, cmd: List<String>) { rpc(server, pid, cmd) }
}

// MARK: - Navidrome (Subsonic API 1.16.1, token auth: t = md5(password + salt))

object Subsonic {
    data class Conf(val url: String, val user: String, val pass: String) {
        val ok: Boolean get() = url.isNotBlank() && user.isNotBlank() && pass.isNotEmpty()
    }

    fun md5(s: String): String = MessageDigest.getInstance("MD5").digest(s.toByteArray()).joinToString("") { "%02x".format(it) }

    fun url(c: Conf, view: String, params: Map<String, String> = emptyMap()): String? {
        val salt = UUID.randomUUID().toString().replace("-", "").take(10).lowercase()
        val base = Net.url(c.url, "/rest/$view") ?: return null
        return Net.withQuery(base, listOf("u" to c.user.trim(), "t" to md5(c.pass + salt), "s" to salt, "v" to "1.16.1", "c" to "skjold-android", "f" to "json")
            + params.toSortedMap().map { it.key to it.value })
    }

    /** null on success, otherwise an error text for the settings row. */
    suspend fun ping(c: Conf): String? {
        if (!c.ok) return "Fyll inn server, brukernavn og passord"
        return when (val r = call(c, "ping")) { is Res.Ok -> null; is Res.Err -> r.text }
    }

    private suspend fun call(c: Conf, view: String, params: Map<String, String> = emptyMap()): Res<JSONObject> {
        val u = url(c, view, params) ?: return Res.Err("Ugyldig adresse")
        val (d, code) = Net.data(u, timeout = 10.0) ?: return Res.Err("Fant ikke serveren")
        val sr = jsonObject(d)?.optJSONObject("subsonic-response")
        if (code != 200 || sr == null) return Res.Err("Navidrome svarte $code")
        if (sr.str("status") != "ok") {
            val msg = sr.optJSONObject("error")?.str("message") ?: ""
            return Res.Err(if (msg.isEmpty()) "Innlogging feilet" else "Feil brukernavn eller passord")
        }
        return Res.Ok(sr)
    }

    private fun song(c: Conf, s: JSONObject): LibItem {
        val id = s.str("id"); val cover = s.str("coverArt")
        return LibItem(id, s.str("title"), s.str("artist"), s.str("album"),
            if (cover.isEmpty()) "" else url(c, "getCoverArt", mapOf("id" to cover, "size" to "300")) ?: "",
            url(c, "stream", mapOf("id" to id)) ?: "", s.num("duration"))
    }

    private fun coll(c: Conf, a: JSONObject, playlist: Boolean): LibColl {
        val cover = a.str("coverArt")
        return LibColl(a.str("id"), a.str("name").ifEmpty { a.str("title") }, if (playlist) a.str("owner") else a.str("artist"),
            if (cover.isEmpty()) "" else url(c, "getCoverArt", mapOf("id" to cover, "size" to "300")) ?: "", a.num("songCount"), playlist)
    }

    /** type: newest | frequent | random | recent */
    suspend fun albums(c: Conf, type: String, size: Int = 16): Res<List<LibColl>> =
        when (val r = call(c, "getAlbumList2", mapOf("type" to type, "size" to "$size"))) {
            is Res.Ok -> Res.Ok(jsonList(r.v.optJSONObject("albumList2")?.opt("album")).map { coll(c, it, false) })
            is Res.Err -> r
        }

    suspend fun playlists(c: Conf): Res<List<LibColl>> = when (val r = call(c, "getPlaylists")) {
        is Res.Ok -> Res.Ok(jsonList(r.v.optJSONObject("playlists")?.opt("playlist")).map { coll(c, it, true) })
        is Res.Err -> r
    }

    suspend fun tracks(c: Conf, col: LibColl): List<LibItem> {
        if (col.playlist) {
            val r = call(c, "getPlaylist", mapOf("id" to col.id)) as? Res.Ok<JSONObject> ?: return emptyList()
            return jsonList(r.v.optJSONObject("playlist")?.opt("entry")).map { song(c, it) }
        }
        val r = call(c, "getAlbum", mapOf("id" to col.id)) as? Res.Ok<JSONObject> ?: return emptyList()
        return jsonList(r.v.optJSONObject("album")?.opt("song")).map { song(c, it) }
    }

    suspend fun search(c: Conf, q: String): List<LibItem> {
        val r = call(c, "search3", mapOf("query" to q, "songCount" to "30", "albumCount" to "0", "artistCount" to "0")) as? Res.Ok<JSONObject> ?: return emptyList()
        return jsonList(r.v.optJSONObject("searchResult3")?.opt("song")).map { song(c, it) }
    }
}

// MARK: - Plex Media Server (music libraries)

object PlexLib {
    data class Conf(val server: String, val token: String) {
        val ok: Boolean get() = server.isNotBlank() && token.isNotBlank()
    }

    private fun url(c: Conf, path: String, q: Map<String, String> = emptyMap()): String? {
        val u = Net.url(c.server, path) ?: return null
        return Net.withQuery(u, q.toSortedMap().map { it.key to it.value } + listOf("X-Plex-Token" to c.token.trim()))
    }

    private suspend fun get(c: Conf, path: String, q: Map<String, String> = emptyMap()): JSONObject? {
        val u = url(c, path, q) ?: return null
        val (d, code) = Net.data(u, timeout = 10.0, headers = mapOf("Accept" to "application/json", "X-Plex-Product" to "Skjold", "X-Plex-Client-Identifier" to "skjold-android")) ?: return null
        if (code != 200) return null
        return jsonObject(d)?.optJSONObject("MediaContainer")
    }

    fun thumb(c: Conf, path: String): String {
        if (path.isEmpty()) return ""
        return url(c, "/photo/:/transcode", mapOf("width" to "300", "height" to "300", "minSize" to "1", "url" to path)) ?: ""
    }

    /** Key of the first music library ("artist" section). */
    suspend fun musicSection(c: Conf): String? {
        val mc = get(c, "/library/sections") ?: return null
        return jsonList(mc.opt("Directory")).firstOrNull { it.str("type") == "artist" }?.str("key")
    }

    private fun track(c: Conf, t: JSONObject): LibItem {
        val part = jsonList(jsonList(t.opt("Media")).firstOrNull()?.opt("Part")).firstOrNull()?.str("key") ?: ""
        val artist = t.str("originalTitle").ifEmpty { t.str("grandparentTitle") }
        val th = t.str("parentThumb").ifEmpty { t.str("thumb") }
        return LibItem(t.str("ratingKey"), t.str("title"), artist, t.str("parentTitle"), thumb(c, th),
            if (part.isEmpty()) "" else url(c, part) ?: "", t.num("duration") / 1000)
    }

    /** sort: "addedAt:desc", "viewCount:desc", "random" */
    suspend fun albums(c: Conf, section: String, sort: String, size: Int = 16): List<LibColl>? {
        val mc = get(c, "/library/sections/$section/all", mapOf("type" to "9", "sort" to sort, "X-Plex-Container-Start" to "0", "X-Plex-Container-Size" to "$size")) ?: return null
        return jsonList(mc.opt("Metadata")).map {
            LibColl(it.str("ratingKey"), it.str("title"), it.str("parentTitle"), thumb(c, it.str("thumb")), it.num("leafCount"), false)
        }
    }

    suspend fun playlists(c: Conf): List<LibColl>? {
        val mc = get(c, "/playlists", mapOf("playlistType" to "audio")) ?: return null
        return jsonList(mc.opt("Metadata")).map {
            LibColl(it.str("ratingKey"), it.str("title"), "", thumb(c, it.str("composite").ifEmpty { it.str("thumb") }), it.num("leafCount"), true)
        }
    }

    suspend fun tracks(c: Conf, col: LibColl): List<LibItem> {
        val path = if (col.playlist) "/playlists/${col.id}/items" else "/library/metadata/${col.id}/children"
        val mc = get(c, path) ?: return emptyList()
        return jsonList(mc.opt("Metadata")).map { track(c, it) }
    }

    suspend fun search(c: Conf, section: String, q: String): List<LibItem> {
        val mc = get(c, "/library/sections/$section/search", mapOf("type" to "10", "query" to q)) ?: return emptyList()
        return jsonList(mc.opt("Metadata")).take(30).map { track(c, it) }
    }
}

// MARK: - GitHub Releases (skjold-v* in SebastianKristo/pult-forsterker)

object GitHubReleases {
    const val REPO = "SebastianKristo/pult-forsterker"
    const val PREFIX = "skjold-v"

    data class Rel(val tag: String, val name: String, val date: String, val notes: List<String>, val size: String, val pre: Boolean)

    /** Newest skjold-v* release (betas only when `includePre`). `Err` when GitHub could not be reached. */
    suspend fun latest(includePre: Boolean): Res<Rel?> {
        val (d, code) = Net.data("https://api.github.com/repos/$REPO/releases?per_page=30", timeout = 10.0,
            headers = mapOf("Accept" to "application/vnd.github+json", "User-Agent" to "Skjold-Android")) ?: return Res.Err("Fikk ikke kontakt med GitHub")
        val arr = try { JSONArray(String(d)) } catch (_: Exception) { null }
        if (code != 200 || arr == null) return Res.Err("GitHub svarte $code")
        for (r in jsonList(arr)) {
            val tag = r.str("tag_name")
            val pre = r.bool("prerelease")
            if (r.bool("draft") || !tag.startsWith(PREFIX) || (pre && !includePre)) continue
            val bytes = jsonList(r.opt("assets")).sumOf { it.num("size").toLong() }
            val bullet = Regex("""^[-*•]\s*""")
            val notes = r.str("body").lines().map { it.trim().replace(bullet, "") }.filter { it.isNotEmpty() && !it.startsWith("#") }
            val size = if (bytes > 0) String.format(java.util.Locale.US, "%.1f MB", bytes / 1_048_576.0).replace(".", ",") else ""
            val name = r.str("name")
            return Res.Ok(Rel(tag, name.ifEmpty { tag }, r.str("published_at").take(10), notes.take(6), size, pre))
        }
        return Res.Ok(null)
    }

    fun version(tag: String): String {
        var v = tag
        if (v.startsWith(PREFIX)) v = v.drop(PREFIX.length)
        if (v.startsWith("v")) v = v.drop(1)
        return v
    }

    /** > 0 when a is newer than b ("1.2.3", "2.0", "1.6.0-beta.1"). */
    fun cmp(a: String, b: String): Int {
        // først tallene foran «-»; er de like, er versjonen uten forhåndsmerke nyest (1.6.0 > 1.6.0-beta.1)
        val ca = version(a).substringBefore('-').split('.').map { it.toIntOrNull() ?: 0 }
        val cb = version(b).substringBefore('-').split('.').map { it.toIntOrNull() ?: 0 }
        for (i in 0 until maxOf(ca.size, cb.size)) {
            val d = ca.getOrElse(i) { 0 } - cb.getOrElse(i) { 0 }
            if (d != 0) return d
        }
        val prea = '-' in version(a)
        val preb = '-' in version(b)
        if (prea != preb) return if (prea) -1 else 1
        val pa = version(a).split('.', '-').map { it.toIntOrNull() }
        val pb = version(b).split('.', '-').map { it.toIntOrNull() }
        for (i in 0 until maxOf(pa.size, pb.size)) {
            val x = if (i < pa.size) pa[i] else 0
            val y = if (i < pb.size) pb[i] else 0
            if (x == null || y == null) continue
            if (x != y) return x - y
        }
        return 0
    }
}
