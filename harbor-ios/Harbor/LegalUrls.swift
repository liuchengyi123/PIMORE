import SwiftUI
import UIKit
import WebKit

/// Live compliance pages for Pimo. Bundle id stays `com.harbor.app`.
/// Defaults are the shop’s canonical paths. `GET /api/legal` replaces any field it returns.
enum LegalUrls {
    static let displayName = "Pimo"
    static let webOrigin = URL(string: "https://linkiip.com")!
    static let endpoint = URL(string: "https://linkiip.com/api/legal")!
    /// Shop-hosted card vault. Brand and last 4 only; the app never sends a full card number.
    static let accountPayments = URL(string: "https://linkiip.com/account/payments")!
    static let accountAddresses = URL(string: "https://linkiip.com/account/addresses")!

    static func load(session: URLSession = .shared) async -> ComplianceConfig {
        var request = URLRequest(url: endpoint)
        request.timeoutInterval = 6
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        guard let (data, response) = try? await session.data(for: request),
              let http = response as? HTTPURLResponse,
              (200...299).contains(http.statusCode) else {
            return .fallback
        }
        var body = data
        if body.starts(with: [0xEF, 0xBB, 0xBF]) {
            body.removeFirst(3)
        }
        guard let payload = try? JSONDecoder().decode(LegalPayload.self, from: body) else {
            return .fallback
        }
        return payload.applied(to: .fallback)
    }

    /// Absolute http(s) URLs win. Paths are resolved against https://linkiip.com.
    static func resolve(_ raw: String?, fallback: URL) -> URL {
        let trimmed = raw?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        guard !trimmed.isEmpty else { return fallback }
        if let url = URL(string: trimmed), let scheme = url.scheme?.lowercased(), scheme == "https" || scheme == "http" {
            return url
        }
        let path = trimmed.hasPrefix("/") ? trimmed : "/" + trimmed
        return URL(string: webOrigin.absoluteString + path) ?? fallback
    }
}

struct ComplianceConfig: Equatable {
    var brand: String
    var supportEmail: String
    var help: URL
    var privacy: URL
    var terms: URL
    var shipping: URL
    var contact: URL
    var accountDeletion: URL
    /// The legal payload has no returns field. This stays on Help unless `/api/legal` sends `returns`.
    var returns: URL

    static let fallback = ComplianceConfig(
        brand: LegalUrls.displayName,
        supportEmail: "support@linkiip.com",
        help: URL(string: "https://linkiip.com/help")!,
        privacy: URL(string: "https://linkiip.com/policies/privacy")!,
        terms: URL(string: "https://linkiip.com/policies/terms")!,
        shipping: URL(string: "https://linkiip.com/policies/shipping")!,
        contact: URL(string: "https://linkiip.com/contact")!,
        accountDeletion: URL(string: "https://linkiip.com/help#account-deletion")!,
        returns: URL(string: "https://linkiip.com/help")!
    )

    func url(for page: String) -> URL {
        switch page {
        case "privacy": return privacy
        case "terms": return terms
        case "shipping": return shipping
        case "contact": return contact
        case "returns": return returns
        case "account-deletion", "account_deletion": return accountDeletion
        default: return help
        }
    }
}

private struct LegalPayload: Decodable {
    var brand: String?
    var supportEmail: String?
    var help: String?
    var privacy: String?
    var terms: String?
    var shipping: String?
    var contact: String?
    var accountDeletion: String?
    var returns: String?

    enum CodingKeys: String, CodingKey {
        case brand
        case supportEmail = "support_email"
        case help, privacy, terms, shipping, contact, returns
        case accountDeletion = "account_deletion"
    }

    func applied(to base: ComplianceConfig) -> ComplianceConfig {
        ComplianceConfig(
            brand: filled(brand) ?? base.brand,
            supportEmail: filled(supportEmail) ?? base.supportEmail,
            help: LegalUrls.resolve(help, fallback: base.help),
            privacy: LegalUrls.resolve(privacy, fallback: base.privacy),
            terms: LegalUrls.resolve(terms, fallback: base.terms),
            shipping: LegalUrls.resolve(shipping, fallback: base.shipping),
            contact: LegalUrls.resolve(contact, fallback: base.contact),
            accountDeletion: LegalUrls.resolve(accountDeletion, fallback: base.accountDeletion),
            returns: LegalUrls.resolve(returns, fallback: base.returns)
        )
    }

