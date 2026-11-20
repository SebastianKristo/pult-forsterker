package no.kristo.skjold;

import android.Manifest;
import android.content.Context;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.NetworkRequest;
import android.net.wifi.WifiNetworkSpecifier;
import android.os.Build;

import com.getcapacitor.JSObject;
import com.getcapacitor.PermissionState;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import com.getcapacitor.annotation.Permission;
import com.getcapacitor.annotation.PermissionCallback;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.Iterator;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Midlertidig Wi-Fi for oppsett av Skjold Røst (squeezelite-esp32 sitt oppsettnett «Skjold-Rost» på 192.168.4.1).
 *
 * connect({ssid, password, timeoutMs}) – ber Android om akkurat dette nettet med WifiNetworkSpecifier (Android 10+).
 *   Android viser selv en dialog der brukeren godtar. Nettet brukes bare av Skjold-appen; telefonen beholder ellers
 *   hjemmenettet/mobildata. Prosessen bindes også til nettet (bindProcessToNetwork) mens det er aktivt.
 * request({url, method, headers, body, timeoutMs}) – HTTP over det nettet med Network.openConnection(), uavhengig av
 *   WebView/CapacitorHttp-ruting. Bare http://192.168.4.x (Røst) og http://10.42.0.1 (oppsett-nettet til Touch/S1/Node) er lov.
 * disconnect() – slipper nettet og bindingen, så telefonen går tilbake til vanlig Wi-Fi.
 *
 * Feilkoder (call.reject(..., code)): NOT_FOUND (fant ikke nettet eller brukeren avviste), UNSUPPORTED (Android 9 og eldre),
 * NOT_CONNECTED, HTTP.
 */
@CapacitorPlugin(
    name = "SkjoldWifi",
    permissions = {
        // Android 10–12: noen telefoner krever posisjon for å søke etter / foreslå Wi-Fi-nett
        @Permission(alias = "location", strings = { Manifest.permission.ACCESS_FINE_LOCATION }),
        // Android 13+: «Enheter i nærheten» erstatter posisjon for Wi-Fi
        @Permission(alias = "nearby", strings = { "android.permission.NEARBY_WIFI_DEVICES" })
    }
)
public class SkjoldWifiPlugin extends Plugin {

    private ConnectivityManager.NetworkCallback callback;
    private volatile Network network;

    private ConnectivityManager cm() {
        return (ConnectivityManager) getContext().getSystemService(Context.CONNECTIVITY_SERVICE);
    }

    @PluginMethod
    public void connect(PluginCall call) {
        if (Build.VERSION.SDK_INT < 29) {
            call.reject("Krever Android 10 eller nyere.", "UNSUPPORTED");
            return;
        }
        String alias = Build.VERSION.SDK_INT >= 33 ? "nearby" : "location";
        if (getPermissionState(alias) != PermissionState.GRANTED) {
            requestPermissionForAlias(alias, call, "permissionDone");
            return;
        }
        doConnect(call);
    }

    @PermissionCallback
    private void permissionDone(PluginCall call) {
        // Prøv uansett: WifiNetworkSpecifier virker på de fleste telefoner også uten tillatelsen.
        doConnect(call);
    }

    private void doConnect(PluginCall call) {
        String ssid = call.getString("ssid");
        String password = call.getString("password", "");
        int timeout = call.getInt("timeoutMs", 30000);
        if (ssid == null || ssid.isEmpty()) {
            call.reject("Mangler nettverksnavn");
            return;
        }
        if (Build.VERSION.SDK_INT < 29) {
            call.reject("Krever Android 10 eller nyere.", "UNSUPPORTED");
            return;
        }
        release();

        WifiNetworkSpecifier.Builder spec = new WifiNetworkSpecifier.Builder().setSsid(ssid);
        if (password != null && !password.isEmpty()) spec.setWpa2Passphrase(password);
        NetworkRequest request = new NetworkRequest.Builder()
            .addTransportType(NetworkCapabilities.TRANSPORT_WIFI)
            .removeCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)   // oppsettnettet har ikke internett
            .setNetworkSpecifier(spec.build())
            .build();

