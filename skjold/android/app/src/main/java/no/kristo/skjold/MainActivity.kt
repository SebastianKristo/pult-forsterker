package no.kristo.skjold

import android.graphics.Color as AColor
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.Density
import coil.ImageLoader
import coil.ImageLoaderFactory
import coil.decode.SvgDecoder

class MainActivity : ComponentActivity() {
    private val model: AppModel by viewModels()

    @Deprecated("Deprecated in Java")
    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 11) CallDuck.start(applicationContext)   // tilgang til telefonstatus gitt i Innstillinger
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge(
            statusBarStyle = SystemBarStyle.dark(AColor.TRANSPARENT),
            navigationBarStyle = SystemBarStyle.dark(AColor.TRANSPARENT),
        )
        super.onCreate(savedInstanceState)
        Shortcuts.refresh(applicationContext)   // rutine-snarveier på app-ikonet
        CallDuck.start(applicationContext)        // «Senk musikken når telefonen ringer» (bare hvis slått på og tillatt)
        // Varsler trengs for «Spiller nå» i hurtiginnstillingene og på låseskjermen (Android 13+).
        if (android.os.Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS) != android.content.pm.PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(android.Manifest.permission.POST_NOTIFICATIONS), 7)
        }
        setContent {
            // iOS uses fixed-size fonts (no Dynamic Type): keep the design's sizes regardless of the system font scale.
            val d = LocalDensity.current
            CompositionLocalProvider(LocalDensity provides Density(d.density, 1f)) {
                ContentView(model)
            }
        }
    }
}

/** Application: Coil with SVG support for the NRK logos in assets/nrk. */
class SkjoldApp : android.app.Application(), ImageLoaderFactory {
    override fun onCreate() {
        super.onCreate()
        Store.init(this)
        WidgetStore.schedule(this)   // widgets oppdateres hvert 15. min også når appen er lukket
        try { SkjoldRoutes.init(this) } catch (_: Exception) { }   // Skjold-enhetene i systemets «Medieutgang»
        try { WearBridge.init(this) } catch (_: Exception) { }   // Wear OS-klokka: rom og kall via telefonen
    }

    override fun newImageLoader(): ImageLoader =
        ImageLoader.Builder(this).components { add(SvgDecoder.Factory()) }.crossfade(true).build()
}
