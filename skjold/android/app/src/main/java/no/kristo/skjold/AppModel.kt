package no.kristo.skjold

import android.app.Application
import android.content.Context
import android.content.SharedPreferences
import androidx.compose.runtime.MutableState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.serialization.KSerializer
import kotlinx.serialization.builtins.ListSerializer
import kotlinx.serialization.builtins.MapSerializer
import kotlinx.serialization.builtins.serializer
import kotlinx.serialization.json.Json
import kotlin.properties.ReadWriteProperty
import kotlin.reflect.KProperty

// MARK: - Persistence (UserDefaults ↔ SharedPreferences, same keys as iOS)

object Store {
    var prefs: SharedPreferences? = null
    val json = Json { ignoreUnknownKeys = true; encodeDefaults = true }

    fun init(ctx: Context) {
        if (prefs == null) prefs = ctx.getSharedPreferences("skjold", Context.MODE_PRIVATE)
    }

    fun <T> save(key: String, v: T, ser: KSerializer<T>) {
        prefs?.edit()?.putString(key, json.encodeToString(ser, v))?.apply()
    }

    fun <T> load(key: String, ser: KSerializer<T>): T? {
        val s = prefs?.getString(key, null) ?: return null
        return try { json.decodeFromString(ser, s) } catch (_: Exception) { null }
    }

    fun bool(key: String): Boolean = prefs?.getBoolean(key, false) ?: false
    fun setBool(key: String, v: Boolean) { prefs?.edit()?.putBoolean(key, v)?.apply() }
    fun string(key: String): String? = prefs?.getString(key, null)
    fun setString(key: String, v: String?) {
        prefs?.edit()?.apply { if (v == null) remove(key) else putString(key, v) }?.apply()
    }
}

/** Observable property that is written to SharedPreferences on every change (`didSet { Store.save(…) }`). */
class Persisted<T>(private val key: String, initial: T, private val ser: KSerializer<T>) : ReadWriteProperty<Any?, T> {
    private val state: MutableState<T> = mutableStateOf(initial)
    override fun getValue(thisRef: Any?, property: KProperty<*>): T = state.value
    override fun setValue(thisRef: Any?, property: KProperty<*>, value: T) {
        state.value = value
        Store.save(key, value, ser)
    }
}

enum class Mode { ONBOARD, APP }
enum class Link { NONE, CONNECTING, ONLINE, OFFLINE }

/** Navidrome / Plex content for LibraryView. `state`: "" not loaded, "busy", "ok", otherwise an error text. */
data class LibData(
    val state: String = "",
    val newest: List<LibColl> = emptyList(),
    val other: List<LibColl> = emptyList(),
    val frequent: List<LibColl> = emptyList(),
    val playlists: List<LibColl> = emptyList(),
    val tracks: Map<String, List<Track>> = emptyMap(),
) {
    /** All albums once, newest first. */
    val albums: List<LibColl>
        get() {
            val out = ArrayList<LibColl>()
            for (a in newest + other + frequent) if (out.none { it.id == a.id }) out.add(a)
            return out
        }
}

/**
 * App state: AppModel.swift + LiveSync.swift. Mirrors `state` and the logic in `class Component` of the design.
 * Compose snapshot state (mutableStateOf) plays the part of @Observable.
 */
class AppModel(app: Application) : AndroidViewModel(app) {
    data class NowPlaying(val st: String, val t: String, val s: String)
    data class HistEntry(val track: Track, val time: String)
    data class Job2(val done: Boolean = false, val failed: Boolean = false, val step: String = "", val pct: Int = 0, val upd: UpdateState? = null)
    data class PlayerArt(val key: String, val kicker: String, val big: String, val size: Float, val live: Boolean)

    init {
        Store.init(app)
        Haptics.init(app)
        LogoStore.load()
    }

    // MARK: Flow
    var mode by mutableStateOf(if (Store.bool("skjold-setup-done")) Mode.APP else Mode.ONBOARD)
    var welcome by mutableStateOf(mode != Mode.APP)
    var intro by mutableStateOf(true)
    var heroI by mutableStateOf(0)

    // MARK: Onboarding
    var ob by mutableStateOf(0)
    var scan by mutableStateOf(false)
    var camOK by mutableStateOf(false)
    var scanFound by mutableStateOf(false)
    var net by mutableStateOf(0)
    var netManual by mutableStateOf(false)
    var pw by mutableStateOf("")
    var ssid by mutableStateOf("")
    var sec by mutableStateOf(0)
    var room by mutableStateOf("Stue")
    var roomCustom by mutableStateOf(false)
    var tested by mutableStateOf(setOf<String>())
    var obUpd by mutableStateOf(0)
    var obType by mutableStateOf("s1")

    // MARK: Navigation
    var tab by mutableStateOf(0)
    var sub by mutableStateOf("")          // "", "radio", "lib"
    var lib by mutableStateOf("ytm")
    var libTab by mutableStateOf(0)
    var libPl by mutableStateOf<Int?>(null)
    var lq2 by mutableStateOf("")
    var libHero by mutableStateOf(0)
    var libMood by mutableStateOf<Int?>(null)
    var hist by mutableStateOf(mapOf<String, List<HistEntry>>())

    // MARK: Player
    var full by mutableStateOf(false)
    var queueOpen by mutableStateOf(false)
    var srcOpen by mutableStateOf(false)
    var shuffle by mutableStateOf(false)
    var repeatOn by mutableStateOf(false)
    var input by mutableStateOf(0)          // 0 AirPlay, 1 Blåtann, 2 AUX, 3 Radio, 4 USB
    var svc by mutableStateOf<String?>(null) // spotify, upnp, ytm, nd, plex
    var playing by mutableStateOf(true)
    var trk by mutableStateOf(0)
    var pos by mutableStateOf<Int?>(null)
    var vol by mutableStateOf(42)
    var lq by mutableStateOf<List<Track>?>(null)
    var li by mutableStateOf(0)

    // MARK: Radio
    var station by mutableStateOf(1)
    var fav by mutableStateOf(2)
    var rTmp by mutableStateOf<Station?>(null)
    var radio by Persisted("skjold-radio", Store.load("skjold-radio", ListSerializer(Station.serializer())) ?: SK.defaultRadio, ListSerializer(Station.serializer()))
    var rEdit by mutableStateOf(false)
    var rAdd by mutableStateOf(false)
    var q by mutableStateOf("")
    var rRes by mutableStateOf<List<RadioResult>?>(null)
    var rBusy by mutableStateOf(false)
    var rGenre by mutableStateOf<Int?>(null)
    var rMode by mutableStateOf("sok")
    var uName by mutableStateOf("")
    var uUrl by mutableStateOf("")
    var uGenre by mutableStateOf("")
    var uTest by mutableStateOf<String?>(null)
    var uDone by mutableStateOf("")

    // MARK: Settings
    var setCat by mutableStateOf(-1)
    var openK by mutableStateOf("")
    var confirm by mutableStateOf("")
    private var _setDev by mutableStateOf("stue")
    var setDev: String
        get() = _setDev
        set(v) {
            val old = _setDev
            _setDev = v
            if (live && old != v) settingsHost?.let { h -> viewModelScope.launch { loadSettings(h) } }
        }
    /** Hjemskjermens rekkefølge og synlighet (settings.homeLayout på den aktive Skjold-enheten). */
    var homeLayout by mutableStateOf<List<HomeItem>>(emptyList())
    var sset by Persisted("skjold-set", Store.load("skjold-set", MapSerializer(String.serializer(), Int.serializer())) ?: SK.def, MapSerializer(String.serializer(), Int.serializer()))
    var names by Persisted("skjold-names", Store.load("skjold-names", MapSerializer(String.serializer(), String.serializer())) ?: emptyMap(), MapSerializer(String.serializer(), String.serializer()))
    var ytmT by mutableStateOf<Long?>(null)
    var plexT by mutableStateOf<String?>(null)   // null, "busy", or the result text
    var plexOK by mutableStateOf(false)
    var btPairT by mutableStateOf<Long?>(null)
    var headphones by mutableStateOf(false)
    var showLyrionPlayers by mutableStateOf(Store.bool("skjold-show-lyrion-players"))

    // MARK: EQ / system / update
    var eqP by Persisted("skjold-eq", Store.load("skjold-eq", MapSerializer(String.serializer(), EQProfile.serializer())) ?: emptyMap(), MapSerializer(String.serializer(), EQProfile.serializer()))
    var eqSrc by mutableStateOf<String?>(null)
    var sys by Persisted("skjold-sys", Store.load("skjold-sys", SystemState.serializer()) ?: SK.sysDefault, SystemState.serializer())
    var upd by Persisted("skjold-upd", Store.load("skjold-upd", UpdateState.serializer()) ?: SK.updDefault, UpdateState.serializer())
    var job by mutableStateOf<Job2?>(null)
    var checking by mutableStateOf(false)
    var updMsg by mutableStateOf("")
    var restoreConf by mutableStateOf("")

