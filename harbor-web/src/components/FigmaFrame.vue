<template>
  <div class="figma-stage">
    <div class="figma-frame" :data-figma="spec?.id" :data-frame-title="spec?.title">
      <img class="art" :src="src" :alt="spec?.title || 'Harbor'" width="768" height="1792" draggable="false" />
      <button
        v-for="(h, i) in spec?.hits || []"
        :key="i"
        type="button"
        class="hit"
        :style="box(h)"
        :aria-label="h.label"
        @click="go(h)"
      />
      <form v-if="spec?.id === '1-30'" class="login-form" @submit.prevent="submitLogin">
        <input v-model="email" class="field email" type="email" autocomplete="email" aria-label="Email address" required />
        <input v-model="password" class="field pass" type="password" autocomplete="current-password" aria-label="Password" required />
        <p v-if="error" class="login-err">{{ error }}</p>
        <button class="hit submit" type="submit" :disabled="busy" aria-label="Log in" />
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { FRAMES, type FrameHit } from '@/figma/frames'
import { useCart } from '@/composables/cart'
import { loginAccount, submitCheckoutForm } from '@/api/accountApi'
import type { Product } from '@/api/products'

const props = defineProps<{ frame: string }>()
const router = useRouter()
const cart = useCart()
const spec = computed(() => FRAMES[props.frame])
const src = computed(() => `/figma/${props.frame}.png`)

const email = ref('')
const password = ref('')
const busy = ref(false)
const error = ref('')

function box(h: FrameHit) {
  return {
    left: (h.x / 768) * 100 + '%',
    top: (h.y / 1792) * 100 + '%',
    width: (h.w / 768) * 100 + '%',
    height: (h.h / 1792) * 100 + '%',
  }
}

function sampleProduct(): Product {
  return {
    id: 'figma-sample',
    sku: 'figma-sample',
    name: 'Harbor home essential',
    price: 4.99,
    category: 'home',
  }
}

async function placeOrder() {
  try {
    await cart.syncLocalToServer()
  } catch { /* local cart still submits */ }
  const res = await submitCheckoutForm({
    email: 'emily.carter@harbor.test',
    name: 'Emily Carter',
    address: '123 Maple Street, Apt 4B',
    city: 'San Francisco',
    region: 'CA',
    postal: '94107',
    ship_country: 'US',
    phone: '',
    pay_method: 'card',
    coupon_code: '',
    submit_id: 'h5-' + Date.now().toString(36),
  })
  if (res.ok && res.orderId) {
    router.push({ path: '/order-success', query: { id: res.orderId } })
    return
  }
  if (res.ok && res.payUrl) {
    window.location.href = res.payUrl
    return
  }
  router.push('/order-success')
}

function go(h: FrameHit) {
  if (h.action === 'back') {
    if (window.history.length > 1) router.back()
    else router.push('/home')
    return
  }
  if (h.action === 'add-cart') {
    cart.add(sampleProduct())
    router.push('/cart')
    return
  }
  if (h.action === 'place-order') {
    void placeOrder()
    return
  }
  if (h.to) router.push(h.to)
}

async function submitLogin() {
  busy.value = true
  error.value = ''
  try {
    const res = await loginAccount(email.value, password.value, '/me')
    if (!res.ok) {
      error.value = res.error === 'bad-credentials' ? '邮箱或密码不对' : '登录失败'
      return
    }
    const dest = res.next && res.next.startsWith('/') ? res.next : '/me'
    if (/^https?:\/\//i.test(String(res.next || ''))) window.location.href = String(res.next)
    else router.replace(dest)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    busy.value = false
  }
}
</script>

<style scoped>
.figma-stage {
  min-height: 100vh;
  background: #fcfaf8;
  display: flex;
  justify-content: center;
}
.figma-frame {
  position: relative;
  width: min(100vw, 768px);
  line-height: 0;
}
.art {
  width: 100%;
  height: auto;
  display: block;
  user-select: none;
  pointer-events: none;
}
.hit {
  position: absolute;
  border: 0;
  padding: 0;
  margin: 0;
  background: transparent;
  cursor: pointer;
  line-height: 0;
}
.login-form { position: absolute; inset: 0; }
.field {
  position: absolute;
  left: 6.64%;
  width: 86.7%;
  height: 4.7%;
  border: 1.5px solid #e4d8d1;
  border-radius: 16px;
  background: #fdf9f6;
  color: #1c2430;
  font-size: 16px;
  padding: 0 16px 0 48px;
  line-height: 1.2;
  outline: none;
}
.field.email { top: 51.4%; }
.field.pass { top: 56.9%; }
.login-err {
  position: absolute;
  left: 8%;
  top: 62%;
  margin: 0;
  color: #e11d2e;
  font-size: 13px;
  line-height: 1.3;
  background: #fff;
  padding: 2px 6px;
  border-radius: 6px;
}
.submit {
  left: 6.25%;
  top: 63.3%;
  width: 87.5%;
  height: 4.6%;
}
</style>
