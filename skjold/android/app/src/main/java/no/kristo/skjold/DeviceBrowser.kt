package no.kristo.skjold

import android.content.Context
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import android.net.wifi.WifiManager
import android.os.Handler
import android.os.Looper
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import java.net.Inet4Address
import java.net.Inet6Address

/** A Skjold device seen on mDNS. `host` ("ip:port") is filled in once the service has been resolved. */
data class FoundDevice(val name: String, val type: String, val product: String, val host: String? = null) {
    val id: String get() = "$type/$name"
}

/**
 * Browses for the daemon's `_kipultamp._tcp` (TXT: id, version, name, type, product, path) and the older `_skjold._tcp`
 * with Android NSD, and resolves each service to an `ip:port` (DeviceBrowser in Services.swift).
 */
class DeviceBrowser(ctx: Context) {
    companion object {
        val TYPES = listOf("_kipultamp._tcp", "_skjold._tcp")
    }

    private val app = ctx.applicationContext
    private val nsd = app.getSystemService(Context.NSD_SERVICE) as NsdManager
    private val main = Handler(Looper.getMainLooper())
    private var listeners: List<NsdManager.DiscoveryListener> = emptyList()
    private var lock: WifiManager.MulticastLock? = null

    var devices by mutableStateOf<List<FoundDevice>>(emptyList())
        private set

    private val seen = HashMap<String, MutableMap<String, NsdServiceInfo>>()
    private val resolved = HashMap<String, FoundDevice>()
    private val queue = ArrayDeque<NsdServiceInfo>()
    private var resolving = false

    /** Called when a device has been resolved to a host. */
    var onResolved: ((FoundDevice) -> Unit)? = null

    fun start() {
        if (listeners.isNotEmpty()) return
        try {
            lock = (app.getSystemService(Context.WIFI_SERVICE) as? WifiManager)?.createMulticastLock("skjold-nsd")?.apply {
                setReferenceCounted(false); acquire()
            }
        } catch (_: Exception) {}
        listeners = TYPES.map { type ->
            val l = object : NsdManager.DiscoveryListener {
                override fun onDiscoveryStarted(serviceType: String) {}
                override fun onDiscoveryStopped(serviceType: String) {}
                override fun onStartDiscoveryFailed(serviceType: String, errorCode: Int) {}
                override fun onStopDiscoveryFailed(serviceType: String, errorCode: Int) {}
                override fun onServiceFound(info: NsdServiceInfo) {
                    main.post {
                        seen.getOrPut(type) { mutableMapOf() }[info.serviceName] = info
                        publish()
                        if (resolved["$type/${info.serviceName}"] == null) enqueue(info, type)
                    }
                }
                override fun onServiceLost(info: NsdServiceInfo) {
                    main.post {
                        seen[type]?.remove(info.serviceName)
                        resolved.remove("$type/${info.serviceName}")
                        publish()
                    }
                }
            }
            try { nsd.discoverServices(type, NsdManager.PROTOCOL_DNS_SD, l) } catch (_: Exception) {}
            l
        }
    }

    fun stop() {
        listeners.forEach { try { nsd.stopServiceDiscovery(it) } catch (_: Exception) {} }
        listeners = emptyList()
        try { lock?.release() } catch (_: Exception) {}
    }

    private fun publish() {
        val all = ArrayList<FoundDevice>()
        for (t in TYPES) {
            for ((name, _) in seen[t] ?: emptyMap()) {
                val d = resolved["$t/$name"] ?: FoundDevice(name, t, "")
                // the same box can advertise both types: keep the _kipultamp one
                if (all.none { it.name == d.name }) all.add(d)
            }
        }
        devices = all.sortedBy { it.name }
    }

    private val typeOf = HashMap<String, String>()

    private fun enqueue(info: NsdServiceInfo, type: String) {
        typeOf[info.serviceName + "\u0001" + type] = type
        if (queue.none { it.serviceName == info.serviceName && it.serviceType == info.serviceType }) queue.addLast(info)
        next()
    }

    /** Older Android versions only allow one resolve at a time, so they are queued. */
    @Suppress("DEPRECATION")
    private fun next() {
        if (resolving) return
        val info = queue.removeFirstOrNull() ?: return
        resolving = true
        try {
            nsd.resolveService(info, object : NsdManager.ResolveListener {
                override fun onResolveFailed(si: NsdServiceInfo, errorCode: Int) {
                    main.post { resolving = false; next() }
                }

                override fun onServiceResolved(si: NsdServiceInfo) {
                    main.post {
                        resolving = false
                        val type = TYPES.firstOrNull { si.serviceType.contains(it) } ?: TYPES.firstOrNull { info.serviceType.contains(it) } ?: TYPES[0]
                        val addr = si.host
                        val h = when (addr) {
                            is Inet4Address -> addr.hostAddress
                            is Inet6Address -> "[" + (addr.hostAddress ?: "").substringBefore('%') + "]"
                            else -> addr?.hostAddress
                        }
                        val product = si.attributes?.get("product")?.let { String(it) } ?: ""
                        if (h != null) {
                            val d = FoundDevice(si.serviceName, type, product, "$h:${si.port}")
                            resolved[d.id] = d
                            publish()
                            devices.firstOrNull { it.id == d.id }?.let { onResolved?.invoke(it) }
                        }
                        next()
                    }
                }
            })
        } catch (_: Exception) {
            resolving = false
            main.post { next() }
        }
    }
}
