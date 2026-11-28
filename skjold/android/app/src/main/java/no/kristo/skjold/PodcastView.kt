package no.kristo.skjold

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.asPaddingValues
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBars
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
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
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import org.json.JSONObject

/*
 * Podkaster som kildeside, som skjermen Podkaster i web-appen (skjold/app/src/screens/podcasts.tsx).
 * Alt hentes fra Skjold (/api/pod/…): Apple Podcasts-katalogen, NRK, egne RSS-adresser og Podme.
 * Favorittene lagres på enheten, så de er de samme i web-appen og på Skjold Touch.
 * Episodene spilles på enheten og fortsetter der du slapp.
 */

// MARK: - Data

/** En podkast. id: «apple:123», «nrk:serie», «rss:https://…» eller «podme:123». */
data class PodShow(
    val id: String,
    val title: String,
    val author: String = "",
    val image: String = "",
    val genre: String = "",
    val src: String = "",
    val kind: String = "",
) {
    /** Kilden. Mangler den, leses den fra id-en. */
    val source: String get() = src.ifEmpty { id.substringBefore(":", "") }

    fun body(): Map<String, Any?> {
        val b = linkedMapOf<String, Any?>("id" to id, "title" to title, "author" to author, "image" to image, "src" to source)
        if (genre.isNotEmpty()) b["genre"] = genre
        if (kind.isNotEmpty()) b["kind"] = kind
        return b
    }

    companion object {
        fun parse(o: JSONObject): PodShow? {
            val id = o.str("id")
            if (id.isEmpty()) return null
            return PodShow(id, o.str("title"), o.str("author"), o.str("image"), o.str("genre"), o.str("src"), o.str("kind"))
        }

        fun list(x: Any?): List<PodShow> = jsonList(x).mapNotNull { parse(it) }
    }
}

/** En episode. `nrk` betyr at den spilles via /api/nrk/play. */
data class PodEpisode(
    val id: String,
    val url: String,
    val title: String,
    val date: String,
    val duration: Double,
    val image: String,
    val description: String,
    val show: String,
    val pid: String,
    val nrk: Boolean,
    val podcast: Boolean?,
    val pos: Double,
    val heard: Boolean,
) {
    companion object {
        fun parse(o: JSONObject): PodEpisode? {
            val id = o.str("id")
            if (id.isEmpty()) return null
            return PodEpisode(
                id, o.str("url"), o.str("title"), o.str("date"), o.dbl("duration"), o.str("image"), o.str("description"),
                o.str("show"), o.str("pid"), o.bool("nrk"), if (o.has("podcast") && !o.isNull("podcast")) o.bool("podcast") else null,
                o.dbl("pos"), o.bool("heard"),
            )
        }

        fun list(x: Any?): List<PodEpisode> = jsonList(x).mapNotNull { parse(it) }
    }
}

/** En episode du har begynt på (Fortsett). */
data class PodProg(
    val id: String,
    val title: String,
    val series: String,
    val image: String,
    val url: String,
    val pid: String,
    val pos: Double,
    val dur: Double,
) {
    /** Som episode, så den kan spilles på samme måte. */
    fun episode(): PodEpisode = PodEpisode(id, url, title, "", dur, image, "", series, pid, false, null, pos, false)

    companion object {
        fun list(x: Any?): List<PodProg> = jsonList(x).mapNotNull { o ->
            val id = o.str("id")
            if (id.isEmpty()) null
            else PodProg(id, o.str("title"), o.str("series"), o.str("image"), o.str("url"), o.str("pid"), o.dbl("pos"), o.dbl("dur"))
        }
    }
}

/** En podkast med beskrivelse og episoder (GET /api/pod/show). */
data class PodShowDetail(val show: PodShow, val description: String, val fav: Boolean, val episodes: List<PodEpisode>)

// MARK: - API (/api/pod/* på Skjold)

object PodApi {
    private fun enc(s: String) = YtmLib.q(s)

    private suspend fun obj(path: String, host: String?, timeout: Double): JSONObject? =
        jsonObject(DeviceLink.get(path, on = host, timeout = timeout))

    suspend fun genres(host: String?): List<Pair<Int, String>>? {
        val o = obj("/api/pod/genres", host, 8.0) ?: return null
        return jsonList(o.opt("genres")).map { it.num("id") to it.str("name") }.filter { it.second.isNotEmpty() }
    }

