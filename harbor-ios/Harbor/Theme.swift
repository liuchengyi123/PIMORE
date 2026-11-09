import SwiftUI

enum HarborColor {
    static let navy = Color(red: 15 / 255, green: 39 / 255, blue: 68 / 255)
    static let teal = Color(red: 14 / 255, green: 116 / 255, blue: 144 / 255)
    static let amber = Color(red: 180 / 255, green: 83 / 255, blue: 9 / 255)
    static let sand = Color(red: 247 / 255, green: 244 / 255, blue: 239 / 255)
    static let muted = Color(red: 92 / 255, green: 101 / 255, blue: 112 / 255)
    static let inactive = Color(red: 154 / 255, green: 163 / 255, blue: 173 / 255)
    static let line = Color(red: 232 / 255, green: 228 / 255, blue: 220 / 255)
    static let iconBg = Color(red: 238 / 255, green: 241 / 255, blue: 244 / 255)
    static let danger = Color(red: 220 / 255, green: 38 / 255, blue: 38 / 255)
    static let promoKicker = Color(red: 165 / 255, green: 243 / 255, blue: 252 / 255)
    static let trackedBg = Color(red: 220 / 255, green: 245 / 255, blue: 226 / 255)
    static let trackedText = Color(red: 22 / 255, green: 120 / 255, blue: 62 / 255)
    static let shipBg = Color(red: 224 / 255, green: 242 / 255, blue: 250 / 255)
    static let reviewBg = Color(red: 243 / 255, green: 240 / 255, blue: 234 / 255)
    static let shadow = Color(red: 15 / 255, green: 26 / 255, blue: 41 / 255).opacity(0.12)

    static func pastel(for id: String) -> Color {
        let palette: [Color] = [
            Color(red: 214 / 255, green: 222 / 255, blue: 232 / 255),
            Color(red: 200 / 255, green: 230 / 255, blue: 216 / 255),
            Color(red: 197 / 255, green: 220 / 255, blue: 240 / 255),
            Color(red: 232 / 255, green: 217 / 255, blue: 184 / 255),
            Color(red: 229 / 255, green: 207 / 255, blue: 216 / 255),
            Color(red: 213 / 255, green: 207 / 255, blue: 232 / 255)
        ]
        let index = abs(id.unicodeScalars.reduce(0) { $0 + Int($1.value) }) % palette.count
        return palette[index]
    }
}

enum HarborFont {
    static func brand() -> Font { .system(size: 20, weight: .bold) }
    static func title() -> Font { .system(size: 20, weight: .bold) }
    static func price(_ size: CGFloat = 15) -> Font { .system(size: size, weight: .bold) }
}

extension View {
    func harborScreen() -> some View {
        background(HarborColor.sand.ignoresSafeArea())
            .toolbar(.hidden, for: .navigationBar)
            .toolbar(.hidden, for: .tabBar)
    }

    func harborRoot() -> some View {
        harborScreen()
            .safeAreaInset(edge: .bottom, spacing: 0) {
                HarborTabBar()
            }
    }
}
