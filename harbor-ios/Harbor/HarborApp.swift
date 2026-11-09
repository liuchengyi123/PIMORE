import SwiftUI

@main
struct HarborApp: App {
    @StateObject private var store = AppStore()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(store)
                .preferredColorScheme(.light)
                .tint(HarborColor.navy)
                .onOpenURL { url in
                    if SocialAuthController.consume(url) { return }
                    store.open(url)
                }
                .onContinueUserActivity(NSUserActivityTypeBrowsingWeb) { activity in
                    if let url = activity.webpageURL {
                        store.open(url)
                    }
                }
        }
    }
}

struct RootView: View {
    @EnvironmentObject private var store: AppStore

    var body: some View {
        ZStack {
            TabView(selection: $store.tab) {
                NavigationStack(path: $store.homePath) {
                    HomeView()
                        .navigationDestination(for: Route.self) { RouteHost(route: $0) }
                }
                .tag(AppTab.home)

                NavigationStack(path: $store.browsePath) {
                    BrowseView()
                        .navigationDestination(for: Route.self) { RouteHost(route: $0) }
                }
                .tag(AppTab.browse)

                NavigationStack(path: $store.cartPath) {
                    CartView()
                        .navigationDestination(for: Route.self) { RouteHost(route: $0) }
                }
                .tag(AppTab.cart)

                NavigationStack(path: $store.mePath) {
                    MeView()
                        .navigationDestination(for: Route.self) { RouteHost(route: $0) }
                }
                .tag(AppTab.me)
            }
            if store.isOffline {
                OfflineView()
            }
        }
    }
}

struct RouteHost: View {
    var route: Route

    var body: some View {
        switch route {
        case .search(let query):
            SearchView(initialQuery: query)
        case .category(let id):
            CategoryView(categoryID: id)
        case .product(let id):
            ProductDetailView(productID: id)
        case .orders(let status):
            OrdersView(initial: status)
        case .order(let id):
            OrderDetailView(orderID: id)
        case .wishlist:
            WishlistView()
        case .coupons:
            CouponsView()
        case .balance:
            BalanceView()
        case .invite:
            InviteView()
        case .locale:
            LocaleView()
        case .help:
            HelpView()
        case .chat(let topic):
            ChatView(topic: topic)
        case .addresses:
            AddressesView()
        case .history:
            HistoryView()
        case .compare:
            CompareView()
        case .payments:
            PaymentsView()
        case .returns(let id):
            ReturnView(orderID: id)
        case .collection(let kind):
            CollectionView(kind: kind)
        case .success(let id):
            SuccessView(orderID: id)
        case .checkout:
            CheckoutView()
        case .policy(let id):
            PolicyView(page: id)
        case .inAppWeb(let route):
            InAppWebScreen(url: route.url, title: route.title)
        }
    }
}
