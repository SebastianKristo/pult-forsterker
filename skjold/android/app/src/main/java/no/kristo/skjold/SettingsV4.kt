package no.kristo.skjold

import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.rememberCoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.layout
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

/*
 * Innstillinger (v4), som V4Settings.swift på iOS: undertittel «Stue · Skjold S1 · 1.4.2», enhetsvalg som kapsler,
 * kategorilisten med fargede ikonfliser og APPEN-kortene. Tittelen «Innstillinger» tegnes av ContentView.
 * Undersidene er SettingsView.
 */

object SettingsUi {
    // v4-tokens (V4Tokens.swift) som ikke finnes i C
    val gold = hex(0xf0c46a)
    val goldDark = hex(0xd9a441)
    val chev = hex(0x6a6a65)
    val knobOff = hex(0x3a3a3c)
    const val chevRight = "M9 6l6 6-6 6"

    val catIcon = mapOf("tjenester" to "M9 18V5l12-2v13M9 18a3 3 0 1 1-6 0 3 3 0 0 1 6 0zM21 16a3 3 0 1 1-6 0 3 3 0 0 1 6 0z", "eq" to "M5 4v6M5 14v6M12 4v3M12 11v9M19 4v9M19 17v3M3 12h4M10 9h4M17 15h4", "lyd" to "M4 9h3l5-4v14l-5-4H4zM16 9a4 4 0 0 1 0 6M19 6a8 8 0 0 1 0 12", "tilkobling" to "M7 7l10 10-5 5V2l5 5L7 17", "radio" to "M4 9h16v11H4zM8 9l9-5M8 14.5h.01M14 13h4M14 16h4", "stemme" to "M12 3a3 3 0 0 1 3 3v6a3 3 0 0 1-6 0V6a3 3 0 0 1 3-3zM5 11a7 7 0 0 0 14 0M12 18v3", "skjerm" to "M3 5h18v12H3zM8 21h8M12 17v4", "strom" to "M12 3v8M6.3 6.6a8 8 0 1 0 11.4 0", "system" to "M12 8v4M12 16h.01M12 3l9 4v6c0 5-4 8-9 9-5-1-9-4-9-9V7z", "oppdatering" to "M12 4v11M7 10l5 5 5-5M5 20h14", "endringslogg" to "M6 3h9l4 4v14H6zM9 10h7M9 14h7M9 18h4", "programopptak" to "M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16zM12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z", "utgang" to "M4 9h3l5-4v14l-5-4H4zM16 8l5 4-5 4", "steder" to "M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21zM12 12a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z", "kassett" to "M3 6h18v12H3zM8 14a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM16 14a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM10 12h4", "skjoldhjem" to "M7 18a4.5 4.5 0 0 1-.6-9A6 6 0 0 1 18 8.5a4.5 4.5 0 0 1-.5 9.5z")
    val catTile = mapOf("tjenester" to 0x2a3a2eL, "eq" to 0x3a2e17L, "lyd" to 0x2a3340L, "tilkobling" to 0x22314aL, "radio" to 0x3d2a2aL, "stemme" to 0x2f2a40L, "skjerm" to 0x2a3a33L, "strom" to 0x40362aL, "system" to 0x333335L, "oppdatering" to 0x1f3a3aL, "endringslogg" to 0x2a3a2eL, "programopptak" to 0x2a1412L, "utgang" to 0x2a3340L, "steder" to 0x2a3340L, "skjoldhjem" to 0x22314aL, "kassett" to 0x3a2e17L)

    /**
     * m.cats med det iOS har i tillegg (SkjoldData.swift): «Skjerm og lys» har skjermvelgeren («disp», v4) og
     * ny undertekst. Bare innhold i kategoriene endres, aldri antall eller rekkefølge, så m.setCat peker på samme kategori.
     */
    fun cats(m: AppModel): List<SettingCategory> {
        val type = m.devRoom.type
        return m.cats.map { c ->
            if (c.id != "skjerm" || c.items.any { it.k == "disp" }) c
            else c.copy(
                sub = "Skjermtype, dimming, klokke, LED",
                // Node har bare skjermvelgeren; dimming, klokke og LED gjelder S1 (som dev-filtrene på iOS)
                items = listOfNotNull(dispItem(type)) + if (type == "node") emptyList() else c.items.map {
                    if (it.k == "off") it.copy(hint = "Beskytter OLED-skjermen mot innbrenning. TFT-skjermer får ikke innbrenning") else it
                },
            )
        }
    }

