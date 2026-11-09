import Foundation

enum AppTab: String, CaseIterable, Identifiable {
    case home, browse, cart, me
    var id: String { rawValue }
    var title: String {
        switch self {
        case .home: return "Home"
        case .browse: return "Browse"
        case .cart: return "Cart"
        case .me: return "Me"
        }
    }
    var symbol: String {
        switch self {
        case .home: return "house"
        case .browse: return "square.grid.2x2"
        case .cart: return "cart"
        case .me: return "person"
        }
    }
}

/// Shop page shown with the native back bar: help articles, policies, contact,
/// account deletion, and Manage on payments or addresses.
struct InAppWebRoute: Hashable {
    var url: URL
    var title: String
}

enum Route: Hashable {
    case search(String)
    case category(String)
    case product(String)
    case orders(OrderStatus?)
    case order(String)
    case wishlist
    case coupons
    case balance
    case invite
    case locale
    case help
    case chat(String?)
    case addresses
    case history
    case compare
    case payments
    case returns(String)
    case collection(CollectionKind)
    case success(String)
    case checkout
    case policy(String)
    case inAppWeb(InAppWebRoute)
}

enum CollectionKind: String, Hashable {
    case sale, newest, flash
    var title: String {
        switch self {
        case .sale: return "Sale"
        case .newest: return "New"
        case .flash: return "Flash"
        }
    }
}

enum OrderStatus: String, Codable, Hashable, CaseIterable, Identifiable {
    case toPay, paid, shipped, returns
    var id: String { rawValue }
    var title: String {
        switch self {
        case .toPay: return "To pay"
        case .paid: return "Paid"
        case .shipped: return "Shipped"
        case .returns: return "Returns"
        }
    }
}

enum HarborLanguage: String, Codable, CaseIterable, Identifiable {
    case en, es, de, fr, pt, ja, zh
    case zhHant = "zh-Hant"

    var id: String { rawValue }

    /// Same order and names as the Harbor shop language picker.
    static let pickerOrder: [HarborLanguage] = [.en, .zh, .zhHant, .ja, .de, .fr, .es, .pt]

    var endonym: String {
        switch self {
        case .en: return "English"
        case .zh: return "简体中文"
        case .zhHant: return "繁體中文"
        case .ja: return "日本語"
        case .de: return "Deutsch"
        case .fr: return "Français"
        case .es: return "Español"
        case .pt: return "Português"
        }
    }
}

enum HarborCurrency: String, Codable {
    case usd, eur, gbp, jpy, cny, twd, hkd, cad, aud, brl, mxn, krw, inr, sgd, chf, sek, nok, dkk, pln, nzd

    var code: String { rawValue.uppercased() }
    var decimals: Int {
        switch self {
        case .jpy, .krw: return 0
        default: return 2
        }
    }
    /// Display rate from the shop’s USD price. Not a live FX quote.
    var perUSD: Double {
        switch self {
        case .usd: return 1
        case .eur: return 0.92
        case .gbp: return 0.78
        case .jpy: return 150
        case .cny: return 7.2
        case .twd: return 32
        case .hkd: return 7.8
        case .cad: return 1.36
        case .aud: return 1.52
        case .brl: return 5.6
        case .mxn: return 18
        case .krw: return 1350
        case .inr: return 84
        case .sgd: return 1.34
        case .chf: return 0.88
        case .sek: return 10.5
        case .nok: return 10.8
        case .dkk: return 6.9
        case .pln: return 4.0
        case .nzd: return 1.66
        }
    }
    var formatLocale: String {
        switch self {
        case .usd: return "en_US"
        case .eur: return "de_DE"
        case .gbp: return "en_GB"
        case .jpy: return "ja_JP"
        case .cny: return "zh_CN"
        case .twd: return "zh_TW"
        case .hkd: return "zh_HK"
        case .cad: return "en_CA"
        case .aud: return "en_AU"
        case .brl: return "pt_BR"
        case .mxn: return "es_MX"
        case .krw: return "ko_KR"
        case .inr: return "en_IN"
        case .sgd: return "en_SG"
        case .chf: return "de_CH"
        case .sek: return "sv_SE"
        case .nok: return "nb_NO"
        case .dkk: return "da_DK"
        case .pln: return "pl_PL"
        case .nzd: return "en_NZ"
        }
    }

