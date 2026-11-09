import SwiftUI

struct CartView: View {
    @EnvironmentObject private var store: AppStore

    var body: some View {
        VStack(spacing: 0) {
            HarborTitleBar(title: "\(store.t("Cart")) (\(store.cartCount))", backHome: true)
            if store.cart.isEmpty {
                Spacer()
                VStack(spacing: 14) {
                    Image(systemName: "cart")
                        .font(.system(size: 32, weight: .light))
                        .foregroundStyle(HarborColor.navy)
                    Text(store.t("Your cart is empty"))
                        .font(.system(size: 18, weight: .bold))
                        .foregroundStyle(HarborColor.navy)
                    Button {
                        store.goHome()
                    } label: {
                        Text(store.t("Go shopping"))
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundStyle(.white)
                            .padding(.horizontal, 16)
                            .frame(height: 41)
                            .background(HarborColor.navy)
                            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                    }
                    .buttonStyle(.plain)
                }
                Spacer()
            } else {
                ScrollView {
                    VStack(spacing: 10) {
                        ForEach(store.cart) { line in
                            cartRow(line)
                        }
                    }
                    .padding(.horizontal, 16)
                    .padding(.top, 8)
                    .padding(.bottom, 16)
                }
                HStack(spacing: 12) {
                    Text(store.money(store.subtotal))
                        .font(.system(size: 20, weight: .bold))
                        .foregroundStyle(HarborColor.navy)
                    PrimaryButton(title: store.t("Checkout")) {
                        store.push(.checkout)
                    }
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 12)
                .background(Color.white)
            }
        }
        .harborRoot()
    }

    private func cartRow(_ line: CartLine) -> some View {
        HStack(alignment: .center, spacing: 12) {
            ProductPhoto(url: line.imageURL, seed: line.productID)
                .frame(width: 72, height: 72)
                .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
            VStack(alignment: .leading, spacing: 6) {
                Text(line.title)
                    .font(.system(size: 14, weight: .medium))
                    .foregroundStyle(HarborColor.navy)
                    .lineLimit(2)
                Text(line.skuLabel)
                    .font(.system(size: 12))
                    .foregroundStyle(HarborColor.muted)
                    .lineLimit(1)
                HStack {
                    Text(store.money(line.price))
                        .font(.system(size: 16, weight: .bold))
                        .foregroundStyle(HarborColor.amber)
                    Spacer()
                    QtyStepper(
                        quantity: line.quantity,
                        minus: { store.changeQty(line, by: -1) },
                        plus: { store.changeQty(line, by: 1) }
                    )
                }
            }
        }
        .padding(12)
        .background(Color.white)
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .stroke(HarborColor.line, lineWidth: 1)
        )
    }
}

struct CheckoutView: View {
    @EnvironmentObject private var store: AppStore
    @State private var email = ""
    @State private var error: String?

