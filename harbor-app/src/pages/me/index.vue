<template>
  <view class="page">
    <view class="header">
      <text class="signed">{{ signedLabel }}</text>
      <text class="email">{{ displayEmail }}</text>
      <view class="chips">
        <view class="chip soft">{{ checkInLabel }}</view>
        <view class="chip coral" @click="openCheckIn">{{ acct.checkedToday ? t('me_checked_in') : t('me_claim_today') }}</view>
      </view>
      <view v-if="!acct.signedIn" class="login-row">
        <view class="login-btn" @click="openLogin">{{ t('me_sign_in') }}</view>
      </view>
      <text class="live-note">{{ statusNote }}</text>
    </view>

    <view class="tiles">
      <view v-for="t in tiles" :key="t.t" class="tile" @click="openTile(t)">
        <text class="tone">{{ t.tone }}</text>
        <text class="t">{{ t.t }}</text>
        <text class="d">{{ t.d }}</text>
      </view>
    </view>

    <view class="list">
      <view class="row" @click="openPath('/account/wishlist', 'Wishlist')">
        <view>
          <text class="rt">{{ t('me_wishlist') }}</text>
          <text class="rd">{{ wishLabel }}</text>
        </view>
        <text class="chev">›</text>
      </view>
      <view class="row" @click="openPath('/account/history', 'History')">
        <view>
          <text class="rt">{{ t('me_recently_viewed') }}</text>
          <text class="rd">{{ t('me_browse_history') }}</text>
        </view>
        <text class="chev">›</text>
      </view>
      <view class="row" @click="openPath('/account/addresses', 'Addresses')">
        <view>
          <text class="rt">{{ t('me_addresses') }}</text>
          <text class="rd">{{ t('me_ship_to_book') }}</text>
        </view>
        <text class="chev">›</text>
      </view>
      <view class="row" @click="openPath('/account/payments', 'Payments')">
        <view>
          <text class="rt">{{ t('me_payments') }}</text>
          <text class="rd">{{ t('me_saved_cards') }}</text>
        </view>
        <text class="chev">›</text>
      </view>
      <view class="row" @click="openPath('/rewards', 'Rewards')">
        <view>
          <text class="rt">{{ t('me_rewards') }}</text>
          <text class="rd">{{ t('me_rewards_sub') }}</text>
        </view>
        <text class="chev">›</text>
      </view>
      <view class="row" @click="openPath('/locale', 'Locale')">
        <view>
          <text class="rt">{{ t('me_language') }}</text>
          <text class="rd">{{ t('me_language_sub', { lang: localeNative }) }}</text>
        </view>
        <text class="chev">›</text>
      </view>
      <view class="row" @click="openChat">
        <view>
          <text class="rt">{{ t('me_cs') }}</text>
          <text class="rd">{{ t('me_cs_sub') }}</text>
        </view>
        <text class="chev">›</text>
      </view>
      <view class="row" @click="openPath('/help', 'Help')">
        <view>
          <text class="rt">{{ t('me_help') }}</text>
          <text class="rd">{{ t('me_help_sub') }}</text>
        </view>
        <text class="chev">›</text>
      </view>
      <view class="row" @click="openPath('/compare', 'Compare')">
        <view>
          <text class="rt">{{ t('me_compare') }}</text>
          <text class="rd">{{ t('me_compare_sub') }}</text>
        </view>
        <text class="chev">›</text>
      </view>
    </view>

    <view class="install" @click="openPath('/install', 'Install')">
      <text class="it">{{ t('me_install') }}</text>
      <text class="id">{{ t('me_install_sub') }}</text>
    </view>

    <HbTabBar active="me" />
  </view>
</template>

<script setup lang="ts">
function goLogin() { uni.navigateTo({ url: '/pages/login/index' }) }