    static func from(countryCode raw: String) -> HarborCurrency {
        switch raw.uppercased() {
        case "US", "PR", "EC", "SV", "PA": return .usd
        case "GB", "UK": return .gbp
        case "JP": return .jpy
        case "CN": return .cny
        case "TW": return .twd
        case "HK", "MO": return .hkd
        case "CA": return .cad
        case "AU": return .aud
        case "NZ": return .nzd
        case "BR": return .brl
        case "MX": return .mxn
        case "KR": return .krw
        case "IN": return .inr
        case "SG": return .sgd
        case "CH", "LI": return .chf
        case "SE": return .sek
        case "NO": return .nok
        case "DK": return .dkk
        case "PL": return .pln
        case "DE", "FR", "ES", "PT", "IT", "NL", "BE", "AT", "IE", "FI", "GR", "LU", "SK", "SI", "EE", "LV", "LT", "CY", "MT":
            return .eur
        default:
            return .usd
        }
    }
}

struct SpecRow: Decodable, Hashable, Identifiable {
    var name: String
    var value: String
    var id: String { name }
}

enum PaymentKind: String, Codable, CaseIterable, Identifiable {
    case paypal, card, lianlian
    var id: String { rawValue }
    var title: String {
        switch self {
        case .paypal: return "PayPal"
        case .card: return "Card (Stripe)"
        case .lianlian: return "LianLian"
        }
    }
}

enum AuthMode: String, Identifiable {
    case signIn, register
    var id: String { rawValue }
}

struct Promo: Decodable, Hashable {
    var kicker: String
    var title: String
    var cta: String
}

struct Category: Decodable, Identifiable, Hashable {
    var id: String
    var name: String
    var subtitle: String
}

struct SKU: Identifiable, Decodable, Hashable {
    var id: String
    var label: String
    var price: Double
    var compareAt: Double?
    var image: String
    var inStock: Bool

    enum CodingKeys: String, CodingKey {
        case id, sku, label, name, title, price, compareAt, compare_at, original
        case image, imageURL, inStock, stock
    }

    init(id: String, label: String, price: Double, compareAt: Double?, image: String, inStock: Bool) {
        self.id = id
        self.label = label
        self.price = price
        self.compareAt = compareAt
        self.image = image
        self.inStock = inStock
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        if let s = try? c.decode(String.self, forKey: .id) {
            id = s
        } else if let s = try? c.decode(String.self, forKey: .sku) {
            id = s
        } else if let n = try? c.decode(Int.self, forKey: .id) {
            id = String(n)
        } else {
            id = UUID().uuidString
        }
        label = Self.string(c, .label) ?? Self.string(c, .name) ?? Self.string(c, .title) ?? "Standard"
        price = Self.double(c, .price) ?? 0
        compareAt = Self.double(c, .compareAt) ?? Self.double(c, .compare_at) ?? Self.double(c, .original)
        image = harborAbsoluteURL(Self.string(c, .image) ?? Self.string(c, .imageURL) ?? "")
        if let stock = try? c.decode(Bool.self, forKey: .inStock) {
            inStock = stock
        } else if let qty = try? c.decode(Int.self, forKey: .stock) {
            inStock = qty > 0
        } else {
            inStock = true
        }
    }

    private static func string(_ c: KeyedDecodingContainer<CodingKeys>, _ key: CodingKeys) -> String? {
        if let s = try? c.decode(String.self, forKey: key) { return s }
        if let n = try? c.decode(Int.self, forKey: key) { return String(n) }
        return nil
    }

