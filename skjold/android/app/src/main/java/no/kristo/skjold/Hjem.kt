package no.kristo.skjold

import android.annotation.SuppressLint
import android.webkit.CookieManager
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBars
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.compose.ui.window.Popup
import androidx.compose.ui.window.PopupProperties
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.Interceptor
import org.json.JSONArray
import org.json.JSONObject
import java.net.URLEncoder

// Skjold-hjem (docs/SKJOLD_HJEM.md): steder i skyen (Cloudflare Worker bak Cloudflare Access), stedsvelger,
// relé via skyen når en enhet ikke svarer på LAN, og innlogging.
//
// Innlogging: skyen åpnes i en WebView (HjemLoginView). Når Access har satt CF_Authorization for sky-domenet,
// leses den med CookieManager og legges på alle OkHttp-kall til sky-verten (Hjem.cookieInterceptor) – også SSE.
// Begrensning: Google-innlogging tillates ikke i WebView; bruk engangskode (e-post) eller en annen IdP i Access.
// En Custom Tab deler ikke informasjonskapsler med appen og ville krevd et callback-endepunkt i Workeren.

data class HjemSted(val id: String, val navn: String, val rolle: String, val enheter: Int, val online: Int)

data class HjemEnhet(
    val id: String, val navn: String, val produkt: String, val rom: String, val online: Boolean,
    val aktivHoved: Boolean, val hoved: Boolean, val reserveNr: Int?, val lan: String?,
) {
    val merke: String get() = if (hoved) "Hoved" else reserveNr?.let { "Reserve $it" } ?: ""
}

sealed class HjemSvar {
    class Ok(val data: ByteArray) : HjemSvar()
    object Login : HjemSvar()
    class Feil(val msg: String) : HjemSvar()
}

object Hjem {
    const val STANDARD = "https://hjem.skjold-lab.com"
    const val COOKIE = "CF_Authorization"
    private const val URL_KEY = "skjold-sky-url"
    private const val TOKEN_KEY = "skjold-sky-token"

    val base: String get() = Store.string(URL_KEY)?.takeIf { it.isNotEmpty() } ?: STANDARD
    fun saveBase(raw: String) {
        var s = raw.trim().trimEnd('/')
        if (s.isNotEmpty() && !s.lowercase().startsWith("http")) s = "https://$s"
        Store.setString(URL_KEY, if (s == STANDARD || s.isEmpty()) null else s)
    }
    val host: String get() = base.toHttpUrlOrNull()?.host ?: ""
    val token: String? get() = Store.string(TOKEN_KEY)?.takeIf { it.isNotEmpty() }
    val loggedIn: Boolean get() = token != null
    fun saveToken(t: String?) = Store.setString(TOKEN_KEY, t)

    fun enc(s: String): String = URLEncoder.encode(s, "UTF-8").replace("+", "%20")
    /** Relé-base: base + "/api/status" osv. går til enhetens eget API via skyen. */
    fun relay(sted: String, id: String) = "$base/api/hjem/steder/${enc(sted)}/enheter/${enc(id)}"
    fun isRelay(h: String) = h.contains("/api/hjem/steder/")
    fun accessBlocked(host: String, path: String) = host.endsWith("cloudflareaccess.com") || path.startsWith("/cdn-cgi/access")

    /** Legger CF_Authorization på kall til sky-verten (OkHttp har ingen felles informasjonskapsel-lager her). */
    val cookieInterceptor = Interceptor { chain ->
        val r = chain.request()
        val t = token
        if (t != null && r.url.host == host) chain.proceed(r.newBuilder().header("Cookie", "$COOKIE=$t").build()) else chain.proceed(r)
    }

    /** CF_Authorization for sky-verten fra WebView-ens CookieManager, eller null. */
    fun cookieFromWebView(): String? {
        val all = CookieManager.getInstance().getCookie(base) ?: return null
        return all.split(";").map { it.trim() }.firstOrNull { it.startsWith("$COOKIE=") }?.substringAfter("=")?.takeIf { it.isNotEmpty() }
    }

    fun logout() {
        saveToken(null)
        CookieManager.getInstance().setCookie(base, "$COOKIE=; Max-Age=0")
    }

