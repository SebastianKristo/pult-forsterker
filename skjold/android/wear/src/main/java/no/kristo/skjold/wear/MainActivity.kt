package no.kristo.skjold.wear

import android.os.Bundle
import android.view.HapticFeedbackConstants
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.focusable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.rotary.onRotaryScrollEvent
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.wear.compose.foundation.lazy.ScalingLazyColumn
import androidx.wear.compose.foundation.lazy.items
import androidx.wear.compose.material.Button
import androidx.wear.compose.material.ButtonDefaults
import androidx.wear.compose.material.Chip
import androidx.wear.compose.material.ChipDefaults
import androidx.wear.compose.material.CircularProgressIndicator
import androidx.wear.compose.material.MaterialTheme
import androidx.wear.compose.material.Text
import coil.compose.AsyncImage

private val Gold = Color(0xFFD9A54A)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        WearStore.start(this)
        setContent { MaterialTheme { SkjoldWear() } }
    }

    override fun onDestroy() {
        WearStore.stop()
        super.onDestroy()
    }
}

@Composable
fun SkjoldWear() {
    val pager = rememberPagerState(pageCount = { 3 })
    HorizontalPager(state = pager, modifier = Modifier.fillMaxSize().background(Color.Black)) { page ->
        when (page) {
            0 -> NowPlaying(active = pager.currentPage == 0)
            1 -> Favorites()
            else -> Rooms()
        }
    }
}

@Composable
fun Art(path: String, title: String, size: Dp) {
    val url = WearStore.imageUrl(path)
    Box(
        Modifier.size(size).clip(RoundedCornerShape(size * 0.18f))
            .background(Brush.linearGradient(listOf(Gold.copy(alpha = 0.55f), Color(0xFF1E1E20)))),
        contentAlignment = Alignment.Center,
    ) {
        Text(title.take(1), fontSize = (size.value * 0.4f).sp, color = Color.White, fontWeight = FontWeight.SemiBold)
        if (url != null) AsyncImage(model = url, contentDescription = null, contentScale = ContentScale.Crop, modifier = Modifier.size(size))
    }
}

