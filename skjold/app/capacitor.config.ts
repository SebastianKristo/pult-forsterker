import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'no.kristo.skjold',
  appName: 'Skjold',
  webDir: 'dist',
  backgroundColor: '#0b0b0c',
  android: {
    // The S1 speaks plain http on the LAN (skjold.local:8765)
    allowMixedContent: true
  },
  ios: {
    contentInset: 'automatic',
    backgroundColor: '#0b0b0c'
  },
  plugins: {
    // Route window.fetch through native HTTP: no CORS needed on the Pi, and http:// works on iOS/Android.
    CapacitorHttp: { enabled: true }
  }
};

export default config;
