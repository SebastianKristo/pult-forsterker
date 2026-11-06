package no.kristo.skjold

import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Bundle
import androidx.annotation.OptIn
import androidx.media3.common.MediaItem
import androidx.media3.common.MediaMetadata
import androidx.media3.common.util.UnstableApi
import androidx.media3.session.LibraryResult
import androidx.media3.session.MediaLibraryService
import androidx.media3.session.MediaLibraryService.LibraryParams
import androidx.media3.session.MediaLibraryService.MediaLibrarySession
import androidx.media3.session.MediaSession
import com.google.common.collect.ImmutableList
import com.google.common.util.concurrent.Futures
import com.google.common.util.concurrent.ListenableFuture
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.serialization.builtins.ListSerializer
import org.json.JSONObject

/**
 * Media3 MediaLibraryService for Skjold:
 * - Mediekontroller i hurtigpanelet, på låseskjermen og i Samsungs Now Bar (Media3 lager MediaStyle-varselet og
 *   foreground-tjenesten selv via DefaultMediaNotificationProvider når spilleren spiller).
 * - Medibibliotek (Radiofavoritter, Nylig spilt, Rom) for systemets «Media»-liste, Android Auto-lignende klienter og
 *   gjenopptak (onPlaybackResumption).
 *
 * Plattform: gjenopptak («media resumption») vises av Android 11+ når appen er en MediaBrowserService (intent-filter i
 * manifestet) og har spilt nylig; Samsung One UI viser medieøkter i hurtigpanelet og i Now Bar (One UI 7+).
 * Tjenesten startes fra appen (WidgetStore.publish → onSnap) eller av systemet når en kontroller kobler til; Android 12+
 * tillater ikke å starte foreground-tjenester fra bakgrunnen ellers, så uten appen åpen oppdateres den bare når
 * systemet binder seg (gjenopptak) eller widgetene poller.
 */
@OptIn(UnstableApi::class)
class SkjoldMediaService : MediaLibraryService() {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    private var session: MediaLibrarySession? = null
    private var player: SkjoldPlayer? = null
    private var poller: Job? = null
    private var idleSince = 0L

    override fun onCreate() {
        super.onCreate()
        Store.init(this)
        val p = SkjoldPlayer(this)
        player = p
        val activity = PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        session = MediaLibrarySession.Builder(this, p, LibraryCallback()).setSessionActivity(activity).build()
        instance = this
        startPolling()
    }

    override fun onGetSession(controllerInfo: MediaSession.ControllerInfo): MediaLibrarySession? = session

    /** Uten appen åpen: hent status selv (hvert 3. s), og stopp etter 10 min uten avspilling. */
    private fun startPolling() {
        if (poller != null) return
        poller = scope.launch {
            while (isActive) {
                delay(3000)
                WidgetStore.poll(this@SkjoldMediaService)?.let { player?.update(it) }
                val playing = player?.current?.playing == true
                if (playing) idleSince = 0L
                else if (idleSince == 0L) idleSince = System.currentTimeMillis()
                else if (System.currentTimeMillis() - idleSince > 10 * 60_000L) { stopSelf(); break }
            }
        }
    }

    override fun onTaskRemoved(rootIntent: Intent?) {
        // Lyden spiller på Skjold, ikke i telefonen: la varselet stå mens det spiller, ellers stopp tjenesten.
        if (player?.current?.playing != true) stopSelf()
    }

    override fun onDestroy() {
        instance = null
        poller?.cancel()
        scope.cancel()
        session?.release()
        player?.release()
        session = null
        player = null
        super.onDestroy()
    }

