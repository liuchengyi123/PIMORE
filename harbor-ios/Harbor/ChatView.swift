import SwiftUI

struct ChatView: View {
    @EnvironmentObject private var store: AppStore
    var topic: String?
    @State private var draft = ""
    @State private var showEmoji = false
    @State private var sheet: ChatSheet?
    @State private var previewProduct: String?
    @State private var previewOrder: String?

    private let emojis = ["😊", "👍", "❤️", "🙏", "📦", "✨", "🏠", "🚚", "😂", "😍", "👌", "🙌"]

    private var offer: Product? {
        guard let topic else { return nil }
        return store.product(topic)
    }

    var body: some View {
        VStack(spacing: 0) {
            header
            ScrollViewReader { proxy in
                ScrollView {
                    VStack(alignment: .leading, spacing: 10) {
                        if store.chat.isEmpty {
                            emptyState
                        }
                        ForEach(store.chat) { message in
                            bubble(message)
                                .id(message.id)
                        }
                        if store.chatTyping {
                            Text(store.t("Harbor is typing…"))
                                .font(.system(size: 12))
                                .foregroundStyle(HarborColor.muted)
                                .padding(.horizontal, 4)
                        }
                    }
                    .padding(16)
                }
                .onChange(of: store.chat.count) { _ in
                    if let last = store.chat.last?.id {
                        withAnimation { proxy.scrollTo(last, anchor: .bottom) }
                    }
                }
            }
            if let offer {
                offerBar(offer)
            }
            toolRow
            if showEmoji {
                emojiPanel
            }
            composer
        }
        .harborScreen()
        .sheet(item: $sheet) { kind in
            switch kind {
            case .orders:
                ChatOrdersSheet { order in
                    store.sendOrderToChat(order.id)
                    sheet = nil
                }
            case .visited:
                ChatVisitedSheet { product in
                    store.sendProductToChat(product.id)
                    sheet = nil
                }
            }
        }
        .overlay {
            if let id = previewProduct, let product = store.product(id) {
                ChatProductPopup(product: product) { previewProduct = nil }
            }
            if let id = previewOrder, let order = store.orders.first(where: { $0.id == id }) {
                ChatOrderPopup(order: order) { previewOrder = nil }
            }
        }
    }

    private var header: some View {
        HStack(spacing: 10) {
            HarborBackButton()
            VStack(alignment: .leading, spacing: 0) {
                Text("Harbor")
                    .font(.system(size: 17, weight: .bold))
                    .foregroundStyle(HarborColor.navy)
                Text(store.chatTyping ? store.t("Harbor is typing…") : store.t("Usually replies in a few minutes"))
                    .font(.system(size: 12))
                    .foregroundStyle(HarborColor.muted)
                    .lineLimit(1)
            }
            Spacer()
            Button(store.t("Orders")) { sheet = .orders }
                .font(.system(size: 14, weight: .medium))
                .foregroundStyle(HarborColor.teal)
        }
        .padding(.horizontal, 16)
        .padding(.top, 8)
        .padding(.bottom, 6)
    }

    private var emptyState: some View {
        VStack(spacing: 8) {
            Text("💬")
                .font(.system(size: 28))
                .frame(width: 64, height: 64)
                .background(Color.white)
                .clipShape(Circle())
            Text(store.t("How can we help?"))
                .font(.system(size: 18, weight: .bold))
                .foregroundStyle(HarborColor.navy)
            Text(store.t("Ask about shipping, an order, or a product."))
                .font(.system(size: 14))
                .foregroundStyle(HarborColor.muted)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity)
        .padding(.top, 36)
        .padding(.bottom, 12)
    }

