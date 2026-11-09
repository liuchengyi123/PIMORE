import Foundation

enum APIEnvironment {
    /// Release builds talk to the live shop. Debug builds on the simulator
    /// prefer a local Harbor server, then fall back to the bundled catalog.
    static var baseURL: URL {
        #if DEBUG && targetEnvironment(simulator)
        return URL(string: "http://127.0.0.1:8787")!
        #else
        return URL(string: "https://linkiip.com")!
        #endif
    }
}

enum HarborAPIError: Error {
    case badURL
    case badStatus
    case badBody
}

struct HarborAPI {
    var session: URLSession = .shared
    var baseURL: URL = APIEnvironment.baseURL

    func home() async throws -> HomeFeed {
        let data = try await get("/api/home")
        if let feed = try? JSONDecoder().decode(HomeFeed.self, from: data), !feed.products.isEmpty {
            return feed
        }
        let products = try decodeProducts(data)
        return HomeFeed(promo: Promo(kicker: "THIS WEEK", title: "Kitchen refresh · up to 30% off", cta: "Shop"), categories: Category.defaults, products: products)
    }

    func products() async throws -> [Product] {
        try decodeProducts(try await get("/api/products"))
    }

    func product(id: String) async throws -> Product {
        let allowed = CharacterSet.urlPathAllowed
        let encoded = id.addingPercentEncoding(withAllowedCharacters: allowed) ?? id
        let data = try await get("/api/products/\(encoded)")
        if let product = try? JSONDecoder().decode(Product.self, from: data) {
            return product
        }
        struct Wrapper: Decodable { var product: Product?; var item: Product? }
        if let wrapper = try? JSONDecoder().decode(Wrapper.self, from: data), let product = wrapper.product ?? wrapper.item {
            return product
        }
        let list = try decodeProducts(data)
        if let match = list.first(where: { $0.id == id }) ?? list.first {
            return match
        }
        throw HarborAPIError.badBody
    }

    func submitSocial(_ profile: SocialProfile) async throws -> SocialAuthResponse {
        struct Body: Encodable {
            var provider: String
            var token: String
            var name: String?
            var email: String?
            var userID: String
        }
        let body = Body(
            provider: profile.provider.rawValue,
            token: profile.token,
            name: profile.name,
            email: profile.email,
            userID: profile.userID
        )
        let data = try await send(path: "/api/auth/social", method: "POST", json: body)
        return try JSONDecoder().decode(SocialAuthResponse.self, from: data)
    }

    private func decodeProducts(_ data: Data) throws -> [Product] {
        if let list = try? JSONDecoder().decode([Product].self, from: data) {
            return list
        }
        let feed = try JSONDecoder().decode(HomeFeed.self, from: data)
        return feed.products
    }

    private func get(_ path: String) async throws -> Data {
        try await send(path: path, method: "GET", json: nil as String?)
    }

    private func send<Body: Encodable>(path: String, method: String, json: Body?) async throws -> Data {
        guard let url = URL(string: baseURL.absoluteString + path) else { throw HarborAPIError.badURL }
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.timeoutInterval = 6
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let json {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try JSONEncoder().encode(json)
        }
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
            throw HarborAPIError.badStatus
        }
        var body = data
        if body.starts(with: [0xEF, 0xBB, 0xBF]) {
            body = Data(body.dropFirst(3))
        }
        guard let first = body.first(where: { !($0 == 32 || $0 == 10 || $0 == 13 || $0 == 9) }),
              first == UInt8(ascii: "{") || first == UInt8(ascii: "[") else {
            throw HarborAPIError.badBody
        }
        return body
    }
}

struct SocialAuthResponse: Decodable {
    var name: String?
    var email: String?

    enum CodingKeys: String, CodingKey { case name, email, user }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        name = try? container.decode(String.self, forKey: .name)
        email = try? container.decode(String.self, forKey: .email)
        if let user = try? container.nestedContainer(keyedBy: CodingKeys.self, forKey: .user) {
            if name == nil { name = try? user.decode(String.self, forKey: .name) }
            if email == nil { email = try? user.decode(String.self, forKey: .email) }
        }
    }
}

enum GeoCountry {
    struct Info {
        var country: String
        var currency: String
    }

    /// Lightweight /api/geo. Language is not consulted.
    static func detectInfo() async -> Info? {
        let base = APIEnvironment.baseURL.absoluteString.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        guard let url = URL(string: base + "/api/geo") else { return nil }
        var request = URLRequest(url: url)
        request.timeoutInterval = 6
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        guard let (data, response) = try? await URLSession.shared.data(for: request),
              let http = response as? HTTPURLResponse,
              (200...299).contains(http.statusCode),
              let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return nil }
        let country = ((obj["country"] as? String) ?? "").uppercased()
        guard country.count == 2 else { return nil }
        var currency = ((obj["currency"] as? String) ?? "").uppercased()
        if currency.count != 3 {
            currency = HarborCurrency.from(countryCode: country).code
        }
        return Info(country: country, currency: currency)
    }

    static func detect() async -> String? {
        await detectInfo()?.country
    }
}


enum HarborMock {
    static func bundled() -> HomeFeed? {
        let url = Bundle.main.url(forResource: "MockCatalog", withExtension: "json")
            ?? Bundle.main.url(forResource: "MockCatalog", withExtension: "json", subdirectory: "Resources")
        guard let url, let data = try? Data(contentsOf: url) else { return nil }
        return try? JSONDecoder().decode(HomeFeed.self, from: data)
    }
}
