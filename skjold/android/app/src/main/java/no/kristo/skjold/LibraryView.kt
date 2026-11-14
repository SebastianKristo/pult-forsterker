package no.kristo.skjold

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.unit.dp

/*
 * Bibliotekene (YouTube Music / Navidrome / Plex) som kildeside (v4), innebygd i fanesiden når `m.sub == "lib"`.
 * Innholdet er det samme som SourcePage (V4SourcePage.swift): søk, spillelister (mosaikk) og låter. En åpen
 * spilleliste (SourceUi.pl) vises her i stedet for kildesiden. Det nye skallet bør heller bruke SourceOverlays.
 */
@Composable
fun LibraryView(m: AppModel) {
    val label = SourceLib.names[m.lib] ?: "YouTube Music"
    // «Søk etter artist» fra spilleren legger artisten i m.lq2: bruk den som søk på kildesiden
    LaunchedEffect(m.lq2) { if (m.lq2.isNotBlank()) { SourceUi.srcQ = m.lq2.trim(); m.lq2 = "" } }
    val pl = SourceUi.pl
    Column(verticalArrangement = Arrangement.spacedBy(if (pl != null) 18.dp else 22.dp)) {
        if (pl != null) PlaylistBody(m, pl)
        else SourceBody(m, label) { m.sub = ""; SourceUi.srcQ = "" }
    }
    SourceMoreSheet(m)
}
