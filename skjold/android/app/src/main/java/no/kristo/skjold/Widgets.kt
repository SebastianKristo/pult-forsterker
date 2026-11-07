package no.kristo.skjold

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.DpSize
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.glance.GlanceId
import androidx.glance.GlanceModifier
import androidx.glance.Image
import androidx.glance.ImageProvider
import androidx.glance.LocalSize
import androidx.glance.action.ActionParameters
import androidx.glance.action.actionParametersOf
import androidx.glance.action.actionStartActivity
import androidx.glance.action.clickable
import androidx.glance.appwidget.GlanceAppWidget
import androidx.glance.appwidget.GlanceAppWidgetReceiver
import androidx.glance.appwidget.SizeMode
import androidx.glance.appwidget.action.ActionCallback
import androidx.glance.appwidget.action.actionRunCallback
import androidx.glance.appwidget.cornerRadius
import androidx.glance.appwidget.provideContent
import androidx.glance.appwidget.updateAll
import androidx.glance.background
import androidx.glance.layout.Alignment
import androidx.glance.layout.Box
import androidx.glance.layout.Column
import androidx.glance.layout.ContentScale
import androidx.glance.layout.Row
import androidx.glance.layout.Spacer
import androidx.glance.layout.fillMaxSize
import androidx.glance.layout.fillMaxWidth
import androidx.glance.layout.height
import androidx.glance.layout.padding
import androidx.glance.layout.size
import androidx.glance.layout.width
import androidx.glance.text.FontWeight
import androidx.glance.text.Text
import androidx.glance.text.TextStyle
import androidx.glance.unit.ColorProvider
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.concurrent.TimeUnit

// MARK: - Snapshot shared by the widgets, the media notification and the app

/** What the widgets show. Written by the app (AppModel.apply), the widget actions, the worker and the media service. */
data class WidgetSnap(
    val host: String = "", val room: String = "", val title: String = "", val sub: String = "", val input: String = "",
    val playing: Boolean = false, val power: Boolean = true, val volume: Int = 0, val cover: String = "",
    val presets: List<Pair<Int, String>> = emptyList(), val preset: Int = 0,
    // for Media3-spilleren (hurtigpanel/låseskjerm): album, demping, varighet og posisjon i sekunder, direktesending
    val album: String = "", val mute: Boolean = false, val duration: Int = 0, val position: Int = 0, val live: Boolean = false,
)

object WidgetStore {
    private const val PREFS = "skjold-widget"
    private const val COVER_FILE = "widget_cover.img"
    private const val COVER_KEY_FILE = "widget_cover.key"   // hvilken adresse bildet i COVER_FILE kom fra
    private var lastKey = ""
    private var lastCover = ""

    fun load(ctx: Context): WidgetSnap {
        val s = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString("snap", null) ?: return WidgetSnap(host = Store.string("skjold-host") ?: "")
        return try {
            val j = JSONObject(s)
            val pa = j.optJSONArray("presets") ?: JSONArray()
            val presets = (0 until pa.length()).mapNotNull { i -> pa.optJSONObject(i)?.let { it.optInt("n") to it.optString("t") } }
            WidgetSnap(
                j.optString("host"), j.optString("room"), j.optString("title"), j.optString("sub"), j.optString("input"),
                j.optBoolean("playing"), j.optBoolean("power", true), j.optInt("volume"), j.optString("cover"), presets, j.optInt("preset"),
                j.optString("album"), j.optBoolean("mute"), j.optInt("duration"), j.optInt("position"), j.optBoolean("live"),
            )
        } catch (_: Exception) { WidgetSnap() }
    }

    private fun save(ctx: Context, s: WidgetSnap) {
        val pa = JSONArray()
        s.presets.forEach { (n, t) -> pa.put(JSONObject().put("n", n).put("t", t)) }
        val j = JSONObject().put("host", s.host).put("room", s.room).put("title", s.title).put("sub", s.sub).put("input", s.input)
            .put("playing", s.playing).put("power", s.power).put("volume", s.volume).put("cover", s.cover).put("presets", pa).put("preset", s.preset)
            .put("album", s.album).put("mute", s.mute).put("duration", s.duration).put("position", s.position).put("live", s.live)
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString("snap", j.toString()).apply()
    }