    private func filled(_ raw: String?) -> String? {
        let trimmed = raw?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        return trimmed.isEmpty ? nil : trimmed
    }
}

/// Shop page inside the app. The bar is the same native back control as the rest of Me.
/// http(s) navigations stay in this WKWebView. X sign-in still uses `ASWebAuthenticationSession`.
struct InAppWebScreen: View {
    @EnvironmentObject private var store: AppStore
    var url: URL
    var title: String
    @State private var progress: Double = 0
    @State private var failed = false
    @State private var reloadID = 0

    var body: some View {
        VStack(spacing: 0) {
            HarborTitleBar(title: title)
            ZStack {
                InAppWebView(url: url, reloadID: reloadID, progress: $progress, failed: $failed)
                if failed {
                    VStack(spacing: 12) {
                        Text(store.t("Could not open this page."))
                            .font(.system(size: 15))
                            .foregroundStyle(HarborColor.muted)
                            .multilineTextAlignment(.center)
                        Button {
                            failed = false
                            progress = 0
                            reloadID += 1
                        } label: {
                            Text(store.t("Retry"))
                                .font(.system(size: 16, weight: .semibold))
                                .foregroundStyle(.white)
                                .padding(.horizontal, 22)
                                .frame(height: 41)
                                .background(HarborColor.navy)
                                .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                        }
                        .buttonStyle(.plain)
                    }
                    .padding(24)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(HarborColor.sand)
                }
            }
            .overlay(alignment: .top) {
                if !failed, progress < 1 {
                    ProgressView(value: max(progress, 0.05))
                        .progressViewStyle(.linear)
                        .tint(HarborColor.teal)
                }
            }
        }
        .harborScreen()
        .navigationBarBackButtonHidden(true)
        .accessibilityElement(children: .contain)
        .onChange(of: url) { _ in
            failed = false
            progress = 0
        }
    }
}

struct InAppWebView: UIViewRepresentable {
    var url: URL
    var reloadID: Int
    @Binding var progress: Double
    @Binding var failed: Bool

    func makeCoordinator() -> Coordinator {
        Coordinator(parent: self)
    }

    func makeUIView(context: Context) -> WKWebView {
        let preferences = WKWebpagePreferences()
        preferences.allowsContentJavaScript = true
        let configuration = WKWebViewConfiguration()
        configuration.defaultWebpagePreferences = preferences
        configuration.preferences.javaScriptCanOpenWindowsAutomatically = true
        configuration.websiteDataStore = .default()
        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.navigationDelegate = context.coordinator
        webView.uiDelegate = context.coordinator
        webView.allowsLinkPreview = false
        webView.allowsBackForwardNavigationGestures = false
        webView.isOpaque = true
        webView.backgroundColor = .white
        webView.scrollView.backgroundColor = .white
        webView.underPageBackgroundColor = .white
        context.coordinator.attach(webView)
        context.coordinator.load(url, reloadID: reloadID, in: webView)
        return webView
    }

    func updateUIView(_ webView: WKWebView, context: Context) {
        context.coordinator.parent = self
        if context.coordinator.loadedURL != url || context.coordinator.reloadID != reloadID {
            context.coordinator.load(url, reloadID: reloadID, in: webView)
        }
    }

    static func dismantleUIView(_ webView: WKWebView, coordinator: Coordinator) {
        coordinator.observation?.invalidate()
        webView.navigationDelegate = nil
        webView.uiDelegate = nil
        webView.stopLoading()
    }

    final class Coordinator: NSObject, WKNavigationDelegate, WKUIDelegate {
        var parent: InAppWebView
        var loadedURL: URL?
        var reloadID = 0
        var active: WKNavigation?
        var observation: NSKeyValueObservation?

        init(parent: InAppWebView) {
            self.parent = parent
        }

        func attach(_ webView: WKWebView) {
            observation = webView.observe(\.estimatedProgress, options: [.new]) { [weak self] webView, _ in
                let value = webView.estimatedProgress
                DispatchQueue.main.async {
                    self?.parent.progress = value
                }
            }
        }

        func load(_ url: URL, reloadID: Int, in webView: WKWebView) {
            loadedURL = url
            self.reloadID = reloadID
            active = webView.load(URLRequest(url: url))
        }

