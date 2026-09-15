import UIKit

@main
final class AppDelegate: UIResponder, UIApplicationDelegate {
    var window: UIWindow?

    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        let viewController = UIViewController()
        viewController.view.backgroundColor = UIColor(red: 0.035, green: 0.13, blue: 0.16, alpha: 1)

        let title = UILabel()
        title.translatesAutoresizingMaskIntoConstraints = false
        title.text = FixtureStatus.ready
        title.textColor = .white
        title.font = .systemFont(ofSize: 30, weight: .bold)
        title.textAlignment = .center
        title.numberOfLines = 0
        title.accessibilityIdentifier = "fixture.status.ready"

        let detail = UILabel()
        detail.translatesAutoresizingMaskIntoConstraints = false
        detail.text = FixtureStatus.detail
        detail.textColor = UIColor(red: 0.55, green: 0.88, blue: 0.82, alpha: 1)
        detail.font = .systemFont(ofSize: 17, weight: .medium)
        detail.textAlignment = .center
        detail.numberOfLines = 0
        detail.accessibilityIdentifier = "fixture.detail.verified"

        let stack = UIStackView(arrangedSubviews: [title, detail])
        stack.translatesAutoresizingMaskIntoConstraints = false
        stack.axis = .vertical
        stack.alignment = .fill
        stack.spacing = 18
        viewController.view.addSubview(stack)

        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: viewController.view.safeAreaLayoutGuide.leadingAnchor, constant: 28),
            stack.trailingAnchor.constraint(equalTo: viewController.view.safeAreaLayoutGuide.trailingAnchor, constant: -28),
            stack.centerYAnchor.constraint(equalTo: viewController.view.centerYAnchor),
        ])

        let window = UIWindow(frame: UIScreen.main.bounds)
        window.rootViewController = viewController
        window.makeKeyAndVisible()
        self.window = window
        return true
    }
}
