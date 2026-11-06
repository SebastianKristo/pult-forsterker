package no.kristo.skjold

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.delay
import java.util.Calendar
import kotlin.math.ceil
import kotlin.math.cos
import kotlin.math.roundToInt
import kotlin.math.sin

private val catIcon = mapOf("tjenester" to "M9 18V5l12-2v13M9 18a3 3 0 1 1-6 0 3 3 0 0 1 6 0zM21 16a3 3 0 1 1-6 0 3 3 0 0 1 6 0z", "eq" to "M5 4v6M5 14v6M12 4v3M12 11v9M19 4v9M19 17v3M3 12h4M10 9h4M17 15h4", "lyd" to "M4 9h3l5-4v14l-5-4H4zM16 9a4 4 0 0 1 0 6M19 6a8 8 0 0 1 0 12", "tilkobling" to "M7 7l10 10-5 5V2l5 5L7 17", "radio" to "M4 9h16v11H4zM8 9l9-5M8 14.5h.01M14 13h4M14 16h4", "stemme" to "M12 3a3 3 0 0 1 3 3v6a3 3 0 0 1-6 0V6a3 3 0 0 1 3-3zM5 11a7 7 0 0 0 14 0M12 18v3", "skjerm" to "M3 5h18v12H3zM8 21h8M12 17v4", "strom" to "M12 3v8M6.3 6.6a8 8 0 1 0 11.4 0", "system" to "M12 8v4M12 16h.01M12 3l9 4v6c0 5-4 8-9 9-5-1-9-4-9-9V7z", "oppdatering" to "M12 4v11M7 10l5 5 5-5M5 20h14", "endringslogg" to "M6 3h9l4 4v14H6zM9 10h7M9 14h7M9 18h4", "programopptak" to "M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16zM12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z", "utgang" to "M4 9h3l5-4v14l-5-4H4zM16 8l5 4-5 4", "steder" to "M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21zM12 12a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z", "skjoldhjem" to "M7 18a4.5 4.5 0 0 1-.6-9A6 6 0 0 1 18 8.5a4.5 4.5 0 0 1-.5 9.5z")
private val catTile = mapOf("tjenester" to 0x2a3a2eL, "eq" to 0x3a2e17L, "lyd" to 0x2a3340L, "tilkobling" to 0x22314aL, "radio" to 0x3d2a2aL, "stemme" to 0x2f2a40L, "skjerm" to 0x2a3a33L, "strom" to 0x40362aL, "system" to 0x333335L, "oppdatering" to 0x1f3a3aL, "endringslogg" to 0x2a3a2eL, "programopptak" to 0x2a1412L, "utgang" to 0x2a3340L, "steder" to 0x2a3340L, "skjoldhjem" to 0x22314aL)

/** 18 Innstillinger, 19 Innst. → Radio, 20 Innst. → Equalizer and the other categories from catsFor(type). */
@Composable
fun SettingsView(m: AppModel) {
    val cats = m.cats
    if (m.setCat < 0 || m.setCat >= cats.size) { Top(m, cats); return }
    val cat = cats[m.setCat]
    SKBackButton("Innstillinger") { m.setCat = -1; m.openK = "" }
    if (cat.id == "radio") {
        T("Favoritter", sora(17f, W.Semibold))
        if (m.rAdd) RadioAddView(m) else RadioFavoritesView(m)
        T("Knapper og oppstart", sora(17f, W.Semibold), Modifier.padding(top = 6.dp))
    }
    if (cat.id == "oppdatering") { DeviceUpdateView(m); UpdateSettingsView(m) }
    else if (cat.id == "endringslogg") ChangelogView(m)
    else if (cat.id == "programopptak") RecordedProgramsView(m)
    else if (cat.id == "steder") StederSettingsView(m)
    else if (cat.id == "skjoldhjem") SkyDeviceView(m)
    else {
        if (cat.id == "skjerm") ClockPicker(m)
        if (cat.id == "tilkobling") WifiSettingsView(m)
        SettingItemsCard(m, cat.items.filter { it.kind != SettingKind.Update && it.kind != SettingKind.Clocks })
    }
}