        private func isCurrent(_ navigation: WKNavigation?) -> Bool {
            guard let active, let navigation else { return true }
            return navigation === active
        }

        func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
            if navigationAction.shouldPerformDownload {
                decisionHandler(.cancel)
                return
            }
            guard let target = navigationAction.request.url else {
                decisionHandler(.allow)
                return
            }
            let scheme = target.scheme?.lowercased() ?? ""
            if scheme == "http" || scheme == "https" || scheme == "about" {
                decisionHandler(.allow)
                return
            }
            decisionHandler(.cancel)
            if scheme == "mailto" || scheme == "tel" {
                UIApplication.shared.open(target)
            }
        }

        func webView(_ webView: WKWebView, createWebViewWith configuration: WKWebViewConfiguration, for navigationAction: WKNavigationAction, windowFeatures: WKWindowFeatures) -> WKWebView? {
            if let target = navigationAction.request.url, let scheme = target.scheme?.lowercased(), scheme == "http" || scheme == "https" {
                active = webView.load(URLRequest(url: target))
            }
            return nil
        }

        func webView(_ webView: WKWebView, contextMenuConfigurationForElement elementInfo: WKContextMenuElementInfo, completionHandler: @escaping (UIContextMenuConfiguration?) -> Void) {
            completionHandler(nil)
        }

        func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
            guard isCurrent(navigation) else { return }
            parent.progress = 1
            parent.failed = false
        }

        func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
            note(navigation, error)
        }

        func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
            note(navigation, error)
        }

        private func note(_ navigation: WKNavigation?, _ error: Error) {
            guard isCurrent(navigation) else { return }
            let ns = error as NSError
            if ns.domain == NSURLErrorDomain && ns.code == NSURLErrorCancelled { return }
            parent.failed = true
        }
    }
}

/// “By continuing you agree to Terms and Privacy”. Each document stays in the in-app web screen.
struct LegalConsent: View {
    @EnvironmentObject private var store: AppStore
    var open: ((URL, String) -> Void)? = nil

    var body: some View {
        Text(consent)
            .font(.system(size: 12))
            .foregroundStyle(HarborColor.muted)
            .tint(HarborColor.teal)
            .multilineTextAlignment(.center)
            .frame(maxWidth: .infinity)
            .environment(\.openURL, OpenURLAction { url in
                let title = title(for: url)
                if let open {
                    open(url, title)
                } else {
                    store.push(.inAppWeb(InAppWebRoute(url: url, title: title)))
                }
                return .handled
            })
            .task { await store.loadLegal() }
    }

    private func title(for url: URL) -> String {
        let path = url.path.lowercased()
        if path.contains("terms") { return store.t("Terms") }
        if path.contains("privacy") { return store.t("Privacy") }
        if path.contains("shipping") { return store.t("Shipping") }
        if path.contains("contact") { return store.t("Contact / Chat") }
        return store.t("Help")
    }

    private var consent: AttributedString {
        let sentence = store.t("By continuing you agree to [[terms]] and [[privacy]].")
        return LegalConsentText.make(
            sentence: sentence,
            terms: store.t("Terms"),
            privacy: store.t("Privacy"),
            termsURL: store.legal.terms,
            privacyURL: store.legal.privacy
        )
    }
}

enum LegalConsentText {
    static func make(sentence: String, terms: String, privacy: String, termsURL: URL, privacyURL: URL) -> AttributedString {
        var output = AttributedString()
        var rest = sentence[...]
        while let start = rest.range(of: "[[") {
            output.append(AttributedString(String(rest[..<start.lowerBound])))
            guard let end = rest.range(of: "]]", range: start.lowerBound..<rest.endIndex) else {
                output.append(AttributedString(String(rest)))
                return output
            }
            let token = String(rest[start.lowerBound..<end.upperBound])
            if token == "[[terms]]" {
                output.append(link(terms, url: termsURL))
            } else if token == "[[privacy]]" {
                output.append(link(privacy, url: privacyURL))
            } else {
                output.append(AttributedString(token))
            }
            rest = rest[end.upperBound...]
        }
        output.append(AttributedString(String(rest)))
        return output
    }

    private static func link(_ label: String, url: URL) -> AttributedString {
        var text = AttributedString(label)
        text.link = url
        text.underlineStyle = .single
        text.foregroundColor = Color(red: 14 / 255, green: 116 / 255, blue: 144 / 255)
        return text
    }
}
