/** Official Figma frame exports (file eptrtDM0XUICi87bqapjQb).
 *  These artboards are flattened renders — the PNG is the 1:1 visual.
 *  Hits are transparent controls in design-pixel space (768×1792).
 */

export interface FrameHit {
  x: number
  y: number
  w: number
  h: number
  label: string
  to?: string
  action?: 'back' | 'place-order' | 'add-cart'
}

export interface FrameSpec {
  id: string
  title: string
  /** Tab set drawn on this artboard. */
  tabs?: 'h4' | 'b4' | 'c5' | 'p5'
  back?: boolean
  hits?: FrameHit[]
}

const H4: FrameHit[] = [
  { x: 0, y: 1648, w: 192, h: 144, label: 'Home', to: '/home' },
  { x: 192, y: 1648, w: 192, h: 144, label: 'Browse', to: '/categories' },
  { x: 384, y: 1648, w: 192, h: 144, label: 'Cart', to: '/cart' },
  { x: 576, y: 1648, w: 192, h: 144, label: 'Me', to: '/me' },
]

const B4: FrameHit[] = [
  { x: 0, y: 1648, w: 192, h: 144, label: 'Home', to: '/home' },
  { x: 192, y: 1648, w: 192, h: 144, label: 'Browse', to: '/browse' },
  { x: 384, y: 1648, w: 192, h: 144, label: 'Wishlist', to: '/wishlist' },
  { x: 576, y: 1648, w: 192, h: 144, label: 'Profile', to: '/me' },
]

const C5: FrameHit[] = [
  { x: 0, y: 1648, w: 154, h: 144, label: 'Home', to: '/home' },
  { x: 154, y: 1648, w: 154, h: 144, label: 'Search', to: '/search' },
  { x: 308, y: 1648, w: 154, h: 144, label: 'Cart', to: '/cart' },
  { x: 462, y: 1648, w: 154, h: 144, label: 'Wishlist', to: '/wishlist' },
  { x: 616, y: 1648, w: 152, h: 144, label: 'Account', to: '/me' },
]

const P5: FrameHit[] = [
  { x: 0, y: 1648, w: 154, h: 144, label: 'Home', to: '/featured' },
  { x: 154, y: 1648, w: 154, h: 144, label: 'Browse', to: '/categories' },
  { x: 308, y: 1648, w: 154, h: 144, label: 'Cart', to: '/cart' },
  { x: 462, y: 1648, w: 154, h: 144, label: 'Rewards', to: '/rewards' },
  { x: 616, y: 1648, w: 152, h: 144, label: 'Me', to: '/me' },
]

const BACK: FrameHit = { x: 8, y: 48, w: 72, h: 72, label: 'Back', action: 'back' }

function spec(id: string, title: string, extra?: Partial<FrameSpec>): FrameSpec {
  const tabs = extra?.tabs
  const tabHits = tabs === 'h4' ? H4 : tabs === 'b4' ? B4 : tabs === 'c5' ? C5 : tabs === 'p5' ? P5 : []
  const backHits = extra?.back ? [BACK] : []
  return {
    id,
    title,
    tabs,
    back: extra?.back,
    hits: [...backHits, ...(extra?.hits || []), ...tabHits],
  }
}

