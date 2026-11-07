import UIKit

/// Haptic feedback used across the app. Generators are kept warm so taps feel immediate.
@MainActor
enum Haptics {
    private static let light = UIImpactFeedbackGenerator(style: .light)
    private static let medium = UIImpactFeedbackGenerator(style: .medium)
    private static let soft = UIImpactFeedbackGenerator(style: .soft)
    private static let selection = UISelectionFeedbackGenerator()
    private static let notification = UINotificationFeedbackGenerator()

    /// Button press.
    static func tap() { light.impactOccurred(intensity: 0.7); light.prepare() }
    /// Bigger action: play/pause, opening/closing the player.
    static func thump() { medium.impactOccurred(); medium.prepare() }
    /// Slider detent, tab change, chip/segment selection.
    static func tick() { selection.selectionChanged(); selection.prepare() }
    /// Soft bump when a drag crosses a threshold.
    static func bump() { soft.impactOccurred(); soft.prepare() }

    private static let rigid = UIImpactFeedbackGenerator(style: .rigid)
    private static let heavy = UIImpactFeedbackGenerator(style: .heavy)

    /// «Haptikk på glidebrytere» (Innstillinger). På som standard.
    static var slidersOn: Bool {
        get { UserDefaults.standard.object(forKey: "hapticSliders") as? Bool ?? true }
        set { UserDefaults.standard.set(newValue, forKey: "hapticSliders") }
    }

    /// Gjør generatorene klare når et drag starter, så første tikk kommer uten forsinkelse.
    static func prepareSlider() { selection.prepare(); rigid.prepare(); heavy.prepare() }

    /// Informativ haptikk for et trinn på en glidebryter (EQ i dB, volum i %):
    /// lett tikk per hele steg, tydelig klikk på/over nullpunktet, kraftig «stopp» når grensen nås.
    static func sliderStep(from old: Int, to new: Int, min lo: Int, max hi: Int, zero: Int? = 0) {
        guard slidersOn, old != new else { return }
        if new == lo || new == hi {
            heavy.impactOccurred(intensity: 1.0); heavy.prepare()
        } else if let z = zero, new == z || (old < z) != (new < z) && old != z {
            rigid.impactOccurred(intensity: 0.9); rigid.prepare()
        } else {
            selection.selectionChanged(); selection.prepare()
        }
    }

    /// Lett bekreftelse når man slipper glidebryteren.
    static func sliderRelease() { guard slidersOn else { return }; soft.impactOccurred(intensity: 0.5); soft.prepare() }

    static func success() { notification.notificationOccurred(.success) }
    static func warning() { notification.notificationOccurred(.warning) }
    static func error() { notification.notificationOccurred(.error) }
}