    /** Ny aktiv enhet valgt utenfor appen (medieutgang/bibliotek). */
    fun setHost(ctx: Context, host: String) { save(ctx, load(ctx).copy(host = host)); lastKey = "" }

    fun coverBytes(ctx: Context): ByteArray? = try {
        val f = File(ctx.filesDir, COVER_FILE)
        if (f.exists()) f.readBytes() else null
    } catch (_: Exception) { null }

    /** Bildet bare hvis det faktisk hører til [url] (ellers fikk varselet forrige låts omslag). */
    fun coverBytes(ctx: Context, url: String): ByteArray? =
        if (url.isNotEmpty() && coverKey(ctx) == url) coverBytes(ctx) else null

    private fun coverKey(ctx: Context): String = try {
        val f = File(ctx.filesDir, COVER_KEY_FILE)
        if (f.exists()) f.readText() else ""
    } catch (_: Exception) { "" }

    fun coverBitmap(ctx: Context, url: String): Bitmap? = try {
        val f = File(ctx.filesDir, COVER_FILE)
        if (url.isEmpty() || coverKey(ctx) != url) null else
        if (f.exists()) BitmapFactory.decodeFile(f.absolutePath) else null
    } catch (_: Exception) { null }

    fun snapOf(st: DevStatus, host: String): WidgetSnap {
        val rn = st.radioNow
        val inputName = INPUT_NAMES[st.input] ?: st.input.replaceFirstChar { it.uppercase() }
        val title = when {
            st.input == "radio" && st.title.isEmpty() -> rn?.name ?: "Radio"
            st.title.isNotEmpty() -> st.title
            else -> inputName
        }
        val sub = listOf(st.artist, if (st.input == "radio") rn?.name ?: "" else inputName)
            .filter { it.isNotEmpty() && it != title }.distinct().joinToString(" · ").ifEmpty { inputName }
        val cover = DeviceLink.coverURL(st.coverURL, host).ifEmpty { rn?.let { if (it.logo.isNotEmpty()) DeviceLink.coverURL(it.logo, host) else it.image.takeUnless { im -> "html/images/" in im } } ?: "" }   // Lyrions standardmast er ikke en logo
        val presets = st.presetTitles.mapIndexedNotNull { i, t -> if (t.isNotEmpty()) (i + 1) to t else null }
        return WidgetSnap(host, st.name, title, sub, st.input, st.playing && st.power, st.power, st.volume, cover, presets, st.preset,
            st.album, st.mute, st.duration, st.position, st.input == "radio" && st.duration <= 0)
    }

    /** Save a new status and refresh widgets + notification, but only when something visible changed. */
    suspend fun publish(ctx: Context, st: DevStatus, host: String) {
        val s = snapOf(st, host)
        SkjoldMediaService.onSnap(ctx, s)   // Media3-spilleren får alle endringer (også posisjon)
        val key = listOf(s.host, s.room, s.title, s.sub, s.playing, s.power, s.volume, s.cover, s.preset, s.presets.size).joinToString("|")
        if (key == lastKey) return
        lastKey = key
        save(ctx, s)
        if (s.cover != lastCover) {
            lastCover = s.cover
            if (s.cover.isEmpty() || coverKey(ctx) != s.cover) fetchCover(ctx, s.cover)
        }
        refresh(ctx)
        SkjoldMediaService.onSnap(ctx, s)   // nytt omslag lastet ned
    }

    private suspend fun fetchCover(ctx: Context, url: String) = withContext(Dispatchers.IO) {
        val f = File(ctx.filesDir, COVER_FILE)
        val k = File(ctx.filesDir, COVER_KEY_FILE)
        if (url.isEmpty()) { f.delete(); k.delete(); return@withContext }
        // samme klient som resten av appen (relé/fjernstyring og samme opphav som API-et)
        val r = Net.data(url, timeout = 8.0)
        val small = if (r != null && r.second < 300 && r.first.isNotEmpty()) shrink(r.first) else null
        if (small != null) { f.writeBytes(small); k.writeText(url) }
        else { f.delete(); k.delete() }
    }

