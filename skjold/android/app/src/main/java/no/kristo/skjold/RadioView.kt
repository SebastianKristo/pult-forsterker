package no.kristo.skjold

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.runtime.Composable
import androidx.compose.ui.unit.dp

/*
 * Radio som kildeside (v4, V4SourcePage.swift med n = «Radio»), innebygd i fanesiden når `m.sub == "radio"`:
 * søkefelt «Søk etter kanal», KANALER (favorittene) og treff fra Radio Browser. «⋯» legger til/fjerner favoritt.
 */
@Composable
fun RadioView(m: AppModel) {
    val pl = SourceUi.pl
    Column(verticalArrangement = Arrangement.spacedBy(if (pl != null) 18.dp else 22.dp)) {
        if (pl != null) PlaylistBody(m, pl)
        else SourceBody(m, "Radio") { m.sub = ""; SourceUi.srcQ = "" }
    }
    SourceMoreSheet(m)
}