    suspend fun top(host: String?, genre: Int): List<PodShow>? =
        obj("/api/pod/top?genre=$genre", host, 15.0)?.let { PodShow.list(it.opt("shows")) }

    suspend fun search(host: String?, q: String): List<PodShow>? =
        obj("/api/pod/search?q=" + enc(q), host, 15.0)?.let { PodShow.list(it.opt("shows")) }

    suspend fun show(host: String?, id: String, fresh: Boolean = false): PodShowDetail? {
        val o = obj("/api/pod/show?id=" + enc(id) + (if (fresh) "&fresh=1" else ""), host, 20.0) ?: return null
        val s = PodShow.parse(o) ?: PodShow(id, o.str("title"))
        return PodShowDetail(s, o.str("description"), o.bool("fav"), PodEpisode.list(o.opt("episodes")))
    }

    suspend fun favs(host: String?): List<PodShow>? =
        obj("/api/pod/favs", host, 8.0)?.let { PodShow.list(it.opt("items")) }

    /** Legger til eller fjerner en favoritt. Gir den nye listen, eller null hvis det ikke gikk. */
    suspend fun setFav(host: String?, s: PodShow, on: Boolean): List<PodShow>? {
        val body: Map<String, Any?> = if (on) mapOf("add" to s.body()) else mapOf("remove" to s.id)
        return jsonObject(DeviceLink.send("/api/pod/favs", body, on = host, timeout = 10.0))?.let { PodShow.list(it.opt("items")) }
    }

    suspend fun newest(host: String?): List<PodEpisode>? =
        obj("/api/pod/new", host, 30.0)?.let { PodEpisode.list(it.opt("items")) }

    suspend fun resume(host: String?): List<PodProg>? =
        obj("/api/pod/continue", host, 8.0)?.let { PodProg.list(it.opt("items")) }

    /** Spiller en episode på Skjold. Gir teksten som skal vises etterpå. */
    suspend fun play(host: String?, e: PodEpisode, show: PodShow?, restart: Boolean): String {
        val path: String
        val body = HashMap<String, Any?>()
        if (e.nrk) {
            path = "/api/nrk/play"
            body["id"] = e.id; body["title"] = e.title; body["series"] = e.show
            body["image"] = e.image; body["duration"] = e.duration
            e.podcast?.let { body["podcast"] = it }
        } else {
            path = "/api/pod/play"
            body["id"] = e.id; body["url"] = e.url; body["title"] = e.title
            body["show"] = show?.title?.takeIf { it.isNotEmpty() } ?: e.show
            body["image"] = e.image.ifEmpty { show?.image ?: "" }
            body["duration"] = e.duration
            body["pid"] = show?.id ?: e.pid
        }
        if (restart) body["restart"] = true
        val (d, code) = DeviceLink.sendCode(path, body, on = host, timeout = 15.0) ?: return "Fikk ikke svar fra Skjold"
        val o = jsonObject(d)
        if (code >= 400 || o == null || (o.has("ok") && !o.bool("ok"))) {
            val msg = o?.str("error").orEmpty()
            return if (msg.isEmpty()) "Kunne ikke spille episoden" else msg.replaceFirstChar { it.uppercase() }
        }
        val r = o.dbl("resume")
        return if (r > 0) "Fortsetter fra " + podMins(r) else "Spiller " + e.title
    }
}

/** «1 t 5 min» / «42 min». */
fun podMins(s: Double): String {
    val sec = s.toLong()
    return (if (sec >= 3600) "${sec / 3600} t " else "") + Math.round((sec % 3600) / 60.0) + " min"
}

private val podSrcText = mapOf("apple" to "PODKAST", "nrk" to "NRK", "rss" to "RSS", "podme" to "PODME")

// MARK: - UI-tilstand (ikke lagret)

object PodUi {
    /** Podkasten som er åpen (ligger over kildesiden), null = ingen. */
    var show by mutableStateOf<PodShow?>(null)
    var genre by mutableStateOf(0)
    /** Favorittene fra Skjold. null = ikke hentet ennå. */
    var favs by mutableStateOf<List<PodShow>?>(null)
}

/** Spiller en episode og viser svaret øverst i appen. */
private suspend fun AppModel.playPod(e: PodEpisode, show: PodShow?, restart: Boolean = false) {
    if (demo) { showNotice("Koble til en Skjold-enhet for å spille podkaster"); return }
    livePlayPodcast()
    Haptics.thump()
    showNotice(PodApi.play(activeHost, e, show, restart))
}

