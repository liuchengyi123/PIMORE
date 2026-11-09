import Foundation
import Network
import SwiftUI

@MainActor
final class AppStore: ObservableObject {
    @Published var tab: AppTab = .home
    @Published var homePath = NavigationPath()
    @Published var browsePath = NavigationPath()
    @Published var cartPath = NavigationPath()
    @Published var mePath = NavigationPath()

    @Published var products: [Product] = []
    @Published var categories: [Category] = Category.defaults
    @Published var promo = Promo(kicker: "THIS WEEK", title: "Kitchen refresh · up to 30% off", cta: "Shop")
    @Published var usedMock = false
    @Published var isLoading = false
    @Published var isOffline = false
    @Published var legal: ComplianceConfig = .fallback

    @Published var cart: [CartLine] = []
    @Published var orders: [StoreOrder] = []
    @Published var wishlist: [String] = []
    @Published var history: [String] = []
    @Published var compare: [String] = []
    @Published var session: Session?
    @Published var language: HarborLanguage = .en
    @Published var currency: HarborCurrency = .usd
    @Published var balance: Double = 0
    @Published var streak: Int = 0
    @Published var lastCheckIn: Date?
    @Published var addresses: [Address] = []
    @Published var payment: PaymentKind = .paypal
    @Published var couponArmed = false
    @Published var notifyIDs: [String] = []
    @Published var authMode: AuthMode?
    @Published var chat: [ChatMessage] = []
    @Published var chatTyping = false

    let coupons: [Coupon] = [
        Coupon(id: "WELCOME5", amount: 5, code: "WELCOME5", detail: "Over $20 · Dec 31")
    ]

    private let monitor = NWPathMonitor()
    private let monitorQueue = DispatchQueue(label: "harbor.network")
    private let defaultsKey = "harbor.snapshot.v1"
    private let api = HarborAPI()

    var cartCount: Int { cart.reduce(0) { $0 + $1.quantity } }
    var subtotal: Double { cart.reduce(0) { $0 + $1.price * Double($1.quantity) } }
    var discount: Double {
        guard couponArmed, subtotal >= 20 else { return 0 }
        return coupons.first?.amount ?? 0
    }
    var payable: Double { max(0, subtotal - discount) }
    var checkedInToday: Bool {
        guard let lastCheckIn else { return false }
        return Calendar.current.isDateInToday(lastCheckIn)
    }
    var defaultAddress: Address? {
        addresses.first(where: \.isDefault) ?? addresses.first
    }

    init() {
        if addresses.isEmpty {
            addresses = [
                Address(id: UUID(), name: "Alex Miller", line: "221 Market St · SF, CA 94105", isDefault: true)
            ]
        }
        restore()
        monitor.pathUpdateHandler = { [weak self] path in
            let offline = path.status != .satisfied
            Task { @MainActor in
                self?.isOffline = offline
            }
        }
        monitor.start(queue: monitorQueue)
        Task {
            async let catalog: Void = loadCatalog()
            async let geo: Void = refreshGeoCurrency()
            _ = await (catalog, geo)
        }
        Task { await loadLegal() }
    }

    func t(_ key: String) -> String {
        HarborCopy.text(key, language)
    }

    func interestLine(_ product: Product) -> String {
        let key = product.interestKind == "watching" ? "%d watching" : "%d interested"
        return String(format: t(key), product.interest)
    }

    func peopleInterested(_ count: Int) -> String {
        String(format: t("%d people are interested"), count)
    }

    func loadLegal() async {
        legal = await LegalUrls.load()
    }

    func loadCatalog() async {
        isLoading = true
        defer { isLoading = false }
        if let feed = try? await api.home(), !feed.products.isEmpty {
            apply(feed, mock: false)
            return
        }
        if let list = try? await api.products(), !list.isEmpty {
            products = list
            usedMock = false
            return
        }
        if let feed = HarborMock.bundled() {
            apply(feed, mock: true)
        }
    }

    func refresh(_ id: String) async {
        guard let product = try? await api.product(id: id) else { return }
        if let index = products.firstIndex(where: { $0.id == id }) {
            products[index] = product
        } else {
            products.append(product)
        }
    }

    func product(_ id: String) -> Product? {
        products.first { $0.id == id }
    }