@Composable
private fun Top(m: AppModel, cats: List<SettingCategory>) {
    val dev = m.devRoom
    EdgeScroll(6.dp) {
        for (r in m.sys.rooms) {
            val s = SelStyle.of(r.id == dev.id)
            Column(
                Modifier.clip(RoundedCornerShape(12.dp)).background(s.bg).skBorder(s.bd, 12.dp).press { m.setDev = r.id; m.setCat = -1 }
                    .padding(horizontal = 12.dp, vertical = 8.dp),
                verticalArrangement = Arrangement.spacedBy(1.dp),
            ) {
                SKIcon(SK.dev(r.type).icon, 30.dp, 1.2f, C.ink2)
                T(r.name, sora(13f, W.Regular, s.fg), maxLines = 1)
                T(SK.dev(r.type).n, mono(9.5f), maxLines = 1)
            }
        }
    }
    T(AppModel.hwText(dev) + if (dev.type == "node") " · ingen skjerm eller knapper" else "", sora(11f, W.Regular, C.muted))
    SKCard {
        cats.forEachIndexed { i, c ->
            Row(
                Modifier.fillMaxWidth().heightIn(min = 58.dp).topLine(if (i > 0) C.line else Color.Transparent)
                    .press { m.setCat = i; m.openK = ""; m.confirm = "" }.padding(vertical = 8.dp, horizontal = 14.dp),
                verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                Box(Modifier.size(32.dp).clip(RoundedCornerShape(8.dp)).background(hex(catTile[c.id] ?: 0x333333L)), contentAlignment = Alignment.Center) {
                    SKIcon(catIcon[c.id] ?: "", 18.dp, 1.8f, C.ink)
                }
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    T(c.n, sora(14f))
                    T(c.sub, sora(11f, W.Regular, C.muted))
                }
                SKIcon(Icons.chevronRight, 16.dp, 2f, C.muted)
            }
        }
    }
    // App-level settings (not stored on the amplifier)
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        SKMonoLabel("APPEN", modifier = Modifier.padding(top = 6.dp))
        Row(Modifier.fillMaxWidth().skBox(C.card, C.line).padding(14.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                T("Vis andre Lyrion-spillere", sora(14f))
                T("Ta med spillere som ikke er Skjold (for eksempel max2play eller TV-bokser) under Rom.", sora(11f, W.Regular, C.muted))
            }
            SKToggle(m.showLyrionPlayers) { m.setShowLyrion(!m.showLyrionPlayers) }
        }
    }
}

// MARK: - Item rows

@Composable
fun SettingItemsCard(m: AppModel, items: List<SettingItem>) {
    SKCard {
        items.forEachIndexed { i, d ->
            Box(Modifier.fillMaxWidth().topLine(if (i > 0) C.line else Color.Transparent).padding(vertical = 12.dp, horizontal = 14.dp)) { ItemRow(m, d) }
        }
    }
}

@Composable
private fun ItemRow(m: AppModel, d: SettingItem) {
    val v = m.sset[d.k] ?: SK.def[d.k] ?: 0
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(Modifier.fillMaxWidth().heightIn(min = 30.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                T(d.n, sora(14f))
                if (d.hint != null) T(d.hint, sora(11f, W.Regular, C.muted))
            }
            Control(m, d, v)
        }
        Extra(m, d, v)
    }
}

private val nameDefaults = mapOf("nAux1" to "AUX 1", "nAux2" to "AUX 2", "nUsb1" to "PC", "nUsb2" to "Switch")

private fun nameValue(m: AppModel, k: String) = m.names[k] ?: nameDefaults[k] ?: ""

private fun setName(m: AppModel, k: String, max: Int, v: String) {
    if (k == "ytmCookie") m.ytmT = null
    if (k == "plexUrl" || k == "plexToken") { m.plexT = null; m.libs = m.libs - "plex" }
    if (k == "ndUrl" || k == "ndUser" || k == "ndPass") { m.ndT = null; m.libs = m.libs - "nd" }
    m.saveName(k, v.take(max))
}