import { computed, reactive, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import HbTabBar from '@/components/HbTabBar.vue'
import { accountLinks, fetchAccountSummary, openHarborWeb, type AccountSummary } from '@/api/accountApi'
import { useI18n } from '@/composables/i18n'

const { t, localeNative } = useI18n()
const links = accountLinks()
const loading = ref(false)
const acct = reactive<AccountSummary>({
  ok: false,
  live: false,
  signedIn: false,
  email: '',
  pending: 0,
  paid: 0,
  shipped: 0,
  openOrders: 0,
  couponCount: 0,
  balanceText: '—',
  checkedToday: false,
  wishCount: 0,
  invitePath: '/share',
})

const signedLabel = computed(() => {
  if (!acct.live) return t('me_offline')
  return acct.signedIn ? t('me_signed_in') : t('me_guest')
})

const displayEmail = computed(() => {
  if (acct.signedIn && acct.email) return acct.email
  if (acct.live) return t('me_sync_orders')
  return 'alex@email.com'
})

const checkInLabel = computed(() => {
  if (!acct.live || !acct.signedIn) return t('me_checkin_harbor')
  return acct.checkedToday ? t('me_checked_in') : t('me_claim_today')
})

const statusNote = computed(() => {
  if (loading.value) return t('me_status_refreshing')
  if (!acct.live) return t('me_status_preview')
  if (!acct.signedIn) return t('me_status_guest')
  return t('me_status_live')
})

const wishLabel = computed(() => {
  if (acct.live && acct.signedIn) return t('me_wish_count', { n: acct.wishCount })
  return t('me_wish_saved')
})

const tiles = computed(() => {
  const live = acct.live && acct.signedIn
  return [
    {
      t: t('me_orders'),
      d: t('me_tile_orders_sub'),
      tone: live ? `${acct.openOrders}` : acct.live ? t('me_tile_open_site') : t('common_open_harbor'),
      path: '/account/orders',
    },
    {
      t: t('me_returns') || 'Returns',
      d: t('me_tile_returns_sub') || 'Start a return',
      tone: '',
      path: '/account/returns',
    },
    {
      t: t('me_coupons'),
      d: t('me_tile_coupons_sub'),
      tone: live ? `${acct.couponCount}` : acct.live ? t('me_tile_open_site') : t('common_open_harbor'),
      path: '/account/coupons',
    },
    {
      t: t('me_balance'),
      d: t('me_tile_balance_sub'),
      tone: live ? acct.balanceText : acct.live ? t('me_tile_open_site') : t('common_open_harbor'),
      path: '/account/balance',
    },
    {
      t: t('me_invite'),
      d: t('me_tile_invite_sub'),
      tone: t('me_tile_earn'),
      path: '/share',
    },
  ]
})

async function refresh() {
  loading.value = true
  try {
    const s = await fetchAccountSummary()
    Object.assign(acct, s)
  } finally {
    loading.value = false
  }
}

const nativeMap: Record<string, string> = {
  '/account/orders': '/pages/orders/index',
  '/account/returns': '/pages/return/index',
  '/account/coupons': '/pages/coupons/index',
  '/account/balance': '/pages/balance/index',
  '/account/withdraw': '/pages/withdraw/index',
  '/account/wishlist': '/pages/wishlist/index',
  '/account/history': '/pages/history/index',
  '/account/addresses': '/pages/addresses/index',
  '/account/payments': '/pages/payments/index',
  '/share': '/pages/invite/index',
  '/check-in': '/pages/checkin/index',
  '/install': '/pages/install/index',
  '/rewards': '/pages/rewards/index',
  '/help': '/pages/help/index',
  '/contact': '/pages/contact/index',
  '/chat': '/pages/chat/index',
  '/compare': '/pages/compare/index',
  '/locale': '/pages/locale/index',
  '/lp/ship': '/pages/ship-lp/index',
}

function openPath(path: string, title: string) {
  const native = nativeMap[path]
  if (native) {
    uni.navigateTo({ url: native })
    return
  }
  openHarborWeb(path, title)
}

function openTile(t: { path: string; t: string }) {
  openPath(t.path, t.t)
}

function openLogin() { uni.navigateTo({ url: '/pages/login/index' }) }

function openCheckIn() {
  uni.navigateTo({ url: '/pages/checkin/index' })
}

function openChat() {
  uni.navigateTo({ url: '/pages/chat/index' })
}


onShow(() => {
  refresh()
})
</script>

<style lang="scss" scoped>
@import '@/styles/theme.scss';

.page {
  min-height: 100vh;
  background: $hb-paper;
  padding: 16px;
  padding-top: calc(16px + env(safe-area-inset-top));
  padding-bottom: 100px;
}
.header {
  border-radius: 26px;
  background:
    radial-gradient(circle at 90% 0%, rgba(255, 255, 255, 0.12), transparent 40%),
    linear-gradient(160deg, $hb-deep, $hb-forest);
  color: $hb-white;
  padding: 20px 18px;
  margin-bottom: 16px;
  box-shadow: $hb-shadow-lift;
}
.signed {
  display: block;
  font-size: 11px;
  letter-spacing: 0.8px;
  text-transform: uppercase;
  opacity: 0.7;
  font-weight: 650;
}
.email {
  display: block;
  font-size: 22px;
  font-weight: 720;
  margin-top: 6px;
  letter-spacing: -0.4px;
}
.chips {
  margin-top: 16px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.chip {
  border-radius: $hb-radius-pill;
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 650;
  &.soft {
    background: rgba(255, 255, 255, 0.12);
  }
  &.coral {
    background: $hb-coral;
  }
}
.login-row {
  margin-top: 14px;
}
.login-btn {
  display: inline-flex;
  background: $hb-white;
  color: $hb-forest;
  font-weight: 720;
  font-size: 13px;
  padding: 10px 16px;
  border-radius: 999px;
}
.live-note {
  display: block;
  margin-top: 12px;
  font-size: 11px;
  opacity: 0.7;
}
.tiles {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 14px;
}
.tile {
  border-radius: 20px;
  padding: 16px 14px;
  background: $hb-white;
  box-shadow: $hb-shadow-soft;
}
.tone {
  display: block;
  font-size: 12px;
  color: $hb-forest;
  font-weight: 680;
}
.t {
  display: block;
  font-size: 17px;
  font-weight: 720;
  margin-top: 6px;
  letter-spacing: -0.3px;
}
.d {
  display: block;
  font-size: 12px;
  color: $hb-muted;
  margin-top: 4px;
}
.list {
  background: $hb-white;
  border-radius: 20px;
  overflow: hidden;
  margin-bottom: 12px;
  box-shadow: $hb-shadow-soft;
}
.row {
  padding: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid $hb-line;
  &:last-child {
    border-bottom: none;
  }
}
.rt {
  display: block;
  font-weight: 680;
  font-size: 14px;
  letter-spacing: -0.15px;
}
.rd {
  display: block;
  font-size: 12px;
  color: $hb-muted;
  margin-top: 4px;
}
.chev {
  font-size: 22px;
  color: $hb-muted;
  padding-left: 10px;
  line-height: 1;
}
.install {
  border-radius: 20px;
  background: $hb-soft;
  padding: 16px;
}
.it {
  display: block;
  font-weight: 720;
  font-size: 14px;
  color: $hb-forest;
}
.id {
  display: block;
  font-size: 12px;
  color: $hb-muted;
  margin-top: 4px;
}
.page { background: #F7F4EF; padding-top: env(safe-area-inset-top); }
</style>
