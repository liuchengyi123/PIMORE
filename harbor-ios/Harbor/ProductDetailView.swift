import SwiftUI

private enum BuyIntent: Identifiable {
    case add, buy
    var id: Int { self == .add ? 0 : 1 }
}

struct ProductDetailView: View {
    @EnvironmentObject private var store: AppStore
    var productID: String
    @State private var page = 0
    @State private var intent: BuyIntent?
    @State private var notifyNote = false
    @State private var sharing = false

    private var product: Product? { store.product(productID) }

    var body: some View {
        Group {
            if let product {
                content(product)
            } else {
                VStack(spacing: 12) {
                    HarborTitleBar(title: "Product")
                    Text("This item is no longer in the shop.")
                        .foregroundStyle(HarborColor.muted)
                        .padding(.top, 40)
                    Spacer()
                }
            }
        }
        .harborScreen()
        .task {
            store.remember(productID)
            await store.refresh(productID)
        }
        .sheet(item: $intent) { mode in
            if let product {
                SKUSheet(product: product, buying: mode == .buy)
            }
        }
        .alert("We’ll email you when it’s back.", isPresented: $notifyNote) {
            Button("OK", role: .cancel) {}
        }
        .sheet(isPresented: $sharing) {
            if let product {
                ActivitySheet(items: [
                    product.title,
                    HarborLink.product(product.id)
                ])
            }
        }
    }

    private func content(_ product: Product) -> some View {
        VStack(spacing: 0) {
            ScrollView {
                VStack(spacing: 0) {
                    gallery(product)
                    detailCard(product)
                        .padding(.top, -20)
                    related(product)
                        .padding(.top, 18)
                }
                .padding(.bottom, 24)
            }
            bottomBar(product)
        }
        .overlay(alignment: .bottomTrailing) {
            CSButton {
                store.push(.chat(product.id))
            }
            .padding(.trailing, 16)
            .padding(.bottom, 92)
        }
    }

    private func gallery(_ product: Product) -> some View {
        let urls = product.images.isEmpty ? [product.image] : product.images
        return ZStack(alignment: .top) {
            Color.clear
                .aspectRatio(1, contentMode: .fit)
                .overlay {
                    TabView(selection: $page) {
                        ForEach(Array(urls.enumerated()), id: \.offset) { index, url in
                            ProductPhoto(url: url, seed: product.id)
                                .tag(index)
                        }
                    }
                    .tabViewStyle(.page(indexDisplayMode: urls.count > 1 ? .automatic : .never))
                }
                .clipped()
            HStack {
                HarborBackButton()
                    .padding(8)
                    .background(.white.opacity(0.9))
                    .clipShape(Circle())
                Spacer()
                Button {
                    sharing = true
                } label: {
                    Image(systemName: "square.and.arrow.up")
                        .font(.system(size: 16, weight: .light))
                        .foregroundStyle(HarborColor.navy)
                        .frame(width: 36, height: 36)
                        .background(.white.opacity(0.9))
                        .clipShape(Circle())
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Share")
                Button {
                    store.toggleWishlist(product.id)
                } label: {
                    Image(systemName: store.wishlist.contains(product.id) ? "heart.fill" : "heart")
                        .font(.system(size: 18, weight: .light))
                        .foregroundStyle(store.wishlist.contains(product.id) ? HarborColor.danger : HarborColor.navy)
                        .frame(width: 36, height: 36)
                        .background(.white.opacity(0.9))
                        .clipShape(Circle())
                }
                .buttonStyle(.plain)
            }
            .padding(.horizontal, 12)
            .padding(.top, 8)
            VStack {
                Spacer()
                Text(product.skus.first?.label ?? product.title)
                    .font(.system(size: 12))
                    .foregroundStyle(.white)
                    .lineLimit(1)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 4)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(HarborColor.navy.opacity(0.35))
            }
        }
    }