@Composable
private fun Control(m: AppModel, d: SettingItem, v: Int) {
    when (val k = d.kind) {
        SettingKind.Bool -> SKToggle(v != 0) { m.setS(d.k, if (v != 0) 0 else 1) }
        is SettingKind.Num -> Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            StepButton("−") { m.setS(d.k, maxOf(k.min, v - 1)) }
            T(k.format.format(v), mono(12f, C.ink), Modifier.widthIn(min = 52.dp), align = TextAlign.Center)
            StepButton("+") { m.setS(d.k, minOf(k.max, v + 1)) }
        }
        is SettingKind.Opt -> {
            val open = m.openK == d.k
            T("${k.list[v.coerceIn(0, k.list.size - 1)]} ${if (open) "⌃" else "›"}", sora(13f, W.Regular, C.muted), Modifier.press { m.openK = if (open) "" else d.k }, maxLines = 1)
        }
        is SettingKind.Info -> T(k.value ?: m.infoText(k.key), mono(12f, C.ink2), align = TextAlign.End)
        is SettingKind.Act -> {
            var now by remember { mutableLongStateOf(System.currentTimeMillis()) }
            LaunchedEffect(k.id) { while (true) { delay(1000); now = System.currentTimeMillis() } }
            val c = m.confirm == k.id
            val (text, color) = actLabel(m, k.id, k.label, c, now)
            Box(
                Modifier.height(32.dp).clip(RoundedCornerShape(8.dp)).background(C.card2).skBorder(if (c) C.live else C.line2, 8.dp)
                    .press { m.runAction(k.id, k.safe) }.padding(horizontal = 12.dp),
                contentAlignment = Alignment.Center,
            ) { T(text, sora(12f, W.Regular, color), maxLines = 1) }
        }
        is SettingKind.Str -> if (!k.long) {
            SKField(k.placeholder, nameValue(m, d.k), { setName(m, d.k, k.max, it) }, Modifier.width(130.dp), height = 34.dp, size = 13f, radius = 8.dp, bg = C.card2, maxLength = k.max)
        }
        SettingKind.Eq -> SKLinkButton("Åpne ›") { m.tab = 1 }
        else -> {}
    }
}

@Composable
private fun Extra(m: AppModel, d: SettingItem, v: Int) {
    when (val k = d.kind) {
        is SettingKind.Str -> if (k.long) {
            SKField(k.placeholder, nameValue(m, d.k), { setName(m, d.k, k.max, it) }, height = 40.dp, size = 13f, radius = 8.dp, bg = C.card2,
                secure = k.secret, plainInput = true, maxLength = k.max, keyboard = if (d.k.endsWith("Url")) KeyboardType.Uri else KeyboardType.Text)
        }
        is SettingKind.Steps -> Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            k.steps.forEachIndexed { j, t ->
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    T("${j + 1}", mono(12f, C.accent), Modifier.width(18.dp))
                    T(t, sora(12f, W.Regular, C.ink2, 1.45f))
                }
            }
        }
        is SettingKind.Opt -> if (m.openK == d.k) Flow(6.dp) {
            k.list.forEachIndexed { j, label -> SKChip(label, on = v == j, height = 34.dp) { m.setS(d.k, j); m.openK = "" } }
        }
        else -> {}
    }
}

@Composable
private fun StepButton(s: String, action: () -> Unit) {
    Box(Modifier.size(32.dp).clip(RoundedCornerShape(8.dp)).background(C.card2).skBorder(C.line2, 8.dp).press(onClick = action), contentAlignment = Alignment.Center) {
        T(s, sora(14f))
    }
}

private fun actLabel(m: AppModel, id: String, label: String, confirm: Boolean, now: Long): Pair<String, Color> {
    if (id == "ytmTest" && m.ytmT != null) {
        val c = (m.names["ytmCookie"] ?: "").trim()
        if (c.isEmpty()) return "Lim inn cookien først" to C.danger
        if (!c.contains("__Secure-3PAPISID")) return "Mangler __Secure-3PAPISID · hent på nytt" to C.danger
        // no YouTube Music service on the amplifier yet, so the cookie cannot be checked
        return if (m.demo) "Innlogget · Premium" to C.ok else "Ikke støttet ennå" to C.danger
    }
    val nd = m.ndT
    if (id == "ndTest" && nd != null) return if (nd == "busy") "Tester …" to C.ink2 else nd to (if (m.ndOK) C.ok else C.danger)
    val px = m.plexT
    if (id == "plexTest" && px != null) return if (px == "busy") "Tester …" to C.ink2 else px to (if (m.plexOK) C.ok else C.danger)
    val bt = m.btPairT
    if (id == "btPair" && bt != null && now - bt < 120_000) return "Synlig · ${ceil((120_000 - (now - bt)) / 1000.0).toInt()} s" to C.ink
    return if (confirm) "Trykk igjen" to C.danger else label to C.ink
}

// MARK: - 19 Radio favourites

private fun stationAbbr(n: String): String {
    val s = (if (n.startsWith("NRK ")) n.drop(4) else n).replace("Radio ", "")
    return s.split(" ").joinToString(" ") { it.take(4) }.take(7)
}

