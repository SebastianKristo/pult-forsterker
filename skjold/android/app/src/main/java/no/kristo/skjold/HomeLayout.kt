package no.kristo.skjold

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.MutableTransitionState
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.input.pointer.positionChange
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.compose.ui.zIndex
import kotlinx.coroutines.flow.first
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


// MARK: - Rediger hjemskjerm (V4HomeEditor)

private val editSheetBg = hex(0x1c1c1e)   // grupperte lister i et ark (mørk modus)
private val editRowBg = hex(0x2c2c2e)
private val editRowLift = hex(0x3a3a3c)
private val editSep = Color.White.copy(alpha = 0.1f)
private val editRed = hex(0xff453a)
private val editRowH = 52.dp

/**
 * «Rediger hjemskjerm» (som Plexamp): et ark med seksjonene og kildene som lister i redigeringsmodus –
 * bryter for å vise/skjule og håndtak (≡) til høyre for å dra i ny rekkefølge. Seksjonene lagres på
 * Skjold-enheten (settings.homeLayout), kildene på telefonen. «Ferdig» lukker, «Tilbakestill» nullstiller begge.
 */
@Composable
fun HomeEditorSheet(m: AppModel, onClose: () -> Unit) {
    val vis = remember { MutableTransitionState(false).apply { targetState = true } }
    val close = { vis.targetState = false }
    val done by rememberUpdatedState(onClose)
    LaunchedEffect(Unit) {
        snapshotFlow { vis.isIdle && !vis.currentState && !vis.targetState }.first { it }
        done()
    }
    Dialog(onDismissRequest = close, properties = DialogProperties(usePlatformDefaultWidth = false, decorFitsSystemWindows = false)) {
        HomeNoDialogDim()
        val scrim by animateFloatAsState(if (vis.targetState) 0.4f else 0f, tween(300), label = "editScrim")
        Box(Modifier.fillMaxSize().background(Color.Black.copy(alpha = scrim)).pointerInput(Unit) { detectTapGestures { close() } }) {
            AnimatedVisibility(
                vis, Modifier.align(Alignment.BottomCenter),
                enter = slideInVertically(tween(420, easing = CubicBezierEasing(0.2f, 0.8f, 0.2f, 1f))) { it },
                exit = slideOutVertically(tween(300)) { it },
            ) {
                Column(
                    Modifier.fillMaxSize().statusBarsPadding().padding(top = 10.dp)
                        .clip(RoundedCornerShape(topStart = 34.dp, topEnd = 34.dp)).background(editSheetBg)
                        .pointerInput(Unit) { detectTapGestures { } },   // trykk i arket lukker det ikke
                ) {
                    // verktøylinje: tittel i midten, «Ferdig» til høyre
                    Box(Modifier.fillMaxWidth().padding(start = 16.dp, end = 16.dp, top = 12.dp, bottom = 8.dp).height(44.dp)) {
                        T("Rediger hjemskjerm", sora(17f, W.Semibold), Modifier.align(Alignment.Center), maxLines = 1)
                        Box(
                            Modifier.align(Alignment.CenterEnd).height(44.dp).clip(CircleShape).background(HomeV4.goldDark)
                                .press(label = "Ferdig") { close() }.padding(horizontal = 18.dp),
                            contentAlignment = Alignment.Center,
                        ) { T("Ferdig", sora(15f, W.Semibold, C.bg)) }
                    }
                    Column(
                        Modifier.weight(1f).verticalScroll(rememberScrollState()).padding(horizontal = 16.dp)
                            .navigationBarsPadding().padding(top = 12.dp, bottom = 32.dp),
                    ) {
                        val items = HomeLayout.resolve(m.homeLayout, HomeLayout.android)
                        EditList(items, { HomeLayout.label(it) },
                            onToggle = { id, v -> m.saveHomeLayout(items.map { if (it.id == id) HomeItem(it.id, v) else it }) },
                            onMove = { m.saveHomeLayout(it) })
                        EditFooter("Endringene gjelder dette rommet og vises også i web-UI-et og iOS-appen.")

                        val kilder = HomeLayout.resolve(m.homeSources, homeAlleKilder(m.actRoom.type).map { it.first })
                        T("KILDER", sora(13f, W.Regular, HomeV4.muted), Modifier.padding(start = 16.dp, top = 30.dp, bottom = 8.dp))
                        EditList(kilder, { it },
                            onToggle = { id, v -> m.homeSources = kilder.map { if (it.id == id) HomeItem(it.id, v) else it } },
                            onMove = { m.homeSources = it })
                        EditFooter("Slå av kilder du ikke bruker, og dra dem i den rekkefølgen du vil ha på Hjem. Lagres på denne telefonen.")

                        Box(
                            Modifier.padding(top = 30.dp).fillMaxWidth().height(editRowH).clip(RoundedCornerShape(22.dp)).background(editRowBg)
                                .press { m.resetHomeLayout(); m.homeSources = emptyList() }.padding(horizontal = 16.dp),
                            contentAlignment = Alignment.CenterStart,
                        ) { T("Tilbakestill", sora(17f, W.Regular, editRed)) }
                    }
                }
            }
        }
    }
}