private suspend fun AppModel.togglePodFav(s: PodShow, on: Boolean) {
    val r = PodApi.setFav(activeHost, s, on)
    if (r == null) { showNotice("Fikk ikke lagret favoritten"); Haptics.warning(); return }
    PodUi.favs = r
    if (on) Haptics.success()
    showNotice(if (on) "Lagt til i Mine podkaster – vises også på Skjold Touch" else "Fjernet fra Mine podkaster")
}

// MARK: - Byggeklosser

/** Omslag: bildet fra podkasten, eller gradienten fra navnet mens det lastes (og når det mangler). */
@Composable
private fun PodImg(url: String, name: String, size: Dp, radius: Dp = 12.dp, modifier: Modifier = Modifier) {
    Box(modifier.size(size).clip(RoundedCornerShape(radius))) {
        ArtFill(art(name))
        val u = DeviceLink.coverURL(url)
        if (u.isNotEmpty()) AsyncImage(model = u, contentDescription = null, contentScale = ContentScale.Crop, modifier = Modifier.fillMaxSize())
    }
}

/** Fremdrift: 3 høy, gull på #2e2e30. */
@Composable
private fun PodBar(pos: Double, dur: Double, modifier: Modifier = Modifier) {
    if (pos <= 0 || dur <= 0) return
    Box(modifier.fillMaxWidth().height(3.dp).clip(RoundedCornerShape(2.dp)).background(SourceTok.line2)) {
        Box(Modifier.fillMaxWidth((pos / dur).toFloat().coerceIn(0f, 1f)).fillMaxHeight().background(SourceTok.goldDark))
    }
}

/** Overskrift 17/600 med grå undertekst, som H i web-appen. */
@Composable
private fun PodHead(t: String, sub: String? = null) {
    Row(verticalAlignment = Alignment.Bottom, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        T(t, sora(17f, W.Semibold), maxLines = 1)
        if (!sub.isNullOrEmpty()) T(sub, sora(12f, W.Regular, SourceTok.muted), Modifier.padding(bottom = 2.dp), maxLines = 1)
    }
}

@Composable
private fun PodNote(t: String, color: Color = SourceTok.muted) = T(t, sora(13f, W.Regular, color, 1.45f))

/** Flis for en podkast: omslag, tittel og forfatter. Trykk åpner podkasten. */
@Composable
private fun PodTile(s: PodShow, w: Dp, rank: Int? = null) {
    Column(Modifier.width(w).press { PodUi.show = s }, verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Box {
            PodImg(s.image, s.title, w)
            if (rank != null) {
                Box(
                    Modifier.padding(6.dp).widthIn(min = 22.dp).height(20.dp).clip(RoundedCornerShape(6.dp))
                        .background(SourceTok.bg.copy(alpha = 0.78f)).padding(horizontal = 5.dp),
                    contentAlignment = Alignment.Center,
                ) { T("$rank", mono(10f, SourceTok.ink)) }
            }
        }
        T(s.title, sora(13.5f, W.Semibold), maxLines = 1)
        T(s.author.ifEmpty { podSrcText[s.source] ?: "" }, sora(11.5f, W.Regular, SourceTok.muted), maxLines = 1)
    }
}

/** Rutenett av fliser (minst 132 brede), uten egen rulling. */
@Composable
private fun PodGrid(shows: List<PodShow>, ranked: Boolean = false) {
    BoxWithConstraints(Modifier.fillMaxWidth()) {
        val gap = 14.dp
        val cols = maxOf(2, ((maxWidth + gap) / (132.dp + gap)).toInt())
        val w = (maxWidth - gap * (cols - 1)) / cols
        Column(verticalArrangement = Arrangement.spacedBy(18.dp)) {
            shows.chunked(cols).forEachIndexed { r, row ->
                Row(horizontalArrangement = Arrangement.spacedBy(gap)) {
                    row.forEachIndexed { c, s -> PodTile(s, w, if (ranked) r * cols + c + 1 else null) }
                }
            }
        }
    }
}