@Composable
fun RadioFavoritesView(m: AppModel) {
    val rl = m.radio
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        T("${rl.size} " + if (rl.size == 1) "favoritt" else "favoritter", sora(12f, W.Regular, C.muted))
        Spacer(Modifier.weight(1f))
        SKLinkButton(if (m.rEdit) "Ferdig" else "Endre rekkefølge", modifier = Modifier.padding(vertical = 4.dp)) { m.rEdit = !m.rEdit }
    }
    SKCard {
        rl.forEachIndexed { i, st ->
            val playing = m.input == 3 && m.stIdx == i && m.rTmp == null
            val a = art(st.name)
            Row(
                Modifier.fillMaxWidth().heightIn(min = 58.dp).background(if (playing) C.selBg else Color.Transparent).topLine(if (i > 0) C.line else Color.Transparent).padding(horizontal = 12.dp),
                verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                Box(Modifier.size(38.dp).clip(RoundedCornerShape(8.dp)), contentAlignment = Alignment.Center) {
                    ArtFill(a)
                    T(stationAbbr(st.name), sora(10f, W.Semibold, a.ink), align = TextAlign.Center)
                }
                Column(Modifier.weight(1f).press { m.playStation(i, open = false) }.padding(vertical = 8.dp), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    T(st.name, sora(14f))
                    T(st.genre, sora(11f, W.Regular, C.muted))
                }
                if (m.rEdit) {
                    Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                        EditButton(Icons.chevronUp, if (i > 0) C.ink else C.off, C.line2) {
                            if (i > 0) { val l = m.radio.toMutableList(); java.util.Collections.swap(l, i - 1, i); m.setRL(l) }
                        }
                        EditButton(Icons.chevronDown, if (i < rl.size - 1) C.ink else C.off, C.line2) {
                            if (i < m.radio.size - 1) { val l = m.radio.toMutableList(); java.util.Collections.swap(l, i + 1, i); m.setRL(l) }
                        }
                        EditButton(Icons.close, C.danger, hex(0x4a2522)) {
                            if (m.radio.size > 1) { val l = m.radio.toMutableList(); l.removeAt(i); m.setRL(l) }
                        }
                    }
                } else {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        T(if (playing) "Spiller" else "", sora(11f, W.Regular, C.accent2))
                        Box(Modifier.size(32.dp).press { m.fav = i; m.post(mapOf("type" to "set", "k" to "hold", "v" to i)) }, contentAlignment = Alignment.Center) {
                            T("★", sora(15f, W.Regular, if (m.fav == i) C.accent2 else C.off))
                        }
                    }
                }
            }
        }
    }
    val full = m.radioFull
    Box(
        Modifier.fillMaxWidth().height(46.dp).skBorder(if (full) C.line2 else C.selLine, 14.dp, dash = listOf(4f, 3f)).press { if (!full) { m.rAdd = true; m.q = "" } },
        contentAlignment = Alignment.Center,
    ) { T(if (full) "Maks ${SK.maxRadio} favoritter · fjern én for å legge til" else "+ Legg til kanal", sora(13f, W.Regular, if (full) C.muted else C.accent2)) }
    T("Rekkefølgen er den samme som på radioknappen. ★ spilles når du holder radioknappen inne.", sora(11f, W.Regular, C.muted))
}

@Composable
private fun EditButton(d: String, fg: Color, bd: Color, action: () -> Unit) {
    Box(Modifier.size(30.dp).clip(RoundedCornerShape(8.dp)).background(C.card2).skBorder(bd, 8.dp).press(onClick = action), contentAlignment = Alignment.Center) {
        SKIcon(d, 14.dp, 2.2f, fg)
    }
}

/** Add favourites: search (catalogue + Radio Browser) or a custom stream URL. */
@Composable
fun RadioAddView(m: AppModel) {
    SKBackButton("Favoritter") { m.rAdd = false }
    SKSegmented(listOf("Søk", "Fra URL"), if (m.rMode == "url") 1 else 0) { i -> m.rMode = if (i == 1) "url" else "sok" }
    if (m.rMode == "sok") {
        val ql = m.q.trim().lowercase()
        SKField("Søk etter kanal, by eller sjanger", m.q, { m.setQ(it) }, height = 44.dp, size = 15f)
        SKMonoLabel("NORSKE KANALER")
        AddList(m, SK.catalog.filter { ql.isEmpty() || (it.name + " " + it.genre).lowercase().contains(ql) }, null)
        if (m.rBusy) T("Søker i Radio Browser …", sora(12f, W.Regular, C.muted))
        val res = m.rRes ?: emptyList()
        val onl = res.filter { s -> SK.catalog.none { it.name.lowercase() == s.name.lowercase() } }.map { s ->
            Station(s.name, listOf(s.genre, s.country, if (s.br > 0) "${s.br} kbps" else s.codec).filter { it.isNotEmpty() }.joinToString(" · "), s.url)
        }
        if (onl.isNotEmpty()) {
            SKMonoLabel("FRA RADIO BROWSER")
            AddList(m, onl) { st -> res.firstOrNull { it.name == st.name }?.genre?.ifEmpty { null } ?: "Nettradio" }
        }
        if (ql.length < 3) T("Skriv minst tre bokstaver for å søke blant over 50 000 kanaler fra hele verden.", sora(12f, W.Regular, C.muted, 1.45f))
    } else UrlForm(m)
}

