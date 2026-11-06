package no.kristo.skjold

import kotlinx.serialization.Serializable
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

// Kotlin version of SkjoldData.swift (skjold_settings.js). Same ids and keys as the amplifier menu and the web UI.

// MARK: - Settings schema

enum class NumFormat {
    DB, BAL;

    fun format(v: Int): String = when (this) {
        DB -> (if (v > 0) "+" else if (v < 0) "−" else "") + "${kotlin.math.abs(v)} dB"
        BAL -> if (v == 0) "Midt" else (if (v < 0) "V " else "H ") + "${kotlin.math.abs(v)}"
    }
}

sealed class SettingKind {
    object Eq : SettingKind()
    data class Num(val min: Int, val max: Int, val format: NumFormat) : SettingKind()
    data class Opt(val list: List<String>) : SettingKind()
    object Bool : SettingKind()
    data class Str(val placeholder: String, val long: Boolean, val max: Int, val secret: Boolean) : SettingKind()
    data class Info(val value: String?, val key: String?) : SettingKind()
    data class Act(val id: String, val label: String, val safe: Boolean) : SettingKind()
    data class Steps(val steps: List<String>) : SettingKind()
    object Update : SettingKind()
    object Clocks : SettingKind()
}

data class SettingItem(val kind: SettingKind, val k: String, val n: String, val hint: String? = null, val dev: List<String>? = null) {
    companion object {
        fun num(k: String, n: String, mn: Int, mx: Int, f: NumFormat, hint: String? = null, dev: List<String>? = null) = SettingItem(SettingKind.Num(mn, mx, f), k, n, hint, dev)
        fun opt(k: String, n: String, list: List<String>, hint: String? = null, dev: List<String>? = null) = SettingItem(SettingKind.Opt(list), k, n, hint, dev)
        fun bool(k: String, n: String, hint: String? = null, dev: List<String>? = null) = SettingItem(SettingKind.Bool, k, n, hint, dev)
        fun str(k: String, n: String, ph: String, hint: String? = null, long: Boolean = false, max: Int = 14, secret: Boolean = false, dev: List<String>? = null) =
            SettingItem(SettingKind.Str(ph, long, max, secret), k, n, hint, dev)
        fun info(n: String, key: String? = null, hint: String? = null, value: String? = null) = SettingItem(SettingKind.Info(value, key), key ?: n, n, hint)
        fun act(n: String, id: String, label: String, safe: Boolean = false, hint: String? = null, dev: List<String>? = null) =
            SettingItem(SettingKind.Act(id, label, safe), id, n, hint, dev)
    }
}

data class SettingCategory(val id: String, val n: String, val sub: String, val dev: List<String>? = null, val items: List<SettingItem>)

// MARK: - Value types

@Serializable
data class Station(val name: String, val genre: String, val url: String? = null, val image: String? = null)

data class Track(
    val t: String, val artist: String, val album: String, val dur: Int,
    /** Live libraries: service id, cover URL and a stream URL the amplifier can play. Empty for demo tracks. */
    val id: String = "", val cover: String = "", val stream: String = "",
)

@Serializable
data class Room(
    val id: String, val name: String, val type: String, val hw: String, val vol: Int,
    val group: String? = null, val np: List<String>? = null, val role: Int? = null,
    /** Skjold daemon ("ip:port") when the room is a Skjold device, null for a plain Lyrion player. */
    val host: String? = null,
    /** Lyrion playerid (Squeezelite MAC) used for sync and per-room volume. */
    val pid: String? = null,
)

@Serializable
data class SystemState(val active: String, val rooms: List<Room>, val modes: Map<String, String> = emptyMap()) {
    fun groupOf(id: String): List<Room> {
        val r = rooms.firstOrNull { it.id == id } ?: return emptyList()
        val g = r.group ?: return listOf(r)
        return rooms.filter { it.group == g }
    }