    func setLanguage(_ value: HarborLanguage) {
        language = value
        save()
    }

    /// Currency comes from IP/geo only. Language never writes this.
    func refreshGeoCurrency() async {
        guard let info = await GeoCountry.detectInfo() else { return }
        currency = HarborCurrency.from(countryCode: info.country)
        save()
    }

    func setPayment(_ value: PaymentKind) {
        payment = value
        save()
    }

    func money(_ usd: Double) -> String {
        let value = usd * currency.perUSD
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = currency.code
        formatter.locale = Locale(identifier: currency.formatLocale)
        formatter.minimumFractionDigits = currency.decimals
        formatter.maximumFractionDigits = currency.decimals
        return formatter.string(from: NSNumber(value: value)) ?? "\(currency.code) \(value)"
    }

    func push(_ route: Route) {
        switch tab {
        case .home: homePath.append(route)
        case .browse: browsePath.append(route)
        case .cart: cartPath.append(route)
        case .me: mePath.append(route)
        }
    }

    func pop() {
        switch tab {
        case .home: if !homePath.isEmpty { homePath.removeLast() }
        case .browse: if !browsePath.isEmpty { browsePath.removeLast() }
        case .cart: if !cartPath.isEmpty { cartPath.removeLast() }
        case .me: if !mePath.isEmpty { mePath.removeLast() }
        }
    }

    func replaceTop(with route: Route) {
        pop()
        push(route)
    }

    func goHome() {
        tab = .home
        homePath = NavigationPath()
        browsePath = NavigationPath()
        cartPath = NavigationPath()
        mePath = NavigationPath()
    }

    func openCategory(_ id: String) {
        push(.category(id))
    }

    func addToCart(product: Product, sku: SKU, quantity: Int) {
        let qty = max(1, quantity)
        if let index = cart.firstIndex(where: { $0.productID == product.id && $0.skuID == sku.id }) {
            cart[index].quantity += qty
        } else {
            cart.append(CartLine(
                productID: product.id,
                skuID: sku.id,
                title: product.title,
                skuLabel: sku.label,
                price: sku.price,
                imageURL: sku.image.isEmpty ? product.image : sku.image,
                quantity: qty
            ))
        }
        save()
    }

    func changeQty(_ line: CartLine, by delta: Int) {
        guard let index = cart.firstIndex(where: { $0.id == line.id }) else { return }
        cart[index].quantity += delta
        if cart[index].quantity <= 0 {
            cart.remove(at: index)
        }
        save()
    }

    func toggleWishlist(_ id: String) {
        if let index = wishlist.firstIndex(of: id) {
            wishlist.remove(at: index)
        } else {
            wishlist.insert(id, at: 0)
        }
        save()
    }

    func remember(_ id: String) {
        history.removeAll { $0 == id }
        history.insert(id, at: 0)
        if history.count > 40 { history = Array(history.prefix(40)) }
        save()
    }

    func toggleCompare(_ id: String) {
        if let index = compare.firstIndex(of: id) {
            compare.remove(at: index)
        } else {
            if compare.count >= 2 { compare.removeFirst() }
            compare.append(id)
        }
        save()
    }

    func signIn(email rawEmail: String, password: String) -> String? {
        let email = rawEmail.trimmingCharacters(in: .whitespacesAndNewlines)
        guard email.contains("@"), email.contains("."), password.count >= 4 else {
            return "Use a valid email and a password of at least 4 characters."
        }
        let name: String
        if email.lowercased() == "alex@example.com" {
            name = "Alex Miller"
        } else {
            let local = email.split(separator: "@").first.map(String.init) ?? "Harbor"
            name = local.prefix(1).uppercased() + local.dropFirst()
        }
        applySession(name: name, email: email, provider: SocialProvider.email.rawValue)
        return nil
    }

    func finishSocial(_ profile: SocialProfile) async {
        let remote = try? await api.submitSocial(profile)
        let name = Self.filled(remote?.name) ?? Self.filled(profile.name) ?? profile.provider.fallbackName
        let email = Self.filled(remote?.email) ?? Self.filled(profile.email) ?? "\(profile.provider.rawValue)@harbor.local"
        applySession(name: name, email: email, provider: profile.provider.rawValue)
    }