@Composable
private fun AddList(m: AppModel, list: List<Station>, newGenre: ((Station) -> String)?) {
    if (list.isEmpty()) return
    SKCard {
        list.forEachIndexed { i, st ->
            val has = m.favIndex(st.name) != null || m.radio.any { it.name.lowercase() == st.name.lowercase() }
            val full = m.radioFull
            val a = art(st.name)
            Row(
                Modifier.fillMaxWidth().heightIn(min = 52.dp).topLine(if (i > 0) C.line else Color.Transparent).padding(horizontal = 12.dp),
                verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                Box(Modifier.size(34.dp).clip(RoundedCornerShape(7.dp)), contentAlignment = Alignment.Center) {
                    ArtFill(a)
                    T(stationAbbr(st.name), sora(9f, W.Semibold, a.ink), align = TextAlign.Center)
                }
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    T(st.name, sora(14f), maxLines = 1)
                    T(st.genre, sora(11f, W.Regular, C.muted), maxLines = 1)
                }
                Box(
                    Modifier.height(30.dp).skCapsuleBorder(if (has || full) C.line2 else C.accent)
                        .press { if (!has && !full) m.setRL(m.radio + Station(st.name, newGenre?.invoke(st) ?: st.genre, st.url)) }.padding(horizontal = 12.dp),
                    contentAlignment = Alignment.Center,
                ) { T(if (has) "Lagt til" else if (full) "Fullt" else "Legg til", sora(12f, W.Regular, if (has || full) C.muted else C.accent2)) }
            }
        }
    }
}

@Composable
private fun UrlForm(m: AppModel) {
    val u = m.uUrl.trim()
    val okUrl = Regex("""^https?://\S+\.\S+""", RegexOption.IGNORE_CASE).containsMatchIn(u)
    val nm = m.uName.trim()
    val isPl = Regex("""\.(m3u8?|pls)(\?|$)""", RegexOption.IGNORE_CASE).containsMatchIn(u)
    val has = m.radio.any { it.name.lowercase() == nm.lowercase() }
    val full = m.radioFull
    val canAdd = okUrl && nm.isNotEmpty() && !full && !has
    val msg: Pair<String, Color> = when {
        u.isEmpty() -> "Støtter MP3, AAC, OGG, FLAC og spillelister (.m3u, .pls)." to C.muted
        !okUrl -> "Adressen må starte med http:// eller https://" to C.danger
        m.uTest == "busy" -> "Tester strømmen …" to C.ink2
        m.uTest == "ok" -> "Strømmen virker." to C.ok
        m.uTest == "bad" -> if (isPl) "Spilleliste. Lyrion henter strømmen fra den ved avspilling." to C.ink2 else "Fikk ikke kontakt med strømmen. Sjekk adressen." to C.danger
        else -> "Trykk Test for å sjekke at strømmen virker." to C.muted
    }
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        SKField("Navn, for eksempel Jazzradio", m.uName, { m.uName = it.take(40); m.uDone = "" }, height = 44.dp, size = 15f)
        SKField("https://… strømadresse", m.uUrl, { m.uUrl = it; m.uTest = null; m.uDone = "" }, height = 44.dp, size = 13f, mono = true, keyboard = KeyboardType.Uri, plainInput = true)
        SKField("Sjanger (valgfritt)", m.uGenre, { m.uGenre = it.take(30) }, height = 44.dp, size = 15f)
        T(msg.first, sora(12f, W.Regular, msg.second, 1.45f))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Box(Modifier.height(44.dp).clip(RoundedCornerShape(12.dp)).background(C.card2).skBorder(C.line2, 12.dp).press { if (okUrl) m.testCustomStream() }.padding(horizontal = 18.dp), contentAlignment = Alignment.Center) {
                T("Test", sora(14f))
            }
            Box(
                Modifier.weight(1f).height(44.dp).clip(RoundedCornerShape(12.dp)).background(if (canAdd) C.accent else C.line).press {
                    if (canAdd) {
                        val g = m.uGenre.trim()
                        m.setRL(m.radio + Station(nm, g.ifEmpty { "Egen strøm" }, u))
                        m.uName = ""; m.uUrl = ""; m.uGenre = ""; m.uTest = null; m.uDone = nm
                    }
                },
                contentAlignment = Alignment.Center,
            ) {
                T(if (full) "Fullt · fjern en favoritt først" else if (nm.isNotEmpty() && has) "Finnes allerede" else "Legg til i favoritter", sora(14f, W.Semibold, if (canAdd) C.bg else C.dim), maxLines = 1)
            }
        }
        if (m.uDone.isNotEmpty()) T("«${m.uDone}» er lagt til i favorittene.", sora(12f, W.Regular, C.ok))
    }
}

