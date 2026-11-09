import AuthenticationServices
import CryptoKit
import SwiftUI
import UIKit

#if canImport(FacebookLogin)
import FacebookCore
import FacebookLogin
#endif

enum SocialProvider: String {
    case apple, facebook, x, instagram, email

    var title: String {
        switch self {
        case .apple: return "Apple"
        case .facebook: return "Facebook"
        case .x: return "X"
        case .instagram: return "Instagram"
        case .email: return "Email"
        }
    }

    var fallbackName: String {
        switch self {
        case .apple: return "Apple member"
        case .facebook: return "Facebook member"
        case .x: return "X member"
        case .instagram: return "Instagram member"
        case .email: return "Harbor member"
        }
    }
}

struct SocialProfile {
    var provider: SocialProvider
    var token: String
    var name: String?
    var email: String?
    var userID: String
}

enum SocialAuthError: LocalizedError {
    case cancelled
    case notConfigured(SocialProvider)
    case sdkMissing
    case failed(String)

    var errorDescription: String? {
        switch self {
        case .cancelled:
            return nil
        case .notConfigured(let provider):
            switch provider {
            case .facebook:
                return "Add FACEBOOK_APP_ID and FACEBOOK_CLIENT_TOKEN in Config/Debug.xcconfig."
            case .x:
                return "Add TWITTER_CLIENT_ID in Config/Debug.xcconfig. Redirect URI is harbor://oauth/x."
            case .instagram:
                return "Add FACEBOOK_APP_ID or INSTAGRAM_APP_ID in Config/Debug.xcconfig."
            case .apple:
                return "Select your Apple Team and turn on Sign in with Apple."
            case .email:
                return "Enter your email and password."
            }
        case .sdkMissing:
            return "Facebook Login SDK is not linked. The button stays in the app; add facebook-ios-sdk to enable it."
        case .failed(let message):
            return message
        }
    }
}

enum SocialConfig {
    static var facebookAppID: String { value("FacebookAppID") }
    static var facebookClientToken: String { value("FacebookClientToken") }
    static var twitterClientID: String { value("HarborTwitterClientID") }
    static var twitterRedirectURI: String {
        let raw = value("HarborTwitterRedirectURI")
        return raw.isEmpty ? "harbor://oauth/x" : raw
    }
    static var instagramAppID: String { value("HarborInstagramAppID") }
    static var instagramRedirectURI: String {
        let raw = value("HarborInstagramRedirectURI")
        return raw.isEmpty ? "harbor://oauth/instagram" : raw
    }

    static var isFacebookConfigured: Bool {
        configured(facebookAppID) && configured(facebookClientToken)
    }
    static var isTwitterConfigured: Bool { configured(twitterClientID) }
    static var isInstagramConfigured: Bool { configured(instagramAppID) }

    private static func value(_ key: String) -> String {
        let raw = Bundle.main.object(forInfoDictionaryKey: key) as? String ?? ""
        return raw.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private static func configured(_ raw: String) -> Bool {
        !raw.isEmpty && !raw.hasPrefix("YOUR_") && !raw.hasPrefix("$(")
    }
}

enum HarborLink {
    static func product(_ id: String) -> URL {
        let encoded = id.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? id
        return URL(string: "https://linkiip.com/p/\(encoded)?country=US")!
    }

    static func invite(_ code: String) -> URL {
        var components = URLComponents(string: "https://linkiip.com/")!
        components.queryItems = [URLQueryItem(name: "invite", value: code)]
        return components.url ?? URL(string: "https://linkiip.com/")!
    }
}

struct ActivitySheet: UIViewControllerRepresentable {
    var items: [Any]

    func makeUIViewController(context: Context) -> UIActivityViewController {
        let controller = UIActivityViewController(activityItems: items, applicationActivities: nil)
        if let popover = controller.popoverPresentationController {
            let window = Self.keyWindow
            popover.sourceView = window
            popover.sourceRect = CGRect(x: window?.bounds.midX ?? 0, y: window?.bounds.midY ?? 0, width: 1, height: 1)
            popover.permittedArrowDirections = []
        }
        return controller
    }

    func updateUIViewController(_ uiViewController: UIActivityViewController, context: Context) {}

