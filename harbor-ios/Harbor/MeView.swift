import SwiftUI

struct MeView: View {
    @EnvironmentObject private var store: AppStore

    var body: some View {
        ZStack(alignment: .bottomTrailing) {
            ScrollView {
                if let session = store.session {
                    signedIn(session)
                } else {
                    guest
                }
            }
            CSButton { store.push(.chat(nil)) }
                .padding(.trailing, 20)
                .padding(.bottom, 12)
        }
        .harborRoot()
        .sheet(item: $store.authMode) { mode in
            AuthForm(mode: mode)
        }
    }

    private var guest: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text(store.t("Welcome to Harbor"))
                .font(.system(size: 26, weight: .bold))
                .foregroundStyle(HarborColor.navy)
                .padding(.top, 28)
            Text(store.t("Guest checkout OK · sign in to sync"))
                .font(.system(size: 14))
                .foregroundStyle(HarborColor.muted)
            LegalConsent()
            PrimaryButton(title: store.t("Sign in"), fill: HarborColor.navy) {
                store.authMode = .signIn
            }
            OutlineButton(title: store.t("Register")) {
                store.authMode = .register
            }
            SocialSignInButtons()
            Button(store.t("Help")) { store.push(.help) }
                .font(.system(size: 15, weight: .medium))
                .foregroundStyle(HarborColor.teal)
                .frame(maxWidth: .infinity)
                .buttonStyle(.plain)
            Text(store.t("You’re in the Harbor app · no install prompt"))
                .font(.system(size: 12))
                .foregroundStyle(HarborColor.muted)
                .frame(maxWidth: .infinity)
                .padding(.top, 28)
        }
        .padding(.horizontal, 20)
        .padding(.bottom, 80)
    }

    private func signedIn(_ session: Session) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 12) {
                Text(session.initials)
                    .font(.system(size: 16, weight: .bold))
                    .foregroundStyle(.white)
                    .frame(width: 48, height: 48)
                    .background(HarborColor.teal)
                    .clipShape(Circle())
                VStack(alignment: .leading, spacing: 2) {
                    Text(session.name)
                        .font(.system(size: 18, weight: .bold))
                        .foregroundStyle(.white)
                    Text(session.email)
                        .font(.system(size: 13))
                        .foregroundStyle(.white.opacity(0.8))
                    if let provider = session.providerTitle {
                        Text("Signed in with \(provider)")
                            .font(.system(size: 12))
                            .foregroundStyle(.white.opacity(0.75))
                    }
                }
                Spacer()
            }
            .padding(16)
            .background(HarborColor.navy)
            .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))

            VStack(alignment: .leading, spacing: 12) {
                HStack {
                    Text(store.t("My orders"))
                        .font(.system(size: 16, weight: .bold))
                        .foregroundStyle(HarborColor.navy)
                    Spacer()
                    Button(store.t("All ›")) { store.push(.orders(nil)) }
                        .font(.system(size: 13, weight: .medium))
                        .foregroundStyle(HarborColor.teal)
                }
                HStack {
                    orderStat(.toPay)
                    orderStat(.paid)
                    orderStat(.shipped)
                    orderStat(.returns)
                }
            }
            .padding(14)
            .background(Color.white)
            .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: 16, style: .continuous).stroke(HarborColor.line, lineWidth: 1))

            VStack(spacing: 0) {
                meRow(store.t("Wishlist ›")) { store.push(.wishlist) }
                divider
                meRow(store.t("Coupons · Rewards ›")) { store.push(.coupons) }
                divider
                meRow("\(store.t("Language")) ›") { store.push(.locale) }
                divider
                meRow("\(store.t("Addresses")) ›") { store.push(.addresses) }
                divider
                meRow("\(store.t("Payment methods")) ›") { store.push(.payments) }
                divider
                meRow(store.t("Help · Contact ›")) { store.push(.help) }
            }
            .background(Color.white)
            .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: 16, style: .continuous).stroke(HarborColor.line, lineWidth: 1))

            Text(store.t("You’re in the Harbor app · no install prompt"))
                .font(.system(size: 12))
                .foregroundStyle(HarborColor.muted)
                .frame(maxWidth: .infinity)
                .padding(.top, 12)

            Button(store.t("Sign out")) { store.signOut() }
                .font(.system(size: 13, weight: .medium))
                .foregroundStyle(HarborColor.muted)
                .frame(maxWidth: .infinity)
                .padding(.top, 8)
        }
        .padding(.horizontal, 16)
        .padding(.top, 8)
        .padding(.bottom, 88)
    }

    private func orderStat(_ status: OrderStatus) -> some View {
        Button {
            store.push(.orders(status))
        } label: {
            VStack(spacing: 4) {
                Text(store.t(status.title))
                    .font(.system(size: 12))
                    .foregroundStyle(HarborColor.muted)
                Text("\(store.count(status))")
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundStyle(HarborColor.navy)
            }
            .frame(maxWidth: .infinity)
        }
        .buttonStyle(.plain)
    }

    private func meRow(_ title: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack {
                Text(title)
                    .font(.system(size: 15))
                    .foregroundStyle(HarborColor.navy)
                Spacer()
            }
            .padding(.horizontal, 14)
            .frame(height: 48)
        }
        .buttonStyle(.plain)
    }

    private var divider: some View {
        Rectangle().fill(HarborColor.line).frame(height: 1).padding(.leading, 14)
    }
}

