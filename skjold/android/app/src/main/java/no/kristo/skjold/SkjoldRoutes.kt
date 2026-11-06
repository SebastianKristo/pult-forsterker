package no.kristo.skjold

import android.content.Context
import android.content.IntentFilter
import android.media.AudioManager
import android.os.Bundle
import androidx.mediarouter.app.SystemOutputSwitcherDialogController
import androidx.mediarouter.media.MediaRouteDescriptor
import androidx.mediarouter.media.MediaRouteDiscoveryRequest
import androidx.mediarouter.media.MediaRouteProvider
import androidx.mediarouter.media.MediaRouteProviderDescriptor
import androidx.mediarouter.media.MediaRouteProviderService
import androidx.mediarouter.media.MediaRouteSelector
import androidx.mediarouter.media.MediaRouter
import androidx.mediarouter.media.MediaRouterParams
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.launch
import kotlinx.serialization.builtins.ListSerializer

/**
 * Skjold-enhetene som medieruter («Medieutgang» / output switcher).
 *
 * Plattformbegrensninger (viktig):
 * - Systemets output switcher (Android 11+, «Medieutgang» i mediekontrollen) viser tredjeparts ruter bare for appens
 *   EGEN medieøkt, og bare når appen har en MediaRoute2ProviderService (androidx pakker MediaRouteProviderService inn
 *   som MediaRoute2ProviderService når intent-filteret android.media.MediaRoute2ProviderService er med i manifestet)
 *   og MediaRouterParams.setOutputSwitcherEnabled(true) + MediaTransferReceiver. Det fungerer fra Android 11 (R) og
 *   er mest pålitelig fra Android 14.
 * - Samsung One UI har sitt eget «Mediautgang»-panel (Smart View / lydutgang) som i praksis viser Bluetooth, telefonen
 *   og Samsung-/Chromecast-enheter. Tredjeparts MediaRoute2-ruter vises der ikke på alle One UI-versjoner. Derfor finnes
 *   «Spill på» inne i appen som reserve (showOutputSwitcher → faller tilbake til appens romliste).
 * - Ruter fra andre apper (f.eks. Spotify) kan aldri sendes hit: rutene gjelder bare Skjold-appens egen økt.
 */
object SkjoldRoutes {
    const val CATEGORY = "no.kristo.skjold.CATEGORY_SKJOLD"
    private const val EXTRA_HOST = "no.kristo.skjold.HOST"

    data class Found(val host: String, val name: String)

    /** Enheter funnet av ruteleverandøren (NSD), delt med medibiblioteket. */
    @Volatile var found: List<Found> = emptyList()

