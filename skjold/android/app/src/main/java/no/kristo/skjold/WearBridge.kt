package no.kristo.skjold

import android.content.Context
import android.content.SharedPreferences
import com.google.android.gms.wearable.MessageEvent
import com.google.android.gms.wearable.PutDataMapRequest
import com.google.android.gms.wearable.Wearable
import com.google.android.gms.wearable.WearableListenerService
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import org.json.JSONArray
import org.json.JSONObject

/**
 * Telefonens side av Wear OS-appen (modulen :wear).
 * - Kjente Skjold-enheter og aktiv enhet sendes til klokka som DataItem «/skjold/rom».
 * - Klokka sender kommandoer hit (MessageClient «/skjold/kall») når den ikke når Skjold selv; svaret sendes tilbake
 *   som «/skjold/svar» med samme id.
 */
object WearBridge {
    private var listener: SharedPreferences.OnSharedPreferenceChangeListener? = null

    fun init(ctx: Context) {
        val app = ctx.applicationContext
        push(app)
        val l = SharedPreferences.OnSharedPreferenceChangeListener { _, key ->
            if (key == "skjold-known" || key == "skjold-host") push(app)
        }
        listener = l   // SharedPreferences holder bare en svak referanse
        Store.prefs?.registerOnSharedPreferenceChangeListener(l)
    }

    fun push(ctx: Context) {
        try {
            val p = Store.prefs ?: return
            val rooms = JSONArray()
            val known = p.getString("skjold-known", null)
            if (known != null) {
                val arr = JSONArray(known)
                for (i in 0 until arr.length()) {
                    val k = arr.optJSONObject(i) ?: continue
                    val host = k.optString("host")
                    if (host.isNotEmpty()) rooms.put(JSONObject().put("host", host).put("name", k.optString("name", host)).put("product", k.optString("product")))
                }
            }
            val req = PutDataMapRequest.create("/skjold/rom").apply {
                dataMap.putString("rom", rooms.toString())
                dataMap.putString("aktiv", p.getString("skjold-host", "") ?: "")
            }.asPutDataRequest().setUrgent()
            Wearable.getDataClient(ctx).putDataItem(req)
        } catch (_: Exception) {
            // Ingen Google Play-tjenester / ingen klokke – ignorer.
        }
    }
}

/** Tar imot kall fra klokka og gjør dem mot Skjold på vegne av den. */
class WearCallService : WearableListenerService() {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    override fun onMessageReceived(event: MessageEvent) {
        if (event.path != "/skjold/kall") return
        val node = event.sourceNodeId
        val raw = event.data
        scope.launch {
            var id = ""
            val svar: ByteArray = try {
                Store.init(applicationContext)
                val j = JSONObject(String(raw))
                id = j.optString("id")
                val host = j.optString("host")
                val path = j.optString("path")
                val method = j.optString("method", "GET")
                val body = j.optString("body", "").takeIf { it.isNotEmpty() }?.toByteArray()
                val url = Net.url(host, path)
                val r = if (url != null) Net.data(url, method, body, 8.0) else null
                if (r != null && r.second < 300) r.first else ByteArray(0)
            } catch (_: Exception) {
                ByteArray(0)
            }
            try {
                val out = JSONObject().put("id", id).put("data", android.util.Base64.encodeToString(svar, android.util.Base64.NO_WRAP))
                Wearable.getMessageClient(applicationContext).sendMessage(node, "/skjold/svar", out.toString().toByteArray())
            } catch (_: Exception) { }
        }
    }
}
