package no.kristo.skjold

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import com.google.mlkit.vision.barcode.BarcodeScannerOptions
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.common.InputImage
import kotlinx.coroutines.delay
import java.util.concurrent.Executors
import kotlin.math.sin

/** 02–08: OPPSETT · n AV 4 (find amplifier, QR, Wi-Fi, room, speaker test, software). */
@Composable
fun OnboardingView(m: AppModel) {
    LaunchedEffect(Unit) { m.browser.start() }
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(start = 20.dp, end = 20.dp, top = 8.dp, bottom = 18.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Row(Modifier.fillMaxWidth().heightIn(min = 28.dp), verticalAlignment = Alignment.CenterVertically) {
            SKMonoLabel("OPPSETT · ${m.obStep + 1} AV 4")
            Spacer(Modifier.weight(1f))
            if (m.ob > 0 || m.scan) SKLinkButton("Tilbake", modifier = Modifier.padding(vertical = 6.dp)) { m.obBack() }
        }
        SKProgressSteps(m.obStep)
        T(if (m.scan) "Skann QR-koden" else AppModel.obText[m.ob].first, sora(28f, W.Semibold, lineHeight = 1.15f))
        T(if (m.scan) "Hold kameraet mot skjermen på forsterkeren." else AppModel.obText[m.ob].second, sora(13f, W.Regular, C.body, 1.5f))
        if (m.scan) ScanStep(m)
        else when (m.ob) {
            0 -> FindStep(m)
            1 -> WifiStep(m)
            2 -> RoomStep(m)
            3 -> TestStep(m)
            else -> SoftwareStep(m)
        }
        if (m.ob != 0 && !m.scan) {
            VSpace(8.dp)
            val label = if (m.ob == 1) "Koble til" else if (m.ob == 4) (if (m.obUpd >= 100) "Ferdig" else "Oppdaterer …") else "Neste"
            SKButton(label, if (m.okOb) SKButtonKind.PRIMARY else SKButtonKind.DISABLED) { m.obNext() }
        }
    }
}

// MARK: - 02 Finn forsterker

/** Model from the TXT record (product=s1|node|core), else guessed from the name. */
fun foundType(d: FoundDevice): String {
    if (d.product in listOf("s1", "node", "core")) return d.product
    if (d.name.contains("core", ignoreCase = true)) return "core"
    return if (d.name.contains("node", ignoreCase = true)) "node" else "s1"
}

@Composable
private fun FindStep(m: AppModel) {
    val ctx = LocalContext.current
    val hasCam = remember { ctx.packageManager.hasSystemFeature(PackageManager.FEATURE_CAMERA_ANY) }
    val perm = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { ok -> if (ok) m.startScan(false) else m.cameraDenied() }
    val devices = m.browser.devices
    if (devices.isEmpty()) {
        // nothing on the network: the design's two cards, which continue in demo mode
        DeviceCard("Skjold S1", "Demo · ingen enhet funnet ennå", SK.dev("s1").icon, true, "Sett opp") { m.pickDevice("s1") }
        DeviceCard("Skjold Node", "Demo · ingen enhet funnet ennå", SK.dev("node").icon, false, "Sett opp") { m.pickDevice("node") }
    } else {
        devices.forEachIndexed { i, d ->
            val type = foundType(d)
            val set = m.known.any { it.host == d.host }
            DeviceCard(SK.dev(type).n, d.name + " · " + (d.host?.let { it + if (set) " · lagt til" else "" } ?: "kobler til …"),
                SK.dev(type).icon, i == 0, if (set) "Åpne" else "Koble til") {
                val h = d.host
                if (h != null) m.pickFound(h, type) else Haptics.warning()
            }
        }
    }
    var tick by remember { mutableLongStateOf(0L) }
    LaunchedEffect(Unit) { while (true) { delay(420); tick++ } }
    Row(Modifier.padding(vertical = 4.dp, horizontal = 2.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Dot(if (tick % 2 == 0L) C.accent else C.off, 8.dp)
        T("Leter etter flere …", sora(12f, W.Regular, C.muted))
    }
    if (m.obErr.isNotEmpty()) T(m.obErr, sora(12f, W.Regular, C.danger, 1.45f))
    SKButton("Skann QR-kode på skjermen", SKButtonKind.SECONDARY, 50.dp, 14f) {
        when {
            !hasCam -> m.startScan(true)
            ContextCompat.checkSelfPermission(ctx, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED -> m.startScan(false)
            else -> perm.launch(Manifest.permission.CAMERA)
        }
    }
    // Hopp over oppsettet: rett inn i appen (Skjold-enheter kan legges til senere under Rom → Legg til enhet)
    Box(Modifier.fillMaxWidth().padding(vertical = 6.dp), contentAlignment = Alignment.Center) {
        SKLinkButton("Hopp over – legg til enhet senere") { m.skipSetup() }
    }
}

@Composable
private fun DeviceCard(name: String, meta: String, icon: String, selected: Boolean, label: String, action: () -> Unit) {
    Row(
        Modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp)).background(if (selected) C.selBg else C.card)
            .skBorder(if (selected) C.accent else C.line2, 14.dp).press(onClick = action).padding(14.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        SKIcon(icon, 40.dp, 1.1f, if (selected) C.ink else C.ink2)
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            T(name, sora(14f))
            T(meta, mono(10f))
        }
        T(label, sora(12f, W.Regular, C.accent2))
    }
}