    // MARK: Live system (LiveSync)
    var known by Persisted("skjold-known", Store.load("skjold-known", ListSerializer(KnownDevice.serializer())) ?: emptyList(), ListSerializer(KnownDevice.serializer()))
    private var _activeHost by mutableStateOf<String?>(Store.string("skjold-host"))
    var activeHost: String?
        get() = _activeHost
        set(v) { _activeHost = v; Store.setString("skjold-host", v); DeviceLink.host = v }
    var link by mutableStateOf(Link.NONE)

    // MARK: Skjold-hjem (Hjem.kt)
    var steder by mutableStateOf(listOf<HjemSted>())
    private var _stedId by mutableStateOf(Store.string("skjold-sted") ?: "")
    /** "" = «Dette nettverket» (LAN som før). Lagres. */
    var stedId: String
        get() = _stedId
        set(v) { _stedId = v; Store.setString("skjold-sted", v) }
    var stedEnheter by mutableStateOf(listOf<HjemEnhet>())
    /** Enhets-id → adressen som brukes: "ip:port" på LAN eller relé-URL via skyen. */
    var stedHosts by mutableStateOf(mapOf<String, String>())
    /** "", "laster", "ok", "login" eller feiltekst. */
    var hjemState by mutableStateOf("")
    var hjemLogin by mutableStateOf(false)
    var showKassett by mutableStateOf(false)  // «Lag kassett» (KassettView)
    var showRoomEQ by mutableStateOf(false)   // romkorreksjon med mikrofonen (RoomEQView)
    var showSpeakers by mutableStateOf(false)   // høyttalerprofil / Skjold Sertifisert (SpeakerView)
    var dev by mutableStateOf<DevStatus?>(null)
    val devStats = mutableStateMapOf<String, DevStatus?>()
    var lyrionServer by mutableStateOf<String?>(null)
    var lyPlayers by mutableStateOf(listOf<Lyrion.Player>())
    var lyStats by mutableStateOf(mapOf<String, Lyrion.PStatus>())
    var presetNs by mutableStateOf(listOf<Int>())
    var wifiNets by mutableStateOf(listOf<String>())
    var wifiBusy by mutableStateOf(false)
    var obErr by mutableStateOf("")
    var ndT by mutableStateOf<String?>(null)
    var ndOK by mutableStateOf(false)
    var libs by mutableStateOf(mapOf<String, LibData>())
    var libRes by mutableStateOf<List<Track>?>(null)
    val browser = DeviceBrowser(app)
    private val holds = HashMap<String, Long>()
    private var volWant: Int? = null
    private var volBusy = false
    private var libStream: String? = null
    private var libSawPlaying = false
    private var presetSig = ""
    private val tasks = HashMap<String, Job>()
    private var started = false

    init {
        val u = upd
        if (u.repo != GitHubReleases.REPO) upd = u.copy(repo = GitHubReleases.REPO, latest = null)
        if (eqP["air"] == null) {
            val eq = eqP.toMutableMap()
            for ((k, _) in SK.eqSources) {
                val p = SK.eqDefaults[k] ?: 0
                eq[k] = EQProfile(p, SK.eqPresets[p].second, k != "hp")
            }
            eqP = eq
        }
        DeviceLink.host = activeHost
        start()
    }

    // MARK: - Lifecycle

    fun start() {
        if (started) return
        started = true
        LogoStore.fetch(SK.catalog.map { it.name } + radio.map { it.name })
        run("intro") { delay(4700); intro = false }
        restartHero(heroI)
        run("pos") {
            while (isActive) {
                delay(1000)
                if (!playing || !hasProgress) continue
                val p = (pos ?: if (live) 0 else 45) + 1
                if (live) pos = minOf(p, duration)   // the amplifier advances by itself
                else if (p >= duration) next() else pos = p
            }
        }
        startLive()
        launch { startHjem() }
    }

    /** Bytt aktiv enhet til en adresse (LAN eller relé) uten å legge den i `known` (Skjold-hjem). */
    fun switchHost(h: String?) {
        activeHost = h
        dev = null
        devStats.clear()
        link = if (h == null) Link.NONE else Link.CONNECTING
        libStream = null
        rebuildRooms()
        if (h != null) {
            startEvents()
            launch { loadSettings(h) }
            launch { loadPresets() }
        }
    }

    fun restartHero(i: Int) {
        heroI = i
        run("hero") {
            while (isActive) {
                delay(2800)
                if (mode == Mode.ONBOARD && welcome) heroI = (heroI + 1) % 4
            }
        }
    }

    fun run(key: String, op: suspend CoroutineScope.() -> Unit) {
        tasks[key]?.cancel()
        tasks[key] = viewModelScope.launch(block = op)
    }

    private fun cancel(key: String) { tasks.remove(key)?.cancel() }

    private fun launch(op: suspend CoroutineScope.() -> Unit) = viewModelScope.launch(block = op)

    override fun onCleared() {
        browser.stop()
        super.onCleared()
    }

    /** The design's BroadcastChannel messages, mapped to the daemon API. Demo mode sends nothing. */
    fun post(msg: Map<String, Any?>) {
        val type = msg["type"] as? String ?: return
        if (!live) return
        when (type) {
            "setupTest" -> devSend("/api/test", mapOf("channel" to (msg["ch"] as? String ?: "L")))
            "testSpk", "testOut" -> speakerTest(settingsHost)
            "testVoice" -> devSend("/api/voice", mapOf("say" to "bt_pairing"), on = settingsHost)
            "vinylSide" -> devSend("/api/vinyl/start", emptyMap<String, Any>(), on = settingsHost)
            "vinylStop" -> devSend("/api/vinyl/stop", emptyMap<String, Any>(), on = settingsHost)
            "vinylSave" -> devSend("/api/vinyl/save", emptyMap<String, Any>(), on = settingsHost)
            "btPair" -> devSend("/api/bt", mapOf("pairing" to true), on = settingsHost)
            "src" -> (msg["v"] as? Int)?.let { livePlayFavourite(it) }
            "set" -> { val k = msg["k"] as? String; val v = msg["v"]; if (k != null && v != null) liveSetting(k, v) }
            "eqSync" -> (msg["src"] as? String)?.let { liveEQ(it) }
        }
    }

    // MARK: - Onboarding

    companion object {
        val obText = listOf(
            "Legg til forsterker" to "Slå på forsterkeren. Den dukker opp her.",
            "Koble til Wi-Fi" to "Sendes kryptert over Blåtann. Godta på forsterkeren med volumknappen.",
            "Hvor står den?" to "Navnet vises i AirPlay, Blåtann og Lyrion.",
            "Test høyttalerne" to "Trykk på en side og hør etter.",
            "Programvare" to "Installerer siste versjon.",
        )
        val roomList = listOf("Stue", "Kjøkken", "Soverom", "Kontor", "Barnerom", "Bad", "Gang", "Verksted")
        val demoNets = listOf("Hjemme", "Hjemme-5G", "Telenor-8F2A")
        val svcInfo = mapOf("upnp" to ("UPnP/DLNA" to ""), "spotify" to ("Spotify Connect" to ""), "ytm" to ("YouTube Music" to ""), "nd" to ("Navidrome" to " · FLAC"), "plex" to ("Plex" to " · FLAC"))
        val inputNames = listOf("airplay", "bt", "aux", "radio", "usb")
        val boolKeys: Set<String> = SK.cats.flatMap { it.items }.filter { it.kind == SettingKind.Bool }.map { it.k }.toSet() + setOf("updAuto", "setupDone")
        /** Service credentials stay on the phone (the daemon ignores unknown keys anyway). */
        val localKeys = setOf("ytmUser", "ytmCookie", "ndUrl", "ndUser", "ndPass", "plexUrl", "plexToken")
        val stringKeys = listOf("nAux1", "nAux2", "nUsb1", "nUsb2", "nameCustom")

        fun hwText(r: Room): String {
            val hw = if (r.type == "s1" && r.hw.contains("Raspberry Pi 4")) "Pi Zero 2 W · TPA3116 2 × 50 W" else r.hw
            // keep "2 × 50 W" together like the design's non-breaking spaces
            return hw.replace(" ×", " ×").replace("× ", "× ").replace(" W", " W").replace(" kHz", " kHz")
        }

        fun hw(type: String, st: DevStatus?): String {
            val base = mapOf("s1" to "Pi Zero 2 W · TPA3116 2 × 50 W", "node" to "Raspberry Pi · Skjold Node", "core" to "Raspberry Pi · Lyrion-server")[type] ?: "Raspberry Pi"
            val v = st?.version ?: ""
            return if (v.isEmpty()) base else "$base · v$v"
        }

        fun track(x: LibItem) = Track(x.title, x.artist, x.album, x.dur, x.id, x.cover, x.stream)
    }

    val needPw: Boolean get() = !netManual || sec < 2

    val okOb: Boolean
        get() = when (ob) {
            0 -> true
            1 -> (!netManual || ssid.isNotBlank()) && (!needPw || pw.length >= 8)
            2 -> if (roomCustom) room.isNotBlank() else room.isNotEmpty()
            3 -> tested.contains("L") && tested.contains("R")
            else -> obUpd >= 100
        }