    private static var keyWindow: UIWindow? {
        UIApplication.shared.connectedScenes
            .compactMap { $0 as? UIWindowScene }
            .flatMap(\.windows)
            .first { $0.isKeyWindow }
    }
}

final class SocialAuthController: NSObject, ObservableObject, ASWebAuthenticationPresentationContextProviding {
    private var webSession: ASWebAuthenticationSession?
    #if canImport(FacebookLogin)
    private let facebook = LoginManager()
    #endif

    func presentationAnchor(for session: ASWebAuthenticationSession) -> ASPresentationAnchor {
        let scenes = UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }
        if let window = scenes.flatMap(\.windows).first(where: \.isKeyWindow) {
            return window
        }
        if let scene = scenes.first {
            return UIWindow(windowScene: scene)
        }
        return ASPresentationAnchor()
    }

    static func consume(_ url: URL) -> Bool {
        #if canImport(FacebookLogin)
        guard SocialConfig.isFacebookConfigured else { return false }
        prepareFacebook()
        return ApplicationDelegate.shared.application(
            UIApplication.shared,
            open: url,
            sourceApplication: nil,
            annotation: nil
        )
        #else
        return false
        #endif
    }

    static func logout() {
        #if canImport(FacebookLogin)
        LoginManager().logOut()
        #endif
    }

    func signInWithX() async throws -> SocialProfile {
        guard SocialConfig.isTwitterConfigured else { throw SocialAuthError.notConfigured(.x) }
        let verifier = PKCE.verifier()
        let challenge = PKCE.challenge(for: verifier)
        let state = UUID().uuidString
        guard let url = Self.authorizeURL(
            base: "https://twitter.com/i/oauth2/authorize",
            items: [
                URLQueryItem(name: "response_type", value: "code"),
                URLQueryItem(name: "client_id", value: SocialConfig.twitterClientID),
                URLQueryItem(name: "redirect_uri", value: SocialConfig.twitterRedirectURI),
                URLQueryItem(name: "scope", value: "tweet.read users.read"),
                URLQueryItem(name: "state", value: state),
                URLQueryItem(name: "code_challenge", value: challenge),
                URLQueryItem(name: "code_challenge_method", value: "S256")
            ]
        ) else {
            throw SocialAuthError.failed("Could not start X sign-in.")
        }
        let code = try await webCode(url: url, expectedState: state)
        let access = await Self.exchangeX(code: code, verifier: verifier)
        let account = await Self.xAccount(accessToken: access)
        return SocialProfile(
            provider: .x,
            token: access ?? code,
            name: account?.name,
            email: nil,
            userID: account?.id ?? "x"
        )
    }

    func signInWithInstagram() async throws -> SocialProfile {
        if SocialConfig.isInstagramConfigured {
            guard let url = Self.authorizeURL(
                base: "https://www.instagram.com/oauth/authorize",
                items: [
                    URLQueryItem(name: "client_id", value: SocialConfig.instagramAppID),
                    URLQueryItem(name: "redirect_uri", value: SocialConfig.instagramRedirectURI),
                    URLQueryItem(name: "response_type", value: "code"),
                    URLQueryItem(name: "scope", value: "instagram_business_basic"),
                    URLQueryItem(name: "enable_fb_login", value: "1")
                ]
            ) else {
                throw SocialAuthError.failed("Could not start Instagram sign-in.")
            }
            let code = try await webCode(url: url, expectedState: nil)
            return SocialProfile(provider: .instagram, token: code, name: nil, email: nil, userID: "instagram")
        }
        return try await signInWithFacebook(as: .instagram)
    }

    func signInWithFacebook(as provider: SocialProvider) async throws -> SocialProfile {
        guard SocialConfig.isFacebookConfigured else { throw SocialAuthError.notConfigured(provider) }
        #if canImport(FacebookLogin)
        Self.prepareFacebook()
        let viewController = Self.topViewController()
        return try await withCheckedThrowingContinuation { continuation in
            var resumed = false
            facebook.logIn(permissions: ["public_profile", "email"], from: viewController) { result, error in
                guard !resumed else { return }
                resumed = true
                if let error {
                    continuation.resume(throwing: SocialAuthError.failed(error.localizedDescription))
                    return
                }
                if result?.isCancelled == true {
                    continuation.resume(throwing: SocialAuthError.cancelled)
                    return
                }
                let access = result?.token
                let jwt = result?.authenticationToken?.tokenString
                let token = access?.tokenString ?? jwt ?? ""
                guard !token.isEmpty else {
                    continuation.resume(throwing: SocialAuthError.failed("Facebook did not return a token."))
                    return
                }
                let profile = Profile.current
                let userID: String
                if let id = access?.userID {
                    userID = String(describing: id)
                } else if let id = profile?.userID {
                    userID = String(describing: id)
                } else {
                    userID = provider.rawValue
                }
                continuation.resume(returning: SocialProfile(
                    provider: provider,
                    token: token,
                    name: profile?.name,
                    email: profile?.email,
                    userID: userID
                ))
            }
        }
        #else
        throw SocialAuthError.sdkMissing
        #endif
    }