    var body: some View {
        VStack(spacing: 0) {
            ScrollView {
                VStack(alignment: .leading, spacing: 10) {
                    HarborTitleBar(title: store.t("Checkout"))
                    Button {
                        store.push(.addresses)
                    } label: {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(store.t("Ship to"))
                                .font(.system(size: 15, weight: .semibold))
                                .foregroundStyle(HarborColor.navy)
                            Text(store.defaultAddress?.summary ?? "Add an address")
                                .font(.system(size: 14))
                                .foregroundStyle(HarborColor.muted)
                        }
                        .padding(15)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(Color.white)
                        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                        .overlay(RoundedRectangle(cornerRadius: 14, style: .continuous).stroke(HarborColor.line, lineWidth: 1))
                    }
                    .buttonStyle(.plain)
                    .padding(.horizontal, 16)

                    FieldBlock(label: store.t("Email"), text: $email, prompt: "you@email.com", keyboard: .emailAddress)
                        .padding(.horizontal, 16)

                    VStack(alignment: .leading, spacing: 8) {
                        Text(store.t("Pay with"))
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundStyle(HarborColor.navy)
                        ForEach(PaymentKind.allCases) { kind in
                            Button {
                                store.setPayment(kind)
                            } label: {
                                HStack(spacing: 8) {
                                    Image(systemName: store.payment == kind ? "checkmark.circle.fill" : "circle")
                                        .font(.system(size: 16, weight: .light))
                                        .foregroundStyle(store.payment == kind ? HarborColor.teal : HarborColor.inactive)
                                    Text(kind.title)
                                        .font(.system(size: 15))
                                        .foregroundStyle(HarborColor.navy)
                                    Spacer()
                                }
                                .padding(.horizontal, 12)
                                .frame(height: store.payment == kind ? 40 : 38)
                                .background(store.payment == kind ? HarborColor.sand : Color.white)
                                .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                                .overlay(
                                    RoundedRectangle(cornerRadius: 10, style: .continuous)
                                        .stroke(HarborColor.line, lineWidth: 1)
                                )
                            }
                            .buttonStyle(.plain)
                        }
                        Button {
                            store.push(.payments)
                        } label: {
                            Text(store.t("Payment methods"))
                                .font(.system(size: 13, weight: .medium))
                                .foregroundStyle(HarborColor.teal)
                        }
                        .buttonStyle(.plain)
                    }
                    .padding(15)
                    .background(Color.white)
                    .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                    .overlay(RoundedRectangle(cornerRadius: 14, style: .continuous).stroke(HarborColor.line, lineWidth: 1))
                    .padding(.horizontal, 16)

                    coupon
                        .padding(.horizontal, 16)

                    if let error {
                        Text(error)
                            .font(.system(size: 13))
                            .foregroundStyle(HarborColor.danger)
                            .padding(.horizontal, 16)
                    }
                    Text(store.t("Preview checkout · no payment is sent."))
                        .font(.system(size: 12))
                        .foregroundStyle(HarborColor.muted)
                        .padding(.horizontal, 16)
                        .padding(.bottom, 12)
                }
            }
            HStack(spacing: 12) {
                Text(store.money(store.payable))
                    .font(.system(size: 20, weight: .bold))
                    .foregroundStyle(HarborColor.navy)
                PrimaryButton(title: store.t("Place order")) { place() }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            .background(Color.white)
        }
        .harborScreen()
        .onAppear {
            if email.isEmpty {
                email = store.session?.email ?? ""
            }
        }
    }

    private var coupon: some View {
        Button {
            store.couponArmed.toggle()
        } label: {
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text("WELCOME5 · $5")
                        .font(.system(size: 14, weight: .semibold))
                        .foregroundStyle(HarborColor.navy)
                    Text(store.subtotal >= 20 ? "Over $20" : "Add more to reach $20")
                        .font(.system(size: 12))
                        .foregroundStyle(HarborColor.muted)
                }
                Spacer()
                Image(systemName: store.couponArmed ? "checkmark.circle.fill" : "circle")
                    .foregroundStyle(store.couponArmed ? HarborColor.teal : HarborColor.inactive)
            }
            .padding(14)
            .background(Color.white)
            .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: 14, style: .continuous).stroke(HarborColor.line, lineWidth: 1))
        }
        .buttonStyle(.plain)
    }

    private func place() {
        let trimmed = email.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmed.contains("@") else {
            error = "Add an email for the receipt."
            return
        }
        guard store.defaultAddress != nil else {
            error = "Add a shipping address."
            return
        }
        guard !store.cart.isEmpty else {
            error = "Your cart is empty."
            return
        }
        let order = store.placeOrder(email: trimmed, address: store.defaultAddress?.summary ?? "")
        store.replaceTop(with: .success(order.id))
    }
}

struct SuccessView: View {
    @EnvironmentObject private var store: AppStore
    var orderID: String

    private var order: StoreOrder? { store.orders.first { $0.id == orderID } }

    var body: some View {
        VStack(spacing: 16) {
            Spacer()
            Image(systemName: "checkmark")
                .font(.system(size: 28, weight: .semibold))
                .foregroundStyle(HarborColor.teal)
                .frame(width: 64, height: 64)
                .background(HarborColor.shipBg)
                .clipShape(Circle())
            Text("Payment successful")
                .font(.system(size: 22, weight: .bold))
                .foregroundStyle(HarborColor.navy)
            if let order {
                Text("\(order.id) · \(store.money(order.total))")
                    .font(.system(size: 14))
                    .foregroundStyle(HarborColor.muted)
            }
            Button {
                store.push(.order(orderID))
            } label: {
                Text("View order")
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundStyle(.white)
                    .padding(.horizontal, 18)
                    .frame(height: 41)
                    .background(HarborColor.navy)
                    .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
            }
            .buttonStyle(.plain)
            Button("Back to Home") { store.goHome() }
                .font(.system(size: 14, weight: .medium))
                .foregroundStyle(HarborColor.teal)
            Spacer()
        }
        .frame(maxWidth: .infinity)
        .harborScreen()
    }
}
