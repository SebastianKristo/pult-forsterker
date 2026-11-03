package no.kristo.skjold

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import org.json.JSONObject

/** One network from GET /api/wifi. */
data class WifiNet(val ssid: String, val signal: Int, val secure: Boolean, val active: Boolean) {
    companion object {
        fun parse(d: ByteArray): List<WifiNet> = try {
            val arr = JSONObject(String(d)).optJSONArray("networks")
            val out = mutableListOf<WifiNet>()
            if (arr != null) for (i in 0 until arr.length()) {
                val x = arr.optJSONObject(i) ?: continue
                val s = x.optString("ssid")
                if (s.isEmpty() || out.any { it.ssid == s }) continue
                out.add(WifiNet(s, x.optInt("signal", 0), x.optString("security", "wpa2") != "open", x.optBoolean("active", false)))
            }
            out
        } catch (_: Exception) { emptyList() }

        fun errText(d: ByteArray, code: Int): String = try {
            JSONObject(String(d)).optString("error").ifEmpty { "HTTP $code" }
        } catch (_: Exception) { "HTTP $code" }
    }
}

private const val LOCK = "M5 11h14v10H5zM8 11V7a4 4 0 0 1 8 0v4"

/** Innstillinger → Tilkobling → Wi-Fi: change the network later (same choices as the Wi-Fi step in setup). */
@Composable
fun WifiSettingsView(m: AppModel) {
    val scope = rememberCoroutineScope()
    var open by remember { mutableStateOf(false) }
    var nets by remember { mutableStateOf(listOf<WifiNet>()) }
    var loading by remember { mutableStateOf(true) }
    var unavailable by remember { mutableStateOf("") }
    var pick by remember { mutableIntStateOf(-1) }      // -1 none, -2 «Annet nettverk …», else index
    var ssid by remember { mutableStateOf("") }
    var sec by remember { mutableIntStateOf(0) }
    var pw by remember { mutableStateOf("") }
    var phase by remember { mutableStateOf("") }        // "", connecting, waiting, done, lost
    var err by remember { mutableStateOf("") }
    var alt by remember { mutableStateOf("") }

    suspend fun scan() {
        loading = true
        val h = m.activeHost
        val url = if (h != null) Net.url(h, "/api/wifi") else null
        if (url == null) { unavailable = "ingen enhet valgt"; loading = false; return }
        val r = Net.data(url, timeout = 25.0)
        if (r == null) unavailable = "svarer ikke"
        else if (r.second >= 300) unavailable = WifiNet.errText(r.first, r.second)
        else { unavailable = ""; nets = WifiNet.parse(r.first); if (pick >= nets.size) pick = -1 }
        loading = false
    }

    LaunchedEffect(m.activeHost) { scan() }

    val manual = pick == -2
    val picked = nets.getOrNull(pick)
    val needPw = if (manual) sec < 2 else (picked?.secure ?: false)
    val busy = phase == "connecting" || phase == "waiting"
    val hasNet = if (manual) ssid.trim().isNotEmpty() else picked != null
    val canJoin = !busy && hasNet && (!needPw || pw.length >= 8)
    val activeName = nets.firstOrNull { it.active }?.ssid
    val summary = when {
        loading -> "Henter …"
        unavailable.isNotEmpty() -> "Ikke tilgjengelig"
        activeName != null -> "Tilkoblet $activeName"
        else -> "Ikke tilkoblet Wi-Fi (kabel eller ukjent)"
    }

    /** After switching: wait up to 60 s for the device to answer again (same address, else <id>.local). */
    suspend fun waitBack(host: String) {
        phase = "waiting"
        val id = m.dev?.id ?: ""
        val local = if (id.isEmpty()) "" else "$id.local:8765"
        val start = System.currentTimeMillis()
        while (System.currentTimeMillis() - start < 60_000) {
            delay(3000)
            if (DeviceLink.get("/api/status", on = host, timeout = 4.0) != null) {
                phase = "done"; Haptics.success(); scan(); return
            }
            if (local.isNotEmpty() && local != host && DeviceLink.get("/api/status", on = local, timeout = 4.0) != null) {
                m.activeHost = local
                phase = "done"; Haptics.success(); scan(); return
            }
        }
        alt = local
        phase = "lost"; Haptics.error()
    }

    fun join() {
        val h = m.activeHost ?: return
        val url = Net.url(h, "/api/wifi") ?: return
        val name = if (manual) ssid.trim() else picked?.ssid ?: ""
        val body = mutableMapOf<String, Any?>("ssid" to name, "hidden" to manual)
        if (needPw) body["psk"] = pw
        if (manual) body["security"] = listOf("wpa2", "wpa3", "open")[sec]
        err = ""; alt = ""; phase = "connecting"
        scope.launch {
            val r = Net.data(url, "POST", DeviceLink.json(body), 50.0)
            if (r != null && r.second >= 300) {
                phase = ""; err = "Fikk ikke koblet til «$name»: " + WifiNet.errText(r.first, r.second)
                Haptics.error()
            } else {
                // null = the connection dropped while the device switched network – wait for it either way
                pw = ""
                waitBack(h)
            }
        }
    }

    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        SKCard {
            Row(
                Modifier.fillMaxWidth().heightIn(min = 54.dp).press { open = !open }.padding(horizontal = 14.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    T("Wi-Fi", sora(14f))
                    T(summary, sora(11f, W.Regular, C.muted), maxLines = 1)
                }
                T(if (open) "Lukk" else "Endre", sora(13f, W.Regular, C.accent))
            }
        }
        if (open) {
            if (unavailable.isNotEmpty()) {
                T("Enheten kan ikke styre Wi-Fi herfra ($unavailable). Den trenger NetworkManager (Skjold OS / Raspberry Pi OS Bookworm). Wi-Fi kan også settes i Skjold Flasher.",
                    sora(12f, W.Regular, C.danger, 1.5f))
            } else {
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    T("Velg nettverk", sora(14f, W.Semibold), Modifier.weight(1f))
                    T("Oppdater", sora(13f, W.Regular, C.accent), Modifier.clickable { scope.launch { scan() } }.padding(vertical = 4.dp))
                }
                SKCard {
                    if (loading) NetRow("Leter etter nettverk …", null, false, true) {}
                    nets.forEachIndexed { i, n -> NetRow(n.ssid, n, pick == i, i == 0 && !loading) { pick = i } }
                    NetRow("Annet nettverk …", null, manual, false) { pick = -2 }
                }
                if (manual) {
                    SKField("Nettverksnavn (SSID)", ssid, { ssid = it }, height = 44.dp, size = 15f, plainInput = true)
                    Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        listOf("WPA2", "WPA3", "Ingen").forEachIndexed { i, label ->
                            val s = SelStyle.of(sec == i)
                            Box(Modifier.weight(1f).height(36.dp).clip(CircleShape).background(s.bg).skCapsuleBorder(s.bd).press { sec = i }, contentAlignment = Alignment.Center) {
                                T(label, sora(13f, W.Regular, s.fg), maxLines = 1)
                            }
                        }
                    }
                }
                if (needPw) SKField("Passord (minst 8 tegn)", pw, { pw = it }, height = 44.dp, size = 15f, secure = true)
                T("Når enheten bytter nettverk, mister den forbindelsen noen sekunder. Appen kobler til igjen av seg selv. Havner telefonen på et annet nett enn enheten, finner du den ikke før de er på samme nett.",
                    sora(12f, W.Regular, C.muted, 1.5f))
                if (err.isNotEmpty()) T(err, sora(12f, W.Regular, C.danger, 1.45f))
                if (phase == "waiting") T("Bytter nettverk – venter på at enheten svarer igjen …", sora(12f, W.Regular, C.accent2))
                if (phase == "done") T("Enheten er tilkoblet og svarer.", sora(12f, W.Regular, C.ok))
                if (phase == "lost") T(
                    if (alt.isEmpty()) "Enheten svarer ikke. Koble telefonen til samme nett som enheten og prøv igjen."
                    else "Enheten svarer ikke. Koble telefonen til samme nett som enheten – den finnes da på $alt.",
                    sora(12f, W.Regular, C.danger, 1.45f))
                Box(
                    Modifier.fillMaxWidth().height(44.dp).clip(RoundedCornerShape(12.dp)).background(if (canJoin) C.accent else C.seg)
                        .press(enabled = canJoin) { join() },
                    contentAlignment = Alignment.Center,
                ) {
                    T(if (phase == "connecting") "Kobler til …" else if (phase == "waiting") "Venter …" else "Koble til",
                        sora(14f, W.Semibold, if (canJoin) C.bg else C.muted))
                }
            }
        }
    }
}

