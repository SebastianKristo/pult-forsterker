package no.kristo.skjold

import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageInstaller
import android.net.Uri
import android.os.Build
import android.provider.Settings
import android.widget.Toast
import org.json.JSONArray
import java.net.HttpURLConnection
import java.net.URL

/**
 * Oppdatering av selve Skjold-appen fra GitHub (utgivelsene app-v*, filen skjold-android-<tag>.apk).
 *
 * Appen laster ned APK-en og gir den til Androids pakkeinstallerer (PackageInstaller). Android spør brukeren én gang
 * om Skjold får installere apper, og viser så «Oppdater?». APK-ene signeres med samme nøkkel i hver utgivelse
 * (SKJOLD_KEYSTORE_B64 i app-release.yml), så den nye versjonen legger seg over den gamle med innstillingene i behold.
 */
object AppUpdate {
    private const val REPO = "SebastianKristo/pult-forsterker"
    const val ACTION = "no.kristo.skjold.APP_UPDATE_STATUS"

    data class Ny(val tag: String, val versjon: String, val url: String, val bytes: Long, val dato: String)

    fun installert(ctx: Context): String = try {
        ctx.packageManager.getPackageInfo(ctx.packageName, 0).versionName ?: "0.0.0"
    } catch (_: Exception) { "0.0.0" }

    private fun tall(v: String) = v.removePrefix("app-v").removePrefix("v").substringBefore('-').split('.').map { it.toIntOrNull() ?: 0 }

    /** > 0 når a er nyere enn b. */
    fun cmp(a: String, b: String): Int {
        val x = tall(a); val y = tall(b)
        for (i in 0 until maxOf(x.size, y.size)) { val d = x.getOrElse(i) { 0 } - y.getOrElse(i) { 0 }; if (d != 0) return d }
        return 0
    }

    /** Nyeste app-v*-utgivelse med Android-APK, eller null hvis du har den. Kaster med en norsk melding ved feil. */
    fun sjekk(ctx: Context): Ny? {
        val c = URL("https://api.github.com/repos/$REPO/releases?per_page=30").openConnection() as HttpURLConnection
        c.connectTimeout = 10000; c.readTimeout = 15000
        c.setRequestProperty("Accept", "application/vnd.github+json"); c.setRequestProperty("User-Agent", "Skjold-Android")
        val code = try { c.responseCode } catch (e: Exception) { throw RuntimeException("Fikk ikke kontakt med GitHub") }
        if (code != 200) throw RuntimeException("GitHub svarte $code")
        val arr = JSONArray(c.inputStream.bufferedReader().readText())
        var best: Ny? = null
        for (i in 0 until arr.length()) {
            val r = arr.optJSONObject(i) ?: continue
            val tag = r.optString("tag_name")
            if (r.optBoolean("draft") || r.optBoolean("prerelease") || !tag.startsWith("app-v")) continue
            val assets = r.optJSONArray("assets") ?: continue
            val apk = (0 until assets.length()).mapNotNull { assets.optJSONObject(it) }
                .firstOrNull { it.optString("name").startsWith("skjold-android-") && it.optString("name").endsWith(".apk") } ?: continue
            val ny = Ny(tag, tag.removePrefix("app-v"), apk.optString("browser_download_url"), apk.optLong("size"), r.optString("published_at").take(10))
            if (best == null || cmp(ny.tag, best.tag) > 0) best = ny
        }
        return best?.takeIf { cmp(it.versjon, installert(ctx)) > 0 }
    }

    /** Kan Skjold installere apper? (Android 8+: «Installer ukjente apper» for Skjold.) */
    fun kanInstallere(ctx: Context) = Build.VERSION.SDK_INT < 26 || ctx.packageManager.canRequestPackageInstalls()

    fun aapneTillatelse(ctx: Context) {
        if (Build.VERSION.SDK_INT >= 26) ctx.startActivity(
            Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES, Uri.parse("package:" + ctx.packageName)).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
    }