    suspend fun call(method: String, path: String, body: Map<String, Any?>? = null): HjemSvar {
        val url = base + path
        if (url.toHttpUrlOrNull() == null) return HjemSvar.Feil("Ugyldig sky-adresse")
        val data = body?.let { (toJson(it) as JSONObject).toString().toByteArray() }
        val r = Net.data(url, method, data, 10.0, mapOf("Accept" to "application/json")) ?: return HjemSvar.Feil("Får ikke kontakt med Skjold-hjem")
        val (d, code) = r
        if (code == 401) return HjemSvar.Login
        val txt = String(d).trim()
        val json = txt.startsWith("{") || txt.startsWith("[")
        if (code !in 200..299) {
            if (code == 403 && !json) return HjemSvar.Login
            val o = jsonObject(d)
            return HjemSvar.Feil(if (code == 403) "Bare eieren kan gjøre det" else o?.str("error")?.ifEmpty { null } ?: o?.str("feil")?.ifEmpty { null } ?: "HTTP $code")
        }
        return if (json || txt.isEmpty()) HjemSvar.Ok(d) else HjemSvar.Login   // HTML = Access-innloggingssiden
    }

    fun list(d: ByteArray): List<JSONObject> = try { jsonList(JSONArray(String(d))) } catch (_: Exception) { emptyList() }

    fun sted(o: JSONObject): HjemSted? {
        val id = o.str("id").ifEmpty { return null }
        val en = o.opt("enheter")
        val n = if (en is JSONArray) en.length() else o.num("enheter")
        val on = when (val v = o.opt("online")) { is Boolean -> if (v) 1 else 0; else -> o.num("online") }
        return HjemSted(id, o.str("navn").ifEmpty { id }, o.str("rolle").ifEmpty { "medlem" }, n, on)
    }

    fun enhet(o: JSONObject): HjemEnhet? {
        val id = o.str("id").ifEmpty { return null }
        val lan = when (val l = o.opt("lan")) {
            is String -> l.ifEmpty { null }
            is JSONObject -> l.str("ip").ifEmpty { null }?.let { ip -> "$ip:${l.num("port").takeIf { it > 0 } ?: DeviceLink.PORT}" }
            else -> null
        }
        return HjemEnhet(
            id, o.str("navn").ifEmpty { id }, o.str("produkt").ifEmpty { "s1" }, o.str("rom"), o.bool("online"),
            o.bool("aktivHoved"), o.bool("hoved"), o.num("reserveNr").takeIf { it > 0 }, lan,
        )
    }
}

// MARK: - Modell

/** Enhetene som vises som rom: valgt steds enheter, ellers de kjente på LAN. */
val AppModel.devices: List<KnownDevice>
    get() = if (stedId.isEmpty()) known else stedEnheter.map { e -> KnownDevice(stedHosts[e.id] ?: Hjem.relay(stedId, e.id), e.id, e.navn, e.produkt) }
val AppModel.stedNavn: String get() = steder.firstOrNull { it.id == stedId }?.navn ?: if (stedId.isEmpty()) "Hjemme" else "Sted"
val AppModel.visSted: Boolean get() = stedId.isNotEmpty() || steder.isNotEmpty()
fun AppModel.hjemEnhet(id: String): HjemEnhet? = if (stedId.isEmpty()) null else stedEnheter.firstOrNull { it.id == id }

fun AppModel.openStederSettings() {
    tab = 3
    val i = cats.indexOfFirst { it.id == "steder" }
    if (i >= 0) { setCat = i; openK = "" }
}

private fun AppModel.hjemFail(s: HjemSvar) {
    when (s) {
        is HjemSvar.Login -> hjemState = "login"
        is HjemSvar.Feil -> hjemState = s.msg
        is HjemSvar.Ok -> {}
    }
}

suspend fun AppModel.startHjem() {
    loadSteder()
    if (stedId.isEmpty()) return
    loadStedEnheter(probe = true)
    // Adressene er nettopp sjekket: bytt hvis den lagrede (relé/gammel LAN) ikke lenger er den beste
    if (activeHost == null || devices.none { it.host == activeHost }) pickDefault()?.let { velgEnhet(it) }
    run("hjem") {
        while (isActive) {
            delay(15_000)
            if (stedId.isNotEmpty() && hjemState == "ok") loadStedEnheter(probe = false)
        }
    }
}