    fun groupLabel(id: String): String {
        val g = groupOf(id)
        val first = g.firstOrNull() ?: return ""
        return (g.firstOrNull { it.id == id } ?: first).name + if (g.size > 1) " + ${g.size - 1}" else ""
    }

    fun toggledInGroup(activeId: String, id: String): SystemState {
        val rs = rooms.toMutableList()
        val ai = rs.indexOfFirst { it.id == activeId }
        val ri = rs.indexOfFirst { it.id == id }
        if (ai < 0 || ri < 0 || ai == ri) return this
        if (rs[ai].group == null) rs[ai] = rs[ai].copy(group = "g${System.currentTimeMillis()}")
        val g = rs[ai].group
        rs[ri] = if (rs[ri].group == g) rs[ri].copy(group = null) else rs[ri].copy(group = g, np = null)
        if (rs.count { it.group == g } == 1) rs[ai] = rs[ai].copy(group = null)
        return copy(rooms = rs)
    }

    fun groupedAll(): SystemState = copy(rooms = rooms.map { it.copy(group = "gall", np = null) })

    fun withGroupMode(gid: String, mode: String): SystemState {
        val m = modes.toMutableMap(); m[gid] = mode
        var rs = rooms
        if (mode == "surround") {
            var i = 0
            rs = rooms.map { r ->
                if (r.group == gid && r.role == null) { val n = r.copy(role = listOf(0, 3, 4, 5)[minOf(3, i)]); i++; n } else r
            }
        }
        return copy(rooms = rs, modes = m)
    }
}

@Serializable
data class EQProfile(val preset: Int, val eq: List<Int>, val loud: Boolean)

@Serializable
data class Release(val tag: String, val name: String, val date: String, val notes: List<String>, val size: String, val pre: Boolean)

@Serializable
data class Backup(val id: String, val ver: String, val date: String, val kind: String)

@Serializable
data class UpdateLog(val date: String, val text: String, val bad: Boolean = false)

@Serializable
data class UpdateState(
    val version: String, val repo: String, val channel: Int, val auto: Boolean, val failNext: Boolean,
    val latest: Release? = null, val checkedAt: String, val log: List<UpdateLog>, val backups: List<Backup>,
)

/** A Skjold device the app has talked to. Saved, so rooms survive restarts and NSD hiccups. */
@Serializable
data class KnownDevice(val host: String, val id: String, val name: String, val product: String)

// MARK: - Catalog

object SK {
    val names = listOf("Skjold S1", "Stue", "Kontor", "Soverom")
    val presetsRadio = listOf("NRK P1", "NRK P2", "NRK P3", "P4 Norge", "Radio Norge", "NRK Klassisk")
    const val maxRadio = 50