// MARK: - 03 QR

@Composable
private fun ScanStep(m: AppModel) {
    Box(Modifier.fillMaxWidth().heightIn(min = 360.dp).clip(RoundedCornerShape(14.dp)).background(hex(0x151517)), contentAlignment = Alignment.Center) {
        if (m.camOK) QRScanner(Modifier.matchParentSize()) { m.qrFound(it) }
        Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(16.dp)) {
            var tick by remember { mutableLongStateOf(0L) }
            LaunchedEffect(Unit) { while (true) { delay(140); tick++ } }
            Canvas(Modifier.size(190.dp)) {
                val k = density
                val corner = Path().apply {
                    val i = 1.5f * k
                    moveTo(i, 34 * k); lineTo(i, 14 * k)
                    cubicTo(i, 14 * k + 2f / 3f * (i - 14 * k), 14 * k + 2f / 3f * (i - 14 * k), i, 14 * k, i)
                    lineTo(34 * k, i)
                }
                for (r in 0 until 4) rotate(r * 90f, Offset(size.width / 2, size.height / 2)) { drawPath(corner, C.accent, style = Stroke(3 * k)) }
                // same motion as the design: 12 + (sin(t·0.35)·0.5 + 0.5)·160, t in 140 ms ticks
                val y = 12 + (sin(tick * 0.35) * 0.5 + 0.5) * 160
                drawRect(C.accent.copy(alpha = 0.35f), Offset(12 * k, (y.toFloat() - 3) * k), Size(166 * k, 8 * k))
                drawRect(C.accent, Offset(12 * k, y.toFloat() * k), Size(166 * k, 2 * k))
            }
            T(if (m.scanFound) "Fant Skjold-Oppsett-0001 …" else "Leter etter QR-kode …", sora(13f, W.Regular, C.ink2))
        }
    }
}

/** Camera feed for the QR step: CameraX preview + ML Kit barcode scanning (VisionKit DataScanner on iOS). */
@androidx.annotation.OptIn(markerClass = [androidx.camera.core.ExperimentalGetImage::class])
@Composable
fun QRScanner(modifier: Modifier, onFound: (String) -> Unit) {
    val ctx = LocalContext.current
    val owner = LocalLifecycleOwner.current
    val exec = remember { Executors.newSingleThreadExecutor() }
    val scanner = remember { BarcodeScanning.getClient(BarcodeScannerOptions.Builder().setBarcodeFormats(Barcode.FORMAT_QR_CODE).build()) }
    val done = remember { booleanArrayOf(false) }
    DisposableEffect(Unit) {
        onDispose {
            try { ProcessCameraProvider.getInstance(ctx).get().unbindAll() } catch (_: Exception) {}
            scanner.close(); exec.shutdown()
        }
    }
    AndroidView(modifier = modifier, factory = { c ->
        val view = PreviewView(c).apply { scaleType = PreviewView.ScaleType.FILL_CENTER }
        val future = ProcessCameraProvider.getInstance(c)
        future.addListener({
            val provider = future.get()
            val preview = Preview.Builder().build().also { it.setSurfaceProvider(view.surfaceProvider) }
            val analysis = ImageAnalysis.Builder().setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST).build()
            analysis.setAnalyzer(exec) { proxy ->
                val media = proxy.image
                if (media == null || done[0]) { proxy.close(); return@setAnalyzer }
                val img = InputImage.fromMediaImage(media, proxy.imageInfo.rotationDegrees)
                scanner.process(img)
                    .addOnSuccessListener { codes ->
                        val s = codes.firstOrNull()?.rawValue
                        if (s != null && !done[0]) { done[0] = true; ContextCompat.getMainExecutor(c).execute { onFound(s) } }
                    }
                    .addOnCompleteListener { proxy.close() }
            }
            try {
                provider.unbindAll()
                provider.bindToLifecycle(owner, CameraSelector.DEFAULT_BACK_CAMERA, preview, analysis)
            } catch (_: Exception) {}
        }, ContextCompat.getMainExecutor(c))
        view
    })
}

// MARK: - 04/05 Wi-Fi

