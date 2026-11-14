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
    /** Seksjonene Android-appen viser, i standardrekkefølge (samme som iOS: HomeLayout.ios). */
    val android = listOf("recent", "sources", "favs", "playlists", "library")

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