    val obStep: Int get() = if (ob == 4) 3 else ob

    fun goOb(n: Int) {
        ob = n
        obErr = ""
        post(mapOf("type" to "setup", "step" to listOf(1, 2, 3, 4, 6)[minOf(n, 4)], "name" to room))
        if (n == 1 && live) loadWifi()
        if (n == 4 && live) checkUpdate()
        if (n == 4) {
            obUpd = 0
            run("obUpd") {
                while (obUpd < 100 && isActive) {
                    delay(110)
                    obUpd = minOf(100, obUpd + 5)
                    post(mapOf("type" to "setup", "step" to 6, "upd" to obUpd))
                }
            }
        }
    }

    fun obBack() {
        if (scan) { cancel("scan"); scan = false; return }
        goOb(if (ob == 4) 2 else ob - 1)
    }

    fun obNext() {
        if (!okOb) return
        if (live && ob == 1) { joinWifi(); return }
        if (live && ob == 2) {
            val name = room.trim()
            activeHost?.let { h -> launch { DeviceLink.send("/api/settings", mapOf("nameCustom" to name), on = h) } }
            names = names + ("nameCustom" to name)
        }
        // speaker test lives in Innstillinger → Lyd, not in setup
        if (ob < 4) { goOb(if (ob == 2) 4 else ob + 1); return }
        if (demo && obType == "node" && sys.rooms.none { it.name == room }) {
            sys = sys.copy(rooms = sys.rooms + Room("r${System.currentTimeMillis()}", room, "node", "Raspberry Pi 4 · HDMI", 30))
        }
        Haptics.success()
        mode = Mode.APP
        tab = if (obType == "node") 2 else 0
        Store.setBool("skjold-setup-done", true)
        post(mapOf("type" to "setup", "step" to 7, "name" to room))
        if (live) activeHost?.let { h -> launch { DeviceLink.send("/api/settings", mapOf("setupDone" to true), on = h) } }
        startLive()
        run("setupDone") { delay(3000); post(mapOf("type" to "setup", "step" to 8)) }
    }

    fun pickDevice(type: String) { obType = type; goOb(1) }

    /** GET /api/settings → setupDone. */
    suspend fun deviceSetupDone(host: String): Boolean {
        val j = jsonObject(DeviceLink.get("/api/settings", on = DeviceLink.normHost(host))) ?: return false
        val se = j.optJSONObject("settings") ?: j
        return se.optBoolean("setupDone", false)
    }

    /** Brukeren hopper over oppsettet: rett inn i appen. Uten lagrede enheter er appen i demomodus til en enhet legges til. */
    fun skipSetup() {
        Haptics.tap()
        welcome = false
        enterApp()
    }

    /** Hopp over oppsettet for en forsterker som allerede er satt opp. */
    fun enterApp() {
        scan = false
        mode = Mode.APP
        tab = if (obType == "node") 2 else 0
        Store.setBool("skjold-setup-done", true)
        startLive()
    }

    /** A real device in «Finn forsterker» (NSD or QR): connect, then continue the setup against it. */
    fun pickFound(host: String, type: String) {
        obType = type
        launch {
            val wasKnown = known.any { it.host == DeviceLink.normHost(host) }
            if (!connect(host)) { Haptics.error(); return@launch }
            Haptics.success()
            // Allerede satt opp (setupDone i daemonen, eller lagt til før): rett inn i appen, uten Wi-Fi/rom-stegene.
            val ready = wasKnown || deviceSetupDone(host)
            if (ready) enterApp() else goOb(1)
        }
    }

    /** Wi-Fi networks seen by the amplifier (GET /api/wifi, nmcli). */
    val nets: List<String> get() = if (live && wifiNets.isNotEmpty()) wifiNets else if (live) emptyList() else demoNets

    fun loadWifi() {
        wifiBusy = true
        launch {
            val d = DeviceLink.get("/api/wifi", timeout = 25.0)
            wifiBusy = false
            wifiNets = if (d != null) DevWifi.list(d) else emptyList()
            if (wifiNets.isEmpty()) netManual = true
        }
    }

    /** POST /api/wifi {ssid, psk, hidden}; the result shows in obErr. */
    fun joinWifi() {
        val name = if (netManual) ssid.trim() else nets.getOrElse(net) { "" }
        val h = activeHost
        if (name.isEmpty() || h == null) { goOb(2); return }
        val body = mutableMapOf<String, Any?>("ssid" to name, "hidden" to netManual)
        if (needPw && pw.isNotEmpty()) body["psk"] = pw
        obErr = "Kobler til $name …"
        launch {
            val ok = DeviceLink.send("/api/wifi", body, on = h, timeout = 50.0) != null
            if (ok) { Haptics.success(); goOb(2) } else { Haptics.error(); obErr = "Fikk ikke koblet til $name. Sjekk passordet." }
        }
    }

    /** Starts the QR step. With a camera the scanner calls `qrFound()`; without one it finishes after 2.2 s like the design. */
    fun startScan(simulated: Boolean) {
        scan = true
        scanFound = false
        obErr = ""
        if (!simulated) { camOK = true; return }
        run("scan") {
            delay(1400)
            if (!scan) return@run
            Haptics.success()
            scanFound = true
            delay(800)
            if (!scan) return@run
            scan = false
            goOb(1)
        }
    }

    fun cameraDenied() {
        scan = false
        obErr = "Skjold har ikke tilgang til kameraet. Slå det på i Innstillinger → Apper → Skjold → Tillatelser."
        Haptics.error()
    }

    fun qrFound(payload: String = "") {
        if (!scan) return
        // QR with an address (http://ip:8765, ip or name.local): connect to it
        val p = payload.trim()
        if (p.isNotEmpty() && Regex("""^(https?://)?[A-Za-z0-9.\-\[\]:]+(/.*)?$""").matches(p)) {
            scan = false
            pickFound(p, obType)
            return
        }
        Haptics.success()
        scanFound = true
        run("scan") {
            delay(600)
            if (!scan) return@run
            scan = false
            goOb(1)
        }
    }

    fun testSide(k: String) {
        tested = tested + k
        if (live) { devSend("/api/test", mapOf("channel" to k)); return }
        post(mapOf("type" to "setupTest", "ch" to k))
    }

    fun restartSetup() {
        mode = Mode.ONBOARD; welcome = false; ob = 0; tested = emptySet(); pw = ""; obUpd = 0; scan = false
        post(mapOf("type" to "setup", "step" to 0))
    }

    // MARK: - System / rooms

    val actRoom: Room get() = sys.rooms.firstOrNull { it.id == sys.active } ?: sys.rooms.firstOrNull() ?: Room("stue", room, "s1", "", vol)
    val devRoom: Room get() = sys.rooms.firstOrNull { it.id == setDev } ?: sys.rooms.firstOrNull() ?: Room("stue", "Stue", "s1", "", 0)
    val groupName: String get() = if (sys.rooms.isEmpty()) room else sys.groupLabel(actRoom.id)
    val actModel: String get() = SK.dev(actRoom.type).n

    @JvmName("updateSys")
    fun setSys(n: SystemState) {
        val old = sys
        sys = n
        if (live) liveSys(old, n)
    }

    // MARK: - Player

    val curRadio: Station get() = rTmp ?: radio[station.coerceIn(0, maxOf(0, radio.size - 1))]
    val stIdx: Int get() = station.coerceIn(0, maxOf(0, radio.size - 1))

    val libTrack: Track?
        get() {
            val l = lq ?: return null
            if (svc == null || input != 0 || li >= l.size) return null
            return l[li]
        }

    val np: NowPlaying
        get() {
            val lt = libTrack; val s = svc
            if (lt != null && s != null) return NowPlaying(svcInfo[s]?.first ?: "", lt.t, lt.artist + " · " + lt.album)
            liveNP?.let { return it }
            if (s != null && input == 0) svcInfo[s]?.let { info -> return NowPlaying(info.first, SK.tr[trk].first, SK.tr[trk].second + info.second) }
            return when (input) {
                3 -> { val n = SK.nowPlaying(curRadio.name); NowPlaying("Radio · " + curRadio.name, n.first, n.second) }
                2 -> NowPlaying("AUX", names["nAux1"]?.takeIf { it.isNotEmpty() } ?: "AUX 1", "3,5 mm · analog")
                4 -> NowPlaying("USB-lyd", names["nUsb1"]?.takeIf { it.isNotEmpty() } ?: "PC", "USB-C «PC 1» · 48 kHz · 24 bit")
                else -> NowPlaying(if (input == 1) "Blåtann · telefon" else "AirPlay · telefon", SK.tr[trk].first, SK.tr[trk].second)
            }
        }

    val playerArt: PlayerArt
        get() {
            val n = np
            val big = if (input == 3) curRadio.name else n.t
            val kicker = when (input) { 3 -> "RADIO · " + curRadio.genre.uppercase(); 2 -> "AUX"; 4 -> "USB-LYD"; else -> n.s.uppercase() }
            return PlayerArt(big, kicker, big, if (big.length > 14) 30f else 40f, input == 3)
        }