        final ConnectivityManager cm = cm();
        final AtomicBoolean answered = new AtomicBoolean(false);
        ConnectivityManager.NetworkCallback cb = new ConnectivityManager.NetworkCallback() {
            @Override
            public void onAvailable(Network n) {
                network = n;
                cm.bindProcessToNetwork(n);
                if (answered.compareAndSet(false, true)) {
                    JSObject ret = new JSObject();
                    ret.put("ssid", ssid);
                    ret.put("verified", true);
                    call.resolve(ret);
                }
            }

            @Override
            public void onLost(Network n) {
                // Røst kan bytte radiokanal når den kobler til ruteren. Android kobler gjerne til igjen (onAvailable).
                if (n.equals(network)) {
                    network = null;
                    cm.bindProcessToNetwork(null);
                }
            }

            @Override
            public void onUnavailable() {
                callback = null;
                if (answered.compareAndSet(false, true)) {
                    call.reject("Fant ikke nettet «" + ssid + "», eller tilkoblingen ble avvist.", "NOT_FOUND");
                }
            }
        };
        callback = cb;
        try {
            cm.requestNetwork(request, cb, timeout);
        } catch (Exception e) {
            callback = null;
            call.reject("Fikk ikke bedt om Wi-Fi: " + e.getMessage(), "NOT_FOUND");
        }
    }

    @PluginMethod
    public void request(PluginCall call) {
        final String url = call.getString("url", "");
        final String method = call.getString("method", "GET");
        final String body = call.getString("body");
        final int timeout = call.getInt("timeoutMs", 6000);
        final JSObject headers = call.getObject("headers", new JSObject());
        if (url == null || !(url.startsWith("http://192.168.4.") || url.startsWith("http://10.42.0.1:"))) {
            call.reject("Bare http://192.168.4.x og http://10.42.0.1 (Skjold-oppsett) er lov");
            return;
        }
        final Network net = network;
        if (net == null) {
            call.reject("Ikke koblet til oppsettnettet", "NOT_CONNECTED");
            return;
        }
        new Thread(() -> {
            HttpURLConnection con = null;
            try {
                con = (HttpURLConnection) net.openConnection(new URL(url));
                con.setConnectTimeout(timeout);
                con.setReadTimeout(timeout);
                con.setUseCaches(false);
                con.setRequestMethod(method);
                Iterator<String> keys = headers.keys();
                while (keys.hasNext()) {
                    String k = keys.next();
                    con.setRequestProperty(k, headers.getString(k));
                }
                if (body != null) {
                    byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
                    con.setDoOutput(true);
                    con.setFixedLengthStreamingMode(bytes.length);
                    try (OutputStream out = con.getOutputStream()) { out.write(bytes); }
                }
                int status = con.getResponseCode();
                InputStream in = status >= 400 ? con.getErrorStream() : con.getInputStream();
                String data = "";
                if (in != null) {
                    try (InputStream is = in; ByteArrayOutputStream buf = new ByteArrayOutputStream()) {
                        byte[] b = new byte[8192];
                        int r;
                        while ((r = is.read(b)) != -1) buf.write(b, 0, r);
                        data = buf.toString("UTF-8");
                    }
                }
                JSObject ret = new JSObject();
                ret.put("status", status);
                ret.put("data", data);
                call.resolve(ret);
            } catch (Exception e) {
                call.reject("HTTP-feil: " + e.getMessage(), "HTTP");
            } finally {
                if (con != null) con.disconnect();
            }
        }).start();
    }

    @PluginMethod
    public void disconnect(PluginCall call) {
        release();
        call.resolve();
    }

    private void release() {
        ConnectivityManager cm = cm();
        ConnectivityManager.NetworkCallback cb = callback;
        callback = null;
        network = null;
        try { cm.bindProcessToNetwork(null); } catch (Exception ignored) { }
        if (cb != null) {
            try { cm.unregisterNetworkCallback(cb); } catch (Exception ignored) { /* allerede frigjort (onUnavailable) */ }
        }
    }

    @Override
    protected void handleOnDestroy() {
        release();
        super.handleOnDestroy();
    }
}
