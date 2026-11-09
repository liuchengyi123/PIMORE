import SwiftUI

struct OrdersView: View {
    @EnvironmentObject private var store: AppStore
    @State private var filter: OrderStatus?

    init(initial: OrderStatus?) {
        _filter = State(initialValue: initial)
    }

    private var rows: [StoreOrder] { store.orders(matching: filter) }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HarborTitleBar(title: store.t("My orders"))
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    Button { filter = nil } label: {
                        HarborChip(title: store.t("All"), selected: filter == nil)
                    }
                    .buttonStyle(.plain)
                    ForEach(OrderStatus.allCases) { status in
                        Button { filter = status } label: {
                            HarborChip(title: store.t(status.title), selected: filter == status)
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 8)
            }
            if rows.isEmpty {
                Text(store.t("No orders in this tab yet."))
                    .font(.system(size: 14))
                    .foregroundStyle(HarborColor.muted)
                    .frame(maxWidth: .infinity)
                    .padding(.top, 48)
                Spacer()
            } else {
                ScrollView {
                    VStack(spacing: 10) {
                        ForEach(rows) { order in
                            NavigationLink(value: Route.order(order.id)) {
                                orderRow(order)
                            }
                            .buttonStyle(.plain)
                        }
                    }
                    .padding(.horizontal, 16)
                    .padding(.bottom, 24)
                }
            }
        }
        .harborScreen()
    }

    private func orderRow(_ order: StoreOrder) -> some View {
        HStack(spacing: 12) {
            ProductPhoto(url: order.lines.first?.imageURL, seed: order.id)
                .frame(width: 64, height: 64)
                .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text(order.status.title)
                        .font(.system(size: 14, weight: .semibold))
                        .foregroundStyle(HarborColor.navy)
                    Spacer()
                    Text(order.id)
                        .font(.system(size: 12))
                        .foregroundStyle(HarborColor.muted)
                }
                Text(order.lines.first?.title ?? "Harbor order")
                    .font(.system(size: 13))
                    .foregroundStyle(HarborColor.muted)
                    .lineLimit(1)
                Text(store.money(order.total))
                    .font(.system(size: 15, weight: .bold))
                    .foregroundStyle(HarborColor.amber)
            }
        }
        .padding(12)
        .background(Color.white)
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
        .overlay(RoundedRectangle(cornerRadius: 16, style: .continuous).stroke(HarborColor.line, lineWidth: 1))
    }
}

struct OrderDetailView: View {
    @EnvironmentObject private var store: AppStore
    var orderID: String