    val duration: Int
        get() {
            libTrack?.dur?.let { if (it > 0) return it }
            if (live) return if (actLyrionOnly) activeLyrion?.duration ?: 0 else dev?.duration ?: 0
            return libTrack?.dur ?: SK.dur.getOrElse(trk) { 240 }
        }
    val position: Int get() = minOf(pos ?: if (live) 0 else 45, duration)
    val hasProgress: Boolean get() = input != 3 && input != 2 && input != 4 && (!live || duration > 0)

    val srcName: String
        get() {
            val sn = mapOf("upnp" to "UPnP/DLNA", "spotify" to "Spotify", "ytm" to "YouTube Music", "nd" to "Navidrome", "plex" to "Plex")
            val s = svc
            if (s != null && input == 0) sn[s]?.let { return it }
            return listOf("AirPlay", "Blåtann", "AUX", "Radio", "USB-lyd")[input]
        }

    val quality: String
        get() = when {
            input == 3 -> "DIREKTE"
            svc == "nd" -> "FLAC · 44,1 kHz"
            svc == "plex" -> "FLAC · Direkte avspilling"
            input == 1 -> "AAC"
            input == 2 -> "ANALOG"
            input == 4 -> "48 kHz · 24 bit"
            svc == "ytm" -> "AAC · 256 kbps"
            svc == "spotify" -> "OGG · 320 kbps"
            else -> "ALAC · 44,1 kHz"
        }

    /** Inputs available on the active device type. */
    val inputs: List<Pair<String, Int>>
        get() {
            val allowed = SK.dev(actRoom.type).inputs
            return listOf("AirPlay", "Blåtann", "AUX", "Radio", "USB").mapIndexed { i, s -> s to i }.filter { allowed.contains(it.first) }
        }

    fun pickInput(i: Int) {
        input = i; svc = null
        if (live) { liveInput(i); return }
        if (i < 2) post(mapOf("type" to "wl", "v" to if (i == 1) "bt" else "air")) else post(mapOf("type" to "input", "i" to i - 1))
    }

    fun togglePlay() {
        Haptics.thump()
        playing = !playing
        if (live) { hold("play", 3.0); liveTransport(if (playing) "play" else "pause") } else post(mapOf("type" to "pause"))
    }

    fun next() {
        val l = lq
        if (l != null && svc != null) { playLib(l, (li + 1) % l.size, keepOpen = true); return }
        if (live) { pos = 0; hold("pos", 1.0); liveTransport("next"); return }
        trk = (trk + 1) % 3; pos = 0
        post(mapOf("type" to "next"))
    }

    fun prev() {
        val l = lq
        if (l != null && svc != null) { playLib(l, (li + l.size - 1) % l.size, keepOpen = true); return }
        if (live) { pos = 0; hold("pos", 1.0); liveTransport("previous"); return }
        trk = (trk + 2) % 3; pos = 0
    }

    @JvmName("updateVol")
    fun setVol(v: Int) {
        vol = v
        if (live) liveVolume(v) else post(mapOf("type" to "vol", "v" to v))
    }

    fun playLib(list: List<Track>, i: Int, keepOpen: Boolean = false) {
        val tr = list[i]
        val cur = (hist[lib] ?: defaultHist(lib)).filter { it.track.t != tr.t }
        hist = hist + (lib to (listOf(HistEntry(tr, "Nå")) + cur).take(20))
        svc = lib; input = 0; lq = list; li = i; pos = 0; playing = true
        if (!keepOpen) full = true
        if (live) livePlayTrack(tr) else post(mapOf("type" to "play", "svc" to lib, "t" to tr.t))
    }

    fun addQueue(list: List<Track>) {
        val cur = lq
        if (cur.isNullOrEmpty()) { playLib(list, 0); return }
        lq = cur + list
    }

    fun defaultHist(lib: String): List<HistEntry> {
        if (!demo) return emptyList()
        return (SK.lib[lib]?.hist ?: emptyList()).map { HistEntry(SK.lt[it.first], it.second) }
    }

    fun openLib(id: String) {
        sub = "lib"; lib = id; libTab = 0; libPl = null; lq2 = ""; tab = 0
    }

    // MARK: - Radio

    val radioFull: Boolean get() = radio.size >= SK.maxRadio

    fun setRL(l: List<Station>) {
        radio = l
        station = minOf(station, l.size - 1)
        if (live) pushPresets(l)
        LogoStore.fetch(l.map { it.name })
    }

    fun playStation(i: Int, open: Boolean = true) {
        rTmp = null; station = i; input = 3
        if (open) full = true
        if (live) livePlayFavourite(i)
    }

    fun playAny(st: Station) {
        rTmp = st; input = 3; full = true
        if (live) livePlayStream(st)
    }

    fun favIndex(name: String): Int? = radio.indexOfFirst { it.name == name }.takeIf { it >= 0 }

    fun playRadio(st: Station) {
        val f = favIndex(st.name)
        if (f != null) playStation(f) else playAny(st)
    }

    fun toggleFav(st: Station) {
        val f = favIndex(st.name)
        if (f != null) {
            if (radio.size > 1) { Haptics.tick(); setRL(radio.filterIndexed { i, _ -> i != f }) } else Haptics.warning()
        } else if (!radioFull) {
            Haptics.success()
            setRL(radio + st)
        } else Haptics.warning()
    }

    /** Name of the station currently playing ("" if radio is not the input). */
    val curRadioName: String get() = if (input == 3) curRadio.name else ""

    @JvmName("updateQ")
    fun setQ(v: String) {
        q = v; rRes = null
        val t = v.trim()
        if (t.length < 3) { rBusy = false; cancel("rq"); return }
        rBusy = true
        run("rq") {
            delay(400)
            val r = RadioBrowser.search(t)
            if (q.trim() != t) return@run
            rRes = r; rBusy = false
        }
    }

    fun goRadioSettings() {
        tab = 3; sub = ""; openK = ""
        setCat = cats.indexOfFirst { it.id == "radio" }
    }

    fun testCustomStream() {
        val u = uUrl.trim()
        uTest = "busy"
        launch {
            val ok = RadioBrowser.testStream(u)
            if (ok) Haptics.success() else Haptics.error()
            uTest = if (ok) "ok" else "bad"
        }
    }

    // MARK: - Settings

    val cats: List<SettingCategory> get() = SK.catsFor(devRoom.type)

    fun setS(k: String, v: Int) {
        sset = sset + (k to v)
        post(mapOf("type" to "set", "k" to k, "v" to v))
    }

    fun saveName(k: String, v: String) {
        names = names + (k to v)
        post(mapOf("type" to "set", "k" to k, "v" to v))
    }

