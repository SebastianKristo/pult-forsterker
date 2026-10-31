package no.kristo.skjold;

import android.content.Intent;
import android.content.pm.PackageInfo;
import android.net.Uri;
import android.os.Build;
import android.provider.Settings;

import androidx.core.content.FileProvider;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

/**
 * Oppdaterer Skjold-appen fra en APK på GitHub Releases:
 * getInfo() – installert versjon, canInstall() – om brukeren har tillatt «Installer ukjente apper» for Skjold,
 * openInstallSettings() – åpner den innstillingen, downloadAndInstall({url}) – laster ned APK-en (med «progress»-hendelser)
 * og åpner Androids installasjonsdialog. Android krever alltid at brukeren bekrefter installasjonen selv.
 */
@CapacitorPlugin(name = "AppUpdater")
public class AppUpdaterPlugin extends Plugin {

    @PluginMethod
    public void getInfo(PluginCall call) {
        try {
            PackageInfo pi = getContext().getPackageManager().getPackageInfo(getContext().getPackageName(), 0);
            JSObject ret = new JSObject();
            ret.put("versionName", pi.versionName);
            ret.put("versionCode", Build.VERSION.SDK_INT >= 28 ? pi.getLongVersionCode() : pi.versionCode);
            call.resolve(ret);
        } catch (Exception e) {
            call.reject("Fant ikke versjonen: " + e.getMessage());
        }
    }

    @PluginMethod
    public void canInstall(PluginCall call) {
        JSObject ret = new JSObject();
        ret.put("allowed", Build.VERSION.SDK_INT < 26 || getContext().getPackageManager().canRequestPackageInstalls());
        call.resolve(ret);
    }

    @PluginMethod
    public void openInstallSettings(PluginCall call) {
        if (Build.VERSION.SDK_INT >= 26) {
            Intent i = new Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES, Uri.parse("package:" + getContext().getPackageName()));
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            getContext().startActivity(i);
        }
        call.resolve();
    }

    @PluginMethod
    public void downloadAndInstall(PluginCall call) {
        String url = call.getString("url");
        if (url == null || !url.startsWith("https://")) {
            call.reject("Ugyldig adresse");
            return;
        }
        call.setKeepAlive(false);
        new Thread(() -> {
            HttpURLConnection con = null;
            try {
                File dir = new File(getContext().getCacheDir(), "updates");
                if (!dir.exists() && !dir.mkdirs()) throw new Exception("kan ikke lage mappe");
                File apk = new File(dir, "skjold-update.apk");
                if (apk.exists()) apk.delete();

                // GitHub sender en omdirigering til objects.githubusercontent.com (https -> https følges automatisk)
                con = (HttpURLConnection) new URL(url).openConnection();
                con.setInstanceFollowRedirects(true);
                con.setConnectTimeout(15000);
                con.setReadTimeout(30000);
                con.setRequestProperty("Accept", "application/octet-stream");
                int code = con.getResponseCode();
                if (code != 200) throw new Exception("GitHub svarte " + code);
                long total = con.getContentLengthLong();
                long done = 0;
                int lastPct = -1;
                try (InputStream in = con.getInputStream(); OutputStream out = new FileOutputStream(apk)) {
                    byte[] buf = new byte[64 * 1024];
                    int n;
                    while ((n = in.read(buf)) > 0) {
                        out.write(buf, 0, n);
                        done += n;
                        if (total > 0) {
                            int pct = (int) (done * 100 / total);
                            if (pct != lastPct) {
                                lastPct = pct;
                                JSObject p = new JSObject();
                                p.put("percent", pct);
                                notifyListeners("progress", p);
                            }
                        }
                    }
                }
                if (total > 0 && done != total) throw new Exception("nedlastingen ble avbrutt");

                Uri uri = FileProvider.getUriForFile(getContext(), getContext().getPackageName() + ".fileprovider", apk);
                Intent i = new Intent(Intent.ACTION_VIEW);
                i.setDataAndType(uri, "application/vnd.android.package-archive");
                i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_ACTIVITY_NEW_TASK);
                getContext().startActivity(i);
                call.resolve();
            } catch (Exception e) {
                call.reject("Oppdateringen feilet: " + e.getMessage());
            } finally {
                if (con != null) con.disconnect();
            }
        }).start();
    }
}