struct AuthForm: View {
    @EnvironmentObject private var store: AppStore
    var mode: AuthMode
    @State private var email = ""
    @State private var password = ""
    @State private var error: String?
    @State private var path = NavigationPath()
    @State private var detent: PresentationDetent = .medium

    var body: some View {
        NavigationStack(path: $path) {
            form
                .toolbar(.hidden, for: .navigationBar)
                .navigationDestination(for: InAppWebRoute.self) { route in
                    InAppWebScreen(url: route.url, title: route.title)
                        .environmentObject(store)
                }
        }
        .background(HarborColor.sand.ignoresSafeArea())
        .presentationDetents([.medium, .large], selection: $detent)
        .presentationDragIndicator(.visible)
    }

    private var form: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                if mode == .signIn {
                    Text(LegalUrls.displayName.uppercased())
                        .font(.system(size: 12, weight: .semibold))
                        .tracking(0.6)
                        .foregroundStyle(HarborColor.teal)
                }
                Text(mode == .signIn ? "Sign in" : "Create account")
                    .font(.system(size: 28, weight: .bold))
                    .foregroundStyle(HarborColor.navy)
                FieldBlock(label: "Email", text: $email, prompt: "you@email.com", keyboard: .emailAddress)
                FieldBlock(label: "Password", text: $password, prompt: "••••••••", secure: true)
                if let error {
                    Text(error)
                        .font(.system(size: 13))
                        .foregroundStyle(HarborColor.danger)
                }
                LegalConsent { url, title in
                    detent = .large
                    path.append(InAppWebRoute(url: url, title: title))
                }
                PrimaryButton(title: mode == .signIn ? "Sign in" : "Register", fill: HarborColor.navy) {
                    error = store.signIn(email: email, password: password)
                }
                Button(mode == .signIn ? "New here? Register" : "Already have an account? Sign in") {
                    store.authMode = mode == .signIn ? .register : .signIn
                }
                .font(.system(size: 13, weight: .medium))
                .foregroundStyle(HarborColor.teal)
                .buttonStyle(.plain)
                Text("or")
                    .font(.system(size: 12, weight: .medium))
                    .foregroundStyle(HarborColor.muted)
                    .frame(maxWidth: .infinity)
                SocialSignInButtons()
            }
            .padding(24)
        }
        .background(HarborColor.sand.ignoresSafeArea())
    }
}
