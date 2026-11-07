package no.kristo.skjold.wear

import android.content.Context
import android.util.Base64
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import com.google.android.gms.wearable.DataClient
import com.google.android.gms.wearable.DataEvent
import com.google.android.gms.wearable.DataEventBuffer
import com.google.android.gms.wearable.DataMapItem
import com.google.android.gms.wearable.MessageClient
import com.google.android.gms.wearable.MessageEvent
import com.google.android.gms.wearable.Wearable
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.TimeUnit

data class Room(val host: String, val name: String, val product: String)
data class Fav(val n: Int, val title: String, val logo: String)

data class Status(
    val name: String = "", val title: String = "", val artist: String = "", val art: String = "",
    val power: Boolean = true, val playing: Boolean = false, val mute: Boolean = false,
    val volume: Int = 0, val preset: Int = 0, val favs: List<Fav> = emptyList(),
) {
    companion object {
        fun parse(b: ByteArray): Status? = try {
            val j = JSONObject(String(b))
            if (!j.has("volume")) null else {
                var title = j.optString("title"); var artist = j.optString("artist")
                var art = j.optString("cover_url").ifEmpty { j.optString("cover").takeIf { it.isNotEmpty() }?.let { "/api/cover?v=$it" } ?: "" }
                j.optJSONObject("radio_now")?.let { r ->
                    if (title.isEmpty()) title = r.optString("name")
                    if (artist.isEmpty()) artist = r.optString("now")
                    if (art.isEmpty()) art = r.optString("logo")
                }
                val favs = mutableListOf<Fav>()
                j.optJSONArray("presets")?.let { a ->
                    for (i in 0 until a.length()) {
                        val p = a.optJSONObject(i) ?: continue
                        val t = p.optString("title")
                        if (t.isNotEmpty()) favs.add(Fav(p.optInt("n"), t, p.optString("logo")))
                    }
                }
                Status(j.optString("name"), title, artist, art, if (j.has("power")) j.optBoolean("power") else true,
                    j.optBoolean("playing"), j.optBoolean("mute"), j.optInt("volume"), j.optInt("preset"), favs)
            }
        } catch (_: Exception) { null }
    }
}

/**
 * Klokkas tilstand. Snakker direkte med Skjold over Wi-Fi; når klokka ikke når Skjold, går kallet via telefonen
 * (MessageClient «/skjold/kall» → telefonens WearCallService → svar «/skjold/svar»). Romlista kommer fra telefonappen.
 */
object WearStore : DataClient.OnDataChangedListener, MessageClient.OnMessageReceivedListener {
    var rooms by mutableStateOf<List<Room>>(emptyList())
    var host by mutableStateOf("")
    var status by mutableStateOf(Status())
    var reachable by mutableStateOf(true)
    var viaPhone by mutableStateOf(false)

    private lateinit var app: Context
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    private var poll: Job? = null
    private val pending = ConcurrentHashMap<String, CompletableDeferred<ByteArray?>>()
    private val http = OkHttpClient.Builder().connectTimeout(3, TimeUnit.SECONDS).readTimeout(5, TimeUnit.SECONDS)
        .callTimeout(6, TimeUnit.SECONDS).retryOnConnectionFailure(false).build()
    private val prefs get() = app.getSharedPreferences("skjold-wear", Context.MODE_PRIVATE)

    fun start(ctx: Context) {
        app = ctx.applicationContext
        host = prefs.getString("host", "") ?: ""
        applyRooms(prefs.getString("rom", "[]") ?: "[]", "")
        Wearable.getDataClient(app).addListener(this)
        Wearable.getMessageClient(app).addListener(this)
        scope.launch {
            try {
                val items = Wearable.getDataClient(app).dataItems.await()
                for (it in items) if (it.uri.path == "/skjold/rom") {
                    val m = DataMapItem.fromDataItem(it).dataMap
                    applyRooms(m.getString("rom") ?: "[]", m.getString("aktiv") ?: "")
                }
                items.release()
            } catch (_: Exception) { }
        }
        poll?.cancel()
        poll = scope.launch {
            while (isActive) { refresh(); delay(3000) }
        }
    }

    fun stop() {
        poll?.cancel()
        try {
            Wearable.getDataClient(app).removeListener(this)
            Wearable.getMessageClient(app).removeListener(this)
        } catch (_: Exception) { }
    }

    val roomName: String get() = rooms.firstOrNull { it.host == host }?.name ?: status.name.ifEmpty { "Skjold" }

    fun imageUrl(s: String): String? = when {
        s.isEmpty() -> null
        s.lowercase().startsWith("http") -> s
        host.isEmpty() -> null
        else -> base(host) + s
    }

