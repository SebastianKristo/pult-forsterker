package no.kristo.skjold

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.support.v4.media.MediaMetadataCompat
import android.support.v4.media.session.MediaSessionCompat
import android.support.v4.media.session.PlaybackStateCompat
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import androidx.core.content.ContextCompat
import androidx.media.VolumeProviderCompat
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

/**
 * «Spiller nå» som pågående medievarsling: MediaSession + MediaStyle. Det gir medieavspilleren i hurtiginnstillingene,
 * låseskjermen og Samsungs Now Bar (One UI 7 viser aktive medieøkter der). Volumknappene på telefonen styrer Skjold
 * (fjernvolum via VolumeProviderCompat). Tjenesten følger selv med på status mens den kjører, og stopper når det ikke
 * har spilt på en stund.
 *
 * Android 16 «Live Updates» (promoted ongoing) gjelder ikke MediaStyle-varsler og krever compileSdk 36; medievarselet er
 * allerede den fremhevede visningen for avspilling, så det brukes ikke her.
 */
class NowPlayingService : Service() {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    private var session: MediaSessionCompat? = null
    private var volume: VolumeProviderCompat? = null
    private var poller: Job? = null
    private var snap = WidgetSnap()
    private var idleSince = 0L
    private var started = false

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        Store.init(this)
        val nm = getSystemService(NotificationManager::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O && nm.getNotificationChannel(CHANNEL) == null) {
            nm.createNotificationChannel(NotificationChannel(CHANNEL, "Spiller nå", NotificationManager.IMPORTANCE_LOW).apply {
                description = "Viser hva Skjold spiller, med knapper for avspilling og volum"
                setShowBadge(false)
            })
        }
        val s = MediaSessionCompat(this, "Skjold")
        s.setCallback(object : MediaSessionCompat.Callback() {
            override fun onPlay() = cmd("/api/transport", mapOf("action" to "play"))
            override fun onPause() = cmd("/api/transport", mapOf("action" to "pause"))
            override fun onSkipToNext() = cmd("/api/transport", mapOf("action" to "next"))
            override fun onSkipToPrevious() = cmd("/api/transport", mapOf("action" to "previous"))
            override fun onStop() = cmd("/api/transport", mapOf("action" to "pause"))
        })
        val vp = object : VolumeProviderCompat(VolumeProviderCompat.VOLUME_CONTROL_ABSOLUTE, 100, snap.volume) {
            override fun onSetVolumeTo(v: Int) { currentVolume = v; cmd("/api/volume", mapOf("volume" to v.coerceIn(0, 100))) }
            override fun onAdjustVolume(direction: Int) {
                val v = (currentVolume + direction * 3).coerceIn(0, 100)
                currentVolume = v; cmd("/api/volume", mapOf("volume" to v))
            }
        }
        s.setPlaybackToRemote(vp)
        s.setSessionActivity(PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT))
        s.isActive = true
        session = s; volume = vp
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACT_PLAYPAUSE -> cmd("/api/transport", mapOf("action" to "playpause"))
            ACT_NEXT -> cmd("/api/transport", mapOf("action" to "next"))
            ACT_PREV -> cmd("/api/transport", mapOf("action" to "previous"))
            ACT_VDOWN -> cmd("/api/volume", mapOf("volume" to (snap.volume - 4).coerceIn(0, 100)))
            ACT_VUP -> cmd("/api/volume", mapOf("volume" to (snap.volume + 4).coerceIn(0, 100)))
            ACT_CLOSE -> { stopSelf(); return START_NOT_STICKY }
        }
        snap = WidgetStore.load(this)
        show()
        if (poller == null) poller = scope.launch {
            while (isActive) {
                delay(3000)
                val s = WidgetStore.poll(this@NowPlayingService)
                if (s != null) { snap = s; show() }
                if (snap.playing) idleSince = 0L
                else if (idleSince == 0L) idleSince = System.currentTimeMillis()
                else if (System.currentTimeMillis() - idleSince > 90_000) { stopSelf(); break }
            }
        }
        return START_NOT_STICKY
    }

    private fun cmd(path: String, body: Map<String, Any?>) {
        scope.launch {
            WidgetStore.command(this@NowPlayingService, path, body)
            snap = WidgetStore.load(this@NowPlayingService)
            show()
        }
    }

    private fun pi(action: String, code: Int): PendingIntent =
        PendingIntent.getService(this, code, Intent(this, NowPlayingService::class.java).setAction(action), PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)

    private fun show() {
        val s = session ?: return
        val art = WidgetStore.coverBitmap(this)
        s.setMetadata(MediaMetadataCompat.Builder()
            .putString(MediaMetadataCompat.METADATA_KEY_TITLE, snap.title)
            .putString(MediaMetadataCompat.METADATA_KEY_ARTIST, snap.sub)
            .putString(MediaMetadataCompat.METADATA_KEY_ALBUM, snap.room)
            .apply { if (art != null) putBitmap(MediaMetadataCompat.METADATA_KEY_ALBUM_ART, art) }
            .build())
        s.setPlaybackState(PlaybackStateCompat.Builder()
            .setActions(PlaybackStateCompat.ACTION_PLAY or PlaybackStateCompat.ACTION_PAUSE or PlaybackStateCompat.ACTION_PLAY_PAUSE or
                PlaybackStateCompat.ACTION_SKIP_TO_NEXT or PlaybackStateCompat.ACTION_SKIP_TO_PREVIOUS or PlaybackStateCompat.ACTION_STOP)
            .setState(if (snap.playing) PlaybackStateCompat.STATE_PLAYING else PlaybackStateCompat.STATE_PAUSED, PlaybackStateCompat.PLAYBACK_POSITION_UNKNOWN, 1f)
            .build())
        volume?.currentVolume = snap.volume

        val n = NotificationCompat.Builder(this, CHANNEL)
            .setSmallIcon(R.drawable.ic_stat_skjold)
            .setContentTitle(snap.title)
            .setContentText(snap.sub)
            .setSubText(snap.room)
            .setLargeIcon(art)
            .setOngoing(snap.playing)
            .setOnlyAlertOnce(true)
            .setShowWhen(false)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .setCategory(NotificationCompat.CATEGORY_TRANSPORT)
            .setContentIntent(s.controller.sessionActivity)
            .setDeleteIntent(pi(ACT_CLOSE, 6))
            .addAction(R.drawable.ic_n_vol_down, "Volum ned", pi(ACT_VDOWN, 1))
            .addAction(R.drawable.ic_n_prev, "Forrige", pi(ACT_PREV, 2))
            .addAction(if (snap.playing) R.drawable.ic_n_pause else R.drawable.ic_n_play, if (snap.playing) "Pause" else "Spill", pi(ACT_PLAYPAUSE, 3))
            .addAction(R.drawable.ic_n_next, "Neste", pi(ACT_NEXT, 4))
            .addAction(R.drawable.ic_n_vol_up, "Volum opp", pi(ACT_VUP, 5))
            .setStyle(androidx.media.app.NotificationCompat.MediaStyle().setMediaSession(s.sessionToken).setShowActionsInCompactView(1, 2, 3))
            .build()
        try {
            if (!started) {
                ServiceCompat.startForeground(this, NOTIF_ID, n,
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK else 0)
                started = true
            } else {
                getSystemService(NotificationManager::class.java).notify(NOTIF_ID, n)
            }
        } catch (_: Exception) { stopSelf() }
    }

    override fun onDestroy() {
        stopped()
        poller?.cancel()
        scope.cancel()
        session?.isActive = false
        session?.release()
        session = null
        ServiceCompat.stopForeground(this, ServiceCompat.STOP_FOREGROUND_REMOVE)
        super.onDestroy()
    }

    companion object {
        private const val CHANNEL = "skjold-now-playing"
        private const val NOTIF_ID = 4711
        private const val ACT_PLAYPAUSE = "no.kristo.skjold.PLAYPAUSE"
        private const val ACT_NEXT = "no.kristo.skjold.NEXT"
        private const val ACT_PREV = "no.kristo.skjold.PREV"
        private const val ACT_VDOWN = "no.kristo.skjold.VDOWN"
        private const val ACT_VUP = "no.kristo.skjold.VUP"
        private const val ACT_CLOSE = "no.kristo.skjold.CLOSE"
        @Volatile private var running = false

        /** Start when Skjold plays (the app is in front, so a foreground service may start); the service stops itself later. */
        fun sync(ctx: Context, s: WidgetSnap) {
            if (!s.playing || running) return
            try {
                ContextCompat.startForegroundService(ctx, Intent(ctx, NowPlayingService::class.java))
                running = true
            } catch (_: Exception) { }   // f.eks. ForegroundServiceStartNotAllowedException når appen er i bakgrunnen
        }

        internal fun stopped() { running = false }
    }
}