    private val S = SettingItem
    val cats: List<SettingCategory> = listOf(
        SettingCategory("eq", "Equalizer", "Egen profil per inngang", items = listOf(SettingItem(SettingKind.Eq, "eq", "Equalizer"))),
        SettingCategory("lyd", "Lyd", "Tone, volum og nivå", items = listOf(
            S.num("bass", "Bass", -6, 6, NumFormat.DB), S.num("treb", "Diskant", -6, 6, NumFormat.DB), S.num("bal", "Balanse", -5, 5, NumFormat.BAL),
            S.opt("vstart", "Startvolum", listOf("Sist brukt", "20", "30", "40")), S.opt("vmax", "Maksvolum", listOf("100", "90", "80", "70")),
            S.bool("perIn", "Volum per inngang", "Hver inngang husker sitt eget volum", dev = listOf("s1", "node")),
            S.bool("hpOwn", "Eget volum for hodetelefoner", dev = listOf("s1")),
            S.num("lvlAux", "Nivå AUX", -6, 6, NumFormat.DB, "Juster så AUX er like høy som strømming", dev = listOf("s1")),
            S.num("lvlUsb", "Nivå USB", -6, 6, NumFormat.DB, dev = listOf("s1")),
            S.act("Test høyttalerne", "testSpk", "Spill av", true, "Spiller en kort tone i venstre og så i høyre høyttaler, så du kan sjekke at de er koblet riktig"),
            S.act("Romkorreksjon", "roomeq", "Mål rommet", true, "Mål bassen i rommet med mikrofonen på telefonen, og la Skjold dempe toppene mellom 40 og 300 Hz"),
            S.act("Platesamling: ta opp side", "vinylSide", "Start", true, "Spill platen på AUX. Skjold tar opp siden, deler den i spor og gjenkjenner albumet. Trykk igjen for side B."),
            S.act("Platesamling: side ferdig", "vinylStop", "Ferdig", true),
            S.act("Platesamling: lagre platen", "vinylSave", "Lagre", true, "FLAC med omslag på NAS-en fra Radioopptak. Rett titler i web-UI-et under Integrasjoner → Platesamling."))),
        SettingCategory("touch", "Skjold Touch", "Rolle, skjerm og standby", dev = listOf("touch"), items = listOf(
            S.opt("tRole", "Rolle", listOf("Spiller og fjernkontroll", "Bare spiller", "Bare fjernkontroll"), "Som spiller har den egen lydutgang (RCA og 3,5 mm). Som fjernkontroll styrer den alle Skjold-enhetene i huset."),
            S.opt("tOut", "Lydutgang", listOf("RCA", "3,5 mm", "Begge"), "PCM5122 HIFI HAT"),
            S.opt("tStandby", "Standby etter", listOf("Aldri", "30 s", "1 min", "5 min"), "Uten trykk på skjermen"),
            S.opt("tIdle", "I standby vis", listOf("Klokke", "Cover og klokke", "Svart")),
            S.bool("tNight", "Nattmodus", "Rødlig, svakt lys mellom 23 og 07"))),
        SettingCategory("utgang", "Lydutgang", "DAC, HDMI, optisk eller 3,5 mm", dev = listOf("node", "core", "touch"), items = listOf(
            S.opt("out", "Utgang", listOf("3,5 mm (innebygd)", "HDMI", "USB-DAC", "I²S-kort (HiFiBerry / IQaudio)", "Optisk (S/PDIF)"), "Pi 3B og Pi 4 har 3,5 mm og HDMI. Et I²S-kort gir best lyd."),
            S.opt("hat", "I²S-kort", listOf("Spotpear HIFI HAT (PCM5122)", "HiFiBerry DAC+", "HiFiBerry DAC2 HD", "IQaudio DAC Pro", "Allo Boss"), "Brukes bare når utgang er I²S-kort"),
            S.opt("rate", "Samplingsfrekvens", listOf("44,1 kHz", "48 kHz", "96 kHz", "Følg kilden")),
            S.opt("mixer", "Volumkontroll", listOf("Programvare", "Maskinvare (DAC)", "Fast 100 % (styres av forsterker)"), "Velg fast hvis enheten er koblet til en egen forsterker med volumknapp"),
            S.act("Test utgang", "testOut", "Spill testtone", true))),
        SettingCategory("tilkobling", "Tilkobling", "Wi-Fi, navn og Blåtann", items = listOf(
            S.opt("name", "Enhetsnavn", names, "Navnet som vises i AirPlay og Blåtann"),
            S.str("nAux1", "Navn på AUX 1", "AUX 1", "Vises på skjermen og i appen", dev = listOf("s1")), S.str("nAux2", "Navn på AUX 2", "AUX 2", dev = listOf("s1")),
            S.str("nUsb1", "Navn på USB-C «PC 1»", "PC", "For eksempel Mac eller Jobb-PC", dev = listOf("s1")), S.str("nUsb2", "Navn på USB-C «PC 2»", "Switch", dev = listOf("s1")),
            S.info("Parede enheter", key = "btDev"),
            S.act("Blåtann-paring", "btPair", "Start paring", true, "Enheten har ingen knapp. Gjør den synlig for Blåtann i 2 minutter herfra.", dev = listOf("node", "core", "touch")),
            S.bool("btAuto", "Blåtann alltid synlig", "Kan pares uten å starte paring først. Mindre sikkert.", dev = listOf("node", "core", "touch")),
            S.act("Glem alle Blåtann-enheter", "forget", "Glem alle"))),
        SettingCategory("radio", "Radio", "Favoritter, knapper og oppstart", items = listOf(
            S.opt("hold", "Hold radioknappen", presetsRadio, "Kanalen som spilles når du holder radioknappen inne", dev = listOf("s1")),
            S.opt("nodeStart", "Kanal ved oppstart", listOf("Ingen") + presetsRadio, "Enheten har ingen knapper. Velg om den skal starte en radiokanal når den slås på.", dev = listOf("node", "core")))),
        SettingCategory("tjenester", "Musikktjenester", "Spotify, UPnP/DLNA, YouTube Music, Navidrome, Plex", items = listOf(
            S.bool("spEn", "Spotify Connect", "Vises som høyttaler i Spotify-appen"),
            S.bool("upnpEn", "UPnP/DLNA-mottaker", "Vises som høyttaler i apper som BubbleUPnP, foobar2000, Plex og «Cast til enhet» i Windows"),
            S.info("Navn på nettverket", key = "netName", hint = "Samme navn som i AirPlay. Endres under Enhet."),
            S.bool("ytmEn", "YouTube Music", "Krever YouTube Music Premium. Gratiskontoer virker ikke."),
            S.str("ytmUser", "Google-konto", "navn@gmail.com", "Gmail-adressen, eller den 21-sifrede ID-en for en merkekonto", long = true, max = 64),
            S.str("ytmCookie", "Innloggings-cookie", "Lim inn Cookie-verdien", "Google tillater ikke vanlig innlogging for andre apper. Cookien må hentes på nytt når den utløper.", long = true, max = 8000, secret = true),
            SettingItem(SettingKind.Steps(listOf("Åpne music.youtube.com i et privat vindu (inkognito) på en datamaskin og logg inn.", "Åpne utviklerverktøyene og velg fanen Nettverk (Network).", "Skriv /browse i filterfeltet. Åpne en av spillelistene dine.", "Klikk på forespørselen som dukker opp. Under Request Headers kopierer du hele verdien til Cookie, uten mellomrom foran eller bak.", "Lukk det private vinduet med en gang, uten å logge ut. Lim inn verdien over.")), "ytmSteps", "Slik henter du cookien"),
            S.info("PO-token-tjeneste", key = "ytmPo", hint = "Bekrefter overfor Google at avspillingen kommer fra en ekte YouTube-klient"),
            S.act("Test innlogging", "ytmTest", "Test", true),
            S.bool("ndEn", "Navidrome", "Eget musikkbibliotek via Subsonic-API"),
            S.str("ndUrl", "Navidrome-server", "http://192.168.1.10:4533", "Adressen til Navidrome-serveren på hjemmenettet"),
            S.str("ndUser", "Brukernavn", "brukernavn"),
            S.str("ndPass", "Passord", "Navidrome-passord", "Lagres på Skjold og deles med web-UI-et", long = true, max = 128, secret = true),
            S.act("Test Navidrome", "ndTest", "Test tilkobling", true),
            S.bool("plexEn", "Plex", "Spill musikk fra Plex Media Server"),
            S.str("plexUrl", "Plex-server", "http://192.168.1.20:32400", "Adressen til Plex Media Server på hjemmenettet", long = true, max = 120),
            S.str("plexToken", "Plex-token", "X-Plex-Token", "Finnes i Plex Web: åpne et album, velg ⋯ → Vis XML og kopier X-Plex-Token fra adressen", long = true, max = 64, secret = true),
            S.act("Test Plex", "plexTest", "Test tilkobling", true))),
        SettingCategory("stemme", "Stemme", "Talebeskjeder", items = listOf(
            S.bool("voice", "Talebeskjed ved bytte"), S.opt("lang", "Språk", listOf("Norsk", "English", "Svenska", "Dansk")), S.opt("vv", "Stemmevolum", listOf("Lav", "Middels", "Høy")),
            S.act("Test stemme", "testVoice", "Spill av", true))),
        SettingCategory("skjerm", "Skjerm og lys", "Dimming, klokke, LED", dev = listOf("s1"), items = listOf(
            S.opt("dim", "Dimme skjermen etter", listOf("Av", "30 s", "1 min")), S.opt("off", "Slukk skjermen etter", listOf("Av", "2 min", "5 min"), "Beskytter OLED-skjermen mot innbrenning"),
            S.bool("clock", "Klokke i standby"), SettingItem(SettingKind.Clocks, "clockStyle", "Klokke i standby"), S.opt("led", "LED-ringer", listOf("Høy", "Middels", "Lav", "Av")))),
        SettingCategory("strom", "Strøm", "Standby og påslag", items = listOf(
            S.opt("auto", "Auto-standby uten lyd", listOf("Av", "20 min", "60 min")), S.bool("wake", "Slå på ved signal", "AirPlay eller Blåtann vekker forsterkeren"))),
        SettingCategory("oppdatering", "Oppdatering", "GitHub, backup og gjenoppretting", items = listOf(SettingItem(SettingKind.Update, "update", "Oppdatering"))),
        SettingCategory("steder", "Steder", "Skjold-hjem: Hjem, Hytta … hovedenhet og reserve", items = listOf(SettingItem(SettingKind.Update, "steder", "Steder"))),
        SettingCategory("skjoldhjem", "Skjold-hjem", "Koble denne enheten til et sted", items = listOf(SettingItem(SettingKind.Update, "skjoldhjem", "Skjold-hjem"))),
        SettingCategory("system", "System", "Om, oppsett og tilbakestilling", items = listOf(
            S.info("Programvare", key = "version"), S.info("IP-adresse", key = "ip"),
            S.info("Lyrion", key = "lyrion"), S.info("Serienummer", key = "serial"),
            S.act("Kjør oppsett på nytt", "setup", "Start oppsett"),
            S.act("Fabrikkinnstillinger", "reset", "Tilbakestill"))),
    )