suspend fun AppModel.loadSteder() {
    if (hjemState != "ok") hjemState = "laster"
    val s = Hjem.call("GET", "/api/hjem/steder")
    if (s !is HjemSvar.Ok) { hjemFail(s); return }
    steder = Hjem.list(s.data).mapNotNull { Hjem.sted(it) }
    hjemState = "ok"
}

/** Hent enhetene i valgt sted. `probe`: finn LAN-adresser som svarer innen 1,5 s (ellers relé). */
suspend fun AppModel.loadStedEnheter(probe: Boolean) {
    val id = stedId
    if (id.isEmpty()) { stedEnheter = emptyList(); return }
    val s = Hjem.call("GET", "/api/hjem/steder/${Hjem.enc(id)}/enheter")
    if (s !is HjemSvar.Ok) { hjemFail(s); return }
    val list = Hjem.list(s.data).mapNotNull { Hjem.enhet(it) }
    if (stedId != id) return
    if (probe) {
        val found = coroutineScope {
            list.filter { it.lan != null }.map { e ->
                async {
                    val h = DeviceLink.normHost(e.lan!!)
                    val st = DeviceLink.status(h, 1.5)
                    if (st != null && (st.id.isEmpty() || st.id == e.id)) e.id to h else null
                }
            }.awaitAll().filterNotNull().toMap()
        }
        if (stedId == id) stedHosts = found
    }
    stedEnheter = list
    rebuildRooms()
}

private fun AppModel.pickDefault(): HjemEnhet? {
    val last = Store.string("skjold-sted-enhet:$stedId")
    return stedEnheter.firstOrNull { it.id == last } ?: stedEnheter.firstOrNull { it.aktivHoved }
        ?: stedEnheter.firstOrNull { it.online } ?: stedEnheter.firstOrNull()
}

/** Bytt sted ("" = Dette nettverket). Valget huskes. */
suspend fun AppModel.selectSted(id: String) {
    if (id == stedId) return
    val cur = activeHost
    if (stedId.isEmpty() && cur != null && !Hjem.isRelay(cur)) Store.setString("skjold-lan-host", cur)
    stedId = id
    stedEnheter = emptyList(); stedHosts = emptyMap()
    if (id.isEmpty()) { switchHost(Store.string("skjold-lan-host") ?: known.firstOrNull()?.host); return }
    loadStedEnheter(probe = true)
    val e = pickDefault()
    if (e != null) velgEnhet(e) else switchHost(null)
}

/** Styr en enhet i valgt sted: LAN hvis den svarte, ellers relé. */
suspend fun AppModel.velgEnhet(e: HjemEnhet) {
    Store.setString("skjold-sted-enhet:$stedId", e.id)
    val lan = e.lan
    if (stedHosts[e.id] == null && lan != null) {
        val h = DeviceLink.normHost(lan)
        if (DeviceLink.status(h, 1.5) != null) stedHosts = stedHosts + (e.id to h)
    }
    switchHost(stedHosts[e.id] ?: Hjem.relay(stedId, e.id))
    sys.rooms.firstOrNull { it.host == activeHost }?.let { r -> sys = sys.copy(active = r.id); setDev = r.id }
}

fun AppModel.hjemLoggedIn(token: String) {
    Hjem.saveToken(token)
    hjemLogin = false
    viewModelScope.launch { startHjem() }
}

// MARK: - Visninger

@Composable
fun HjemBadges(e: HjemEnhet, modifier: Modifier = Modifier) {
    Row(modifier, verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
        Dot(if (e.online) C.ok else C.danger)
        if (e.merke.isNotEmpty()) BadgePill(e.merke, e.hoved)
        if (e.aktivHoved) BadgePill("aktiv", true)
        if (!e.online) T("offline", sora(10.5f, W.Regular, C.muted))
    }
}

@Composable
private fun BadgePill(t: String, on: Boolean) {
    Box(
        Modifier.height(18.dp).clip(CircleShape).background(if (on) C.selBg else Color.Transparent)
            .skCapsuleBorder(if (on) C.selLine else C.line2).padding(horizontal = 6.dp),
        contentAlignment = Alignment.Center,
    ) { T(t, mono(9.5f, if (on) C.accent2 else C.ink2, 0.04f)) }
}