export const FRAMES: Record<string, FrameSpec> = {
  '1-5': spec('1-5', 'Home', {
    tabs: 'h4',
    hits: [
      { x: 24, y: 118, w: 720, h: 64, label: 'Search', to: '/search' },
      { x: 560, y: 56, w: 180, h: 56, label: 'Locale', to: '/locale' },
      { x: 28, y: 420, w: 200, h: 64, label: 'Shop Sale', to: '/sale' },
      { x: 24, y: 540, w: 170, h: 130, label: 'Kitchen', to: '/category?id=kitchen' },
      { x: 206, y: 540, w: 170, h: 130, label: 'Storage', to: '/category?id=storage' },
      { x: 388, y: 540, w: 170, h: 130, label: 'Cleaning', to: '/category?id=cleaning' },
      { x: 570, y: 540, w: 170, h: 130, label: 'Textile', to: '/category?id=textile' },
      { x: 560, y: 680, w: 180, h: 48, label: 'Flash', to: '/flash' },
      { x: 24, y: 740, w: 720, h: 220, label: 'Flash deals', to: '/flash' },
      { x: 580, y: 980, w: 160, h: 40, label: 'See all new', to: '/new' },
      { x: 24, y: 1030, w: 720, h: 280, label: 'New arrivals', to: '/new' },
      { x: 24, y: 1360, w: 720, h: 260, label: 'Just for you', to: '/pdp' },
    ],
  }),
  '1-2': spec('1-2', 'Browse', {
    tabs: 'b4',
    hits: [
      { x: 620, y: 56, w: 64, h: 56, label: 'Search', to: '/search' },
      { x: 690, y: 56, w: 64, h: 56, label: 'Cart', to: '/cart' },
      { x: 24, y: 130, w: 720, h: 56, label: 'Search field', to: '/search' },
      { x: 24, y: 400, w: 350, h: 420, label: 'Product', to: '/pdp' },
      { x: 394, y: 400, w: 350, h: 420, label: 'Product', to: '/pdp' },
    ],
  }),
  '1-4': spec('1-4', 'PDP', {
    back: true,
    hits: [
      { x: 24, y: 1636, w: 360, h: 88, label: 'Add to cart', action: 'add-cart' },
      { x: 390, y: 1636, w: 354, h: 88, label: 'Buy now', to: '/checkout' },
      { x: 640, y: 56, w: 56, h: 56, label: 'Wishlist', to: '/wishlist' },
      { x: 700, y: 56, w: 52, h: 56, label: 'Share', to: '/compare' },
    ],
  }),
  '1-3': spec('1-3', 'PDP SKU Sheet', {
    back: true,
    hits: [
      { x: 40, y: 1500, w: 688, h: 80, label: 'Confirm add to cart', action: 'add-cart' },
      { x: 680, y: 860, w: 64, h: 64, label: 'Close', to: '/pdp' },
    ],
  }),
  '1-7': spec('1-7', 'Cart', {
    tabs: 'c5',
    hits: [
      { x: 24, y: 1500, w: 720, h: 120, label: 'Checkout', to: '/checkout' },
      { x: 520, y: 64, w: 220, h: 48, label: 'Saved for later', to: '/wishlist' },
    ],
  }),
  '1-6': spec('1-6', 'Checkout', {
    back: true,
    hits: [
      { x: 36, y: 1596, w: 696, h: 84, label: 'Place order', action: 'place-order' },
      { x: 560, y: 250, w: 160, h: 40, label: 'Edit address', to: '/addresses' },
      { x: 36, y: 900, w: 520, h: 64, label: 'Coupon', to: '/coupons' },
    ],
  }),
  '1-12': spec('1-12', 'Categories', {
    tabs: 'h4',
    hits: [
      { x: 680, y: 56, w: 64, h: 56, label: 'Search', to: '/search' },
      { x: 200, y: 160, w: 260, h: 280, label: 'Cookware', to: '/category?id=kitchen' },
      { x: 480, y: 160, w: 260, h: 280, label: 'Utensils', to: '/category?id=kitchen' },
      { x: 200, y: 460, w: 260, h: 280, label: 'Food storage', to: '/category?id=storage' },
      { x: 480, y: 460, w: 260, h: 280, label: 'Drinkware', to: '/category?id=kitchen' },
    ],
  }),
  '1-13': spec('1-13', 'Category PLP', {
    tabs: 'h4',
    back: true,
    hits: [
      { x: 24, y: 200, w: 350, h: 420, label: 'Product', to: '/pdp' },
      { x: 390, y: 200, w: 350, h: 420, label: 'Product', to: '/pdp' },
      { x: 640, y: 56, w: 56, h: 56, label: 'Filter', to: '/search' },
      { x: 700, y: 56, w: 52, h: 56, label: 'Sort', to: '/search' },
    ],
  }),
  '1-14': spec('1-14', 'Search', {
    tabs: 'h4',
    hits: [
      { x: 24, y: 150, w: 600, h: 64, label: 'Search field', to: '/search' },
      { x: 630, y: 150, w: 120, h: 64, label: 'Cancel', to: '/home' },
      { x: 24, y: 900, w: 350, h: 280, label: 'Suggested', to: '/pdp' },
      { x: 390, y: 900, w: 350, h: 280, label: 'Suggested', to: '/pdp' },
    ],
  }),
  '1-15': spec('1-15', 'Sale', {
    tabs: 'h4',
    hits: [
      { x: 620, y: 56, w: 64, h: 56, label: 'Search', to: '/search' },
      { x: 690, y: 56, w: 64, h: 56, label: 'Cart', to: '/cart' },
      { x: 24, y: 560, w: 350, h: 420, label: 'Deal', to: '/pdp' },
      { x: 390, y: 560, w: 350, h: 420, label: 'Deal', to: '/pdp' },
      { x: 400, y: 480, w: 340, h: 56, label: 'Coupons', to: '/coupons' },
    ],
  }),
  '1-16': spec('1-16', 'Flash', {
    tabs: 'h4',
    hits: [
      { x: 24, y: 280, w: 350, h: 520, label: 'Grab', action: 'add-cart' },
      { x: 394, y: 280, w: 350, h: 520, label: 'Grab', action: 'add-cart' },
    ],
  }),
  '1-17': spec('1-17', 'New', {
    tabs: 'h4',
    hits: [
      { x: 560, y: 56, w: 180, h: 56, label: 'Filter', to: '/search' },
      { x: 24, y: 280, w: 350, h: 360, label: 'New product', to: '/pdp' },
      { x: 394, y: 280, w: 350, h: 360, label: 'New product', to: '/pdp' },
    ],
  }),
  '1-19': spec('1-19', 'Ship Flash LP', {
    tabs: 'h4',
    hits: [
      { x: 620, y: 56, w: 64, h: 56, label: 'Search', to: '/search' },
      { x: 690, y: 56, w: 64, h: 56, label: 'Cart', to: '/cart' },
      { x: 40, y: 1480, w: 688, h: 72, label: 'Enter flash ship', to: '/flash' },
    ],
  }),
  '1-20': spec('1-20', 'Compare', {
    tabs: 'h4',
    back: true,
    hits: [
      { x: 24, y: 360, w: 230, h: 80, label: 'Add to cart', action: 'add-cart' },
      { x: 268, y: 360, w: 230, h: 80, label: 'Add to cart', action: 'add-cart' },
      { x: 512, y: 360, w: 230, h: 80, label: 'Add to cart', action: 'add-cart' },
    ],
  }),
  '1-21': spec('1-21', 'Peek Quick View', {
    hits: [
      { x: 0, y: 0, w: 768, h: 520, label: 'Close peek', to: '/browse' },
      { x: 36, y: 1480, w: 400, h: 80, label: 'Add to cart', action: 'add-cart' },
      { x: 450, y: 1480, w: 280, h: 80, label: 'View details', to: '/pdp' },
    ],
  }),
  '1-22': spec('1-22', 'Cart Gap Picks', {
    hits: [
      { x: 680, y: 820, w: 64, h: 64, label: 'Close', to: '/cart' },
      { x: 40, y: 1560, w: 688, h: 72, label: 'Add selected', action: 'add-cart' },
    ],
  }),
  '1-23': spec('1-23', 'Cart Bundle', {
    hits: [
      { x: 680, y: 820, w: 64, h: 64, label: 'Close', to: '/cart' },
      { x: 40, y: 1560, w: 688, h: 72, label: 'Apply bundle', to: '/checkout' },
    ],
  }),
  '1-24': spec('1-24', 'Payment Status', {
    back: true,
    hits: [
      { x: 48, y: 1180, w: 672, h: 80, label: 'Refresh status', to: '/payment-status' },
      { x: 48, y: 1280, w: 672, h: 80, label: 'Contact support', to: '/chat' },
    ],
  }),
  '1-25': spec('1-25', 'Order Success', {
    hits: [
      { x: 48, y: 1280, w: 672, h: 80, label: 'Track order', to: '/orders' },
      { x: 48, y: 1380, w: 672, h: 80, label: 'Continue shopping', to: '/home' },
    ],
  }),
  '1-26': spec('1-26', 'Orders', {
    tabs: 'h4',
    hits: [
      { x: 620, y: 56, w: 64, h: 56, label: 'Search', to: '/search' },
      { x: 690, y: 56, w: 64, h: 56, label: 'Cart', to: '/cart' },
      { x: 24, y: 280, w: 720, h: 280, label: 'Order', to: '/orders/H0527843' },
      { x: 24, y: 580, w: 720, h: 280, label: 'Order', to: '/orders/H0526712' },
    ],
  }),
  '1-27': spec('1-27', 'Order Detail', {
    back: true,
    hits: [
      { x: 48, y: 1500, w: 672, h: 72, label: 'Track', to: '/orders' },
      { x: 48, y: 1588, w: 320, h: 64, label: 'Invoice', to: '/invoice' },
      { x: 400, y: 1588, w: 320, h: 64, label: 'Return', to: '/return' },
    ],
  }),
  '1-28': spec('1-28', 'Invoice', { back: true }),
  '1-29': spec('1-29', 'Return Request', {
    back: true,
    hits: [{ x: 40, y: 1500, w: 688, h: 80, label: 'Submit return', to: '/orders' }],
  }),
  '1-30': spec('1-30', 'Login', {
    hits: [
      { x: 48, y: 1220, w: 240, h: 48, label: 'Forgot password', to: '/reset' },
      { x: 480, y: 1220, w: 240, h: 48, label: 'Register', to: '/register' },
      { x: 48, y: 1364, w: 672, h: 84, label: 'Google', to: '/login' },
      { x: 48, y: 1460, w: 672, h: 84, label: 'Apple', to: '/login' },
    ],
  }),
  '1-56': spec('1-56', 'Buyer Chat', {
    back: true,
    hits: [{ x: 24, y: 80, w: 200, h: 48, label: 'Orders', to: '/orders' }],
  }),
  '1-57': spec('1-57', 'Lucky Wheel', {
    hits: [
      { x: 640, y: 280, w: 80, h: 80, label: 'Close', to: '/home' },
      { x: 250, y: 1100, w: 268, h: 80, label: 'Spin', to: '/rewards' },
    ],
  }),
  '1-59': spec('1-59', 'Newcomer Hold', {
    hits: [
      { x: 640, y: 420, w: 80, h: 80, label: 'Close', to: '/home' },
      { x: 80, y: 1200, w: 608, h: 80, label: 'Shop now', to: '/sale' },
    ],
  }),
  '1-58': spec('1-58', 'Offline', {
    hits: [{ x: 80, y: 1100, w: 608, h: 80, label: 'Retry', to: '/home' }],
  }),
  '1-60': spec('1-60', '404', {
    hits: [{ x: 80, y: 1100, w: 608, h: 80, label: 'Back home', to: '/home' }],
  }),
  '1-61': spec('1-61', 'WebView Pay Bridge', {
    hits: [
      { x: 48, y: 1400, w: 320, h: 72, label: 'Return', to: '/checkout' },
      { x: 400, y: 1400, w: 320, h: 72, label: 'Done', to: '/order-success' },
    ],
  }),
  '3-4': spec('3-4', 'App Tab Bar', {
    tabs: 'p5',
    hits: [
      { x: 620, y: 56, w: 64, h: 56, label: 'Search', to: '/search' },
      { x: 690, y: 56, w: 64, h: 56, label: 'Alerts', to: '/orders' },
      { x: 48, y: 360, w: 200, h: 56, label: 'Shop now', to: '/sale' },
      { x: 24, y: 900, w: 350, h: 420, label: 'Product', to: '/pdp' },
      { x: 394, y: 900, w: 350, h: 420, label: 'Product', to: '/pdp' },
    ],
  }),
  '3-35': spec('3-35', '买家客服', {
    back: true,
    hits: [{ x: 24, y: 1560, w: 560, h: 72, label: 'Send', to: '/chat-zh' }],
  }),
  // Account growth — filled as assets land
  '1-31': spec('1-31', 'Register', {
    hits: [
      { x: 80, y: 1280, w: 280, h: 48, label: 'Terms', to: '/policy/terms' },
      { x: 80, y: 1320, w: 220, h: 40, label: 'Privacy', to: '/policy/privacy' },
      { x: 250, y: 1540, w: 260, h: 56, label: 'Log in', to: '/login' },
    ],
  }),
  '1-32': spec('1-32', 'Reset Password', { back: true }),
  '1-33': spec('1-33', 'Set Password', { back: true }),
  '1-34': spec('1-34', 'Auth Modal', {
    hits: [{ x: 0, y: 0, w: 768, h: 500, label: 'Close', to: '/home' }],
  }),
  '1-36': spec('1-36', 'Account Orders', { back: true, tabs: 'h4' }),
  '1-38': spec('1-38', 'Coupons', { back: true, tabs: 'h4' }),
  '1-39': spec('1-39', 'Withdraw', { back: true }),
  '1-40': spec('1-40', 'Balance', { back: true, tabs: 'h4' }),
  '1-41': spec('1-41', 'Wishlist', { back: true, tabs: 'h4' }),
  '1-42': spec('1-42', 'History', { back: true, tabs: 'h4' }),
  '1-43': spec('1-43', 'Addresses', { back: true, tabs: 'h4' }),
  '1-44': spec('1-44', 'Payments', { back: true, tabs: 'h4' }),
  '1-45': spec('1-45', 'Rewards', { back: true, tabs: 'h4' }),
  '1-46': spec('1-46', 'Invite', { back: true, tabs: 'h4' }),
  '1-47': spec('1-47', 'Referral', { back: true }),
  '1-48': spec('1-48', 'Install', { back: true }),
  '1-49': spec('1-49', 'Check-in', { back: true, tabs: 'h4' }),
  '1-50': spec('1-50', 'Help', { back: true, tabs: 'h4' }),
  '1-51': spec('1-51', 'Contact', { back: true }),
  '1-52': spec('1-52', 'Policy Shipping', { back: true }),
  '1-53': spec('1-53', 'Policy Privacy', { back: true }),
  '1-54': spec('1-54', 'Policy Terms', { back: true }),
  '1-55': spec('1-55', 'Locale', { back: true, tabs: 'h4' }),
  '1-35': spec('1-35', 'Me', {
    tabs: 'h4',
    hits: [
      { x: 24, y: 280, w: 720, h: 160, label: 'Your orders', to: '/orders' },
      { x: 24, y: 460, w: 180, h: 120, label: 'Unpaid', to: '/orders' },
      { x: 204, y: 460, w: 180, h: 120, label: 'Shipping', to: '/orders' },
      { x: 384, y: 460, w: 180, h: 120, label: 'Completed', to: '/orders' },
      { x: 564, y: 460, w: 180, h: 120, label: 'Returns', to: '/return' },
      { x: 24, y: 620, w: 720, h: 88, label: 'Orders', to: '/orders' },
      { x: 24, y: 708, w: 720, h: 88, label: 'Coupons', to: '/coupons' },
      { x: 24, y: 796, w: 720, h: 88, label: 'Balance', to: '/balance' },
      { x: 24, y: 884, w: 720, h: 88, label: 'Wishlist', to: '/wishlist' },
      { x: 24, y: 972, w: 720, h: 88, label: 'Addresses', to: '/addresses' },
      { x: 24, y: 1060, w: 720, h: 88, label: 'Payments', to: '/payments' },
      { x: 24, y: 1148, w: 720, h: 88, label: 'Rewards', to: '/rewards' },
      { x: 24, y: 1236, w: 720, h: 88, label: 'Invite', to: '/invite' },
      { x: 24, y: 1324, w: 720, h: 88, label: 'Help', to: '/help' },
      { x: 24, y: 1412, w: 720, h: 88, label: 'Settings', to: '/locale' },
    ],
  }),
}

