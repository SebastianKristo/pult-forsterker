package no.kristo.skjold

import android.content.Context
import android.net.Uri
import android.os.Looper
import android.os.SystemClock
import androidx.annotation.OptIn
import androidx.media3.common.C
import androidx.media3.common.DeviceInfo
import androidx.media3.common.MediaItem
import androidx.media3.common.MediaMetadata
import androidx.media3.common.Player
import androidx.media3.common.SimpleBasePlayer
import androidx.media3.common.util.UnstableApi
import com.google.common.util.concurrent.Futures
import com.google.common.util.concurrent.ListenableFuture
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch

/**
 * Media3-spiller som speiler en Skjold-enhet. Lyden spilles på enheten, ikke i telefonen, så i stedet for ExoPlayer
 * sender denne spilleren kommandoer til daemonens API (via WidgetStore/DeviceLink) og bygger tilstanden fra
 * /api/status (+ /api/events når appen er åpen, som publiserer gjennom WidgetStore.publish → SkjoldMediaService.onSnap).
 *
 * - DeviceInfo PLAYBACK_TYPE_REMOTE 0–100: Media3 setter fjernvolum på den systemsynlige mediesesjonen, så
 *   volumknappene på telefonen styrer Skjold mens økten er aktiv.
 * - Spillelisten har alltid tre elementer [forrige-plassholder, nå, neste-plassholder]. Det gjør at «neste»/«forrige»
 *   alltid er tilgjengelige i systemets mediekontroller; valget sendes som /api/transport, og indeksen settes tilbake
 *   til 1 ved neste statusoppdatering. (Skjold har ingen kø-API mot telefonen.)
 * - Radio er direktesending: isLive + dynamisk, ingen spoling. Låter med varighet (Navidrome, YouTube Music, Plex …)
 *   kan spoles fra varselet og låseskjermen (POST /api/seek).
 */
@OptIn(UnstableApi::class)
class SkjoldPlayer(private val ctx: Context) : SimpleBasePlayer(Looper.getMainLooper()) {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    private var snap: WidgetSnap = WidgetStore.load(ctx)
    private var cover: ByteArray? = WidgetStore.coverBytes(ctx, snap.cover)
    private var coverKey = snap.cover
    private var posAtMs = SystemClock.elapsedRealtime()

    /** Ny status fra enheten. */
    fun update(s: WidgetSnap) {
        // bare bildet som hører til denne adressen: første kall kommer før omslaget er lastet ned, det andre etter
        if (s.cover != coverKey) { coverKey = s.cover; cover = WidgetStore.coverBytes(ctx, s.cover) }
        else if (cover == null && s.cover.isNotEmpty()) cover = WidgetStore.coverBytes(ctx, s.cover)
        snap = s
        posAtMs = SystemClock.elapsedRealtime()
        invalidateState()
    }

    val current: WidgetSnap get() = snap

    private val commands: Player.Commands = Player.Commands.Builder().addAll(
        Player.COMMAND_PLAY_PAUSE, Player.COMMAND_PREPARE, Player.COMMAND_STOP,
        Player.COMMAND_SEEK_TO_NEXT, Player.COMMAND_SEEK_TO_PREVIOUS, Player.COMMAND_SEEK_IN_CURRENT_MEDIA_ITEM,
        Player.COMMAND_SEEK_TO_NEXT_MEDIA_ITEM, Player.COMMAND_SEEK_TO_PREVIOUS_MEDIA_ITEM,
        Player.COMMAND_GET_CURRENT_MEDIA_ITEM, Player.COMMAND_GET_TIMELINE, Player.COMMAND_GET_METADATA,
        Player.COMMAND_SET_MEDIA_ITEM, Player.COMMAND_CHANGE_MEDIA_ITEMS,
        Player.COMMAND_GET_DEVICE_VOLUME,
        Player.COMMAND_SET_DEVICE_VOLUME_WITH_FLAGS, Player.COMMAND_ADJUST_DEVICE_VOLUME_WITH_FLAGS,
    ).build()

    private val deviceInfo = DeviceInfo.Builder(DeviceInfo.PLAYBACK_TYPE_REMOTE).setMinVolume(0).setMaxVolume(100).build()

    private fun metadata(s: WidgetSnap): MediaMetadata {
        val b = MediaMetadata.Builder()
            .setTitle(s.title)
            .setArtist(s.sub)
            .setAlbumTitle(s.album.ifEmpty { null })
            .setSubtitle(s.room)
            .setStation(if (s.input == "radio") s.sub.ifEmpty { null } else null)
            .setIsPlayable(true)
            .setIsBrowsable(false)
            .setMediaType(if (s.live) MediaMetadata.MEDIA_TYPE_RADIO_STATION else MediaMetadata.MEDIA_TYPE_MUSIC)
        val c = cover
        if (c != null) b.setArtworkData(c, MediaMetadata.PICTURE_TYPE_FRONT_COVER)
        else if (s.cover.startsWith("http")) b.setArtworkUri(Uri.parse(s.cover))
        return b.build()
    }

    private fun placeholder(id: String): MediaItemData =
        MediaItemData.Builder(id).setMediaItem(MediaItem.Builder().setMediaId(id).build()).setIsPlaceholder(true).build()