/** Tittelrad «Hytta ▾» som åpner stedsmenyen. */
@Composable
fun StedPicker(m: AppModel, size: Float = 28f) {
    var open by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    LaunchedEffect(Unit) { if (m.steder.isEmpty()) m.loadSteder() }
    Box {
        Row(
            Modifier.press { Haptics.tap(); open = !open; if (open) scope.launch { m.loadSteder() } },
            verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            T(m.stedNavn, sora(size, W.Semibold), maxLines = 1)
            SKIcon("M6 9l6 6 6-6", (size * 0.55f).dp, 2.2f, C.ink2)
        }
        if (open) Popup(offset = IntOffset(0, (size * 3.2f).toInt()), onDismissRequest = { open = false }, properties = PopupProperties(focusable = true)) {
            Column(Modifier.width(290.dp).clip(RoundedCornerShape(14.dp)).background(C.card).skBorder(C.line2, 14.dp)) {
                SKMonoLabel("VELG STED", modifier = Modifier.padding(start = 14.dp, top = 12.dp, bottom = 8.dp))
                MenuRow("Dette nettverket", "Skjold-enheter på LAN", m.stedId.isEmpty()) { open = false; scope.launch { m.selectSted("") } }
                for (s in m.steder) {
                    MenuRow(s.navn, "${s.online}/${s.enheter} online", s.id == m.stedId) { open = false; scope.launch { m.selectSted(s.id) } }
                }
                if (m.hjemState == "laster" && m.steder.isEmpty()) MenuRow("Henter steder …", "", false) {}
                if (m.hjemState == "login") MenuRow("Logg inn på Skjold-hjem", "", false, C.accent) { open = false; m.hjemLogin = true }
                MenuRow("Administrer steder …", "", false, C.accent) { open = false; m.openStederSettings() }
            }
        }
    }
}

@Composable
private fun MenuRow(title: String, sub: String, on: Boolean, color: Color = C.ink, action: () -> Unit) {
    Row(
        Modifier.fillMaxWidth().background(if (on) C.selBg else Color.Transparent).topLine(C.line).press(onClick = action)
            .padding(horizontal = 14.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            T(title, sora(14f, W.Regular, if (on) C.accent2 else color), maxLines = 1)
            if (sub.isNotEmpty()) T(sub, mono(10.5f))
        }
        if (on) SKIcon(Icons.check, 14.dp, 2.4f, C.accent)
    }
}

/** Innstillinger → Steder. */
@Composable
fun StederSettingsView(m: AppModel) {
    var url by remember { mutableStateOf(Hjem.base) }
    var nytt by remember { mutableStateOf("") }
    var open by remember { mutableStateOf(m.stedId) }
    val scope = rememberCoroutineScope()
    LaunchedEffect(Unit) { m.loadSteder() }
    Column(Modifier.fillMaxWidth().skBox(C.card, C.line).padding(14.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        T("Steder samler Skjold-enheter på flere adresser (Hjem, Hytta …). Når en enhet ikke svarer på nettet du er på, går trafikken via skyen.", sora(12f, W.Regular, C.ink2))
        SKMonoLabel("SKY-ADRESSE")
        SKField(Hjem.STANDARD, url, { url = it }, height = 44.dp, size = 14f, plainInput = true, keyboard = androidx.compose.ui.text.input.KeyboardType.Uri)
        Flow(8.dp) {
            SKPill("Lagre og hent", height = 34.dp) { Hjem.saveBase(url); scope.launch { m.loadSteder() } }
            if (m.hjemState == "login" || !Hjem.loggedIn) SKPill("Logg inn på Skjold-hjem", primary = true, height = 34.dp) { m.hjemLogin = true }
            else SKPill("Logg ut", height = 34.dp) { Hjem.logout(); m.hjemState = "login"; m.steder = emptyList() }
        }
        when (m.hjemState) {
            "laster" -> T("Henter steder …", sora(12f, W.Regular, C.muted))
            "", "ok", "login" -> {}
            else -> T(m.hjemState, sora(12f, W.Regular, C.danger))
        }
    }
    for (s in m.steder) {
        androidx.compose.runtime.key(s.id) { StedCard(m, s, open == s.id) { open = if (open == s.id) "" else s.id } }
    }
    if (m.hjemState == "ok") {
        Column(Modifier.fillMaxWidth().skBox(C.card, C.line).padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            T("Nytt sted", sora(14f, W.Semibold))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                SKField("For eksempel Hytta", nytt, { nytt = it }, Modifier.weight(1f), height = 44.dp, size = 14f)
                SKPill("Lag", primary = true, height = 44.dp) {
                    val n = nytt.trim()
                    if (n.isNotEmpty()) scope.launch {
                        val r = Hjem.call("POST", "/api/hjem/steder", mapOf("navn" to n))
                        if (r is HjemSvar.Ok) { nytt = ""; open = jsonObject(r.data)?.str("id") ?: ""; Haptics.success() } else Haptics.error()
                        m.loadSteder()
                    }
                }
            }
        }
    }
}

