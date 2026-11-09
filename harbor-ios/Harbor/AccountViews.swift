import SwiftUI
import UIKit

struct LocaleView: View {
    @EnvironmentObject private var store: AppStore

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 10) {
                HarborTitleBar(title: store.t("Language"))
                ForEach(HarborLanguage.pickerOrder) { item in
                    Button {
                        store.setLanguage(item)
                    } label: {
                        HStack {
                            Text(item.endonym)
                                .font(.system(size: 16, weight: .semibold))
                                .foregroundStyle(HarborColor.navy)
                            Spacer()
                            if store.language == item {
                                Image(systemName: "checkmark")
                                    .foregroundStyle(HarborColor.teal)
                            }
                        }
                        .padding(14)
                        .background(Color.white)
                        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                        .overlay(RoundedRectangle(cornerRadius: 14, style: .continuous).stroke(HarborColor.line, lineWidth: 1))
                    }
                    .buttonStyle(.plain)
                    .padding(.horizontal, 16)
                }
                HStack {
                    Text(store.t("Currency"))
                        .font(.system(size: 16, weight: .semibold))
                        .foregroundStyle(HarborColor.navy)
                    Spacer()
                    Text(store.currency.code)
                        .font(.system(size: 15, weight: .semibold))
                        .foregroundStyle(HarborColor.teal)
                }
                .padding(14)
                .background(Color.white)
                .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                .overlay(RoundedRectangle(cornerRadius: 14, style: .continuous).stroke(HarborColor.line, lineWidth: 1))
                .padding(.horizontal, 16)
                Text(store.t("Currency follows your location. Changing language does not change prices."))
                    .font(.system(size: 12))
                    .foregroundStyle(HarborColor.muted)
                    .padding(.horizontal, 16)
                    .padding(.top, 4)
            }
        }
        .harborScreen()
    }
}

struct WishlistView: View {
    @EnvironmentObject private var store: AppStore

    private var items: [Product] {
        store.wishlist.compactMap { store.product($0) }
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                HarborTitleBar(title: "Wishlist")
                if items.isEmpty {
                    empty("Save pieces with the heart on a product.")
                } else {
                    ProductGrid(products: items)
                        .padding(.horizontal, 16)
                }
            }
            .padding(.bottom, 24)
        }
        .harborScreen()
    }
}

struct CouponsView: View {
    @EnvironmentObject private var store: AppStore

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                HarborTitleBar(title: "Coupons", backHome: true)
                ForEach(store.coupons) { coupon in
                    HStack(alignment: .center, spacing: 12) {
                        Text(store.money(coupon.amount))
                            .font(.system(size: 28, weight: .bold))
                            .foregroundStyle(HarborColor.amber)
                            .frame(width: 88)
                        VStack(alignment: .leading, spacing: 4) {
                            Text(coupon.code)
                                .font(.system(size: 16, weight: .bold))
                                .foregroundStyle(HarborColor.navy)
                            Text(coupon.detail)
                                .font(.system(size: 13))
                                .foregroundStyle(HarborColor.muted)
                        }
                        Spacer()
                    }
                    .padding(16)
                    .background(Color.white)
                    .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
                    .overlay(RoundedRectangle(cornerRadius: 16, style: .continuous).stroke(HarborColor.line, lineWidth: 1))
                    .padding(.horizontal, 16)
                }
                Text("Apply WELCOME5 at checkout on orders over $20.")
                    .font(.system(size: 12))
                    .foregroundStyle(HarborColor.muted)
                    .padding(.horizontal, 16)
            }
        }
        .harborScreen()
    }
}

struct BalanceView: View {
    @EnvironmentObject private var store: AppStore
    @State private var withdrawNote = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                HarborTitleBar(title: "Balance", backHome: true)
                VStack(alignment: .leading, spacing: 8) {
                    Text("Available")
                        .font(.system(size: 13))
                        .foregroundStyle(HarborColor.muted)
                    Text(store.money(store.balance))
                        .font(.system(size: 34, weight: .bold))
                        .foregroundStyle(HarborColor.navy)
                    Button("Withdraw") { withdrawNote = true }
                        .font(.system(size: 16, weight: .semibold))
                        .foregroundStyle(.white)
                        .padding(.horizontal, 16)
                        .frame(height: 41)
                        .background(HarborColor.navy)
                        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                        .padding(.top, 6)
                }
                .padding(20)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color.white)
                .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
                .overlay(RoundedRectangle(cornerRadius: 16, style: .continuous).stroke(HarborColor.line, lineWidth: 1))
                .padding(.horizontal, 16)

                Button {
                    store.claimCheckIn()
                } label: {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Daily check-in")
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundStyle(HarborColor.navy)
                        Text(store.checkedInToday
                             ? "Day \(store.streak) streak · claimed today"
                             : "Day \(max(store.streak, 0)) streak · tap to claim")
                            .font(.system(size: 13))
                            .foregroundStyle(HarborColor.muted)
                    }
                    .padding(15)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(Color.white)
                    .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
                    .overlay(RoundedRectangle(cornerRadius: 16, style: .continuous).stroke(HarborColor.line, lineWidth: 1))
                }
                .buttonStyle(.plain)
                .padding(.horizontal, 16)
                .disabled(store.checkedInToday)
            }
        }
        .harborScreen()
        .alert("Withdrawal is a preview in this build. No funds move.", isPresented: $withdrawNote) {
            Button("OK", role: .cancel) {}
        }
    }
}