    fun runAction(id: String, safe: Boolean) {
        if (confirm != id && !safe) { Haptics.warning(); confirm = id; return }
        confirm = ""
        when (id) {
            "ytmTest" -> ytmT = System.currentTimeMillis()
            "ndTest" -> testNavidrome()
            "plexTest" -> testPlex()
            "btPair" -> { btPairT = System.currentTimeMillis(); post(mapOf("type" to "btPair", "room" to devRoom.id)) }
            "openRadio" -> { tab = 0; sub = "radio" }
            "setup" -> restartSetup()
            "roomeq" -> showRoomEQ = true
            "kassett" -> showKassett = true
            "hjulInfo" -> settingsHost?.let { h ->
                runCatching {
                    getApplication<Application>().startActivity(android.content.Intent(android.content.Intent.ACTION_VIEW, android.net.Uri.parse("http://$h/"))
                        .addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK))
                }
            }
            "speakers" -> showSpeakers = true
            else -> post(mapOf("type" to id))
        }
    }

    fun setShowLyrion(on: Boolean) {
        showLyrionPlayers = on
        Store.setBool("skjold-show-lyrion-players", on)
        rebuildRooms()
    }

    fun testPlex() {
        val url = names["plexUrl"] ?: ""; val token = names["plexToken"] ?: ""
        if (url.isBlank()) { plexT = "Skriv inn serveradressen"; plexOK = false; Haptics.warning(); return }
        if (token.isBlank()) { plexT = "Lim inn Plex-token"; plexOK = false; Haptics.warning(); return }
        plexT = "busy"
        launch {
            when (val r = PlexAPI.test(url, token)) {
                is PlexAPI.Result.Ok -> { plexT = if (r.n == 1) "Tilkoblet · 1 musikkbibliotek" else "Tilkoblet · ${r.n} musikkbiblioteker"; plexOK = true; Haptics.success() }
                PlexAPI.Result.Unauthorized -> { plexT = "Feil token"; plexOK = false; Haptics.error() }
                PlexAPI.Result.Unreachable -> { plexT = "Fant ikke serveren"; plexOK = false; Haptics.error() }
                PlexAPI.Result.BadURL -> { plexT = "Ugyldig adresse"; plexOK = false; Haptics.error() }
            }
        }
    }

    // MARK: - EQ

    val actSrc: String get() = if (headphones) "hp" else listOf("air", "bt", "aux", "radio", "usb")[input]
    val eqEditing: String get() = eqSrc ?: actSrc
    val prof: EQProfile get() = eqP[eqEditing] ?: EQProfile(0, listOf(0, 0, 0, 0, 0), true)

    fun setProf(change: (EQProfile) -> EQProfile) {
        eqP = eqP + (eqEditing to change(prof))
        post(mapOf("type" to "eqSync", "src" to eqEditing))
    }

    // MARK: - Update

    fun checkUpdate() = liveCheckUpdate()

    fun backupNow() {
        if (live) { updMsg = "Backup fra appen er ikke støttet av forsterkeren ennå."; Haptics.warning(); return }
        upd = upd.copy(backups = (listOf(Backup("b${System.currentTimeMillis()}", upd.version, SK.now(), "Manuell")) + upd.backups).take(6))
        Haptics.success()
        updMsg = "Backup av ${upd.version} er lagret."
        job = null
    }

    fun installUpdate() {
        val rel = upd.latest ?: return
        updMsg = ""
        if (live) {
            Haptics.warning()
            updMsg = "Installering fra appen er ikke koblet til forsterkeren ennå. Oppdater med Skjold Flasher eller fra forsterkerens meny (${rel.tag})."
            return
        }
        val u = upd; val fail = u.failNext; val ver = rel.tag.removePrefix("v")
        val steps = listOf("Tar backup av " + u.version, "Laster ned " + rel.tag + " fra github.com/" + u.repo, "Verifiserer SHA-256", "Installerer", if (fail) "Starter tjenester …" else "Starter på nytt")
        runJob(steps, 4, if (fail) 4 else null) { failed ->
            val n = if (failed) u.copy(failNext = false, log = (listOf(UpdateLog(SK.now(), "Oppdatering til $ver feilet ved oppstart. Gjenopprettet ${u.version} automatisk.", true)) + u.log).take(8))
            else u.copy(version = ver, latest = null,
                backups = (listOf(Backup("b${System.currentTimeMillis()}", u.version, SK.now(), "Automatisk før oppdatering")) + u.backups).take(6),
                log = (listOf(UpdateLog(SK.now(), "Oppdatert ${u.version} → $ver")) + u.log).take(8))
            if (failed) Haptics.error() else Haptics.success()
            upd = n
            job = Job2(done = true, failed = failed, upd = n)
            post(mapOf("type" to "updSync", "version" to n.version))
        }
    }

    fun restore(b: Backup) {
        if (restoreConf != b.id) { Haptics.warning(); restoreConf = b.id; return }
        if (live) { restoreConf = ""; updMsg = "Gjenoppretting fra appen er ikke støttet av forsterkeren ennå."; return }
        restoreConf = ""; updMsg = ""
        val u = upd
        runJob(listOf("Stopper tjenester", "Gjenoppretter " + b.ver, "Starter på nytt"), 6, null) {
            val n = u.copy(version = b.ver, latest = null, log = (listOf(UpdateLog(SK.now(), "Gjenopprettet backup ${b.ver} (${b.date})")) + u.log).take(8))
            Haptics.success()
            upd = n
            job = null
            updMsg = "Backup ${b.ver} er gjenopprettet."
            post(mapOf("type" to "updSync", "version" to n.version))
        }
    }

    private fun runJob(steps: List<String>, inc: Int, failAt: Int?, done: (Boolean) -> Unit) {
        run("job") {
            var i = 0; var p = 0
            while (isActive) {
                delay(70)
                p += inc
                if (p >= 100) { p = 0; i++ }
                if (failAt != null && i == failAt && p > 40) { done(true); return@run }
                if (i >= steps.size) { done(false); return@run }
                val frac = (i + p / 100.0) / steps.size
                job = Job2(step = steps[i], pct = (frac * 100 + 0.5).toInt())
            }
        }
    }

    // =====================================================================================================
    // MARK: - LiveSync (live connection: Skjold daemons, Lyrion, Navidrome, Plex and GitHub)
    // =====================================================================================================

    /** Demo mode: no Skjold device has ever been found or chosen. */
    val demo: Boolean get() = known.isEmpty() && stedId.isEmpty()
    val live: Boolean get() = !demo

    /** The active room is a plain Lyrion player (no Skjold daemon): control it over JSON-RPC. */
    val actLyrionOnly: Boolean get() = live && actRoom.host == null && actRoom.pid != null && lyrionServer != null
    val activeLyrion: Lyrion.PStatus? get() = if (actLyrionOnly) actRoom.pid?.let { lyStats[it] } else null

    /** Status of the device behind the room selected in Innstillinger. */
    val devRoomStatus: DevStatus? get() = devRoom.host?.let { if (it == activeHost) dev else devStats[it] }
    /** Host settings are sent to: the device chosen in Innstillinger, else the active one. */
    val settingsHost: String? get() = devRoom.host ?: activeHost

    val lyrionURL: String? get() = lyrionServer?.let { Net.url(it, "/") }

    // Hold window (like hold() in skjold/app/src/lib/store.ts): the user's last change wins for a while.
    fun hold(k: String, seconds: Double = 1.5) { holds[k] = System.currentTimeMillis() + (seconds * 1000).toLong() }
    fun held(k: String): Boolean = (holds[k] ?: 0L) > System.currentTimeMillis()

    /** Talks to a device ("ip", "ip:port", "name.local" or a URL), remembers it and makes it the active one. */
    suspend fun connect(raw: String): Boolean {
        val h = DeviceLink.normHost(raw)
        link = Link.CONNECTING
        val st = DeviceLink.status(h)
        if (st == null) { if (dev == null) link = Link.NONE; return false }
        val wasDemo = demo
        remember(h, st)
        if (wasDemo) {
            upd = UpdateState(st.version, GitHubReleases.REPO, upd.channel, upd.auto, false, null, "", emptyList(), emptyList())
            hist = emptyMap()
        }
        activeHost = h
        dev = null
        apply(st, h)
        rebuildRooms()
        sys.rooms.firstOrNull { it.host == h }?.let { r -> sys = sys.copy(active = r.id); setDev = r.id }
        startLive()
        return true
    }

    fun remember(h: String, st: DevStatus) {
        val k = known.filter { it.host != h && (st.id.isEmpty() || it.id != st.id) }.toMutableList()
        k.add(0, KnownDevice(h, if (st.id.isEmpty()) h else st.id, st.name, st.product))
        known = k.take(16)
    }

    /** NSD found and resolved a device: add it to the system (and leave demo mode). */
    fun discovered(d: FoundDevice) {
        val h = d.host ?: return
        if (known.any { it.host == h }) return
        launch {
            val st = DeviceLink.status(h) ?: return@launch
            if (known.any { it.id == st.id && it.host != h }) {
                // same box, new address (DHCP): update it
                remember(h, st)
                if (activeHost == null || dev == null) activeHost = h
                return@launch
            }
            if (demo && mode == Mode.APP) { connect(h); return@launch }
            if (mode == Mode.APP) { remember(h, st); devStats[h] = st; rebuildRooms() }
        }
    }

    private var routeWatch = false

    fun startLive() {
        if (!routeWatch) {
            routeWatch = true
            // Enhet valgt i systemets «Medieutgang» eller i mediebiblioteket: bytt aktivt rom
            launch { SkjoldRoutes.selected.collect { h -> if (h != null && h != activeHost) { val r = sys.rooms.firstOrNull { it.host == h }; if (r != null) activate(r) else { activeHost = h; dev = null; startEvents() } } } }
        }
        browser.onResolved = { d -> discovered(d) }
        browser.start()
        if (!live) return
        if (activeHost == null) activeHost = known.firstOrNull()?.host
        startEvents()
        run("poll") {
            var n = 0
            while (isActive) {
                pollSystem()
                if (n % 2 == 0) settingsHost?.let { loadSettings(it) }
                n++
                delay(4000)
            }
        }
        launch { loadPresets() }
    }

    /** Subscribes to /api/events of the active device; falls back to polling /api/status every 2 s. */
    fun startEvents() {
        run("sse") {
            var fails = 0
            while (isActive) {
                val h = activeHost
                val url = h?.let { Net.url(it, "/api/events") }
                if (h == null || url == null) { delay(2000); continue }
                var got = false
                DeviceEvents.stream(url) { line ->
                    if (activeHost == h) DevStatus.parse(line.toByteArray())?.let { st -> got = true; fails = 0; apply(st, h) }
                }
                if (!isActive) return@run
                val st = DeviceLink.status(h)
                if (st != null) { fails = 0; apply(st, h) } else {
                    fails++
                    if (fails >= 2) { link = Link.OFFLINE; rebuildRooms() }
                }
                delay(if (got) 500 else 2000)
            }
        }
    }

    // MARK: Status → model

    fun apply(st: DevStatus, h: String) {
        devStats[h] = st
        if (h != activeHost) return
        val first = dev == null || link != Link.ONLINE
        dev = st
        link = Link.ONLINE
        val ctx = getApplication<Application>()
        viewModelScope.launch { WidgetStore.publish(ctx, st, h) }   // widgets + «Spiller nå»-varsling (bare når noe synlig endres)
        if (st.lyrionServer.isNotEmpty()) lyrionServer = st.lyrionServer
        headphones = st.headphones
        if (upd.repo == GitHubReleases.REPO && st.version.isNotEmpty() && upd.version != st.version) upd = upd.copy(version = st.version)

        val cover = DeviceLink.coverURL(st.coverURL)
        if (cover.isNotEmpty()) CoverStore.set(st.title, cover)
        st.radioNow?.let {
            if (it.name.isNotEmpty()) { if (it.logo.isNotEmpty()) LogoStore.device(it.name, DeviceLink.coverURL(it.logo)) else LogoStore.adopt(it.name, it.image) }
        }

        val sig = st.presetTitles.joinToString("\u0001")
        if (sig != presetSig) { presetSig = sig; launch { loadPresets() } }
        if (first) launch { loadSettings(h) }

        if (actLyrionOnly) return
        if (!held("vol")) vol = st.volume
        if (!held("pos")) pos = st.position

        // a library track we started on the amplifier (via Lyrion as a stream)?
        val ls = libStream
        if (ls != null) {
            if (st.input == "radio" && st.radioNow?.url == ls) {
                if (st.playing) libSawPlaying = true
                else if (libSawPlaying && !st.paused && !held("input")) { libSawPlaying = false; libEnded() }
                if (!held("play")) playing = st.playing
                return
            }
            if (!held("input")) { libStream = null; lq = null; svc = null }
        }
        if (!held("play")) playing = st.playing
        if (held("input")) return
        when (st.input) {
            "airplay" -> { input = 0; if (svc != "upnp") svc = null }
            "bt" -> { input = 1; svc = null }
            "aux", "aux2" -> { input = 2; svc = null }
            "usb" -> { input = 4; svc = null }
            "spotify" -> { input = 0; svc = "spotify" }
            "plex" -> { input = 0; svc = "plex" }
            "radio" -> {
                input = 3; svc = null
                val rn = st.radioNow
                if (rn != null) {
                    val pi = presetNs.indexOf(rn.n)
                    if (rn.n > 0 && pi >= 0) { station = pi; rTmp = null }
                    else if (rn.name.isNotEmpty() && rn.n == 0) {
                        val fi = radio.indexOfFirst { it.url == rn.url && rn.url.isNotEmpty() }
                        if (fi >= 0) { station = fi; rTmp = null }
                        else if (rTmp?.name != rn.name) rTmp = Station(rn.name, rn.genre.ifEmpty { "Nettradio" }, rn.url, rn.image)
                    }
                }
            }
        }
    }

    /** Now playing from the live system. null = use the design's local text (AUX/USB, demo, library queue). */
    val liveNP: NowPlaying?
        get() {
            if (!live || libTrack != null) return null
            if (actLyrionOnly) {
                val s = activeLyrion
                val t = s?.title ?: ""
                return NowPlaying("Lyrion · " + actRoom.name, t.ifEmpty { "Ingenting spiller" }, listOf(s?.artist ?: "", s?.album ?: "").filter { it.isNotEmpty() }.joinToString(" · "))
            }
            val d = dev ?: return NowPlaying(actRoom.name, if (link == Link.OFFLINE) "Frakoblet" else "Kobler til …", activeHost ?: "")
            if (link == Link.OFFLINE) return NowPlaying(d.name, "Frakoblet", "Får ikke kontakt med ${d.name}")
            if (!d.power) return NowPlaying(d.name, "Standby", srcName)
            return when (input) {
                2, 4 -> null
                3 -> {
                    val name = d.radioNow?.name?.takeIf { it.isNotEmpty() } ?: curRadio.name
                    NowPlaying("Radio · $name", if (d.title.isEmpty() || d.title == name) "Direkte" else d.title, d.artist.ifEmpty { name })
                }
                else -> {
                    val who = if (input == 1) d.btDevice else d.airplayDevice
                    NowPlaying(if (who.isEmpty()) srcName else "$srcName · $who", d.title.ifEmpty { "Ingenting spiller" },
                        listOf(d.artist, d.album).filter { it.isNotEmpty() }.joinToString(" · "))
                }
            }
        }

    // MARK: Commands

    /** Sends to the active device. Result status (if any) is applied straight away. */
    fun devSend(path: String, body: Map<String, Any?> = emptyMap(), method: String = "POST", on: String? = null) {
        val h = on ?: activeHost ?: return
        launch {
            val d = DeviceLink.send(path, body, method, h)
            DevStatus.parse(d)?.let { apply(it, h) }
        }
    }

    fun lyrionCmd(pid: String, cmd: List<String>) {
        val srv = lyrionServer ?: return
        launch { Lyrion.command(srv, pid, cmd) }
    }

    fun liveTransport(action: String) {
        val pid = actRoom.pid
        if (actLyrionOnly && pid != null) {
            when (action) {
                "play" -> lyrionCmd(pid, listOf("pause", "0"))
                "pause" -> lyrionCmd(pid, listOf("pause", "1"))
                "next" -> lyrionCmd(pid, listOf("playlist", "index", "+1"))
                "previous" -> lyrionCmd(pid, listOf("playlist", "index", "-1"))
            }
            return
        }
        devSend("/api/transport", mapOf("action" to action))
    }

    /** Volume with at most one request in flight; the newest value is sent when the previous answer arrives. */
    fun liveVolume(v: Int) {
        hold("vol", 1.2)
        val pid = actRoom.pid
        if (actLyrionOnly && pid != null) { lyrionCmd(pid, listOf("mixer", "volume", "$v")); return }
        volWant = v
        pumpVolume()
    }

    private fun pumpVolume() {
        if (volBusy) return
        val v = volWant ?: return
        val h = activeHost ?: return
        volWant = null
        volBusy = true
        launch {
            DeviceLink.send("/api/volume", mapOf("volume" to v), on = h)
            volBusy = false
            hold("vol", 0.8)
            pumpVolume()
        }
    }

    fun roomVolume(r: Room, v: Int) {
        val h = r.host
        if (h != null) launch { DeviceLink.send("/api/volume", mapOf("volume" to v), on = h) }
        else r.pid?.let { lyrionCmd(it, listOf("mixer", "volume", "$v")) }
    }

    fun liveInput(i: Int) {
        hold("input", 2.5)
        libStream = null
        devSend("/api/input", mapOf("input" to inputNames[i.coerceIn(0, 4)]))
    }

    /** Spotify Connect / UPnP from Kilder. Spotify is a real input on newer daemons; UPnP has no backend yet. */
    fun pickService(s: String) {
        svc = s; input = 0; full = true
        if (!live || s != "spotify" || dev?.inputs?.contains("spotify") != true) return
        hold("input", 2.5)
        devSend("/api/input", mapOf("input" to "spotify"))
    }

    fun livePlayFavourite(i: Int) {
        hold("input", 3.0)
        libStream = null
        val n = presetNs.getOrElse(i) { i + 1 }
        devSend("/api/presets/$n/play")
    }

    fun livePlayStream(st: Station) {
        hold("input", 3.0)
        libStream = null
        launch {
            var url = st.url ?: ""
            if (url.isEmpty()) url = RadioBrowser.streamURL(st.name) ?: ""
            if (url.isEmpty()) { Haptics.error(); return@launch }
            val body = mutableMapOf<String, Any?>("url" to url, "title" to st.name, "genre" to st.genre)
            (st.image ?: LogoStore.url(st.name))?.let { body["image"] = it }
            devSend("/api/radio/play", body)
        }
    }

    /** Library track → the amplifier plays the stream URL through Lyrion (POST /api/radio/play). */
    fun livePlayTrack(tr: Track) {
        if (tr.stream.isEmpty()) { Haptics.warning(); return }
        hold("input", 4.0); hold("play", 4.0); hold("pos", 2.0)
        libStream = tr.stream
        libSawPlaying = false
        if (tr.cover.isNotEmpty()) { CoverStore.set(tr.t, tr.cover); CoverStore.set(tr.album, tr.cover) }
        devSend("/api/radio/play", mapOf("url" to tr.stream, "title" to if (tr.artist.isEmpty()) tr.t else tr.t + " – " + tr.artist, "image" to tr.cover))
    }

    /** The stream of a library track finished: play the next one in the queue. */
    fun libEnded() {
        val l = lq ?: return
        if (svc == null || l.isEmpty()) return
        if (li + 1 < l.size || repeatOn) playLib(l, (li + 1) % l.size, keepOpen = true) else libStream = null
    }

    // MARK: Radio favourites (GET/POST /api/presets)

    suspend fun loadPresets() {
        val h = activeHost ?: return
        val ps = DevPreset.list(DeviceLink.get("/api/presets", on = h)) ?: return
        if (ps.isEmpty()) {
            if (radio.isNotEmpty()) pushPresets(radio)
            return
        }
        presetNs = ps.map { it.n }
        // Logoen fra Skjold (/api/logo) først: den nås alltid fra telefonen, i motsetning til Lyrions http-/relative bildeadresser
        val l = ps.map { p ->
            val img = if (p.logo.isNotEmpty()) DeviceLink.coverURL(p.logo, h) else p.image
            Station(p.title, p.genre.ifEmpty { "Nettradio" }, p.url, img.ifEmpty { null })
        }
        for (p in ps) { if (p.logo.isNotEmpty()) LogoStore.device(p.title, DeviceLink.coverURL(p.logo, h)) else LogoStore.adopt(p.title, p.image) }
        if (l != radio) { radio = l; station = minOf(station, maxOf(0, l.size - 1)) }
        LogoStore.fetch(l.map { it.name })
    }

    /** Replaces the favourites on the amplifier. Catalog stations without a URL are looked up on Radio Browser first. */
    fun pushPresets(l: List<Station>) {
        val h = activeHost ?: return
        launch {
            val out = l.map { s -> if ((s.url ?: "").isEmpty()) s.copy(url = RadioBrowser.streamURL(s.name)) else s }
            val body = out.mapNotNull { s ->
                val u = s.url
                if (u.isNullOrEmpty()) null
                else mapOf("title" to s.name, "url" to u, "genre" to s.genre, "icon" to (s.image ?: LogoStore.url(s.name) ?: ""))
            }
            if (body.size < out.size) Haptics.warning()
            DeviceLink.send("/api/presets", mapOf("presets" to body), on = h)
            loadPresets()
        }
    }

    // MARK: Settings (GET/POST /api/settings)

    suspend fun loadSettings(h: String) {
        val s = DevSettings.parse(DeviceLink.get("/api/settings", on = h)) ?: return
        if (h != settingsHost) return
        val n = sset.toMutableMap()
        for ((k, v) in s.ints) if (!held("set-$k")) n[k] = v
        if (n != sset) sset = n
        s.ints["hold"]?.let { fav = it }
        val nm = names.toMutableMap()
        for (k in stringKeys) { val v = s.strings[k]; if (v != null && !held("set-$k")) nm[k] = v }
        if (nm != names) {
            // Endret i web-UI-et eller en annen app: last bibliotekene på nytt med de nye innloggingene.
            val changed = listOf("ytmUser", "ytmCookie", "ndUrl", "ndUser", "ndPass", "plexUrl", "plexToken").filter { (nm[it] ?: "") != (names[it] ?: "") }.toSet()
            names = nm
            if (changed.any { it.startsWith("nd") }) { ndT = null; libs = libs - "nd" }
            if (changed.any { it.startsWith("plex") }) { plexT = null; libs = libs - "plex" }
            if (changed.any { it.startsWith("ytm") }) ytmT = null
        }
        s.homeLayout?.let { hl -> if (!held("set-homeLayout") && hl != homeLayout) homeLayout = hl }
        val e = eqP.toMutableMap()
        for ((src, p) in s.eq) if (!held("eq-$src")) e[src] = p
        if (e != eqP) eqP = e
    }

    fun liveSetting(k: String, v: Any) {
        if (localKeys.contains(k)) return
        val h = settingsHost ?: return
        hold("set-$k", 3.0)
        var value: Any = v
        if (v is Int && boolKeys.contains(k)) value = v != 0
        val patch = mutableMapOf<String, Any?>(k to value)
        if (k == "name") { patch["nameCustom"] = ""; names = names + ("nameCustom" to "") }
        launch { DeviceLink.send("/api/settings", patch, on = h) }
    }

    /** Lagrer ny rekkefølge for hjemskjermen; seksjoner andre klienter kjenner (men ikke Android) beholdes på slutten. */
    fun saveHomeLayout(items: List<HomeItem>) {
        homeLayout = items + homeLayout.filter { o -> items.none { it.id == o.id } }
        val h = settingsHost ?: return
        hold("set-homeLayout", 3.0)
        val body = mapOf("homeLayout" to HomeLayout.toJson(homeLayout))
        launch { DeviceLink.send("/api/settings", body, on = h) }
    }

    fun resetHomeLayout() {
        homeLayout = emptyList()
        val h = settingsHost ?: return
        hold("set-homeLayout", 3.0)
        launch { DeviceLink.send("/api/settings", mapOf("homeLayout" to emptyList<Any>()), on = h) }
    }

    fun liveEQ(src: String) {
        val h = settingsHost ?: return
        val p = eqP[src] ?: return
        hold("eq-$src", 3.0)
        launch { DeviceLink.send("/api/settings", mapOf("eq" to mapOf(src to mapOf("preset" to p.preset, "eq" to p.eq, "loud" to p.loud))), on = h) }
    }

    /** 440 Hz tone left, then right (POST /api/test). */
    fun speakerTest(on: String?) {
        val h = on ?: activeHost ?: return
        launch {
            DeviceLink.send("/api/test", mapOf("channel" to "L"), on = h, timeout = 12.0)
            delay(300)
            DeviceLink.send("/api/test", mapOf("channel" to "R"), on = h, timeout = 12.0)
        }
    }

    /** Info rows in Innstillinger (Parede enheter, Lyrion, IP …). */
    fun infoText(key: String?): String {
        val st = devRoomStatus
        val offline = live && st == null && devRoom.host != null
        return when (key) {
            "btDev" -> when {
                demo -> "Sebastians iPhone, MacBook Pro"
                offline -> "Frakoblet"
                else -> st?.let { it.btDevice.ifEmpty { "Ingen tilkoblet" } } ?: "–"
            }
            "lyrion" -> when {
                demo -> "Demo"
                offline -> "Frakoblet"
                st != null && st.lyrion -> "Tilkoblet · " + st.lyrionServer.ifEmpty { "ukjent adresse" }
                devRoom.host == null && lyrionServer != null -> "Tilkoblet · " + (lyrionServer ?: "")
                else -> "Ikke funnet"
            }
            "version" -> if (demo) upd.version else if (offline) "Frakoblet" else st?.version ?: "–"
            "ip" -> if (demo) "192.168.1.42" else devRoom.host?.substringBefore(":") ?: "–"
            "serial" -> if (demo) "SKJ-S1-0001" else st?.id ?: "–"
            "netName" -> if (demo) "Skjold · romnavn" else st?.name ?: devRoom.name
            "ytmPo" -> "Ikke tilgjengelig"
            else -> ""
        }
    }

    // MARK: Rooms (Skjold devices + Lyrion players)

    suspend fun pollSystem() {
        for (k in devices) {
            if (k.host == activeHost) continue
            if (stedId.isNotEmpty() && stedEnheter.firstOrNull { it.id == k.id }?.online == false) { devStats[k.host] = null; continue }
            devStats[k.host] = DeviceLink.status(k.host, if (Hjem.isRelay(k.host)) 5.0 else 2.5)
        }
        val srv = lyrionServer
        if (srv != null) {
            val ps = Lyrion.players(srv)
            if (ps != null) {
                lyPlayers = ps
                val st = HashMap<String, Lyrion.PStatus>()
                for (p in ps) if (p.connected) Lyrion.status(srv, p.id)?.let { st[p.id] = it }
                lyStats = st
                val pid = actRoom.pid
                val s = pid?.let { st[it] }
                if (actLyrionOnly && s != null) {
                    if (!held("vol")) vol = s.volume
                    if (!held("play")) playing = s.playing
                    if (!held("pos")) pos = s.time
                    if (s.cover.isNotEmpty()) CoverStore.set(s.title, s.cover)
                }
            }
        }
        rebuildRooms()
    }

    fun rebuildRooms() {
        if (!live) return
        val prev = sys
        val rooms = ArrayList<Room>()
        val used = HashSet<String>()
        for (k in devices) {
            val st = if (k.host == activeHost) (if (link == Link.OFFLINE) null else dev) else devStats[k.host]
            val id = st?.id?.takeIf { it.isNotEmpty() } ?: k.id
            val p = st?.product ?: k.product
            val type = if (p in listOf("s1", "node", "core", "touch")) p else "s1"
            var r = Room(id, st?.name ?: k.name, type, hw(type, st), st?.volume ?: 0, host = k.host)
            var pid = (st?.lyrionPlayer ?: "").lowercase()
            if (pid.isEmpty() || pid == "00:00:00:00:00:01") pid = lyPlayers.firstOrNull { it.name.equals(r.name, ignoreCase = true) }?.id?.lowercase() ?: ""
            if (pid.isNotEmpty() && (lyPlayers.isEmpty() || lyPlayers.any { it.id.lowercase() == pid })) { r = r.copy(pid = pid); used.add(pid) }
            if (st == null) r = r.copy(np = listOf("Frakoblet", if (Hjem.isRelay(k.host)) "Skjold-hjem" else k.host))
            else if (k.host != activeHost && st.playing && st.title.isNotEmpty()) r = r.copy(np = listOf(st.title, st.artist.ifEmpty { st.name }))
            if (rooms.none { it.id == r.id }) rooms.add(r)
        }
        // Andre Lyrion-spillere (max2play, TV-bokser …) er ikke Skjold-enheter – bare med når brukeren ber om det.
        if (showLyrionPlayers) for (p in lyPlayers) {
            if (used.contains(p.id.lowercase())) continue
            var r = Room(p.id, p.name, "node", p.model.ifEmpty { "Lyrion-spiller" } + " · Lyrion", lyStats[p.id]?.volume ?: 0, pid = p.id)
            val s = lyStats[p.id]
            if (!p.connected) r = r.copy(np = listOf("Frakoblet", "Lyrion"))
            else if (s != null && s.playing && s.title.isNotEmpty()) r = r.copy(np = listOf(s.title, s.artist.ifEmpty { "Lyrion" }))
            rooms.add(r)
        }
        val lyGroups = lyStats.isNotEmpty() && !held("groups")
        for (i in rooms.indices) {
            val old = prev.rooms.firstOrNull { it.id == rooms[i].id }
            var r = rooms[i].copy(role = old?.role)
            if (held("rvol-" + r.id) && old != null) r = r.copy(vol = old.vol)
            val pid = r.pid
            val s = if (lyGroups && pid != null) lyStats[pid] ?: lyStats.entries.firstOrNull { it.key.lowercase() == pid }?.value else null
            r = if (s != null && pid != null) {
                val master = s.syncMaster.ifEmpty { if (s.syncSlaves.isEmpty()) "" else pid }
                val g = if (master.isEmpty()) null else "ly-" + master.lowercase()
                r.copy(group = g, np = if (g != null) null else r.np)
            } else r.copy(group = old?.group)
            rooms[i] = r
        }
        var n = SystemState(prev.active, rooms, prev.modes)
        if (rooms.none { it.id == n.active }) n = n.copy(active = rooms.firstOrNull { it.host == activeHost }?.id ?: rooms.firstOrNull()?.id ?: "")
        if (n.rooms != prev.rooms || n.active != prev.active) sys = n
    }

    /** Room tile tapped / active room changed. */
    fun activate(r: Room) {
        val h = r.host
        if (h != null && h != activeHost) {
            activeHost = h
            dev = null
            link = Link.CONNECTING
            libStream = null
            devStats[h]?.let { apply(it, h) }
            startEvents()
            launch { loadPresets() }
        }
        setDev = r.id
    }

    /** setSys() from RoomsView in live mode: volumes per room and Lyrion sync for group changes. */
    fun liveSys(old: SystemState, n: SystemState) {
        if (n.active != old.active) n.rooms.firstOrNull { it.id == n.active }?.let { activate(it) }
        var groupsChanged = false
        for (r in n.rooms) {
            val o = old.rooms.firstOrNull { it.id == r.id } ?: continue
            if (o.vol != r.vol && r.id != n.active) { hold("rvol-" + r.id, 2.5); roomVolume(r, r.vol) }
            if (o.group != r.group) groupsChanged = true
        }
        val srv = lyrionServer
        if (!groupsChanged || srv == null) return
        hold("groups", 5.0)
        val cmds = ArrayList<Pair<String, List<String>>>()
        for (r in n.rooms) {
            val pid = r.pid ?: continue
            val o = old.rooms.firstOrNull { it.id == r.id } ?: continue
            if (o.group == r.group) continue
            val g = r.group
            if (g == null) { cmds.add(pid to listOf("sync", "-")); continue }
            val members = n.rooms.filter { it.group == g && it.pid != null }
            val leader = members.firstOrNull { it.id == n.active } ?: members.firstOrNull()
            val lp = leader?.pid
            if (lp != null && lp != pid) cmds.add(lp to listOf("sync", pid))
        }
        launch { for ((p, c) in cmds) Lyrion.command(srv, p, c) }
    }

    // MARK: Libraries (Navidrome, Plex; YouTube Music has no backend)

    val ndConf: Subsonic.Conf get() = Subsonic.Conf(names["ndUrl"] ?: "", names["ndUser"] ?: "", names["ndPass"] ?: "")
    val plexConf: PlexLib.Conf get() = PlexLib.Conf(names["plexUrl"] ?: "", names["plexToken"] ?: "")

    private fun setLib(id: String, d: LibData?) { libs = if (d == null) libs - id else libs + (id to d) }

    suspend fun loadLib(id: String, force: Boolean = false) {
        if (!live) return
        val cur = libs[id]?.state
        if (!force && (cur == "ok" || cur == "busy")) return
        setLib(id, LibData(state = "busy"))
        var d = LibData(state = "busy")
        when (id) {
            "nd" -> {
                val c = ndConf
                d = if (!c.ok) d.copy(state = "Navidrome er ikke satt opp. Legg inn server, brukernavn og passord under Innstillinger → Musikktjenester.")
                else {
                    val ra = Subsonic.albums(c, "newest"); val rr = Subsonic.albums(c, "random")
                    val rf = Subsonic.albums(c, "frequent"); val rp = Subsonic.playlists(c)
                    LibData(
                        state = when (ra) { is Res.Ok -> "ok"; is Res.Err -> "Navidrome: " + ra.text },
                        newest = ra.getOrNull() ?: emptyList(), other = rr.getOrNull() ?: emptyList(),
                        frequent = rf.getOrNull() ?: emptyList(), playlists = rp.getOrNull() ?: emptyList(),
                    )
                }
            }
            "plex" -> {
                val c = plexConf
                d = if (!c.ok) d.copy(state = "Plex er ikke satt opp. Legg inn server og token under Innstillinger → Musikktjenester.")
                else {
                    val sec = PlexLib.musicSection(c)
                    if (sec == null) d.copy(state = "Fant ikke Plex-serveren eller et musikkbibliotek.")
                    else {
                        val ra = PlexLib.albums(c, sec, "addedAt:desc"); val rr = PlexLib.albums(c, sec, "random")
                        val rf = PlexLib.albums(c, sec, "viewCount:desc"); val rp = PlexLib.playlists(c)
                        LibData(if (ra == null) "Plex svarte ikke." else "ok", ra ?: emptyList(), rr ?: emptyList(), rf ?: emptyList(), rp ?: emptyList())
                    }
                }
            }
            else -> d = d.copy(state = "YouTube Music er ikke koblet til. Forsterkeren har ingen YouTube Music-tjeneste ennå.")
        }
        for (c in d.albums + d.playlists) CoverStore.set(c.name, c.cover)
        setLib(id, d)
    }

    suspend fun collTracks(lib: String, c: LibColl): List<Track> {
        libs[lib]?.tracks?.get(c.id)?.let { if (it.isNotEmpty()) return it }
        val items = if (lib == "plex") PlexLib.tracks(plexConf, c) else Subsonic.tracks(ndConf, c)
        val t = items.map { track(it) }
        for (x in t) if (x.cover.isNotEmpty()) CoverStore.set(x.album, x.cover)
        val d = libs[lib] ?: LibData()
        setLib(lib, d.copy(tracks = d.tracks + (c.id to t)))
        return t
    }

    suspend fun searchLib(lib: String, q: String): List<Track> {
        val items = when (lib) {
            "nd" -> if (!ndConf.ok) return emptyList() else Subsonic.search(ndConf, q)
            "plex" -> {
                if (!plexConf.ok) return emptyList()
                val sec = PlexLib.musicSection(plexConf) ?: return emptyList()
                PlexLib.search(plexConf, sec, q)
            }
            else -> emptyList()
        }
        val t = items.map { track(it) }
        for (x in t) if (x.cover.isNotEmpty()) CoverStore.set(x.album, x.cover)
        return t
    }

    fun testNavidrome() {
        ndT = "busy"
        launch {
            val err = Subsonic.ping(ndConf)
            ndOK = err == null
            ndT = err ?: "Tilkoblet"
            if (err == null) { Haptics.success(); setLib("nd", null) } else Haptics.error()
        }
    }

    // MARK: Updates (GitHub Releases, skjold-v*)

    fun liveCheckUpdate() {
        checking = true; job = null; updMsg = ""
        if (upd.repo != GitHubReleases.REPO) upd = upd.copy(repo = GitHubReleases.REPO)
        run("check") {
            val r = GitHubReleases.latest(upd.channel == 1)
            checking = false
            upd = upd.copy(checkedAt = SK.now())
            when (r) {
                is Res.Err -> { Haptics.error(); updMsg = r.text + "." }
                is Res.Ok -> {
                    Haptics.tick()
                    val rel = r.v
                    if (rel != null && GitHubReleases.cmp(rel.tag, upd.version) > 0) {
                        upd = upd.copy(latest = Release(rel.tag, rel.name, rel.date, rel.notes, rel.size, rel.pre))
                    } else {
                        upd = upd.copy(latest = null)
                        val newest = rel?.let { " Nyeste utgivelse er ${GitHubReleases.version(it.tag)}." } ?: ""
                        updMsg = "Du har siste versjon (${upd.version}). Sjekket ${SK.now()}.$newest"
                    }
                }
            }
        }
    }
}