    private static func double(_ c: KeyedDecodingContainer<CodingKeys>, _ key: CodingKeys) -> Double? {
        if let d = try? c.decode(Double.self, forKey: key) { return d }
        if let i = try? c.decode(Int.self, forKey: key) { return Double(i) }
        if let s = try? c.decode(String.self, forKey: key) {
            let cleaned = s.replacingOccurrences(of: "$", with: "").replacingOccurrences(of: ",", with: "")
            return Double(cleaned)
        }
        return nil
    }
}

func harborAbsoluteURL(_ raw: String) -> String {
    if raw.hasPrefix("http://") || raw.hasPrefix("https://") { return raw }
    if raw.hasPrefix("/") { return "https://linkiip.com" + raw }
    return raw
}

struct Product: Identifiable, Decodable, Hashable {
    var id: String
    var title: String
    var price: Double
    var compareAt: Double?
    var image: String
    var images: [String]
    var category: String
    var subcategory: String
    var interest: Int
    var interestKind: String
    var tracked: Bool
    var shipsIn: String
    var inStock: Bool
    var description: String
    var specs: [SpecRow]
    var skus: [SKU]

    enum CodingKeys: String, CodingKey {
        case id, title, name, price, compareAt, compare_at, image, imageURL, images
        case category, categoryId, dept, subcategory, interest, interestKind
        case tracked, shipsIn, inStock, availability, description, specs, skus, variants, offers
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        if let s = try? c.decode(String.self, forKey: .id) {
            id = s
        } else if let n = try? c.decode(Int.self, forKey: .id) {
            id = String(n)
        } else {
            throw DecodingError.dataCorrupted(.init(codingPath: decoder.codingPath, debugDescription: "Missing product id"))
        }
        title = Self.string(c, .title) ?? Self.string(c, .name) ?? "Harbor item"
        price = Self.double(c, .price) ?? 0
        compareAt = Self.double(c, .compareAt) ?? Self.double(c, .compare_at)
        image = harborAbsoluteURL(Self.string(c, .image) ?? Self.string(c, .imageURL) ?? "")
        let rawImages = (try? c.decode([String].self, forKey: .images)) ?? []
        let gallery = [image] + rawImages.map(harborAbsoluteURL)
        var seen = Set<String>()
        images = gallery.filter { seen.insert($0).inserted && !$0.isEmpty }
        if image.isEmpty { image = images.first ?? "" }
        category = (Self.string(c, .category) ?? Self.string(c, .categoryId) ?? Self.string(c, .dept) ?? "kitchen").lowercased()
        subcategory = (Self.string(c, .subcategory) ?? "").lowercased()
        interest = Self.int(c, .interest) ?? 0
        interestKind = Self.string(c, .interestKind) ?? "interested"
        tracked = (try? c.decode(Bool.self, forKey: .tracked)) ?? true
        shipsIn = Self.string(c, .shipsIn) ?? "7–12 days"
        if let stock = try? c.decode(Bool.self, forKey: .inStock) {
            inStock = stock
        } else if let availability = Self.string(c, .availability)?.lowercased() {
            inStock = !availability.contains("outofstock") && !availability.contains("sold")
        } else {
            inStock = true
        }
        description = Self.string(c, .description) ?? ""
        specs = ((try? c.decode([SpecRow].self, forKey: .specs)) ?? []).filter { !$0.name.isEmpty && !$0.value.isEmpty }
        skus = (try? c.decode([SKU].self, forKey: .skus))
            ?? (try? c.decode([SKU].self, forKey: .variants))
            ?? (try? c.decode([SKU].self, forKey: .offers))
            ?? []
        if skus.isEmpty {
            skus = [SKU(id: id + "-default", label: "Standard", price: price, compareAt: compareAt, image: image, inStock: inStock)]
        }
    }

    private static func string(_ c: KeyedDecodingContainer<CodingKeys>, _ key: CodingKeys) -> String? {
        if let s = try? c.decode(String.self, forKey: key) { return s }
        if let n = try? c.decode(Int.self, forKey: key) { return String(n) }
        return nil
    }