    private var order: StoreOrder? { store.orders.first { $0.id == orderID } }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 10) {
                HarborTitleBar(title: "Order detail")
                if let order {
                    VStack(alignment: .leading, spacing: 6) {
                        HStack {
                            Text(order.status.title)
                                .font(.system(size: 16, weight: .semibold))
                                .foregroundStyle(HarborColor.navy)
                            Spacer()
                            Text(order.id)
                                .font(.system(size: 12))
                                .foregroundStyle(HarborColor.muted)
                        }
                        if let tracking = order.tracking, !tracking.isEmpty {
                            Text(tracking)
                                .font(.system(size: 13))
                                .foregroundStyle(HarborColor.muted)
                        } else {
                            Text("Tracking appears when the parcel ships.")
                                .font(.system(size: 13))
                                .foregroundStyle(HarborColor.muted)
                        }
                        Text(order.address)
                            .font(.system(size: 13))
                            .foregroundStyle(HarborColor.navy)
                        Text(order.payment)
                            .font(.system(size: 12))
                            .foregroundStyle(HarborColor.muted)
                    }
                    .padding(15)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(Color.white)
                    .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                    .overlay(RoundedRectangle(cornerRadius: 14, style: .continuous).stroke(HarborColor.line, lineWidth: 1))
                    .padding(.horizontal, 16)

                    ForEach(order.lines) { line in
                        HStack(spacing: 12) {
                            ProductPhoto(url: line.imageURL, seed: line.productID)
                                .frame(width: 64, height: 64)
                                .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                            VStack(alignment: .leading, spacing: 4) {
                                Text(line.title)
                                    .font(.system(size: 14, weight: .medium))
                                    .foregroundStyle(HarborColor.navy)
                                    .lineLimit(2)
                                Text("× \(line.quantity)")
                                    .font(.system(size: 12))
                                    .foregroundStyle(HarborColor.muted)
                                Text(store.money(line.price))
                                    .font(.system(size: 16, weight: .bold))
                                    .foregroundStyle(HarborColor.amber)
                            }
                            Spacer()
                        }
                        .padding(12)
                        .background(Color.white)
                        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                        .overlay(RoundedRectangle(cornerRadius: 14, style: .continuous).stroke(HarborColor.line, lineWidth: 1))
                        .padding(.horizontal, 16)
                    }

                    if order.status != .returns {
                        Button {
                            store.push(.returns(order.id))
                        } label: {
                            Text("Request return")
                                .font(.system(size: 15, weight: .semibold))
                                .foregroundStyle(HarborColor.navy)
                                .frame(maxWidth: .infinity)
                                .frame(height: 44)
                                .background(Color.white)
                                .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                                .overlay(RoundedRectangle(cornerRadius: 12, style: .continuous).stroke(HarborColor.line, lineWidth: 1))
                        }
                        .buttonStyle(.plain)
                        .padding(.horizontal, 16)
                        .padding(.top, 4)
                    }
                } else {
                    Text("Order not found.")
                        .foregroundStyle(HarborColor.muted)
                        .padding(16)
                }
            }
            .padding(.bottom, 24)
        }
        .harborScreen()
    }
}

struct ReturnView: View {
    @EnvironmentObject private var store: AppStore
    var orderID: String
    @State private var reason = "Damaged / not as described"
    @State private var sent = false

    private var order: StoreOrder? { store.orders.first { $0.id == orderID } }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                HarborTitleBar(title: "Request return")
                if let line = order?.lines.first {
                    HStack(spacing: 12) {
                        ProductPhoto(url: line.imageURL, seed: line.productID)
                            .frame(width: 64, height: 64)
                            .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                        VStack(alignment: .leading, spacing: 4) {
                            Text(line.title)
                                .font(.system(size: 14, weight: .medium))
                                .foregroundStyle(HarborColor.navy)
                                .lineLimit(2)
                            Text(orderID)
                                .font(.system(size: 12))
                                .foregroundStyle(HarborColor.muted)
                        }
                    }
                    .padding(12)
                    .background(Color.white)
                    .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                    .overlay(RoundedRectangle(cornerRadius: 14, style: .continuous).stroke(HarborColor.line, lineWidth: 1))
                    .padding(.horizontal, 16)
                }
                VStack(alignment: .leading, spacing: 6) {
                    Text("Reason")
                        .font(.system(size: 13))
                        .foregroundStyle(HarborColor.muted)
                    TextField("Reason", text: $reason, axis: .vertical)
                        .lineLimit(3...5)
                        .font(.system(size: 15))
                        .foregroundStyle(HarborColor.navy)
                }
                .padding(14)
                .background(Color.white)
                .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                .overlay(RoundedRectangle(cornerRadius: 14, style: .continuous).stroke(HarborColor.line, lineWidth: 1))
                .padding(.horizontal, 16)

                PrimaryButton(title: sent ? "Requested" : "Submit request") {
                    guard !reason.trimmingCharacters(in: .whitespaces).isEmpty else { return }
                    store.requestReturn(orderID)
                    sent = true
                }
                .disabled(sent)
                .padding(.horizontal, 16)
                if sent {
                    Text("Return requested. You can follow it under Returns.")
                        .font(.system(size: 13))
                        .foregroundStyle(HarborColor.muted)
                        .padding(.horizontal, 16)
                }
            }
        }
        .harborScreen()
    }
}