struct InviteView: View {
    @EnvironmentObject private var store: AppStore
    @State private var copied = false
    @State private var sharing = false
    private let code = "HARBOR-AM7"

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                HarborTitleBar(title: "Invite friends", backHome: true)
                VStack(alignment: .leading, spacing: 8) {
                    Text("Earn rewards")
                        .font(.system(size: 16, weight: .semibold))
                        .foregroundStyle(HarborColor.navy)
                    Text(code)
                        .font(.system(size: 28, weight: .bold))
                        .foregroundStyle(HarborColor.teal)
                    Text("Share your code. Rewards land in Balance after a friend orders.")
                        .font(.system(size: 13))
                        .foregroundStyle(HarborColor.muted)
                }
                .padding(16)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color.white)
                .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
                .overlay(RoundedRectangle(cornerRadius: 16, style: .continuous).stroke(HarborColor.line, lineWidth: 1))
                .padding(.horizontal, 16)
                PrimaryButton(title: copied ? "Copied" : "Copy invite link", fill: HarborColor.navy) {
                    UIPasteboard.general.string = HarborLink.invite(code).absoluteString
                    copied = true
                }
                .padding(.horizontal, 16)
                OutlineButton(title: "Share") { sharing = true }
                    .padding(.horizontal, 16)
            }
        }
        .harborScreen()
        .sheet(isPresented: $sharing) {
            ActivitySheet(items: [
                "Join me on Harbor",
                HarborLink.invite(code)
            ])
        }
    }
}

struct AddressesView: View {
    var body: some View {
        AccountPortalView(
            titleKey: "Addresses",
            emptyKey: "No saved addresses",
            noteKey: "A saved address can be used at checkout.",
            actionKey: "Manage addresses",
            symbol: "mappin.and.ellipse",
            destination: LegalUrls.accountAddresses
        )
    }
}

struct HistoryView: View {
    @EnvironmentObject private var store: AppStore

    private var items: [Product] { store.history.compactMap { store.product($0) } }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                HarborTitleBar(title: "Browsing history")
                if items.isEmpty {
                    empty("Products you open show up here.")
                } else {
                    ProductGrid(products: items)
                        .padding(.horizontal, 16)
                }
            }
            .padding(.bottom, 24)
        }
        .harborScreen()
    }
}

struct CompareView: View {
    @EnvironmentObject private var store: AppStore

    private var items: [Product] { store.compare.compactMap { store.product($0) } }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                HarborTitleBar(title: "Compare")
                if items.count < 2 {
                    empty("Open two products and tap Compare.")
                } else {
                    HStack(alignment: .top, spacing: 12) {
                        ForEach(items.prefix(2)) { product in
                            VStack(alignment: .leading, spacing: 8) {
                                ProductPhoto(url: product.image, seed: product.id)
                                    .aspectRatio(1, contentMode: .fit)
                                    .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                                Text(product.title)
                                    .font(.system(size: 14, weight: .semibold))
                                    .foregroundStyle(HarborColor.navy)
                                    .lineLimit(3)
                                Text(store.money(product.price))
                                    .font(.system(size: 16, weight: .bold))
                                    .foregroundStyle(HarborColor.amber)
                                Text(product.shipsIn)
                                    .font(.system(size: 12))
                                    .foregroundStyle(HarborColor.muted)
                                NavigationLink(value: Route.product(product.id)) {
                                    Text("View")
                                        .font(.system(size: 13, weight: .semibold))
                                        .foregroundStyle(HarborColor.teal)
                                }
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)
                        }
                    }
                    .padding(.horizontal, 16)
                }
            }
        }
        .harborScreen()
    }
}

/// Native help hub. Policy, contact, and account-deletion rows push the in-app web screen.
struct HelpView: View {
    @EnvironmentObject private var store: AppStore