    func open(_ url: URL) {
        if url.scheme == "harbor", url.host == "oauth" { return }
        let parts = url.path.split(separator: "/").map(String.init)
        let id: String?
        if parts.count >= 2, parts[0] == "p" {
            id = parts[1]
        } else if url.host == "p" {
            id = parts.first
        } else {
            id = nil
        }
        guard let id, !id.isEmpty else { return }
        tab = .home
        homePath = NavigationPath()
        homePath.append(Route.product(id))
    }

    func signOut() {
        SocialAuthController.logout()
        session = nil
        save()
    }

    private func applySession(name: String, email: String, provider: String) {
        let initials = name.split(separator: " ").prefix(2).compactMap(\.first).map(String.init).joined().uppercased()
        session = Session(name: name, email: email, initials: initials.isEmpty ? "H" : initials, provider: provider)
        authMode = nil
        save()
    }

    private static func filled(_ raw: String?) -> String? {
        let trimmed = raw?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        return trimmed.isEmpty ? nil : trimmed
    }

    func claimCheckIn() {
        guard !checkedInToday else { return }
        if let lastCheckIn, Calendar.current.isDateInYesterday(lastCheckIn) {
            streak += 1
        } else {
            streak = 1
        }
        lastCheckIn = Date()
        balance += 0.20
        save()
    }

    func placeOrder(email: String, address: String) -> StoreOrder {
        let number = 100000 + Int.random(in: 0...89999)
        let order = StoreOrder(
            id: "HB-\(number)",
            created: Date(),
            status: .paid,
            email: email,
            address: address,
            payment: payment.title,
            lines: cart,
            total: payable,
            tracking: nil
        )
        orders.insert(order, at: 0)
        cart.removeAll()
        couponArmed = false
        save()
        return order
    }

    func requestReturn(_ id: String) {
        guard let index = orders.firstIndex(where: { $0.id == id }) else { return }
        orders[index].status = .returns
        save()
    }

    func selectAddress(_ id: UUID) {
        for index in addresses.indices {
            addresses[index].isDefault = addresses[index].id == id
        }
        save()
    }

    func addAddress(name: String, line: String) {
        let address = Address(id: UUID(), name: name, line: line, isDefault: addresses.isEmpty)
        addresses.append(address)
        if addresses.count == 1 { addresses[0].isDefault = true }
        save()
    }

    func sendChat(_ text: String) {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        chat.append(ChatMessage(fromShop: false, text: trimmed))
        replyLater()
    }

    func sendProductToChat(_ id: String) {
        guard product(id) != nil else { return }
        chat.append(ChatMessage(fromShop: false, text: "", productID: id))
        replyLater()
    }

    func sendOrderToChat(_ id: String) {
        guard orders.contains(where: { $0.id == id }) else { return }
        chat.append(ChatMessage(fromShop: false, text: "", orderID: id))
        replyLater()
    }

    private func replyLater() {
        chatTyping = true
        Task {
            try? await Task.sleep(nanoseconds: 700_000_000)
            chatTyping = false
            chat.append(ChatMessage(fromShop: true, text: "Thanks — we’ll follow up on orders, shipping, and products."))
        }
    }

    func notify(_ id: String) {
        if !notifyIDs.contains(id) { notifyIDs.append(id) }
        save()
    }

    func orders(matching status: OrderStatus?) -> [StoreOrder] {
        guard let status else { return orders }
        return orders.filter { $0.status == status }
    }

    func count(_ status: OrderStatus) -> Int {
        orders.filter { $0.status == status }.count
    }

    private func apply(_ feed: HomeFeed, mock: Bool) {
        products = feed.products
        if !feed.categories.isEmpty { categories = feed.categories }
        promo = feed.promo
        usedMock = mock
    }

    private struct Snapshot: Codable {
        var cart: [CartLine]
        var orders: [StoreOrder]
        var wishlist: [String]
        var history: [String]
        var compare: [String]
        var session: Session?
        var language: HarborLanguage
        var currency: HarborCurrency
        var balance: Double
        var streak: Int
        var lastCheckIn: Date?
        var addresses: [Address]
        var payment: PaymentKind
        var notifyIDs: [String]

        enum CodingKeys: String, CodingKey {
            case cart, orders, wishlist, history, compare, session, language, currency, locale
            case balance, streak, lastCheckIn, addresses, payment, notifyIDs
        }