export const ROUTE_FRAME: Record<string, string> = {
  root: '1-5',
  home: '1-5',
  browse: '1-2',
  pdp: '1-4',
  product: '1-4',
  cart: '1-7',
  checkout: '1-6',
  categories: '1-12',
  category: '1-13',
  search: '1-14',
  sale: '1-15',
  flash: '1-16',
  new: '1-17',
  'ship-lp': '1-19',
  compare: '1-20',
  peek: '1-21',
  'cart-gap': '1-22',
  'cart-bundle': '1-23',
  'payment-status': '1-24',
  'order-success': '1-25',
  orders: '1-26',
  'order-detail': '1-27',
  invoice: '1-28',
  return: '1-29',
  login: '1-30',
  chat: '1-56',
  lucky: '1-57',
  hold: '1-59',
  offline: '1-58',
  notfound: '1-60',
  'pay-bridge': '1-61',
  featured: '3-4',
  'chat-zh': '3-35',
  me: '1-35',
  register: '1-31',
  reset: '1-32',
  'set-password': '1-33',
  'auth-modal': '1-34',
  'account-orders': '1-36',
  coupons: '1-38',
  withdraw: '1-39',
  balance: '1-40',
  wishlist: '1-41',
  history: '1-42',
  addresses: '1-43',
  payments: '1-44',
  rewards: '1-45',
  invite: '1-46',
  referral: '1-47',
  install: '1-48',
  checkin: '1-49',
  help: '1-50',
  contact: '1-51',
  'policy-shipping': '1-52',
  'policy-privacy': '1-53',
  'policy-terms': '1-54',
  policy: '1-52',
  locale: '1-55',
}