// MARK: - Oppdatering

@Composable
fun UpdateSettingsView(m: AppModel) {
    val uri = LocalUriHandler.current
    val u = m.upd
    val busy = m.job?.let { !it.done } ?: false
    val idle = !busy && !m.checking
    val j = m.job
    val ju = j?.upd
    val msg: Pair<String, Boolean>? = if (j != null && j.done && ju != null) {
        if (j.failed) "Oppdateringen feilet ved oppstart. Forrige versjon (${ju.version}) er gjenopprettet automatisk, og alt virker som før." to true
        else "Ferdig. Skjold ${ju.version} kjører nå." to false
    } else if (m.updMsg.isEmpty()) null else m.updMsg to false

    @Composable
    fun link(title: String, url: String) = T(title, sora(12f, W.Regular, C.accent), Modifier.press { try { uri.openUri(url) } catch (_: Exception) {} }, maxLines = 1)

    Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Column(Modifier.fillMaxWidth().skBox(C.card, C.line).padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(verticalAlignment = Alignment.Top, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    T("Installert", sora(12f, W.Regular, C.muted))
                    T("Skjold ${u.version}", sora(22f, W.Semibold))
                }
                link("github.com/${u.repo} ↗", "https://github.com/${u.repo}/releases")
            }
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                listOf("Stabil", "Beta").forEachIndexed { i, label ->
                    val on = u.channel == i
                    SKChip(label, height = 32.dp, radius = 14.dp, style = SelStyle(if (on) C.accent else C.line2, if (on) C.selBg2 else C.card2, if (on) C.accent2 else C.ink)) {
                        m.upd = m.upd.copy(channel = i, latest = null)
                    }
                }
            }
            Row(verticalAlignment = Alignment.CenterVertically) {
                T("Installer automatisk om natten", sora(13f), Modifier.weight(1f))
                SKToggle(u.auto) { m.upd = m.upd.copy(auto = !m.upd.auto) }
            }
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    T("Demo: la neste oppdatering feile", sora(13f))
                    T("Viser automatisk gjenoppretting", sora(11f, W.Regular, C.muted))
                }
                SKToggle(u.failNext, C.live) { m.upd = m.upd.copy(failNext = !m.upd.failNext) }
            }
            if (idle || m.checking) {
                Box(Modifier.fillMaxWidth().height(42.dp).clip(RoundedCornerShape(14.dp)).background(C.card2).skBorder(C.line2, 14.dp).press { if (idle) m.checkUpdate() }, contentAlignment = Alignment.Center) {
                    T(if (m.checking) "Sjekker GitHub …" else "Se etter oppdatering", sora(13f))
                }
            }
            if (msg != null && !busy) {
                Box(Modifier.fillMaxWidth().skBox(if (msg.second) hex(0x2a1412) else hex(0x16201a), if (msg.second) hex(0x5a2620) else hex(0x2a4a33), 8.dp).padding(vertical = 10.dp, horizontal = 12.dp)) {
                    T(msg.first, sora(13f, W.Regular, if (msg.second) hex(0xff9a8a) else hex(0x9be0a8), 1.45f))
                }
            }
        }

        val rel = u.latest
        if (rel != null && !busy) {
            Column(Modifier.fillMaxWidth().skBox(C.selBg, C.selLine).padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    T(rel.name, sora(16f, W.Semibold), Modifier.weight(1f))
                    T("${rel.tag} · ${rel.date} · ${rel.size}", mono(11f, hex(0xc9b48a)))
                }
                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) { for (n in rel.notes) T("· $n", sora(13f, W.Regular, hex(0xe8dcc4), 1.45f)) }
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    if (idle) Box(Modifier.height(40.dp).clip(RoundedCornerShape(14.dp)).background(C.accent).press { m.installUpdate() }.padding(horizontal = 16.dp), contentAlignment = Alignment.Center) {
                        T("Installer ${rel.tag}", sora(13f, W.Semibold, C.bg))
                    }
                    link("Se på GitHub ↗", "https://github.com/${u.repo}/releases/tag/${rel.tag}")
                }
                T("Det tas automatisk backup før installering. Hvis forsterkeren ikke starter etterpå, gjenopprettes forrige versjon.", sora(11f, W.Regular, hex(0xc9b48a)))
            }
        }

        if (busy && j != null) {
            Column(Modifier.fillMaxWidth().skBox(C.card, C.line).padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Row { T(j.step, sora(13f), Modifier.weight(1f)); T("${j.pct} %", mono(12f)) }
                Box(Modifier.fillMaxWidth().height(6.dp).clip(RoundedCornerShape(3.dp)).background(C.line)) {
                    Box(Modifier.fillMaxWidth(j.pct / 100f).height(6.dp).background(C.accent))
                }
                T("Ikke slå av forsterkeren.", sora(11f, W.Regular, C.muted))
            }
        }

        Row(verticalAlignment = Alignment.CenterVertically) {
            T("Backup", sora(14f, W.Semibold), Modifier.weight(1f))
            if (idle) SKLinkButton("Ta backup nå", modifier = Modifier.padding(vertical = 4.dp)) { m.backupNow() }
        }
        if (u.backups.isNotEmpty()) SKCard {
            u.backups.forEachIndexed { i, b ->
                val cur = b.ver == u.version; val c = m.restoreConf == b.id
                Row(Modifier.fillMaxWidth().topLine(if (i > 0) C.line else Color.Transparent).padding(vertical = 12.dp, horizontal = 14.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                        T("${b.ver} ${if (cur) "· installert" else ""}", sora(14f))
                        T("${b.date} · ${b.kind}", sora(11f, W.Regular, C.muted))
                    }
                    if (!busy && !cur) Box(Modifier.height(32.dp).clip(RoundedCornerShape(8.dp)).background(C.card2).skBorder(if (c) C.live else C.line2, 8.dp).press { m.restore(b) }.padding(horizontal = 12.dp), contentAlignment = Alignment.Center) {
                        T(if (c) "Trykk igjen" else "Gjenopprett", sora(12f, W.Regular, if (c) C.danger else C.ink))
                    }
                }
            }
        }

        if (u.log.isNotEmpty()) {
            T("Historikk", sora(14f, W.Semibold))
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                for (l in u.log) Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    T(l.date, mono(12f))
                    T(l.text, sora(12f, W.Regular, if (l.bad) hex(0xff9a8a) else C.ink2, 1.4f))
                }
            }
        }
    }
}