@Composable
private fun EditFooter(text: String) =
    T(text, sora(13f, W.Regular, HomeV4.muted, 1.35f), Modifier.padding(start = 16.dp, end = 16.dp, top = 8.dp))

/**
 * Liste i redigeringsmodus: navn, bryter og håndtak. Draget starter på håndtaket (ytterst til høyre) og følger
 * fingeren; raden bytter plass med naboen når den er dratt over halvveis, og rekkefølgen lagres når fingeren slippes.
 */
@Composable
private fun EditList(items: List<HomeItem>, label: (String) -> String, onToggle: (String, Boolean) -> Unit, onMove: (List<HomeItem>) -> Unit) {
    var local by remember { mutableStateOf<List<HomeItem>?>(null) }
    var dragId by remember { mutableStateOf<String?>(null) }
    var dy by remember { mutableFloatStateOf(0f) }
    val latest by rememberUpdatedState(items)
    val move by rememberUpdatedState(onMove)
    val rowPx = with(LocalDensity.current) { editRowH.toPx() }
    val shown = local ?: items
    Column(
        Modifier.fillMaxWidth().clip(RoundedCornerShape(22.dp)).background(editRowBg)
            .pointerInput(Unit) {
                awaitEachGesture {
                    val down = awaitFirstDown(requireUnconsumed = false)
                    if (down.position.x < size.width - 52.dp.toPx()) return@awaitEachGesture
                    val start = latest
                    val idx0 = (down.position.y / rowPx).toInt()
                    if (idx0 !in start.indices) return@awaitEachGesture
                    val id = start[idx0].id
                    down.consume()
                    local = start; dragId = id; dy = 0f
                    Haptics.tick()
                    while (true) {
                        val ev = awaitPointerEvent()
                        val ch = ev.changes.firstOrNull { it.id == down.id } ?: break
                        if (!ch.pressed) break
                        dy += ch.positionChange().y
                        ch.consume()
                        val l = local ?: break
                        val i = l.indexOfFirst { it.id == id }
                        if (dy > rowPx / 2 && i < l.size - 1) {
                            local = l.toMutableList().apply { add(i + 1, removeAt(i)) }; dy -= rowPx; Haptics.tick()
                        } else if (dy < -rowPx / 2 && i > 0) {
                            local = l.toMutableList().apply { add(i - 1, removeAt(i)) }; dy += rowPx; Haptics.tick()
                        }
                    }
                    val end = local
                    local = null; dragId = null; dy = 0f
                    if (end != null && end.map { it.id } != start.map { it.id }) move(end)
                }
            },
    ) {
        shown.forEachIndexed { i, it ->
            key(it.id) {
                val dragging = dragId == it.id
                Row(
                    Modifier.fillMaxWidth().height(editRowH).zIndex(if (dragging) 1f else 0f)
                        .graphicsLayer { translationY = if (dragging) dy else 0f }
                        .background(if (dragging) editRowLift else Color.Transparent)
                        .drawBehind {
                            if (i > 0 && !dragging) drawRect(editSep, Offset(16.dp.toPx(), 0f), Size(size.width - 16.dp.toPx(), 0.5.dp.toPx()))
                        }
                        .padding(start = 16.dp, end = 4.dp),
                    verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    T(label(it.id), sora(17f), Modifier.weight(1f), maxLines = 1)
                    HomeSwitch(it.visible, label(it.id)) { onToggle(it.id, !it.visible) }
                    Box(Modifier.size(44.dp), contentAlignment = Alignment.Center) {
                        SKIcon(HomeV4.handle, 20.dp, 1.8f, HomeV4.muted)
                    }
                }
            }
        }
    }
}