@Composable
private fun WifiStep(m: AppModel) {
    SKCard {
        m.nets.forEachIndexed { i, ssid ->
            val on = !m.netManual && m.net == i
            WifiRow(ssid, if (on) "✓" else "", if (on) C.selBg else Color.Transparent, if (i > 0) C.line else Color.Transparent, C.ink) { m.net = i; m.netManual = false }
        }
        WifiRow("Annet nettverk …", if (m.netManual) "✓" else "", if (m.netManual) C.selBg else Color.Transparent, C.line, C.ink2) { m.netManual = true }
    }
    if (m.netManual) {
        T("Skriv inn navnet hvis nettverket er skjult eller ikke dukker opp. Forsterkeren støtter 2,4 GHz.", sora(12f, W.Regular, C.muted, 1.45f))
        SKField("Nettverksnavn (SSID)", m.ssid, { m.ssid = it }, plainInput = true)
        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            listOf("WPA2", "WPA3", "Ingen").forEachIndexed { i, label ->
                val s = SelStyle.of(m.sec == i)
                Box(Modifier.weight(1f).height(38.dp).clip(CircleShape).background(s.bg).skCapsuleBorder(s.bd).press { m.sec = i }, contentAlignment = Alignment.Center) {
                    T(label, sora(13f, W.Regular, s.fg), maxLines = 1)
                }
            }
        }
    }
    if (m.needPw) SKField("Passord", m.pw, { m.pw = it }, secure = true)
    if (m.wifiBusy) T("Henter nettverk fra forsterkeren …", sora(12f, W.Regular, C.muted))
    if (m.obErr.isNotEmpty()) T(m.obErr, sora(12f, W.Regular, if (m.obErr.startsWith("Kobler")) C.muted else C.danger, 1.45f))
}

@Composable
private fun WifiRow(title: String, mark: String, bg: Color, line: Color, fg: Color, action: () -> Unit) {
    Row(
        Modifier.fillMaxWidth().heightIn(min = 50.dp).background(bg).topLine(line).press(onClick = action).padding(horizontal = 14.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        T(title, sora(14f, W.Regular, fg), Modifier.weight(1f))
        T(mark, sora(12f, W.Regular, C.accent2))
    }
}

// MARK: - 06 Rom

@Composable
private fun RoomStep(m: AppModel) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        AppModel.roomList.chunked(2).forEach { pair ->
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                pair.forEach { label ->
                    val on = !m.roomCustom && m.room == label
                    val s = SelStyle.of(on)
                    Row(
                        Modifier.weight(1f).height(50.dp).clip(RoundedCornerShape(12.dp)).background(s.bg).skBorder(s.bd, 12.dp)
                            .press { m.room = label; m.roomCustom = false }.padding(horizontal = 14.dp),
                        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        T(label, sora(14f, W.Regular, s.fg), Modifier.weight(1f), maxLines = 1)
                        T(if (on) "✓" else "", sora(12f, W.Regular, C.accent2))
                    }
                }
            }
        }
    }
    Row(
        Modifier.fillMaxWidth().height(50.dp).clip(RoundedCornerShape(12.dp)).background(if (m.roomCustom) C.selBg else Color.Transparent)
            .skBorder(if (m.roomCustom) C.accent else C.off, 12.dp, dash = listOf(4f, 3f))
            .press {
                if (!m.roomCustom) m.room = if (AppModel.roomList.contains(m.room)) "" else m.room
                m.roomCustom = true
            }.padding(horizontal = 14.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        SKIcon(Icons.plus, 16.dp, 2f, if (m.roomCustom) C.accent2 else C.ink2)
        T("Skriv eget navn", sora(14f, W.Regular, if (m.roomCustom) C.accent2 else C.ink2))
    }
    if (m.roomCustom) {
        SKField("For eksempel Hytta eller Runes rom", m.room, { m.room = it }, border = C.accent, maxLength = 20)
        T("Maks 20 tegn. Kan endres senere under Innstillinger.", sora(12f, W.Regular, C.muted))
    }
}

// MARK: - 07 Test høyttalere

@Composable
private fun TestStep(m: AppModel) {
    SKLinkButton("Hopp over høyttalertest") { m.goOb(4) }
    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        listOf("L" to "Venstre", "R" to "Høyre").forEach { (k, label) ->
            val done = m.tested.contains(k)
            val s = SelStyle.of(done)
            Column(
                Modifier.weight(1f).height(150.dp).clip(RoundedCornerShape(14.dp)).background(s.bg).skBorder(s.bd, 14.dp).press { m.testSide(k) },
                horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(8.dp, Alignment.CenterVertically),
            ) {
                T(k, sora(42f, W.Light, C.ink))
                T(if (done) "Spilt av" else label, sora(12f, W.Regular, s.fg))
            }
        }
    }
}

// MARK: - 08 Programvare

@Composable
private fun SoftwareStep(m: AppModel) {
    val text = if (!m.live) {
        if (m.obUpd >= 100) "1.4.2 installert" else "1.4.1 → 1.4.2 · ${m.obUpd} %"
    } else {
        val cur = m.dev?.version ?: "–"
        val rel = m.upd.latest
        when {
            m.obUpd < 100 || m.checking -> "$cur · ser etter oppdatering · ${minOf(m.obUpd, 99)} %"
            rel != null -> cur + " → " + GitHubReleases.version(rel.tag) + " · installeres fra forsterkeren"
            else -> "$cur installert"
        }
    }
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Box(Modifier.fillMaxWidth().height(6.dp).clip(RoundedCornerShape(3.dp)).background(C.line)) {
            Box(Modifier.fillMaxWidth(m.obUpd / 100f).height(6.dp).background(C.accent))
        }
        T(text, mono(12f))
    }
}
