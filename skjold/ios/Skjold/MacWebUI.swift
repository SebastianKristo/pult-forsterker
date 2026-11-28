import SwiftUI
import UIKit
import WebKit

// Mac: Skjold-enhetens eget web-UI (det samme som på http://<enhet>:8765 i nettleseren) i et Mac-vindu, med
// sidemenyen og skrivebordsoppsettet derfra. Appen finner enhetene (Bonjour), husker dem, og menylinjen har
// avspilling, volum og «Enhet» for å bytte. «Vis → Appvisning» gir iPad-utseendet i stedet.
// Uten enhet (demo) eller via Skjold-hjem utenfor hjemmet brukes appvisningen, siden web-UI-et bare nås lokalt.

enum MacUI {
    /// Varsel som laster web-UI-et på nytt (⌘R).
    static let reload = Notification.Name("skjold.mac.reload")

    /// Web-UI-et vises bare i Mac-versjonen.
    static var isMac: Bool {
        #if targetEnvironment(macCatalyst)
        return true
        #else
        return false
        #endif
    }
}

/// Velger web-UI eller appvisning på Mac. På iPhone/iPad: alltid appvisningen.
struct MacShell<App: View>: View {
    @Environment(AppModel.self) private var m
    @AppStorage("macWebUI") private var web = true
    @ViewBuilder var app: () -> App

    var body: some View {
        if MacUI.isMac, web, m.mode == .app, let h = m.activeHost, !HjemAPI.isRelay(h), let url = Net.url(h, "/") {
            MacWebView(url: url)
                .ignoresSafeArea()
                .background(V4.bg)
        } else {
            app()
        }
    }
}

/// WKWebView med web-UI-et. Lastes på nytt når enheten byttes, eller med ⌘R.
struct MacWebView: UIViewRepresentable {
    let url: URL

    func makeCoordinator() -> Coordinator { Coordinator() }

    func makeUIView(context: Context) -> WKWebView {
        let cfg = WKWebViewConfiguration()
        cfg.websiteDataStore = .default()              // web-UI-ets egne innstillinger (localStorage) huskes
        cfg.preferences.isElementFullscreenEnabled = true
        let w = WKWebView(frame: .zero, configuration: cfg)
        w.isOpaque = false
        w.backgroundColor = UIColor(V4.bg)
        w.scrollView.backgroundColor = w.backgroundColor
        w.allowsBackForwardNavigationGestures = false
        w.navigationDelegate = context.coordinator
        context.coordinator.web = w
        context.coordinator.observe()
        load(w, context.coordinator)
        return w
    }

    func updateUIView(_ w: WKWebView, context: Context) {
        if context.coordinator.loaded != url { load(w, context.coordinator) }
    }

    private func load(_ w: WKWebView, _ c: Coordinator) {
        c.loaded = url
        w.load(URLRequest(url: url, cachePolicy: .reloadRevalidatingCacheData, timeoutInterval: 15))
    }

    final class Coordinator: NSObject, WKNavigationDelegate {
        weak var web: WKWebView?
        var loaded: URL?
        private var token: NSObjectProtocol?

        func observe() {
            token = NotificationCenter.default.addObserver(forName: MacUI.reload, object: nil, queue: .main) { [weak self] _ in
                MainActor.assumeIsolated { _ = self?.web?.reloadFromOrigin() }
            }
        }

        deinit { if let token { NotificationCenter.default.removeObserver(token) } }

        /// Lenker ut av Skjold (GitHub, Navidrome, Lyrion i nytt vindu …) åpnes i nettleseren, ikke i appvinduet.
        func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction,
                     decisionHandler: @escaping @MainActor @Sendable (WKNavigationActionPolicy) -> Void) {
            if let u = action.request.url, let host = loaded?.host,
               action.navigationType == .linkActivated || action.targetFrame == nil,
               u.host != host, ["http", "https", "mailto"].contains(u.scheme ?? "") {
                UIApplication.shared.open(u)
                decisionHandler(.cancel)
                return
            }
            decisionHandler(.allow)
        }

        /// Enheten svarer ikke (omstart, ny adresse): prøv igjen om litt.
        func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
            DispatchQueue.main.asyncAfter(deadline: .now() + 4) { [weak webView, weak self] in
                guard let webView, let u = self?.loaded else { return }
                webView.load(URLRequest(url: u))
            }
        }
    }
}

/// Menyen «Enhet» (bytt Skjold) og visningsvalgene i «Vis».
struct MacCommands: Commands {
    let model: AppModel
    @AppStorage("macWebUI") private var web = true

    var body: some Commands {
        CommandMenu("Enhet") {
            ForEach(model.known, id: \.host) { d in
                Button((d.host == model.activeHost ? "✓ " : "") + (d.name.isEmpty ? d.host : d.name)) {
                    Task { await model.connect(d.host) }
                }
            }
            if model.known.isEmpty { Text("Ingen Skjold funnet ennå") }
            Divider()
            if let h = model.activeHost, !HjemAPI.isRelay(h), let u = Net.url(h, "/") {
                Button("Åpne i nettleseren") { UIApplication.shared.open(u) }
            }
        }
        CommandGroup(after: .toolbar) {
            Toggle("Web-UI (som i nettleseren)", isOn: $web)
            Button("Last inn på nytt") { NotificationCenter.default.post(name: MacUI.reload, object: nil) }
                .keyboardShortcut("r", modifiers: .command)
                .disabled(!web)
        }
    }
}