/** Spiller nå. Skiven/den roterende knappen styrer volumet: tikk per steg, tydelig klikk ved 0 og 100. */
@Composable
fun NowPlaying(active: Boolean) {
    val st = WearStore.status
    val view = LocalView.current
    val focus = remember { FocusRequester() }
    var acc by remember { mutableFloatStateOf(0f) }
    LaunchedEffect(active) { if (active) try { focus.requestFocus() } catch (_: Exception) { } }

    Box(
        Modifier.fillMaxSize()
            .onRotaryScrollEvent { e ->
                acc += e.verticalScrollPixels
                val steps = (acc / 24f).toInt()
                if (steps != 0) {
                    acc -= steps * 24f
                    val before = WearStore.status.volume
                    val n = (before + steps).coerceIn(0, 100)
                    if (n != before) {
                        WearStore.setVolume(n)
                        view.performHapticFeedback(if (n == 0 || n == 100) HapticFeedbackConstants.LONG_PRESS else HapticFeedbackConstants.CLOCK_TICK)
                    }
                }
                true
            }
            .focusRequester(focus)
            .focusable(),
        contentAlignment = Alignment.Center,
    ) {
        CircularProgressIndicator(
            progress = st.volume / 100f, modifier = Modifier.fillMaxSize().padding(2.dp),
            indicatorColor = Gold, trackColor = Color(0x33FFFFFF), strokeWidth = 4.dp,
        )
        if (WearStore.host.isEmpty()) {
            Text("Åpne Skjold på telefonen for å koble til klokka.", textAlign = TextAlign.Center, fontSize = 13.sp,
                modifier = Modifier.padding(24.dp))
        } else {
            Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.padding(horizontal = 22.dp)) {
                Text(
                    WearStore.roomName + when { !WearStore.reachable -> " · frakoblet"; WearStore.viaPhone -> " · via telefon"; else -> "" },
                    color = Gold, fontSize = 12.sp, maxLines = 1, overflow = TextOverflow.Ellipsis,
                )
                Spacer(Modifier.height(4.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Art(st.art, st.title.ifEmpty { WearStore.roomName }, 40.dp)
                    Spacer(Modifier.width(6.dp))
                    Column(Modifier.width(96.dp)) {
                        Text(st.title.ifEmpty { if (st.power) "Ingenting spilles" else "Av" }, fontSize = 14.sp,
                            fontWeight = FontWeight.SemiBold, maxLines = 2, overflow = TextOverflow.Ellipsis)
                        if (st.artist.isNotEmpty()) Text(st.artist, fontSize = 11.sp, color = Color(0xFFAAAAAA), maxLines = 1, overflow = TextOverflow.Ellipsis)
                    }
                }
                Spacer(Modifier.height(6.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    Button(onClick = { WearStore.power(!st.power) }, modifier = Modifier.size(ButtonDefaults.SmallButtonSize),
                        colors = ButtonDefaults.buttonColors(backgroundColor = if (st.power) Gold else Color(0xFF333333))) { Text("⏻") }
                    Button(onClick = { WearStore.transport("playpause") }, modifier = Modifier.size(ButtonDefaults.SmallButtonSize)) {
                        Text(if (st.playing) "❚❚" else "▶")
                    }
                    Button(onClick = { WearStore.transport("next") }, modifier = Modifier.size(ButtonDefaults.SmallButtonSize)) { Text("⏭") }
                }
                Text("Volum ${st.volume}", fontSize = 11.sp, color = Color(0xFFAAAAAA), modifier = Modifier.padding(top = 4.dp))
            }
        }
    }
}

@Composable
fun Favorites() {
    val st = WearStore.status
    val view = LocalView.current
    ScalingLazyColumn(Modifier.fillMaxSize()) {
        item { Text("Favoritter", color = Gold, fontSize = 14.sp, fontWeight = FontWeight.SemiBold) }
        if (st.favs.isEmpty()) item { Text("Ingen favoritter", fontSize = 12.sp, color = Color(0xFFAAAAAA)) }
        items(st.favs) { f ->
            Chip(
                onClick = { view.performHapticFeedback(HapticFeedbackConstants.VIRTUAL_KEY); WearStore.playFav(f.n) },
                label = { Text(f.title, maxLines = 2, overflow = TextOverflow.Ellipsis) },
                icon = { Art(f.logo, f.title, 28.dp) },
                colors = if (st.preset == f.n && st.power) ChipDefaults.primaryChipColors(backgroundColor = Gold) else ChipDefaults.secondaryChipColors(),
                modifier = Modifier.fillMaxWidth(),
            )
        }
    }
}

@Composable
fun Rooms() {
    val view = LocalView.current
    ScalingLazyColumn(Modifier.fillMaxSize()) {
        item { Text("Rom", color = Gold, fontSize = 14.sp, fontWeight = FontWeight.SemiBold) }
        if (WearStore.rooms.isEmpty()) item {
            Text("Åpne Skjold på telefonen for å hente rommene.", fontSize = 12.sp, color = Color(0xFFAAAAAA), textAlign = TextAlign.Center)
        }
        items(WearStore.rooms) { r ->
            Chip(
                onClick = { view.performHapticFeedback(HapticFeedbackConstants.VIRTUAL_KEY); WearStore.select(r) },
                label = { Text(r.name, maxLines = 1, overflow = TextOverflow.Ellipsis) },
                secondaryLabel = { Text(if (r.host == WearStore.host) "Valgt" else r.product.uppercase()) },
                colors = if (r.host == WearStore.host) ChipDefaults.primaryChipColors(backgroundColor = Gold) else ChipDefaults.secondaryChipColors(),
                modifier = Modifier.fillMaxWidth(),
            )
        }
    }
}