    override fun getState(): State {
        val s = snap
        val now = MediaItem.Builder().setMediaId(SkjoldLibrary.currentId(s)).setMediaMetadata(metadata(s)).build()
        val item = MediaItemData.Builder("now:" + s.host)
            .setMediaItem(now)
            .setMediaMetadata(metadata(s))
            .setIsSeekable(!s.live && s.duration > 0)
            .apply {
                if (s.live) {
                    setIsDynamic(true)
                    setLiveConfiguration(MediaItem.LiveConfiguration.UNSET)
                    setDurationUs(C.TIME_UNSET)
                } else if (s.duration > 0) {
                    setDurationUs(s.duration * 1_000_000L)
                }
            }
            .build()
        // posisjon: siste kjente + tid siden, mens det spiller (daemonen oppgir sekunder)
        val elapsed = if (s.playing) SystemClock.elapsedRealtime() - posAtMs else 0L
        val posMs = if (s.live || s.duration <= 0) 0L else (s.position * 1000L + elapsed).coerceAtMost(s.duration * 1000L)
        return State.Builder()
            .setAvailableCommands(commands)
            .setPlaylist(listOf(placeholder("prev"), item, placeholder("next")))
            .setCurrentMediaItemIndex(1)
            .setContentPositionMs(posMs)
            .setPlayWhenReady(s.playing, Player.PLAY_WHEN_READY_CHANGE_REASON_REMOTE)
            .setPlaybackState(if (s.host.isEmpty() || !s.power) Player.STATE_IDLE else Player.STATE_READY)
            .setDeviceInfo(deviceInfo)
            .setDeviceVolume(s.volume.coerceIn(0, 100))
            .setIsDeviceMuted(s.mute)
            .build()
    }

    private fun send(path: String, body: Map<String, Any?>) {
        scope.launch { WidgetStore.command(ctx, path, body) }   // command() poller etterpå → publish → update()
    }

    private fun local(f: (WidgetSnap) -> WidgetSnap) { snap = f(snap); posAtMs = SystemClock.elapsedRealtime() }

    override fun handleSetPlayWhenReady(playWhenReady: Boolean): ListenableFuture<*> {
        local { it.copy(playing = playWhenReady) }
        send("/api/transport", mapOf("action" to if (playWhenReady) "play" else "pause"))
        return Futures.immediateVoidFuture()
    }

    override fun handlePrepare(): ListenableFuture<*> = Futures.immediateVoidFuture()

    override fun handleStop(): ListenableFuture<*> {
        local { it.copy(playing = false) }
        send("/api/transport", mapOf("action" to "pause"))
        return Futures.immediateVoidFuture()
    }

    override fun handleSeek(mediaItemIndex: Int, positionMs: Long, seekCommand: Int): ListenableFuture<*> {
        when (seekCommand) {
            Player.COMMAND_SEEK_TO_NEXT, Player.COMMAND_SEEK_TO_NEXT_MEDIA_ITEM -> send("/api/transport", mapOf("action" to "next"))
            Player.COMMAND_SEEK_TO_PREVIOUS, Player.COMMAND_SEEK_TO_PREVIOUS_MEDIA_ITEM -> send("/api/transport", mapOf("action" to "previous"))
            Player.COMMAND_SEEK_IN_CURRENT_MEDIA_ITEM -> send("/api/seek", mapOf("pos" to positionMs / 1000))
            else -> if (mediaItemIndex == 2) send("/api/transport", mapOf("action" to "next"))
                    else if (mediaItemIndex == 0) send("/api/transport", mapOf("action" to "previous"))
        }
        return Futures.immediateVoidFuture()
    }

    override fun handleSetDeviceVolume(deviceVolume: Int, flags: Int): ListenableFuture<*> {
        val v = deviceVolume.coerceIn(0, 100)
        local { it.copy(volume = v) }
        send("/api/volume", mapOf("volume" to v))
        return Futures.immediateVoidFuture()
    }

    override fun handleIncreaseDeviceVolume(flags: Int): ListenableFuture<*> = handleSetDeviceVolume(snap.volume + 3, flags)

    override fun handleDecreaseDeviceVolume(flags: Int): ListenableFuture<*> = handleSetDeviceVolume(snap.volume - 3, flags)

    override fun handleSetDeviceMuted(muted: Boolean, flags: Int): ListenableFuture<*> {
        local { it.copy(mute = muted) }
        send("/api/mute", mapOf("mute" to muted))
        return Futures.immediateVoidFuture()
    }

    /** Valg fra bibliotek, systemets gjenopptak eller en annen kontroller: spill elementet på enheten. */
    override fun handleSetMediaItems(mediaItems: MutableList<MediaItem>, startIndex: Int, startPositionMs: Long): ListenableFuture<*> {
        val i = if (startIndex in mediaItems.indices) startIndex else 0
        mediaItems.getOrNull(i)?.let { play(it) }
        return Futures.immediateVoidFuture()
    }

    override fun handleAddMediaItems(index: Int, mediaItems: MutableList<MediaItem>): ListenableFuture<*> {
        mediaItems.firstOrNull()?.let { play(it) }
        return Futures.immediateVoidFuture()
    }

    override fun handleRemoveMediaItems(fromIndex: Int, toIndex: Int): ListenableFuture<*> = Futures.immediateVoidFuture()

    override fun handleMoveMediaItems(fromIndex: Int, toIndex: Int, newIndex: Int): ListenableFuture<*> = Futures.immediateVoidFuture()

    private fun play(item: MediaItem) {
        val id = item.mediaId
        if (id.startsWith("now:") || id == "prev" || id == "next") { send("/api/transport", mapOf("action" to "play")); return }
        SkjoldLibrary.remember(ctx, item)
        local { it.copy(playing = true) }
        scope.launch { SkjoldLibrary.play(ctx, item) }
    }

    override fun handleRelease(): ListenableFuture<*> {
        scope.cancel()
        return Futures.immediateVoidFuture()
    }
}
