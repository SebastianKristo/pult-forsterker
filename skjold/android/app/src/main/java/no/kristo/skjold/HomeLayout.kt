package no.kristo.skjold

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import org.json.JSONArray

/** Én seksjon på hjemskjermen. Samme id-er som web (lib/homelayout.ts), iOS og pi/skjold_homelayout.py. */
data class HomeItem(val id: String, val visible: Boolean)

/** Rekkefølge og synlighet for seksjonene på hjemskjermen (settings.homeLayout) – per Skjold-enhet, synkes via /api/settings. */
object HomeLayout {
    val sections = listOf(
        "recent" to "Nylig spilt", "favs" to "Radiofavoritter", "sources" to "Kilder", "routines" to "Rutiner",
        "discover" to "Oppdag", "ask" to "Spill noe til …", "nrk" to "Fortsett på NRK", "playlists" to "Dine spillelister",
        "library" to "Fra bibliotekene", "wrapped" to "Skjold Wrapped",
    )
    /** Seksjonene Android-appen viser, i standardrekkefølge. */
    val android = listOf("recent", "sources", "favs", "playlists")

    fun label(id: String): String = sections.firstOrNull { it.first == id }?.second ?: id

    /** Lagret rekkefølge først (bare kjente id-er), deretter manglende seksjoner – synlige – på slutten. */
    fun resolve(layout: List<HomeItem>, available: List<String>): List<HomeItem> {
        val out = ArrayList<HomeItem>()
        for (it in layout) if (it.id in available && out.none { o -> o.id == it.id }) out.add(it)
        for (id in available) if (out.none { it.id == id }) out.add(HomeItem(id, true))
        return out
    }

    fun parse(a: JSONArray?): List<HomeItem>? {
        if (a == null) return null
        val out = ArrayList<HomeItem>()
        for (i in 0 until a.length()) {
            val o = a.optJSONObject(i) ?: continue
            val id = o.optString("id", "")
            if (id.isNotEmpty()) out.add(HomeItem(id, o.optBoolean("visible", true)))
        }
        return out
    }

    fun toJson(items: List<HomeItem>): List<Map<String, Any?>> = items.map { mapOf("id" to it.id, "visible" to it.visible) }
}

/** «Rediger hjemskjerm» (som Plexamp): opp/ned for rekkefølge og bryter for å vise/skjule. Lagres på Skjold-enheten. */
@Composable
fun HomeEditorDialog(m: AppModel, onClose: () -> Unit) {
    Dialog(onDismissRequest = onClose) {
        val items = HomeLayout.resolve(m.homeLayout, HomeLayout.android)
        Column(
            Modifier.fillMaxWidth().clip(RoundedCornerShape(20.dp)).background(C.card).padding(18.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            T("Rediger hjemskjerm", sora(17f, W.Semibold))
            T("Endringene gjelder dette rommet og vises også i web-UI-et og iOS-appen.", sora(12f, W.Regular, C.muted), Modifier.padding(bottom = 8.dp))
            items.forEachIndexed { i, it ->
                Row(Modifier.fillMaxWidth().padding(vertical = 6.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    T(HomeLayout.label(it.id), sora(15f, W.Regular, if (it.visible) C.ink else C.muted), Modifier.weight(1f), maxLines = 1)
                    Arrow("↑", enabled = i > 0) { m.saveHomeLayout(items.toMutableList().also { l -> val x = l.removeAt(i); l.add(i - 1, x) }) }
                    Arrow("↓", enabled = i < items.size - 1) { m.saveHomeLayout(items.toMutableList().also { l -> val x = l.removeAt(i); l.add(i + 1, x) }) }
                    SKToggle(it.visible) { m.saveHomeLayout(items.map { o -> if (o.id == it.id) o.copy(visible = !o.visible) else o }) }
                }
            }
            Row(Modifier.fillMaxWidth().padding(top = 10.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                T("Tilbakestill", sora(14f, W.Regular, C.ink2), Modifier.press { m.resetHomeLayout() }.padding(8.dp))
                T("Ferdig", sora(14f, W.Semibold, C.accent), Modifier.press(onClick = onClose).padding(8.dp))
            }
        }
    }
}

@Composable
private fun Arrow(s: String, enabled: Boolean, onClick: () -> Unit) {
    Box(
        Modifier.size(34.dp).clip(RoundedCornerShape(9.dp)).skBorder(C.line2, 9.dp).press(enabled = enabled, onClick = onClick),
        contentAlignment = Alignment.Center,
    ) { T(s, sora(15f, W.Regular, if (enabled) C.ink2 else C.line2)) }
}