// MARK: - Standby clocks (Skjerm og lys)

@Composable
fun ClockPicker(m: AppModel) {
    val sel = m.sset["clockStyle"] ?: 0
    var now by remember { mutableLongStateOf(System.currentTimeMillis()) }
    LaunchedEffect(Unit) { while (true) { delay(15_000); now = System.currentTimeMillis() } }
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            T("Klokke i standby", sora(14f, W.Semibold), Modifier.weight(1f))
            SKLinkButton("Vis på forsterkeren", 12f) { m.post(mapOf("type" to "previewClock")) }
        }
        SK.clocks.chunked(2).forEachIndexed { row, pair ->
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                pair.forEachIndexed { k, label ->
                    val i = row * 2 + k
                    val on = sel == i
                    Column(Modifier.weight(1f).skBox(if (on) C.selBg else C.card, if (on) C.accent else C.line).press { m.setS("clockStyle", i) }.padding(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        ClockFace(i, now, if (on) hex(0xe8e8e2) else C.muted, Modifier.fillMaxWidth().aspectRatio(2f).clip(RoundedCornerShape(6.dp)).background(Color.Black))
                        Row(Modifier.padding(horizontal = 2.dp)) {
                            T(label, sora(12f, W.Regular, if (on) C.accent2 else C.ink2), Modifier.weight(1f))
                            T(if (on) "✓" else "", sora(12f, W.Regular, if (on) C.accent2 else C.ink2))
                        }
                    }
                }
            }
        }
        T("Vises dempet på skjermen og flytter seg litt hvert minutt for å unngå innbrenning.", sora(11f, W.Regular, C.muted))
    }
}

private val hw = listOf("tolv", "ett", "to", "tre", "fire", "fem", "seks", "sju", "åtte", "ni", "ti", "elleve", "tolv")
private val days = listOf("søndag", "mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag")
private val months = listOf("januar", "februar", "mars", "april", "mai", "juni", "juli", "august", "september", "oktober", "november", "desember")