@Composable
private fun StedCard(m: AppModel, s: HjemSted, open: Boolean, toggle: () -> Unit) {
    var navn by remember(s.navn) { mutableStateOf(s.navn) }
    var list by remember { mutableStateOf(listOf<HjemEnhet>()) }
    var kode by remember { mutableStateOf<String?>(null) }
    var msg by remember { mutableStateOf("") }
    var confirm by remember { mutableStateOf("") }
    val scope = rememberCoroutineScope()

    suspend fun load() {
        when (val r = Hjem.call("GET", "/api/hjem/steder/${Hjem.enc(s.id)}/enheter")) {
            is HjemSvar.Ok -> { list = Hjem.list(r.data).mapNotNull { Hjem.enhet(it) }; msg = "" }
            is HjemSvar.Feil -> msg = r.msg
            is HjemSvar.Login -> m.hjemLogin = true
        }
    }
    fun send(method: String, sub: String, body: Map<String, Any?>?) {
        Haptics.tap()
        scope.launch {
            when (val r = Hjem.call(method, "/api/hjem/steder/${Hjem.enc(s.id)}$sub", body)) {
                is HjemSvar.Ok -> msg = ""
                is HjemSvar.Login -> m.hjemLogin = true
                is HjemSvar.Feil -> { msg = r.msg; Haptics.error() }
            }
            load()
            m.loadSteder()
            if (s.id == m.stedId) m.loadStedEnheter(probe = false)
        }
    }
    LaunchedEffect(open) { if (open) load() }
    val reserve = list.filter { it.reserveNr != null }.sortedBy { it.reserveNr ?: 0 }.map { it.id }

    Column(Modifier.fillMaxWidth().skBox(C.card, C.line).padding(14.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Row(Modifier.fillMaxWidth().press(onClick = toggle), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                T(s.navn + if (s.id == m.stedId) " · valgt" else "", sora(15f, W.Semibold))
                T("${s.enheter} enheter · ${s.rolle}", mono(10.5f))
            }
            SKIcon(if (open) "M6 15l6-6 6 6" else "M6 9l6 6 6-6", 14.dp, 2.2f, C.muted)
        }
        if (!open) return@Column
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
            SKField("Navn", navn, { navn = it }, Modifier.weight(1f), height = 40.dp, size = 14f)
            SKPill("Gi nytt navn", height = 40.dp) { send("PATCH", "", mapOf("navn" to navn.trim())) }
        }
        SKMonoLabel("ENHETER")
        if (list.isEmpty()) T("Ingen enheter ennå. Trykk «Legg til enhet».", sora(12f, W.Regular, C.muted))
        Column(Modifier.fillMaxWidth().skBox(C.bg, C.line, 12.dp)) {
            list.forEachIndexed { i, e ->
                Column(
                    Modifier.fillMaxWidth().topLine(if (i > 0) C.line else Color.Transparent).padding(horizontal = 12.dp, vertical = 10.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    T(e.navn + if (e.rom.isEmpty()) "" else " · ${e.rom}", sora(14f))
                    HjemBadges(e)
                    Flow(6.dp) {
                        if (!e.hoved) {
                            SKPill("Gjør til hoved", height = 30.dp, hPad = 10.dp, border = C.selLine, fg = C.accent2) {
                                send("PATCH", "", mapOf("hoved" to e.id, "reserve" to reserve.filter { it != e.id }))
                            }
                            if (e.id !in reserve) SKPill("Legg i reserve", height = 30.dp, hPad = 10.dp) { send("PATCH", "", mapOf("reserve" to reserve + e.id)) }
                        }
                        val k = reserve.indexOf(e.id)
                        if (k >= 0) {
                            SKPill("↑", height = 30.dp, hPad = 12.dp) {
                                if (k > 0) { val n = reserve.toMutableList(); n[k] = n[k - 1]; n[k - 1] = e.id; send("PATCH", "", mapOf("reserve" to n)) }
                            }
                            SKPill("↓", height = 30.dp, hPad = 12.dp) {
                                if (k < reserve.size - 1) { val n = reserve.toMutableList(); n[k] = n[k + 1]; n[k + 1] = e.id; send("PATCH", "", mapOf("reserve" to n)) }
                            }
                            SKPill("Ut av reserve", height = 30.dp, hPad = 10.dp) { send("PATCH", "", mapOf("reserve" to reserve.filter { it != e.id })) }
                        }
                        SKPill(if (confirm == e.id) "Sikker? Fjern" else "Fjern", height = 30.dp, hPad = 10.dp, border = C.danger.copy(alpha = 0.5f), fg = C.danger) {
                            if (confirm == e.id) { confirm = ""; send("DELETE", "/enheter/${Hjem.enc(e.id)}", null) } else confirm = e.id
                        }
                    }
                }
            }
        }
        val k = kode
        if (k != null) {
            Column(
                Modifier.fillMaxWidth().skBox(C.selBg, C.selLine, 12.dp).padding(16.dp),
                horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                T(k, mono(40f, C.accent2, 0.18f, W.Medium))
                T("Tast inn koden på enheten under Innstillinger → Skjold-hjem", sora(13f), align = TextAlign.Center)
                T("Gyldig i 10 minutter", sora(11f, W.Regular, C.muted))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    SKPill("Oppdater liste", height = 32.dp) { scope.launch { load() } }
                    SKPill("Ferdig", height = 32.dp) { kode = null }
                }
            }
        } else {
            Flow(8.dp) {
                SKPill("Legg til enhet", primary = true, height = 40.dp) {
                    scope.launch {
                        when (val r = Hjem.call("POST", "/api/hjem/steder/${Hjem.enc(s.id)}/kobling", emptyMap())) {
                            is HjemSvar.Ok -> { kode = jsonObject(r.data)?.str("kode"); Haptics.success() }
                            is HjemSvar.Login -> m.hjemLogin = true
                            is HjemSvar.Feil -> { msg = r.msg; Haptics.error() }
                        }
                    }
                }
                if (s.id != m.stedId) SKPill("Bruk dette stedet", height = 40.dp) { scope.launch { m.selectSted(s.id) } }
                if (s.rolle == "eier") {
                    SKPill(if (confirm == "sted") "Sikker? Slett" else "Slett sted", height = 40.dp, border = C.danger.copy(alpha = 0.5f), fg = C.danger) {
                        if (confirm != "sted") { confirm = "sted"; return@SKPill }
                        confirm = ""
                        scope.launch {
                            val r = Hjem.call("DELETE", "/api/hjem/steder/${Hjem.enc(s.id)}")
                            if (r is HjemSvar.Feil) { msg = r.msg; Haptics.error(); return@launch }
                            if (s.id == m.stedId) m.selectSted("")
                            m.loadSteder()
                        }
                    }
                }
            }
        }
        if (msg.isNotEmpty()) T(msg, sora(12f, W.Regular, C.danger))
    }
}