    private func detailCard(_ product: Product) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .firstTextBaseline, spacing: 8) {
                Text(store.money(product.price))
                    .font(.system(size: 28, weight: .bold))
                    .foregroundStyle(HarborColor.amber)
                if let was = product.compareAt, was > product.price {
                    Text(store.money(was))
                        .font(.system(size: 14))
                        .foregroundStyle(HarborColor.inactive)
                        .strikethrough()
                }
            }
            Text(product.title)
                .font(.system(size: 17, weight: .bold))
                .foregroundStyle(HarborColor.navy)
                .fixedSize(horizontal: false, vertical: true)
            Text(store.peopleInterested(product.interest))
                .font(.system(size: 13))
                .foregroundStyle(HarborColor.muted)
            HStack(spacing: 8) {
                if product.inStock {
                    if product.tracked {
                        MetaChip(title: store.t("Tracked"), fg: HarborColor.trackedText, bg: HarborColor.trackedBg)
                    }
                    MetaChip(title: product.shipsIn, fg: HarborColor.teal, bg: HarborColor.shipBg)
                } else {
                    MetaChip(title: store.t("Sold out"), fg: HarborColor.danger, bg: Color(red: 1, green: 0.93, blue: 0.93))
                }
            }
            .padding(.top, 2)
            VStack(alignment: .leading, spacing: 6) {
                Text(store.t("Description"))
                    .font(.system(size: 15, weight: .bold))
                    .foregroundStyle(HarborColor.navy)
                Text(product.description.isEmpty ? product.title : product.description)
                    .font(.system(size: 14))
                    .foregroundStyle(HarborColor.navy)
                    .fixedSize(horizontal: false, vertical: true)
            }
            .padding(.top, 10)
            VStack(alignment: .leading, spacing: 0) {
                Text(store.t("Specifications"))
                    .font(.system(size: 15, weight: .bold))
                    .foregroundStyle(HarborColor.navy)
                    .padding(.bottom, 8)
                ForEach(detailRows(product)) { row in
                    HStack(alignment: .top) {
                        Text(store.t(row.name))
                            .font(.system(size: 13))
                            .foregroundStyle(HarborColor.muted)
                            .frame(width: 110, alignment: .leading)
                        Text(row.value)
                            .font(.system(size: 13))
                            .foregroundStyle(HarborColor.navy)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    .padding(.vertical, 8)
                    .overlay(Rectangle().frame(height: 1).foregroundStyle(HarborColor.line), alignment: .bottom)
                }
            }
            .padding(.top, 14)
            Text(store.t("No reviews yet"))
                .font(.system(size: 14))
                .foregroundStyle(HarborColor.muted)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 12)
                .background(HarborColor.reviewBg)
                .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                .padding(.top, 14)
            Button {
                store.toggleCompare(product.id)
            } label: {
                Text(store.compare.contains(product.id) ? store.t("In compare") : store.t("Compare"))
                    .font(.system(size: 14, weight: .medium))
                    .foregroundStyle(HarborColor.teal)
            }
            .buttonStyle(.plain)
            .padding(.top, 4)
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.white)
        .clipShape(RoundedRectangle(cornerRadius: 22, style: .continuous))
    }

    private func detailRows(_ product: Product) -> [SpecRow] {
        var rows = product.specs
        let names = Set(rows.map { $0.name.lowercased() })
        if !names.contains("category") {
            let titled = product.category.prefix(1).uppercased() + product.category.dropFirst()
            rows.append(SpecRow(name: "Category", value: store.t(String(titled))))
        }
        if !names.contains("shipping") {
            rows.append(SpecRow(name: "Shipping", value: product.shipsIn))
        }
        return rows
    }

    private func related(_ product: Product) -> some View {
        let same = store.products.filter { $0.id != product.id && $0.category == product.category }
        let items = Array((same.isEmpty ? store.products.filter { $0.id != product.id } : same).prefix(4))
        return VStack(alignment: .leading, spacing: 10) {
            if !items.isEmpty {
                Text(store.t("Similar items"))
                    .font(.system(size: 16, weight: .bold))
                    .foregroundStyle(HarborColor.navy)
                    .padding(.horizontal, 16)
                ProductGrid(products: items)
                    .padding(.horizontal, 16)
            }
        }
    }

    @ViewBuilder
    private func bottomBar(_ product: Product) -> some View {
        HStack(spacing: 10) {
            if product.inStock {
                OutlineButton(title: store.t("Add to cart")) { intent = .add }
                PrimaryButton(title: store.t("Buy now")) { intent = .buy }
            } else {
                Text(store.t("Sold out"))
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundStyle(HarborColor.muted)
                    .frame(maxWidth: .infinity)
                    .frame(height: 44)
                    .background(HarborColor.iconBg)
                    .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                PrimaryButton(title: store.notifyIDs.contains(product.id) ? store.t("Notified") : store.t("Notify me"), fill: HarborColor.navy) {
                    store.notify(product.id)
                    notifyNote = true
                }
                .disabled(store.notifyIDs.contains(product.id))
            }
        }
        .padding(.horizontal, 14)
        .padding(.top, 10)
        .padding(.bottom, 12)
        .background(Color.white.ignoresSafeArea(edges: .bottom))
    }
}