    @ViewBuilder
    private func bubble(_ message: ChatMessage) -> some View {
        HStack {
            if !message.fromShop { Spacer(minLength: 48) }
            VStack(alignment: .leading, spacing: 8) {
                if !message.text.isEmpty {
                    Text(message.fromShop ? store.t(message.text) : message.text)
                        .font(.system(size: 14))
                        .foregroundStyle(message.fromShop ? HarborColor.navy : Color.white)
                }
                if let id = message.productID, let product = store.product(id) {
                    Button { previewProduct = id } label: {
                        productCard(product)
                    }
                    .buttonStyle(.plain)
                }
                if let id = message.orderID, let order = store.orders.first(where: { $0.id == id }) {
                    Button { previewOrder = id } label: {
                        orderCard(order)
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(12)
            .background(message.fromShop ? Color.white : HarborColor.navy)
            .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 16, style: .continuous)
                    .stroke(message.fromShop ? HarborColor.line : Color.clear, lineWidth: 1)
            )
            if message.fromShop { Spacer(minLength: 48) }
        }
    }

    private func productCard(_ product: Product) -> some View {
        HStack(spacing: 10) {
            ProductPhoto(url: product.image, seed: product.id)
                .frame(width: 56, height: 56)
                .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
            VStack(alignment: .leading, spacing: 2) {
                Text(product.title)
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundStyle(HarborColor.navy)
                    .lineLimit(2)
                    .multilineTextAlignment(.leading)
                Text(store.money(product.price))
                    .font(.system(size: 14, weight: .bold))
                    .foregroundStyle(HarborColor.amber)
                Text(store.t("Tap to preview"))
                    .font(.system(size: 12))
                    .foregroundStyle(HarborColor.teal)
            }
        }
        .padding(8)
        .frame(maxWidth: 260, alignment: .leading)
        .background(HarborColor.sand)
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
    }

    private func orderCard(_ order: StoreOrder) -> some View {
        HStack(spacing: 10) {
            ProductPhoto(url: order.lines.first?.imageURL, seed: order.id)
                .frame(width: 52, height: 52)
                .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
            VStack(alignment: .leading, spacing: 2) {
                Text("\(order.id) · \(store.t(order.status.title))")
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundStyle(HarborColor.navy)
                    .lineLimit(1)
                Text(order.lines.first?.title ?? store.t("My orders"))
                    .font(.system(size: 12))
                    .foregroundStyle(HarborColor.muted)
                    .lineLimit(1)
                Text(store.money(order.total))
                    .font(.system(size: 13, weight: .bold))
                    .foregroundStyle(HarborColor.amber)
            }
        }
        .padding(8)
        .frame(maxWidth: 260, alignment: .leading)
        .background(HarborColor.sand)
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
    }

    private func offerBar(_ product: Product) -> some View {
        HStack(spacing: 10) {
            ProductPhoto(url: product.image, seed: product.id)
                .frame(width: 52, height: 52)
                .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
            VStack(alignment: .leading, spacing: 2) {
                Text(product.title)
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundStyle(HarborColor.navy)
                    .lineLimit(1)
                Text(store.money(product.price))
                    .font(.system(size: 13, weight: .bold))
                    .foregroundStyle(HarborColor.amber)
            }
            Spacer()
            Button(store.t("Send")) { store.sendProductToChat(product.id) }
                .font(.system(size: 13, weight: .semibold))
                .foregroundStyle(.white)
                .padding(.horizontal, 12)
                .frame(height: 32)
                .background(HarborColor.navy)
                .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
        }
        .padding(10)
        .background(Color.white)
        .overlay(Rectangle().frame(height: 1).foregroundStyle(HarborColor.line), alignment: .top)
    }

    private var toolRow: some View {
        HStack(spacing: 8) {
            tool(store.t("Emoji")) { showEmoji.toggle() }
            tool(store.t("My orders")) { sheet = .orders }
            tool(store.t("Visited")) { sheet = .visited }
            Spacer()
        }
        .padding(.horizontal, 12)
        .padding(.top, 8)
        .background(HarborColor.sand)
    }

    private func tool(_ title: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(title)
                .font(.system(size: 12, weight: .semibold))
                .foregroundStyle(HarborColor.navy)
                .padding(.horizontal, 10)
                .frame(height: 30)
                .background(Color.white)
                .clipShape(Capsule())
                .overlay(Capsule().stroke(HarborColor.line, lineWidth: 1))
        }
        .buttonStyle(.plain)
    }

    private var emojiPanel: some View {
        LazyVGrid(columns: Array(repeating: GridItem(.flexible()), count: 6), spacing: 8) {
            ForEach(emojis, id: \.self) { emoji in
                Button(emoji) { draft.append(emoji) }
                    .font(.system(size: 24))
                    .buttonStyle(.plain)
            }
        }
        .padding(12)
        .background(Color.white)
    }