    /** Enhet valgt fra systemets utgangsvelger eller biblioteket. AppModel følger med og bytter aktivt rom. */
    val selected = MutableStateFlow<String?>(null)

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)

    val selector: MediaRouteSelector = MediaRouteSelector.Builder().addControlCategory(CATEGORY).build()

    /** Kalles fra MainActivity: slå på systemets output switcher for appens økt og overføring tilbake til telefonen. */
    fun init(ctx: Context) {
        val router = MediaRouter.getInstance(ctx)
        router.setRouterParams(MediaRouterParams.Builder().setOutputSwitcherEnabled(true).setTransferToLocalEnabled(true).build())
        router.addCallback(selector, object : MediaRouter.Callback() {
            override fun onRouteSelected(router: MediaRouter, route: MediaRouter.RouteInfo, reason: Int) {
                route.extras?.getString(EXTRA_HOST)?.let { select(ctx, it) }
            }
        }, MediaRouter.CALLBACK_FLAG_REQUEST_DISCOVERY)
    }

    /** Bytt aktiv Skjold: widgets/mediesesjon og appen følger etter. */
    fun select(ctx: Context, host: String) {
        Store.init(ctx)
        Store.setString("skjold-host", host)
        WidgetStore.setHost(ctx, host)
        selected.value = host
        scope.launch { WidgetStore.poll(ctx) }
    }

    /** «Spill på»: systemets utgangsvelger der den finnes (Android 11+, også Samsung), ellers false → appens romliste. */
    fun showOutputSwitcher(ctx: Context): Boolean =
        try { SystemOutputSwitcherDialogController.showDialog(ctx) } catch (_: Exception) { false }

    internal fun descriptor(f: Found, active: Boolean, volume: Int): MediaRouteDescriptor =
        MediaRouteDescriptor.Builder("skjold:" + f.host, f.name)
            .setDescription("Skjold")
            .addControlFilter(IntentFilter().apply { addCategory(CATEGORY) })
            .setPlaybackType(MediaRouter.RouteInfo.PLAYBACK_TYPE_REMOTE)
            .setPlaybackStream(AudioManager.STREAM_MUSIC)
            .setDeviceType(MediaRouter.RouteInfo.DEVICE_TYPE_SPEAKER)
            .setVolumeHandling(MediaRouter.RouteInfo.PLAYBACK_VOLUME_VARIABLE)
            .setVolumeMax(100)
            .setVolume(if (active) volume else 0)
            .setConnectionState(if (active) MediaRouter.RouteInfo.CONNECTION_STATE_CONNECTED else MediaRouter.RouteInfo.CONNECTION_STATE_DISCONNECTED)
            .setExtras(Bundle().apply { putString(EXTRA_HOST, f.host) })
            .setEnabled(true)
            .build()
}

/** Systemtjenesten som publiserer rutene (MediaRouteProviderService + MediaRoute2ProviderService via androidx). */
class SkjoldRouteProviderService : MediaRouteProviderService() {
    override fun onCreateMediaRouteProvider(): MediaRouteProvider = SkjoldRouteProvider(this)
}

class SkjoldRouteProvider(private val ctx: Context) : MediaRouteProvider(ctx) {
    private val browser = DeviceBrowser(ctx)
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)

    init {
        Store.init(ctx)
        browser.onResolved = { d -> d.host?.let { h -> add(SkjoldRoutes.Found(h, d.name)) } }
        // kjente enheter fra appen vises med en gang, før NSD har svart
        val known = try { Store.load("skjold-known", ListSerializer(KnownDevice.serializer())) } catch (_: Exception) { null } ?: emptyList()
        known.forEach { add(SkjoldRoutes.Found(it.host, it.name.ifEmpty { it.host }), publish = false) }
        publish()
    }

    private fun add(f: SkjoldRoutes.Found, publish: Boolean = true) {
        if (SkjoldRoutes.found.any { it.host == f.host }) return
        SkjoldRoutes.found = SkjoldRoutes.found + f
        if (publish) publish()
    }

    private fun publish() {
        val snap = WidgetStore.load(ctx)
        val b = MediaRouteProviderDescriptor.Builder()
        SkjoldRoutes.found.forEach { b.addRoute(SkjoldRoutes.descriptor(it, it.host == snap.host, snap.volume)) }
        setDescriptor(b.build())
    }

    override fun onDiscoveryRequestChanged(request: MediaRouteDiscoveryRequest?) {
        if (request != null && request.selector.hasControlCategory(SkjoldRoutes.CATEGORY)) browser.start() else browser.stop()
    }

    override fun onCreateRouteController(routeId: String): RouteController? {
        val host = routeId.removePrefix("skjold:")
        if (SkjoldRoutes.found.none { it.host == host }) return null
        return object : RouteController() {
            override fun onSelect() { SkjoldRoutes.select(ctx, host); publish() }
            override fun onSetVolume(volume: Int) {
                scope.launch { DeviceLink.send("/api/volume", mapOf("volume" to volume.coerceIn(0, 100)), on = host) }
            }
            override fun onUpdateVolume(delta: Int) {
                val v = (WidgetStore.load(ctx).volume + delta * 3).coerceIn(0, 100)
                scope.launch { DeviceLink.send("/api/volume", mapOf("volume" to v), on = host) }
            }
        }
    }
}