    private func webCode(url: URL, expectedState: String?) async throws -> String {
        try await withCheckedThrowingContinuation { continuation in
            let session = ASWebAuthenticationSession(url: url, callbackURLScheme: "harbor") { callback, error in
                if let error = error as? ASWebAuthenticationSessionError, error.code == .canceledLogin {
                    continuation.resume(throwing: SocialAuthError.cancelled)
                    return
                }
                if let error {
                    continuation.resume(throwing: SocialAuthError.failed(error.localizedDescription))
                    return
                }
                guard let callback else {
                    continuation.resume(throwing: SocialAuthError.failed("The sign-in window closed without a code."))
                    return
                }
                let items = URLComponents(url: callback, resolvingAgainstBaseURL: false)?.queryItems ?? []
                if let expectedState {
                    let state = items.first { $0.name == "state" }?.value
                    guard state == expectedState else {
                        continuation.resume(throwing: SocialAuthError.failed("Sign-in state did not match."))
                        return
                    }
                }
                if let code = items.first(where: { $0.name == "code" })?.value, !code.isEmpty {
                    continuation.resume(returning: code)
                } else {
                    let reason = items.first { $0.name == "error_description" }?.value
                        ?? items.first { $0.name == "error" }?.value
                        ?? "No authorization code."
                    continuation.resume(throwing: SocialAuthError.failed(reason))
                }
            }
            session.presentationContextProvider = self
            session.prefersEphemeralWebBrowserSession = false
            webSession = session
            if !session.start() {
                continuation.resume(throwing: SocialAuthError.failed("Could not open the sign-in window."))
            }
        }
    }

    private static func authorizeURL(base: String, items: [URLQueryItem]) -> URL? {
        var components = URLComponents(string: base)
        components?.queryItems = items
        return components?.url
    }

    private static func exchangeX(code: String, verifier: String) async -> String? {
        guard let url = URL(string: "https://api.twitter.com/2/oauth2/token") else { return nil }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.timeoutInterval = 8
        request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        var components = URLComponents()
        components.queryItems = [
            URLQueryItem(name: "grant_type", value: "authorization_code"),
            URLQueryItem(name: "code", value: code),
            URLQueryItem(name: "redirect_uri", value: SocialConfig.twitterRedirectURI),
            URLQueryItem(name: "client_id", value: SocialConfig.twitterClientID),
            URLQueryItem(name: "code_verifier", value: verifier)
        ]
        request.httpBody = components.percentEncodedQuery?.data(using: .utf8)
        guard let (data, response) = try? await URLSession.shared.data(for: request),
              let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode),
              let json = try? JSONDecoder().decode(XToken.self, from: data) else {
            return nil
        }
        return json.access_token
    }

    private static func xAccount(accessToken: String?) async -> XAccount? {
        guard let accessToken, let url = URL(string: "https://api.twitter.com/2/users/me") else { return nil }
        var request = URLRequest(url: url)
        request.timeoutInterval = 8
        request.setValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")
        guard let (data, response) = try? await URLSession.shared.data(for: request),
              let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode),
              let json = try? JSONDecoder().decode(XMe.self, from: data) else {
            return nil
        }
        return json.data
    }

    #if canImport(FacebookLogin)
    private static func prepareFacebook() {
        Settings.shared.appID = SocialConfig.facebookAppID
        Settings.shared.clientToken = SocialConfig.facebookClientToken
        Settings.shared.isAutoLogAppEventsEnabled = false
        Settings.shared.isAdvertiserIDCollectionEnabled = false
    }

    private static func topViewController() -> UIViewController? {
        let root = UIApplication.shared.connectedScenes
            .compactMap { $0 as? UIWindowScene }
            .flatMap(\.windows)
            .first { $0.isKeyWindow }?
            .rootViewController
        return deepest(root)
    }

    private static func deepest(_ controller: UIViewController?) -> UIViewController? {
        if let presented = controller?.presentedViewController {
            return deepest(presented)
        }
        if let navigation = controller as? UINavigationController {
            return deepest(navigation.visibleViewController)
        }
        if let tab = controller as? UITabBarController {
            return deepest(tab.selectedViewController)
        }
        return controller
    }
    #endif
}

