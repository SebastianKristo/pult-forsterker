// SkjoldWifi: lokal Capacitor-plugin (android/…/SkjoldWifiPlugin.java, ios/App/App/SkjoldWifiPlugin.swift).
// Kobler telefonen midlertidig til et Wi-Fi (Røst sitt oppsettnett «Skjold-Rost»), gjør HTTP-kall over akkurat det
// nettet og kobler fra igjen, så telefonen går tilbake til hjemmenettet.
//
// HTTP-kallene gjøres i native (ikke med fetch): på Android sendes de med Network.openConnection() over nettet vi ba om,
// så det spiller ingen rolle hva WebView/CapacitorHttp gjør med rutingen. På iOS går de med URLSession uten mobildata.
import { Capacitor, registerPlugin } from '@capacitor/core';

export interface WifiConnectResult { ssid: string; /** iOS: true hvis vi fikk bekreftet at telefonen står på nettet. */ verified?: boolean }
export interface WifiHttpResult { status: number; data: string }
export interface WifiHttpOptions { url: string; method?: 'GET' | 'POST' | 'DELETE'; headers?: Record<string, string>; body?: string; timeoutMs?: number }

export interface SkjoldWifiPlugin {
  /** Koble til et Wi-Fi midlertidig. Feilkoder: NOT_FOUND (fant ikke nettet / brukeren avviste), DENIED, UNSUPPORTED. */
  connect(o: { ssid: string; password?: string; timeoutMs?: number }): Promise<WifiConnectResult>;
  /** HTTP over nettet fra connect() (bare http://192.168.4.x). */
  request(o: WifiHttpOptions): Promise<WifiHttpResult>;
  /** Slipp nettet: telefonen går tilbake til vanlig Wi-Fi. Trygg å kalle flere ganger. */
  disconnect(): Promise<void>;
}

class WebFallback implements SkjoldWifiPlugin {
  private no(): never { throw Object.assign(new Error('Virker bare i Skjold-appen på telefonen.'), { code: 'UNAVAILABLE' }); }
  async connect(): Promise<WifiConnectResult> { this.no(); }
  async request(): Promise<WifiHttpResult> { this.no(); }
  async disconnect(): Promise<void> { /* ingenting å slippe */ }
}

const native = registerPlugin<SkjoldWifiPlugin>('SkjoldWifi', { web: () => new WebFallback() });

/** Testbryter for skjermbilder og utvikling i nettleseren: window.__skjoldWifiMock = { connect, request, disconnect }. */
function mock(): SkjoldWifiPlugin | null {
  const m = (globalThis as { __skjoldWifiMock?: SkjoldWifiPlugin }).__skjoldWifiMock;
  return m && typeof m.connect === 'function' ? m : null;
}

/** Kan appen bytte Wi-Fi selv? (native Android/iOS, eller mock). Ellers vises manuell veiledning. */
export function canJoinWifi(): boolean { return !!mock() || Capacitor.isNativePlatform(); }

export const SkjoldWifi: SkjoldWifiPlugin = {
  connect: (o) => (mock() ?? native).connect(o),
  request: (o) => (mock() ?? native).request(o),
  disconnect: () => (mock() ?? native).disconnect()
};

/** Feilkoden fra plugin-en (Capacitor legger den på .code). */
export function wifiErrCode(e: unknown): string {
  return e && typeof e === 'object' && 'code' in e ? String((e as { code: unknown }).code ?? '') : '';
}
