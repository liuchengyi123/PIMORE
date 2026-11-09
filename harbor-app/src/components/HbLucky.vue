<template>
  <view v-if="lucky.pane" class="mask" @click="onMask">
    <view class="sheet" @click.stop>
      <text class="x" @click="closeLucky">×</text>

      <view v-if="lucky.pane === 'wheel'">
        <text class="title">Spin your luck.</text>
        <view class="wheel-wrap">
          <view class="pointer" />
          <view class="wheel" :class="{ go: lucky.spinning }">
            <view class="slice light s0"><text>{{ lucky.percent }}%</text><text>OFF</text></view>
            <view class="slice s1"><text>5%</text><text>OFF</text></view>
            <view class="slice light s2"><text>NO</text><text>PRIZE</text></view>
            <view class="slice s3"><text>5%</text><text>OFF</text></view>
            <view class="slice light s4"><text>NO</text><text>PRIZE</text></view>
            <view class="slice s5"><text>SPIN</text><text>AGAIN</text></view>
          </view>
          <view class="hub" />
        </view>
        <view class="go-btn" :class="{ off: lucky.spinning }" @click="spinLucky">Spin</view>
        <text class="rules">The top slice is the one you get. It starts when you win, and does not combine with other coupons.</text>
      </view>

      <view v-else-if="lucky.pane === 'win'">
        <text class="kicker">You hit the top prize</text>
        <text class="winpct">{{ lucky.percent }}% OFF</text>
        <text class="clock">{{ lucky.clock }}</text>
        <text class="lead">Starts now. Gone in 6 hours. No cap.</text>
        <view class="go-btn" @click="shop">Shop now</view>
      </view>

      <view v-else-if="lucky.pane === 'browse' || lucky.pane === 'pay'">
        <text class="kicker">{{ lucky.pane === 'pay' ? 'Before you leave checkout' : 'Still yours' }}</text>
        <text class="title">{{ lucky.pane === 'pay' ? 'Your ' + lucky.percent + '% off is still on this order.' : 'Order today. These are still ' + lucky.percent + '% off.' }}</text>
        <text class="clock">{{ lucky.clock }}</text>
        <view v-for="(item, i) in lucky.goods" :key="i" class="good">
          <image v-if="item.image" class="pic" :src="item.image" mode="aspectFill" />
          <view v-else class="pic" />
          <view class="meta">
            <text class="name">{{ item.name }}</text>
            <text class="prices"><text class="was">${{ item.from.toFixed(2) }}</text> ${{ item.now.toFixed(2) }}</text>
          </view>
        </view>
        <view class="go-btn" @click="lucky.pane === 'pay' ? closeLucky() : shop()">
          {{ lucky.pane === 'pay' ? 'Stay and pay' : 'Keep the discount' }}
        </view>
      </view>

      <view v-else-if="lucky.pane === 'placed'">
        <text class="kicker">Order placed</text>
        <text class="title">Your order is in.</text>
        <text class="lead">One more draw. Smash an egg. This one is the free-order coupon.</text>
        <view class="go-btn" @click="openEggs">Smash the eggs</view>
      </view>

      <view v-else-if="lucky.pane === 'eggs'">
        <text class="kicker">Free-order coupon</text>
        <text class="title">Pick an egg</text>
        <view class="eggs">
          <view
            v-for="(label, i) in lucky.eggs"
            :key="i"
            class="egg"
            :class="{ win: label === 'Free order', miss: lucky.eggDone && label !== 'Free order' }"
            @click="smashEgg(i)"
          >{{ label }}</view>
        </view>
        <text v-if="lucky.prize" class="prize">{{ lucky.prize }}</text>
        <text class="rules">One coupon per customer, always on your latest paid order. Five later paid orders in the window, from you or a friend, bring the merchandise total back as Harbor credit.</text>
      </view>

      <view v-else-if="lucky.pane === 'status' && lucky.free">
        <text class="kicker">Free-order coupon</text>
        <text class="title">{{ lucky.free.stamps }} of {{ lucky.free.needed }}</text>
        <text class="lead">Order #{{ lucky.free.order_id }} · ${{ (lucky.free.amount_cents / 100).toFixed(2) }} back as credit · {{ lucky.free.status }}</text>
        <text class="rules">A newer order of yours moves this coupon onto that order. It never opens a second one.</text>
      </view>
    </view>
  </view>
  <view v-else-if="chip" class="chip" @click="openLuckyChip">{{ chip }}</view>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import {
  lucky,
  refreshLucky,
  startLuckyClock,
  stopLuckyClock,
  closeLucky,
  spinLucky,
  openEggs,
  smashEgg,
  openLuckyChip,
  chipText,
  showChip,
} from '@/composables/lucky'

const chip = computed(() => (showChip() ? chipText() : ''))

function shop() {
  closeLucky()
  uni.reLaunch({ url: '/pages/home/index' })
}

function onMask() {
  closeLucky()
}

onMounted(() => {
  startLuckyClock()
  refreshLucky()
})

onUnmounted(() => {
  stopLuckyClock()
})
</script>

