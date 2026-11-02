package no.kristo.skjold

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.width
import androidx.compose.runtime.Composable
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import coil.compose.AsyncImage
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import org.json.JSONObject

/** Cover / station art (Art.swift): a real logo when one is known, otherwise a 150° oklch gradient from a hash of the name. */
data class ArtInfo(
    val stops: List<Pair<Float, Color>>,
    val ink: Color,
    val logoAsset: String? = null,
    val logoURL: String? = null,
) {
    val hasLogo: Boolean get() = logoAsset != null || logoURL != null
    val base: Color get() = stops.firstOrNull()?.second ?: C.card
}

object ArtHash {
    fun hue(s: String): Int {
        var h = 0
        // UTF-16 code units like JS charCodeAt
        for (ch in s) h = (h * 31 + ch.code) % 360
        return h
    }
}

private val artCache = HashMap<String, Pair<List<Pair<Float, Color>>, Color>>()

fun art(key: String): ArtInfo {
    val (stops, ink) = synchronized(artCache) {
        artCache.getOrPut(key) {
            val h = ArtHash.hue(key).toDouble()
            val a = OKLCH.lab(0.42, 0.09, h); val b = OKLCH.lab(0.2, 0.04, ((h.toInt() + 40) % 360).toDouble())
            Pair(OKLCH.stops(a, b), OKLCH.color(0.93, 0.03, h))
        }
    }
    SK.nrkAsset[key]?.let { return ArtInfo(stops, Color.Transparent, logoAsset = it) }
    val u = CoverStore.url(key) ?: LogoStore.url(key)
    if (u != null) return ArtInfo(stops, Color.Transparent, logoURL = u)
    return ArtInfo(stops, ink)
}

/** Draws the art background: gradient, or logo on #121214 (NRK, 72 % wide) / #f4f2ee (others, cover). */
@Composable
fun ArtFill(info: ArtInfo, modifier: Modifier = Modifier) {
    when {
        info.logoAsset != null -> BoxWithConstraints(modifier.fillMaxSize().background(hex(0x121214)), contentAlignment = Alignment.Center) {
            AsyncImage(
                model = "file:///android_asset/nrk/${info.logoAsset}.svg", contentDescription = null,
                contentScale = ContentScale.Fit, modifier = Modifier.width(maxWidth * 0.72f),
            )
        }
        info.logoURL != null -> Box(modifier.fillMaxSize().background(hex(0xf4f2ee)).clipToBounds()) {
            AsyncImage(model = info.logoURL, contentDescription = null, contentScale = ContentScale.Crop, modifier = Modifier.fillMaxSize())
        }
        else -> Box(modifier.fillMaxSize().cssGradient(150.0, info.stops))
    }
}

@Composable
fun ArtFill(key: String, modifier: Modifier = Modifier) = ArtFill(art(key), modifier)

/** Real cover art by key (track title, album or playlist name, station). In memory only: the URLs carry tokens. */
object CoverStore {
    val urls = mutableStateMapOf<String, String>()

    fun url(key: String): String? = if (key.isEmpty()) null else urls[key]

    fun set(key: String, url: String) {
        if (key.isEmpty() || url.isEmpty() || urls[key] == url) return
        urls[key] = url
    }
}

/** Fetches station logos from Radio Browser (same source as the design) and caches the URLs. */
object LogoStore {
    private const val KEY = "skjold-logos-v2"
    val urls = mutableStateMapOf<String, String>()
    private val pending = HashSet<String>()
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)

    fun load() {
        val s = Store.prefs?.getString(KEY, null) ?: return
        try {
            val j = JSONObject(s)
            for (k in j.keys()) urls[k] = j.optString(k)
        } catch (_: Exception) {}
    }

    fun url(name: String): String? = urls[name]?.takeIf { it.isNotEmpty() }

    fun fetch(names: List<String>) {
        for (name in names) {
            if (urls.containsKey(name) || pending.contains(name) || SK.nrkAsset[name] != null) continue
            val (q, cc) = SK.logoQuery[name] ?: continue
            pending.add(name)
            scope.launch {
                val found = RadioBrowser.logo(q, cc)
                pending.remove(name)
                // null = network error (try again next launch), "" = no usable logo
                if (found != null) store(name, found)
            }
        }
    }

    /** Station image from the amplifier's favourites (only when no logo is known yet). */
    fun adopt(name: String, url: String) {
        if (url.isEmpty() || !url.lowercase().startsWith("https") || SK.nrkAsset[name] != null || (urls[name] ?: "").isNotEmpty()) return
        store(name, url)
    }

    private fun store(name: String, url: String) {
        urls[name] = url
        val j = JSONObject()
        urls.forEach { (k, v) -> j.put(k, v) }
        Store.prefs?.edit()?.putString(KEY, j.toString())?.apply()
    }
}
