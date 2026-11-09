import SwiftUI

struct HomeView: View {
    @EnvironmentObject private var store: AppStore
    @State private var aisle = "foryou"
    @State private var shown = 20
    @State private var paging = false
    @State private var pageToken = 0
    @State private var tailTop: CGFloat = 0
    @State private var viewportBottom: CGFloat = 0

    private let pageSize = 20
    /// Start the next batch before the last row reaches the bottom edge.
    private let prefetchDistance: CGFloat = 400

    private var filtered: [Product] {
        if aisle == "foryou" { return store.products }
        return store.products.filter { $0.category == aisle }
    }

    private var visible: [Product] {
        Array(filtered.prefix(shown))
    }

    private var hasMore: Bool { shown < filtered.count }

    /// Tail is inside the scroll view, or within `prefetchDistance` below it.
    private var tailIsNear: Bool {
        guard viewportBottom > 1, tailTop > 1 else { return false }
        return tailTop < viewportBottom + prefetchDistance
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                header
                search
                promo
                entries
                chips
                sectionHead
                ProductGrid(products: visible)
                    .padding(.horizontal, 16)
                feedTail
            }
            .padding(.bottom, 12)
        }
        .background(viewportProbe)
        .onPreferenceChange(HomeTailTopKey.self) { value in
            tailTop = value
            requestNextPage()
        }
        .onPreferenceChange(HomeViewportBottomKey.self) { value in
            viewportBottom = value
            requestNextPage()
        }
        .refreshable { await store.loadCatalog() }
        .harborRoot()
        .onChange(of: aisle) { _ in
            pageToken += 1
            paging = false
            shown = pageSize
            requestNextPage()
        }
        .onChange(of: store.tab) { tab in
            if tab == .home {
                requestNextPage()
            } else {
                pageToken += 1
                paging = false
            }
        }
        .onDisappear {
            pageToken += 1
            paging = false
        }
    }

    private var header: some View {
        HStack(alignment: .center) {
            VStack(alignment: .leading, spacing: 0) {
                HStack(alignment: .firstTextBaseline, spacing: 6) {
                    Text("Harbor")
                        .font(.system(size: 20, weight: .bold))
                        .foregroundStyle(HarborColor.navy)
                    Text(store.t("small goods"))
                        .font(.system(size: 12, weight: .medium))
                        .foregroundStyle(HarborColor.teal)
                }
                Text(store.t("Cross-border household"))
                    .font(.system(size: 10))
                    .foregroundStyle(HarborColor.muted)
            }
            Spacer()
            Button {
                store.push(.locale)
            } label: {
                Text(store.language.endonym)
                    .font(.system(size: 11, weight: .medium))
                    .foregroundStyle(HarborColor.navy)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                    .background(Color.white)
                    .clipShape(Capsule())
                    .overlay(Capsule().stroke(HarborColor.line, lineWidth: 1))
            }
            .buttonStyle(.plain)
        }
        .padding(.horizontal, 16)
        .padding(.top, 4)
        .padding(.bottom, 8)
    }

    private var search: some View {
        Button {
            store.push(.search(""))
        } label: {
            HStack(spacing: 8) {
                Image(systemName: "magnifyingglass")
                    .font(.system(size: 16, weight: .light))
                    .foregroundStyle(HarborColor.muted)
                Text(store.t("Search kitchen, storage, cleaning…"))
                    .font(.system(size: 13))
                    .foregroundStyle(HarborColor.muted)
                Spacer()
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 11)
            .background(Color.white)
            .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .stroke(HarborColor.line, lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
        .padding(.horizontal, 16)
        .padding(.bottom, 10)
    }

    private var promo: some View {
        Button {
            store.push(.collection(.sale))
        } label: {
            HStack(spacing: 12) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(store.promo.kicker)
                        .font(.system(size: 10, weight: .semibold))
                        .foregroundStyle(HarborColor.promoKicker)
                    Text(store.promo.title)
                        .font(.system(size: 14, weight: .bold))
                        .foregroundStyle(.white)
                        .multilineTextAlignment(.leading)
                }
                Spacer(minLength: 8)
                Text("\(store.t(store.promo.cta)) →")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(HarborColor.teal)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 8)
                    .background(Color.white)
                    .clipShape(Capsule())
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 12)
            .background(HarborColor.teal)
            .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
        }
        .buttonStyle(.plain)
        .padding(.horizontal, 16)
        .padding(.bottom, 12)
    }

    private var entries: some View {
        VStack(spacing: 12) {
            HStack(spacing: 0) {
                entry("tag", store.t("Sale")) { store.push(.collection(.sale)) }
                entry("sparkles", store.t("New")) { store.push(.collection(.newest)) }
                entry("bolt", store.t("Flash")) { store.push(.collection(.flash)) }
                entry("ticket", store.t("Coupons")) { store.push(.coupons) }
                entry("calendar", store.t("Check-in")) { store.push(.balance) }
            }
            HStack(spacing: 0) {
                entry("wallet.pass", store.t("Balance")) { store.push(.balance) }
                entry("gift", store.t("Invite")) { store.push(.invite) }
                entry("heart", store.t("Wishlist")) { store.push(.wishlist) }
                entry("shippingbox", store.t("Orders")) { store.push(.orders(nil)) }
                entry("questionmark.circle", store.t("Help")) { store.push(.help) }
            }
        }
        .padding(.horizontal, 8)
        .padding(.bottom, 14)
    }

    private func entry(_ symbol: String, _ title: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            VStack(spacing: 6) {
                ZStack {
                    RoundedRectangle(cornerRadius: 14, style: .continuous)
                        .fill(HarborColor.iconBg)
                        .frame(width: 48, height: 48)
                    Image(systemName: symbol)
                        .font(.system(size: 20, weight: .light))
                        .foregroundStyle(HarborColor.navy)
                }
                Text(title)
                    .font(.system(size: 11, weight: .medium))
                    .foregroundStyle(HarborColor.navy)
                    .lineLimit(1)
                    .minimumScaleFactor(0.8)
            }
            .frame(maxWidth: .infinity)
        }
        .buttonStyle(.plain)
    }

    private var chips: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                Button { aisle = "foryou" } label: {
                        HarborChip(title: store.t("For you"), selected: aisle == "foryou")
                }
                .buttonStyle(.plain)
                ForEach(store.categories) { category in
                    Button { aisle = category.id } label: {
                        HarborChip(title: store.t(category.name), selected: aisle == category.id)
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.horizontal, 16)
        }
        .padding(.bottom, 12)
    }

    private var sectionHead: some View {
        HStack {
            Text(store.t("In the shop"))
                .font(.system(size: 16, weight: .bold))
                .foregroundStyle(HarborColor.navy)
            Spacer()
            Text(sectionNote)
                .font(.system(size: 11))
                .foregroundStyle(HarborColor.muted)
        }
        .padding(.horizontal, 16)
        .padding(.bottom, 10)
    }

    private var sectionNote: String {
        guard !visible.isEmpty else { return "" }
        return String(format: store.t("Showing %d"), visible.count)
    }

    /// Bottom of the feed. More products append themselves as this edge nears the viewport.
    @ViewBuilder
    private var feedTail: some View {
        if filtered.isEmpty {
            Text(store.isLoading ? store.t("Loading the shop…") : store.t("Nothing in this aisle yet."))
                .font(.system(size: 13))
                .foregroundStyle(HarborColor.muted)
                .frame(maxWidth: .infinity)
                .padding(.top, 28)
                .padding(.bottom, 12)
        } else if hasMore {
            VStack(spacing: 0) {
                if paging {
                    ProgressView()
                        .controlSize(.small)
                        .tint(HarborColor.teal)
                        .padding(.top, 18)
                        .padding(.bottom, 8)
                        .accessibilityHidden(true)
                }
                Color.clear
                    .frame(height: 1)
                    .background(tailProbe)
            }
            .frame(maxWidth: .infinity)
            .padding(.bottom, 12)
        }
    }

    private var tailProbe: some View {
        GeometryReader { proxy in
            Color.clear.preference(key: HomeTailTopKey.self, value: proxy.frame(in: .global).minY)
        }
    }

    private var viewportProbe: some View {
        GeometryReader { proxy in
            Color.clear.preference(key: HomeViewportBottomKey.self, value: proxy.frame(in: .global).maxY)
        }
    }

    /// Appends the next page while the tail stays near the bottom. No pull gesture.
    private func requestNextPage() {
        guard !paging, hasMore, tailIsNear, store.tab == .home else { return }
        paging = true
        pageToken += 1
        let token = pageToken
        Task { @MainActor in
            await runPaging(token: token)
        }
    }

    private func runPaging(token: Int) async {
        defer {
            if token == pageToken { paging = false }
        }
        while token == pageToken, hasMore, tailIsNear, store.tab == .home {
            let previousTail = tailTop
            try? await Task.sleep(nanoseconds: 80_000_000)
            guard token == pageToken, hasMore, tailIsNear, store.tab == .home else { return }
            shown = min(shown + pageSize, filtered.count)
            // Layout has to publish a new tail position before another batch is allowed.
            var spins = 0
            while token == pageToken, tailTop == previousTail, spins < 8 {
                try? await Task.sleep(nanoseconds: 16_000_000)
                spins += 1
            }
            guard token == pageToken, tailTop != previousTail else { return }
        }
    }
}

private struct HomeTailTopKey: PreferenceKey {
    static var defaultValue: CGFloat = 0
    static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) {
        value = nextValue()
    }
}

private struct HomeViewportBottomKey: PreferenceKey {
    static var defaultValue: CGFloat = 0
    static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) {
        value = nextValue()
    }
}
