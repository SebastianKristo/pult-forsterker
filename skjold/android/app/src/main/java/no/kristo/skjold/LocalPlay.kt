package no.kristo.skjold

import android.content.Context
import android.media.AudioAttributes
import android.media.MediaPlayer
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue

/**
 * «Denne telefonen»: spill det Skjold spiller på telefonen i stedet for i rommet.
 * Skjold fortsetter å spille, men dempet (POST /api/mute), så kø, neste/forrige, pause og spoling virker som før.
 * Telefonen speiler strømmen fra status `listen` (Skjolds /api/stream-proxy) og holder seg i takt med posisjonen.
 * Tilbake til rommet: lyden slås på igjen i Skjold, fra samme sted i låten.
 */
object LocalPlay {
    var on by mutableStateOf(false)
        private set
    var vol by mutableStateOf(80)
        private set

    private var player: MediaPlayer? = null
    private var prepared = false
    private var cur = ""
    private var host = ""
    private var wasMuted = false
    private var model: AppModel? = null
    private var prefs: android.content.SharedPreferences? = null

    /** Kan det som spilles nå spilles på telefonen? (Radio og bibliotekene – ikke AirPlay, Blåtann, Spotify eller AUX.) */
    fun can(m: AppModel): Boolean = m.live && !m.dev?.listen.isNullOrEmpty()

    fun start(ctx: Context, m: AppModel) {
        val d = m.dev
        val h = m.activeHost
        if (d == null || d.listen.isEmpty() || h == null) { Haptics.warning(); return }
        prefs = ctx.applicationContext.getSharedPreferences("skjold-local", Context.MODE_PRIVATE)
        vol = prefs?.getInt("vol", 80) ?: 80
        model = m
        host = h
        wasMuted = d.mute
        cur = ""
        on = true
        sync(m, d, h)
        if (!wasMuted) m.devSend("/api/mute", mapOf("mute" to true), on = h)
        Haptics.tick()
    }

    fun stop() {
        if (!on) return
        on = false
        val p = player
        val pos = if (p != null && prepared) p.currentPosition / 1000 else -1
        release()
        val m = model ?: return
        val d = m.devStats[host] ?: m.dev
        if (d != null && d.duration > 0 && pos >= 0 && kotlin.math.abs(d.position - pos) > 3) m.devSend("/api/seek", mapOf("pos" to pos), on = host)
        if (!wasMuted) m.devSend("/api/mute", mapOf("mute" to false), on = host)
    }

    fun changeVol(v: Int) {
        vol = v.coerceIn(0, 100)
        player?.setVolume(vol / 100f, vol / 100f)
        prefs?.edit()?.putInt("vol", vol)?.apply()
    }

    /** Kalles for hver ny status fra det aktive rommet: ny strøm, pause/spill og posisjon. */
    fun sync(m: AppModel, d: DevStatus, h: String) {
        if (!on) return
        if (h != host) { stop(); return }   // byttet rom: lyden tilbake til rommet den kom fra
        val url = if (d.listen.isEmpty()) null else Net.url(h, d.listen)
        if (url == null) { stop(); return }
        val track = d.duration > 0
        if (d.listen != cur) {
            cur = d.listen
            release()
            prepared = false
            val p = MediaPlayer()
            player = p
            p.setAudioAttributes(AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_MEDIA).setContentType(AudioAttributes.CONTENT_TYPE_MUSIC).build())
            p.setOnPreparedListener { mp ->
                prepared = true
                val s = m.devStats[host] ?: d
                if (s.duration > 0 && s.position > 1) mp.seekTo(s.position * 1000)
                mp.setVolume(vol / 100f, vol / 100f)
                if (s.playing) mp.start()
            }
            p.setOnErrorListener { _, _, _ -> if (on) stop(); true }
            try { p.setDataSource(url); p.prepareAsync() } catch (_: Exception) { stop() }
            return
        }
        val p = player ?: return
        if (!prepared) return
        if (track && kotlin.math.abs(p.currentPosition / 1000 - d.position) > 4) p.seekTo(d.position * 1000)
        p.setVolume(vol / 100f, vol / 100f)
        if (d.playing && !p.isPlaying) p.start() else if (!d.playing && p.isPlaying) p.pause()
    }

    private fun release() {
        try { player?.stop() } catch (_: Exception) {}
        player?.release()
        player = null
        prepared = false
    }
}