    private inner class LibraryCallback : MediaLibrarySession.Callback {
        override fun onGetLibraryRoot(session: MediaLibrarySession, browser: MediaSession.ControllerInfo, params: LibraryParams?): ListenableFuture<LibraryResult<MediaItem>> {
            // Systemets gjenopptak spør etter en «recent»-rot: svar med Nylig spilt.
            if (params?.isRecent == true) return Futures.immediateFuture(LibraryResult.ofItem(SkjoldLibrary.folder(SkjoldLibrary.RECENT, "Nylig spilt"), params))
            return Futures.immediateFuture(LibraryResult.ofItem(SkjoldLibrary.folder(SkjoldLibrary.ROOT, "Skjold"), params))
        }

        override fun onGetChildren(session: MediaLibrarySession, browser: MediaSession.ControllerInfo, parentId: String, page: Int, pageSize: Int, params: LibraryParams?): ListenableFuture<LibraryResult<ImmutableList<MediaItem>>> {
            val all = SkjoldLibrary.children(this@SkjoldMediaService, parentId)
            val from = (page * pageSize).coerceAtLeast(0)
            val slice = if (pageSize <= 0 || from >= all.size) (if (page == 0) all else emptyList()) else all.subList(from, minOf(all.size, from + pageSize))
            return Futures.immediateFuture(LibraryResult.ofItemList(ImmutableList.copyOf(slice), params))
        }

        override fun onGetItem(session: MediaLibrarySession, browser: MediaSession.ControllerInfo, mediaId: String): ListenableFuture<LibraryResult<MediaItem>> {
            val item = SkjoldLibrary.find(this@SkjoldMediaService, mediaId)
                ?: return Futures.immediateFuture(LibraryResult.ofError(LibraryResult.RESULT_ERROR_BAD_VALUE))
            return Futures.immediateFuture(LibraryResult.ofItem(item, null))
        }

        /** Elementene trenger ingen URI: SkjoldPlayer spiller dem på enheten ut fra mediaId. */
        override fun onAddMediaItems(mediaSession: MediaSession, controller: MediaSession.ControllerInfo, mediaItems: MutableList<MediaItem>): ListenableFuture<MutableList<MediaItem>> {
            val resolved = mediaItems.map { SkjoldLibrary.find(this@SkjoldMediaService, it.mediaId) ?: it }.toMutableList()
            return Futures.immediateFuture(resolved)
        }

        /** Android/Samsung «gjenoppta avspilling»: siste element appen spilte. */
        override fun onPlaybackResumption(mediaSession: MediaSession, controller: MediaSession.ControllerInfo): ListenableFuture<MediaSession.MediaItemsWithStartPosition> {
            val last = SkjoldLibrary.last(this@SkjoldMediaService) ?: SkjoldLibrary.children(this@SkjoldMediaService, SkjoldLibrary.FAVS).firstOrNull()
            val items = if (last != null) listOf(last) else emptyList()
            return Futures.immediateFuture(MediaSession.MediaItemsWithStartPosition(items, 0, 0L))
        }
    }

    companion object {
        @Volatile private var instance: SkjoldMediaService? = null

        /** Ny status (fra appen, widgetene eller tjenestens egen polling). Start tjenesten når Skjold spiller. */
        fun onSnap(ctx: Context, s: WidgetSnap) {
            val inst = instance
            if (inst != null) { inst.player?.update(s); return }
            if (!s.playing) return
            try { ctx.startService(Intent(ctx, SkjoldMediaService::class.java)) }
            catch (_: Exception) { }   // IllegalStateException når appen er i bakgrunnen (Android 8+)
        }
    }
}

/** Mediebiblioteket: Radiofavoritter, Nylig spilt og Rom. Lagres i SharedPreferences for gjenopptak. */
object SkjoldLibrary {
    const val ROOT = "root"
    const val FAVS = "favs"
    const val RECENT = "recent"
    const val ROOMS = "rooms"
    private const val PREFS = "skjold-media"

    fun folder(id: String, title: String): MediaItem = MediaItem.Builder().setMediaId(id).setMediaMetadata(
        MediaMetadata.Builder().setTitle(title).setIsBrowsable(true).setIsPlayable(false)
            .setMediaType(MediaMetadata.MEDIA_TYPE_FOLDER_MIXED).build()).build()