    private fun base(h: String): String {
        var b = h.trim()
        if (!b.lowercase().startsWith("http")) b = "http://$b"
        return b.trimEnd('/')
    }

    private fun applyRooms(json: String, aktiv: String) {
        val list = mutableListOf<Room>()
        try {
            val a = JSONArray(json)
            for (i in 0 until a.length()) {
                val r = a.optJSONObject(i) ?: continue
                val h = r.optString("host")
                if (h.isNotEmpty()) list.add(Room(h, r.optString("name", h), r.optString("product")))
            }
        } catch (_: Exception) { }
        rooms = list
        prefs.edit().putString("rom", json).apply()
        if (host.isEmpty() || list.none { it.host == host }) {
            selectHost(aktiv.ifEmpty { list.firstOrNull()?.host ?: "" })
        }
    }

    private fun selectHost(h: String) {
        host = h
        prefs.edit().putString("host", h).apply()
        status = Status()
        scope.launch { refresh() }
    }

    fun select(r: Room) = selectHost(r.host)

    suspend fun refresh() {
        if (host.isEmpty()) return
        val d = call("/api/status", "GET", null)
        val st = d?.let { Status.parse(it) }
        if (st != null) { status = st; reachable = true } else reachable = false
    }

    fun setVolume(v: Int) {
        val n = v.coerceIn(0, 100)
        status = status.copy(volume = n)
        scope.launch { call("/api/volume", "POST", JSONObject().put("volume", n).toString()) }
    }

    fun transport(a: String) {
        if (a == "playpause") status = status.copy(playing = !status.playing)
        scope.launch { call("/api/transport", "POST", JSONObject().put("action", a).toString()); refresh() }
    }

    fun power(on: Boolean) {
        status = status.copy(power = on)
        scope.launch { call("/api/power", "POST", JSONObject().put("on", on).toString()); refresh() }
    }

    fun playFav(n: Int) {
        status = status.copy(preset = n)
        scope.launch { call("/api/preset", "POST", JSONObject().put("n", n).toString()); refresh() }
    }

    /** Direkte HTTP mot Skjold; feiler det, går kallet via telefonen. */
    private suspend fun call(path: String, method: String, body: String?): ByteArray? {
        val h = host
        if (h.isEmpty()) return null
        val direct = withContext(Dispatchers.IO) {
            try {
                val rb = (body ?: if (method == "POST") "" else null)?.toByteArray()?.toRequestBody("application/json".toMediaType())
                val req = Request.Builder().url(base(h) + path).method(method, rb).header("Cache-Control", "no-cache").build()
                http.newCall(req).execute().use { r -> if (r.code < 300) r.body?.bytes() else null }
            } catch (_: Exception) { null }
        }
        if (direct != null) { viaPhone = false; return direct }
        val p = viaPhoneCall(h, path, method, body)
        if (p != null) viaPhone = true
        return p
    }

    private suspend fun viaPhoneCall(h: String, path: String, method: String, body: String?): ByteArray? = try {
        val nodes = Wearable.getNodeClient(app).connectedNodes.await()
        val node = nodes.firstOrNull { it.isNearby } ?: nodes.firstOrNull()
        if (node == null) null else {
            val id = UUID.randomUUID().toString()
            val wait = CompletableDeferred<ByteArray?>()
            pending[id] = wait
            val msg = JSONObject().put("id", id).put("host", h).put("path", path).put("method", method)
            if (body != null) msg.put("body", body)
            Wearable.getMessageClient(app).sendMessage(node.id, "/skjold/kall", msg.toString().toByteArray()).await()
            val r = withTimeoutOrNull(8000) { wait.await() }
            pending.remove(id)
            r?.takeIf { it.isNotEmpty() }
        }
    } catch (_: Exception) { null }

    override fun onMessageReceived(event: MessageEvent) {
        if (event.path != "/skjold/svar") return
        try {
            val j = JSONObject(String(event.data))
            val d = Base64.decode(j.optString("data"), Base64.DEFAULT)
            pending[j.optString("id")]?.complete(d)
        } catch (_: Exception) { }
    }

    override fun onDataChanged(events: DataEventBuffer) {
        for (e in events) {
            if (e.type == DataEvent.TYPE_CHANGED && e.dataItem.uri.path == "/skjold/rom") {
                val m = DataMapItem.fromDataItem(e.dataItem).dataMap
                val rom = m.getString("rom") ?: "[]"
                val aktiv = m.getString("aktiv") ?: ""
                scope.launch { applyRooms(rom, aktiv) }
            }
        }
    }
}
