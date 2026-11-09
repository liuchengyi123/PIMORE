import SwiftUI
import UIKit

struct ProductPhoto: View {
    var url: String?
    var seed: String = ""

    var body: some View {
        Color.clear
            .overlay {
                AsyncImage(url: URL(string: url ?? "")) { phase in
                    switch phase {
                    case .success(let image):
                        image.resizable().scaledToFill()
                    default:
                        HarborColor.pastel(for: seed.isEmpty ? (url ?? "") : seed)
                    }
                }
            }
            .clipped()
    }
}

struct ProductCard: View {
    @EnvironmentObject private var store: AppStore
    var product: Product

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            ProductPhoto(url: product.image, seed: product.id)
                .aspectRatio(1, contentMode: .fit)
                .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
            Text(product.title)
                .font(.system(size: 13, weight: .medium))
                .foregroundStyle(HarborColor.navy)
                .lineLimit(2)
                .multilineTextAlignment(.leading)
                .frame(maxWidth: .infinity, alignment: .leading)
            Text(store.money(product.price))
                .font(.system(size: 15, weight: .bold))
                .foregroundStyle(HarborColor.amber)
            Text(store.interestLine(product))
                .font(.system(size: 11))
                .foregroundStyle(HarborColor.muted)
                .lineLimit(1)
        }
        .padding(.bottom, 2)
    }
}

struct ProductGrid: View {
    var products: [Product]

    var body: some View {
        LazyVGrid(columns: [GridItem(.flexible(), spacing: 12), GridItem(.flexible(), spacing: 12)], spacing: 14) {
            ForEach(products) { product in
                NavigationLink(value: Route.product(product.id)) {
                    ProductCard(product: product)
                }
                .buttonStyle(.plain)
            }
        }
    }
}

struct HarborChip: View {
    var title: String
    var selected: Bool

    var body: some View {
        Text(title)
            .font(.system(size: 12, weight: selected ? .semibold : .medium))
            .foregroundStyle(selected ? Color.white : HarborColor.navy)
            .padding(.horizontal, 14)
            .padding(.vertical, 8)
            .background(selected ? HarborColor.navy : Color.white)
            .clipShape(Capsule())
            .overlay(Capsule().stroke(selected ? Color.clear : HarborColor.line, lineWidth: 1))
    }
}

struct HarborTitleBar: View {
    var title: String
    var showsBack = true
    var backHome = false
    var trailing: String?
    var trailingAction: () -> Void = {}

    var body: some View {
        HStack(spacing: 10) {
            if showsBack {
                HarborBackButton(backHome: backHome)
            }
            Text(title)
                .font(.system(size: 20, weight: .bold))
                .foregroundStyle(HarborColor.navy)
                .lineLimit(1)
            Spacer(minLength: 8)
            if let trailing {
                Button(trailing, action: trailingAction)
                    .font(.system(size: 14, weight: .medium))
                    .foregroundStyle(HarborColor.teal)
            }
        }
        .padding(.horizontal, 16)
        .padding(.top, 8)
        .padding(.bottom, 4)
    }
}

struct HarborBackButton: View {
    @EnvironmentObject private var store: AppStore
    @Environment(\.dismiss) private var dismiss
    var backHome = false

    var body: some View {
        Button {
            if backHome {
                store.goHome()
            } else {
                dismiss()
            }
        } label: {
            Image(systemName: "chevron.left")
                .font(.system(size: 18, weight: .semibold))
                .foregroundStyle(HarborColor.navy)
                .frame(width: 22, height: 28, alignment: .leading)
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Back")
    }
}

struct HarborTabBar: View {
    @EnvironmentObject private var store: AppStore

    var body: some View {
        HStack(spacing: 0) {
            ForEach(AppTab.allCases) { tab in
                Button {
                    store.tab = tab
                } label: {
                    tabItem(tab)
                }
                .buttonStyle(.plain)
            }
        }
        .padding(.horizontal, 6)
        .padding(.top, 4)
        .padding(.bottom, 6)
        .background(Color.white)
        .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
        .shadow(color: HarborColor.shadow, radius: 16, y: 4)
        .padding(.horizontal, 16)
        .padding(.bottom, 6)
        .background(HarborColor.sand)
    }

