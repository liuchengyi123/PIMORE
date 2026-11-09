import SwiftUI

enum CatalogSort: String, CaseIterable, Identifiable {
    case best, price, newest
    var id: String { rawValue }
    var title: String {
        switch self {
        case .best: return "Best"
        case .price: return "Price ↑"
        case .newest: return "Newest"
        }
    }
}

struct SearchView: View {
    @EnvironmentObject private var store: AppStore
    @State private var query: String
    @State private var sort: CatalogSort = .best
    @FocusState private var focused: Bool

    init(initialQuery: String) {
        _query = State(initialValue: initialQuery)
    }

    private var results: [Product] {
        let needle = query.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        let base = needle.isEmpty ? store.products : store.products.filter {
            $0.title.lowercased().contains(needle)
                || $0.category.contains(needle)
                || $0.subcategory.contains(needle)
                || $0.description.lowercased().contains(needle)
        }
        return apply(sort, to: base)
    }

    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: 8) {
                HarborBackButton()
                HStack(spacing: 8) {
                    Image(systemName: "magnifyingglass")
                        .font(.system(size: 15, weight: .light))
                        .foregroundStyle(HarborColor.muted)
                    TextField(store.t("Search kitchen, storage, cleaning…"), text: $query)
                        .font(.system(size: 15))
                        .focused($focused)
                        .submitLabel(.search)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 10)
                .background(Color.white)
                .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: 14, style: .continuous)
                        .stroke(HarborColor.line, lineWidth: 1)
                )
            }
            .padding(.horizontal, 16)
            .padding(.top, 8)

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(CatalogSort.allCases) { item in
                        Button { sort = item } label: {
                            HarborChip(title: store.t(item.title), selected: sort == item)
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 12)
            }

            ScrollView {
                if results.isEmpty {
                    Text(store.t("No matches."))
                        .font(.system(size: 14))
                        .foregroundStyle(HarborColor.muted)
                        .frame(maxWidth: .infinity)
                        .padding(.top, 48)
                } else {
                    ProductGrid(products: results)
                        .padding(.horizontal, 16)
                        .padding(.bottom, 24)
                }
            }
        }
        .harborScreen()
        .onAppear { focused = query.isEmpty }
    }
}

struct CategoryView: View {
    @EnvironmentObject private var store: AppStore
    var categoryID: String
    @State private var sub = "all"
    @State private var sort: CatalogSort = .best
    @State private var showFilter = false

    private var category: Category? {
        store.categories.first { $0.id == categoryID }
    }

    private var subs: [String] {
        let values = Set(store.products.filter { $0.category == categoryID }.map(\.subcategory).filter { !$0.isEmpty })
        let preferred = ["tools", "prep", "cloths", "brushes", "bins", "shelves", "bowls", "care", "towels"]
        return preferred.filter { values.contains($0) } + values.filter { !preferred.contains($0) }.sorted()
    }

    private var results: [Product] {
        var list = store.products.filter { $0.category == categoryID }
        if sub != "all" {
            list = list.filter { $0.subcategory == sub }
        }
        return apply(sort, to: list)
    }

    var body: some View {
        VStack(spacing: 0) {
            HarborTitleBar(title: store.t(category?.name ?? categoryID.capitalized), trailing: store.t("Filter")) {
                showFilter = true
            }
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    Button { sub = "all" } label: {
                        HarborChip(title: store.t("All"), selected: sub == "all")
                    }
                    .buttonStyle(.plain)
                    ForEach(subs, id: \.self) { item in
                        Button { sub = item } label: {
                            HarborChip(title: subcategoryName(item), selected: sub == item)
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 8)
            }
            ScrollView {
                if results.isEmpty {
                    Text(store.t("Nothing in this aisle yet."))
                        .font(.system(size: 14))
                        .foregroundStyle(HarborColor.muted)
                        .frame(maxWidth: .infinity)
                        .padding(.top, 48)
                } else {
                    ProductGrid(products: results)
                        .padding(.horizontal, 16)
                        .padding(.bottom, 24)
                }
            }
        }
        .harborScreen()
        .confirmationDialog("Filter", isPresented: $showFilter, titleVisibility: .visible) {
            ForEach(CatalogSort.allCases) { item in
                Button(store.t(item.title)) { sort = item }
            }
            Button(store.t("Cancel"), role: .cancel) {}
        }
    }
}

struct CollectionView: View {
    @EnvironmentObject private var store: AppStore
    var kind: CollectionKind

    private var items: [Product] {
        switch kind {
        case .sale:
            let marked = store.products.filter { ($0.compareAt ?? 0) > $0.price }
            return marked.isEmpty ? store.products : marked
        case .newest:
            return Array(store.products.reversed().prefix(10))
        case .flash:
            return Array(store.products.sorted { $0.price < $1.price }.prefix(8))
        }
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                HarborTitleBar(title: store.t(kind.title))
                VStack(alignment: .leading, spacing: 2) {
                    Text(kind == .sale ? store.t("Kitchen deals") : store.t(kind.title))
                        .font(.system(size: 16, weight: .semibold))
                        .foregroundStyle(HarborColor.navy)
                    Text(store.t("Real sale items"))
                        .font(.system(size: 13))
                        .foregroundStyle(HarborColor.muted)
                }
                .padding(.horizontal, 16)
                ProductGrid(products: items)
                    .padding(.horizontal, 16)
                    .padding(.bottom, 24)
            }
        }
        .harborScreen()
    }
}

func apply(_ sort: CatalogSort, to products: [Product]) -> [Product] {
    switch sort {
    case .best:
        return products
    case .price:
        return products.sorted { $0.price < $1.price }
    case .newest:
        return products.reversed()
    }
}
