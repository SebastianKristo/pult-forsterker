import Foundation
import Capacitor
import NetworkExtension

/// Midlertidig Wi-Fi for oppsett av Skjold Røst (squeezelite-esp32 sitt oppsettnett «Skjold-Rost» på 192.168.4.1).
///
/// connect({ssid, password, timeoutMs}) – NEHotspotConfiguration med joinOnce (iOS viser selv «Vil koble til …»).
///   joinOnce betyr at iOS glemmer nettet igjen når appen går i bakgrunnen eller vi kaller disconnect().
/// request({url, method, headers, body, timeoutMs}) – HTTP med URLSession uten mobildata, så kallet går over Wi-Fi.
///   192.168.4.1 ligger på samme subnett som Wi-Fi-adressen telefonen får, så iOS ruter det dit selv om nettet
///   ikke har internett. Bare http://192.168.4.x er lov.
/// disconnect() – removeConfiguration, så telefonen går tilbake til hjemmenettet.
///
/// Krever entitlement com.apple.developer.networking.HotspotConfiguration (App.entitlements). Wi-Fi-info-entitlementet
/// gjør at vi kan bekrefte nettet med NEHotspotNetwork.fetchCurrent; uten det svarer vi verified=false og appen sjekker
/// selv om 192.168.4.1 svarer.
@objc(SkjoldWifiPlugin)
public class SkjoldWifiPlugin: CAPPlugin, CAPBridgedPlugin {
    public let identifier = "SkjoldWifiPlugin"
    public let jsName = "SkjoldWifi"
    public let pluginMethods: [CAPPluginMethod] = [
        CAPPluginMethod(name: "connect", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "request", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "disconnect", returnType: CAPPluginReturnPromise)
    ]

    private var currentSsid: String?

    private lazy var session: URLSession = {
        let cfg = URLSessionConfiguration.ephemeral
        cfg.allowsCellularAccess = false
        cfg.waitsForConnectivity = false
        cfg.requestCachePolicy = .reloadIgnoringLocalCacheData
        return URLSession(configuration: cfg)
    }()

    @objc func connect(_ call: CAPPluginCall) {
        guard let ssid = call.getString("ssid"), !ssid.isEmpty else {
            call.reject("Mangler nettverksnavn")
            return
        }
        let password = call.getString("password") ?? ""
        let timeoutMs = call.getInt("timeoutMs") ?? 30000

        let cfg = password.isEmpty
            ? NEHotspotConfiguration(ssid: ssid)
            : NEHotspotConfiguration(ssid: ssid, passphrase: password, isWEP: false)
        cfg.joinOnce = true

        NEHotspotConfigurationManager.shared.apply(cfg) { [weak self] error in
            if let err = error as NSError?, err.domain == NEHotspotConfigurationErrorDomain {
                switch NEHotspotConfigurationError(rawValue: err.code) {
                case .alreadyAssociated:
                    break   // står allerede på nettet
                case .userDenied:
                    call.reject("Du avviste tilkoblingen til «\(ssid)».", "DENIED")
                    return
                default:
                    call.reject("Fant ikke nettet «\(ssid)»: \(err.localizedDescription)", "NOT_FOUND", err)
                    return
                }
            } else if let err = error {
                call.reject("Fant ikke nettet «\(ssid)»: \(err.localizedDescription)", "NOT_FOUND", err)
                return
            }
            self?.currentSsid = ssid
            // apply() svarer «ok» også når nettet ikke finnes på noen iOS-versjoner – sjekk hvilket nett vi står på.
            self?.verify(ssid: ssid, deadline: Date().addingTimeInterval(min(Double(timeoutMs) / 1000.0, 15.0))) { verified, wrong in
                if wrong {
                    NEHotspotConfigurationManager.shared.removeConfiguration(forSSID: ssid)
                    self?.currentSsid = nil
                    call.reject("Fant ikke nettet «\(ssid)».", "NOT_FOUND")
                } else {
                    call.resolve(["ssid": ssid, "verified": verified])
                }
            }
        }
    }

    /// verified = vi så nettet; wrong = vi fikk svar, men telefonen står på et annet nett hele tiden.
    private func verify(ssid: String, deadline: Date, done: @escaping (_ verified: Bool, _ wrong: Bool) -> Void) {
        if #available(iOS 14.0, *) {
            NEHotspotNetwork.fetchCurrent { [weak self] net in
                if let net = net, net.ssid == ssid {
                    done(true, false)
                } else if Date() >= deadline {
                    // nil = mangler Wi-Fi-info-entitlement eller tillatelse: la appen sjekke 192.168.4.1 selv
                    done(false, net != nil)
                } else {
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.8) {
                        self?.verify(ssid: ssid, deadline: deadline, done: done)
                    }
                }
            }
        } else {
            done(false, false)
        }
    }

    @objc func request(_ call: CAPPluginCall) {
        guard let urlString = call.getString("url"), urlString.hasPrefix("http://192.168.4."), let url = URL(string: urlString) else {
            call.reject("Bare http://192.168.4.x er lov")
            return
        }
        var req = URLRequest(url: url)
        req.httpMethod = call.getString("method") ?? "GET"
        req.timeoutInterval = Double(call.getInt("timeoutMs") ?? 6000) / 1000.0
        req.allowsCellularAccess = false
        if let headers = call.getObject("headers") {
            for (k, v) in headers {
                if let s = v as? String { req.setValue(s, forHTTPHeaderField: k) }
            }
        }
        if let body = call.getString("body") {
            req.httpBody = body.data(using: .utf8)
        }
        session.dataTask(with: req) { data, response, error in
            if let error = error {
                call.reject("HTTP-feil: \(error.localizedDescription)", "HTTP", error)
                return
            }
            let status = (response as? HTTPURLResponse)?.statusCode ?? 0
            let text = data.flatMap { String(data: $0, encoding: .utf8) ?? String(data: $0, encoding: .isoLatin1) } ?? ""
            call.resolve(["status": status, "data": text])
        }.resume()
    }

    @objc func disconnect(_ call: CAPPluginCall) {
        if let ssid = currentSsid {
            NEHotspotConfigurationManager.shared.removeConfiguration(forSSID: ssid)
        }
        currentSsid = nil
        call.resolve()
    }
}

/// Lokale plugins i app-målet må registreres for hånd (Capacitor finner bare plugins fra npm-pakker selv).
class SkjoldBridgeViewController: CAPBridgeViewController {
    override func capacitorDidLoad() {
        bridge?.registerPluginInstance(SkjoldWifiPlugin())
    }
}