    private func tabItem(_ tab: AppTab) -> some View {
        let selected = store.tab == tab
        return VStack(spacing: 4) {
            ZStack(alignment: .topTrailing) {
                Image(systemName: tab.symbol)
                    .font(.system(size: 20, weight: .light))
                    .frame(width: 24, height: 24)
                if tab == .cart && store.cartCount > 0 {
                    Text(store.cartCount > 9 ? "9+" : "\(store.cartCount)")
                        .font(.system(size: 9, weight: .bold))
                        .foregroundStyle(.white)
                        .padding(.horizontal, 4)
                        .frame(minWidth: 16, minHeight: 16)
                        .background(HarborColor.danger)
                        .clipShape(Capsule())
                        .offset(x: 10, y: -6)
                }
            }
            Text(store.t(tab.title))
                .font(.system(size: 10, weight: selected ? .semibold : .medium))
        }
        .foregroundStyle(selected ? HarborColor.navy : HarborColor.inactive)
        .frame(maxWidth: .infinity)
        .padding(.vertical, 4)
    }
}

struct CSButton: View {
    var action: () -> Void

    var body: some View {
        Button(action: action) {
            Text("CS")
                .font(.system(size: 12, weight: .semibold))
                .foregroundStyle(.white)
                .frame(width: 48, height: 48)
                .background(HarborColor.navy)
                .clipShape(Circle())
                .shadow(color: HarborColor.shadow, radius: 8, y: 3)
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Customer service")
    }
}

struct HarborCard<Content: View>: View {
    @ViewBuilder var content: () -> Content

    var body: some View {
        content()
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Color.white)
            .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 16, style: .continuous)
                    .stroke(HarborColor.line, lineWidth: 1)
            )
    }
}

struct PrimaryButton: View {
    var title: String
    var fill: Color = HarborColor.amber
    var action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.system(size: 16, weight: .semibold))
                .foregroundStyle(.white)
                .frame(maxWidth: .infinity)
                .frame(height: 44)
                .background(fill)
                .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        }
        .buttonStyle(.plain)
    }
}

struct OutlineButton: View {
    var title: String
    var action: () -> Void

    var body: some View {
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
                        .stroke(HarborColor.navy, lineWidth: 1)
                )
        }
        .buttonStyle(.plain)
    }
}

struct FieldBlock: View {
    var label: String
    var text: Binding<String>
    var prompt: String
    var secure = false
    var keyboard: UIKeyboardType = .default

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label)
                .font(.system(size: 12))
                .foregroundStyle(HarborColor.muted)
            Group {
                if secure {
                    SecureField(prompt, text: text)
                } else {
                    TextField(prompt, text: text)
                        .keyboardType(keyboard)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                }
            }
            .font(.system(size: 16))
            .foregroundStyle(HarborColor.navy)
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.white)
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .stroke(HarborColor.line, lineWidth: 1)
        )
    }
}

struct QtyStepper: View {
    var quantity: Int
    var minus: () -> Void
    var plus: () -> Void

    var body: some View {
        HStack(spacing: 10) {
            Button("−", action: minus)
            Text("\(quantity)")
                .frame(minWidth: 12)
            Button("+", action: plus)
        }
        .font(.system(size: 15, weight: .medium))
        .foregroundStyle(HarborColor.navy)
        .padding(.horizontal, 10)
        .padding(.vertical, 5)
        .background(HarborColor.sand)
        .clipShape(Capsule())
        .buttonStyle(.plain)
    }
}

struct MetaChip: View {
    var title: String
    var fg: Color
    var bg: Color

    var body: some View {
        Text(title)
            .font(.system(size: 12, weight: .medium))
            .foregroundStyle(fg)
            .padding(.horizontal, 10)
            .padding(.vertical, 4)
            .background(bg)
            .clipShape(Capsule())
    }
}

func subcategoryName(_ raw: String) -> String {
    switch raw {
    case "prep": return "Prep"
    case "tools": return "Tools"
    case "cloths": return "Cloths"
    case "brushes": return "Brushes"
    case "bins": return "Bins"
    case "shelves": return "Shelves"
    case "care": return "Care"
    case "bowls": return "Bowls"
    case "towels": return "Towels"
    default:
        return raw.isEmpty ? raw : raw.prefix(1).uppercased() + raw.dropFirst()
    }
}