@Composable
private fun NetRow(title: String, net: WifiNet?, on: Boolean, first: Boolean, action: () -> Unit) {
    Row(
        Modifier.fillMaxWidth().heightIn(min = 50.dp).background(if (on) C.selBg else Color.Transparent)
            .topLine(if (first) Color.Transparent else C.line).press(onClick = action).padding(horizontal = 14.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        T(title, sora(14f, W.Regular, if (net == null && !on) C.ink2 else C.ink), Modifier.weight(1f, fill = false), maxLines = 1)
        if (net?.active == true) T("· tilkoblet", sora(11f, W.Regular, C.ok))
        Box(Modifier.weight(1f))
        if (net != null) {
            if (net.secure) SKIcon(LOCK, size = 12.dp, stroke = 2.4f, color = C.muted)
            Bars(net.signal)
        }
        T(if (on) "✓" else "", sora(12f, W.Regular, C.accent2), Modifier.width(10.dp))
    }
}

/** Four signal bars, lit by strength 0–100. */
@Composable
private fun Bars(sig: Int) {
    val lit = when { sig >= 75 -> 4; sig >= 50 -> 3; sig >= 25 -> 2; else -> 1 }
    Row(horizontalArrangement = Arrangement.spacedBy(2.dp), verticalAlignment = Alignment.Bottom) {
        for (i in 0 until 4) {
            Box(Modifier.width(3.dp).height((4 + i * 3).dp).clip(RoundedCornerShape(1.dp)).background(if (i < lit) C.ink2 else C.line))
        }
    }
}
