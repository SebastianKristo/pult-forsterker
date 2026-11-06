package no.kristo.skjold

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.content.pm.ShortcutInfo
import android.content.pm.ShortcutManager
import android.graphics.drawable.Icon
import android.net.Uri
import android.os.Bundle
import android.widget.Toast
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import kotlin.concurrent.thread

/**
 * App-snarveier (langt trykk på ikonet): «Hva er dette?» (statisk) og én snarvei per Skjold-rutine (dynamisk,
 * hentet fra /api/routines). Snarveiene åpner denne usynlige aktiviteten, som sender kallet og lukker seg.
 */
class ShortcutActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val u = intent?.data
        val (path, msg) = when (u?.host) {
            "routine" -> "/api/routines/${Uri.encode(u.lastPathSegment ?: "")}/run" to "Kjører rutine"
            "recognize" -> "/api/recognize" to "Lytter …"
            "doorbell" -> "/api/doorbell" to "Ringer på"
            else -> { finish(); return }
        }
        val app = applicationContext
        thread {
            val ok = Shortcuts.post(app, path)
            runOnUiThread { Toast.makeText(app, if (ok) msg else "Fikk ikke kontakt med Skjold", Toast.LENGTH_SHORT).show() }
        }
        finish()
    }
}

object Shortcuts {
    private fun base(ctx: Context): String? {
        val h = WidgetStore.load(ctx).host.trim().trimEnd('/')
        if (h.isEmpty()) return null
        return if (h.startsWith("http")) h else "http://$h"
    }

    private fun http(ctx: Context, method: String, path: String): String? = try {
        val b = base(ctx) ?: return null
        val c = URL(b + path).openConnection() as HttpURLConnection
        c.requestMethod = method; c.connectTimeout = 4000; c.readTimeout = 8000
        if (method == "POST") { c.doOutput = true; c.setRequestProperty("Content-Type", "application/json"); c.outputStream.use { it.write("{}".toByteArray()) } }
        if (c.responseCode in 200..299) c.inputStream.bufferedReader().readText() else null
    } catch (_: Exception) { null }

    fun post(ctx: Context, path: String): Boolean = http(ctx, "POST", path) != null

    /** Oppdater de dynamiske rutine-snarveiene. Kalles i bakgrunnen når appen starter. */
    fun refresh(ctx: Context) = thread {
        val body = http(ctx, "GET", "/api/routines") ?: return@thread
        val arr = try { JSONObject(body).optJSONArray("routines") } catch (_: Exception) { null } ?: return@thread
        val sm = ctx.getSystemService(ShortcutManager::class.java) ?: return@thread
        val max = (sm.maxShortcutCountPerActivity - 1).coerceAtLeast(1)
        val list = (0 until minOf(arr.length(), max)).mapNotNull { i ->
            val r = arr.optJSONObject(i) ?: return@mapNotNull null
            val id = r.optString("id").ifEmpty { return@mapNotNull null }
            val name = r.optString("navn", r.optString("name", id)).ifEmpty { id }
            ShortcutInfo.Builder(ctx, "routine-$id").setShortLabel(name).setLongLabel("Kjør $name")
                .setIcon(Icon.createWithResource(ctx, R.mipmap.ic_launcher))
                .setIntent(Intent(Intent.ACTION_VIEW, Uri.parse("skjold://routine/$id"), ctx, ShortcutActivity::class.java))
                .setRank(i).build()
        }
        try { sm.dynamicShortcuts = list } catch (_: Exception) {}
    }
}