    /** Default setting values. Booleans are stored as 0/1. */
    val def: Map<String, Int> = mapOf("nodeStart" to 0, "btAuto" to 0, "out" to 3, "hat" to 0, "rate" to 3, "mixer" to 0, "clockStyle" to 0, "name" to 0, "lvlAux" to 0, "lvlUsb" to 0, "led" to 0, "voice" to 0, "lang" to 0, "vv" to 1, "hold" to 2, "bass" to 0, "treb" to 0, "bal" to 0, "vstart" to 0, "vmax" to 0, "perIn" to 1, "hpOwn" to 1, "dim" to 1, "off" to 1, "clock" to 1, "auto" to 1, "wake" to 1, "tRole" to 0, "tOut" to 2, "tStandby" to 1, "tIdle" to 0, "tNight" to 0)

    fun forDev(dev: List<String>?, type: String) = dev == null || dev.contains(type)

    fun catsFor(type: String): List<SettingCategory> =
        cats.filter { forDev(it.dev, type) }.map { c -> c.copy(items = c.items.filter { forDev(it.dev, type) }) }.filter { it.items.isNotEmpty() }

    // MARK: EQ

    val eqBands = listOf("60", "250", "1k", "4k", "12k")
    val eqNames = listOf("Dypbass", "Bass", "Mellomtone", "Presens", "Luft")
    val eqHz = listOf("60 Hz", "250 Hz", "1 kHz", "4 kHz", "12 kHz")
    val eqDesc = listOf("Den dype bassen du kjenner mer enn hører. Skru ned hvis små høyttalere dundrer.", "Fylde og varme. For mye gjør lyden grøtete.", "Der stemmer og instrumenter bor. Senk for en mykere, mer avslappet lyd.", "Gjør vokal og detaljer tydeligere. For mye blir skarpt.", "Cymbaler, glans og romfølelse.")
    val eqPresets: List<Pair<String, List<Int>>> = listOf("Flat" to listOf(0, 0, 0, 0, 0), "Bass+" to listOf(5, 2, 0, 0, 1), "Vokal" to listOf(-2, -1, 2, 3, 1), "Kveld" to listOf(2, 1, 0, -2, -3), "Podkast" to listOf(-5, -1, 3, 3, -2), "Klassisk" to listOf(1, 0, 0, 1, 2), "Rock" to listOf(4, 1, -2, 2, 3), "Pop" to listOf(2, 0, 1, 2, 2), "Elektronisk" to listOf(6, 1, -1, 1, 3), "Hip-hop" to listOf(6, 3, -1, 1, 1), "Jazz" to listOf(2, 1, -1, 1, 2), "Akustisk" to listOf(1, 2, 0, 2, 2), "Små høyttalere" to listOf(-4, 2, 1, 1, 0), "Lavt volum" to listOf(4, 1, -1, 1, 3))
    val eqSources: List<Pair<String, String>> = listOf("air" to "AirPlay", "bt" to "Blåtann", "radio" to "Radio", "aux" to "AUX", "usb" to "USB", "hp" to "Hodetelefoner")
    val eqDefaults = mapOf("air" to 0, "bt" to 1, "radio" to 2, "aux" to 0, "usb" to 0, "hp" to 3)

