<template>
  <view class="fn-page page" data-figma="A26">
    <view class="head">
      <view class="back" @click="goBack">←</view>
      <view>
        <text class="title">{{ t('help_contact') }}</text>
        <text class="sub">{{ t('contact_sub') }}</text>
      </view>
    </view>
    <view class="form">
      <text class="fl">{{ t('contact_email') }}</text>
      <input class="inp" v-model="email" :placeholder="t('contact_email_ph')" />
      <text class="fl">{{ t('contact_topic') }}</text>
      <input class="inp" v-model="topic" :placeholder="t('contact_topic_ph')" />
      <text class="fl">{{ t('contact_message') }}</text>
      <textarea class="area" v-model="body" :placeholder="t('contact_how')" />
      <view class="btn" @click="send">{{ t('contact_send') }}</view>
    </view>
    <view class="links">
      <text class="l" @click="goPolicy('shipping')">{{ t('help_shipping') }}</text>
      <text class="l" @click="goPolicy('privacy')">{{ t('help_privacy') }}</text>
    </view>
  </view>
</template>
<script setup lang="ts">
import { onShow } from '@dcloudio/uni-app'
import { useI18n } from '@/composables/i18n'
import { ref } from 'vue'
import { postContact, openHarborWeb } from '@/api/accountApi'
const { t } = useI18n()
const email = ref('')
const topic = ref('')
const body = ref('')
async function send() {
  if (!email.value.includes('@') || !body.value.trim()) {
    uni.showToast({ title: t('contact_required'), icon: 'none' })
    return
  }
  const msg = topic.value ? `${topic.value}\n${body.value}` : body.value
  try {
    const res = await postContact(email.value, msg, topic.value)
    uni.showToast({ title: res.statusCode < 400 ? 'Sent' : 'Try Harbor form', icon: 'none' })
    if (res.statusCode >= 400) openHarborWeb('/contact', 'Contact')
    else { body.value = ''; topic.value = '' }
  } catch {
    openHarborWeb('/contact', 'Contact')
  }
}
function goPolicy(kind: string) { uni.navigateTo({ url: '/pages/policy/index?kind=' + kind }) }
function goBack() { uni.navigateBack({ fail: () => uni.navigateTo({ url: '/pages/help/index' }) }) }

onShow(() => {
  uni.setNavigationBarTitle({ title: t('contact_title') })
})
</script>
<style lang="scss" scoped>
@import '@/styles/theme.scss';
.page { min-height: 100vh; background: $hb-paper; padding: 12px 16px 40px; padding-top: calc(12px + env(safe-area-inset-top)); }
.head { display: flex; gap: 12px; align-items: center; margin-bottom: 16px; }
.back { width: 36px; height: 36px; border-radius: 12px; background: $hb-white; text-align: center; line-height: 36px; box-shadow: $hb-shadow-soft; }
.title { display: block; font-size: 24px; font-weight: 720; }
.sub { display: block; font-size: 12px; color: $hb-muted; margin-top: 2px; }
.form { background: $hb-white; border-radius: 20px; padding: 16px; box-shadow: $hb-shadow-soft; }
.fl { display: block; font-size: 12px; color: $hb-muted; font-weight: 650; margin: 10px 0 6px; }
.inp, .area { background: $hb-paper; border-radius: 12px; padding: 12px; font-size: 14px; width: 100%; box-sizing: border-box; }
.area { min-height: 120px; }
.btn { margin-top: 16px; text-align: center; padding: 14px; border-radius: 16px; background: $hb-forest; color: #fff; font-weight: 720; }
.links { margin-top: 16px; display: flex; gap: 16px; }
.l { color: $hb-forest; font-weight: 680; font-size: 13px; }

.fn-page { background: #F7F4EF; color: #0F2744; min-height: 100vh; }

/* Function layout deepen */

.fn-page { background: #F7F4EF; color: #0F2744; min-height: 100vh; }
.fn-card { background: #fff; border: 1px solid #E8E4DC; border-radius: 16px; padding: 14px; margin-bottom: 10px; }
.fn-title { font-size: 17px; font-weight: 700; color: #0F2744; }
.fn-muted { font-size: 12px; color: #6B7280; }
.fn-btn { display: flex; align-items: center; justify-content: center; height: 40px; border-radius: 12px; background: #0F2744; color: #fff; font-weight: 600; }
.fn-btn.outline { background: #fff; color: #0F2744; border: 1px solid #E8E4DC; }
.fn-amber { color: #B45309; font-weight: 700; }
</style>
