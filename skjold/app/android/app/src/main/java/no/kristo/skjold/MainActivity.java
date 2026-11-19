package no.kristo.skjold;

import android.os.Bundle;

import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(AppUpdaterPlugin.class);   // oppdatering av appen fra GitHub Releases
        registerPlugin(SkjoldWifiPlugin.class);   // Legg til enhet → Skjold Røst: midlertidig Wi-Fi til oppsettnettet
        super.onCreate(savedInstanceState);
    }
}