private fun wordTime(hour: Int, minute: Int): Pair<String, String> {
    val mm = ((minute / 5.0).roundToInt() * 5) % 60
    val h = (hour + if (minute >= 58) 1 else 0) % 12
    val n = hw[if (h == 0) 12 else h]; val n1 = hw[if ((h + 1) % 12 == 0) 12 else (h + 1) % 12]
    val table = listOf("klokka er" to n, "fem over" to n, "ti over" to n, "kvart over" to n, "ti på halv" to n1, "fem på halv" to n1,
        "halv" to n1, "fem over halv" to n1, "ti over halv" to n1, "kvart på" to n1, "ti på" to n1, "fem på" to n1)
    return table[mm / 5]
}

private fun cap(s: String) = s.replaceFirstChar { it.uppercase() }

/** drawClock(): 128×64 logical OLED pixels, scaled to fit. */
@Composable
fun ClockFace(style: Int, now: Long, color: Color, modifier: Modifier) {
    val tm = rememberTextMeasurer()
    Canvas(modifier) {
        val k = size.width / 128; val oy = (size.height - 64 * k) / 2
        val cal = Calendar.getInstance().apply { timeInMillis = now }
        val h = cal.get(Calendar.HOUR_OF_DAY); val mi = cal.get(Calendar.MINUTE)
        val hh = "%02d".format(h); val mm = "%02d".format(mi)
        val wd = cal.get(Calendar.DAY_OF_WEEK) - 1; val day = cal.get(Calendar.DAY_OF_MONTH); val mon = cal.get(Calendar.MONTH)
        fun text(s: String, weight: Int, px: Float, x: Float, y: Float, align: Float = 0.5f) {
            val st = TextStyle(fontFamily = SoraFamily, fontWeight = FontWeight(weight.coerceAtMost(600)), fontSize = (px * k / density / fontScale).sp, color = color)
            val l = tm.measure(s, st)
            // canvas baseline: anchor at the bottom of the glyph box minus the descender
            val bx = x * k - l.size.width * align
            val by = oy + y * k + px * k * 0.22f - l.size.height
            drawText(l, topLeft = Offset(bx, by))
        }
        fun fill(x: Float, y: Float, w: Float, hgt: Float) = drawRect(color, Offset(x * k, oy + y * k), Size(w * k, hgt * k))
        when (style) {
            0 -> text("$hh:$mm", 300, 22f, 64f, 40f)
            1 -> text("$hh:$mm", 700, 40f, 64f, 47f)
            2 -> {
                val cx = 40f; val cy = 32f; val r = 24f
                drawCircle(color, r * k, Offset(cx * k, oy + cy * k), style = Stroke(k))
                val p = Path()
                for (i in 0 until 12) {
                    val a = i / 12f * Math.PI.toFloat() * 2; val l = if (i % 3 == 0) 4f else 2f
                    p.moveTo((cx + sin(a) * (r - 1.5f)) * k, oy + (cy - cos(a) * (r - 1.5f)) * k)
                    p.lineTo((cx + sin(a) * (r - 1.5f - l)) * k, oy + (cy - cos(a) * (r - 1.5f - l)) * k)
                }
                drawPath(p, color, style = Stroke(k))
                val ha = ((h % 12) + mi / 60f) / 12f * Math.PI.toFloat() * 2; val ma = mi / 60f * Math.PI.toFloat() * 2
                fun hand(a: Float, len: Float, w: Float) = drawLine(color, Offset(cx * k, oy + cy * k), Offset((cx + sin(a) * len) * k, oy + (cy - cos(a) * len) * k), w * k, StrokeCap.Round)
                hand(ha, 12f, 2.4f); hand(ma, 19f, 1.4f)
                drawCircle(color, 1.6f * k, Offset(cx * k, oy + cy * k))
                text(cap(days[wd].take(3)), 600, 9f, 74f, 30f, 0f)
                text("$day. " + months[mon].take(3), 400, 8f, 74f, 41f, 0f)
            }
            3 -> { val (a, b) = wordTime(h, mi); text(a, 300, 11f, 64f, 28f); text(b, 600, 15f, 64f, 45f) }
            4 -> {
                val p = (h * 60 + mi) / 1440f
                fill(8f, 40f, 112f, 0.8f)
                for (i in 0..24 step 6) fill(8 + 112 * i / 24f - 0.4f, 37.5f, 0.8f, 5f)
                drawCircle(color, 2.4f * k, Offset((8 + 112 * p) * k, oy + 40.4f * k))
                text("$hh:$mm", 400, 10f, 8 + 112 * p, 31f, if (p > 0.75f) 1f else if (p < 0.25f) 0f else 0.5f)
            }
            else -> {
                text("$hh:$mm", 300, 26f, 64f, 34f)
                text(cap(days[wd]) + " $day. " + months[mon], 400, 8f, 64f, 48f)
            }
        }
    }
}