    private var legalRows: [(String, URL)] {
        let legal = store.legal
        return [
            (store.t("Shipping"), legal.shipping),
            (store.t("Returns"), legal.returns),
            (store.t("Privacy"), legal.privacy),
            (store.t("Terms"), legal.terms),
            (store.t("Contact / Chat"), legal.contact),
            (store.t("Delete account"), legal.accountDeletion)
        ]
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 10) {
                HarborTitleBar(title: store.t("Help & contact"))
                ForEach(Array(legalRows.enumerated()), id: \.offset) { _, row in
                    link(row.0) {
                        store.push(.inAppWeb(InAppWebRoute(url: row.1, title: row.0)))
                    }
                }
                link("Browsing history") { store.push(.history) }
                link(store.t("Addresses")) { store.push(.addresses) }
                link(store.t("Payment methods")) { store.push(.payments) }
                link(store.t("Compare")) { store.push(.compare) }
            }
            .padding(.bottom, 24)
        }
        .harborScreen()
        .task { await store.loadLegal() }
    }

    private func link(_ title: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack {
                Text(title)
                    .font(.system(size: 15))
                    .foregroundStyle(HarborColor.navy)
                Spacer()
                Image(systemName: "chevron.right")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(HarborColor.inactive)
            }
            .padding(14)
            .background(Color.white)
            .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: 14, style: .continuous).stroke(HarborColor.line, lineWidth: 1))
        }
        .buttonStyle(.plain)
        .padding(.horizontal, 16)
    }
}

struct PaymentsView: View {
    var body: some View {
        AccountPortalView(
            titleKey: "Payment methods",
            emptyKey: "No saved cards",
            noteKey: "Only the card brand and the last 4 digits are stored. The full card number is never kept.",
            actionKey: "Manage payment methods",
            symbol: "creditcard",
            destination: LegalUrls.accountPayments
        )
    }
}

/// Native account screen. The Me tab stays in SwiftUI.
/// Privacy and Manage open the shop page in the in-app web screen.
private struct AccountPortalView: View {
    @EnvironmentObject private var store: AppStore
    var titleKey: String
    var emptyKey: String
    var noteKey: String
    var actionKey: String
    var symbol: String
    var destination: URL

    var body: some View {
        VStack(spacing: 0) {
            HarborTitleBar(title: store.t(titleKey))
            ScrollView {
                VStack(alignment: .leading, spacing: 12) {
                    Image(systemName: symbol)
                        .font(.system(size: 26, weight: .light))
                        .foregroundStyle(HarborColor.navy)
                        .frame(width: 52, height: 52)
                        .background(HarborColor.iconBg)
                        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                    Text(store.t(emptyKey))
                        .font(.system(size: 18, weight: .bold))
                        .foregroundStyle(HarborColor.navy)
                    Text(store.t(noteKey))
                        .font(.system(size: 14))
                        .foregroundStyle(HarborColor.muted)
                        .fixedSize(horizontal: false, vertical: true)
                    Button {
                        store.push(.inAppWeb(InAppWebRoute(url: store.legal.privacy, title: store.t("Privacy"))))
                    } label: {
                        Text(store.t("Privacy"))
                            .font(.system(size: 14, weight: .semibold))
                            .underline()
                            .foregroundStyle(HarborColor.teal)
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel(store.t("Privacy"))
                }
                .padding(16)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color.white)
                .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
                .overlay(RoundedRectangle(cornerRadius: 16, style: .continuous).stroke(HarborColor.line, lineWidth: 1))
                .padding(.horizontal, 16)
                .padding(.top, 8)
                .padding(.bottom, 24)
            }
            PrimaryButton(title: store.t(actionKey), fill: HarborColor.navy) {
                store.push(.inAppWeb(InAppWebRoute(url: destination, title: store.t(actionKey))))
            }
            .padding(.horizontal, 16)
            .padding(.top, 12)
            .padding(.bottom, 16)
            .background(Color.white)
        }
        .harborScreen()
        .task { await store.loadLegal() }
    }
}

struct PolicyView: View {
    @EnvironmentObject private var store: AppStore
    var page: String

    private var title: String {
        switch page {
        case "privacy": return store.t("Privacy")
        case "terms": return store.t("Terms")
        case "shipping": return store.t("Shipping")
        case "contact": return store.t("Contact / Chat")
        case "returns": return store.t("Returns")
        case "account-deletion", "account_deletion": return store.t("Delete account")
        default: return store.t("Help")
        }
    }

    var body: some View {
        InAppWebScreen(url: store.legal.url(for: page), title: title)
            .task { await store.loadLegal() }
    }
}

struct OfflineView: View {
    @EnvironmentObject private var store: AppStore

    var body: some View {
        VStack(spacing: 14) {
            Image(systemName: "icloud.slash")
                .font(.system(size: 36, weight: .light))
                .foregroundStyle(HarborColor.navy)
            Text("You’re offline")
                .font(.system(size: 22, weight: .bold))
                .foregroundStyle(HarborColor.navy)
            Button {
                Task { await store.loadCatalog() }
            } label: {
                Text("Retry")
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundStyle(.white)
                    .padding(.horizontal, 22)
                    .frame(height: 41)
                    .background(HarborColor.navy)
                    .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
            }
            .buttonStyle(.plain)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(HarborColor.sand.ignoresSafeArea())
    }
}

private func empty(_ text: String) -> some View {
    Text(text)
        .font(.system(size: 14))
        .foregroundStyle(HarborColor.muted)
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, 16)
        .padding(.top, 12)
}
