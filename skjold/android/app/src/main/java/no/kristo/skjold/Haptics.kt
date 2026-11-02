package no.kristo.skjold

import android.content.Context
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager

/** Haptic feedback used across the app (Haptics.swift). */
object Haptics {
    private var vib: Vibrator? = null

    fun init(ctx: Context) {
        vib = if (Build.VERSION.SDK_INT >= 31) {
            (ctx.getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as? VibratorManager)?.defaultVibrator
        } else {
            @Suppress("DEPRECATION")
            ctx.getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator
        }
    }

    private fun predefined(effect: Int, fallbackMs: Long, amp: Int) {
        val v = vib ?: return
        if (!v.hasVibrator()) return
        try {
            if (Build.VERSION.SDK_INT >= 29) v.vibrate(VibrationEffect.createPredefined(effect))
            else v.vibrate(VibrationEffect.createOneShot(fallbackMs, amp))
        } catch (_: Throwable) {
        }
    }

    private fun wave(timings: LongArray, amps: IntArray) {
        val v = vib ?: return
        if (!v.hasVibrator()) return
        try { v.vibrate(VibrationEffect.createWaveform(timings, amps, -1)) } catch (_: Throwable) {}
    }

    /** Button press. */
    fun tap() = predefined(if (Build.VERSION.SDK_INT >= 29) VibrationEffect.EFFECT_TICK else 0, 8, 60)
    /** Bigger action: play/pause, opening/closing the player. */
    fun thump() = predefined(if (Build.VERSION.SDK_INT >= 29) VibrationEffect.EFFECT_CLICK else 0, 14, 140)
    /** Slider detent, tab change, chip/segment selection. */
    fun tick() = predefined(if (Build.VERSION.SDK_INT >= 29) VibrationEffect.EFFECT_TICK else 0, 6, 50)
    /** Soft bump when a drag crosses a threshold. */
    fun bump() = predefined(if (Build.VERSION.SDK_INT >= 29) VibrationEffect.EFFECT_HEAVY_CLICK else 0, 12, 110)

    fun success() = wave(longArrayOf(0, 12, 70, 18), intArrayOf(0, 90, 0, 160))
    fun warning() = wave(longArrayOf(0, 18, 90, 12), intArrayOf(0, 160, 0, 90))
    fun error() = wave(longArrayOf(0, 14, 60, 14, 60, 20), intArrayOf(0, 160, 0, 160, 0, 200))
}
