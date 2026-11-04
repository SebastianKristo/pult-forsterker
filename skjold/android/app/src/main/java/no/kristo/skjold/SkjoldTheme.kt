package no.kristo.skjold

import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

/**
 * Design-tokens fra «Skjold App v4» med platform = android (objektet G i renderVals(), TABS og hyllene).
 * 1 CSS-px = 1 dp. Android har ikke glass: flater er heldekkende.
 */
object SkG {
    // fanelinje (andBarOn): 96 px høy, #161618 med kant #232326, indikator 64×32 r16
    val barBg = hex(0x161618)
    val barLine = hex(0x232326)
    val barIndicator = Color(240, 196, 106, (0.2f * 255).toInt())
    val barOn = hex(0xf0c46a)
    val barOff = hex(0xc9c9c4)
    val barLabel = hex(0xe4e4df)
    val barPadTop = 14.dp
    val barIndW = 64.dp
    val barIndH = 32.dp

    // minispiller (miniPhone): r16, marg 0 8, #1f1f22, skygge 0 2 8 rgba(0,0,0,.4)
    val miniBg = hex(0x1f1f22)
    val miniR = 16.dp
    val miniM = 8.dp
    val miniSub = hex(0xd0d0cb)
    val miniVolTrack = Color(242, 242, 238, (0.18f * 255).toInt())
    val miniVolIcon = hex(0xa9a9a3)

    // ark, menyer og felter
    val menuBg = hex(0x26262a)
    val menuR = 12.dp
    val fieldBg = hex(0x232326)
    val panelBg = Color(0, 0, 0, (0.3f * 255).toInt())
    val panelLine = Color(255, 255, 255, (0.08f * 255).toInt())
    val dimBg = Color(5, 5, 6, (0.88f * 255).toInt())
    val segLens = Color(240, 196, 106, (0.24f * 255).toInt())
    val segLine = Color(242, 242, 238, (0.4f * 255).toInt())

    // Hjem: toppknapper (søk + innstillinger) i en kapsel
    val pillBg = Color(40, 40, 42, (0.6f * 255).toInt())
    val pillLine = Color(255, 255, 255, (0.1f * 255).toInt())

    // hyller
    val shelfTitle = 17f
    val recentSize = 132.dp
    val recentR = 16.dp
    val sourceSize = 68.dp
    val favSize = 112.dp
    val favBg = hex(0x151517)
    val subText = hex(0xa9a9a3)

    // innstillingslister
    val rowLine = Color(255, 255, 255, (0.06f * 255).toInt())
    val listBg = hex(0x141415)
}