        init(cart: [CartLine], orders: [StoreOrder], wishlist: [String], history: [String], compare: [String], session: Session?, language: HarborLanguage, currency: HarborCurrency, balance: Double, streak: Int, lastCheckIn: Date?, addresses: [Address], payment: PaymentKind, notifyIDs: [String]) {
            self.cart = cart
            self.orders = orders
            self.wishlist = wishlist
            self.history = history
            self.compare = compare
            self.session = session
            self.language = language
            self.currency = currency
            self.balance = balance
            self.streak = streak
            self.lastCheckIn = lastCheckIn
            self.addresses = addresses
            self.payment = payment
            self.notifyIDs = notifyIDs
        }

        init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self)
            cart = (try? c.decode([CartLine].self, forKey: .cart)) ?? []
            orders = (try? c.decode([StoreOrder].self, forKey: .orders)) ?? []
            wishlist = (try? c.decode([String].self, forKey: .wishlist)) ?? []
            history = (try? c.decode([String].self, forKey: .history)) ?? []
            compare = (try? c.decode([String].self, forKey: .compare)) ?? []
            session = try? c.decode(Session.self, forKey: .session)
            if let language = try? c.decode(HarborLanguage.self, forKey: .language) {
                self.language = language
            } else {
                switch (try? c.decode(String.self, forKey: .locale)) ?? "" {
                case "cn": self.language = .zh
                case "jp": self.language = .ja
                default: self.language = .en
                }
            }
            // Old builds stored currency inside locale. Ignore that and keep USD until geo refresh.
            currency = (try? c.decode(HarborCurrency.self, forKey: .currency)) ?? .usd
            balance = (try? c.decode(Double.self, forKey: .balance)) ?? 0
            streak = (try? c.decode(Int.self, forKey: .streak)) ?? 0
            lastCheckIn = try? c.decode(Date.self, forKey: .lastCheckIn)
            addresses = (try? c.decode([Address].self, forKey: .addresses)) ?? []
            payment = (try? c.decode(PaymentKind.self, forKey: .payment)) ?? .paypal
            notifyIDs = (try? c.decode([String].self, forKey: .notifyIDs)) ?? []
        }

        func encode(to encoder: Encoder) throws {
            var c = encoder.container(keyedBy: CodingKeys.self)
            try c.encode(cart, forKey: .cart)
            try c.encode(orders, forKey: .orders)
            try c.encode(wishlist, forKey: .wishlist)
            try c.encode(history, forKey: .history)
            try c.encode(compare, forKey: .compare)
            try c.encodeIfPresent(session, forKey: .session)
            try c.encode(language, forKey: .language)
            try c.encode(currency, forKey: .currency)
            try c.encode(balance, forKey: .balance)
            try c.encode(streak, forKey: .streak)
            try c.encodeIfPresent(lastCheckIn, forKey: .lastCheckIn)
            try c.encode(addresses, forKey: .addresses)
            try c.encode(payment, forKey: .payment)
            try c.encode(notifyIDs, forKey: .notifyIDs)
        }
    }

    private func save() {
        let snapshot = Snapshot(
            cart: cart,
            orders: orders,
            wishlist: wishlist,
            history: history,
            compare: compare,
            session: session,
            language: language,
            currency: currency,
            balance: balance,
            streak: streak,
            lastCheckIn: lastCheckIn,
            addresses: addresses,
            payment: payment,
            notifyIDs: notifyIDs
        )
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        if let data = try? encoder.encode(snapshot) {
            UserDefaults.standard.set(data, forKey: defaultsKey)
        }
    }

    private func restore() {
        guard let data = UserDefaults.standard.data(forKey: defaultsKey) else { return }
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        guard let snapshot = try? decoder.decode(Snapshot.self, from: data) else { return }
        cart = snapshot.cart
        orders = snapshot.orders
        wishlist = snapshot.wishlist
        history = snapshot.history
        compare = snapshot.compare
        session = snapshot.session
        language = snapshot.language
        currency = snapshot.currency
        balance = snapshot.balance
        streak = snapshot.streak
        lastCheckIn = snapshot.lastCheckIn
        if !snapshot.addresses.isEmpty { addresses = snapshot.addresses }
        payment = snapshot.payment
        notifyIDs = snapshot.notifyIDs
    }
}