    // MARK: Radio

    val catalog: List<Station> = listOf("NRK P1" to "Distriktsprogram", "NRK P1+" to "Musikk for voksne", "NRK P2" to "Kultur og samfunn", "NRK P3" to "Pop og humor", "NRK mP3" to "Hits", "NRK Klassisk" to "Klassisk musikk", "NRK Jazz" to "Jazz", "NRK Folkemusikk" to "Folkemusikk", "NRK Alltid Nyheter" to "Nyheter", "NRK Sport" to "Sport", "P4 Norge" to "Hits", "P5 Hits" to "Hits", "P6 Rock" to "Rock", "P7 Klem" to "Ballader", "P9 Retro" to "80- og 90-tallet", "Radio Norge" to "Pop og rock", "NRJ" to "Dance og pop", "Radio Rock" to "Rock", "Kiss" to "Pop", "BBC Radio 6 Music" to "Alternativ").map { Station(it.first, it.second) }

    val defaultRadio: List<Station> = listOf("NRK P1" to "Distriktsprogram", "NRK P2" to "Kultur og samfunn", "NRK P3" to "Pop og humor", "P4 Norge" to "Hits", "Radio Norge" to "Pop og rock", "NRK Klassisk" to "Klassisk musikk").map { Station(it.first, it.second) }