/** Episoderad: omslag 52, tittel (grå når den er hørt), dato · varighet · status, fremdrift og «Fra start». */
@Composable
private fun PodEpRow(m: AppModel, e: PodEpisode, show: PodShow?) {
    val scope = rememberCoroutineScope()
    Row(
        Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(hex(0x121214)).padding(8.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        PodImg(e.image.ifEmpty { show?.image ?: "" }, e.show.ifEmpty { e.title }, 52.dp, 10.dp)
        Column(Modifier.weight(1f).press { scope.launch { m.playPod(e, show) } }, verticalArrangement = Arrangement.spacedBy(3.dp)) {
            T(e.title, sora(14f, W.Semibold, if (e.heard) SourceTok.muted else SourceTok.ink), maxLines = 1)
            val sub = listOf(
                if (show == null) e.show else "", e.date, if (e.duration > 0) podMins(e.duration) else "",
                if (e.heard) "Hørt" else if (e.pos > 0) "Fortsett" else "",
            ).filter { it.isNotEmpty() }.joinToString(" · ")
            if (sub.isNotEmpty()) T(sub, sora(12f, W.Regular, SourceTok.muted), maxLines = 1)
            PodBar(e.pos, e.duration)
        }
        if (e.pos > 0) {
            Box(
                Modifier.height(32.dp).clip(RoundedCornerShape(8.dp)).skBorder(SourceTok.line2, 8.dp)
                    .press(label = "Spill fra start") { scope.launch { m.playPod(e, show, restart = true) } }.padding(horizontal = 10.dp),
                contentAlignment = Alignment.Center,
            ) { T("Fra start", sora(12f, W.Regular, SourceTok.ink2)) }
        }
    }
}

// MARK: - Kildesiden (innebygd i SourceBody når n == «Podkaster»)

/**
 * Innholdet på kildesiden Podkaster, under søkefeltet: Fortsett, Nye episoder, Mine podkaster, Podme og topplisten
 * med sjangre. Med et søk vises bare treffene. I demomodus finnes det ingen Skjold å spørre, så da vises en forklaring.
 */
@Composable
fun PodcastBody(m: AppModel, q: String, inset: Dp = 20.dp) {
    if (m.demo) {
        PodNote("Podkaster hentes fra Skjold-enheten. Koble til en Skjold for å bla i podkaster og spille dem.")
        return
    }
    val host = m.activeHost
    var genres by remember { mutableStateOf(listOf<Pair<Int, String>>()) }
    var top by remember { mutableStateOf<List<PodShow>?>(null) }
    var nye by remember { mutableStateOf<List<PodEpisode>?>(null) }
    var cont by remember { mutableStateOf(listOf<PodProg>()) }
    var res by remember { mutableStateOf<List<PodShow>?>(null) }
    var err by remember { mutableStateOf("") }
    val favs = PodUi.favs ?: emptyList()
    val genre = PodUi.genre

    LaunchedEffect(host) {
        PodUi.favs = PodApi.favs(host) ?: emptyList()
        genres = PodApi.genres(host) ?: emptyList()
        cont = PodApi.resume(host) ?: emptyList()
    }
    // nye episoder fra favorittene, på nytt når favorittene endres
    LaunchedEffect(host, PodUi.favs?.joinToString(",") { it.id }) {
        if (PodUi.favs == null) return@LaunchedEffect
        nye = PodApi.newest(host) ?: emptyList()
    }
    LaunchedEffect(host, genre) {
        top = null
        val r = PodApi.top(host, genre)
        top = r ?: emptyList()
        err = if (r == null) "Fikk ikke hentet topplisten fra Skjold" else ""
    }
    LaunchedEffect(host, q) {
        res = null
        if (q.isEmpty()) return@LaunchedEffect
        delay(400)
        val r = PodApi.search(host, q)
        res = r ?: emptyList()
        err = if (r == null) "Fikk ikke søkt. Sjekk at Skjold er på nettet." else ""
    }

    if (err.isNotEmpty()) PodNote(err, C.danger)

    if (q.isNotEmpty()) {
        val r = res
        when {
            r == null -> PodNote("Søker …")
            r.isEmpty() -> PodNote("Fant ingen podkaster for «$q».")
            else -> Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                PodHead("Treff", if (r.size == 1) "1 podkast" else "${r.size} podkaster")
                PodGrid(r)
            }
        }
        return
    }

    if (cont.isNotEmpty()) {
        val scope = rememberCoroutineScope()
        Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
            PodHead("Fortsett")
            EdgeScroll(12.dp, inset) {
                for (p in cont) {
                    Column(Modifier.width(132.dp).press { scope.launch { m.playPod(p.episode(), null) } }, verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        PodImg(p.image, p.series.ifEmpty { p.title.ifEmpty { "Podkast" } }, 132.dp)
                        T(p.title.ifEmpty { "Episode" }, sora(13f, W.Semibold), maxLines = 1)
                        T(p.series, sora(11.5f, W.Regular, SourceTok.muted), maxLines = 1)
                        PodBar(p.pos, p.dur)
                    }
                }
            }
        }
    }

    val nyeList = nye ?: emptyList()
    if (nyeList.isNotEmpty()) {
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            PodHead("Nye episoder", "Fra podkastene dine")
            for (e in nyeList.take(8)) PodEpRow(m, e, null)
        }
    }

    val mine = favs.filter { it.source != "podme" }.reversed()
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        PodHead("Mine podkaster", if (mine.isNotEmpty()) "Vises også på Skjold Touch" else null)
        when {
            PodUi.favs == null -> PodNote("Henter …")
            mine.isEmpty() -> PodNote("Ingen podkaster ennå. Åpne en podkast og trykk «Følg».")
            else -> EdgeScroll(12.dp, inset) { for (s in mine) PodTile(s, 132.dp) }
        }
    }

    val podme = favs.filter { it.source == "podme" }.reversed()
    if (podme.isNotEmpty()) {
        Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
            PodHead("Podme", "Fra Podme-kontoen din")
            EdgeScroll(12.dp, inset) { for (s in podme) PodTile(s, 132.dp) }
        }
    }

    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        PodHead("Topplisten", "Mest lyttet i Norge akkurat nå")
        if (genres.isNotEmpty()) {
            EdgeScroll(6.dp, inset) {
                for ((id, name) in genres) {
                    val on = genre == id
                    Box(
                        Modifier.height(34.dp).clip(CircleShape).background(if (on) SourceTok.ink else Color.Transparent)
                            .skCapsuleBorder(if (on) SourceTok.ink else SourceTok.line2)
                            .press { Haptics.tick(); PodUi.genre = id }.padding(horizontal = 14.dp),
                        contentAlignment = Alignment.Center,
                    ) { T(name, sora(12.5f, W.Regular, if (on) SourceTok.bg else SourceTok.ink2), maxLines = 1) }
                }
            }
        }
        val t = top
        when {
            t == null -> PodNote("Henter topplisten …")
            t.isEmpty() -> PodNote("Ingen podkaster i denne sjangeren akkurat nå.")
            else -> PodGrid(t.take(60), ranked = true)
        }
    }
}