    /** Ned til maks 512 px JPEG: lite nok for varsel, låseskjerm, Now Bar og widgets. */
    private fun shrink(bytes: ByteArray): ByteArray? = try {
        val src = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
        if (src == null) null else {
            val max = 512
            val scale = minOf(1f, max.toFloat() / maxOf(src.width, src.height))
            val bmp = if (scale < 1f) Bitmap.createScaledBitmap(src, (src.width * scale).toInt().coerceAtLeast(1), (src.height * scale).toInt().coerceAtLeast(1), true) else src
            val out = java.io.ByteArrayOutputStream()
            bmp.compress(Bitmap.CompressFormat.JPEG, 88, out)
            out.toByteArray()
        }
    } catch (_: Exception) { null }


    suspend fun refresh(ctx: Context) {
        try { NowPlayingWidget().updateAll(ctx) } catch (_: Exception) { }
        try { FavoritesWidget().updateAll(ctx) } catch (_: Exception) { }
    }

    /** Fetch the status from the last known device and publish it (widget actions, worker, media service). */
    suspend fun poll(ctx: Context): WidgetSnap? {
        Store.init(ctx)
        val host = load(ctx).host.ifEmpty { Store.string("skjold-host") ?: "" }
        if (host.isEmpty()) return null
        val st = DeviceLink.status(host, 5.0) ?: return null
        publish(ctx, st, host)
        return snapOf(st, host)
    }

    /** Send a command to the last known device, then refresh. */
    suspend fun command(ctx: Context, path: String, body: Map<String, Any?>) {
        Store.init(ctx)
        val host = load(ctx).host.ifEmpty { Store.string("skjold-host") ?: "" }
        if (host.isEmpty()) return
        DeviceLink.send(path, body, on = host)
        poll(ctx)
    }

    fun schedule(ctx: Context) {
        try {
            WorkManager.getInstance(ctx).enqueueUniquePeriodicWork(
                "skjold-widgets", ExistingPeriodicWorkPolicy.KEEP,
                PeriodicWorkRequestBuilder<WidgetWorker>(15, TimeUnit.MINUTES).build(),
            )
        } catch (_: Exception) { }
    }

    private val INPUT_NAMES = mapOf(
        "airplay" to "AirPlay", "bt" to "Blåtann", "radio" to "Radio", "aux" to "AUX", "aux2" to "AUX 2",
        "usb" to "USB", "spotify" to "Spotify", "plex" to "Plex", "upnp" to "UPnP/DLNA",
    )
}

class WidgetWorker(ctx: Context, params: WorkerParameters) : CoroutineWorker(ctx, params) {
    override suspend fun doWork(): Result {
        WidgetStore.poll(applicationContext)
        return Result.success()
    }
}

// MARK: - Actions

private val KEY_ACT = ActionParameters.Key<String>("act")
private val KEY_N = ActionParameters.Key<Int>("n")
private val KEY_DV = ActionParameters.Key<Int>("dv")

class TransportAction : ActionCallback {
    override suspend fun onAction(context: Context, glanceId: GlanceId, parameters: ActionParameters) {
        WidgetStore.command(context, "/api/transport", mapOf("action" to (parameters[KEY_ACT] ?: "playpause")))
    }
}

class VolumeAction : ActionCallback {
    override suspend fun onAction(context: Context, glanceId: GlanceId, parameters: ActionParameters) {
        val v = (WidgetStore.load(context).volume + (parameters[KEY_DV] ?: 0)).coerceIn(0, 100)
        WidgetStore.command(context, "/api/volume", mapOf("volume" to v))
    }
}

class PresetAction : ActionCallback {
    override suspend fun onAction(context: Context, glanceId: GlanceId, parameters: ActionParameters) {
        WidgetStore.command(context, "/api/preset", mapOf("n" to (parameters[KEY_N] ?: 1)))
    }
}

class RefreshAction : ActionCallback {
    override suspend fun onAction(context: Context, glanceId: GlanceId, parameters: ActionParameters) {
        WidgetStore.poll(context)
    }
}

// MARK: - Look (same tokens as the app: dark surface, gold accent)

private val W_BG = Color(0xFF141415)
private val W_CARD = Color(0xFF1F1F21)
private val W_TEXT = Color(0xFFF2F2EE)
private val W_MUTED = Color(0xFF8B8B86)
private val W_GOLD = Color(0xFFF0C46A)
private val W_INK = Color(0xFF0B0B0C)

