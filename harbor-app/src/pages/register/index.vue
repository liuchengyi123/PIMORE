<template>
  <view class="page" data-figma="A12">
    <view class="status">
      <text class="t">9:41</text>
      <text class="t">●●● 5G</text>
    </view>
    <view class="body">
      <text class="brand">HARBOR APP</text>
      <text class="title">Create account</text>
      <view class="field">
        <text class="lab">Email</text>
        <input class="inp" v-model="email" type="text" placeholder="you@email.com" />
      </view>
      <view class="field">
        <text class="lab">Password</text>
        <input class="inp" v-model="password" password placeholder="••••••••" />
      </view>
      <view class="field">
        <text class="lab">Confirm</text>
        <input class="inp" v-model="confirm" password placeholder="••••••••" />
      </view>
      <view class="btn" @click="submit">Register</view>
      <view class="alt" @click="goLogin">Already have an account · Sign in</view>
    </view>
  </view>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { openHarborWeb, accountLinks } from '@/api/accountApi'
const email = ref('')
const password = ref('')
const confirm = ref('')
function submit() {
  openHarborWeb(accountLinks().register || accountLinks().login, 'Register')
}
function goLogin() { uni.navigateTo({ url: '/pages/login/index' }) }
onShow(() => { uni.setNavigationBarTitle({ title: 'Register' }) })
</script>
<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page { min-height: 100vh; background: $hb-paper; }
.status { display: flex; justify-content: space-between; padding: 14px 28px 0; }
.t { font-size: 12px; font-weight: 700; color: $hb-ink; }
.body { padding: 40px 24px; }
.brand { display: block; font-size: 13px; font-weight: 700; color: $hb-deep; }
.title { display: block; margin-top: 8px; font-size: 26px; font-weight: 800; color: $hb-ink; }
.field { margin-top: 14px; background: #fff; border: 1px solid $hb-line; border-radius: 12px; padding: 12px 14px; }
.lab { display: block; font-size: 11px; font-weight: 600; color: $hb-muted; margin-bottom: 4px; }
.inp { width: 100%; font-size: 14px; color: $hb-ink; }
.btn {
  margin-top: 16px; height: 48px; border-radius: 12px; background: $hb-ink; color: #fff;
  display: flex; align-items: center; justify-content: center; font-weight: 700;
}
.alt { margin-top: 14px; text-align: center; color: $hb-deep; font-size: 13px; font-weight: 600; }
</style>