private enum PKCE {
    static func verifier() -> String {
        var bytes = [UInt8](repeating: 0, count: 32)
        _ = SecRandomCopyBytes(kSecRandomDefault, bytes.count, &bytes)
        return Data(bytes).base64URL()
    }

    static func challenge(for verifier: String) -> String {
        let digest = SHA256.hash(data: Data(verifier.utf8))
        return Data(digest).base64URL()
    }
}

private extension Data {
    func base64URL() -> String {
        base64EncodedString()
            .replacingOccurrences(of: "+", with: "-")
            .replacingOccurrences(of: "/", with: "_")
            .replacingOccurrences(of: "=", with: "")
    }
}

private struct XToken: Decodable { let access_token: String }
private struct XAccount: Decodable { let id: String; let name: String; let username: String }
private struct XMe: Decodable { let data: XAccount }

struct SocialSignInButtons: View {
    @EnvironmentObject private var store: AppStore
    @StateObject private var auth = SocialAuthController()
    @State private var message: String?
    @State private var busy = false

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            SignInWithAppleButton(.signIn) { request in
                request.requestedScopes = [.fullName, .email]
            } onCompletion: { result in
                handleApple(result)
            }
            .signInWithAppleButtonStyle(.black)
            .frame(maxWidth: .infinity)
            .frame(height: 44)
            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
            .disabled(busy)

            providerButton("Facebook") { Task { await run(.facebook) } }
            providerButton("X") { Task { await run(.x) } }

            if busy {
                Text("Signing in…")
                    .font(.system(size: 12))
                    .foregroundStyle(HarborColor.muted)
            }
            if let message {
                Text(message)
                    .font(.system(size: 12))
                    .foregroundStyle(HarborColor.danger)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private func providerButton(_ title: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(title)
                .font(.system(size: 16, weight: .semibold))
                .foregroundStyle(HarborColor.navy)
                .frame(maxWidth: .infinity)
                .frame(height: 44)
                .background(Color.white)
                .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: 12, style: .continuous)
                        .stroke(HarborColor.line, lineWidth: 1)
                )
        }
        .buttonStyle(.plain)
        .disabled(busy)
    }

    private func handleApple(_ result: Result<ASAuthorization, Error>) {
        switch result {
        case .failure(let error):
            if let authError = error as? ASAuthorizationError, authError.code == .canceled {
                message = nil
                return
            }
            message = "\(error.localizedDescription) Select your Apple Team and turn on Sign in with Apple."
        case .success(let authorization):
            guard let credential = authorization.credential as? ASAuthorizationAppleIDCredential else {
                message = SocialAuthError.failed("Apple did not return a credential.").errorDescription
                return
            }
            let token = credential.identityToken.flatMap { String(data: $0, encoding: .utf8) } ?? credential.user
            let parts = [credential.fullName?.givenName, credential.fullName?.familyName].compactMap { $0 }
            let name = parts.joined(separator: " ")
            let profile = SocialProfile(
                provider: .apple,
                token: token,
                name: name.isEmpty ? nil : name,
                email: credential.email,
                userID: credential.user
            )
            Task { await store.finishSocial(profile) }
        }
    }

    private func run(_ provider: SocialProvider) async {
        busy = true
        message = nil
        defer { busy = false }
        do {
            let profile: SocialProfile
            switch provider {
            case .facebook:
                profile = try await auth.signInWithFacebook(as: .facebook)
            case .x:
                profile = try await auth.signInWithX()
            case .instagram:
                profile = try await auth.signInWithInstagram()
            default:
                return
            }
            await store.finishSocial(profile)
        } catch SocialAuthError.cancelled {
            message = nil
        } catch {
            message = error.localizedDescription
        }
    }
}
