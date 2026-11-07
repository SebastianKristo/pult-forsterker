package no.kristo.skjold

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.telephony.PhoneStateListener
import android.telephony.TelephonyCallback
import android.telephony.TelephonyManager
import org.json.JSONObject
import java.util.concurrent.Executors

/**
 * «Senk musikken når telefonen ringer»: når det ringer eller du er i samtale, ber appen Skjold om å senke
 * volumet (POST /api/duck {kilde: telefon}); når samtalen er over, løftes det igjen ({slutt: true}).
 * Krever tillatelsen READ_PHONE_STATE (spørres bare når brukeren slår funksjonen på) og at appen har kjørt
 * siden siste omstart. Virker ikke når appen er tvangsstoppet.
 */
object CallDuck {
    private const val PREF = "skjold_callduck"
    private val io = Executors.newSingleThreadExecutor()
    private var started = false
    private var ducked = false

    fun enabled(ctx: Context): Boolean = ctx.getSharedPreferences(PREF, Context.MODE_PRIVATE).getBoolean("on", false)
    fun setEnabled(ctx: Context, on: Boolean) {
        ctx.getSharedPreferences(PREF, Context.MODE_PRIVATE).edit().putBoolean("on", on).apply()
        if (on) start(ctx)
    }

    fun hasPermission(ctx: Context): Boolean =
        ctx.checkSelfPermission(Manifest.permission.READ_PHONE_STATE) == PackageManager.PERMISSION_GRANTED

    private fun send(ctx: Context, end: Boolean) {
        val app = ctx.applicationContext
        io.execute {
            val body = JSONObject().put("kilde", "telefon")
            if (end) body.put("slutt", true)
            Shortcuts.duck(app, body)
        }
    }

    private fun onState(ctx: Context, state: Int) {
        if (!enabled(ctx)) return
        val busy = state == TelephonyManager.CALL_STATE_RINGING || state == TelephonyManager.CALL_STATE_OFFHOOK
        if (busy && !ducked) { ducked = true; send(ctx, false) }
        if (!busy && ducked) { ducked = false; send(ctx, true) }
    }

    /** Start lyttingen (kalles ved oppstart og når funksjonen slås på). */
    fun start(ctx: Context) {
        if (started || !enabled(ctx) || !hasPermission(ctx)) return
        val app = ctx.applicationContext
        val tm = app.getSystemService(Context.TELEPHONY_SERVICE) as? TelephonyManager ?: return
        try {
            if (Build.VERSION.SDK_INT >= 31) {
                val cb = object : TelephonyCallback(), TelephonyCallback.CallStateListener {
                    override fun onCallStateChanged(state: Int) = onState(app, state)
                }
                tm.registerTelephonyCallback(app.mainExecutor, cb)
            } else {
                @Suppress("DEPRECATION")
                tm.listen(object : PhoneStateListener() {
                    @Deprecated("Deprecated in Java")
                    override fun onCallStateChanged(state: Int, phoneNumber: String?) = onState(app, state)
                }, PhoneStateListener.LISTEN_CALL_STATE)
            }
            started = true
        } catch (_: SecurityException) {
        }
    }
}
