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

    static func success() { notification.notificationOccurred(.success) }
    static func warning() { notification.notificationOccurred(.warning) }
    static func error() { notification.notificationOccurred(.error) }
}