    private fun dispItem(type: String): SettingItem? = when (type) {
        "s1" -> SettingItem.opt("disp", "Skjerm", listOf("1,3″ OLED", "2,42″ OLED", "2,0″ TFT"),
            "Menyene og klokkene tilpasses skjermen. OLED: 128 × 64, TFT: 320 × 240 med bakgrunnslys og farge")
        "node" -> SettingItem.opt("disp", "Skjerm", listOf("0,91″ OLED", "1,3″ OLED", "1,8″ TFT", "Ingen skjerm"),
            "Menyene og klokkene tilpasses skjermen. Den lille 0,91″ OLED-en (128 × 32) får kompakte klokker")
        else -> null
    }

    /** «Stue · Skjold S1 · 1.4.2»: valgt enhet, type og programvareversjon (fra enheten, ellers appens oppdateringsstatus). */
    fun subtitle(m: AppModel): String {
        val r = m.devRoom
        val v = m.devRoomStatus?.version ?: ""
        return listOf(r.name, SK.dev(r.type).n, v.ifEmpty { m.upd.version }).filter { it.isNotEmpty() }.joinToString(" · ")
    }
}

/** Toppen av Innstillinger-fanen (V4SettingsTab uten undersider). */
@Composable
fun SettingsTop(m: AppModel) {
    val cats = SettingsUi.cats(m)
    // tittelen og undertittelen («Stue · Skjold S1 · 1.4.2») tegnes av DockTitleRow i ContentView
    Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(22.dp)) {
        if (m.sys.rooms.size > 1) DevicePicker(m)
        CategoryList(m, cats)
        AppCard(m)
    }
}


@Composable
private fun DevicePicker(m: AppModel) {
    val dev = m.devRoom
    EdgeScroll(8.dp, alignment = Alignment.CenterVertically) {
        for (r in m.sys.rooms) {
            val on = r.id == dev.id
            Row(
                Modifier.height(36.dp).clip(CircleShape).background(if (on) C.selBg else C.card)
                    .skCapsuleBorder(if (on) SettingsUi.goldDark else C.line2)
                    .press { Haptics.tick(); m.setDev = r.id; m.setCat = -1 }
                    .padding(horizontal = 14.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                SKIcon(SK.dev(r.type).icon, 18.dp, 1.4f, if (on) SettingsUi.gold else C.ink2)
                T(r.name, sora(13f, W.Regular, if (on) SettingsUi.gold else C.ink), maxLines = 1)
            }
        }
    }
}

@Composable
private fun CategoryList(m: AppModel, cats: List<SettingCategory>) {
    Column(Modifier.fillMaxWidth().skBox(C.card, C.line, 22.dp)) {
        cats.forEachIndexed { i, c ->
            Row(
                Modifier.fillMaxWidth().heightIn(min = 62.dp).topLine(if (i > 0) C.line else Color.Transparent)
                    .press { openCategory(m, i, c) }.padding(horizontal = 16.dp, vertical = 10.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(14.dp),
            ) {
                Box(
                    Modifier.size(38.dp).clip(RoundedCornerShape(11.dp)).background(hex(SettingsUi.catTile[c.id] ?: 0x2a2a2cL)),
                    contentAlignment = Alignment.Center,
                ) { SKIcon(SettingsUi.catIcon[c.id] ?: "", 19.dp, 1.7f, C.ink) }
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    T(c.n, sora(15f), maxLines = 1)
                    T(c.sub, sora(12f, W.Regular, C.muted), maxLines = 1)
                }
                SKIcon(SettingsUi.chevRight, 16.dp, 2f, SettingsUi.chev)
            }
        }
    }
}

/** Equalizer i listen går rett til Lyd-fanen (som i malen). */
private fun openCategory(m: AppModel, i: Int, c: SettingCategory) {
    if (c.id == "eq") { m.tab = 1; return }
    m.setCat = i; m.openK = ""; m.confirm = ""
}

/** APPEN: innstillinger som bare gjelder appen (lagres ikke på forsterkeren). */
@Composable
private fun AppCard(m: AppModel) {
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        SKMonoLabel("APPEN")
        AppUpdateBox()
        AppToggle("Vis andre Lyrion-spillere", "Ta med spillere som ikke er Skjold (for eksempel max2play eller TV-bokser) under Rom.", m.showLyrionPlayers) {
            m.setShowLyrion(!m.showLyrionPlayers)
        }
        var hapticSliders by remember { mutableStateOf(Haptics.slidersOn) }
        AppToggle("Haptikk på glidebrytere", "Tikk for hvert steg på equalizer og balanse, tydelig klikk ved 0 dB og et støt ved grensen.", hapticSliders) {
            hapticSliders = !hapticSliders
            Haptics.slidersOn = hapticSliders
            if (hapticSliders) Haptics.tick()
        }
        val ctx = LocalContext.current
        var callDuck by remember { mutableStateOf(CallDuck.enabled(ctx) && CallDuck.hasPermission(ctx)) }
        // Android: krever READ_PHONE_STATE, derfor en annen forklaring enn på iOS
        AppToggle("Senk musikken når telefonen ringer", "Skjold senker volumet mens det ringer og under samtalen, og løfter det igjen etterpå. Krever tilgang til telefonstatus.", callDuck) {
            callDuck = !callDuck
            if (callDuck && !CallDuck.hasPermission(ctx)) {
                (ctx as? android.app.Activity)?.requestPermissions(arrayOf(android.Manifest.permission.READ_PHONE_STATE), 11)
            }
            CallDuck.setEnabled(ctx, callDuck)
        }
    }
}