    private var composer: some View {
        HStack(spacing: 8) {
            TextField(store.t("Message Harbor…"), text: $draft)
                .font(.system(size: 15))
                .padding(.horizontal, 12)
                .frame(height: 40)
                .background(Color.white)
                .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                .overlay(RoundedRectangle(cornerRadius: 12, style: .continuous).stroke(HarborColor.line, lineWidth: 1))
            Button {
                store.sendChat(draft)
                draft = ""
                showEmoji = false
            } label: {
                Image(systemName: "arrow.up")
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundStyle(.white)
                    .frame(width: 36, height: 36)
                    .background(draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? HarborColor.inactive : HarborColor.navy)
                    .clipShape(Circle())
            }
            .buttonStyle(.plain)
            .disabled(draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
        .background(HarborColor.sand)
    }
}

private enum ChatSheet: String, Identifiable {
    case orders, visited
    var id: String { rawValue }
}

private struct ChatOrdersSheet: View {
    @EnvironmentObject private var store: AppStore
    var send: (StoreOrder) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Capsule().fill(HarborColor.line).frame(width: 40, height: 4).frame(maxWidth: .infinity)
            HStack {
                Text(store.t("Orders"))
                    .font(.system(size: 18, weight: .bold))
                    .foregroundStyle(HarborColor.navy)
                Spacer()
                Text(store.t("Visited"))
                    .font(.system(size: 12))
                    .foregroundStyle(HarborColor.muted)
            }
            if store.orders.isEmpty {
                Text(store.t("No orders yet"))
                    .font(.system(size: 14))
                    .foregroundStyle(HarborColor.muted)
                    .padding(.vertical, 24)
            } else {
                ScrollView {
                    VStack(spacing: 8) {
                        ForEach(store.orders) { order in
                            HStack(spacing: 10) {
                                ProductPhoto(url: order.lines.first?.imageURL, seed: order.id)
                                    .frame(width: 52, height: 52)
                                    .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                                VStack(alignment: .leading, spacing: 2) {
                                    Text("\(order.id) · \(store.t(order.status.title))")
                                        .font(.system(size: 14, weight: .semibold))
                                        .foregroundStyle(HarborColor.navy)
                                        .lineLimit(1)
                                    Text("\(order.lines.first?.title ?? "") · \(store.money(order.total))")
                                        .font(.system(size: 12))
                                        .foregroundStyle(HarborColor.muted)
                                        .lineLimit(1)
                                }
                                Spacer()
                                Button(store.t("Send")) { send(order) }
                                    .font(.system(size: 13, weight: .semibold))
                                    .foregroundStyle(HarborColor.teal)
                            }
                            .padding(10)
                            .background(Color.white)
                            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                            .overlay(RoundedRectangle(cornerRadius: 12, style: .continuous).stroke(HarborColor.line, lineWidth: 1))
                        }
                    }
                }
            }
        }
        .padding(16)
        .background(HarborColor.sand.ignoresSafeArea())
        .presentationDetents([.medium, .large])
        .presentationDragIndicator(.hidden)
    }
}

private struct ChatVisitedSheet: View {
    @EnvironmentObject private var store: AppStore
    var send: (Product) -> Void

