import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'root', component: () => import('@/views/HomeView.vue') },
    { path: '/home', name: 'home', component: () => import('@/views/HomeView.vue') },
    { path: '/browse', name: 'browse', component: () => import('@/views/BrowseView.vue') },
    { path: '/search', name: 'search', component: () => import('@/views/SearchView.vue') },
    { path: '/sale', name: 'sale', component: () => import('@/views/SaleView.vue') },
    { path: '/new', name: 'new', component: () => import('@/views/NewView.vue') },
    { path: '/compare', name: 'compare', component: () => import('@/views/CompareView.vue') },
    { path: '/ship-lp', name: 'ship-lp', component: () => import('@/views/ShipLpView.vue') },
    { path: '/help', name: 'help', component: () => import('@/views/HelpView.vue') },
    { path: '/contact', name: 'contact', component: () => import('@/views/ContactView.vue') },
    { path: '/policy', name: 'policy', component: () => import('@/views/PolicyView.vue') },
    { path: '/pdp', name: 'pdp', component: () => import('@/views/PdpView.vue') },
    { path: '/product/:sku', name: 'product', component: () => import('@/views/PdpView.vue') },
    { path: '/cart', name: 'cart', component: () => import('@/views/CartView.vue') },
    { path: '/checkout', name: 'checkout', component: () => import('@/views/CheckoutView.vue') },
    { path: '/order-success', name: 'order-success', component: () => import('@/views/OrderSuccessView.vue') },
    { path: '/orders', name: 'orders', component: () => import('@/views/OrdersView.vue') },
    { path: '/orders/:id', name: 'order-detail', component: () => import('@/views/OrderDetailView.vue') },
    { path: '/invoice', name: 'invoice', component: () => import('@/views/InvoiceView.vue') },
    { path: '/me', name: 'me', component: () => import('@/views/MeView.vue') },
    { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue') },
    { path: '/register', name: 'register', component: () => import('@/views/RegisterView.vue') },
    { path: '/addresses', name: 'addresses', component: () => import('@/views/AddressesView.vue') },
    { path: '/payments', name: 'payments', component: () => import('@/views/PaymentsView.vue') },
    { path: '/wishlist', name: 'wishlist', component: () => import('@/views/WishlistView.vue') },
    { path: '/history', name: 'history', component: () => import('@/views/HistoryView.vue') },
    { path: '/checkin', name: 'checkin', component: () => import('@/views/CheckinView.vue') },
    { path: '/coupons', name: 'coupons', component: () => import('@/views/CouponsView.vue') },
    { path: '/balance', name: 'balance', component: () => import('@/views/BalanceView.vue') },
    { path: '/withdraw', name: 'withdraw', component: () => import('@/views/WithdrawView.vue') },
    { path: '/invite', name: 'invite', component: () => import('@/views/InviteView.vue') },
    { path: '/referral', name: 'referral', component: () => import('@/views/ReferralView.vue') },
    { path: '/rewards', name: 'rewards', component: () => import('@/views/RewardsView.vue') },
    { path: '/locale', name: 'locale', component: () => import('@/views/LocaleView.vue') },
    { path: '/install', name: 'install', component: () => import('@/views/InstallView.vue') },
    { path: '/chat', name: 'chat', component: () => import('@/views/ChatView.vue') },
  ],
  scrollBehavior() {
    return { top: 0 }
  },
})

export default router