/** Oppdater selve Skjold-appen fra GitHub (app-v*-utgivelsene), uten Play Butikk. */
@Composable
private fun AppUpdateBox() {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    val har = remember { AppUpdate.installert(ctx) }
    var ny by remember { mutableStateOf<AppUpdate.Ny?>(null) }
    var msg by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    var prog by remember { mutableStateOf(-1f) }
    fun sjekk() {
        busy = true; msg = "Ser etter ny versjon …"
        scope.launch {
            try {
                val r = withContext(Dispatchers.IO) { AppUpdate.sjekk(ctx) }
                ny = r; msg = if (r == null) "Du har nyeste versjon." else ""
            } catch (e: Exception) { msg = e.message ?: "Fikk ikke sjekket" }
            busy = false
        }
    }
    LaunchedEffect(Unit) { sjekk() }
    Column(
        Modifier.fillMaxWidth().skBox(C.card, C.line, 22.dp).padding(horizontal = 16.dp, vertical = 14.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        T("Skjold-appen $har", sora(15f))
        val n = ny
        if (n != null) T("Versjon ${n.versjon} er klar (${String.format(java.util.Locale.US, "%.1f", n.bytes / 1_048_576.0).replace('.', ',')} MB, ${n.dato}).", sora(12f, W.Regular, C.muted, 1.4f))
        if (msg.isNotEmpty()) T(msg, sora(12f, W.Regular, C.muted, 1.4f))
        if (prog >= 0f) T("Laster ned … ${(prog * 100).toInt()} %", sora(12f, W.Regular, C.accent, 1.4f))
        if (n != null) {
            SKButton(if (busy) "Laster ned …" else "Oppdater til ${n.versjon}", if (busy) SKButtonKind.DISABLED else SKButtonKind.PRIMARY, height = 46.dp, size = 14f) {
                if (busy) return@SKButton
                if (!AppUpdate.kanInstallere(ctx)) { msg = "Gi Skjold lov til å installere apper (slå på bryteren), og trykk Oppdater igjen."; AppUpdate.aapneTillatelse(ctx); return@SKButton }
                busy = true; prog = 0f; msg = ""
                scope.launch {
                    try {
                        withContext(Dispatchers.IO) { AppUpdate.installer(ctx, n) { p -> scope.launch { prog = p } } }
                        msg = "Bekreft oppdateringen i vinduet fra Android."
                    } catch (e: Exception) { msg = e.message ?: "Oppdateringen feilet" }
                    busy = false; prog = -1f
                }
            }
        } else {
            SKButton(if (busy) "Sjekker …" else "Se etter oppdatering", if (busy) SKButtonKind.DISABLED else SKButtonKind.SECONDARY, height = 42.dp, size = 13.5f) { if (!busy) sjekk() }
        }
    }
}

@Composable
private fun AppToggle(title: String, sub: String, on: Boolean, toggle: () -> Unit) {
    Row(
        Modifier.fillMaxWidth().skBox(C.card, C.line, 22.dp).padding(horizontal = 16.dp, vertical = 13.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            T(title, sora(15f))
            T(sub, sora(12f, W.Regular, C.muted, 1.4f))
        }
        SettingsSwitch(on, title, toggle)
    }
}

/** V4Switch: iOS-bryter 51 × 31 (spor #d9a441 / #3a3a3c, knott 27, venstre 22 / 2). */
@Composable
fun SettingsSwitch(on: Boolean, label: String, toggle: () -> Unit) {
    val x by animateDpAsState(if (on) 22.dp else 2.dp, tween(200), label = "settingsSwitch")
    Box(
        Modifier.size(51.dp, 31.dp).clip(CircleShape).background(if (on) SettingsUi.goldDark else SettingsUi.knobOff)
            .press(label = label) { Haptics.tick(); toggle() }
            .semantics { stateDescription = if (on) "På" else "Av" },
    ) {
        Box(Modifier.offset(x = x, y = 2.dp).size(27.dp).shadow(3.dp, CircleShape).background(Color.White, CircleShape))
    }
}