    private fun playable(id: String, title: String, sub: String, type: Int, extras: Bundle? = null): MediaItem =
        MediaItem.Builder().setMediaId(id).setMediaMetadata(
            MediaMetadata.Builder().setTitle(title).setArtist(sub.ifEmpty { null }).setIsBrowsable(false).setIsPlayable(true)
                .setMediaType(type).apply { if (extras != null) setExtras(extras) }.build()).build()

    fun currentId(s: WidgetSnap): String = if (s.input == "radio" && s.preset > 0) "fav:${s.preset}" else "now:${s.host}"

    fun children(ctx: Context, parentId: String): List<MediaItem> {
        val s = WidgetStore.load(ctx)
        return when (parentId) {
            ROOT -> listOf(folder(FAVS, "Radiofavoritter"), folder(RECENT, "Nylig spilt"), folder(ROOMS, "Rom"))
            FAVS -> s.presets.map { (n, t) -> playable("fav:$n", t, "Radiofavoritt $n", MediaMetadata.MEDIA_TYPE_RADIO_STATION) }
            RECENT -> recent(ctx)
            ROOMS -> rooms(ctx).map { (h, name) -> playable("room:$h", name, "Spill på $name", MediaMetadata.MEDIA_TYPE_MIXED) }
            else -> emptyList()
        }
    }

    fun find(ctx: Context, id: String): MediaItem? = when {
        id == ROOT -> folder(ROOT, "Skjold")
        id == FAVS || id == RECENT || id == ROOMS -> children(ctx, ROOT).firstOrNull { it.mediaId == id }
        else -> (children(ctx, FAVS) + recent(ctx) + children(ctx, ROOMS)).firstOrNull { it.mediaId == id }
    }

    private fun rooms(ctx: Context): List<Pair<String, String>> {
        Store.init(ctx)
        val known = try { Store.load("skjold-known", ListSerializer(KnownDevice.serializer())) } catch (_: Exception) { null } ?: emptyList()
        return (known.map { it.host to it.name.ifEmpty { it.host } } + SkjoldRoutes.found.map { it.host to it.name })
            .distinctBy { it.first }
    }

    /** Spill et element på den aktive enheten (eller bytt enhet for «room:»). */
    suspend fun play(ctx: Context, item: MediaItem) {
        val id = item.mediaId
        when {
            id.startsWith("fav:") -> id.removePrefix("fav:").toIntOrNull()?.let { WidgetStore.command(ctx, "/api/preset", mapOf("n" to it)) }
            id.startsWith("url:") -> WidgetStore.command(ctx, "/api/radio/play", mapOf("url" to id.removePrefix("url:"), "title" to (item.mediaMetadata.title?.toString() ?: "")))
            id.startsWith("room:") -> SkjoldRoutes.select(ctx, id.removePrefix("room:"))
        }
    }

    fun remember(ctx: Context, item: MediaItem) {
        val id = item.mediaId
        if (!(id.startsWith("fav:") || id.startsWith("url:"))) return
        val title = item.mediaMetadata.title?.toString() ?: find(ctx, id)?.mediaMetadata?.title?.toString() ?: id
        val p = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val list = (listOf(JSONObject().put("id", id).put("t", title)) + recentRaw(ctx).filter { it.optString("id") != id }).take(12)
        p.edit().putString("recent", org.json.JSONArray(list).toString()).apply()
    }

    private fun recentRaw(ctx: Context): List<JSONObject> = try {
        val a = org.json.JSONArray(ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString("recent", "[]"))
        (0 until a.length()).mapNotNull { a.optJSONObject(it) }
    } catch (_: Exception) { emptyList() }

    private fun recent(ctx: Context): List<MediaItem> = recentRaw(ctx).map {
        playable(it.optString("id"), it.optString("t"), "Nylig spilt", MediaMetadata.MEDIA_TYPE_RADIO_STATION)
    }

    fun last(ctx: Context): MediaItem? = recent(ctx).firstOrNull()
}