    private var items: [Product] {
        store.history.compactMap { store.product($0) }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Capsule().fill(HarborColor.line).frame(width: 40, height: 4).frame(maxWidth: .infinity)
            HStack {
                Text(store.t("Visited"))
                    .font(.system(size: 18, weight: .bold))
                    .foregroundStyle(HarborColor.navy)
                Spacer()
                Text(store.t("Orders"))
                    .font(.system(size: 12))
                    .foregroundStyle(HarborColor.muted)
            }
            if items.isEmpty {
                Text(store.t("No recent products"))
                    .font(.system(size: 14))
                    .foregroundStyle(HarborColor.muted)
                    .padding(.vertical, 24)
            } else {
                ScrollView {
                    VStack(spacing: 8) {
                        ForEach(items) { product in
                            HStack(spacing: 10) {
                                ProductPhoto(url: product.image, seed: product.id)
                                    .frame(width: 52, height: 52)
                                    .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(product.title)
                                        .font(.system(size: 14, weight: .semibold))
                                        .foregroundStyle(HarborColor.navy)
                                        .lineLimit(1)
                                    Text(store.money(product.price))
                                        .font(.system(size: 13, weight: .bold))
                                        .foregroundStyle(HarborColor.amber)
                                }
                                Spacer()
                                Button(store.t("Send")) { send(product) }
                                    .font(.system(size: 13, weight: .semibold))
                                    .foregroundStyle(HarborColor.teal)
                            }
                            .padding(10)
                            .background(Color.white)
                            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                            .overlay(RoundedRectangle(cornerRadius: 12, style: .continuous).stroke(HarborColor.line, lineWidth: 1))
                        }
                    }
                }
            }
        }
        .padding(16)
        .background(HarborColor.sand.ignoresSafeArea())
        .presentationDetents([.medium, .large])
        .presentationDragIndicator(.hidden)
    }
}

private struct ChatProductPopup: View {
    @EnvironmentObject private var store: AppStore
    var product: Product
    var close: () -> Void

    var body: some View {
        ZStack {
            Color.black.opacity(0.35).ignoresSafeArea().onTapGesture { close() }
            VStack(alignment: .leading, spacing: 8) {
                ProductPhoto(url: product.image, seed: product.id)
                    .frame(maxWidth: .infinity)
                    .frame(height: 160)
                    .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                Text(product.title)
                    .font(.system(size: 16, weight: .bold))
                    .foregroundStyle(HarborColor.navy)
                    .fixedSize(horizontal: false, vertical: true)
                Text(store.money(product.price))
                    .font(.system(size: 20, weight: .bold))
                    .foregroundStyle(HarborColor.amber)
                Text(store.peopleInterested(product.interest))
                    .font(.system(size: 12))
                    .foregroundStyle(HarborColor.muted)
                HStack(spacing: 8) {
                    OutlineButton(title: store.t("Add to cart")) {
                        add(thenBuy: false)
                    }
                    PrimaryButton(title: store.t("Buy now")) {
                        add(thenBuy: true)
                    }
                }
                .padding(.top, 4)
            }
            .padding(16)
            .background(Color.white)
            .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
            .padding(.horizontal, 24)
        }
    }

    private func add(thenBuy: Bool) {
        let sku = product.skus.first(where: \.inStock) ?? product.skus.first
        if let sku {
            store.addToCart(product: product, sku: sku, quantity: 1)
        }
        close()
        if thenBuy {
            store.push(.checkout)
        }
    }
}

private struct ChatOrderPopup: View {
    @EnvironmentObject private var store: AppStore
    var order: StoreOrder
    var close: () -> Void

    var body: some View {
        ZStack {
            Color.black.opacity(0.35).ignoresSafeArea().onTapGesture { close() }
            VStack(alignment: .leading, spacing: 8) {
                Text(order.id)
                    .font(.system(size: 18, weight: .bold))
                    .foregroundStyle(HarborColor.navy)
                Text(store.t(order.status.title))
                    .font(.system(size: 13))
                    .foregroundStyle(HarborColor.muted)
                if let line = order.lines.first {
                    HStack(spacing: 10) {
                        ProductPhoto(url: line.imageURL, seed: line.productID)
                            .frame(width: 64, height: 64)
                            .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                        VStack(alignment: .leading, spacing: 4) {
                            Text(line.title)
                                .font(.system(size: 14, weight: .medium))
                                .foregroundStyle(HarborColor.navy)
                                .lineLimit(2)
                            Text(store.money(line.price))
                                .font(.system(size: 16, weight: .bold))
                                .foregroundStyle(HarborColor.amber)
                        }
                    }
                }
                HStack(spacing: 8) {
                    OutlineButton(title: store.t("Close"), action: close)
                    PrimaryButton(title: store.t("View order"), fill: HarborColor.navy) {
                        close()
                        store.push(.order(order.id))
                    }
                }
                .padding(.top, 6)
            }
            .padding(16)
            .background(Color.white)
            .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
            .padding(.horizontal, 24)
        }
    }
}
