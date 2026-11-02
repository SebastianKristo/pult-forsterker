import SwiftUI
import VisionKit
import Vision
import AVFoundation

/// Camera feed for the QR step (DataScannerViewController). The gold frame and scan line are drawn on top in SwiftUI.
struct QRScannerView: UIViewControllerRepresentable {
    let onFound: (String) -> Void

    /// Kamera finnes og VisionKit støtter skanning. (isAvailable er false før brukeren har gitt kameratilgang –
    /// derfor sjekkes ikke den her; tilgangen spørres om i requestAccess().)
    static var isAvailable: Bool { DataScannerViewController.isSupported }

    /// Spør om kameratilgang (første gang) – true når skanneren kan brukes.
    static func requestAccess() async -> Bool {
        guard DataScannerViewController.isSupported else { return false }
        switch AVCaptureDevice.authorizationStatus(for: .video) {
        case .authorized: return true
        case .notDetermined: return await AVCaptureDevice.requestAccess(for: .video)
        default: return false
        }
    }

    func makeUIViewController(context: Context) -> DataScannerViewController {
        let vc = DataScannerViewController(recognizedDataTypes: [.barcode(symbologies: [.qr])],
                                           qualityLevel: .balanced,
                                           recognizesMultipleItems: false,
                                           isHighFrameRateTrackingEnabled: false,
                                           isHighlightingEnabled: false)
        vc.delegate = context.coordinator
        return vc
    }

    /// startScanning() før visningen er i vinduet feiler stille – start (på nytt) her.
    func updateUIViewController(_ vc: DataScannerViewController, context: Context) {
        guard !vc.isScanning else { return }
        DispatchQueue.main.async { if !vc.isScanning { try? vc.startScanning() } }
    }

    static func dismantleUIViewController(_ vc: DataScannerViewController, coordinator: Coordinator) {
        vc.stopScanning()
    }

    func makeCoordinator() -> Coordinator { Coordinator(onFound: onFound) }

    final class Coordinator: NSObject, DataScannerViewControllerDelegate {
        let onFound: (String) -> Void
        var done = false
        init(onFound: @escaping (String) -> Void) { self.onFound = onFound }

        func dataScanner(_ dataScanner: DataScannerViewController, didAdd addedItems: [RecognizedItem], allItems: [RecognizedItem]) {
            for item in addedItems {
                if case let .barcode(code) = item, let s = code.payloadStringValue, !done {
                    done = true
                    DispatchQueue.main.async { self.onFound(s) }
                    return
                }
            }
        }
    }
}