/** Innstillinger → Skjold-hjem på enheten selv (GET/POST /api/sky via LAN eller relé). */
@Composable
fun SkyDeviceView(m: AppModel) {
    var st by remember { mutableStateOf<JSONObject?>(null) }
    var kode by remember { mutableStateOf("") }
    var err by remember { mutableStateOf("") }
    var confirm by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    val h = m.settingsHost
    LaunchedEffect(h) {
        while (isActive) {
            if (h == null) err = "Ingen enhet valgt"
            else {
                val d = DeviceLink.get("/api/sky", on = h)
                if (d == null) err = "Enheten svarer ikke på /api/sky – oppdater programvaren på enheten." else { st = jsonObject(d); err = "" }
            }
            delay(5000)
        }
    }
    fun send(body: Map<String, Any?>) {
        val host = h ?: return
        Haptics.tap()
        scope.launch {
            val d = DeviceLink.send("/api/sky", body, on = host, timeout = 15.0)
            if (d != null) { st = jsonObject(d); kode = ""; err = ""; Haptics.success() }
            else { err = "Enheten godtok ikke forespørselen. Sjekk koden (gyldig i 10 minutter)."; Haptics.error() }
        }
    }
    val o = st
    val koblet = o?.bool("koblet") == true
    val tilkoblet = o?.bool("tilkoblet") == true
    val navn = o?.str("stedNavn")?.ifEmpty { null } ?: o?.str("sted")?.ifEmpty { null } ?: "Skjold-hjem"
    Column(Modifier.fillMaxWidth().skBox(C.card, C.line).padding(14.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            T(if (koblet) "Koblet til $navn" else "Ikke koblet til Skjold-hjem", sora(15f, W.Semibold), Modifier.weight(1f))
            if (o != null) T(if (tilkoblet) "● Tilkoblet skyen" else if (koblet) "○ Ikke tilkoblet nå" else "", sora(12f, W.Regular, if (tilkoblet) C.ok else C.muted))
        }
        if (koblet) {
            val aktiv = o?.str("aktivHoved") ?: ""
            T((if (o?.bool("erHoved") == true) "Denne enheten er stedets hovedenhet" else "Denne enheten er med i stedet") + if (aktiv.isEmpty()) "." else " · kontaktpunkt nå: $aktiv.", sora(12f, W.Regular, C.ink2))
            SKPill(if (confirm) "Sikker? Koble fra" else "Koble fra", height = 36.dp, border = C.danger.copy(alpha = 0.5f), fg = C.danger) {
                if (!confirm) confirm = true else { confirm = false; send(mapOf("koble_fra" to true)) }
            }
        } else {
            T("Lag en kode under Innstillinger → Steder → «Legg til enhet», og tast den inn her.", sora(12f, W.Regular, C.ink2))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                SKField("K7Q2XM", kode, { v -> kode = v.uppercase().filter { it.isLetterOrDigit() } }, Modifier.weight(1f), height = 44.dp, size = 18f, mono = true, plainInput = true, maxLength = 6)
                SKPill("Koble til", primary = true, height = 44.dp) {
                    if (kode.length != 6) err = "Koden har seks tegn" else send(mapOf("kode" to kode))
                }
            }
        }
        if (err.isNotEmpty()) T(err, sora(12f, W.Regular, C.danger))
    }
}

