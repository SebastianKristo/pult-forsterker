package no.kristo.skjold;

import android.os.Bundle;

import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(AppUpdaterPlugin.class);   // oppdatering av appen fra GitHub Releases
        super.onCreate(savedInstanceState);
    }
}