private fun cp(c: Color) = ColorProvider(c)

@Composable
private fun RoundBtn(label: String, action: androidx.glance.action.Action, big: Boolean = false) {
    val s = if (big) 44.dp else 36.dp
    Box(
        modifier = GlanceModifier.size(s).cornerRadius(s / 2).background(if (big) W_TEXT else W_CARD).clickable(action),
        contentAlignment = Alignment.Center,
    ) {
        Text(label, style = TextStyle(color = cp(if (big) W_INK else W_TEXT), fontSize = if (big) 18.sp else 15.sp, fontWeight = FontWeight.Bold))
    }
}

// MARK: - «Spiller nå» (2×2 og 4×2)

class NowPlayingWidget : GlanceAppWidget() {
    override val sizeMode = SizeMode.Responsive(setOf(DpSize(110.dp, 110.dp), DpSize(250.dp, 110.dp)))

    override suspend fun provideGlance(context: Context, id: GlanceId) {
        Store.init(context)
        val s = WidgetStore.load(context)
        val bmp = WidgetStore.coverBitmap(context, s.cover)
        provideContent { NowPlaying(s, bmp) }
    }

    @Composable
    private fun NowPlaying(s: WidgetSnap, bmp: Bitmap?) {
        val wide = LocalSize.current.width >= 220.dp
        val open = actionStartActivity<MainActivity>()
        val pp = actionRunCallback<TransportAction>(actionParametersOf(KEY_ACT to "playpause"))
        val next = actionRunCallback<TransportAction>(actionParametersOf(KEY_ACT to "next"))
        val vDown = actionRunCallback<VolumeAction>(actionParametersOf(KEY_DV to -4))
        val vUp = actionRunCallback<VolumeAction>(actionParametersOf(KEY_DV to 4))
        Box(GlanceModifier.fillMaxSize().cornerRadius(22.dp).background(W_BG).padding(12.dp)) {
            if (s.host.isEmpty()) {
                Column(GlanceModifier.fillMaxSize().clickable(open), verticalAlignment = Alignment.CenterVertically) {
                    Text("Skjold", style = TextStyle(color = cp(W_GOLD), fontSize = 15.sp, fontWeight = FontWeight.Bold))
                    Text("Åpne appen og velg en enhet", style = TextStyle(color = cp(W_MUTED), fontSize = 12.sp))
                }
            } else if (wide) {
                Row(GlanceModifier.fillMaxSize(), verticalAlignment = Alignment.CenterVertically) {
                    Cover(bmp, 86, open)
                    Spacer(GlanceModifier.width(12.dp))
                    Column(GlanceModifier.defaultWeight()) {
                        Texts(s, open)
                        Spacer(GlanceModifier.height(10.dp))
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            RoundBtn("−", vDown)
                            Spacer(GlanceModifier.width(6.dp))
                            RoundBtn(if (s.playing) "❚❚" else "▶", pp, big = true)
                            Spacer(GlanceModifier.width(6.dp))
                            RoundBtn("⏭", next)
                            Spacer(GlanceModifier.width(6.dp))
                            RoundBtn("+", vUp)
                            Spacer(GlanceModifier.width(8.dp))
                            Text("${s.volume}", style = TextStyle(color = cp(W_GOLD), fontSize = 14.sp, fontWeight = FontWeight.Bold))
                        }
                    }
                }
            } else {
                Column(GlanceModifier.fillMaxSize()) {
                    Row(GlanceModifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                        Cover(bmp, 44, open)
                        Spacer(GlanceModifier.defaultWeight())
                        RoundBtn(if (s.playing) "❚❚" else "▶", pp, big = true)
                    }
                    Spacer(GlanceModifier.defaultWeight())
                    Texts(s, open)
                }
            }
        }
    }

    @Composable
    private fun Cover(bmp: Bitmap?, size: Int, open: androidx.glance.action.Action) {
        val m = GlanceModifier.size(size.dp).cornerRadius(12.dp).clickable(open)
        if (bmp != null) Image(ImageProvider(bmp), contentDescription = "Omslag", modifier = m, contentScale = ContentScale.Crop)
        else Box(m.background(Color(0xFF2A2112)), contentAlignment = Alignment.Center) {
            Text("♪", style = TextStyle(color = cp(W_GOLD), fontSize = (size / 2.4).sp))
        }
    }

    @Composable
    private fun Texts(s: WidgetSnap, open: androidx.glance.action.Action) {
        Column(GlanceModifier.clickable(open)) {
            Text(s.room.uppercase().ifEmpty { "SKJOLD" }, style = TextStyle(color = cp(W_MUTED), fontSize = 10.sp), maxLines = 1)
            Text(if (s.power) s.title else "Standby", style = TextStyle(color = cp(W_TEXT), fontSize = 15.sp, fontWeight = FontWeight.Bold), maxLines = 1)
            Text(s.sub, style = TextStyle(color = cp(W_MUTED), fontSize = 12.sp), maxLines = 1)
        }
    }
}