    private val nowPlayingMap = mapOf("NRK P1" to ("Nyheter" to "NRK Dagsnytt"), "NRK P2" to ("Ekko" to "Et aktuelt samfunnsprogram"), "NRK P3" to ("Dance The Way I Feel" to "Ofenbach"), "P4 Norge" to ("Flowers" to "Miley Cyrus"), "Radio Norge" to ("Mr. Brightside" to "The Killers"), "NRK Klassisk" to ("Clair de lune" to "Claude Debussy"))

    fun nowPlaying(name: String): Pair<String, String> = nowPlayingMap[name] ?: ("Direkte" to name)

    /** Search query + country code used to find station logos on Radio Browser. */
    val logoQuery = mapOf("P4 Norge" to ("P4" to "NO"), "P5 Hits" to ("P5" to "NO"), "P6 Rock" to ("P6 Rock" to "NO"), "P7 Klem" to ("P7 Klem" to "NO"), "P9 Retro" to ("P9 Retro" to "NO"), "Radio Norge" to ("Radio Norge" to "NO"), "NRJ" to ("NRJ Norge" to "NO"), "Radio Rock" to ("Radio Rock" to "NO"), "Kiss" to ("Kiss" to "NO"), "BBC Radio 6 Music" to ("BBC Radio 6 Music" to "GB"), "NRK Alltid Nyheter" to ("NRK Alltid Nyheter" to "NO"))