<style lang="scss" scoped>
.mask {
  position: fixed;
  left: 0;
  right: 0;
  top: 0;
  bottom: 0;
  z-index: 80;
  background: rgba(18, 32, 48, 0.46);
  display: flex;
  align-items: center;
  justify-content: center;
}
.sheet {
  width: calc(100% - 28px);
  max-width: 400px;
  max-height: 88vh;
  overflow: auto;
  background: #fbf8f2;
  color: #16325c;
  border-radius: 28px;
  padding: 28px 20px calc(18px + env(safe-area-inset-bottom));
  text-align: center;
  position: relative;
}
.x {
  position: absolute;
  right: 18px;
  margin-top: -6px;
  width: 36px;
  height: 36px;
  border-radius: 18px;
  background: #f7f4ef;
  text-align: center;
  line-height: 36px;
  font-size: 22px;
}
.kicker {
  display: block;
  color: #16325c;
  font-size: 22px;
  font-weight: 560;
  line-height: 1.2;
}
.title, .kicker, .winpct, .go-btn, .prize {
  font-family: Georgia, "Times New Roman", serif;
}
.title {
  display: block;
  margin: 0 28px 8px;
  font-size: 32px;
  font-weight: 560;
  line-height: 1.12;
  color: #16325c;
}
.winpct {
  display: block;
  margin: 0 0 10px;
  font-size: 40px;
  font-weight: 640;
  line-height: 1;
  color: #16325c;
}
.lead, .rules {
  display: block;
  color: #5c6570;
  font-size: 14px;
  line-height: 1.45;
  margin-bottom: 12px;
}
.rules { font-size: 12px; }
.clock {
  display: inline-flex;
  align-self: center;
  color: #16325c;
  font-size: 18px;
  font-weight: 700;
  margin: 0 auto 12px;
  padding: 8px 16px;
  border-radius: 999px;
  border: 1px solid #e6dfd4;
  background: #fff;
}
.go-btn {
  height: 52px;
  border-radius: 999px;
  background: #16325c;
  color: #fff;
  font-size: 20px;
  font-weight: 560;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 8px 0 12px;
}
.go-btn.off { opacity: 0.6; }
.wheel-wrap {
  width: 268px;
  height: 268px;
  margin: 14px auto 16px;
  position: relative;
}
.pointer {
  position: absolute;
  top: -2px;
  left: 50%;
  width: 22px;
  height: 16px;
  margin-left: -11px;
  background: #e0b44a;
  clip-path: polygon(50% 100%, 0 0, 100% 0);
  z-index: 4;
}
.hub {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 34px;
  height: 34px;
  margin: -17px 0 0 -17px;
  border-radius: 17px;
  background: #e2b34c;
  z-index: 3;
}
.wheel {
  width: 268px;
  height: 268px;
  border-radius: 134px;
  background: conic-gradient(from -30deg, #1b3f6b 0 60deg, #f7f3ea 60deg 120deg, #1b3f6b 120deg 180deg, #f7f3ea 180deg 240deg, #1b3f6b 240deg 300deg, #f7f3ea 300deg 360deg);
  box-shadow: 0 0 0 7px #e6c36a, 0 0 0 10px #c4963a;
  position: relative;
}
.wheel.go { animation: spin 4s cubic-bezier(0.15, 0.7, 0.1, 1) forwards; }
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(1800deg); }
}
.slice {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 58px;
  margin-left: -29px;
  margin-top: -16px;
  text-align: center;
  font-size: 12px;
  font-weight: 800;
  line-height: 1.05;
  color: #1b3f6b;
}
.slice text { display: block; }
.slice.light { color: #fff; }
.s0 { transform: translateY(-78px); }
.s1 { transform: rotate(60deg) translateY(-78px) rotate(-60deg); }
.s2 { transform: rotate(120deg) translateY(-78px) rotate(-120deg); }
.s3 { transform: rotate(180deg) translateY(-78px) rotate(-180deg); }
.s4 { transform: rotate(240deg) translateY(-78px) rotate(-240deg); }
.s5 { transform: rotate(300deg) translateY(-78px) rotate(-300deg); }
.good { display: flex; gap: 10px; align-items: center; margin-bottom: 10px; }
.pic { width: 64px; height: 64px; border-radius: 12px; background: #f7f4ef; }
.meta { flex: 1; }
.name { display: block; font-size: 14px; font-weight: 700; }
.prices { display: block; margin-top: 4px; color: #b45309; font-weight: 800; }
.was { color: #5c6570; font-weight: 500; text-decoration: line-through; margin-right: 6px; }
.eggs { display: flex; gap: 10px; margin: 12px 0; }
.egg {
  flex: 1;
  height: 118px;
  border-radius: 60px 60px 50px 50px;
  background: #f4efe6;
  color: transparent;
  font-weight: 800;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 8px;
}
.egg.win, .egg.miss { color: #1b3f6b; }
.egg.win { background: #e2b34c; }
.prize { display: block; color: #b45309; font-size: 20px; font-weight: 800; margin-bottom: 8px; }
.chip {
  position: fixed;
  right: 16px;
  bottom: calc(96px + env(safe-area-inset-bottom));
  z-index: 70;
  background: #0f2744;
  color: #fff;
  font-weight: 700;
  font-size: 13px;
  padding: 10px 14px;
  border-radius: 999px;
}
</style>
