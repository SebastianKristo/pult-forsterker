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

    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge(
            statusBarStyle = SystemBarStyle.dark(AColor.TRANSPARENT),
            navigationBarStyle = SystemBarStyle.dark(AColor.TRANSPARENT),
        )
        super.onCreate(savedInstanceState)
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
    override fun newImageLoader(): ImageLoader =
        ImageLoader.Builder(this).components { add(SvgDecoder.Factory()) }.crossfade(true).build()
}