    /** NRK logos ship as vector assets (static.nrk.no SVGs, in assets/nrk). */
    val nrkAsset = mapOf("NRK P1" to "nrk-p1", "NRK P1+" to "nrk-p1plus", "NRK P2" to "nrk-p2", "NRK P3" to "nrk-p3", "NRK mP3" to "nrk-mp3", "NRK Klassisk" to "nrk-klassisk", "NRK Jazz" to "nrk-jazz", "NRK Folkemusikk" to "nrk-folkemusikk", "NRK Sport" to "nrk-sport")

    // MARK: Devices and rooms

    data class DevType(val n: String, val d: String, val icon: String, val inputs: List<String>)

    val devTypes = mapOf(
        "s1" to DevType("Skjold S1", "Forsterker med skjerm, knapper og AUX/USB-innganger", "M3 7.5h18a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1v-7a1 1 0 0 1 1-1zM4.5 9.8h5v3.4h-5zM11.6 10.3a.6.6 0 1 0 1.2 0a.6.6 0 1 0-1.2 0M13.8 10.3a.6.6 0 1 0 1.2 0a.6.6 0 1 0-1.2 0M11.6 13.7a.6.6 0 1 0 1.2 0a.6.6 0 1 0-1.2 0M13.8 13.7a.6.6 0 1 0 1.2 0a.6.6 0 1 0-1.2 0M16.4 12a2.3 2.3 0 1 0 4.6 0a2.3 2.3 0 1 0-4.6 0M18.7 10.2v1.2M3.5 16.5v1M20.5 16.5v1", listOf("AirPlay", "Blåtann", "AUX", "Radio", "USB")),
        "node" to DevType("Skjold Node", "Raspberry Pi 3B eller 4 med bare lydutgang. Kobles til egen forsterker, aktive høyttalere eller DAC.", "M4 6h14a1.5 1.5 0 0 1 1.5 1.5v9A1.5 1.5 0 0 1 18 18H4a1.5 1.5 0 0 1-1.5-1.5v-9A1.5 1.5 0 0 1 4 6zM19.5 8h2v2.6h-2zM19.5 11.4h2v2.6h-2zM19.5 14.6h2v2h-2zM5 7.8h9M8 18v1.2M11.5 18v1.2M6.2 11.2h4.6v4.6H6.2zM15.2 15.3a.5.5 0 1 0 1 0a.5.5 0 1 0-1 0", listOf("AirPlay", "Blåtann", "Radio")),
        "core" to DevType("Skjold Core", "Sentral enhet uten skjerm. Kjører Lyrion-serveren for hele systemet og kan spille via linjeutgang eller digital utgang.", "M5 4h14a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1zM8 8h8v8H8zM12 4V2M12 22v-2M4 12H2M22 12h-2M10 11h4M10 13h4", listOf("AirPlay", "Blåtann", "Radio")),
    )

    fun dev(type: String): DevType = devTypes[type] ?: devTypes.getValue("s1")

    val roles = listOf("Stereo", "Venstre", "Høyre", "Bak V", "Bak H", "Sub")