/** Innlogging i Cloudflare Access i en WebView; CF_Authorization hentes fra CookieManager når den finnes. */
@SuppressLint("SetJavaScriptEnabled")
@Composable
fun HjemLoginView(m: AppModel) {
    Column(Modifier.fillMaxSize().background(C.bg).windowInsetsPadding(WindowInsets.statusBars)) {
        Row(Modifier.fillMaxWidth().padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            T("Logg inn på Skjold-hjem", sora(15f, W.Semibold), Modifier.weight(1f))
            SKLinkButton("Avbryt") { m.hjemLogin = false }
        }
        AndroidView(
            modifier = Modifier.fillMaxWidth().weight(1f),
            factory = { ctx ->
                CookieManager.getInstance().setAcceptCookie(true)
                WebView(ctx).apply {
                    settings.javaScriptEnabled = true
                    settings.domStorageEnabled = true
                    CookieManager.getInstance().setAcceptThirdPartyCookies(this, true)
                    var done = false
                    webViewClient = object : WebViewClient() {
                        override fun onPageFinished(view: WebView?, url: String?) {
                            if (done) return
                            val t = Hjem.cookieFromWebView() ?: return
                            done = true
                            CookieManager.getInstance().flush()
                            m.hjemLoggedIn(t)
                        }
                    }
                    loadUrl(Hjem.base + "/api/hjem/steder")
                }
            },
        )
    }
}