class NowPlayingReceiver : GlanceAppWidgetReceiver() {
    override val glanceAppWidget: GlanceAppWidget = NowPlayingWidget()
}

// MARK: - «Radiofavoritter» (4×2 / 4×3)

class FavoritesWidget : GlanceAppWidget() {
    override val sizeMode = SizeMode.Responsive(setOf(DpSize(250.dp, 110.dp), DpSize(250.dp, 180.dp)))

    override suspend fun provideGlance(context: Context, id: GlanceId) {
        Store.init(context)
        val s = WidgetStore.load(context)
        provideContent { Favorites(s) }
    }

    @Composable
    private fun Favorites(s: WidgetSnap) {
        val tall = LocalSize.current.height >= 170.dp
        val perRow = 3
        val rows = if (tall) 3 else 2
        val items = s.presets.take(perRow * rows)
        Column(GlanceModifier.fillMaxSize().cornerRadius(22.dp).background(W_BG).padding(12.dp)) {
            Row(GlanceModifier.fillMaxWidth().clickable(actionRunCallback<RefreshAction>()), verticalAlignment = Alignment.CenterVertically) {
                Text("RADIOFAVORITTER", style = TextStyle(color = cp(W_GOLD), fontSize = 10.sp, fontWeight = FontWeight.Bold), modifier = GlanceModifier.defaultWeight())
                Text(s.room, style = TextStyle(color = cp(W_MUTED), fontSize = 11.sp), maxLines = 1)
            }
            Spacer(GlanceModifier.height(8.dp))
            if (items.isEmpty()) {
                Text("Ingen favoritter ennå. Legg dem til i appen.", style = TextStyle(color = cp(W_MUTED), fontSize = 12.sp),
                    modifier = GlanceModifier.clickable(actionStartActivity<MainActivity>()))
            }
            items.chunked(perRow).forEachIndexed { ri, row ->
                if (ri > 0) Spacer(GlanceModifier.height(6.dp))
                Row(GlanceModifier.fillMaxWidth().defaultWeight()) {
                    row.forEachIndexed { ci, (n, t) ->
                        if (ci > 0) Spacer(GlanceModifier.width(6.dp))
                        val on = s.input == "radio" && s.preset == n
                        Column(
                            GlanceModifier.defaultWeight().fillMaxSize().cornerRadius(12.dp).background(if (on) Color(0xFF2A2112) else W_CARD).padding(8.dp)
                                .clickable(actionRunCallback<PresetAction>(actionParametersOf(KEY_N to n))),
                        ) {
                            Text("$n", style = TextStyle(color = cp(if (on) W_GOLD else W_MUTED), fontSize = 10.sp))
                            Spacer(GlanceModifier.defaultWeight())
                            Text(t, style = TextStyle(color = cp(if (on) W_GOLD else W_TEXT), fontSize = 12.sp, fontWeight = FontWeight.Bold), maxLines = 2)
                        }
                    }
                    repeat(perRow - row.size) { Spacer(GlanceModifier.width(6.dp)); Spacer(GlanceModifier.defaultWeight()) }
                }
            }
        }
    }
}

class FavoritesReceiver : GlanceAppWidgetReceiver() {
    override val glanceAppWidget: GlanceAppWidget = FavoritesWidget()
}
