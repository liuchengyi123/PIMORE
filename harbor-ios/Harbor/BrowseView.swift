import SwiftUI

struct BrowseView: View {
    @EnvironmentObject private var store: AppStore

    private var rows: [Category] {
        let preferred = Category.browseOrder.compactMap { id in
            store.categories.first { $0.id == id }
        }
        return preferred.isEmpty ? Array(store.categories.prefix(4)) : preferred
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                Text(store.t("Browse"))
                    .font(.system(size: 20, weight: .bold))
                    .foregroundStyle(HarborColor.navy)
                    .padding(.horizontal, 16)
                    .padding(.top, 8)
                ForEach(rows) { category in
                    NavigationLink(value: Route.category(category.id)) {
                        categoryRow(category)
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.bottom, 16)
        }
        .harborRoot()
    }

    private func categoryRow(_ category: Category) -> some View {
        let cover = store.products.first { $0.category == category.id }?.image
        return HStack(spacing: 0) {
            ZStack {
                HarborColor.sand
                if let cover {
                    ProductPhoto(url: cover, seed: category.id)
                        .padding(8)
                } else {
                    Image(systemName: category.symbol)
                        .font(.system(size: 22, weight: .light))
                        .foregroundStyle(HarborColor.navy)
                }
            }
            .frame(width: 78, height: 78)
            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
            .padding(8)

            VStack(alignment: .leading, spacing: 2) {
                Text(store.t(category.name))
                    .font(.system(size: 17, weight: .semibold))
                    .foregroundStyle(HarborColor.navy)
                Text(store.t(category.subtitle))
                    .font(.system(size: 13))
                    .foregroundStyle(HarborColor.muted)
            }
            Spacer()
        }
        .background(Color.white)
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .stroke(HarborColor.line, lineWidth: 1)
        )
        .padding(.horizontal, 16)
    }
}