struct SKUSheet: View {
    @EnvironmentObject private var store: AppStore
    @Environment(\.dismiss) private var dismiss
    var product: Product
    var buying: Bool
    @State private var skuID: String = ""
    @State private var quantity = 1

    private var sku: SKU? {
        product.skus.first { $0.id == skuID } ?? product.skus.first
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .top, spacing: 12) {
                ProductPhoto(url: sku?.image ?? product.image, seed: product.id)
                    .frame(width: 88, height: 88)
                    .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                VStack(alignment: .leading, spacing: 4) {
                    Text(store.money(sku?.price ?? product.price))
                        .font(.system(size: 22, weight: .bold))
                        .foregroundStyle(HarborColor.amber)
                    Text(sku?.label ?? product.title)
                        .font(.system(size: 13))
                        .foregroundStyle(HarborColor.navy)
                        .lineLimit(2)
                }
                Spacer()
                Button {
                    dismiss()
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 14, weight: .semibold))
                        .foregroundStyle(HarborColor.muted)
                        .frame(width: 32, height: 32)
                }
                .buttonStyle(.plain)
            }
            Text("Choose")
                .font(.system(size: 14, weight: .semibold))
                .foregroundStyle(HarborColor.navy)
            ScrollView {
                VStack(spacing: 8) {
                    ForEach(product.skus) { item in
                        Button {
                            skuID = item.id
                        } label: {
                            HStack(spacing: 10) {
                                ProductPhoto(url: item.image, seed: item.id)
                                    .frame(width: 48, height: 48)
                                    .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(item.label)
                                        .font(.system(size: 13, weight: .medium))
                                        .foregroundStyle(HarborColor.navy)
                                        .multilineTextAlignment(.leading)
                                    Text(store.money(item.price))
                                        .font(.system(size: 13, weight: .bold))
                                        .foregroundStyle(HarborColor.amber)
                                }
                                Spacer()
                                if item.id == (sku?.id ?? "") {
                                    Image(systemName: "checkmark.circle.fill")
                                        .foregroundStyle(HarborColor.teal)
                                }
                            }
                            .padding(8)
                            .background(item.id == (sku?.id ?? "") ? HarborColor.sand : Color.white)
                            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                            .overlay(
                                RoundedRectangle(cornerRadius: 12, style: .continuous)
                                    .stroke(HarborColor.line, lineWidth: 1)
                            )
                        }
                        .buttonStyle(.plain)
                        .disabled(!item.inStock)
                        .opacity(item.inStock ? 1 : 0.45)
                    }
                }
            }
            HStack {
                Text("Quantity")
                    .font(.system(size: 14, weight: .medium))
                    .foregroundStyle(HarborColor.navy)
                Spacer()
                QtyStepper(quantity: quantity, minus: { quantity = max(1, quantity - 1) }, plus: { quantity += 1 })
            }
            PrimaryButton(title: store.t(buying ? "Buy now" : "Add to cart"), fill: buying ? HarborColor.amber : HarborColor.navy) {
                guard let sku else { return }
                store.addToCart(product: product, sku: sku, quantity: quantity)
                dismiss()
                if buying {
                    DispatchQueue.main.async {
                        store.push(.checkout)
                    }
                }
            }
        }
        .padding(16)
        .background(HarborColor.sand.ignoresSafeArea())
        .presentationDetents([.medium, .large])
        .presentationDragIndicator(.visible)
        .onAppear {
            skuID = product.skus.first(where: \.inStock)?.id ?? product.skus.first?.id ?? ""
        }
    }
}