    /** Last ned og gi APK-en til installereren. fremdrift(0–1). Kjøres i en bakgrunnstråd. */
    fun installer(ctx: Context, ny: Ny, fremdrift: (Float) -> Unit) {
        val app = ctx.applicationContext
        val pi = app.packageManager.packageInstaller
        val params = PackageInstaller.SessionParams(PackageInstaller.SessionParams.MODE_FULL_INSTALL).apply {
            setAppPackageName(app.packageName)
            if (Build.VERSION.SDK_INT >= 31) setRequireUserAction(PackageInstaller.SessionParams.USER_ACTION_NOT_REQUIRED)
        }
        val id = pi.createSession(params)
        pi.openSession(id).use { s ->
            var url = ny.url; var c: HttpURLConnection
            var hopp = 0
            while (true) {   // GitHub sender videre til lagringen (andre vert), følg det selv
                c = URL(url).openConnection() as HttpURLConnection
                c.instanceFollowRedirects = false; c.connectTimeout = 15000; c.readTimeout = 30000
                c.setRequestProperty("User-Agent", "Skjold-Android")
                val code = c.responseCode
                if (code in 300..399 && hopp++ < 5) { url = c.getHeaderField("Location") ?: break; continue }
                if (code != 200) throw RuntimeException("Nedlastingen feilet ($code)")
                break
            }
            val total = c.contentLengthLong.takeIf { it > 0 } ?: ny.bytes
            c.inputStream.use { inn ->
                s.openWrite("skjold.apk", 0, total.takeIf { it > 0 } ?: -1).use { ut ->
                    val buf = ByteArray(64 * 1024); var n: Int; var sum = 0L
                    while (inn.read(buf).also { n = it } > 0) {
                        ut.write(buf, 0, n); sum += n
                        if (total > 0) fremdrift((sum.toFloat() / total).coerceIn(0f, 1f))
                    }
                    s.fsync(ut)
                }
            }
            val flags = PendingIntent.FLAG_UPDATE_CURRENT or (if (Build.VERSION.SDK_INT >= 31) PendingIntent.FLAG_MUTABLE else 0)
            val status = PendingIntent.getBroadcast(app, id, Intent(app, AppUpdateReceiver::class.java).setAction(ACTION), flags)
            s.commit(status.intentSender)
        }
    }
}

/** Svar fra pakkeinstallereren: be brukeren bekrefte, eller vis hvorfor det feilet. */
class AppUpdateReceiver : BroadcastReceiver() {
    override fun onReceive(ctx: Context, intent: Intent) {
        when (intent.getIntExtra(PackageInstaller.EXTRA_STATUS, PackageInstaller.STATUS_FAILURE)) {
            PackageInstaller.STATUS_PENDING_USER_ACTION -> {
                @Suppress("DEPRECATION")
                val bekreft = if (Build.VERSION.SDK_INT >= 33) intent.getParcelableExtra(Intent.EXTRA_INTENT, Intent::class.java)
                              else intent.getParcelableExtra(Intent.EXTRA_INTENT)
                bekreft?.let { ctx.startActivity(it.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)) }
            }
            PackageInstaller.STATUS_SUCCESS -> Toast.makeText(ctx, "Skjold er oppdatert", Toast.LENGTH_SHORT).show()
            else -> {
                val msg = intent.getStringExtra(PackageInstaller.EXTRA_STATUS_MESSAGE) ?: ""
                val tekst = if ("signature" in msg.lowercase() || "conflict" in msg.lowercase())
                    "Oppdateringen er signert med en annen nøkkel enn appen du har. Avinstaller Skjold og installer den nye én gang."
                    else "Oppdateringen ble ikke installert" + (if (msg.isNotBlank()) ": $msg" else "")
                Toast.makeText(ctx, tekst, Toast.LENGTH_LONG).show()
            }
        }
    }
}