    private static func double(_ c: KeyedDecodingContainer<CodingKeys>, _ key: CodingKeys) -> Double? {
        if let d = try? c.decode(Double.self, forKey: key) { return d }
        if let i = try? c.decode(Int.self, forKey: key) { return Double(i) }
        if let s = try? c.decode(String.self, forKey: key) {
            let cleaned = s.replacingOccurrences(of: "$", with: "").replacingOccurrences(of: ",", with: "")
            return Double(cleaned)
        }
        return nil
    }

    private static func int(_ c: KeyedDecodingContainer<CodingKeys>, _ key: CodingKeys) -> Int? {
        if let i = try? c.decode(Int.self, forKey: key) { return i }
        if let d = try? c.decode(Double.self, forKey: key) { return Int(d) }
        if let s = try? c.decode(String.self, forKey: key) { return Int(s) }
        return nil
    }
}

struct HomeFeed: Decodable {
    var promo: Promo
    var categories: [Category]
    var products: [Product]

    enum CodingKeys: String, CodingKey {
        case promo, categories, products, items
    }

    init(promo: Promo, categories: [Category], products: [Product]) {
        self.promo = promo
        self.categories = categories
        self.products = products
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        promo = (try? c.decode(Promo.self, forKey: .promo)) ?? Promo(
            kicker: "THIS WEEK",
            title: "Kitchen refresh · up to 30% off",
            cta: "Shop"
        )
        categories = (try? c.decode([Category].self, forKey: .categories)) ?? Category.defaults
        products = (try? c.decode([Product].self, forKey: .products))
            ?? (try? c.decode([Product].self, forKey: .items))
            ?? []
    }
}

extension Category {
    static let defaults: [Category] = [
        Category(id: "kitchen", name: "Kitchen", subtitle: "Tools · prep"),
        Category(id: "cleaning", name: "Cleaning", subtitle: "Cloths · brushes"),
        Category(id: "storage", name: "Storage", subtitle: "Bins · shelves"),
        Category(id: "pet", name: "Pet", subtitle: "Bowls · care"),
        Category(id: "bath", name: "Bath", subtitle: "Towels · care")
    ]

    static let browseOrder = ["kitchen", "cleaning", "storage", "pet"]

    var symbol: String {
        switch id {
        case "kitchen": return "fork.knife"
        case "cleaning": return "sparkles"
        case "storage": return "archivebox"
        case "pet": return "pawprint"
        case "bath": return "drop"
        default: return "square.grid.2x2"
        }
    }
}

struct CartLine: Identifiable, Codable, Hashable {
    var id: String { "\(productID)|\(skuID)" }
    var productID: String
    var skuID: String
    var title: String
    var skuLabel: String
    var price: Double
    var imageURL: String
    var quantity: Int
}

struct Address: Identifiable, Codable, Hashable {
    var id: UUID
    var name: String
    var line: String
    var isDefault: Bool

    var summary: String { "\(name) · \(line)" }
}

struct Session: Codable, Equatable {
    var name: String
    var email: String
    var initials: String
    var provider: String? = nil

    var providerTitle: String? {
        guard let provider, !provider.isEmpty, provider != "email" else { return nil }
        return SocialProvider(rawValue: provider)?.title
    }
}

struct StoreOrder: Identifiable, Codable, Hashable {
    var id: String
    var created: Date
    var status: OrderStatus
    var email: String
    var address: String
    var payment: String
    var lines: [CartLine]
    var total: Double
    var tracking: String?
}

struct ChatMessage: Identifiable, Hashable {
    var id = UUID()
    var fromShop: Bool
    var text: String
    var productID: String? = nil
    var orderID: String? = nil
}

struct Coupon: Identifiable, Hashable {
    var id: String
    var amount: Double
    var code: String
    var detail: String
}