// MARK: - Podkastsiden (over kildesiden)

/** Én podkast: omslag, kilde og forfatter, tittel, beskrivelse, Spill nyeste, Følg og episodene. */
@Composable
fun PodShowPage(m: AppModel, s: PodShow, wide: Boolean = false) {
    BackHandler { PodUi.show = null }
    val host = m.activeHost
    val scope = rememberCoroutineScope()
    var d by remember(s.id) { mutableStateOf<PodShowDetail?>(null) }
    var err by remember(s.id) { mutableStateOf("") }
    var n by remember(s.id) { mutableStateOf(40) }
    var more by remember(s.id) { mutableStateOf(false) }
    var fresh by remember(s.id) { mutableStateOf(0) }
    LaunchedEffect(s.id, fresh) {
        if (m.demo) { err = "Koble til en Skjold-enhet for å se episodene."; return@LaunchedEffect }
        err = ""
        val r = PodApi.show(host, s.id, fresh = fresh > 0)
        if (r == null) err = "Fikk ikke hentet podkasten fra Skjold" else d = r
    }
    val det = d
    // det Skjold svarte, med det vi visste fra før der svaret mangler noe
    val h = det?.show?.let { x -> x.copy(title = x.title.ifEmpty { s.title }, image = x.image.ifEmpty { s.image }, author = x.author.ifEmpty { s.author }, src = x.src.ifEmpty { s.src }) } ?: s
    val fav = PodUi.favs?.any { it.id == s.id } ?: (det?.fav == true)
    val first = det?.episodes?.firstOrNull()

    Box(Modifier.fillMaxSize().background(SourceTok.bg)) {
        val topp = WindowInsets.statusBars.asPaddingValues().calculateTopPadding()
        val glow = art(h.title).base
        Box(
            Modifier.fillMaxWidth().height(460.dp + topp).drawBehind {
                drawRect(Brush.radialGradient(listOf(glow.copy(alpha = 0.6f), Color.Transparent), center = Offset(size.width * 0.3f, 0f), radius = (340.dp + topp).toPx()))
            },
        )
        Column(
            Modifier.fillMaxSize().windowInsetsPadding(WindowInsets.statusBars).verticalScroll(rememberScrollState()),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Column(
                Modifier.then(if (wide) Modifier.widthIn(max = 760.dp) else Modifier).fillMaxWidth()
                    .padding(start = 20.dp, end = 20.dp, top = 6.dp, bottom = if (wide) 130.dp else 240.dp),
                verticalArrangement = Arrangement.spacedBy(18.dp),
            ) {
                Box(
                    Modifier.size(46.dp).clip(CircleShape).background(SourceTok.glassBg).skCapsuleBorder(SourceTok.glassLine)
                        .press(label = "Tilbake") { PodUi.show = null },
                    contentAlignment = Alignment.Center,
                ) { SKIcon(SourceTok.back, 20.dp, 2.4f, SourceTok.ink) }
                Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                    PodImg(h.image, h.title, 220.dp, 18.dp,
                        Modifier.shadow(30.dp, RoundedCornerShape(18.dp), ambientColor = Color.Black.copy(alpha = 0.5f), spotColor = Color.Black.copy(alpha = 0.5f)))
                }
                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    val kicker = (podSrcText[h.source] ?: "PODKAST") + (if (h.author.isNotEmpty() && h.source != "nrk") " · " + h.author.uppercase() else "")
                    SourceKicker(kicker)
                    T(h.title, sora(28f, W.Semibold, lineHeight = 1.12f).copy(letterSpacing = (-0.5).sp), maxLines = 3)
                    val desc = det?.description.orEmpty()
                    if (desc.isNotEmpty()) {
                        T(desc, sora(13f, W.Regular, SourceTok.body, 1.5f), Modifier.press(label = if (more) "Vis mindre" else "Vis mer") { more = !more },
                            maxLines = if (more) Int.MAX_VALUE else 3)
                    }
                }
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    if (first != null) {
                        Row(
                            Modifier.height(46.dp).clip(CircleShape).background(SourceTok.ink).press { scope.launch { m.playPod(first, h) } }
                                .padding(start = 16.dp, end = 20.dp),
                            verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp),
                        ) {
                            SKIcon(SourceTok.play, 18.dp, color = SourceTok.bg, fill = true)
                            T("Spill nyeste", sora(14f, W.Semibold, SourceTok.bg), maxLines = 1)
                        }
                    }
                    if (!m.demo) {
                        Row(
                            Modifier.height(46.dp).clip(CircleShape).background(if (fav) SourceTok.selBg else Color.Transparent)
                                .skCapsuleBorder(if (fav) SourceTok.goldDark else SourceTok.line2)
                                .press(label = if (fav) "Slutt å følge" else "Følg") { scope.launch { m.togglePodFav(h, !fav) } }
                                .padding(horizontal = 16.dp),
                            verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp),
                        ) {
                            if (fav) SKIcon(SourceTok.heart, 18.dp, color = SourceTok.goldDark, fill = true)
                            SKIcon(SourceTok.heart, 18.dp, 1.9f, if (fav) SourceTok.goldDark else SourceTok.ink)
                            T(if (fav) "Følger" else "Følg", sora(14f, W.Regular, if (fav) SourceTok.gold else SourceTok.ink), maxLines = 1)
                        }
                    }
                }
                if (err.isNotEmpty()) PodNote(err, C.danger)
                if (det == null && err.isEmpty()) PodNote("Henter episoder …")
                if (det != null) {
                    if (det.episodes.isEmpty()) PodNote("Ingen episoder tilgjengelig akkurat nå.")
                    else {
                        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.Bottom) {
                            PodHead("Episoder", "${det.episodes.size}")
                            Spacer(Modifier.weight(1f))
                            T("Se etter nye", sora(12f, W.Regular, SourceTok.muted), Modifier.press { d = null; fresh += 1 })
                        }
                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            for (e in det.episodes.take(n)) PodEpRow(m, e, h)
                        }
                        if (det.episodes.size > n) {
                            Box(
                                Modifier.height(36.dp).clip(CircleShape).skCapsuleBorder(SourceTok.line2).press { n += 60 }.padding(horizontal = 14.dp),
                                contentAlignment = Alignment.Center,
                            ) { T("Vis flere episoder (${det.episodes.size - n})", sora(13f, W.Regular, SourceTok.ink), align = TextAlign.Center) }
                        }
                    }
                }
            }
        }
    }
}

