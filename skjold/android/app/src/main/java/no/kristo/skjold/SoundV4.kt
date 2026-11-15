package no.kristo.skjold

import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.unit.dp
import kotlinx.serialization.builtins.ListSerializer
import kotlinx.serialization.builtins.serializer

/*
 * Tilstand og modellhjelpere for Lyd-fanen (v4), som V4Sound.swift på iOS. Alt som lagres bruker iOS-nøklene:
 * «skjold-v4-night», «skjold-v4-hpf» og «skjold-eqoff-<kilde>» ([preset] + eq mens equalizeren er av).
 */

object SoundUi {
    /** Valgt bånd (0–4), som `@State band = 3` i V4SoundTab. Ligger her så det overlever fanebytte. */
    var band by mutableIntStateOf(3)
    /** Profilen som var på før «Hold for å sammenligne» (null = ikke trykket). */
    var cmp by mutableStateOf<List<Int>?>(null)

    private val nightS = mutableStateOf(Store.bool("skjold-v4-night"))
    private val hpfS = mutableStateOf(Store.bool("skjold-v4-hpf"))
    var night: Boolean
        get() = nightS.value
        set(v) { nightS.value = v; Store.setBool("skjold-v4-night", v) }
    var hpf: Boolean
        get() = hpfS.value
        set(v) { hpfS.value = v; Store.setBool("skjold-v4-hpf", v) }

    // «skjold-eqoff-<kilde>»: lagret [preset, eq0…eq4] mens EQ er av. offVer gjør lesingen observerbar.
    private var offVer by mutableIntStateOf(0)
    private val offSer = ListSerializer(Int.serializer())
    private fun offKey(src: String) = "skjold-eqoff-$src"

    fun off(src: String): List<Int>? {
        @Suppress("UNUSED_VARIABLE") val v = offVer
        return Store.load(offKey(src), offSer)
    }

    fun setOff(src: String, v: List<Int>?) {
        if (v == null) Store.setString(offKey(src), null) else Store.save(offKey(src), v, offSer)
        offVer++
    }

    val bandNames = listOf(Triple("Dypbass", "60 Hz", "60"), Triple("Bass", "250 Hz", "250"), Triple("Mellomtone", "1 kHz", "1k"),
                           Triple("Presens", "4 kHz", "4k"), Triple("Luft", "12 kHz", "12k"))
    val desc = listOf(
        "Den dype bassen du kjenner mer enn hører. Skru ned hvis små høyttalere dundrer.",
        "Fylde og varme. For mye gjør lyden grøtete.",
        "Der stemmer og instrumenter bor. Senk for en mykere, mer avslappet lyd.",
        "Gjør vokal og detaljer tydeligere. For mye blir skarpt.",
        "Cymbaler, glans og romfølelse.",
    )
    /** Maks volum: indeks i sset["vmax"] → prosent. */
    val vmax = listOf(100, 90, 80, 70)
    val zeros = listOf(0, 0, 0, 0, 0)
}

// MARK: - Modell (som private var/func i V4SoundTab)

/** EQ er på for kilden som redigeres (ingen «skjold-eqoff-<kilde>» lagret). */
val AppModel.soundEqOn: Boolean get() = SoundUi.off(eqEditing) == null

/** Kurven som vises: flat mens man sammenligner eller når EQ er av. */
val AppModel.soundLive: List<Int>
    get() = if (SoundUi.cmp != null || !soundEqOn) SoundUi.zeros else prof.eq.let { if (it.size == 5) it else SoundUi.zeros }

val AppModel.soundPresetName: String
    get() { val p = prof.preset; return if (p >= 0 && p < SK.eqPresets.size) SK.eqPresets[p].first else "Egendefinert" }

val AppModel.soundSrcLabel: String get() = SK.eqSources.firstOrNull { it.first == eqEditing }?.second ?: ""

/** Setter ett bånd (−12…12); slår EQ på igjen hvis den var av og gjør profilen egendefinert. */
fun AppModel.soundSetBand(i: Int, v: Int) {
    val c = v.coerceIn(-12, 12)
    if (!soundEqOn) SoundUi.setOff(eqEditing, null)
    val p = prof
    if (p.eq.size != 5 || (p.eq[i] == c && p.preset == -1)) return
    Haptics.sliderStep(p.eq[i], c, -12, 12)
    setProf { q ->
        val eq = if (q.eq.size != 5) SoundUi.zeros.toMutableList() else q.eq.toMutableList()
        eq[i] = c
        q.copy(eq = eq, preset = -1)
    }
    SoundUi.band = i
}

/** EQ av: husk [preset] + eq og send flat. EQ på: hent det som var lagret. */
fun AppModel.soundToggleEq() {
    if (soundEqOn) {
        val p = prof
        SoundUi.setOff(eqEditing, listOf(p.preset) + p.eq)
        setProf { it.copy(eq = SoundUi.zeros) }
    } else {
        val a = SoundUi.off(eqEditing) ?: listOf(0, 0, 0, 0, 0, 0)
        SoundUi.setOff(eqEditing, null)
        if (a.size == 6) setProf { it.copy(preset = a[0], eq = a.drop(1)) }
    }
}

fun AppModel.soundPickPreset(i: Int) {
    SoundUi.setOff(eqEditing, null)
    Haptics.thump()
    setProf { it.copy(preset = i, eq = SK.eqPresets[i].second) }
}

fun AppModel.soundCompareStart() {
    if (SoundUi.cmp != null) return
    Haptics.tap()
    SoundUi.cmp = prof.eq
    setProf { it.copy(eq = SoundUi.zeros) }
}

fun AppModel.soundCompareEnd() {
    val saved = SoundUi.cmp ?: return
    SoundUi.cmp = null
    setProf { it.copy(eq = saved) }
}

// MARK: - V4Switch

/** iOS-bryter 51 × 31 (spor #d9a441 / #3a3a3c, knott 27 hvit med skygge, venstre 22 / 2), som V4Switch. */
@Composable
fun SoundSwitch(on: Boolean, label: String = "", toggle: () -> Unit) {
    val x by animateDpAsState(if (on) 22.dp else 2.dp, tween(200), label = "soundSwitch")
    Box(
        Modifier.size(51.dp, 31.dp).clip(CircleShape).background(if (on) C.accent else hex(0x3a3a3c))
            .semantics { stateDescription = if (on) "På" else "Av" }
            .press(label = label.ifEmpty { null }) { Haptics.tick(); toggle() },
    ) {
        Box(Modifier.offset(x = x, y = 2.dp).size(27.dp).shadow(3.dp, CircleShape, ambientColor = Color.Black.copy(alpha = 0.35f), spotColor = Color.Black.copy(alpha = 0.35f)).clip(CircleShape).background(Color.White))
    }
}