    val sysDefault = SystemState("stue", listOf(
        Room("stue", "Stue", "s1", "Pi Zero 2 W · TPA3116 2 × 50 W", 42, group = "g1"),
        Room("kjokken", "Kjøkken", "node", "Raspberry Pi 4 · HiFiBerry DAC+", 30, group = "g1"),
        Room("kontor", "Kontor", "node", "Raspberry Pi 3B · 3,5 mm", 25, np = listOf("Teardrop", "Massive Attack", "AirPlay")),
        Room("core", "Hjemmekino", "core", "Raspberry Pi 5 · Lyrion-server · optisk ut", 35),
    ))

    // MARK: Updates

    val updDefault = UpdateState("1.4.2", GitHubReleases.REPO, 0, true, false, null, "", emptyList(), listOf(
        Backup("b3", "1.4.2", "2026-10-28 03:12", "Automatisk før oppdatering"),
        Backup("b2", "1.4.1", "2026-10-02 03:08", "Automatisk før oppdatering"),
        Backup("b1", "1.4.0", "2026-09-14 19:40", "Manuell"),
    ))

    fun now(): String = SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.US).format(Date())

    // MARK: Clocks

    val clocks = listOf("Tynn", "Stor", "Analog", "Ord", "Linje", "Dato")

    // MARK: Demo music library (same as the design file)

    val tr = listOf("Midnight City" to "M83", "Intro" to "The xx", "Breathe" to "Télépopmusik")
    val dur = listOf(243, 128, 279)
    val lt: List<Track> = listOf(
        Track("Eple", "Röyksopp", "Melody A.M.", 219), Track("Take On Me", "a-ha", "Hunting High and Low", 225),
        Track("Runaway", "AURORA", "All My Demons Greeting Me as a Friend", 249), Track("Strangers", "Sigrid", "Sucker Punch", 214),
        Track("Firestone", "Kygo", "Cloud Nine", 272), Track("Midnight City", "M83", "Hurry Up, We're Dreaming", 243),
        Track("Teardrop", "Massive Attack", "Mezzanine", 330), Track("Intro", "The xx", "xx", 128),
        Track("Breathe", "Télépopmusik", "Genetic World", 279), Track("Poor Leno", "Röyksopp", "Melody A.M.", 237),
        Track("Hunting High and Low", "a-ha", "Hunting High and Low", 225), Track("Murder Song (5, 4, 3, 2, 1)", "AURORA", "All My Demons Greeting Me as a Friend", 199),
    )

    data class Library(val name: String, val tabs: List<String>, val pls: List<Pair<String, List<Int>>>, val hist: List<Pair<Int, String>>)

    val lib = mapOf(
        "ytm" to Library("YouTube Music", listOf("Hjem", "Spillelister", "Historikk"), listOf("Likte låter" to (0..11).toList(), "Supermix" to listOf(5, 0, 2, 6, 1, 4), "Fredagskveld" to listOf(4, 3, 1, 10), "Nordisk ro" to listOf(2, 11, 0, 9)), listOf(3 to "I dag 21:40", 0 to "I dag 20:12", 5 to "I går 22:05", 1 to "I går 18:30")),
        "nd" to Library("Navidrome", listOf("Album", "Spillelister", "Historikk"), listOf("Favoritter" to listOf(6, 7, 8, 5), "Vinyl-rips" to listOf(0, 9, 1, 10), "Sent på kvelden" to listOf(7, 6, 8, 2)), listOf(6 to "I dag 19:02", 9 to "Mandag", 7 to "Søndag")),
        "plex" to Library("Plex", listOf("Album", "Spillelister", "Historikk"), listOf("Mest spilt" to listOf(1, 4, 3, 5, 0), "Søndagsmorgen" to listOf(8, 2, 7, 11), "Nordisk" to listOf(0, 1, 2, 3, 9, 10)), listOf(4 to "I dag 17:45", 1 to "I går 21:10", 8 to "Lørdag")),
    )

    val moods = listOf("Ny energi", "Godfølelse", "Avslapping", "Trening", "Fest", "Fokus", "Søvn")
}
