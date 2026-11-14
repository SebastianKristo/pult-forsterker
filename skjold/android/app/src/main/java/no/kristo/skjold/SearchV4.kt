package no.kristo.skjold

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBars
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.text.BasicText
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
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
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/*
 * Søk (v4), som V4SearchPage.swift på iOS: #050506, «Søk i»-filter (ring 3 / opasitet .45), Spillelister, Låter,
 * Radio, «Spill noe til …» og treff fra Music Assistant og NRK. Søkefeltet ligger nederst og løftes over tastaturet.
 */

private val searchSrcs = listOf("YouTube Music", "Navidrome", "Plex", "Radio", "AirPlay")

/**
 * Søkesiden. Tegnes av skallet over alt annet (også dokken) når [SourceUi.search] er sann – gjør ingenting ellers.
 * Åpnes med `m.openSearch()` (eller `m.openSearch("M83")`).
 */
@Composable
fun SearchPage(m: AppModel) {
    if (!SourceUi.search) return
    val focus = LocalFocusManager.current
    val req = remember { FocusRequester() }
    val scope = rememberCoroutineScope()
    var hits by remember { mutableStateOf(mapOf<String, List<Track>>()) }
    var ext by remember { mutableStateOf(listOf<ExtHit>()) }
    var askMsg by remember { mutableStateOf("") }
    val q = SourceUi.sq.trim()
    val sSrc = SourceUi.sSrc
    fun ok(s: String) = sSrc == null || searchSrcs[sSrc] == s
    val close = { focus.clearFocus(); SourceUi.search = false; SourceUi.sq = "" }

    BackHandler { close() }
    LaunchedEffect(Unit) { runCatching { req.requestFocus() } }
    LaunchedEffect(q) { if (ok("Radio")) m.setQ(q) }
    LaunchedEffect(q + "|" + (sSrc ?: -1)) {
        if (q.isEmpty()) { hits = emptyMap(); ext = emptyList(); return@LaunchedEffect }
        delay(350)
        if (!m.demo) ext = ExtSearch.load(m.activeHost, q)
        val out = HashMap<String, List<Track>>()
        for (lib in listOf("nd", "plex", "ytm")) {
            if (!ok(SourceLib.names[lib] ?: "")) continue
            out[lib] = if (m.demo) SK.lt.filter { (it.t + " " + it.artist + " " + it.album).contains(q, ignoreCase = true) }.take(if (lib == "ytm") 6 else 3)
            else m.searchLib(lib, q)
        }
        hits = out
    }

    // Resultater
    val pls: List<SourcePlaylist> = run {
        val all = listOf("ytm", "nd", "plex").filter { ok(SourceLib.names[it] ?: "") }.flatMap { SourceLib.playlists(m, it) }
        if (q.isEmpty()) (if (sSrc == null) emptyList() else all)
        else all.filter { it.name.contains(q, ignoreCase = true) || it.owner.contains(q, ignoreCase = true) }
    }
    val trs: List<Pair<String, Track>> = if (q.isEmpty()) emptyList() else
        listOf("ytm", "nd", "plex").filter { ok(SourceLib.names[it] ?: "") }.flatMap { lib -> (hits[lib] ?: emptyList()).map { lib to it } }
    val rs: List<Station> = run {
        if (!ok("Radio")) emptyList()
        else if (q.isEmpty()) (if (sSrc == 3) m.radio else emptyList())
        else {
            val favs = m.radio.filter { it.name.contains(q, ignoreCase = true) || it.genre.contains(q, ignoreCase = true) }
            val more = (m.rRes ?: emptyList()).map { Station(it.name, it.genre, it.url) }.filter { r -> favs.none { it.name == r.name } }
            favs + more
        }
    }

    Box(Modifier.fillMaxSize().background(SourceTok.searchBg)) {
        Column(Modifier.fillMaxSize().windowInsetsPadding(WindowInsets.statusBars).imePadding()) {
            Column(
                Modifier.weight(1f).fillMaxWidth().verticalScroll(rememberScrollState())
                    .padding(start = 20.dp, end = 20.dp, top = 6.dp, bottom = 120.dp),
                verticalArrangement = Arrangement.spacedBy(22.dp),
            ) {
                T("Søk", sora(32f, W.Semibold).copy(letterSpacing = (-0.64).sp), maxLines = 1)
                if (q.isEmpty()) {
                    val b = SpanStyle(fontWeight = FontWeight.SemiBold, color = SourceTok.ink)
                    BasicText(
                        buildAnnotatedString {
                            append("Søk etter ")
                            withStyle(b) { append("låter, artister, album, spillelister") }
                            append(" eller ")
                            withStyle(b) { append("radiokanaler") }
                            append(" i alle tjenestene dine.")
                        },
                        style = sora(17f, W.Regular, SourceTok.ink2, 1.45f),
                    )
                }
                // «Søk i»
                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                        T("Søk i", sora(17f, W.Semibold), Modifier.weight(1f))
                        T(sSrc?.let { searchSrcs[it] } ?: "Alle tjenester", sora(13f, W.Regular, SourceTok.muted))
                    }
                    EdgeScroll(12.dp) {
                        searchSrcs.forEachIndexed { i, s ->
                            Column(
                                Modifier.width(66.dp).padding(vertical = 2.dp).alpha(if (sSrc == null || sSrc == i) 1f else 0.45f)
                                    .press { Haptics.tick(); SourceUi.sSrc = if (sSrc == i) null else i },
                                horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(7.dp),
                            ) {
                                SourceIcon(s, 62.dp, if (sSrc == i) 3.dp else 0.dp)
                                T(if (s == "YouTube Music") "YT Music" else s, sora(11f, W.Regular, SourceTok.ink2), maxLines = 1)
                            }
                        }
                    }
                }
                if (pls.isNotEmpty()) {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        SourceKicker("SPILLELISTER")
                        for (p in pls) {
                            Row(
                                Modifier.fillMaxWidth().press { SourceUi.search = false; m.openSourcePlaylist(p) }.padding(vertical = 4.dp),
                                verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp),
                            ) {
                                SourceMosaic(p.keys, 52.dp, 9.dp)
                                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                                    T(p.name, sora(15f, W.Semibold), maxLines = 1)
                                    T(p.src + " · ${p.count} låter", sora(12f, W.Regular, SourceTok.muted), maxLines = 1)
                                }
                                SKIcon(SourceTok.chevRight, 16.dp, 2f, SourceTok.chev)
                            }
                        }
                    }
                }
                if (trs.isNotEmpty()) {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        SourceKicker("LÅTER")
                        trs.forEachIndexed { i, (lib, t) ->
                            Row(Modifier.fillMaxWidth().padding(vertical = 4.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                                Row(
                                    Modifier.weight(1f).press {
                                        val list = trs.filter { it.first == lib }.map { it.second }
                                        val idx = list.indexOf(trs[i].second).coerceAtLeast(0)
                                        m.lib = lib
                                        m.playLib(list, idx, keepOpen = true)
                                    },
                                    verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp),
                                ) {
                                    SourceCover(t.album, 52.dp, 9.dp)
                                    Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                                        T(t.t, sora(15f, W.Semibold), maxLines = 1)
                                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                            val name = SourceLib.names[lib] ?: ""
                                            SourceIcon(name, 14.dp)
                                            T(t.artist + " · " + name, sora(12f, W.Regular, SourceTok.muted), maxLines = 1)
                                        }
                                    }
                                }
                                SourceMoreButton { SourceUi.moreTrack = t; SourceUi.more = true }
                            }
                        }
                    }
                }
                if (rs.isNotEmpty()) {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        SourceKicker("RADIO")
                        for (st in rs) {
                            Row(
                                Modifier.fillMaxWidth().press { m.playRadio(st) }.padding(vertical = 4.dp),
                                verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp),
                            ) {
                                SourceCover(st.name, 52.dp, 9.dp)
                                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                                    T(st.name, sora(15f, W.Semibold), maxLines = 1)
                                    T(st.genre, sora(12f, W.Regular, SourceTok.muted), maxLines = 1)
                                }
                                T("DIREKTE", mono(10f, SourceTok.gold, 0.1f))
                            }
                        }
                    }
                }
                if (q.isNotEmpty() && !m.demo) {
                    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Row(
                            Modifier.fillMaxWidth().press {
                                val text = q
                                askMsg = "Finner noe …"
                                scope.launch { askMsg = ExtSearch.ask(m.activeHost, text) }
                            }.padding(vertical = 6.dp),
                            verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp),
                        ) {
                            SKIcon(SourceTok.search, 18.dp, 2.2f, SourceTok.gold)
                            T("Spill noe til «$q»", sora(15f, W.Semibold), Modifier.weight(1f), maxLines = 1)
                        }
                        if (askMsg.isNotEmpty()) T(askMsg, sora(12f, W.Regular, SourceTok.muted))
                    }
                }
                if (ext.isNotEmpty()) ExtHitList(m, ext)
                if (q.isNotEmpty() && pls.isEmpty() && trs.isEmpty() && rs.isEmpty() && ext.isEmpty() && !m.rBusy) {
                    T("Fant ingenting for «$q».", sora(14f, W.Regular, SourceTok.muted))
                }
            }
            // Søkefelt nederst (54, glass på iOS) + lukk
            Row(
                Modifier.fillMaxWidth().windowInsetsPadding(WindowInsets.navigationBars).padding(start = 12.dp, end = 12.dp, bottom = 12.dp),
                verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                Row(
                    Modifier.weight(1f).height(54.dp).clip(CircleShape).background(SkG.fieldBg).skCapsuleBorder(SourceTok.glassLine).padding(horizontal = 18.dp),
                    verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    SKIcon(SourceTok.search, 20.dp, 2.2f, SourceTok.ink)
                    BasicTextField(
                        value = SourceUi.sq, onValueChange = { SourceUi.sq = it }, singleLine = true,
                        textStyle = sora(17f, W.Regular, SourceTok.ink), cursorBrush = SolidColor(SourceTok.goldDark),
                        keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.None, autoCorrectEnabled = false, imeAction = ImeAction.Search),
                        keyboardActions = KeyboardActions(onSearch = { focus.clearFocus() }),
                        modifier = Modifier.weight(1f).focusRequester(req),
                        decorationBox = { inner ->
                            Box(contentAlignment = Alignment.CenterStart) {
                                if (SourceUi.sq.isEmpty()) T("Søk", sora(17f, W.Regular, SourceTok.muted), maxLines = 1)
                                inner()
                            }
                        },
                    )
                }
                Box(
                    Modifier.size(54.dp).clip(CircleShape).background(SkG.fieldBg).skCapsuleBorder(SourceTok.glassLine).press(label = "Lukk søk") { close() },
                    contentAlignment = Alignment.Center,
                ) { SKIcon(SourceTok.close, 20.dp, 2.4f, SourceTok.ink) }
            }
        }
    }
    SourceMoreSheet(m)
}
